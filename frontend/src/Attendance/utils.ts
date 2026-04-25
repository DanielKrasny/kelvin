import { DeviceState } from './dto';

export function getStateBadgeClass(state: DeviceState) {
    switch (state) {
        case DeviceState.ACTIVE:
            return 'bg-success';
        case DeviceState.PENDING:
            return 'bg-warning text-dark';
        case DeviceState.REVOKED:
            return 'bg-danger';
        default:
            return 'bg-secondary';
    }
}

export type StateFormatMode = 'action' | 'passive';

/**
 * Formats DeviceState into a human-readable string.
 * @param state The state to format
 * @param mode 'action' (e.g. Activate), 'passive' (e.g. Activated)
 */
export function formatDeviceState(state: DeviceState, mode: StateFormatMode): string {
    const mapping: Record<DeviceState, Record<StateFormatMode, string>> = {
        [DeviceState.ACTIVE]: {
            action: 'activate',
            passive: 'activated'
        },
        [DeviceState.PENDING]: {
            action: 'mark as pending',
            passive: 'pending'
        },
        [DeviceState.REVOKED]: {
            action: 'revoke',
            passive: 'revoked'
        }
    };

    return mapping[state]?.[mode] || state;
}

export function debounce<T extends (...args: unknown[]) => void>(
    fn: T,
    delay: number
): (...args: Parameters<T>) => void {
    let timeoutId: ReturnType<typeof setTimeout>;
    return (...args: Parameters<T>) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
}
