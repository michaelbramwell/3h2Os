// --- Wizard enums ---

export type Sport = "running" | "swimming";

export type ExperienceLevel = "beginner" | "intermediate" | "advanced";
export const ExperienceLevel = {
  BEGINNER: "beginner",
  INTERMEDIATE: "intermediate",
  ADVANCED: "advanced",
} as const;

export type EventType =
  | "none"
  | "5k"
  | "10k"
  | "half_marathon"
  | "marathon"
  | "ultra"
  | "pool_400m"
  | "pool_800m"
  | "pool_1500m"
  | "ow_1km"
  | "ow_2.5km"
  | "ow_5km"
  | "ow_10km";

export const RunningEvents: EventType[] = [
  "none",
  "5k",
  "10k",
  "half_marathon",
  "marathon",
  "ultra",
];

export const SwimmingPoolEvents: EventType[] = [
  "none",
  "pool_400m",
  "pool_800m",
  "pool_1500m",
];

export const SwimmingOWEvents: EventType[] = [
  "ow_1km",
  "ow_2.5km",
  "ow_5km",
  "ow_10km",
];

export const SwimmingEvents: EventType[] = [
  ...SwimmingPoolEvents,
  ...SwimmingOWEvents,
];

export const EventLabels: Record<EventType, string> = {
  none: "No Event (Build Weekly)",
  "5k": "5K",
  "10k": "10K",
  half_marathon: "Half Marathon",
  marathon: "Marathon",
  ultra: "Ultra",
  pool_400m: "400m Pool",
  pool_800m: "800m Pool",
  pool_1500m: "1500m Pool",
  ow_1km: "1km Open Water",
  "ow_2.5km": "2.5km Open Water",
  ow_5km: "5km Open Water",
  ow_10km: "10km Open Water",
};

export type PrimaryGoal =
  | "finish"
  | "pb"
  | "target_time"
  | "consistency"
  | "enjoyment";
export const PrimaryGoal = {
  FINISH: "finish",
  PB: "pb",
  TARGET_TIME: "target_time",
  CONSISTENCY: "consistency",
  ENJOYMENT: "enjoyment",
} as const;

export const PrimaryGoalLabels: Record<PrimaryGoal, string> = {
  finish: "Finish the event",
  pb: "Personal best",
  target_time: "Hit a target time",
  consistency: "Build consistency",
  enjoyment: "Enjoy the journey",
};

export type PainPoint =
  | "cramping"
  | "bonking"
  | "pacing"
  | "injury"
  | "mental_fatigue"
  | "recovery"
  | "speed_final_third"
  | "breathing"
  | "open_water_anxiety"
  | "stroke_efficiency";

export const PainPointLabels: Record<PainPoint, string> = {
  cramping: "Cramping",
  bonking: "Bonking / hitting the wall",
  pacing: "Pacing",
  injury: "Injury prevention",
  mental_fatigue: "Mental fatigue",
  recovery: "Recovery between sessions",
  speed_final_third: "Slowing in the final third",
  breathing: "Breathing technique",
  open_water_anxiety: "Open water anxiety",
  stroke_efficiency: "Stroke efficiency",
};

// --- Helpers ---

export function defaultTaperWeeks(eventType: EventType): number {
    switch (eventType) {
        case '5k':
        case '10k':
            return 1;
        case 'half_marathon':
        case 'marathon':
        case 'ultra':
            return 2;
        default:
            return 1;
    }
}

// --- Wizard step data ---

export interface WizardSportEvent {
  plan_name: string;
  sport: Sport;
  event_type: EventType;
  event_name?: string;
  event_date?: string; // ISO date string
}

export interface WizardAthleteProfile {
  experience_level: ExperienceLevel;
  age: number;
  weight_kg: number;
  events_completed: number;
  preferred_time_of_day?: "AM" | "PM"; // undefined = no preference
  preferred_training_days?: number[]; // Day indices 0=Mon..6=Sun
  preferred_long_run_day?: number; // Day index 0=Mon..6=Sun
  use_calculated_zones: boolean;
  custom_zones?: Record<string, any>;
}

export interface WizardGoalsFocus {
  primary_goal: PrimaryGoal;
  target_time?: string; // e.g. "3:45:00"
  pain_points: PainPoint[];
  weekly_availability: number; // 3-7
  longest_recent_distance_m: number;
}

export interface WizardPlanConfig {
  total_weeks: number;
  taper_weeks?: number; // 1-3, undefined = use template default
  generation_method: "template" | "ai" | "manual" | "manual_weekly";
}

export interface WizardInput {
  sport_event: WizardSportEvent;
  athlete_profile: WizardAthleteProfile;
  goals_focus: WizardGoalsFocus;
  plan_config: WizardPlanConfig;
}

// --- Preview / Response types ---

export interface PhasePreview {
  name: string;
  weeks: number;
  description: string;
}

export interface PlanPreview {
  title: string;
  sport: Sport;
  event_type: EventType;
  total_weeks: number;
  phases: PhasePreview[];
  peak_weekly_volume_m: number;
  weekly_volumes_m: number[];
  sessions_per_week: number;
  zones?: Record<string, any>;
}

export interface ClonePlanRequest {
  new_title: string;
  date_offset_days: number;
}

// --- Wizard step enum for navigation ---

export type WizardStep =
  | "sport_event"
  | "athlete_profile"
  | "goals_focus"
  | "plan_config"
  | "review";

export const WIZARD_STEPS: WizardStep[] = [
  "sport_event",
  "athlete_profile",
  "goals_focus",
  "plan_config",
  "review",
];

export const WizardStepLabels: Record<WizardStep, string> = {
  sport_event: "Sport & Event",
  athlete_profile: "Athlete Profile",
  goals_focus: "Goals & Focus",
  plan_config: "Plan Config",
  review: "Review & Confirm",
};
