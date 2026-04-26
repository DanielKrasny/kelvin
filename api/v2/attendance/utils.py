from typing import Type, TypeVar, Optional
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import Schema
from ninja.errors import HttpError
from pydantic import ValidationError
from kelvin.settings import ATTENDANCE_PRIVATE_KEY_PATH
from attendance.models import AttendanceToken, AttendanceDevice
from .device.utils import get_active_device
from .dto import (
    AttendanceTokenDTO,
    EncryptedMessageInnerSchema,
    EncryptedMessageSchema,
    EncryptedMessageDataBaseSchema,
)

SchemaType = TypeVar("SchemaType", bound=Schema)
DataSchemaType = TypeVar("DataSchemaType", bound=EncryptedMessageDataBaseSchema)


def validate_json_schema(schema_class: Type[SchemaType], data: str) -> SchemaType:
    try:
        return schema_class.model_validate_json(data)
    except ValidationError:
        raise HttpError(422, "Decrypted schema cannot be parsed.")


def decrypt_attendance_message(message: EncryptedMessageSchema) -> EncryptedMessageInnerSchema:
    try:
        with open(ATTENDANCE_PRIVATE_KEY_PATH, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise Exception()
        aes_key = private_key.decrypt(
            message.key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        aes_gcm = AESGCM(aes_key)
        decrypted_bytes = aes_gcm.decrypt(message.iv, message.ciphertext, None)
    except:
        raise HttpError(500, "Server is unable to decrypt the message.")

    return validate_json_schema(EncryptedMessageInnerSchema, decrypted_bytes.decode())


def verify_attendance_signature(public_key_pem: str, message: EncryptedMessageInnerSchema) -> None:
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise HttpError(500, "User's public key is not an RSA key.")
        public_key.verify(
            message.signature_bytes, message.data.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
    except ValueError:
        raise HttpError(500, "User's public key is invalid.")
    except InvalidSignature:
        raise HttpError(403, "Signature verification failed.")
    except HttpError:
        raise
    except Exception:
        raise HttpError(500, "Server is unable to verify the signature.")


def process_encrypted_attendance_message(
    body: EncryptedMessageSchema,
    schema_class: Type[DataSchemaType],
    user: Optional[User] = None,
) -> DataSchemaType:
    decrypted = decrypt_attendance_message(body)
    data = validate_json_schema(schema_class, decrypted.data)
    message_user = user or get_object_or_404(User, pk=data.user_id)
    device = get_active_device(message_user)
    verify_attendance_signature(device.public_key, decrypted)
    return data
