import { createPortal } from 'react-dom';
import { useNavigate } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { useWizard } from '../../hooks/useWizard';
import { useFeatureFlags } from '../../hooks/useFeatureFlags';
import { useStravaStatus } from '../../hooks/useStravaStatus';
import { useGarminToken } from '../../hooks/useGarminToken';
import { WizardProgress } from './WizardProgress';
import { StepSportEvent } from './StepSportEvent';
import { StepAthleteProfile } from './StepAthleteProfile';
import { StepGoalsFocus } from './StepGoalsFocus';
import { StepPlanConfig } from './StepPlanConfig';
import { StepReview } from './StepReview';
import { toast } from 'sonner';
import type { WizardInput, WizardDefaultsResponse } from '../../types/wizard';
import type { IntegrationSources } from './IntegrationBanner';
import { getWizardDefaults } from '../../lib/api';

interface PlanWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onPlanCreated?: (planId: number) => void;
    /** When set, the wizard opens in edit mode for this plan ID. */
    editPlanId?: number;
    /** Pre-populated wizard data for edit mode. */
    editData?: WizardInput;
}

// ---------------------------------------------------------------------------
// Inner component — mounts only once profileDefaults is settled so that
// useWizard's useState is initialised with the correct defaults on first mount.
// ---------------------------------------------------------------------------

interface PlanWizardContentProps {
    onClose: () => void;
    onPlanCreated?: (planId: number) => void;
    editPlanId?: number;
    editData?: WizardInput;
    profileDefaults?: WizardDefaultsResponse;
    /** Whether we are in create mode (used to show the integration banner). */
    isCreateMode: boolean;
}

