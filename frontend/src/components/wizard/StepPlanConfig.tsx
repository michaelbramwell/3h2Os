import type { WizardPlanConfig, ExperienceLevel, EventType } from '../../types/wizard';
import { defaultTaperWeeks } from '../../types/wizard';
import type { StepErrors } from '../../hooks/useWizard';

interface StepPlanConfigProps {
    data: WizardPlanConfig;
    onChange: (data: Partial<WizardPlanConfig>) => void;
    errors: StepErrors;
    experienceLevel: ExperienceLevel;
    eventType: EventType;
}

const WEEK_OPTIONS = [8, 10, 12, 14, 16, 18, 20];

const TAPER_OPTIONS = [1, 2, 3];

export function StepPlanConfig({ data, onChange, errors, experienceLevel, eventType }: StepPlanConfigProps) {
    const showTaperConfig = experienceLevel !== 'beginner';
    const effectiveTaper = data.taper_weeks ?? defaultTaperWeeks(eventType);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-slate-900 mb-1">Plan Configuration</h2>
                <p className="text-sm text-slate-500">Choose how your plan is generated.</p>
            </div>

            {/* Generation method */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Generation Method</label>
                <div className="grid grid-cols-1 gap-3">
                    <button
                        type="button"
                        onClick={() => onChange({ generation_method: 'template' })}
                        className={`
                            p-4 rounded-lg border-2 text-left transition-all
                            ${data.generation_method === 'template'
                                ? 'border-blue-600 bg-blue-50'
                                : 'border-slate-200 bg-white hover:border-slate-300'}
                        `}
                    >
                        <p className="text-sm font-semibold text-slate-900">Template-based</p>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Generates a periodised plan from proven training templates.
                            Uses progressive overload, step-back recovery, and proper taper.
                        </p>
                    </button>
                    <button
                        type="button"
                        onClick={() => onChange({ generation_method: 'manual' })}
                        className={`
                            p-4 rounded-lg border-2 text-left transition-all
                            ${data.generation_method === 'manual'
                                ? 'border-blue-600 bg-blue-50'
                                : 'border-slate-200 bg-white hover:border-slate-300'}
                        `}
                    >
                        <p className="text-sm font-semibold text-slate-900">Manual (Fixed Length)</p>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Set your plan length and build it week by week.
                            Optionally start from a template as a base.
                        </p>
                    </button>
                    <button
                        type="button"
                        disabled
                        className="p-4 rounded-lg border-2 border-slate-100 bg-slate-50 text-left opacity-60 cursor-not-allowed"
                    >
                        <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold text-slate-500">AI-assisted</p>
                            <span className="text-[10px] px-1.5 py-0.5 bg-slate-200 text-slate-500 rounded font-medium">Coming Soon</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">
                            AI-generated plan personalised to your exact profile and history.
                        </p>
                    </button>
                </div>
            </div>

            {/* Plan length configs */}
            {data.generation_method !== 'manual_weekly' && (
                <>
                    {/* Plan length */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Plan Length (weeks)
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {WEEK_OPTIONS.map(weeks => (
                                <button
                                    key={weeks}
                                    type="button"
                                    onClick={() => onChange({ total_weeks: weeks })}
                                    className={`
                                        px-4 py-2 rounded-lg border text-sm font-medium transition-all
                                        ${data.total_weeks === weeks
                                            ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                                    `}
                                >
                                    {weeks}
                                </button>
                            ))}
                        </div>
                        <p className="mt-1.5 text-xs text-slate-400">
                            {data.total_weeks < 12
                                ? 'Shorter plan -- good for shorter events or experienced athletes.'
                                : data.total_weeks <= 16
                                  ? 'Standard training block -- recommended for most athletes.'
                                  : 'Extended plan -- allows for a longer base-building phase.'}
                        </p>
                    </div>

                    {/* Custom week input */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                            Or enter a custom length
                        </label>
                        <input
                            type="number"
                            min={6}
                            max={30}
                            value={data.total_weeks}
                            onChange={e => {
                                const val = parseInt(e.target.value);
                                if (!isNaN(val)) {
                                    onChange({ total_weeks: val });
                                }
                            }}
                            className={`w-24 p-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                errors.total_weeks ? 'border-red-400' : 'border-slate-300'
                            }`}
                        />
                        <span className="ml-2 text-sm text-slate-500">weeks (6-30)</span>
                        {errors.total_weeks && (
                            <p className="mt-1 text-xs text-red-500">{errors.total_weeks}</p>
                        )}
                    </div>

                    {/* Taper length (intermediate/advanced only) */}
                    {showTaperConfig && (
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Taper Length
                            </label>
                            <div className="flex gap-3">
                                {TAPER_OPTIONS.map(weeks => (
                                    <button
                                        key={weeks}
                                        type="button"
                                        onClick={() => onChange({ taper_weeks: weeks })}
                                        className={`
                                            px-4 py-2 rounded-lg border text-sm font-medium transition-all
                                            ${effectiveTaper === weeks
                                                ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                                        `}
                                    >
                                        {weeks} {weeks === 1 ? 'week' : 'weeks'}
                                    </button>
                                ))}
                            </div>
                            <p className="mt-1.5 text-xs text-slate-400">
                                The taper phase reduces training volume before race day to ensure you arrive fresh.
                                {data.taper_weeks == null && ` Default for ${eventType === 'half_marathon' ? 'half marathon' : eventType}: ${defaultTaperWeeks(eventType)} weeks.`}
                            </p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
