from ninja import Router

from common.models import Semester
from .dto import SemesterResponse, HealthCheckResponse, ErrorResponse
from .security import is_teacher_auth

router = Router()


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
