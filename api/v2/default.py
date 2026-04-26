from ninja import Router

from common.models import Semester, Class, Room
from django.shortcuts import get_object_or_404
from .dto import SemesterResponse, HealthCheckResponse, ErrorResponse, ClassResponse
from .security import is_teacher_auth

router = Router()


@router.get(
    "/class/{class_id}",
    response={200: ClassResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    summary="Get class detail",
    auth=is_teacher_auth,
)
def get_class(request, class_id: int):
    clazz = get_object_or_404(
        Class.objects.select_related("teacher", "subject", "room"), pk=class_id
    )
    return ClassResponse(
        id=clazz.pk,
        teacher_username=clazz.teacher.username,
        timeslot=clazz.timeslot,
        time=clazz.time.strftime("%H:%M"),
        code=clazz.code,
        subject_abbr=clazz.subject.abbr,
        room=clazz.room.code if clazz.room else None,
    )


@router.get(
    "/semesters",
    response={200: list[SemesterResponse], 401: ErrorResponse, 403: ErrorResponse},
    summary="Get list of all semesters",
    description="Retrieve a list of all semesters.",
    auth=is_teacher_auth,
)
def semesters(request):
    semesters = Semester.objects.all()
    semesters_response = [
        SemesterResponse(
            pk=semester.pk,
            year=semester.year,
            winter=semester.winter,
            inbus_semester_id=semester.inbus_semester_id,
        )
        for semester in semesters
    ]
    return semesters_response


@router.get(
    "/health",
    response={200: HealthCheckResponse},
    summary="Health check endpoint",
    description="Check if the API is running and healthy.",
    tags=["CI/CD"],
)
def health_check(request):
    return {"status": "OK"}
