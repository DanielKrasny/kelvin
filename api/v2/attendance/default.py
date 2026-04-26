from datetime import timedelta
from typing import List
from django.db import transaction
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from ninja import Router
from ninja.errors import HttpError
from ninja.security import django_auth
from kelvin.settings import ATTENDANCE_PUBLIC_KEY_PATH
from api.v2.dto import ErrorResponse
from api.v2.security import is_teacher_auth
from attendance.models import ClassSession, AttendanceToken, Attendance
from .class_session.default import get_session_and_ensure_access
from .device.utils import get_active_device
from .dto import (
    AttendancePublicKeyDTO,
    AttendanceTokenDTO,
    AttendanceRecordDTO,
    EncryptedMessageSchema,
    CreateAttendanceTokenInnerSchema,
    CreateAttendanceRecordsTeacherManualSchema,
    attendance_token_to_dto,
    attendance_record_to_dto,
    CreateAttendanceRecordStudentInnerSchema,
    CreateAttendanceRecordsTeacherInnerSchema,
    CreateAttendanceRecordsTeacherResponseSchema,
)
from .utils import process_encrypted_attendance_message

router = Router()


def ensure_api_token(request):
    if not hasattr(request.user, "current_token") or not request.user.current_token:
        raise HttpError(403, "User must be logged in via API token to use this endpoint.")


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
    ensure_api_token(request)

    data = process_encrypted_attendance_message(
        user=request.user,
        body=body,
        schema_class=CreateAttendanceTokenInnerSchema,
    )
    if data.user_id != request.user.id:
        raise HttpError(403, "User mismatch.")

    device = get_active_device(request.user)
    session = get_session_and_ensure_access(request, data.class_session_id)

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


@router.post(
    "/log",
    response={
        200: AttendanceRecordDTO,
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
        422: ErrorResponse,
        500: ErrorResponse,
    },
    summary="Create an attendance record",
    url_name="create_attendance_record",
    auth=django_auth,
)
def create_attendance_record(request, body: EncryptedMessageSchema) -> AttendanceRecordDTO:
    ensure_api_token(request)

    data = process_encrypted_attendance_message(
        user=request.user,
        body=body,
        schema_class=CreateAttendanceRecordStudentInnerSchema,
    )

    if data.user_id != request.user.id:
        raise HttpError(403, "User mismatch.")

    device = get_active_device(request.user)
    session = get_object_or_404(
        ClassSession.objects.select_related("clazz"), pk=data.class_session_id
    )
    token = session.attendance_tokens.filter(
        token=data.token.strip(),
        created_at__gt=data.created_at,
        expires_at__gt=timezone.now(),
        method=AttendanceToken.Method.QR_CODE,
    )

    if not token.exists():
        raise HttpError(403, "Invalid token.")

    record = Attendance.objects.create(
        student=request.user,
        class_session=session,
        attendance_time=data.created_at,
        is_present=True,
        record_format=Attendance.RecordFormat.MANUAL_STUDENT,
        created_by=request.user,
        created_by_device=device,
    )

    return attendance_record_to_dto(record)


@router.post(
    "/teacher/manual",
    response={
        200: List[AttendanceRecordDTO],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
        422: ErrorResponse,
    },
    summary="Manually mark students' presence in a class session (teacher only)",
    url_name="create_attendance_record_manual",
    auth=is_teacher_auth,
)
@transaction.atomic
def create_attendance_records_manual(
    request, body: CreateAttendanceRecordsTeacherManualSchema
) -> List[AttendanceRecordDTO]:
    session = get_session_and_ensure_access(request, body.class_session_id)

    results = []
    for record_data in body.records:
        student = get_object_or_404(User, username=record_data.student_login)

        existing_records = Attendance.objects.filter(
            class_session=session,
            student=student,
            record_format=Attendance.RecordFormat.MANUAL_TEACHER,
        )

        if existing_records.exists():
            for record in existing_records:
                record.is_present = record_data.is_present
                record.save()
                results.append(attendance_record_to_dto(record))
        else:
            record = Attendance.objects.create(
                student=student,
                class_session=session,
                attendance_time=timezone.now(),
                is_present=record_data.is_present,
                record_format=Attendance.RecordFormat.MANUAL_TEACHER,
                created_by=request.user,
                created_by_device=None,
            )
            results.append(attendance_record_to_dto(record))

    return results


@router.post(
    "/teacher/log",
    response={
        200: CreateAttendanceRecordsTeacherResponseSchema,
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
        422: ErrorResponse,
    },
    summary="Mark students' presence in a class session from their encrypted messages (teacher only)",
    url_name="create_attendance_records_teacher",
    auth=is_teacher_auth,
)
def create_attendance_records_teacher(
    request, body: EncryptedMessageSchema
) -> CreateAttendanceRecordsTeacherResponseSchema:
    ensure_api_token(request)

    data = process_encrypted_attendance_message(
        user=request.user,
        body=body,
        schema_class=CreateAttendanceRecordsTeacherInnerSchema
    )

    session = get_session_and_ensure_access(request, data.class_session_id)

    success = []
    failed = {}

    for i, record_msg in enumerate(data.records):
        try:
            data = process_encrypted_attendance_message(
                body=record_msg,
                schema_class=CreateAttendanceRecordStudentInnerSchema,
                user=None,
            )

            if data.class_session_id != session.id:
                raise HttpError(
                    400, f"Session mismatch: expected {session.id}, got {data.class_session_id}"
                )

            if data.created_at > record_msg.received_at:
                raise HttpError(400, "Invalid record creation time.")

            if record_msg.received_at - data.created_at > timedelta(minutes=30):
                raise HttpError(400, "Record is too old.")

            tokens = session.attendance_tokens.filter(
                token=data.token.strip(),
                method=AttendanceToken.Method.BLE,
                created_at__lte=data.created_at,
                expires_at__gte=data.created_at,
            )

            if not tokens.exists():
                raise HttpError(403, "Invalid or expired token.")

            student = get_object_or_404(User, pk=data.user_id)
            record = Attendance.objects.create(
                student=student,
                class_session=session,
                attendance_time=data.created_at,
                is_present=True,
                record_format=Attendance.RecordFormat.AUTOMATIC,
                created_by=request.user,
                created_by_device=None,
            )
            success.append(attendance_record_to_dto(record))
        except HttpError as e:
            failed[i] = str(e.message)
        except Exception as e:
            failed[i] = str(e)

    return CreateAttendanceRecordsTeacherResponseSchema(success=success, failed=failed)
