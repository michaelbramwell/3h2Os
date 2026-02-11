import { createPortal } from 'react-dom';
import { useNavigate } from '@tanstack/react-router';
import { X } from 'lucide-react';
import { useWizard } from '../../hooks/useWizard';
import { WizardProgress } from './WizardProgress';
import { StepSportEvent } from './StepSportEvent';
import { StepAthleteProfile } from './StepAthleteProfile';
import { StepGoalsFocus } from './StepGoalsFocus';
import { StepPlanConfig } from './StepPlanConfig';
import { StepReview } from './StepReview';
import { toast } from 'sonner';

interface PlanWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onPlanCreated?: (planId: number) => void;
}

export function PlanWizard({ isOpen, onClose, onPlanCreated }: PlanWizardProps) {
    const wizard = useWizard();
    const navigate = useNavigate();

    if (!isOpen) return null;

    const handleClose = () => {
        wizard.reset();
        onClose();
    };

    const handleSubmit = async () => {
        const result = await wizard.submitPlan();
        if (result) {
            toast.success(`Plan "${result.title}" created successfully.`);
            onPlanCreated?.(result.id);
            handleClose();
        }
    };

    const isManualMode = wizard.planConfig.generation_method === 'manual';
    const isOnPlanConfigStep = wizard.currentStep === 'plan_config';

    const handleNext = () => {
        if (isOnPlanConfigStep && isManualMode) {
            // Store wizard state for the manual builder page
            sessionStorage.setItem('wizardInput', JSON.stringify(wizard.wizardInput));
            handleClose();
            navigate({ to: '/plans/build' });
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
                    />
                );
            case 'athlete_profile':
                return (
                    <StepAthleteProfile
                        data={wizard.athleteProfile}
                        onChange={wizard.setAthleteProfile}
                        sport={wizard.sportEvent.sport}
                        errors={wizard.stepErrors}
                    />
                );
            case 'goals_focus':
                return (
                    <StepGoalsFocus
                        data={wizard.goalsFocus}
                        onChange={wizard.setGoalsFocus}
                        sport={wizard.sportEvent.sport}
                        errors={wizard.stepErrors}
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
                    />
                );
            default:
                return null;
        }
    };

    const content = (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-100">
                    <h1 className="text-base font-semibold text-slate-900">Create Training Plan</h1>
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
                            Create Plan
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={handleNext}
                            disabled={!wizard.canProceed}
                            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isOnPlanConfigStep && isManualMode ? 'Open Builder' : 'Next'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );

    return createPortal(content, document.body);
}
