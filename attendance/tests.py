import json
from base64 import b64encode
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.test import Client, TestCase
from notifications.models import Notification

from attendance.models import AttendanceDevice, ClassSession
from common.models import Class, Semester, Subject


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
        self.assertEqual(Notification.objects.count(), 1)

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


class ClassSessionAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(username="teacher", password="pw")
        self.other_teacher = User.objects.create_user(username="other-teacher", password="pw")
        self.student = User.objects.create_user(username="student", password="pw")
        self.superuser = User.objects.create_superuser(username="admin", password="pw")

        teachers_group, _ = Group.objects.get_or_create(name="teachers")
        self.teacher.groups.add(teachers_group)
        self.other_teacher.groups.add(teachers_group)

        self.semester = Semester.objects.create(
            begin=date(2026, 2, 1),
            end=date(2026, 6, 30),
            year=2026,
            winter=False,
            active=True,
            inbus_semester_id=1,
        )
        self.subject = Subject.objects.create(name="Programming", abbr="PRG")
        self.teacher_class = self.create_class(self.teacher, code="P/01")
        self.other_teacher_class = self.create_class(self.other_teacher, code="P/02")

    def login(self, user: User) -> None:
        self.client.force_login(user)

    def create_class(self, teacher: User, *, code: str) -> Class:
        return Class.objects.create(
            code=code,
            teacher=teacher,
            semester=self.semester,
            subject=self.subject,
            day=Class.Day.MONDAY,
            time=time(10, 0),
        )

    def create_session(self, clazz: Class, **kwargs) -> ClassSession:
        start = timezone.make_aware(datetime(2026, 4, 28, 10, 0))
        data = {
            "clazz": clazz,
            "start": start,
            "end": start + timedelta(hours=2),
        }
        data.update(kwargs)
        return ClassSession.objects.create(**data)

    def test_teacher_can_create_class_session_for_own_class(self):
        self.login(self.teacher)
        start = timezone.make_aware(datetime(2026, 5, 5, 9, 0))
        end = start + timedelta(hours=2)

        response = self.client.post(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}",
            data=json.dumps(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["class_id"], self.teacher_class.id)
        self.assertEqual(payload["class_code"], self.teacher_class.code)
        self.assertEqual(ClassSession.objects.count(), 1)

    def test_teacher_cannot_create_class_session_for_other_teachers_class(self):
        self.login(self.teacher)
        start = timezone.make_aware(datetime(2026, 5, 5, 9, 0))
        end = start + timedelta(hours=2)

        response = self.client.post(
            f"/api/v2/attendance/class-session/class/{self.other_teacher_class.id}",
            data=json.dumps(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ClassSession.objects.count(), 0)

    def test_list_class_sessions_returns_only_teachers_own_sessions(self):
        own_session = self.create_session(self.teacher_class)
        self.create_session(
            self.other_teacher_class,
            start=timezone.make_aware(datetime(2026, 4, 29, 10, 0)),
            end=timezone.make_aware(datetime(2026, 4, 29, 12, 0)),
        )
        self.login(self.teacher)

        response = self.client.get(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["id"], own_session.id)

    def test_teacher_cannot_list_other_teachers_class_sessions(self):
        self.create_session(self.other_teacher_class)
        self.login(self.teacher)

        response = self.client.get(
            f"/api/v2/attendance/class-session/class/{self.other_teacher_class.id}"
        )

        self.assertEqual(response.status_code, 403)

    def test_get_class_session_returns_session_details(self):
        session = self.create_session(self.teacher_class)
        self.login(self.teacher)

        response = self.client.get(f"/api/v2/attendance/class-session/{session.id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], session.id)
        self.assertEqual(payload["class_id"], self.teacher_class.id)

    def test_get_class_session_for_other_teachers_class_returns_403(self):
        session = self.create_session(self.other_teacher_class)
        self.login(self.teacher)

        response = self.client.get(f"/api/v2/attendance/class-session/{session.id}")

        self.assertEqual(response.status_code, 403)

    def test_teacher_can_update_class_session(self):
        session = self.create_session(self.teacher_class)
        self.login(self.teacher)
        new_end = session.end + timedelta(hours=1)

        response = self.client.patch(
            f"/api/v2/attendance/class-session/{session.id}",
            data=json.dumps({"end": new_end.isoformat()}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.end, new_end)

    def test_teacher_can_delete_class_session(self):
        session = self.create_session(self.teacher_class)
        self.login(self.teacher)

        response = self.client.delete(f"/api/v2/attendance/class-session/{session.id}")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClassSession.objects.filter(id=session.id).exists())

    def test_bulk_create_class_sessions(self):
        self.login(self.teacher)
        first_start = timezone.make_aware(datetime(2026, 5, 6, 8, 0))
        second_start = timezone.make_aware(datetime(2026, 5, 13, 8, 0))

        response = self.client.post(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}/bulk",
            data=json.dumps(
                {
                    "sessions": [
                        {
                            "start": first_start.isoformat(),
                            "end": (first_start + timedelta(hours=2)).isoformat(),
                        },
                        {
                            "start": second_start.isoformat(),
                            "end": (second_start + timedelta(hours=2)).isoformat(),
                        },
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClassSession.objects.count(), 2)
        self.assertEqual(len(response.json()), 2)

    def test_bulk_update_class_sessions(self):
        first_session = self.create_session(self.teacher_class)
        second_session = self.create_session(
            self.teacher_class,
            start=timezone.make_aware(datetime(2026, 4, 30, 10, 0)),
            end=timezone.make_aware(datetime(2026, 4, 30, 12, 0)),
        )
        self.login(self.teacher)
        new_start = first_session.start + timedelta(minutes=30)
        new_end = second_session.end + timedelta(hours=1)

        response = self.client.patch(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}/bulk",
            data=json.dumps(
                {
                    "sessions": [
                        {"id": first_session.id, "start": new_start.isoformat()},
                        {"id": second_session.id, "end": new_end.isoformat()},
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        first_session.refresh_from_db()
        second_session.refresh_from_db()
        self.assertEqual(first_session.start, new_start)
        self.assertEqual(second_session.end, new_end)
        self.assertEqual(len(response.json()), 2)

    def test_bulk_update_class_sessions_returns_404_for_missing_id(self):
        self.login(self.teacher)

        response = self.client.patch(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}/bulk",
            data=json.dumps({"sessions": [{"id": 999999, "end": timezone.now().isoformat()}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_bulk_update_fails_if_session_does_not_belong_to_class(self):
        session = self.create_session(self.other_teacher_class)
        self.login(self.teacher)

        response = self.client.patch(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}/bulk",
            data=json.dumps({"sessions": [{"id": session.id, "end": timezone.now().isoformat()}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_bulk_delete_class_sessions(self):
        first_session = self.create_session(self.teacher_class)
        second_session = self.create_session(
            self.teacher_class,
            start=timezone.make_aware(datetime(2026, 4, 30, 10, 0)),
            end=timezone.make_aware(datetime(2026, 4, 30, 12, 0)),
        )
        self.login(self.teacher)

        response = self.client.delete(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}/bulk",
            data=json.dumps({"session_ids": [first_session.id, second_session.id]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["deleted_ids"]), {first_session.id, second_session.id})
        self.assertEqual(ClassSession.objects.count(), 0)

    def test_create_class_session_rejects_invalid_time_range(self):
        self.login(self.teacher)
        start = timezone.make_aware(datetime(2026, 5, 5, 11, 0))
        end = start - timedelta(minutes=15)

        response = self.client.post(
            f"/api/v2/attendance/class-session/class/{self.teacher_class.id}",
            data=json.dumps(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_list_upcoming_class_sessions(self):
        class_teacher = self.create_class(self.teacher, code="T/01")
        class_student = self.create_class(self.other_teacher, code="S/01")
        class_student.students.add(self.student)
        class_unrelated = self.create_class(self.other_teacher, code="U/01")

        now = timezone.now()

        session_teacher = self.create_session(
            class_teacher, start=now + timedelta(days=1), end=now + timedelta(days=1, hours=2)
        )
        session_student = self.create_session(
            class_student, start=now + timedelta(days=2), end=now + timedelta(days=2, hours=2)
        )

        self.create_session(
            class_teacher,
            start=now - timedelta(days=1, hours=2),
            end=now - timedelta(days=1),
        )

        self.create_session(
            class_unrelated, start=now + timedelta(days=3), end=now + timedelta(days=3, hours=2)
        )

        self.login(self.teacher)
        response = self.client.get("/api/v2/attendance/class-session/upcoming")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["id"], session_teacher.id)
        self.assertEqual(payload["items"][0]["teacher_id"], self.teacher.id)

        self.login(self.student)
        response = self.client.get("/api/v2/attendance/class-session/upcoming")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["id"], session_student.id)
        self.assertEqual(payload["items"][0]["teacher_id"], self.other_teacher.id)
