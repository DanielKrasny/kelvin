from typing import List, Optional, Set
from django.db import transaction
from ninja import Path, Router, Query
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja.security import django_auth, django_auth_superuser
from api.v2.dto import ErrorResponse
from attendance.models import AttendanceDevice
from .dto import AttendanceDeviceDTO, attendance_device_to_dto
from .schema import (
    CreateAttendanceDeviceSchema,
    UpdateAttendanceDeviceSchema,
    BulkUpdateAttendanceDeviceSchema,
)
from .utils import (
    list_devices,
    get_device,
    get_initial_device_state,
    notify_device_change,
    notify_devices_change,
)

router = Router()


@router.get(
    "/",
    response={200: List[AttendanceDeviceDTO], 401: ErrorResponse},
    summary="List all attendance devices for the logged in user",
    url_name="list_attendance_devices",
    auth=django_auth,
)
@paginate
def list_attendance_devices(
    request,
    state: Optional[Set[AttendanceDevice.DeviceState]] = Query(
        None, description="States to filter the list of attendance devices"
    ),
) -> List[AttendanceDeviceDTO]:
    return [
        attendance_device_to_dto(device) for device in list_devices(user=request.user, state=state)
    ]


@router.get(
    "/all",
    response={200: List[AttendanceDeviceDTO], 401: ErrorResponse},
    summary="List all attendance devices for all users",
    url_name="list_all_attendance_devices",
    auth=django_auth_superuser,
)
@paginate
def list_all_attendance_devices(
    request,
    state: Optional[Set[AttendanceDevice.DeviceState]] = Query(
        None, description="States to filter the list of attendance devices"
    ),
) -> List[AttendanceDeviceDTO]:
    return [attendance_device_to_dto(device) for device in list_devices(state=state)]


@router.get(
    "/user/{login}",
    response={
        200: List[AttendanceDeviceDTO],
        401: ErrorResponse,
        404: ErrorResponse,
    },
    summary="List all attendance devices for a specific user",
    url_name="list_attendance_devices_for_user",
    auth=django_auth_superuser,
)
@paginate
def list_attendance_devices_for_user(
    request,
    login: str = Path(...),
    state: Optional[Set[AttendanceDevice.DeviceState]] = Query(
        None, description="States to filter the list of attendance devices"
    ),
) -> List[AttendanceDeviceDTO]:
    return [attendance_device_to_dto(device) for device in list_devices(login=login, state=state)]


@router.post(
    "/",
    response={200: AttendanceDeviceDTO, 400: ErrorResponse, 401: ErrorResponse, 409: ErrorResponse},
    summary="Create a new attendance device for the logged in user",
    url_name="create_attendance_device",
    auth=django_auth,
)
@transaction.atomic
def create_attendance_device(request, body: CreateAttendanceDeviceSchema) -> AttendanceDeviceDTO:
    state = get_initial_device_state(request.user)
    device = AttendanceDevice.objects.create(
        user=request.user,
        device_name=body.device_name,
        public_key=body.public_key,
        state=state,
    )
    notify_device_change(request.user, device)
    return attendance_device_to_dto(device)


@router.patch(
    "/bulk",
    response={
        200: List[AttendanceDeviceDTO],
        400: ErrorResponse,
        401: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Perform a bulk action on attendance devices",
    url_name="bulk_attendance_device_action",
    auth=django_auth_superuser,
)
def bulk_attendance_device_action(
    request, body: BulkUpdateAttendanceDeviceSchema
) -> List[AttendanceDeviceDTO]:
    devices = AttendanceDevice.objects.select_related("user").filter(pk__in=body.device_ids)
    device_ids = {device.pk for device in devices}
    users = {device.user.pk for device in devices}

    missing_ids = [device_id for device_id in body.device_ids if device_id not in device_ids]
    if missing_ids:
        raise HttpError(404, f"Attendance devices with IDs {missing_ids} not found.")
    invalid_ids = [
        device.pk for device in devices if device.state == AttendanceDevice.DeviceState.REVOKED
    ]
    if invalid_ids:
        raise HttpError(
            400,
            f"Attendance devices with IDs {invalid_ids} have revoked state. These can't be changed.",
        )

    if body.revoke_active_devices:
        active_devices = AttendanceDevice.objects.select_related("user").filter(
            user__pk__in=users, state=AttendanceDevice.DeviceState.ACTIVE
        )
        active_devices.update(state=AttendanceDevice.DeviceState.REVOKED)

    devices.update(state=body.state)
    notify_devices_change(request.user, list(devices))
    return [attendance_device_to_dto(device) for device in devices]


@router.get(
    "/{device_id}",
    response={200: AttendanceDeviceDTO, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    summary="Get an attendance device",
    url_name="get_attendance_device",
    auth=django_auth,
)
def get_attendance_device(request, device_id: int) -> AttendanceDeviceDTO:
    return attendance_device_to_dto(get_device(request, device_id))


@router.patch(
    "/{device_id}",
    response={200: AttendanceDeviceDTO, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    summary="Update an attendance device",
    url_name="update_attendance_device",
    auth=django_auth,
)
def update_attendance_device(
    request, device_id: int, body: UpdateAttendanceDeviceSchema
) -> AttendanceDeviceDTO:
    device = get_device(request, device_id)
    if not request.user.is_superuser and body.state == AttendanceDevice.DeviceState.ACTIVE:
        raise HttpError(
            403, "You do not have permission to set an attendance device to active state."
        )
    if (
        body.state == AttendanceDevice.DeviceState.ACTIVE
        and device.state == AttendanceDevice.DeviceState.REVOKED
    ):
        raise HttpError(400, "You cannot activate a revoked device.")
    device.state = body.state
    device.save()
    return attendance_device_to_dto(device)
