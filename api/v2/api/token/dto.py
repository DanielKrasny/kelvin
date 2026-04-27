from ninja import Schema
from pydantic import Field
from datetime import datetime
from api.v2.api.client.dto import ApiClientDTO


class UserTokenDTO(Schema):
    id: int = Field(..., description="ID of the user token")
    client: ApiClientDTO | None = Field(None, description="API Client of the user token")
    created_at: datetime | None = Field(None, description="Creation date of the user token")


class CreateUserTokenDTO(UserTokenDTO):
    token: str = Field(..., description="Token of the user token")
    redirect_url: str | None = Field(None, description="Redirect URL if the client has one")
