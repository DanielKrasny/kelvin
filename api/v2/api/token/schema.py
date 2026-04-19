from ninja import Schema
from pydantic import UUID4, Field


class CreateUserTokenSchema(Schema):
    client_id: UUID4 | None = Field(None, description="Client UUID to use for the user token")
