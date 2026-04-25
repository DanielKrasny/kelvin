export enum DeviceState {
    PENDING = 'pending',
    ACTIVE = 'active',
    REVOKED = 'revoked'
}

export interface AttendanceDevice {
    id: number;
    user_login: string;
    device_name: string;
    state: DeviceState;
    created_at: string;
}

export interface UpdateAttendanceDevice {
    state: DeviceState.ACTIVE | DeviceState.REVOKED;
}

export interface BulkUpdateAttendanceDevice extends UpdateAttendanceDevice {
    device_ids: number[];
    revoke_active_devices: boolean;
}
