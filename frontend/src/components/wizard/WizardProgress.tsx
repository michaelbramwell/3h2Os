import { WIZARD_STEPS, WizardStepLabels } from '../../types/wizard';
import type { WizardStep } from '../../types/wizard';

interface WizardProgressProps {
    currentStep: WizardStep;
    onStepClick: (step: WizardStep) => void;
}

export function WizardProgress({ currentStep, onStepClick }: WizardProgressProps) {
    const currentIndex = WIZARD_STEPS.indexOf(currentStep);

    return (
        <div className="flex items-center justify-between px-2">
            {WIZARD_STEPS.map((step, index) => {
                const isCompleted = index < currentIndex;
                const isCurrent = index === currentIndex;
                const isClickable = index <= currentIndex;

                return (
                    <div key={step} className="flex items-center flex-1 last:flex-none">
                        <button
                            type="button"
                            onClick={() => isClickable && onStepClick(step)}
                            disabled={!isClickable}
                            className={`
                                flex items-center gap-2 text-sm font-medium transition-colors
                                ${isCurrent ? 'text-blue-600' : ''}
                                ${isCompleted ? 'text-slate-700 hover:text-blue-600 cursor-pointer' : ''}
                                ${!isClickable && !isCurrent ? 'text-slate-400 cursor-default' : ''}
                            `}
                        >
                            <span
                                className={`
                                    w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
                                    transition-colors
                                    ${isCurrent ? 'bg-blue-600 text-white' : ''}
                                    ${isCompleted ? 'bg-blue-100 text-blue-700' : ''}
                                    ${!isClickable && !isCurrent ? 'bg-slate-100 text-slate-400' : ''}
                                `}
                            >
                                {isCompleted ? (
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                    </svg>
                                ) : (
                                    index + 1
                                )}
                            </span>
                            <span className="hidden sm:inline">{WizardStepLabels[step]}</span>
                        </button>
                        {index < WIZARD_STEPS.length - 1 && (
                            <div
                                className={`
                                    flex-1 h-0.5 mx-3
                                    ${index < currentIndex ? 'bg-blue-300' : 'bg-slate-200'}
                                `}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
