import axios from 'axios';
import type { Week, ContextData, Activity } from '../types/schema';
import type { WizardInput, PlanPreview, ClonePlanRequest } from '../types/wizard';
import { userManager } from './auth';

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

export const createPlan = async (title: string, type: string, weeks: Week[] = []): Promise<any> => {
  const response = await api.post('/api/plans', { title, type, weeks });
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

export const syncActivities = async (days: number = 7): Promise<{ count: number; message: string }> => {
    const token = localStorage.getItem('garmin_token');
    const headers = token ? { 'X-Garmin-Token': token } : {};
    const response = await api.post(`/api/integrations/garmin/sync?days=${days}`, {}, { headers });
    return response.data;
};

// --- Wizard API ---

export const wizardPreview = async (input: WizardInput): Promise<PlanPreview> => {
    const response = await api.post<PlanPreview>('/api/plans/generate-preview', input);
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


export default api;
