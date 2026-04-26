from datetime import datetime
from typing import List, Optional, cast, Dict

from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Body, Path, Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja.security import django_auth

from api.v2.security import is_teacher_auth
from api.v2.dto import ErrorResponse
from api.v2.attendance.dto import AttendanceRecordDTO, attendance_record_to_dto
from attendance.models import ClassSession
from common.models import Class
from .dto import (
    BulkDeleteClassSessionResultDTO,
    ClassSessionDTO,
    SessionTimespanDTO,
    StudentPresenceDTO,
    class_session_to_dto,
)
from .schema import (
    BulkCreateClassSessionSchema,
    BulkDeleteClassSessionSchema,
    BulkUpdateClassSessionSchema,
    CreateClassSessionSchema,
    UpdateClassSessionSchema,
)
from .utils import calculate_aggregated_presence, calculate_session_timespans


router = Router()


def get_class(class_id: int) -> Class:
    return get_object_or_404(Class, pk=class_id)


def get_session(session_id: int) -> ClassSession:
    return get_object_or_404(
        ClassSession.objects.select_related("clazz", "clazz__teacher"), pk=session_id
    )


def ensure_class_write_access(request, clazz: Class) -> None:
    if clazz.teacher.pk != request.user.pk:
        raise HttpError(403, f"You do not have permission to manage class with ID '{clazz.pk}'.")


def get_session_and_ensure_access(request, session_id: int) -> ClassSession:
    session = get_session(session_id)
    ensure_class_write_access(request, session.clazz)
    return session


def validate_session_times(
    session: ClassSession, start: Optional[datetime], end: Optional[datetime]
) -> None:
    effective_start: datetime = cast(datetime, session.start)
    effective_end: datetime = cast(datetime, session.end)
    if start is not None:
        effective_start = start
    if end is not None:
        effective_end = end
    if effective_end <= effective_start:
        raise HttpError(400, "End time must be after start time.")


@router.get(
    "/upcoming",
    response={
        200: List[ClassSessionDTO],
        401: ErrorResponse,
    },
    summary="List upcoming class sessions for the current user",
    url_name="list_upcoming_class_sessions",
    auth=django_auth,
)
@paginate
def list_upcoming_class_sessions(request) -> List[ClassSessionDTO]:
    now = timezone.now()
    sessions = (
        ClassSession.objects.filter(
            models.Q(clazz__teacher=request.user) | models.Q(clazz__students=request.user),
            end__gt=now,
        )
        .select_related("clazz", "clazz__teacher")
        .distinct()
        .order_by("end", "id")
    )
    return [class_session_to_dto(session) for session in sessions]


