export interface ClassInfo {
    id: number;
    teacher_username: string;
    timeslot: string;
    time: string;
    code: string;
    subject_abbr: string;
    room: string | null;
}

export interface ClassSession {
    id: number;
    class_id: number;
    class_code: string;
    class_day: string;
    class_time: string;
    start: string;
    end: string;
    created_at: string;
    updated_at: string;
}

export interface CreateClassSession {
    start: string;
    end: string;
}

export interface UpdateClassSession {
    id: number;
    start?: string;
    end?: string;
}
