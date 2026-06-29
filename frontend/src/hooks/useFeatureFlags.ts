import { useQuery } from '@tanstack/react-query';
import { useAuth } from 'react-oidc-context';
import { getFeatureFlags } from '../lib/api';
import type { FeatureFlags } from '../types/schema';

const DEFAULT_FLAGS: FeatureFlags = {
    isSwimmingEnabled: false,
    isGarminEnabled: false,
    isAiEnabled: false,
};

/**
 * Returns resolved feature flags for the current user.
 * Falls back to all-disabled defaults if the request fails or the user is not
 * yet authenticated.
 */
export function useFeatureFlags(): FeatureFlags {
    const auth = useAuth();

    const { data } = useQuery<FeatureFlags>({
        queryKey: ['featureFlags'],
        queryFn: getFeatureFlags,
        enabled: auth.isAuthenticated,
        // Flags rarely change; 5-minute stale time is fine
        staleTime: 5 * 60 * 1000,
    });

    return { ...DEFAULT_FLAGS, ...data };
}
