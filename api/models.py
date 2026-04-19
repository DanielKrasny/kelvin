import uuid
from django.db import models
from django.conf import settings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.v2.api.client.dto import ApiClientDTO
    from api.v2.api.token.dto import UserTokenDTO


class ApiClient(models.Model):
    client_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    redirect_uri = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.name

    def to_dto(self) -> "ApiClientDTO":
        from api.v2.api.client.dto import ApiClientDTO

        return ApiClientDTO(
            client_id=self.client_id, name=self.name, redirect_uri=self.redirect_uri
        )


class UserToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.TextField()
    client = models.ForeignKey(ApiClient, null=True, on_delete=models.CASCADE)
    # Keep existing records without creation date
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def to_dto(self) -> "UserTokenDTO":
        from api.v2.api.token.dto import UserTokenDTO

        return UserTokenDTO(
            id=self.id,
            client=self.client.to_dto() if self.client else None,
            created_at=self.created_at,
        )
