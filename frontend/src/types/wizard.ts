// --- Wizard enums ---

export type Sport = "running";
export const Sport = {
  RUNNING: "running",
} as const;

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
  | "ultra";

export const RunningEvents: EventType[] = [
  "none",
  "5k",
  "10k",
  "half_marathon",
  "marathon",
  "ultra",
];

export const EventLabels: Record<EventType, string> = {
  none: "No Event (Build Weekly)",
  "5k": "5K",
  "10k": "10K",
  half_marathon: "Half Marathon",
  marathon: "Marathon",
  ultra: "Ultra",
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
  | "speed_final_third";

export const PainPointLabels: Record<PainPoint, string> = {
  cramping: "Cramping",
  bonking: "Bonking / hitting the wall",
  pacing: "Pacing",
  injury: "Injury prevention",
  mental_fatigue: "Mental fatigue",
  recovery: "Recovery between sessions",
  speed_final_third: "Slowing in the final third",
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

/**
 * generation_method for new plans. The 'ai' value is intentionally absent --
 * the backend rejects it with 422 and the UI no longer offers it. Legacy plans
 * with generation_method='ai' may still be read from the database; use
 * {@link LegacyGenerationMethod} when deserializing historical data.
 */
export type GenerationMethod = "template" | "manual" | "manual_weekly";

/**
 * Read-only union that includes the legacy 'ai' value. Use this only when
 * deserializing persisted plans; never use it for new plan input.
 */
export type LegacyGenerationMethod = GenerationMethod | "ai";

export interface WizardPlanConfig {
  total_weeks: number;
  taper_weeks?: number; // 1-3, undefined = use template default
  generation_method: GenerationMethod;
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

// --- Wizard defaults (from GET /api/wizard/defaults) ---

/** Partial athlete profile fields that can be pre-filled from RunnerProfile. */
export interface WizardAthleteProfileDefaults {
    age?: number;
    weight_kg?: number;
    experience_level?: string;
    use_calculated_zones?: boolean;
    custom_zones?: Record<string, any>;
    events_completed?: number;
}

/** Partial goals/focus fields that can be pre-filled from RunnerProfile. */
export interface WizardGoalsFocusDefaults {
    weekly_availability?: number;
    longest_recent_distance_m?: number;
    pain_points?: string[];
}

/** Response from GET /api/wizard/defaults */
export interface WizardDefaultsResponse {
    athlete_profile: WizardAthleteProfileDefaults;
    goals_focus: WizardGoalsFocusDefaults;
}
