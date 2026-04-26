import math
from datetime import timedelta
from typing import List, cast, Optional
from django.contrib.auth.models import User
from django.utils import timezone
from attendance.models import Attendance, ClassSession
from .dto import StudentPresenceDTO, SessionTimespanDTO


def convert_to_student_presence_dto(
    student: User, is_present: bool, record_format: Optional[Attendance.RecordFormat]
) -> StudentPresenceDTO:
    return StudentPresenceDTO(
        id=student.pk,
        login=student.username,
        first_name=student.first_name,
        last_name=student.last_name,
        is_present=is_present,
        record_format=record_format,
    )


def calculate_aggregated_presence(session: ClassSession) -> List[StudentPresenceDTO]:
    students = {student.pk: cast(User, student) for student in session.clazz.students.all()}
    attendances = session.attendance_records.select_related("student").order_by("attendance_time")

    for att in attendances:
        if att.student_id not in students:
            students[att.student_id] = att.student

    student_records = {student_id: [] for student_id in students}
    for att in attendances:
        student_records[att.student_id].append(att)

    duration_seconds = (session.end - session.start).total_seconds()
    if duration_seconds <= 0:
        total_segments = 0
    else:
        total_segments = math.ceil(duration_seconds / 600)

    required_segments = int(total_segments * 0.8)

    results: List[StudentPresenceDTO] = []

    for student_id, student in students.items():
        records = student_records[student_id]

        manual_teacher = [
            r for r in records if r.record_format == Attendance.RecordFormat.MANUAL_TEACHER
        ]
        manual_student = [
            r for r in records if r.record_format == Attendance.RecordFormat.MANUAL_STUDENT
        ]
        if manual_teacher or manual_student:
            if manual_teacher:
                latest = manual_teacher[-1]
            else:
                latest = manual_student[-1]
            results.append(
                convert_to_student_presence_dto(
                    student=student,
                    is_present=latest.is_present,
                    record_format=latest.record_format,
                )
            )
            continue

        automatic = [r for r in records if r.record_format == Attendance.RecordFormat.AUTOMATIC]
        if automatic:
            covered_segments = set()
            for r in automatic:
                if r.is_present and session.start <= r.attendance_time <= session.end:
                    delta = (r.attendance_time - session.start).total_seconds()
                    segment_idx = int(delta // 600)
                    covered_segments.add(segment_idx)

            is_present = len(covered_segments) >= required_segments if total_segments > 0 else False
            results.append(
                convert_to_student_presence_dto(
                    student=student,
                    is_present=is_present,
                    record_format=Attendance.RecordFormat.AUTOMATIC,
                )
            )
        else:
            results.append(
                convert_to_student_presence_dto(
                    student=student, is_present=False, record_format=None
                )
            )

    results.sort(key=lambda x: (x.last_name, x.first_name, x.login))
    return results


def calculate_session_timespans(
    session: ClassSession, include_manual: bool
) -> List[SessionTimespanDTO]:
    duration_seconds = (session.end - session.start).total_seconds()
    if duration_seconds <= 0:
        return []

    total_segments = math.ceil(duration_seconds / 600)
    attendances = session.attendance_records.select_related("student").order_by("attendance_time")

    student_manual_present = set()
    segment_presence = [set() for _ in range(total_segments)]

    if include_manual:
        for att in attendances:
            if att.is_present and att.record_format in [
                Attendance.RecordFormat.MANUAL_TEACHER,
                Attendance.RecordFormat.MANUAL_STUDENT,
            ]:
                student_manual_present.add(att.student_id)

    for att in attendances:
        if (
            att.is_present
            and att.record_format == Attendance.RecordFormat.AUTOMATIC
            and session.start <= att.attendance_time <= session.end
        ):
            delta = (att.attendance_time - session.start).total_seconds()
            segment_idx = int(delta // 600)
            if segment_idx < total_segments:
                segment_presence[segment_idx].add(att.student_id)

    results = []
    for i in range(total_segments):
        current_time = session.start + timedelta(minutes=10 * i)
        all_present = segment_presence[i] | student_manual_present
        results.append(
            SessionTimespanDTO(
                time=timezone.localtime(current_time).strftime("%H:%M"), count=len(all_present)
            )
        )

    return results
