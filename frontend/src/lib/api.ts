import axios from 'axios';
import type { Week, ContextData, Activity } from '../types/schema';
import { userManager } from './auth';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
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

export default api;
