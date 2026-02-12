import type { WizardGoalsFocus, PrimaryGoal, PainPoint } from '../../types/wizard';
import type { StepErrors } from '../../hooks/useWizard';
import { PrimaryGoalLabels, PainPointLabels } from '../../types/wizard';

interface StepGoalsFocusProps {
    data: WizardGoalsFocus;
    onChange: (data: Partial<WizardGoalsFocus>) => void;
    sport: string;
    errors: StepErrors;
}

const ALL_PAIN_POINTS: PainPoint[] = [
    'cramping', 'bonking', 'pacing', 'injury', 'mental_fatigue',
    'recovery', 'speed_final_third', 'breathing',
];

const SWIMMING_PAIN_POINTS: PainPoint[] = [
    'pacing', 'mental_fatigue', 'recovery', 'breathing',
    'open_water_anxiety', 'stroke_efficiency',
];

export function StepGoalsFocus({ data, onChange, sport }: StepGoalsFocusProps) {
    const painPoints = sport === 'swimming' ? SWIMMING_PAIN_POINTS : ALL_PAIN_POINTS;

    const togglePainPoint = (pp: PainPoint) => {
        const current = data.pain_points;
        if (current.includes(pp)) {
            onChange({ pain_points: current.filter(p => p !== pp) });
        } else {
            onChange({ pain_points: [...current, pp] });
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-slate-900 mb-1">Goals & Focus</h2>
                <p className="text-sm text-slate-500">What are you training for?</p>
            </div>

            {/* Primary goal */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Primary Goal</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {(Object.keys(PrimaryGoalLabels) as PrimaryGoal[]).map(goal => (
                        <button
                            key={goal}
                            type="button"
                            onClick={() => {
                                const updates: Partial<WizardGoalsFocus> = { primary_goal: goal };
                                if (goal !== 'target_time' && goal !== 'pb') {
                                    updates.target_time = undefined;
                                }
                                onChange(updates);
                            }}
                            className={`
                                p-2.5 rounded-lg border text-sm font-medium text-left transition-all
                                ${data.primary_goal === goal
                                    ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                            `}
                        >
                            {PrimaryGoalLabels[goal]}
                        </button>
                    ))}
                </div>
            </div>

            {/* Target time (shown for target_time or pb goals) */}
            {(data.primary_goal === 'target_time' || data.primary_goal === 'pb') && (
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                        {data.primary_goal === 'pb' ? 'Current PB (optional)' : 'Target Time'}
                    </label>
                    <input
                        type="text"
                        value={data.target_time || ''}
                        onChange={e => onChange({ target_time: e.target.value || undefined })}
                        placeholder="e.g. 3:45:00 or 1:30:00"
                        className="w-full p-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="mt-1 text-xs text-slate-400">
                        {data.primary_goal === 'pb'
                            ? 'Enter your current personal best so we can set appropriate pacing targets.'
                            : 'Format: H:MM:SS for longer events, M:SS for shorter events.'}
                    </p>
                </div>
            )}

            {/* Weekly availability */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                    Training Days per Week
                </label>
                <div className="flex gap-2">
                    {[3, 4, 5, 6, 7].map(days => (
                        <button
                            key={days}
                            type="button"
                            onClick={() => onChange({ weekly_availability: days })}
                            className={`
                                w-10 h-10 rounded-lg border text-sm font-medium transition-all
                                ${data.weekly_availability === days
                                    ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                            `}
                        >
                            {days}
                        </button>
                    ))}
                </div>
            </div>

            {/* Longest recent distance */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                    Longest recent session (km)
                </label>
                <input
                    type="number"
                    min={0}
                    max={200}
                    step={0.5}
                    value={data.longest_recent_distance_m ? data.longest_recent_distance_m / 1000 : ''}
                    onChange={e => {
                        const km = parseFloat(e.target.value) || 0;
                        onChange({ longest_recent_distance_m: Math.round(km * 1000) });
                    }}
                    placeholder="0"
                    className="w-full p-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-slate-400">
                    Your longest single session in the past 4 weeks.
                </p>
            </div>

            {/* Pain points */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                    Areas of concern <span className="text-slate-400 font-normal">(optional, select any)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                    {painPoints.map(pp => (
                        <button
                            key={pp}
                            type="button"
                            onClick={() => togglePainPoint(pp)}
                            className={`
                                px-3 py-1.5 rounded-full border text-xs font-medium transition-all
                                ${data.pain_points.includes(pp)
                                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}
                            `}
                        >
                            {PainPointLabels[pp]}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
