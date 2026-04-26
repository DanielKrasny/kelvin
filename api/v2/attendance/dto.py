import base64
from datetime import datetime
from ninja import Schema
from pydantic import Field, model_validator, PrivateAttr
from attendance.models import AttendanceToken


class AttendancePublicKeyDTO(Schema):
    public_key: str = Field(..., description="Server's RSA public key in PEM format")


class EncryptedMessageSchema(Schema):
    encrypted_message: str = Field(..., description="Hybrid encrypted message (key.iv.ciphertext)")
    _key: bytes = PrivateAttr()
    _iv: bytes = PrivateAttr()
    _ciphertext: bytes = PrivateAttr()

    @property
    def key(self) -> bytes:
        return self._key

    @property
    def iv(self) -> bytes:
        return self._iv

    @property
    def ciphertext(self) -> bytes:
        return self._ciphertext

    @model_validator(mode="after")
    def parse_encrypted_message(self) -> "EncryptedMessageSchema":
        parts = self.encrypted_message.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid encrypted message format. Expected 'key.iv.ciphertext'.")

        decoded = []
        for name, part in zip(("key", "iv", "ciphertext"), parts):
            try:
                decoded.append(base64.b64decode(part, validate=True))
            except Exception:
                raise ValueError(f"{name} is not valid base64")

        self._key, self._iv, self._ciphertext = decoded
        return self


class EncryptedMessageInnerSchema(Schema):
    data: str = Field(..., description="Original data string that was signed")
    signature: str = Field(..., description="Base64-encoded signature of the data string")
    _signature_bytes: bytes = PrivateAttr()

    @property
    def signature_bytes(self) -> bytes:
        return self._signature_bytes

    @model_validator(mode="after")
    def parse_encrypted_message(self) -> "EncryptedMessageInnerSchema":
        try:
            self._signature_bytes = base64.b64decode(self.signature, validate=True)
            return self
        except Exception:
            raise ValueError("Signature is not valid base64")


class EncryptedMessageDataBaseSchema(Schema):
    user_id: int = Field(..., description="User's ID")


class CreateAttendanceTokenInnerSchema(EncryptedMessageDataBaseSchema):
    length: int = Field(..., description="Length of token's validity in seconds")
    method: AttendanceToken.Method = Field(..., description="Method of attendance recording")
    class_session_id: int = Field(..., description="ID of the class session this token is for")


class AttendanceTokenDTO(Schema):
    id: int = Field(..., description="ID of attendance token")
    token: str = Field(..., description="Attendance token")
    method: AttendanceToken.Method = Field(..., description="Method of attendance token")
    created_at: datetime = Field(..., description="Date of attendance token creation")
    expires_at: datetime = Field(..., description="Date of attendance token expiration")
    class_session_id: int = Field(..., description="ID of the class session this token is for")


def attendance_token_to_dto(token: AttendanceToken) -> AttendanceTokenDTO:
    return AttendanceTokenDTO(
        id=token.pk,
        token=token.token,
        method=AttendanceToken.Method(token.method),
        created_at=token.created_at,
        expires_at=token.expires_at,
        class_session_id=token.class_session_id,
    )
