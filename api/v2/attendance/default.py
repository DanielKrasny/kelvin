from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from ninja import Router
from ninja.errors import HttpError
from ninja.security import django_auth
from kelvin.settings import ATTENDANCE_PUBLIC_KEY_PATH
from api.v2.dto import ErrorResponse
from api.v2.security import is_teacher_auth
from attendance.models import ClassSession, AttendanceToken
from .class_session.default import ensure_class_write_access
from .device.utils import get_active_device
from .dto import (
    AttendancePublicKeyDTO,
    AttendanceTokenDTO,
    EncryptedMessageSchema,
    CreateAttendanceTokenInnerSchema,
    attendance_token_to_dto,
)
from .utils import process_encrypted_attendance_message

router = Router()


@router.get(
    "/server-public-key",
    summary="Get server's public key for encryption",
    url_name="get_server_public_key",
    response={200: AttendancePublicKeyDTO, 401: ErrorResponse, 404: ErrorResponse},
    auth=django_auth,
)
def get_server_public_key(request) -> AttendancePublicKeyDTO:
    try:
        with open(ATTENDANCE_PUBLIC_KEY_PATH, "r") as f:
            public_key = f.read()
            return AttendancePublicKeyDTO(public_key=public_key)
    except FileNotFoundError:
        raise HttpError(404, "Server public key not found.")


@router.post(
    "/token",
    response={
        200: AttendanceTokenDTO,
        400: ErrorResponse,
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
        422: ErrorResponse,
        500: ErrorResponse,
    },
    summary="Create an attendance token",
    url_name="create_attendance_token",
    auth=is_teacher_auth,
)
def create_attendance_token(request, body: EncryptedMessageSchema) -> AttendanceTokenDTO:
    if not hasattr(request.user, "current_token") or not request.user.current_token:
        raise HttpError(403, "User must be logged in via API token to use this endpoint.")

    data = process_encrypted_attendance_message(
        user=request.user,
        body=body,
        schema_class=CreateAttendanceTokenInnerSchema,
    )
    if data.user_id != request.user.id:
        raise HttpError(403, "User mismatch.")
    device = get_active_device(request.user)
    session = get_object_or_404(
        ClassSession.objects.select_related("clazz"), pk=data.class_session_id
    )
    ensure_class_write_access(request, session.clazz)
    if session.end <= timezone.now():
        raise HttpError(
            400, "Cannot create attendance token for a class session that has already ended."
        )
    expires_at = timezone.now() + timedelta(seconds=data.length)
    token_str = get_random_string(64)

    attendance_token = AttendanceToken.objects.create(
        class_session=session,
        token=token_str,
        method=data.method,
        expires_at=expires_at,
        created_by=request.user,
        created_by_device=device,
    )

    return attendance_token_to_dto(attendance_token)
