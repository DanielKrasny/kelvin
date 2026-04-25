from datetime import datetime
from ninja import Schema
from pydantic import Field
from attendance.models import AttendanceDevice


class AttendanceDeviceDTO(Schema):
    id: int = Field(..., description="ID of the attendance device")
    user_login: str = Field(..., description="Login of the device owner")
    device_name: str = Field(..., description="Name of the device")
    state: AttendanceDevice.DeviceState = Field(..., description="State of the attendance device")
    created_at: datetime = Field(..., description="Creation date of the attendance device")


def attendance_device_to_dto(device: AttendanceDevice) -> AttendanceDeviceDTO:
    return AttendanceDeviceDTO(
        id=device.id,
        user_login=device.user.username,
        device_name=device.device_name,
        state=AttendanceDevice.DeviceState(device.state),
        created_at=device.created_at,
    )
