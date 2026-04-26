import os
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    NoEncryption,
    PrivateFormat,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.management import BaseCommand, CommandError
from kelvin.settings import (
    ATTENDANCE_PUBLIC_KEY_PATH,
    ATTENDANCE_PRIVATE_KEY_PATH,
)


class Command(BaseCommand):
    help = "Create public and private keys for attendance encryption"

    @staticmethod
    def _validate_path(path: str):
        if path.strip() == "" or os.path.isdir(path):
            raise CommandError(
                "Invalid path. Check settings.py for ATTENDANCE_PRIVATE_KEY_PATH and ATTENDANCE_PUBLIC_KEY_PATH."
            )

    def handle(self, *args, **options):
        self._validate_path(ATTENDANCE_PRIVATE_KEY_PATH)
        self._validate_path(ATTENDANCE_PUBLIC_KEY_PATH)
        private_exists = os.path.exists(ATTENDANCE_PRIVATE_KEY_PATH)
        public_exists = os.path.exists(ATTENDANCE_PUBLIC_KEY_PATH)

        if private_exists or public_exists:
            confirm = input(f"A key already exists. Overwrite? [y/N]: ").strip().lower()
            if confirm != "y":
                raise CommandError("Operation cancelled.")

        private = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public = private.public_key()

        try:
            with open(ATTENDANCE_PRIVATE_KEY_PATH, "wb") as f:
                f.write(
                    private.private_bytes(
                        Encoding.PEM,
                        PrivateFormat.TraditionalOpenSSL,
                        NoEncryption(),
                    )
                )

            with open(ATTENDANCE_PUBLIC_KEY_PATH, "wb") as f:
                f.write(
                    public.public_bytes(
                        Encoding.PEM,
                        PublicFormat.SubjectPublicKeyInfo,
                    )
                )
        except OSError as e:
            raise CommandError(f"File write failed: {e}")

        self.stdout.write(
            self.style.SUCCESS("Successfully created a key pair for attendance encryption.")
        )
