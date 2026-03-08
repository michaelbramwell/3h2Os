import { useQuery } from '@tanstack/react-query';
import { useAuth } from 'react-oidc-context';
import { getStravaStatus } from '../lib/api';
import type { StravaStatus } from '../lib/api';

export interface UseStravaStatusResult {
    connected: boolean;
    athleteId: number | null;
    scope: string | null;
    isLoading: boolean;
}

const DEFAULT_STATUS: UseStravaStatusResult = {
    connected: false,
    athleteId: null,
    scope: null,
    isLoading: false,
};

/**
 * Returns Strava connection status for the current user.
 * Falls back to disconnected if the request fails or the user is not authenticated.
 */
export function useStravaStatus(): UseStravaStatusResult {
    const auth = useAuth();

    const { data, isLoading } = useQuery<StravaStatus>({
        queryKey: ['stravaStatus'],
        queryFn: getStravaStatus,
        enabled: auth.isAuthenticated,
        staleTime: 5 * 60 * 1000,
    });

    if (!data) {
        return { ...DEFAULT_STATUS, isLoading };
    }

    return {
        connected: data.connected,
        athleteId: data.athlete_id ?? null,
        scope: data.scope ?? null,
        isLoading,
    };
}