function PlanWizardContent({
    onClose,
    onPlanCreated,
    editPlanId,
    editData,
    profileDefaults,
    isCreateMode,
}: PlanWizardContentProps) {
    const wizard = useWizard(
        editPlanId && editData
            ? { planId: editPlanId, initialData: editData }
            : { profileDefaults }
    );
    const navigate = useNavigate();
    const flags = useFeatureFlags();
    const swimmingEnabled = flags.isSwimmingEnabled;
    const aiEnabled = flags.isAiEnabled;
    const { connected: stravaConnected } = useStravaStatus();
    const { hasToken: garminConnected } = useGarminToken();

    // Integration banner context — only relevant in create mode
    const integrationSources: IntegrationSources | undefined = isCreateMode
        ? {
            hasStrava: stravaConnected,
            hasGarmin: garminConnected && flags.isGarminEnabled,
            hasDefaults: profileDefaults !== undefined,
          }
        : undefined;

    const handleClose = () => {
        wizard.reset();
        onClose();
    };

    const handleSubmit = async () => {
        const result = await wizard.submitPlan();
        if (result) {
            toast.success(
                wizard.isEditMode
                    ? `Plan "${result.title}" updated successfully.`
                    : `Plan "${result.title}" created successfully.`
            );
            onPlanCreated?.(result.id);
            handleClose();
        }
    };

    const isManualMode = wizard.planConfig.generation_method === 'manual' || wizard.planConfig.generation_method === 'manual_weekly' || wizard.sportEvent.event_type === 'none';
    const isOnPlanConfigStep = wizard.currentStep === 'plan_config';
    const isWeekByWeek = wizard.sportEvent.event_type === 'none';

    const handleNext = () => {
        if (isWeekByWeek && wizard.currentStep === 'sport_event') {
            // For week-by-week, we hijack the config so the builder knows what to do
            const updatedInput = {
                ...wizard.wizardInput,
                plan_config: {
                    ...wizard.wizardInput.plan_config,
                    generation_method: 'manual_weekly' as const
                }
            };
            sessionStorage.setItem('wizardInput', JSON.stringify(updatedInput));
            handleClose();
            navigate({ to: '/plans/build', search: { planId: undefined } });
            return;
        }

        if (isOnPlanConfigStep && isManualMode) {
            // Store wizard state for the manual builder page
            sessionStorage.setItem('wizardInput', JSON.stringify(wizard.wizardInput));
            handleClose();
            navigate({ to: '/plans/build', search: { planId: undefined } });
            return;
        }
        wizard.goNext();
    };

    const renderStep = () => {
        switch (wizard.currentStep) {
            case 'sport_event':
                return (
                    <StepSportEvent
                        data={wizard.sportEvent}
                        onChange={wizard.setSportEvent}
                        errors={wizard.stepErrors}
                        swimmingEnabled={swimmingEnabled}
                    />
                );
            case 'athlete_profile':
                return (
                    <StepAthleteProfile
                        data={wizard.athleteProfile}
                        onChange={wizard.setAthleteProfile}
                        sport={wizard.sportEvent.sport}
                        errors={wizard.stepErrors}
                        swimmingEnabled={swimmingEnabled}
                        integrationSources={integrationSources}
                    />
                );
            case 'goals_focus':
                return (
                    <StepGoalsFocus
                        data={wizard.goalsFocus}
                        onChange={wizard.setGoalsFocus}
                        sport={wizard.sportEvent.sport}
                        errors={wizard.stepErrors}
                        integrationSources={integrationSources}
                    />
                );
            case 'plan_config':
                return (
                    <StepPlanConfig
                        data={wizard.planConfig}
                        onChange={wizard.setPlanConfig}
                        errors={wizard.stepErrors}
                        experienceLevel={wizard.athleteProfile.experience_level}
                        eventType={wizard.sportEvent.event_type}
                        eventDate={wizard.sportEvent.event_date}
                        isAiEnabled={aiEnabled}
                    />
                );
            case 'review':
                return (
                    <StepReview
                        preview={wizard.preview}
                        previewLoading={wizard.previewLoading}
                        previewError={wizard.previewError}
                        onLoadPreview={wizard.loadPreview}
                        submitting={wizard.submitting}
                        submitError={wizard.submitError}
                        onSubmit={handleSubmit}
                        isEditMode={wizard.isEditMode}
                    />
                );
            default:
                return null;
        }
    };

    const submitLabel = wizard.isEditMode ? 'Update Plan' : 'Create Plan';

    return (
        <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100">
                <h1 className="text-base font-semibold text-slate-900">
                    {wizard.isEditMode ? 'Edit Training Plan' : 'Create Training Plan'}
                </h1>
                <button
                    type="button"
                    onClick={handleClose}
                    className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Progress bar */}
            <div className="px-4 py-3 border-b border-slate-50 bg-slate-50/50">
                <WizardProgress
                    currentStep={wizard.currentStep}
                    onStepClick={wizard.goToStep}
                />
            </div>

            {/* Step content */}
            <div className="flex-1 overflow-y-auto p-6">
                {renderStep()}
            </div>

            {/* Footer */}
            <div className="p-4 bg-slate-50 flex justify-between border-t border-slate-100">
                <button
                    type="button"
                    onClick={wizard.isFirstStep ? handleClose : wizard.goBack}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
                >
                    {wizard.isFirstStep ? 'Cancel' : 'Back'}
                </button>

                {wizard.isLastStep ? (
                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={wizard.submitting || wizard.previewLoading}
                        className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                    >
                        {wizard.submitting && (
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        )}
                        {submitLabel}
                    </button>
                ) : (
                    <button
                        type="button"
                        onClick={handleNext}
                        disabled={!wizard.canProceed}
                        className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {(isOnPlanConfigStep && isManualMode) || (wizard.currentStep === 'sport_event' && isWeekByWeek) ? 'Open Builder' : 'Next'}
                    </button>
                )}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Outer shell — handles the query and defers mounting the inner component
// until defaults are settled (success or error) so useState is seeded correctly.
// ---------------------------------------------------------------------------

export function PlanWizard({ isOpen, onClose, onPlanCreated, editPlanId, editData }: PlanWizardProps) {
    const isCreateMode = !(editPlanId && editData);

    // Fetch profile-sourced defaults only in create mode.
    const { data: profileDefaults, isLoading: defaultsLoading } = useQuery({
        queryKey: ['wizardDefaults'],
        queryFn: getWizardDefaults,
        enabled: isOpen && isCreateMode,
        staleTime: 5 * 60 * 1000, // 5 min
    });

    if (!isOpen) return null;

    // In create mode, wait for the defaults fetch to settle before mounting the
    // inner component so useWizard's useState is seeded with the right values.
    // Show a brief loading indicator while waiting (typically < 200 ms on LAN).
    // In edit mode we don't need defaults, so render immediately.
    const showLoader = isCreateMode && defaultsLoading;

    const content = (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            {showLoader ? (
                <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
                <PlanWizardContent
                    key={isCreateMode ? 'create' : `edit-${editPlanId}`}
                    onClose={onClose}
                    onPlanCreated={onPlanCreated}
                    editPlanId={editPlanId}
                    editData={editData}
                    profileDefaults={profileDefaults}
                    isCreateMode={isCreateMode}
                />
            )}
        </div>
    );

    return createPortal(content, document.body);
}
