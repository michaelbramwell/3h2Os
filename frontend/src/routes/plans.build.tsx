import { useState, useEffect, useCallback, useMemo } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Plus, Trash2, ChevronDown, ChevronUp, ArrowLeft, Copy, Loader2 } from 'lucide-react';
import type { WizardInput, EventType, ExperienceLevel } from '../types/wizard';
import { defaultTaperWeeks } from '../types/wizard';
import type { Week, Day, Workout, ActivityType, WorkoutFormat } from '../types/schema';
import { createPlan, wizardPreview } from '../lib/api';

export const Route = createFileRoute('/plans/build')({
    component: ManualPlanBuilder,
});

// --- Constants ---

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const ACTIVITY_TYPES: ActivityType[] = ['Run', 'Trail', 'Cycling', 'Swimming', 'Cross', 'Rest', 'Other'];

const WORKOUT_FORMATS: WorkoutFormat[] = [
    'Easy', 'Long', 'Tempo', 'Threshold', 'Intervals', 'Race',
    'Recovery', 'Technique', 'Hills', 'Fartlek', 'Progression',
    'Steady', 'WarmUp', 'CoolDown', 'TimeTrial',
];

const WEEK_STATUSES = ['normal', 'recovery', 'taper', 'race'] as const;

// Event distances in metres (mirrors backend EVENT_DISTANCES_M)
const EVENT_DISTANCES_M: Record<string, number> = {
    '5k': 5000,
    '10k': 10000,
    'half_marathon': 21097,
    'marathon': 42195,
    'ultra': 50000,
    'pool_400m': 400,
    'pool_800m': 800,
    'pool_1500m': 1500,
    'ow_1km': 1000,
    'ow_2.5km': 2500,
    'ow_5km': 5000,
    'ow_10km': 10000,
};

// Event name labels for race workout naming
const EVENT_LABELS: Record<string, string> = {
    '5k': '5K',
    '10k': '10K',
    'half_marathon': 'Half Marathon',
    'marathon': 'Marathon',
    'ultra': 'Ultra',
};

// --- Session template definitions for prefill ---
// Each entry: [dayIndex, name, format, description]
// These mirror the backend week templates from running.py

interface SessionDef {
    name: string;
    format: WorkoutFormat;
    description: string;
    isLongRun: boolean;
}

// Session library
const SESSIONS: Record<string, SessionDef> = {
    easy:       { name: 'Easy Run', format: 'Easy', description: 'Comfortable aerobic pace.', isLongRun: false },
    recovery:   { name: 'Recovery', format: 'Recovery', description: 'Very easy effort for active recovery.', isLongRun: false },
    slr:        { name: 'SLR', format: 'Long', description: 'Steady long run building endurance.', isLongRun: true },
    progSlr:    { name: 'Progression SLR', format: 'Progression', description: 'Long run with progressive pace increase.', isLongRun: true },
    tempo:      { name: 'Tempo', format: 'Tempo', description: 'Sustained effort at lactate threshold pace.', isLongRun: false },
    threshold:  { name: 'Threshold', format: 'Threshold', description: 'Intervals at or near threshold pace.', isLongRun: false },
    intervals:  { name: 'Intervals', format: 'Intervals', description: 'High-intensity repetitions with recovery.', isLongRun: false },
    fartlek:    { name: 'Fartlek', format: 'Fartlek', description: 'Unstructured speed play.', isLongRun: false },
    steady:     { name: 'Steady Run', format: 'Steady', description: 'Moderate aerobic effort.', isLongRun: false },
};

// Phase session patterns per experience level
// Returns array of session keys to place on training days (long run handled separately)
type PhaseSessionPattern = {
    nonLongRun: string[];   // keys from SESSIONS, placed in order on non-long-run training days
    longRun: string;        // key from SESSIONS for the long run day
};

