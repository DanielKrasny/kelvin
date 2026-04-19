from django.contrib import admin
from .models import ApiClient, UserToken


class ApiClientAdmin(admin.ModelAdmin):
    list_display = ("client_id", "name", "redirect_uri")


class UserTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "created_at")
    search_fields = ("user__username",)
    search_help_text = "Search by username of the token owner"


admin.site.register(ApiClient, ApiClientAdmin)
admin.site.register(UserToken, UserTokenAdmin)
