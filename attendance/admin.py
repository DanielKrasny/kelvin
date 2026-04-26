from django.contrib import admin
from .models import AttendanceDevice, ClassSession, Attendance


class AttendanceDeviceAdmin(admin.ModelAdmin):
    list_display = ("device_name", "user", "state", "created_at")
    search_fields = ("user__username",)
    search_help_text = "Search by login of the device owner"

    def has_add_permission(self, request):
        # Since public key cannot be added via Web UI, the admin shouldn't create new devices manually
        return False


class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "class_session", "attendance_time", "is_present", "record_format")
    search_fields = ("student__username",)
    search_help_text = "Search by login of the student"


admin.site.register(AttendanceDevice, AttendanceDeviceAdmin)
admin.site.register(ClassSession)
admin.site.register(Attendance, AttendanceRecordAdmin)
