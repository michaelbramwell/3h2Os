import { useState, useCallback, useMemo } from 'react';
import type {
    WizardStep,
    WizardSportEvent,
    WizardAthleteProfile,
    WizardGoalsFocus,
    WizardPlanConfig,
    WizardInput,
    PlanPreview,
    Sport,
} from '../types/wizard';
import { WIZARD_STEPS, defaultTaperWeeks } from '../types/wizard';
import { wizardPreview, wizardCreatePlan, wizardUpdatePlan } from '../lib/api';

export type StepErrors = Record<string, string>;

export interface UseWizardOptions {
    /** When set, the wizard operates in edit mode for this plan. */
    planId?: number;
    /** Initial data to pre-populate the wizard (used in edit mode). */
    initialData?: WizardInput;
}

interface UseWizardReturn {
    // Mode
    isEditMode: boolean;
    editPlanId: number | null;

    // Navigation
    currentStep: WizardStep;
    stepIndex: number;
    isFirstStep: boolean;
    isLastStep: boolean;
    goNext: () => void;
    goBack: () => void;
    goToStep: (step: WizardStep) => void;

    // Step data
    sportEvent: WizardSportEvent;
    setSportEvent: (data: Partial<WizardSportEvent>) => void;
    athleteProfile: WizardAthleteProfile;
    setAthleteProfile: (data: Partial<WizardAthleteProfile>) => void;
    goalsFocus: WizardGoalsFocus;
    setGoalsFocus: (data: Partial<WizardGoalsFocus>) => void;
    planConfig: WizardPlanConfig;
    setPlanConfig: (data: Partial<WizardPlanConfig>) => void;

    // Validation
    canProceed: boolean;
    stepErrors: StepErrors;

    // Preview
    preview: PlanPreview | null;
    previewLoading: boolean;
    previewError: string | null;
    loadPreview: () => Promise<void>;

    // Submit
    submitting: boolean;
    submitError: string | null;
    submitPlan: () => Promise<{ id: number; title: string } | null>;

    // Assembled input
    wizardInput: WizardInput;

    // Reset
    reset: () => void;
}

const DEFAULT_SPORT_EVENT: WizardSportEvent = {
    plan_name: '',
    sport: 'running' as Sport,
    event_type: 'marathon',
};

const DEFAULT_ATHLETE_PROFILE: WizardAthleteProfile = {
    experience_level: 'intermediate',
    age: 35,
    weight_kg: 75,
    events_completed: 0,
    use_calculated_zones: true,
};

const DEFAULT_GOALS_FOCUS: WizardGoalsFocus = {
    primary_goal: 'finish',
    pain_points: [],
    weekly_availability: 5,
    longest_recent_distance_m: 0,
};

const DEFAULT_PLAN_CONFIG: WizardPlanConfig = {
    total_weeks: 14,
    generation_method: 'template',
};