function getPhasePattern(
    phase: 'base' | 'build' | 'peak' | 'taper_early' | 'taper_late' | 'race',
    level: ExperienceLevel
): PhaseSessionPattern {
    switch (phase) {
        case 'base':
            return {
                nonLongRun: ['easy', 'recovery', 'easy', 'steady', 'recovery'],
                longRun: 'slr',
            };
        case 'build':
            if (level === 'advanced') {
                return {
                    nonLongRun: ['easy', 'intervals', 'easy', 'threshold', 'recovery'],
                    longRun: 'progSlr',
                };
            }
            // beginner/intermediate
            return {
                nonLongRun: ['easy', 'tempo', 'easy', 'threshold', 'recovery'],
                longRun: 'slr',
            };
        case 'peak':
            if (level === 'advanced') {
                return {
                    nonLongRun: ['easy', 'intervals', 'recovery', 'threshold', 'tempo'],
                    longRun: 'progSlr',
                };
            }
            // beginner/intermediate
            return {
                nonLongRun: ['easy', 'intervals', 'easy', 'tempo', 'recovery'],
                longRun: 'progSlr',
            };
        case 'taper_early':
            return {
                nonLongRun: ['easy', 'tempo', 'recovery', 'easy'],
                longRun: 'slr',
            };
        case 'taper_late':
            return {
                nonLongRun: ['easy', 'easy', 'recovery', 'easy'],
                longRun: 'easy',  // no real long run in late taper
            };
        case 'race':
            return {
                nonLongRun: ['easy', 'recovery', 'recovery'],
                longRun: 'easy',  // race day handled separately
            };
    }
}

// --- Helpers ---

function mondayOfWeek(weekIndex: number, startDate: Date): string {
    const d = new Date(startDate);
    d.setDate(d.getDate() + weekIndex * 7);
    return d.toISOString().split('T')[0];
}

function dateOfDay(weekStarting: string, dayIndex: number): string {
    const d = new Date(weekStarting + 'T00:00:00');
    d.setDate(d.getDate() + dayIndex);
    return d.toISOString().split('T')[0];
}

function createEmptyWeek(weekStarting: string): Week {
    const days: Record<string, Day> = {};
    for (let i = 0; i < 7; i++) {
        const date = dateOfDay(weekStarting, i);
        days[DAY_LABELS[i]] = { date, workouts: [] };
    }
    return { weekStarting, status: 'normal', days };
}

function createDefaultWorkout(activityType: ActivityType = 'Run'): Workout {
    return {
        name: '',
        type: activityType,
        format: 'Easy',
        distance_m: 0,
        timeOfDay: 'AM',
        description: '',
    };
}

function formatDistance(meters: number): string {
    if (meters >= 1000) return `${(meters / 1000).toFixed(1)}km`;
    return `${meters}m`;
}

function weekVolume(week: Week): number {
    let total = 0;
    for (const day of Object.values(week.days)) {
        for (const w of day.workouts) {
            total += w.distance_m;
        }
    }
    return total;
}

// --- Components ---

interface WorkoutEditorProps {
    workout: Workout;
    onChange: (workout: Workout) => void;
    onRemove: () => void;
    sport: string;
}

