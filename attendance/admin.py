from django.contrib import admin
from .models import AttendanceDevice, ClassSession


class AttendanceDeviceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Since public key cannot be added via Web UI, the admin shouldn't create new devices manually
        return False


admin.site.register(AttendanceDevice, AttendanceDeviceAdmin)
admin.site.register(ClassSession)