export function useWizard(options?: UseWizardOptions): UseWizardReturn {
    const isEditMode = !!(options?.planId);
    const editPlanId = options?.planId ?? null;
    const init = options?.initialData;

    // Step navigation
    const [stepIndex, setStepIndex] = useState(0);
    const currentStep = WIZARD_STEPS[stepIndex];
    const isFirstStep = stepIndex === 0;
    const isLastStep = stepIndex === WIZARD_STEPS.length - 1;

    // Step data -- seed from initialData when in edit mode
    const [sportEvent, setSportEventState] = useState<WizardSportEvent>(
        init?.sport_event ?? DEFAULT_SPORT_EVENT
    );
    const [athleteProfile, setAthleteProfileState] = useState<WizardAthleteProfile>(
        init?.athlete_profile ?? DEFAULT_ATHLETE_PROFILE
    );
    const [goalsFocus, setGoalsFocusState] = useState<WizardGoalsFocus>(
        init?.goals_focus ?? DEFAULT_GOALS_FOCUS
    );
    const [planConfig, setPlanConfigState] = useState<WizardPlanConfig>(
        init?.plan_config ?? DEFAULT_PLAN_CONFIG
    );

    // Preview state
    const [preview, setPreview] = useState<PlanPreview | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewError, setPreviewError] = useState<string | null>(null);

    // Submit state
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);

    // Partial update helpers -- each clears the cached preview so the review
    // step re-fetches when the user navigates back to it.
    const setSportEvent = useCallback((data: Partial<WizardSportEvent>) => {
        setSportEventState(prev => ({ ...prev, ...data }));
        setPreview(null);
        setPreviewError(null);
    }, []);

    const setAthleteProfile = useCallback((data: Partial<WizardAthleteProfile>) => {
        setAthleteProfileState(prev => ({ ...prev, ...data }));
        setPreview(null);
        setPreviewError(null);
    }, []);

    const setGoalsFocus = useCallback((data: Partial<WizardGoalsFocus>) => {
        setGoalsFocusState(prev => ({ ...prev, ...data }));
        setPreview(null);
        setPreviewError(null);
    }, []);

    const setPlanConfig = useCallback((data: Partial<WizardPlanConfig>) => {
        setPlanConfigState(prev => ({ ...prev, ...data }));
        setPreview(null);
        setPreviewError(null);
    }, []);

    // Assembled wizard input -- resolve effective taper weeks so the backend
    // always receives an explicit value matching what the UI highlights.
    const wizardInput: WizardInput = useMemo(() => ({
        sport_event: sportEvent,
        athlete_profile: athleteProfile,
        goals_focus: goalsFocus,
        plan_config: {
            ...planConfig,
            taper_weeks: planConfig.taper_weeks ?? defaultTaperWeeks(sportEvent.event_type),
        },
    }), [sportEvent, athleteProfile, goalsFocus, planConfig]);

    // Per-step validation
    const stepErrors: StepErrors = useMemo(() => {
        const errors: StepErrors = {};

        // Step 1: sport_event
        if (!sportEvent.plan_name?.trim()) {
            errors.plan_name = 'Plan name is required';
        }
        if (!sportEvent.sport || !['running', 'swimming'].includes(sportEvent.sport)) {
            errors.sport = 'Select a sport';
        }
        if (!sportEvent.event_type) {
            errors.event_type = 'Select an event distance';
        }

        // Step 2: athlete_profile
        if (!athleteProfile.age || athleteProfile.age < 10 || athleteProfile.age > 100) {
            errors.age = 'Age must be between 10 and 100';
        }
        if (!['beginner', 'intermediate', 'advanced'].includes(athleteProfile.experience_level)) {
            errors.experience_level = 'Select an experience level';
        }

        // Step 3: goals_focus
        if (!goalsFocus.weekly_availability || goalsFocus.weekly_availability < 1 || goalsFocus.weekly_availability > 7) {
            errors.weekly_availability = 'Select training days per week (1-7)';
        }

        if (sportEvent.event_type !== 'none' && planConfig.generation_method !== 'manual_weekly') {
            if (!planConfig.total_weeks || planConfig.total_weeks < 6 || planConfig.total_weeks > 30) {
                errors.total_weeks = 'Plan length must be between 6 and 30 weeks';
            }
        }

        return errors;
    }, [sportEvent, athleteProfile, goalsFocus, planConfig]);

    const canProceed = useMemo(() => {
        const stepFieldMap: Record<WizardStep, string[]> = {
            sport_event: ['plan_name', 'sport', 'event_type'],
            athlete_profile: ['age', 'experience_level'],
            goals_focus: ['weekly_availability'],
            plan_config: (sportEvent.event_type === 'none') ? [] : ['total_weeks'],
            review: [], // No gating on review
        };
        const fields = stepFieldMap[currentStep] || [];
        return fields.every(f => !(f in stepErrors));
    }, [currentStep, stepErrors]);

    // Navigation
    const goNext = useCallback(() => {
        setStepIndex(prev => Math.min(prev + 1, WIZARD_STEPS.length - 1));
    }, []);

    const goBack = useCallback(() => {
        setStepIndex(prev => Math.max(prev - 1, 0));
    }, []);

    const goToStep = useCallback((step: WizardStep) => {
        const idx = WIZARD_STEPS.indexOf(step);
        if (idx >= 0) setStepIndex(idx);
    }, []);

    // Preview
    const loadPreview = useCallback(async () => {
        setPreviewLoading(true);
        setPreviewError(null);
        try {
            const result = await wizardPreview(wizardInput);
            setPreview(result);
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'Failed to generate preview';
            setPreviewError(msg);
        } finally {
            setPreviewLoading(false);
        }
    }, [wizardInput]);

    // Submit -- create or update depending on mode
    const submitPlan = useCallback(async () => {
        setSubmitting(true);
        setSubmitError(null);
        try {
            if (isEditMode && editPlanId) {
                const result = await wizardUpdatePlan(editPlanId, wizardInput);
                return { id: result.id, title: result.title };
            } else {
                const result = await wizardCreatePlan(wizardInput);
                return { id: result.id, title: result.title };
            }
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'Failed to save plan';
            setSubmitError(msg);
            return null;
        } finally {
            setSubmitting(false);
        }
    }, [wizardInput, isEditMode, editPlanId]);

    // Reset
    const reset = useCallback(() => {
        setStepIndex(0);
        setSportEventState(DEFAULT_SPORT_EVENT);
        setAthleteProfileState(DEFAULT_ATHLETE_PROFILE);
        setGoalsFocusState(DEFAULT_GOALS_FOCUS);
        setPlanConfigState(DEFAULT_PLAN_CONFIG);
        setPreview(null);
        setPreviewLoading(false);
        setPreviewError(null);
        setSubmitting(false);
        setSubmitError(null);
    }, []);

    return {
        isEditMode,
        editPlanId,
        currentStep,
        stepIndex,
        isFirstStep,
        isLastStep,
        goNext,
        goBack,
        goToStep,
        sportEvent,
        setSportEvent,
        athleteProfile,
        setAthleteProfile,
        goalsFocus,
        setGoalsFocus,
        planConfig,
        setPlanConfig,
        canProceed,
        stepErrors,
        preview,
        previewLoading,
        previewError,
        loadPreview,
        submitting,
        submitError,
        submitPlan,
        wizardInput,
        reset,
    };
}
