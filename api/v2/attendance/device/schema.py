from ninja import Schema
from pydantic import Field
from typing import Set
from typing_extensions import Literal
from attendance.models import AttendanceDevice


class CreateAttendanceDeviceSchema(Schema):
    device_name: str = Field(..., description="Name of the attendance device")
    public_key: str = Field(..., description="RSA Public key in PEM format")


class UpdateAttendanceDeviceSchema(Schema):
    state: Literal[AttendanceDevice.DeviceState.ACTIVE, AttendanceDevice.DeviceState.REVOKED] = (
        Field(..., description="State to set on the attendance device")
    )


class BulkUpdateAttendanceDeviceSchema(UpdateAttendanceDeviceSchema):
    device_ids: Set[int] = Field(..., description="IDs of attendance devices to update")
    revoke_active_devices: bool = Field(
        False,
        description="Whether active devices for affected users should be revoked before change",
    )
