from ninja import Router
from ninja.errors import HttpError
from ninja.security import django_auth
from api.v2.dto import ErrorResponse
from .dto import AttendancePublicKeyDTO
from kelvin.settings import ATTENDANCE_PUBLIC_KEY_PATH

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