function WorkoutEditor({ workout, onChange, onRemove, sport }: WorkoutEditorProps) {
    const relevantTypes = sport === 'swimming'
        ? ACTIVITY_TYPES.filter(t => ['Swimming', 'Rest', 'Cross', 'Other'].includes(t))
        : ACTIVITY_TYPES;

    const [localDistance, setLocalDistance] = useState(
        workout.distance_m > 0 ? (workout.distance_m / 1000).toString() : ''
    );
    const [isEditingDistance, setIsEditingDistance] = useState(false);

    // Sync local input with external changes when not actively editing
    useEffect(() => {
        if (!isEditingDistance) {
            setLocalDistance(workout.distance_m > 0 ? (workout.distance_m / 1000).toString() : '');
        }
    }, [workout.distance_m, isEditingDistance]);

    const handleDistanceChange = (val: string) => {
        setLocalDistance(val);
        const km = parseFloat(val);
        onChange({ ...workout, distance_m: isNaN(km) ? 0 : Math.round(km * 1000) });
    };

    return (
        <div className="bg-white border border-slate-200 rounded-lg p-2 space-y-2 relative group">
            <div className="flex items-start justify-between gap-1">
                <input
                    type="text"
                    value={workout.name}
                    onChange={e => onChange({ ...workout, name: e.target.value })}
                    placeholder="Workout name"
                    className="w-full text-xs font-medium border border-slate-200 rounded px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                    type="button"
                    onClick={onRemove}
                    className="p-1 text-slate-300 hover:text-red-500 bg-white absolute -top-1 -right-1 rounded-full shadow-sm opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Remove workout"
                >
                    <Trash2 className="w-3.5 h-3.5" />
                </button>
            </div>

            <div className="space-y-1.5">
                <select
                    value={workout.type}
                    onChange={e => onChange({ ...workout, type: e.target.value as ActivityType })}
                    className="w-full text-xs border border-slate-200 rounded px-1.5 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                    {relevantTypes.map(t => (
                        <option key={t} value={t}>{t}</option>
                    ))}
                </select>
                <select
                    value={workout.format || ''}
                    onChange={e => onChange({ ...workout, format: (e.target.value || undefined) as WorkoutFormat | undefined })}
                    className="w-full text-xs border border-slate-200 rounded px-1.5 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                    <option value="">No format</option>
                    {WORKOUT_FORMATS.map(f => (
                        <option key={f} value={f}>{f}</option>
                    ))}
                </select>
            </div>

            <div className="flex gap-1.5">
                <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={localDistance}
                    onChange={e => handleDistanceChange(e.target.value)}
                    onFocus={() => setIsEditingDistance(true)}
                    onBlur={() => {
                        setIsEditingDistance(false);
                        setLocalDistance(workout.distance_m > 0 ? (workout.distance_m / 1000).toString() : '');
                    }}
                    placeholder="km"
                    className="w-full flex-1 text-xs border border-slate-200 rounded px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <select
                    value={workout.timeOfDay}
                    onChange={e => onChange({ ...workout, timeOfDay: e.target.value })}
                    className="w-12 shrink-0 text-xs border border-slate-200 rounded px-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                    <option value="AM">AM</option>
                    <option value="PM">PM</option>
                </select>
            </div>

            <textarea
                value={workout.description || ''}
                onChange={e => onChange({ ...workout, description: e.target.value })}
                placeholder="Description"
                rows={2}
                className="w-full text-xs border border-slate-200 rounded px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
        </div>
    );
}

interface DayColumnProps {
    dayLabel: string;
    day: Day;
    onChange: (day: Day) => void;
    sport: string;
}

function DayColumn({ dayLabel, day, onChange, sport }: DayColumnProps) {
    const defaultType: ActivityType = sport === 'swimming' ? 'Swimming' : 'Run';

    const addWorkout = () => {
        onChange({
            ...day,
            workouts: [...day.workouts, createDefaultWorkout(defaultType)],
        });
    };

    const updateWorkout = (index: number, workout: Workout) => {
        const updated = [...day.workouts];
        updated[index] = workout;
        onChange({ ...day, workouts: updated });
    };

    const removeWorkout = (index: number) => {
        onChange({
            ...day,
            workouts: day.workouts.filter((_, i) => i !== index),
        });
    };

    const dayVolume = day.workouts.reduce((sum, w) => sum + w.distance_m, 0);

    return (
        <div className="flex flex-col">
            <div className="text-center mb-2">
                <p className="text-xs font-semibold text-slate-600">{dayLabel}</p>
                <p className="text-[10px] text-slate-400">{day.date}</p>
                {dayVolume > 0 && (
                    <p className="text-[10px] text-blue-500 font-medium">{formatDistance(dayVolume)}</p>
                )}
            </div>

            <div className="space-y-2 flex-1">
                {day.workouts.map((workout, i) => (
                    <WorkoutEditor
                        key={i}
                        workout={workout}
                        onChange={w => updateWorkout(i, w)}
                        onRemove={() => removeWorkout(i)}
                        sport={sport}
                    />
                ))}
            </div>

            <button
                type="button"
                onClick={addWorkout}
                className="mt-2 w-full flex items-center justify-center gap-1 px-2 py-1.5 text-xs text-slate-500 border border-dashed border-slate-300 rounded-lg hover:border-blue-400 hover:text-blue-600 transition-colors"
            >
                <Plus className="w-3 h-3" /> Add
            </button>
        </div>
    );
}

