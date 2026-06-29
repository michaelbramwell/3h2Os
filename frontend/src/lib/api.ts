import axios from 'axios';
import type { Week, ContextData, Activity, FeatureFlags, UserProfile, ProfileSyncPrefs } from '../types/schema';
import type { WizardInput, PlanPreview, ClonePlanRequest, WizardDefaultsResponse } from '../types/wizard';
import { userManager } from './auth';
import { GARMIN_TOKEN_KEY } from '../hooks/useGarminToken';

/**
 * Extract a human-readable error message from an Axios error response.
 * Handles Pydantic validation arrays, string details, and generic fallback.
 */
export function parseApiError(err: any, fallback = 'An error occurred'): string {
    const detail = err?.response?.data?.detail;
    if (Array.isArray(detail)) {
        return detail.map((e: any) => e?.msg || String(e)).join('; ');
    }
    if (typeof detail === 'string') {
        return detail;
    }
    return err?.message || fallback;
}

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL ||
    (window.location.hostname === '3h2os.com'
      ? 'https://3h2os.com'
      : 'http://localhost:8000'),
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config) => {
    // Always try to get the latest token from the manager directly
    // This handles page refreshes where the user object is in local storage
    const user = await userManager.getUser();
    if (user?.access_token) {
        config.headers.Authorization = `Bearer ${user.access_token}`;
    }
    return config;
});

/**
 * Response interceptor: silently refresh the Garmin OAuth2 token on 401.
 *
 * When a Garmin-authenticated request returns 401 the OAuth2 token has likely
 * expired (~1 hour TTL). We refresh it using the stored OAuth1 token (~1 year
 * TTL) via a server-side token exchange that requires no SSO / credentials.
 * On success the new token is persisted to localStorage and the original
 * request is retried once. On failure the token is cleared so the connect
 * form reappears on next interaction.
 */
let _garminRefreshInFlight: Promise<string> | null = null;

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        const hadGarminToken = !!originalRequest.headers?.['X-Garmin-Token'];

        // Never attempt a refresh for the refresh endpoint itself — doing so would
        // recurse infinitely if that endpoint also returns 401.
        const isRefreshEndpoint = originalRequest.url?.includes('/api/garmin/token/refresh');

        if (
            error.response?.status === 401 &&
            hadGarminToken &&
            !originalRequest._garminRetried &&
            !isRefreshEndpoint
        ) {
            originalRequest._garminRetried = true;
            const currentToken = localStorage.getItem(GARMIN_TOKEN_KEY);
            if (!currentToken) {
                return Promise.reject(error);
            }

            try {
                // Deduplicate concurrent refresh requests (e.g. two syncs firing simultaneously)
                if (!_garminRefreshInFlight) {
                    _garminRefreshInFlight = api
                        .post<{ token: string }>(
                            '/api/garmin/token/refresh',
                            {},
                            { headers: { 'X-Garmin-Token': currentToken } }
                        )
                        .then((res) => res.data.token)
                        .finally(() => {
                            _garminRefreshInFlight = null;
                        });
                }

                const newToken = await _garminRefreshInFlight;

                // Persist refreshed token and notify hooks across the page
                localStorage.setItem(GARMIN_TOKEN_KEY, newToken);
                window.dispatchEvent(new Event('garmin-token-change'));
                originalRequest.headers['X-Garmin-Token'] = newToken;

                return api(originalRequest);
            } catch {
                // Refresh failed — OAuth1 token also expired; force re-login
                localStorage.removeItem(GARMIN_TOKEN_KEY);
                window.dispatchEvent(new Event('garmin-token-change'));
                return Promise.reject(error);
            }
        }

        return Promise.reject(error);
    }
);

export const getPlan = async (): Promise<Week[]> => {
  const response = await api.get<Week[]>('/api/plan.json');
  return response.data;
};

export const getContext = async (): Promise<ContextData> => {
  const response = await api.get<ContextData>('/api/context.json');
  return response.data;
};

