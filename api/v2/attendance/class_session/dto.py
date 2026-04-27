from datetime import datetime
from typing import List, Optional
from ninja import Schema
from pydantic import Field
from attendance.models import ClassSession, Attendance
from common.models import Class


class ClassSessionDTO(Schema):
    id: int = Field(..., description="ID of the class session")
    class_id: int = Field(..., description="ID of the related class")
    class_subject: str = Field(..., description="Subject abbreviation of the related class")
    class_code: str = Field(..., description="Code of the related class")
    class_day: Class.Day = Field(..., description="Day of the related class (e.g., PO, UT, ...)")
    class_time: str = Field(..., description="Time of the related class (HH:MM)")
    teacher_id: int = Field(..., description="ID of the teacher for the class")
    start: datetime = Field(..., description="Start time of the class session")
    end: datetime = Field(..., description="End time of the class session")
    created_at: datetime = Field(..., description="Creation time of the class session")
    updated_at: datetime = Field(..., description="Last update time of the class session")


class BulkDeleteClassSessionResultDTO(Schema):
    deleted_ids: List[int] = Field(..., description="IDs of deleted class sessions")


class StudentPresenceDTO(Schema):
    id: int = Field(..., description="ID of the student")
    login: str = Field(..., description="Username/Login of the student")
    first_name: str = Field(..., description="First name of the student")
    last_name: str = Field(..., description="Last name of the student")
    is_present: bool = Field(..., description="Whether the student is marked as present")
    record_format: Optional[Attendance.RecordFormat] = Field(
        None, description="The format of the attendance record that decided the presence"
    )


class SessionTimespanDTO(Schema):
    time: str = Field(..., description="Time of the timespan (HH:MM)")
    count: int = Field(..., description="Count of present students in the timespan")


def class_session_to_dto(session: ClassSession) -> ClassSessionDTO:
    return ClassSessionDTO(
        id=session.id,
        class_id=session.clazz.pk,
        class_subject=session.clazz.subject.abbr,
        class_code=session.clazz.code,
        class_day=session.clazz.day,
        class_time=session.clazz.time.strftime("%H:%M"),
        teacher_id=session.clazz.teacher.pk,
        start=session.start,
        end=session.end,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