@router.get(
    "/class/{class_id}",
    response={
        200: List[ClassSessionDTO],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="List class sessions for a specific class",
    url_name="list_class_sessions",
    auth=is_teacher_auth,
)
@paginate
def list_class_sessions(request, class_id: int = Path(...)) -> List[ClassSessionDTO]:
    clazz = get_class(class_id)
    ensure_class_write_access(request, clazz)

    sessions = (
        ClassSession.objects.select_related("clazz", "clazz__teacher")
        .filter(clazz=clazz)
        .order_by("start", "id")
    )
    return [class_session_to_dto(session) for session in sessions]


@router.post(
    "/class/{class_id}",
    response={200: ClassSessionDTO, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    summary="Create a new class session",
    url_name="create_class_session",
    auth=is_teacher_auth,
)
def create_class_session(
    request, class_id: int = Path(...), body: CreateClassSessionSchema = Body(...)
) -> ClassSessionDTO:
    clazz = get_class(class_id)
    ensure_class_write_access(request, clazz)

    session = ClassSession.objects.create(clazz=clazz, start=body.start, end=body.end)
    return class_session_to_dto(session)


@router.post(
    "/class/{class_id}/bulk",
    response={
        200: List[ClassSessionDTO],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Create multiple class sessions for a specific class",
    url_name="bulk_create_class_sessions",
    auth=is_teacher_auth,
)
@transaction.atomic
def bulk_create_class_sessions(
    request, class_id: int = Path(...), body: BulkCreateClassSessionSchema = Body(...)
) -> List[ClassSessionDTO]:
    clazz = get_class(class_id)
    ensure_class_write_access(request, clazz)

    sessions = [ClassSession(clazz=clazz, start=item.start, end=item.end) for item in body.sessions]

    created_sessions = ClassSession.objects.bulk_create(sessions)
    return [class_session_to_dto(session) for session in created_sessions]


@router.patch(
    "/class/{class_id}/bulk",
    response={
        200: List[ClassSessionDTO],
        400: ErrorResponse,
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Update multiple class sessions for a specific class",
    url_name="bulk_update_class_sessions",
    auth=is_teacher_auth,
)
@transaction.atomic
def bulk_update_class_sessions(
    request, class_id: int = Path(...), body: BulkUpdateClassSessionSchema = Body(...)
) -> List[ClassSessionDTO]:
    clazz = get_class(class_id)
    ensure_class_write_access(request, clazz)

    session_ids = [item.id for item in body.sessions]
    sessions_map = (
        ClassSession.objects.select_related("clazz", "clazz__teacher")
        .filter(clazz=clazz)
        .in_bulk(session_ids)
    )
    missing_ids = sorted(session_id for session_id in session_ids if session_id not in sessions_map)
    if missing_ids:
        raise HttpError(404, f"Class sessions with IDs {missing_ids} not found.")

    updated_sessions = []
    for item in body.sessions:
        session = sessions_map[item.id]
        validate_session_times(session, item.start, item.end)

        if item.start is not None:
            session.start = item.start
        if item.end is not None:
            session.end = item.end
        session.save()
        updated_sessions.append(session)

    return [class_session_to_dto(session) for session in updated_sessions]


@router.delete(
    "/class/{class_id}/bulk",
    response={
        200: BulkDeleteClassSessionResultDTO,
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Delete multiple class sessions",
    url_name="bulk_delete_class_sessions",
    auth=is_teacher_auth,
)
@transaction.atomic
def bulk_delete_class_sessions(
    request, class_id: int = Path(...), body: BulkDeleteClassSessionSchema = Body(...)
) -> BulkDeleteClassSessionResultDTO:
    clazz = get_class(class_id)
    ensure_class_write_access(request, clazz)
    sessions = ClassSession.objects.select_related("clazz", "clazz__teacher").filter(
        clazz=clazz, pk__in=body.session_ids
    )
    session_ids = {session.pk for session in sessions}
    missing_ids = sorted(
        session_id for session_id in body.session_ids if session_id not in session_ids
    )
    if missing_ids:
        raise HttpError(404, f"Class sessions with IDs {missing_ids} not found.")
    sessions.delete()
    return BulkDeleteClassSessionResultDTO(deleted_ids=list(session_ids))


@router.get(
    "/{session_id}",
    response={200: ClassSessionDTO, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    summary="Get a class session",
    url_name="get_class_session",
    auth=is_teacher_auth,
)
def get_class_session(request, session_id: int = Path(...)) -> ClassSessionDTO:
    session = get_session(session_id)
    ensure_class_write_access(request, session.clazz)
    return class_session_to_dto(session)


@router.patch(
    "/{session_id}",
    response={
        200: ClassSessionDTO,
        400: ErrorResponse,
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Update a class session",
    url_name="update_class_session",
    auth=is_teacher_auth,
)
def update_class_session(
    request, session_id: int = Path(...), body: UpdateClassSessionSchema = Body(...)
) -> ClassSessionDTO:
    session = get_session(session_id)
    ensure_class_write_access(request, session.clazz)
    validate_session_times(session, body.start, body.end)

    if body.start is not None:
        session.start = body.start
    if body.end is not None:
        session.end = body.end
    session.save()

    return class_session_to_dto(session)


@router.delete(
    "/{session_id}",
    response={200: bool, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    summary="Delete a class session",
    url_name="delete_class_session",
    auth=is_teacher_auth,
)
def delete_class_session(request, session_id: int = Path(...)) -> bool:
    session = get_session(session_id)
    ensure_class_write_access(request, session.clazz)
    session.delete()
    return True


@router.get(
    "/class/{class_id}/presence",
    response={
        200: Dict[int, List[StudentPresenceDTO]],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Get aggregated presence for an entire class",
    url_name="get_class_presence",
    auth=is_teacher_auth,
)
def get_class_presence(request, class_id: int = Path(...)) -> Dict[int, List[StudentPresenceDTO]]:
    clazz = get_class(class_id)
    ensure_class_write_access(request, clazz)
    sessions = clazz.sessions.order_by("start")
    return {int(session.pk): calculate_aggregated_presence(session) for session in sessions}


@router.get(
    "/{session_id}/presence",
    response={
        200: List[StudentPresenceDTO],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Get aggregated presence for a class session",
    url_name="get_class_session_presence",
    auth=is_teacher_auth,
)
def get_class_session_presence(request, session_id: int = Path(...)) -> List[StudentPresenceDTO]:
    session = get_session_and_ensure_access(request, session_id)
    return calculate_aggregated_presence(session)


@router.get(
    "/{session_id}/timespans",
    response={
        200: List[SessionTimespanDTO],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Get timespan aggregation for a class session",
    url_name="get_class_session_timespans",
    auth=is_teacher_auth,
)
def get_class_session_timespans(
    request, session_id: int = Path(...), include_manual: bool = False
) -> List[SessionTimespanDTO]:
    session = get_session_and_ensure_access(request, session_id)
    return calculate_session_timespans(session, include_manual)


@router.get(
    "/{session_id}/presence/{student_id}",
    response={
        200: List[AttendanceRecordDTO],
        401: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Get detailed attendance records for a student in a class session",
    url_name="get_class_session_student_presence",
    auth=is_teacher_auth,
)
def get_class_session_student_presence(
    request, session_id: int = Path(...), student_id: int = Path(...)
) -> List[AttendanceRecordDTO]:
    session = get_session_and_ensure_access(request, session_id)
    records = session.attendance_records.filter(student_id=student_id).order_by("-attendance_time")
    return [attendance_record_to_dto(r) for r in records]