export const getActuals = async (): Promise<Activity[]> => {
    const response = await api.get<Activity[]>('/api/actuals.json');
    return response.data;
};

export const getContextMarkdown = async (): Promise<string> => {
    const response = await api.get<{content: string}>('/api/context/markdown');
    return response.data.content;
};

export const createPlan = async (title: string, type: string, weeks: Week[] = [], wizardInput?: WizardInput): Promise<any> => {
  const response = await api.post('/api/plans', { title, type, weeks, ...(wizardInput ? { wizard_input: wizardInput } : {}) });
  return response.data;
};

export const getPlanById = async (id: number): Promise<Week[]> => {
  const response = await api.get<Week[]>(`/api/plans/${id}`);
  return response.data;
};

export const updatePlanById = async (id: number, title: string, type: string, weeks: Week[] = [], wizardInput?: WizardInput): Promise<any> => {
  const response = await api.put(`/api/plans/${id}`, { title, type, weeks, ...(wizardInput ? { wizard_input: wizardInput } : {}) });
  return response.data;
};

export interface PlanMeta {
    id: number;
    title: string;
    type: string;
    is_active: boolean;
    created_at: string;
    wizard_input_json?: string;
}

export const getPlans = async (): Promise<PlanMeta[]> => {
    const response = await api.get<PlanMeta[]>('/api/plans');
    return response.data;
};

export const activatePlan = async (id: number): Promise<any> => {
    const response = await api.put(`/api/plans/${id}/activate`);
    return response.data;
};

export const deletePlan = async (id: number): Promise<any> => {
    const response = await api.delete(`/api/plans/${id}`);
    return response.data;
};

export const updateWeek = async (id: number, data: { status?: string }): Promise<any> => {
    const response = await api.put(`/api/weeks/${id}`, data);
    return response.data;
};

export const updateWorkout = async (id: number, data: { name?: string; description?: string; type?: string; distance_m?: number; timeOfDay?: string }, force: boolean = false): Promise<any> => {
    const response = await api.put(`/api/workouts/${id}?force=${force}`, data);
    return response.data;
};

export const createWorkout = async (data: { date: string; name: string; description?: string; type: string; distance_m: number; timeOfDay: string }, force: boolean = false): Promise<any> => {
    const response = await api.post(`/api/workouts?force=${force}`, data);
    return response.data;
};

export const deleteWorkout = async (id: number): Promise<any> => {
    const response = await api.delete(`/api/workouts/${id}`);
    return response.data;
};

export const getGarminToken = async (email: string, password: string): Promise<string> => {
    const response = await api.post<{token: string}>('/api/garmin/token', { email, password });
    return response.data.token;
};

export const refreshGarminToken = async (token: string): Promise<string> => {
    const response = await api.post<{token: string}>(
        '/api/garmin/token/refresh',
        {},
        { headers: { 'X-Garmin-Token': token } }
    );
    return response.data.token;
};

export const syncActivities = async (days: number = 7): Promise<{ count: number; message: string }> => {
    const token = localStorage.getItem('garmin_token');
    const headers = token ? { 'X-Garmin-Token': token } : {};
    const response = await api.post(`/api/integrations/garmin/sync?days=${days}`, {}, { headers });
    return response.data;
};

// --- Wizard API ---

export const wizardPreview = async (input: WizardInput, planId?: number): Promise<PlanPreview> => {
    const url = planId ? `/api/plans/generate-preview?plan_id=${planId}` : '/api/plans/generate-preview';
    const response = await api.post<PlanPreview>(url, input);
    return response.data;
};

export const wizardCreatePlan = async (input: WizardInput): Promise<{ status: string; message: string; id: number; title: string; type: string }> => {
    const response = await api.post('/api/plans/from-wizard', input);
    return response.data;
};