interface WeekRowProps {
    week: Week;
    weekIndex: number;
    onChange: (week: Week) => void;
    onRemove: () => void;
    onDuplicate: () => void;
    sport: string;
}

function WeekRow({ week, weekIndex, onChange, onRemove, onDuplicate, sport }: WeekRowProps) {
    const [collapsed, setCollapsed] = useState(false);
    const vol = weekVolume(week);

    const updateDay = (dayLabel: string, day: Day) => {
        onChange({ ...week, days: { ...week.days, [dayLabel]: day } });
    };

    return (
        <div className="border border-slate-200 rounded-xl bg-white shadow-sm">
            {/* Week header */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 rounded-t-xl border-b border-slate-100">
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={() => setCollapsed(!collapsed)}
                        className="p-0.5 text-slate-400 hover:text-slate-600"
                    >
                        {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                    </button>
                    <h3 className="text-sm font-semibold text-slate-800">
                        Week {weekIndex + 1}
                    </h3>
                    <span className="text-xs text-slate-400">
                        w/c {week.weekStarting}
                    </span>
                    {vol > 0 && (
                        <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                            {formatDistance(vol)}
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    <select
                        value={week.status}
                        onChange={e => onChange({ ...week, status: e.target.value })}
                        className="text-xs border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                        {WEEK_STATUSES.map(s => (
                            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                        ))}
                    </select>
                    <button
                        type="button"
                        onClick={onDuplicate}
                        className="p-1.5 text-slate-400 hover:text-blue-500 transition-colors"
                        title="Duplicate week"
                    >
                        <Copy className="w-3.5 h-3.5" />
                    </button>
                    <button
                        type="button"
                        onClick={onRemove}
                        className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                        title="Remove week"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Day columns */}
            {!collapsed && (
                <div className="p-4 grid grid-cols-7 gap-3">
                    {DAY_LABELS.map(dayLabel => (
                        <DayColumn
                            key={dayLabel}
                            dayLabel={dayLabel}
                            day={week.days[dayLabel] || { date: '', workouts: [] }}
                            onChange={day => updateDay(dayLabel, day)}
                            sport={sport}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

// --- Main page component ---

function ManualPlanBuilder() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // Load wizard input from sessionStorage
    const [wizardInput, setWizardInput] = useState<WizardInput | null>(null);
    const [weeks, setWeeks] = useState<Week[]>([]);
    const [title, setTitle] = useState('');
    const [saving, setSaving] = useState(false);
    const [loadingTemplate, setLoadingTemplate] = useState(false);

    useEffect(() => {
        const stored = sessionStorage.getItem('wizardInput');
        if (stored) {
            try {
                const input = JSON.parse(stored) as WizardInput;
                setWizardInput(input);
                setTitle(input.sport_event.plan_name || `${input.sport_event.event_name || EVENT_LABELS[input.sport_event.event_type] || input.sport_event.event_type} Plan`);

                // Build prefilled weeks
                const prefilled = buildPrefilledWeeks(input);
                setWeeks(prefilled);
            } catch {
                // Invalid JSON -- ignore
            }
        }
    }, []);

    const sport = wizardInput?.sport_event.sport || 'running';

    const loadFromTemplate = useCallback(async () => {
        if (!wizardInput) return;
        setLoadingTemplate(true);
        try {
            const preview = await wizardPreview(wizardInput);

            // Rebuild weeks using phase info from the preview for more accurate
            // phase boundaries, but keep our prefill workout logic.
            const startDate = wizardInput.sport_event.event_date
                ? calculateStartDate(wizardInput.sport_event.event_date, preview.total_weeks)
                : new Date();

            const level = wizardInput.athlete_profile.experience_level as ExperienceLevel;
            const eventType = wizardInput.sport_event.event_type as EventType;
            const sport = wizardInput.sport_event.sport;
            const activityType: ActivityType = sport === 'swimming' ? 'Swimming' : 'Run';
            const timeOfDay = wizardInput.athlete_profile.preferred_time_of_day || 'AM';

            // Resolve training days
            const trainingDays = wizardInput.athlete_profile.preferred_training_days
                || defaultTrainingDays(wizardInput.goals_focus.weekly_availability);
            const longRunDay = wizardInput.athlete_profile.preferred_long_run_day ?? 6; // Sunday

            const raceDistance = EVENT_DISTANCES_M[eventType] || 42195;

            const templateWeeks: Week[] = [];
            let weekCounter = 0;

            for (const phase of preview.phases) {
                for (let i = 0; i < phase.weeks; i++) {
                    const ws = mondayOfWeek(weekCounter, startDate);
                    const week = createEmptyWeek(ws);

                    // Determine phase type and status
                    const phaseLower = phase.name.toLowerCase();
                    let phaseType: 'base' | 'build' | 'peak' | 'taper_early' | 'taper_late' | 'race';

                    if (phaseLower.includes('race')) {
                        week.status = 'race';
                        phaseType = 'race';
                    } else if (phaseLower.includes('taper')) {
                        week.status = 'taper';
                        // Early vs late taper
                        const isLateTaper = phase.weeks > 1 && i >= Math.ceil(phase.weeks / 2);
                        phaseType = isLateTaper ? 'taper_late' : 'taper_early';
                    } else if (phaseLower.includes('peak')) {
                        week.status = (i + 1) % 4 === 0 ? 'recovery' : 'normal';
                        phaseType = 'peak';
                    } else if (phaseLower.includes('build')) {
                        week.status = (i + 1) % 4 === 0 ? 'recovery' : 'normal';
                        phaseType = 'build';
                    } else {
                        week.status = (i + 1) % 4 === 0 ? 'recovery' : 'normal';
                        phaseType = 'base';
                    }

                    // Place workouts on training days
                    if (week.status === 'race') {
                        // Race week: easy/recovery on non-race days, race on race day (Sun)
                        const raceWorkout = createRaceWorkout(eventType, raceDistance, activityType, timeOfDay);
                        week.days[DAY_LABELS[longRunDay]].workouts = [raceWorkout];
                        const otherDays = trainingDays.filter(d => d !== longRunDay).slice(0, 3);
                        const racePattern = getPhasePattern('race', level);
                        otherDays.forEach((d, idx) => {
                            const key = racePattern.nonLongRun[idx] || 'recovery';
                            const sess = SESSIONS[key];
                            week.days[DAY_LABELS[d]].workouts = [{
                                name: sess.name,
                                type: activityType,
                                format: sess.format,
                                distance_m: 0,
                                timeOfDay,
                                description: sess.description,
                            }];
                        });
                    } else {
                        populateWeekWorkouts(week, phaseType, level, trainingDays, longRunDay, activityType, timeOfDay);
                    }

                    templateWeeks.push(week);
                    weekCounter++;
                }
            }

            setWeeks(templateWeeks);
            setTitle(preview.title);
            toast.success('Loaded template structure with workouts. Edit as needed.');
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'Failed to load template';
            toast.error(msg);
        } finally {
            setLoadingTemplate(false);
        }
    }, [wizardInput]);

    const addWeek = useCallback(() => {
        setWeeks(prev => {
            const lastWeek = prev[prev.length - 1];
            const nextMonday = lastWeek
                ? mondayOfWeek(1, new Date(lastWeek.weekStarting + 'T00:00:00'))
                : mondayOfWeek(0, new Date());
            return [...prev, createEmptyWeek(nextMonday)];
        });
    }, []);

    const removeWeek = useCallback((index: number) => {
        setWeeks(prev => prev.filter((_, i) => i !== index));
    }, []);

    const duplicateWeek = useCallback((index: number) => {
        setWeeks(prev => {
            const source = prev[index];
            // Recalculate dates for the duplicated week (insert after source)
            const newWeeks = [...prev];
            const nextMonday = mondayOfWeek(1, new Date(source.weekStarting + 'T00:00:00'));
            const cloned: Week = JSON.parse(JSON.stringify(source));
            cloned.weekStarting = nextMonday;
            // Update day dates
            for (let i = 0; i < 7; i++) {
                const dayLabel = DAY_LABELS[i];
                if (cloned.days[dayLabel]) {
                    cloned.days[dayLabel].date = dateOfDay(nextMonday, i);
                }
            }
            delete cloned.id;
            newWeeks.splice(index + 1, 0, cloned);
            // Recalculate subsequent week dates
            return recalculateWeekDates(newWeeks);
        });
    }, []);

    const updateWeek = useCallback((index: number, week: Week) => {
        setWeeks(prev => {
            const updated = [...prev];
            updated[index] = week;
            return updated;
        });
    }, []);

    const totalVolume = useMemo(() => weeks.reduce((sum, w) => sum + weekVolume(w), 0), [weeks]);

    const handleSave = async () => {
        if (weeks.length === 0) {
            toast.error('Add at least one week before saving.');
            return;
        }
        if (!title.trim()) {
            toast.error('Enter a plan title.');
            return;
        }

        setSaving(true);
        try {
            const result = await createPlan(title, sport, weeks);
            toast.success(`Plan "${result.title || title}" created.`);
            sessionStorage.removeItem('wizardInput');
            queryClient.invalidateQueries({ queryKey: ['plan'] });
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            queryClient.invalidateQueries({ queryKey: ['context'] });
            navigate({ to: '/' });
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'Failed to save plan';
            toast.error(msg);
        } finally {
            setSaving(false);
        }
    };

    if (!wizardInput) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center">
                <div className="text-center space-y-4">
                    <p className="text-slate-500">No wizard data found. Start from the plan wizard.</p>
                    <button
                        type="button"
                        onClick={() => navigate({ to: '/' })}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Top bar */}
            <div className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
                <div className="max-w-[1800px] mx-auto px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            type="button"
                            onClick={() => navigate({ to: '/' })}
                            className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors"
                            title="Back to dashboard"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                            <input
                                type="text"
                                value={title}
                                onChange={e => setTitle(e.target.value)}
                                className="text-lg font-semibold text-slate-900 border-none bg-transparent focus:outline-none focus:ring-0 p-0"
                                placeholder="Plan title"
                            />
                            <p className="text-xs text-slate-400">
                                {weeks.length} weeks -- {formatDistance(totalVolume)} total volume
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={loadFromTemplate}
                            disabled={loadingTemplate}
                            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 transition-colors flex items-center gap-2"
                        >
                            {loadingTemplate && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                            Start from Template
                        </button>
                        <button
                            type="button"
                            onClick={handleSave}
                            disabled={saving || weeks.length === 0}
                            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                        >
                            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                            Save Plan
                        </button>
                    </div>
                </div>
            </div>

            {/* Week list */}
            <div className="max-w-[1800px] mx-auto px-4 py-6 space-y-4">
                {weeks.map((week, i) => (
                    <WeekRow
                        key={`${week.weekStarting}-${i}`}
                        week={week}
                        weekIndex={i}
                        onChange={w => updateWeek(i, w)}
                        onRemove={() => removeWeek(i)}
                        onDuplicate={() => duplicateWeek(i)}
                        sport={sport}
                    />
                ))}

                <button
                    type="button"
                    onClick={addWeek}
                    className="w-full py-4 flex items-center justify-center gap-2 text-sm text-slate-500 border-2 border-dashed border-slate-300 rounded-xl hover:border-blue-400 hover:text-blue-600 transition-colors"
                >
                    <Plus className="w-4 h-4" /> Add Week
                </button>
            </div>
        </div>
    );
}

// --- Utility ---

function calculateStartDate(eventDateStr: string, totalWeeks: number): Date {
    const eventDate = new Date(eventDateStr + 'T00:00:00');
    const start = new Date(eventDate);
    start.setDate(start.getDate() - totalWeeks * 7);
    // Adjust to nearest Monday
    const dayOfWeek = start.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    start.setDate(start.getDate() + diff);
    return start;
}

function recalculateWeekDates(weeks: Week[]): Week[] {
    if (weeks.length === 0) return weeks;
    const firstMonday = new Date(weeks[0].weekStarting + 'T00:00:00');

    return weeks.map((week, i) => {
        const ws = mondayOfWeek(i, firstMonday);
        const updatedDays: Record<string, Day> = {};
        for (let d = 0; d < 7; d++) {
            const dayLabel = DAY_LABELS[d];
            const existingDay = week.days[dayLabel];
            updatedDays[dayLabel] = {
                date: dateOfDay(ws, d),
                workouts: existingDay?.workouts || [],
            };
        }
        return { ...week, weekStarting: ws, days: updatedDays };
    });
}

// Default training days based on weekly availability
function defaultTrainingDays(availability: number): number[] {
    // Standard defaults: Mon(0), Tue(1), Wed(2), Thu(3), Fri(4), Sat(5), Sun(6)
    const defaults: Record<number, number[]> = {
        3: [1, 3, 6],          // Tue, Thu, Sun
        4: [0, 1, 3, 6],      // Mon, Tue, Thu, Sun
        5: [0, 1, 3, 4, 6],   // Mon, Tue, Thu, Fri, Sun
        6: [0, 1, 2, 3, 4, 6],// Mon-Fri + Sun
        7: [0, 1, 2, 3, 4, 5, 6],
    };
    return defaults[availability] || defaults[5];
}

// Create a race day workout
function createRaceWorkout(
    eventType: EventType,
    raceDistance: number,
    activityType: ActivityType,
    timeOfDay: string
): Workout {
    const label = EVENT_LABELS[eventType] || eventType;
    return {
        name: `${label} Race Day`,
        type: activityType,
        format: 'Race',
        distance_m: raceDistance,
        timeOfDay,
        description: `Race day -- ${label} (${formatDistance(raceDistance)}).`,
    };
}

// Place workouts on the training days for a given phase
function populateWeekWorkouts(
    week: Week,
    phaseType: 'base' | 'build' | 'peak' | 'taper_early' | 'taper_late' | 'race',
    level: ExperienceLevel,
    trainingDays: number[],
    longRunDay: number,
    activityType: ActivityType,
    timeOfDay: string,
) {
    const pattern = getPhasePattern(phaseType, level);

    // Place long run on the designated day
    if (trainingDays.includes(longRunDay)) {
        const longSess = SESSIONS[pattern.longRun];
        week.days[DAY_LABELS[longRunDay]].workouts = [{
            name: longSess.name,
            type: activityType,
            format: longSess.format,
            distance_m: 0,
            timeOfDay,
            description: longSess.description,
        }];
    }

    // Place non-long-run sessions on remaining training days
    const otherDays = trainingDays.filter(d => d !== longRunDay);
    otherDays.forEach((d, idx) => {
        const key = pattern.nonLongRun[idx % pattern.nonLongRun.length];
        const sess = SESSIONS[key];
        week.days[DAY_LABELS[d]].workouts = [{
            name: sess.name,
            type: activityType,
            format: sess.format,
            distance_m: 0,
            timeOfDay,
            description: sess.description,
        }];
    });
}

// Build the full set of prefilled weeks from wizard input
function buildPrefilledWeeks(input: WizardInput): Week[] {
    const isManualWeekly = input.plan_config.generation_method === 'manual_weekly' || input.sport_event.event_type === 'none';
    const isManual = input.plan_config.generation_method === 'manual';

    if (isManualWeekly) {
        // Just return one completely empty week starting next Monday
        const today = new Date();
        const daysAhead = (7 - today.getDay() + 1) % 7 || 7;
        const nextMonday = new Date(today);
        nextMonday.setDate(today.getDate() + daysAhead);
        return [createEmptyWeek(nextMonday.toISOString().split('T')[0])];
    }

    const totalWeeks = input.plan_config.total_weeks;
    const taperWeeks = input.plan_config.taper_weeks ?? defaultTaperWeeks(input.sport_event.event_type as EventType);
    const level = input.athlete_profile.experience_level as ExperienceLevel;
    const eventType = input.sport_event.event_type as EventType;
    const sport = input.sport_event.sport;
    const activityType: ActivityType = sport === 'swimming' ? 'Swimming' : 'Run';
    const timeOfDay = input.athlete_profile.preferred_time_of_day || 'AM';

    // Resolve training days
    const trainingDays = input.athlete_profile.preferred_training_days
        || defaultTrainingDays(input.goals_focus.weekly_availability);
    const longRunDay = input.athlete_profile.preferred_long_run_day ?? 6; // Sunday default

    const raceDistance = EVENT_DISTANCES_M[eventType] || 42195;

    const startDate = input.sport_event.event_date
        ? calculateStartDate(input.sport_event.event_date, totalWeeks)
        : new Date();

    // Phase structure: race=1 week (last), taper=N weeks before that, rest split as base/build/peak
    const raceWeeksCount = 1;
    const remainingWeeks = Math.max(0, totalWeeks - raceWeeksCount - taperWeeks);

    // Split remaining into base/build/peak using approximate proportions
    // base ~25%, build ~50%, peak ~25% of remaining
    let baseWeeks: number;
    let buildWeeks: number;
    let peakWeeks: number;

    if (remainingWeeks <= 0) {
        baseWeeks = 0;
        buildWeeks = 0;
        peakWeeks = 0;
    } else if (remainingWeeks === 1) {
        baseWeeks = 0;
        buildWeeks = 1;
        peakWeeks = 0;
    } else if (remainingWeeks === 2) {
        baseWeeks = 1;
        buildWeeks = 1;
        peakWeeks = 0;
    } else {
        baseWeeks = Math.max(1, Math.round(remainingWeeks * 0.25));
        peakWeeks = Math.max(1, Math.round(remainingWeeks * 0.20));
        buildWeeks = remainingWeeks - baseWeeks - peakWeeks;
    }

    const allWeeks: Week[] = [];

    // Helper to conditionally populate workouts
    const maybePopulate = (week: Week, phaseType: 'base' | 'build' | 'peak' | 'taper_early' | 'taper_late' | 'race') => {
        if (!isManual) {
            populateWeekWorkouts(week, phaseType, level, trainingDays, longRunDay, activityType, timeOfDay);
        }
    };

    // Base phase
    for (let i = 0; i < baseWeeks; i++) {
        const ws = mondayOfWeek(allWeeks.length, startDate);
        const week = createEmptyWeek(ws);
        week.status = (i + 1) % 4 === 0 ? 'recovery' : 'normal';
        maybePopulate(week, 'base');
        allWeeks.push(week);
    }

    // Build phase
    for (let i = 0; i < buildWeeks; i++) {
        const ws = mondayOfWeek(allWeeks.length, startDate);
        const week = createEmptyWeek(ws);
        week.status = (i + 1) % 4 === 0 ? 'recovery' : 'normal';
        maybePopulate(week, 'build');
        allWeeks.push(week);
    }

    // Peak phase
    for (let i = 0; i < peakWeeks; i++) {
        const ws = mondayOfWeek(allWeeks.length, startDate);
        const week = createEmptyWeek(ws);
        week.status = (i + 1) % 4 === 0 ? 'recovery' : 'normal';
        maybePopulate(week, 'peak');
        allWeeks.push(week);
    }

    // Taper phase
    for (let i = 0; i < taperWeeks; i++) {
        const ws = mondayOfWeek(allWeeks.length, startDate);
        const week = createEmptyWeek(ws);
        week.status = 'taper';
        const isLateTaper = taperWeeks > 1 && i >= Math.ceil(taperWeeks / 2);
        const taperPhase = isLateTaper ? 'taper_late' : 'taper_early';
        maybePopulate(week, taperPhase);
        allWeeks.push(week);
    }

    // Race week
    {
        const ws = mondayOfWeek(allWeeks.length, startDate);
        const week = createEmptyWeek(ws);
        week.status = 'race';

        if (!isManual) {
            // Race on the long run day (typically Sunday)
            const raceWorkout = createRaceWorkout(eventType, raceDistance, activityType, timeOfDay);
            week.days[DAY_LABELS[longRunDay]].workouts = [raceWorkout];

            // Light sessions on a few other days
            const otherDays = trainingDays.filter(d => d !== longRunDay).slice(0, 3);
            const racePattern = getPhasePattern('race', level);
            otherDays.forEach((d, idx) => {
                const key = racePattern.nonLongRun[idx] || 'recovery';
                const sess = SESSIONS[key];
                week.days[DAY_LABELS[d]].workouts = [{
                    name: sess.name,
                    type: activityType,
                    format: sess.format,
                    distance_m: 0,
                    timeOfDay,
                    description: sess.description,
                }];
            });
        }

        allWeeks.push(week);
    }

    return allWeeks;
}
