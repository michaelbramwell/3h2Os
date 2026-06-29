import { useEffect } from 'react';
import type { WizardPlanConfig, ExperienceLevel, EventType } from '../../types/wizard';
import { defaultTaperWeeks } from '../../types/wizard';
import type { StepErrors } from '../../hooks/useWizard';

interface StepPlanConfigProps {
    data: WizardPlanConfig;
    onChange: (data: Partial<WizardPlanConfig>) => void;
    errors: StepErrors;
    experienceLevel: ExperienceLevel;
    eventType: EventType;
    eventDate?: string | null;
    isAiEnabled?: boolean;
}

const WEEK_OPTIONS = [8, 10, 12, 14, 16, 18, 20];

const TAPER_OPTIONS = [1, 2, 3];

// Uses browser local time which is expected to be AWST (UTC+8).
// The backend validator also uses AWST so both sides agree.
function weeksUntilEvent(eventDate: string | null | undefined): number | null {
    if (!eventDate) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const event = new Date(eventDate + 'T00:00:00');
    const diffMs = event.getTime() - today.getTime();
    return Math.floor(diffMs / (7 * 24 * 60 * 60 * 1000));
}

export function StepPlanConfig({ data, onChange, errors, experienceLevel, eventType, eventDate, isAiEnabled }: StepPlanConfigProps) {
    const showTaperConfig = experienceLevel !== 'beginner';
    const effectiveTaper = data.taper_weeks ?? defaultTaperWeeks(eventType);
    const weeksAvailable = weeksUntilEvent(eventDate);
    const maxWeeks = weeksAvailable != null ? weeksAvailable : 30;

    // Auto-clamp taper_weeks if total_weeks shrinks to the point it becomes invalid.
    // Rule: taper must leave at least 4 non-taper, non-race weeks.
    const MIN_TRAINING_WEEKS = 4;
    const maxTaper = Math.max(1, data.total_weeks - MIN_TRAINING_WEEKS - 1); // -1 for race week

    useEffect(() => {
        if (data.taper_weeks != null && data.taper_weeks > maxTaper) {
            onChange({ taper_weeks: Math.min(data.taper_weeks, maxTaper) });
        }
    }, [maxTaper, data.taper_weeks, onChange]);

    useEffect(() => {
        if (weeksAvailable != null && data.total_weeks > weeksAvailable) {
            onChange({ total_weeks: Math.max(weeksAvailable, 6) });
        }
    }, [weeksAvailable, data.total_weeks, onChange]);

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
                        disabled={!isAiEnabled}
                        className={`p-4 rounded-lg border-2 text-left transition-all ${
                            isAiEnabled
                                ? 'border-slate-200 bg-white hover:border-slate-300'
                                : 'border-slate-100 bg-slate-50 opacity-60 cursor-not-allowed'
                        }`}
                    >
                        <div className="flex items-center gap-2">
                            <p className={`text-sm font-semibold ${isAiEnabled ? 'text-slate-900' : 'text-slate-500'}`}>
                                AI-assisted
                            </p>
                            {!isAiEnabled && (
                                <span className="text-[10px] px-1.5 py-0.5 bg-slate-200 text-slate-500 rounded font-medium">Coming Soon</span>
                            )}
                        </div>
                        <p className={`text-xs mt-0.5 ${isAiEnabled ? 'text-slate-500' : 'text-slate-400'}`}>
                            {isAiEnabled
                                ? 'AI-generated plan personalised to your exact profile and history.'
                                : 'AI-generated plan personalised to your exact profile and history.'}
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
                            {weeksAvailable != null && (
                                <span className="ml-2 font-normal text-slate-400">
                                    ({weeksAvailable} weeks until event)
                                </span>
                            )}
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {WEEK_OPTIONS.map(weeks => {
                                const disabled = weeks > maxWeeks;
                                return (
                                    <button
                                        key={weeks}
                                        type="button"
                                        disabled={disabled}
                                        onClick={() => onChange({ total_weeks: weeks })}
                                        className={`
                                            px-4 py-2 rounded-lg border text-sm font-medium transition-all
                                            ${disabled
                                                ? 'border-slate-100 bg-slate-50 text-slate-300 cursor-not-allowed'
                                                : data.total_weeks === weeks
                                                    ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                                        `}
                                    >
                                        {weeks}
                                    </button>
                                );
                            })}
                        </div>
                        {weeksAvailable != null && (weeksAvailable < 6 ? (
                            <p className="mt-1.5 text-xs text-amber-600">
                                Not enough time before event. Select a later event date to create a plan.
                            </p>
                        ) : weeksAvailable < data.total_weeks ? (
                            <p className="mt-1.5 text-xs text-amber-600">
                                Plan is longer than weeks available. Reduce total weeks or select a later event date.
                            </p>
                        ) : null)}
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
                            max={Math.min(maxWeeks, 30)}
                            value={data.total_weeks}
                            disabled={weeksAvailable != null && weeksAvailable < WEEK_OPTIONS[0]}
                            onChange={e => {
                                const val = parseInt(e.target.value);
                                if (!isNaN(val) && val >= 6 && val <= maxWeeks) {
                                    onChange({ total_weeks: val });
                                }
                            }}
                            className={`w-24 p-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                errors.total_weeks ? 'border-red-400' : 'border-slate-300'
                            } disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed`}
                        />
                        <span className="ml-2 text-sm text-slate-500">
                            {maxWeeks >= 30 ? 'weeks (6-30)' : `weeks (max ${Math.max(maxWeeks, 6)})`}
                        </span>
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
                                {TAPER_OPTIONS.map(weeks => {
                                    const taperDisabled = weeks > maxTaper;
                                    return (
                                        <button
                                            key={weeks}
                                            type="button"
                                            disabled={taperDisabled}
                                            onClick={() => onChange({ taper_weeks: weeks })}
                                            className={`
                                                px-4 py-2 rounded-lg border text-sm font-medium transition-all
                                                ${taperDisabled
                                                    ? 'border-slate-100 bg-slate-50 text-slate-300 cursor-not-allowed'
                                                    : effectiveTaper === weeks
                                                        ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                                            `}
                                        >
                                            {weeks} {weeks === 1 ? 'week' : 'weeks'}
                                        </button>
                                    );
                                })}
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
