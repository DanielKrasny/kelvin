from typing import Optional
from ninja import Schema
from pydantic import Field


class SemesterResponse(Schema):
    pk: int = Field(..., description="Primary key of the semester")
    year: int = Field(..., description="Year of the semester")
    winter: bool = Field(..., description="Is it a winter semester?")
    inbus_semester_id: int = Field(..., description="ID of the INBUS semester")


class ClassResponse(Schema):
    id: int = Field(..., description="Primary key of the class")
    teacher_username: str = Field(..., description="Teacher username")
    timeslot: str = Field(
        ...,
        description="Timeslot of the class (in format Day of week + HHMM, e.g. PO0800 is Monday 08:00)",
    )
    time: str = Field(..., description="Time of the class (HH:MM)")
    code: str = Field(..., description="Code of the class")
    subject_abbr: str = Field(..., description="Abbreviation of the subject")
    room: Optional[str] = Field(None, description="Room code of the class")


class HealthCheckResponse(Schema):
    status: str = Field(..., description="Health status of Kelvin")


class ErrorResponse(Schema):
    detail: str = Field(..., description="Error message")
