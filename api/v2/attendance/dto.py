from ninja import Schema
from pydantic import Field


class AttendancePublicKeyDTO(Schema):
    public_key: str = Field(..., description="Server's RSA public key in PEM format")
