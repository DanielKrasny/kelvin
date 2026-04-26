from datetime import timedelta
from typing import List, Optional, Set
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from ninja.errors import HttpError
from notifications.signals import notify
from attendance.models import AttendanceDevice
from common.utils import is_teacher


def list_devices(
    user: Optional[User] = None,
    login: Optional[str] = None,
    state: Optional[Set[AttendanceDevice.DeviceState]] = None,
) -> models.QuerySet[AttendanceDevice]:
    qs = AttendanceDevice.objects.select_related("user")
    if user:
        qs = qs.filter(user=user)
    elif login:
        qs = qs.filter(user__username__iexact=login)

    if state:
        qs = qs.filter(state__in=state)

    return qs.order_by("-created_at")


def get_active_device(user: User) -> AttendanceDevice:
    device = list_devices(user=user, state={AttendanceDevice.DeviceState.ACTIVE}).first()
    if not device:
        raise HttpError(404, "No active attendance device found for this user.")
    return device


def get_device(request, device_id: int) -> AttendanceDevice:
    device = AttendanceDevice.objects.select_related("user").filter(pk=device_id).first()
    if not device:
        raise HttpError(404, f"Attendance device with ID '{device_id}' not found.")
    if device.user.pk != request.user.pk and not request.user.is_superuser:
        raise HttpError(403, "You do not have permission to access this attendance device.")
    return device


def get_initial_device_state(user: User) -> AttendanceDevice.DeviceState:
    one_year_ago = timezone.now() - timedelta(days=365)
    agg = AttendanceDevice.objects.filter(user=user).aggregate(
        has_pending=models.Count("pk", filter=models.Q(state=AttendanceDevice.DeviceState.PENDING)),
        has_active=models.Count("pk", filter=models.Q(state=AttendanceDevice.DeviceState.ACTIVE)),
        last_created_at=models.Max("created_at"),
    )
    has_pending = agg["has_pending"] > 0
    has_active = agg["has_active"] > 0
    last_created_at = agg["last_created_at"]

    if has_pending:
        raise HttpError(409, "The logged in user already has a pending attendance device.")

    if is_teacher(user):
        if has_active:
            raise HttpError(409, "The logged in user already has an active attendance device.")
        return AttendanceDevice.DeviceState.ACTIVE

    if has_active or (last_created_at is not None and last_created_at >= one_year_ago):
        return AttendanceDevice.DeviceState.PENDING

    return AttendanceDevice.DeviceState.ACTIVE


def notify_device_change(actor: User, device: AttendanceDevice) -> None:
    if actor.pk == device.user.pk:
        return

    match device.state:
        case AttendanceDevice.DeviceState.ACTIVE:
            verb = "activated"
        case AttendanceDevice.DeviceState.REVOKED:
            verb = "revoked"
        case AttendanceDevice.DeviceState.PENDING:
            verb = "added pending"
        case _:
            verb = "updated"

    recipients = [device.user]
    if device.state == AttendanceDevice.DeviceState.PENDING:
        recipients = User.objects.filter(is_superuser=True).exclude(pk=actor.pk)

    notify.send(
        sender=actor,
        recipient=recipients,
        verb=f"{verb} attendance device",
        action_object=device,
        public=False,
        important=True,
    )


def notify_devices_change(actor: User, devices: List[AttendanceDevice]) -> None:
    for device in devices:
        notify_device_change(actor, device)
