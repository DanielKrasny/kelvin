from ninja import Schema
from pydantic import Field, UUID4


class ApiClientDTO(Schema):
    client_id: UUID4 = Field(..., description="Client ID of the API client")
    name: str = Field(..., description="Name of the API client")
    redirect_uri: str | None = Field(None, description="Redirect URI of the API client")
