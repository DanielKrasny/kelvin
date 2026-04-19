import uuid
from django.db import models
from django.conf import settings


class ApiClient(models.Model):
    client_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    redirect_uri = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.name


class UserToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.TextField()
    client = models.ForeignKey(ApiClient, null=True, on_delete=models.CASCADE)
    # Keep existing records without creation date
    created_at = models.DateTimeField(auto_now_add=True, null=True)
