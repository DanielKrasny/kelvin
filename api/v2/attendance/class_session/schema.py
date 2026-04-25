from datetime import datetime
from typing import List, Optional, Set
from ninja import Schema
from pydantic import Field, model_validator


class CreateClassSessionSchema(Schema):
    start: datetime = Field(..., description="Start time of the class session")
    end: datetime = Field(..., description="End time of the class session")

    @model_validator(mode="after")
    def validate_times(self):
        if self.end <= self.start:
            raise ValueError("End time must be after start time.")
        return self


class UpdateClassSessionSchema(Schema):
    start: Optional[datetime] = Field(None, description="Start time of the class session")
    end: Optional[datetime] = Field(None, description="End time of the class session")

    @model_validator(mode="after")
    def validate_present_fields(self):
        if self.start is None and self.end is None:
            raise ValueError("At least one field must be provided for update.")
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("End time must be after start time.")
        return self


class BulkCreateClassSessionSchema(Schema):
    sessions: List[CreateClassSessionSchema] = Field(
        ..., description="List of class sessions to create"
    )


class BulkUpdateClassSessionItemSchema(UpdateClassSessionSchema):
    id: int = Field(..., description="ID of the class session to update")


class BulkUpdateClassSessionSchema(Schema):
    sessions: List[BulkUpdateClassSessionItemSchema] = Field(
        ..., description="List of class sessions to update"
    )


class BulkDeleteClassSessionSchema(Schema):
    session_ids: Set[int] = Field(..., description="IDs of class sessions to delete")
