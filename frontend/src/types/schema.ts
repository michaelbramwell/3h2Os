export type ActivityType =
  | "Run"
  | "Trail"
  | "Cycling"
  | "Swimming"
  | "Cross"
  | "Rest"
  | "Other";

export const ActivityType = {
  RUN: "Run",
  TRAIL: "Trail",
  CYCLING: "Cycling",
  SWIMMING: "Swimming",
  CROSS: "Cross",
  REST: "Rest",
  OTHER: "Other",
} as const;

export type WorkoutFormat =
  | "Easy"
  | "Long"
  | "Tempo"
  | "Threshold"
  | "Intervals"
  | "Race"
  | "Recovery"
  | "Technique"
  | "Hills"
  | "Fartlek"
  | "Progression"
  | "Steady"
  | "WarmUp"
  | "CoolDown"
  | "TimeTrial";

export const WorkoutFormat = {
  EASY: "Easy",
  LONG: "Long",
  TEMPO: "Tempo",
  THRESHOLD: "Threshold",
  INTERVALS: "Intervals",
  RACE: "Race",
  RECOVERY: "Recovery",
  TECHNIQUE: "Technique",
  HILLS: "Hills",
  FARTLEK: "Fartlek",
  PROGRESSION: "Progression",
  STEADY: "Steady",
  WARMUP: "WarmUp",
  COOLDOWN: "CoolDown",
  TIME_TRIAL: "TimeTrial",
} as const;

export interface Workout {
  id?: number;
  name: string;
  type: ActivityType;
  format?: WorkoutFormat;
  distance_m: number;
  timeOfDay: string;
  description?: string;
}

export interface Day {
  date: string;
  workouts: Workout[];
}

export interface Week {
  id?: number;
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
  personalBests?: Record<string, string>;
  fueling?: FuelingStrategy;
  trainingZones?: {
      pace: TrainingZone[];
      heartRate: TrainingZone[];
      swimPace?: TrainingZone[];
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
    splits?: Record<string, any>[];
    
    /**
     * Marker field indicating that this activity represents an actual,
     * completed workout (as opposed to a planned or template activity).
     *
     * This is optional so that any existing `Activity` objects remain
     * assignable to `ActualActivity` without requiring additional fields.
     */
    actual?: true;
}
