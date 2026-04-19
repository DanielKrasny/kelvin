from typing import List

from pydantic import UUID4
from ninja import Router, Path
from ninja.errors import HttpError
from ninja.security import django_auth
from api.models import ApiClient
from api.v2.dto import ErrorResponse
from api.v2.security import is_teacher_auth
from .dto import ApiClientDTO

router = Router()


@router.get(
    "/",
    response={200: List[ApiClientDTO], 401: ErrorResponse, 403: ErrorResponse},
    summary="List all API clients",
    url_name="list_api_client",
    auth=is_teacher_auth,
)
def list_api_clients(request) -> List[ApiClientDTO]:
    clients = ApiClient.objects.all()
    return [client.to_dto() for client in clients]


@router.get(
    "/{client_id}",
    response={200: ApiClientDTO, 401: ErrorResponse, 404: ErrorResponse},
    summary="Get API client details by UUID",
    url_name="get_api_client",
    auth=django_auth,
)
def get_api_client(request, client_id: UUID4 = Path(...)) -> ApiClientDTO:
    client = ApiClient.objects.filter(client_id=client_id).first()

    if not client:
        raise HttpError(404, f"API Client with ID '{client_id}' not found.")

    return client.to_dto()
