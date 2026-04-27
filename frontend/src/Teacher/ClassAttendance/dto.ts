import { AttendanceRecordFormat } from '../../Attendance/dto';

export interface StudentPresence {
    id: number;
    login: string;
    first_name: string;
    last_name: string;
    is_present: boolean;
    record_format: AttendanceRecordFormat | null;
}

export interface SessionTimespan {
    time: string;
    count: number;
}

export interface AttendanceRecord {
    id: number;
    student_login: string;
    class_session_id: number;
    attendance_time: string;
    is_present: boolean;
    record_format: AttendanceRecordFormat;
    description: string | null;
    created_at: string;
    updated_at: string;
    created_by_login: string;
}