export const getWizardSettings = async (planId: number): Promise<WizardInput> => {
    const response = await api.get<WizardInput>(`/api/plans/${planId}/wizard-settings`);
    return response.data;
};

export const wizardUpdatePlan = async (planId: number, input: WizardInput): Promise<{ status: string; message: string; id: number; title: string; type: string }> => {
    const response = await api.put(`/api/plans/${planId}/from-wizard`, input);
    return response.data;
};

export const clonePlan = async (planId: number, request: ClonePlanRequest): Promise<{ status: string; message: string; id: number; title: string; type: string }> => {
    const response = await api.post(`/api/plans/${planId}/clone`, request);
    return response.data;
};

export const getWizardDefaults = async (): Promise<WizardDefaultsResponse> => {
    const response = await api.get<WizardDefaultsResponse>('/api/wizard/defaults');
    return response.data;
};

// --- Feature Flags ---

export const getFeatureFlags = async (): Promise<FeatureFlags> => {
    const response = await api.get<{ flags: FeatureFlags }>('/api/flags');
    return response.data.flags;
};


// --- Strava ---

export interface StravaStatus {
    connected: boolean;
    athlete_id: number | null;
    scope: string | null;
}

export const getStravaAuthUrl = async (): Promise<string> => {
    const response = await api.get<{ url: string }>('/api/strava/auth-url');
    return response.data.url;
};

export const getStravaStatus = async (): Promise<StravaStatus> => {
    const response = await api.get<StravaStatus>('/api/strava/status');
    return response.data;
};

export const disconnectStrava = async (): Promise<void> => {
    await api.delete('/api/strava/disconnect');
};

export const exchangeStravaCode = async (code: string, state: string): Promise<void> => {
    await api.post('/api/strava/exchange', { code, state });
};

export const syncStravaActivities = async (days: number = 7): Promise<{ synced: number; days: number }> => {
    const response = await api.post<{ synced: number; days: number }>(
        `/api/integrations/strava/sync?days=${days}`
    );
    return response.data;
};

export const syncBothActivities = async (days: number = 7): Promise<{ strava_synced: number; garmin_enriched: number; days: number }> => {
    const token = localStorage.getItem('garmin_token');
    const headers = token ? { 'X-Garmin-Token': token } : {};
    const response = await api.post<{ strava_synced: number; garmin_enriched: number; days: number }>(
        `/api/integrations/sync?days=${days}`, {}, { headers }
    );
    return response.data;
};

export const createActivityShare = async (activityId: number): Promise<{ token: string; url: string }> => {
    const response = await api.post<{ token: string; url: string }>(`/api/activities/${activityId}/share`);
    return response.data;
};

export const updateActivityName = async (activityId: number, name: string | null): Promise<{ id: number; name: string; custom_name: string | null }> => {
    const response = await api.patch<{ id: number; name: string; custom_name: string | null }>(`/api/activities/${activityId}`, { name });
    return response.data;
};


// --- Profile ---

export const getProfile = async (): Promise<UserProfile> => {
    const response = await api.get<UserProfile>('/api/profile');
    return response.data;
};

export const patchProfile = async (data: Partial<Omit<UserProfile, 'sync_prefs' | 'profile_last_synced_at' | 'birthday'>>): Promise<UserProfile> => {
    const response = await api.patch<UserProfile>('/api/profile', data);
    return response.data;
};

export const patchSyncPrefs = async (source: 'garmin' | 'strava', field: string, enabled: boolean): Promise<ProfileSyncPrefs> => {
    const response = await api.patch<ProfileSyncPrefs>('/api/profile/sync-prefs', { source, field, enabled });
    return response.data;
};

export const syncProfileNow = async (garminToken?: string): Promise<{ synced: boolean; message: string }> => {
    const headers = garminToken ? { 'X-Garmin-Token': garminToken } : {};
    const response = await api.post<{ synced: boolean; message: string }>('/api/profile/sync-now', {}, { headers });
    return response.data;
};


export default api;
