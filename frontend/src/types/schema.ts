export enum ActivityType {
  RUN = "Run",
  EASY = "Easy",
  LONG = "Long",
  WORKOUT = "Workout",
  RACE = "Race",
  REST = "Rest",
  CROSS = "Cross"
}

export interface Workout {
  id?: number;
  name: string;
  type: ActivityType;
  distance_m: number;
  timeOfDay: string;
  description?: string;
}

export interface Day {
  date: string;
  workouts: Workout[];
}

export interface Week {
  weekStarting: string;
  status: string;
  days: Record<string, Day>;
}

export interface ProjectContext {
  name: string;
  goal: string;
  event: string;
  eventDate: string;
}

export interface WeightRecord {
  date: string;
  weight: number;
}

export interface WeightContext {
  current: number;
  target: number;
  history: WeightRecord[];
}

export interface TrainingZone {
  zone: number;
  lowBoundary_m_s?: number;
  lowBoundary_bpm?: number;
}

export interface FuelingStrategy {
  carbsPerHr: number;
  sodiumPerHr: number;
  preRunCarbs: number;
}

export interface RunnerContext {
  age: number;
  gender: string;
  height_cm: number;
  weight_kg: WeightContext;
  personalBests?: Record<string, string>;
  fueling?: FuelingStrategy;
  trainingZones?: {
      pace: TrainingZone[];
      heartRate: TrainingZone[];
  };
}

export interface ContextData {
  project: ProjectContext;
  runner: RunnerContext;
  status?: {
      lastUpdated: string;
      phase: string;
      nextAction: string;
  };
  philosophy?: {
      crampPrevention: {
          mechanical: string;
          metabolic: string;
          fueling: string;
      };
      weeklyStructure: {
          Wednesday: string;
          Thursday: string;
          Sunday: string;
      };
  };
}

export interface HrZone {
    zoneNumber: number;
    secsInZone: number;
    zoneLow: number;
    zoneHigh: number;
    percentInZone: number;
    avgValue?: number; // Added to match usage in dashboard.js
    zoneLowBoundary?: number; // Fallback for legacy API responses
    zoneHighBoundary?: number; // Fallback for legacy API responses
}

export interface Activity {
    date: string;
    name: string;
    type: string;
    distance_m: number;
    duration_s: number;
    activityId: number;
    average_pace_m_s?: number;
    average_hr?: number;
    max_hr?: number;
    average_power?: number;
    aerobic_te?: number;
    anaerobic_te?: number;
    training_load?: number;
    calories?: number;
    hr_zones?: HrZone[];
    pace_zones?: HrZone[];
    power_zones?: HrZone[];
}
