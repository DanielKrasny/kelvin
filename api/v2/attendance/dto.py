import base64
from datetime import datetime
from typing import List, Dict, Optional
from ninja import Schema
from pydantic import Field, model_validator, PrivateAttr
from attendance.models import AttendanceToken, Attendance


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


class EncryptedMessageReceivedSchema(EncryptedMessageSchema):
    received_at: datetime = Field(..., description="Date of received attendance recording")


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


class CreateAttendanceRecordStudentInnerSchema(EncryptedMessageDataBaseSchema):
    class_session_id: int = Field(..., description="ID of the class session this token is for")
    token: str = Field(..., description="Token of attendance recording")
    created_at: datetime = Field(..., description="Date of attendance recording creation")


class CreateAttendanceRecordsTeacherInnerSchema(EncryptedMessageDataBaseSchema):
    class_session_id: int = Field(..., description="ID of the class session")
    records: List[EncryptedMessageReceivedSchema] = Field(
        ..., description="Encrypted records of student attendance with time of receipt"
    )


class CreateAttendanceRecordTeacherManualSchema(Schema):
    student_login: str = Field(..., description="Student login")
    is_present: bool = Field(
        ..., description="Whether student was marked as present in the class session"
    )


class CreateAttendanceRecordsTeacherManualSchema(Schema):
    class_session_id: int = Field(..., description="ID of the class session")
    records: List[CreateAttendanceRecordTeacherManualSchema] = Field(
        ..., description="Records of student attendance to be created manually by teacher"
    )


class AttendanceTokenDTO(Schema):
    id: int = Field(..., description="ID of attendance token")
    token: str = Field(..., description="Attendance token")
    method: AttendanceToken.Method = Field(..., description="Method of attendance token")
    created_at: datetime = Field(..., description="Date of attendance token creation")
    expires_at: datetime = Field(..., description="Date of attendance token expiration")
    class_session_id: int = Field(..., description="ID of the class session this token is for")


class AttendanceRecordDTO(Schema):
    id: int = Field(..., description="ID of attendance record")
    student_login: str = Field(..., description="Student login")
    class_session_id: int = Field(
        ..., description="ID of the class session for this attendance record"
    )
    attendance_time: datetime = Field(..., description="Time of attendance recording")
    is_present: bool = Field(
        ..., description="Whether the student was marked as present in the class session"
    )
    record_format: Attendance.RecordFormat = Field(..., description="Attendance record format")
    description: Optional[str] = Field(None, description="Optional attendance record description")
    created_at: datetime = Field(..., description="Date of attendance record creation")
    updated_at: datetime = Field(..., description="Date of attendance record last update")
    created_by_login: Optional[str] = Field(
        None, description="Login of user who created this attendance record"
    )


class CreateAttendanceRecordsTeacherResponseSchema(Schema):
    success: List[AttendanceRecordDTO] = Field(..., description="Successfully created records")
    failed: Dict[int, str] = Field(..., description="Failed records with error messages")


def attendance_token_to_dto(token: AttendanceToken) -> AttendanceTokenDTO:
    return AttendanceTokenDTO(
        id=token.pk,
        token=token.token,
        method=AttendanceToken.Method(token.method),
        created_at=token.created_at,
        expires_at=token.expires_at,
        class_session_id=token.class_session_id,
    )


def attendance_record_to_dto(record: Attendance) -> AttendanceRecordDTO:
    return AttendanceRecordDTO(
        id=record.pk,
        student_login=record.student.username,
        class_session_id=record.class_session_id,
        attendance_time=record.attendance_time,
        is_present=record.is_present,
        record_format=Attendance.RecordFormat(record.record_format),
        description=record.description,
        created_at=record.created_at,
        updated_at=record.updated_at,
        created_by_login=record.created_by.username if record.created_by else None,
    )
