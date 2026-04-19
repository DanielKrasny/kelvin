from typing import List
from urllib.parse import urlparse

# from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, Http404
from django.utils.crypto import get_random_string
from ninja import Router
from ninja.errors import AuthorizationError, HttpError
from ninja.pagination import paginate
from ninja.security import django_auth
from kelvin.settings import API_TOKENS_DEFAULT_CLIENT_ID
from web.views.common import UnsafeHttpResponseRedirect
from api.backends import hash_token
from api.models import ApiClient, UserToken
from api.v2.dto import ErrorResponse
from .dto import UserTokenDTO, CreateUserTokenDTO
from .schema import CreateUserTokenSchema


router = Router()


@router.get(
    "/",
    response={200: List[UserTokenDTO], 401: ErrorResponse},
    summary="List all API tokens for the logged in user",
    url_name="list_api_token",
    auth=django_auth,
)
@paginate
def list_api_token(request) -> List[UserTokenDTO]:
    tokens = request.user.usertoken_set.all()
    return [token.to_dto() for token in tokens]


@router.get(
    "/{token_id}",
    response={200: UserTokenDTO, 401: ErrorResponse, 404: ErrorResponse},
    summary="Get details of a specific API token by ID",
    url_name="get_api_token",
    auth=django_auth,
)
def get_api_token(request, token_id: int) -> UserTokenDTO:
    token = request.user.usertoken_set.filter(id=token_id).first()
    if not token:
        raise HttpError(
            404, f"API token with ID '{token_id}' does not exist for the logged in user."
        )
    return token.to_dto()


@router.post(
    "/",
    response={200: CreateUserTokenDTO, 302: None, 401: ErrorResponse, 403: ErrorResponse},
    summary="Create a new API token for the logged in user",
    description="The endpoint performs a redirect in case client ID has a redirect URI set.",
    url_name="create_api_token",
    auth=django_auth,
)
def create_api_token(request, body: CreateUserTokenSchema) -> CreateUserTokenDTO:
    if hasattr(request.user, "current_token") and request.user.current_token:
        raise AuthorizationError(message="API tokens can be created only in the Web UI.")
    token_plaintext = get_random_string(32)
    token_secure = hash_token(token_plaintext)

    client_id = body.client_id if body.client_id else API_TOKENS_DEFAULT_CLIENT_ID
    try:
        client = ApiClient.objects.filter(client_id=client_id).first()
    except ValidationError:
        client = None

    token = UserToken()
    token.user = request.user
    token.token = token_secure
    token.client = client
    token.save()

    if token.client is not None and token.client.redirect_uri:
        redirect_uri = token.client.redirect_uri.format(token_plaintext)
        # Supposing the user is going into an external application, the session is no longer needed
        # logout(request)
        return UnsafeHttpResponseRedirect(redirect_uri)

    return CreateUserTokenDTO(
        id=token.id,
        token=token_plaintext,
        client=token.client.to_dto() if token.client else None,
        created_at=token.created_at,
    )


@router.delete(
    "/{token_id}",
    response={200: bool, 401: ErrorResponse, 404: ErrorResponse},
    summary="Delete a specific API token for the logged in user",
    url_name="delete_api_token",
    auth=django_auth,
)
def delete_api_token(request, token_id: int) -> bool:
    token = request.user.usertoken_set.filter(id=token_id).first()
    if not token:
        raise HttpError(
            404, f"API token with ID '{token_id}' does not exist for the logged in user."
        )
    token.delete()
    return True
