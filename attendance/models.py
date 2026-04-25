from django.db import models
from django.conf import settings
from django.utils import timezone
from common.models import Class


class AttendanceDevice(models.Model):
    class DeviceState(models.TextChoices):
        PENDING = "pending"
        ACTIVE = "active"
        REVOKED = "revoked"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    device_name = models.CharField(max_length=100)
    public_key = models.TextField(editable=False)
    state = models.CharField(
        choices=DeviceState.choices, default=DeviceState.PENDING, max_length=10
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(state="active"),
                name="unique_active_device_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(state="pending"),
                name="unique_pending_device_per_user",
            ),
        ]

    def __str__(self):
        return f"#{self.pk} {self.user.username} {self.device_name}"

    def notification_str(self):
        return self.device_name


class ClassSession(models.Model):
    clazz = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="sessions")
    start = models.DateTimeField()
    end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "class sessions"
        constraints = [
            models.CheckConstraint(
                check=models.Q(end__gt=models.F("start")), name="end_after_start"
            ),
        ]

    def __str__(self):
        return f"{self.clazz} @ {timezone.localtime(self.start):%Y-%m-%d %H:%M}"


class AttendanceToken(models.Model):
    class Method(models.TextChoices):
        QR_CODE = "qr", "QR Code"
        BLE = "ble", "Bluetooth Low Energy"

    class_session = models.ForeignKey(
        ClassSession, on_delete=models.CASCADE, related_name="attendance_tokens"
    )
    token = models.TextField()
    method = models.CharField(max_length=10, choices=Method.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attendance_tokens",
        help_text="User who created this token",
    )
    created_by_device = models.ForeignKey(
        AttendanceDevice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attendance_tokens",
        help_text="Attendance device used to create this token",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(expires_at__gt=models.F("created_at")),
                name="expires_after_creation",
            ),
        ]


class Attendance(models.Model):
    class RecordFormat(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic (Device-based)"
        MANUAL_STUDENT = "manual_student", "Manual (Student-initiated)"
        MANUAL_TEACHER = "manual_teacher", "Manual (Teacher-initiated)"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records"
    )
    class_session = models.ForeignKey(
        ClassSession, on_delete=models.CASCADE, related_name="attendance_records"
    )
    attendance_time = models.DateTimeField(
        help_text="The time when the student's attendance was recorded"
    )
    is_present = models.BooleanField(
        default=True, help_text="Whether the student is marked as present in the class"
    )
    record_format = models.CharField(
        max_length=20,
        choices=RecordFormat.choices,
        help_text="How the attendance record was created",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes about this attendance record (e.g. why was the student marked as not present)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attendance_records",
        help_text="User who created this record",
    )
    created_by_device = models.ForeignKey(
        AttendanceDevice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attendance_records",
        help_text="Attendance device used to authorize creation of this record",
    )

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.get_full_name()} - {self.class_session} - {status} @ {self.attendance_time.strftime('%H:%M')}"

    class Meta:
        verbose_name_plural = "attendance records"
        ordering = ["class_session", "student", "attendance_time"]
        indexes = [
            models.Index(fields=["class_session", "student", "attendance_time"]),
            models.Index(fields=["student", "attendance_time"]),
            models.Index(fields=["class_session", "attendance_time"]),
        ]
