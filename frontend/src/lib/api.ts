import axios from 'axios';
import type { Week, ContextData, Activity } from '../types/schema';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
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

export const updateWorkout = async (id: number, data: { name?: string; description?: string; type?: string; distance_m?: number; timeOfDay?: string }): Promise<any> => {
    const response = await api.put(`/api/workouts/${id}`, data);
    return response.data;
};

export default api;
