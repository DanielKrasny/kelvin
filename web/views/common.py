from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.utils.crypto import get_random_string
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlparse
from api.models import ApiClient, UserToken
from common.exceptions import HttpExceptionData
from kelvin.settings import API_TOKENS_DEFAULT_CLIENT_ID

from .student import student_index, ui
from common.utils import is_teacher
from api.backends import hash_token


class UnsafeHttpResponseRedirect(HttpResponseRedirect):
    """
    An HTTP response that redirects to a given URL without validating the URL's scheme.
    """

    def __init__(self, redirect_to, *args, **kwargs):
        self.allowed_schemes = [urlparse(str(redirect_to)).scheme]
        super().__init__(redirect_to, *args, **kwargs)


def render_custom_error_page(request: HttpRequest, exception):
    exception = HttpExceptionData.from_exception(exception)
    ctx = dict(
        status_code=exception.status,
        message=exception.message,
    )
    return render(request, "error_page.html", ctx, status=exception.status)


@login_required()
def index(request):
    if is_teacher(request.user):
        return ui(request)
    return student_index(request)


@user_passes_test(is_teacher)
def import_inbus(request):
    return render(request, "web/inbusimport.html", {})


@login_required()
def api_token(request):
    data = {
        "base_url": f"{request.scheme}://{request.META.get('HTTP_HOST', 'localhost:8000')}",
        "doc_token": "YOUR_TOKEN",
    }
    if request.method == "POST":
        token_plaintext = get_random_string(32)
        token_secure = hash_token(token_plaintext)

        try:
            client = ApiClient.objects.filter(client_id=API_TOKENS_DEFAULT_CLIENT_ID).first()
        except ValidationError:
            client = None

        token = UserToken()
        token.user = request.user
        token.client = client
        token.token = token_secure
        token.save()

        if client and client.redirect_uri:
            redirect_uri = client.redirect_uri.format(token_plaintext)
            return UnsafeHttpResponseRedirect(redirect_uri)

        data["token_plaintext"] = token_plaintext
        data["doc_token"] = token_plaintext

    return render(request, "web/common/api_token.html", data)


def template_context(request):
    return {
        "is_teacher": is_teacher(request.user),
        "vapid_public_key": getattr(settings, "WEBPUSH_SETTINGS", {}).get("VAPID_PUBLIC_KEY", ""),
        "webpush_save_url": reverse("save_webpush_info"),
        "sentry_url": settings.SENTRY_URL,
    }
