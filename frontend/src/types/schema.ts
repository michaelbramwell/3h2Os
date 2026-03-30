export type ActivityType =
  | "Run"
  | "Trail"
  | "Cycling"
  | "Swimming"
  | "Cross"
  | "Rest"
  | "Race"
  | "Other";

export const ActivityType = {
  RUN: "Run",
  TRAIL: "Trail",
  CYCLING: "Cycling",
  SWIMMING: "Swimming",
  CROSS: "Cross",
  REST: "Rest",
  OTHER: "Other",
  RACE: "Race",
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
  highBoundary_bpm?: number;
  description?: string;
}

export interface RunnerContext {
  age: number;
  gender: string;
  height_cm: number;
  personalBests?: Record<string, string>;
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
    id?: number | null;              // ActualActivity database PK; present on actuals, absent on planned
    date: string;
    name: string;
    custom_name?: string | null;     // User-set title; survives sync overwrites
    type: string;  // Backend returns lowercase ('running', 'swimming'); use isType() for comparisons
    distance_m: number;
    duration_s: number;
    activityId?: number | null;      // Garmin activity ID; null for Strava-only records
    stravaActivityId?: number | null; // Strava activity ID; null for Garmin-only records
    source?: string;                  // 'garmin' | 'strava' | 'manual'
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
     */
    actual?: true;
}

// Profile / Settings

export interface GarminSyncPrefs {
  weight: boolean;
  height: boolean;
  resting_hr: boolean;
  vo2max: boolean;
  lactate_threshold: boolean;
}

export interface StravaSyncPrefs {
  weight: boolean;
  ftp: boolean;
  hr_zones: boolean;
}

export interface ProfileSyncPrefs {
  garmin: GarminSyncPrefs;
  strava: StravaSyncPrefs;
}

export interface UserProfile {
  // Bio
  age: number | null;
  gender: string | null;
  height_cm: number | null;
  birthday: string | null;
  weight_kg: number | null;

  // Performance
  ftp: number | null;
  resting_hr: number | null;
  vo2max: number | null;
  lactate_threshold_hr: number | null;
  lactate_threshold_pace: number | null;

  // Training preferences
  experience_level: string | null;
  weekly_availability: number | null;

  // Sync metadata
  sync_prefs: ProfileSyncPrefs;
  profile_last_synced_at: string | null;
}

// Feature Flags

export type UserType = 'standard' | 'alpha' | 'beta' | 'premium';

export interface FeatureFlags {
    isSwimmingEnabled: boolean;
    [key: string]: boolean;
}
