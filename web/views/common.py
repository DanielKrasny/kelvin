from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest
from django.shortcuts import render
from django.conf import settings
from django.urls import reverse
from common.exceptions import HttpExceptionData

from .student import student_index, ui
from common.utils import is_teacher


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
    return render(request, "web/common/api_token.html", {})


def template_context(request):
    return {
        "is_teacher": is_teacher(request.user),
        "vapid_public_key": getattr(settings, "WEBPUSH_SETTINGS", {}).get("VAPID_PUBLIC_KEY", ""),
        "webpush_save_url": reverse("save_webpush_info"),
        "sentry_url": settings.SENTRY_URL,
    }
