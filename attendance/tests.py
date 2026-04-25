import json
from base64 import b64encode
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from notifications.models import Notification

from attendance.models import AttendanceDevice


class AttendanceDeviceAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="student", password="pw")
        self.other_user = User.objects.create_user(username="other", password="pw")
        self.teacher = User.objects.create_user(username="teacher", password="pw")
        self.superuser = User.objects.create_superuser(username="admin", password="pw")
        teachers_group, _ = Group.objects.get_or_create(name="teachers")
        self.teacher.groups.add(teachers_group)
        self.public_key = b64encode(b"public-key-bytes").decode("ascii")

    def login(self, user: User) -> None:
        self.client.force_login(user)

    def create_device(self, user: User, **kwargs) -> AttendanceDevice:
        data = {
            "user": user,
            "device_name": "Device A",
            "public_key": "existing-public-key",
            "state": AttendanceDevice.DeviceState.ACTIVE,
        }
        data.update(kwargs)
        return AttendanceDevice.objects.create(**data)

    def assert_device_notification(
        self,
        *,
        recipient: User,
        actor: User,
        device: AttendanceDevice,
        verb: str,
    ) -> None:
        self.assertTrue(
            Notification.objects.filter(
                recipient=recipient,
                actor_content_type=ContentType.objects.get_for_model(User),
                actor_object_id=str(actor.id),
                action_object_content_type=ContentType.objects.get_for_model(AttendanceDevice),
                action_object_object_id=str(device.id),
                verb=verb,
                public=False,
            ).exists()
        )

    def test_create_attendance_device_creates_active_device(self):
        self.login(self.user)

        response = self.client.post(
            "/api/v2/attendance/device/",
            data=json.dumps({"device_name": "Phone", "public_key": self.public_key}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["device_name"], "Phone")
        self.assertEqual(payload["user_login"], self.user.username)
        self.assertEqual(payload["state"], AttendanceDevice.DeviceState.ACTIVE)
        self.assertNotIn("public_key", payload)
        self.assertEqual(Notification.objects.count(), 0)

    def test_create_attendance_device_creates_pending_device_when_active_exists(self):
        self.create_device(self.user, state=AttendanceDevice.DeviceState.ACTIVE)
        self.login(self.user)

        response = self.client.post(
            "/api/v2/attendance/device/",
            data=json.dumps({"device_name": "Phone", "public_key": self.public_key}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], AttendanceDevice.DeviceState.PENDING)
        device = AttendanceDevice.objects.get(id=payload["id"])
        self.assertEqual(AttendanceDevice.objects.filter(user=self.user).count(), 2)
        self.assertEqual(Notification.objects.count(), 0)

    def test_create_attendance_device_returns_409_when_pending_exists(self):
        self.create_device(self.user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.user)

        response = self.client.post(
            "/api/v2/attendance/device/",
            data=json.dumps({"device_name": "Phone", "public_key": self.public_key}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(AttendanceDevice.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Notification.objects.count(), 0)

    def test_list_attendance_devices_returns_paginated_items_for_logged_in_user(self):
        device = self.create_device(self.user)
        self.login(self.user)

        with patch(
            "api.v2.attendance.device.default.list_devices", return_value=[device]
        ) as mock_list:
            response = self.client.get("/api/v2/attendance/device/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["id"], device.id)
        mock_list.assert_called_once_with(user=self.user, state=None)

    def test_list_all_attendance_devices_is_superuser_only(self):
        self.login(self.user)
        response = self.client.get("/api/v2/attendance/device/all")
        self.assertEqual(response.status_code, 401)

        self.login(self.superuser)
        devices = [self.create_device(self.user), self.create_device(self.other_user)]

        with patch(
            "api.v2.attendance.device.default.list_devices",
            return_value=devices,
        ) as mock_list:
            response = self.client.get("/api/v2/attendance/device/all")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 2)
        mock_list.assert_called_once_with(state=None)

    def test_list_attendance_devices_for_other_user_requires_superuser(self):
        self.login(self.user)

        response = self.client.get(f"/api/v2/attendance/device/user/{self.other_user.username}")

        self.assertEqual(response.status_code, 401)

    def test_list_attendance_devices_for_specific_user_allows_state_filter(self):
        device = self.create_device(self.other_user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.superuser)

        with patch(
            "api.v2.attendance.device.default.list_devices", return_value=[device]
        ) as mock_list:
            response = self.client.get(
                f"/api/v2/attendance/device/user/{self.other_user.username}?state=pending"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 1)
        mock_list.assert_called_once_with(
            login=self.other_user.username,
            state={AttendanceDevice.DeviceState.PENDING},
        )

    def test_get_attendance_device_returns_404_when_missing(self):
        self.login(self.user)

        response = self.client.get("/api/v2/attendance/device/999999")

        self.assertEqual(response.status_code, 404)

    def test_user_can_revoke_own_attendance_device(self):
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.user)

        response = self.client.patch(
            f"/api/v2/attendance/device/{device.id}",
            data=json.dumps({"state": AttendanceDevice.DeviceState.REVOKED}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.state, AttendanceDevice.DeviceState.REVOKED)

    def test_non_superuser_cannot_activate_attendance_device(self):
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.user)

        response = self.client.patch(
            f"/api/v2/attendance/device/{device.id}",
            data=json.dumps({"state": AttendanceDevice.DeviceState.ACTIVE}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        device.refresh_from_db()
        self.assertEqual(device.state, AttendanceDevice.DeviceState.PENDING)

    def test_superuser_can_activate_pending_device(self):
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.superuser)

        response = self.client.patch(
            f"/api/v2/attendance/device/{device.id}",
            data=json.dumps({"state": AttendanceDevice.DeviceState.ACTIVE}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.state, AttendanceDevice.DeviceState.ACTIVE)

    def test_superuser_cannot_activate_revoked_device(self):
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.REVOKED)
        self.login(self.superuser)

        response = self.client.patch(
            f"/api/v2/attendance/device/{device.id}",
            data=json.dumps({"state": AttendanceDevice.DeviceState.ACTIVE}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        device.refresh_from_db()
        self.assertEqual(device.state, AttendanceDevice.DeviceState.REVOKED)

    def test_update_attendance_device_for_other_user_requires_superuser(self):
        device = self.create_device(self.other_user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.user)

        response = self.client.patch(
            f"/api/v2/attendance/device/{device.id}",
            data=json.dumps({"state": AttendanceDevice.DeviceState.REVOKED}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_revoke_attendance_device_for_other_user(self):
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.ACTIVE)
        self.login(self.superuser)

        response = self.client.patch(
            f"/api/v2/attendance/device/{device.id}",
            data=json.dumps({"state": AttendanceDevice.DeviceState.REVOKED}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.state, AttendanceDevice.DeviceState.REVOKED)
        self.assertEqual(Notification.objects.count(), 0)

    def test_bulk_activate_can_revoke_existing_active_devices(self):
        active_device = self.create_device(self.user, state=AttendanceDevice.DeviceState.ACTIVE)
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.PENDING)
        self.login(self.superuser)

        response = self.client.patch(
            "/api/v2/attendance/device/bulk",
            data=json.dumps(
                {
                    "device_ids": [device.id],
                    "state": AttendanceDevice.DeviceState.ACTIVE,
                    "revoke_active_devices": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        active_device.refresh_from_db()
        device.refresh_from_db()
        self.assertEqual(active_device.state, AttendanceDevice.DeviceState.REVOKED)
        self.assertEqual(device.state, AttendanceDevice.DeviceState.ACTIVE)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(Notification.objects.count(), 1)
        self.assert_device_notification(
            recipient=self.user,
            actor=self.superuser,
            device=device,
            verb="activated attendance device",
        )

    def test_bulk_action_returns_404_for_invalid_ids(self):
        self.login(self.superuser)

        response = self.client.patch(
            "/api/v2/attendance/device/bulk",
            data=json.dumps(
                {
                    "device_ids": [999999],
                    "state": AttendanceDevice.DeviceState.REVOKED,
                    "revoke_active_devices": False,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_bulk_action_returns_400_for_revoked_devices(self):
        device = self.create_device(self.user, state=AttendanceDevice.DeviceState.REVOKED)
        self.login(self.superuser)

        response = self.client.patch(
            "/api/v2/attendance/device/bulk",
            data=json.dumps(
                {
                    "device_ids": [device.id],
                    "state": AttendanceDevice.DeviceState.ACTIVE,
                    "revoke_active_devices": False,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
