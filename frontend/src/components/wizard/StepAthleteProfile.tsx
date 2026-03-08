import type { WizardAthleteProfile, ExperienceLevel } from '../../types/wizard';
import { Sport } from '../../types/wizard';
import type { StepErrors } from '../../hooks/useWizard';
import type { IntegrationSources } from './IntegrationBanner';
import { IntegrationBanner } from './IntegrationBanner';

interface StepAthleteProfileProps {
    data: WizardAthleteProfile;
    onChange: (data: Partial<WizardAthleteProfile>) => void;
    sport: Sport;
    errors: StepErrors;
    swimmingEnabled?: boolean;
    integrationSources?: IntegrationSources;
}

// Default empty custom zones structure matching the zone calculator output
function defaultCustomZones(sport: Sport): Record<string, any> {
    const hrZones = [
        { zone: 1, lowBoundary_bpm: 0, highBoundary_bpm: 0, description: 'Recovery' },
        { zone: 2, lowBoundary_bpm: 0, highBoundary_bpm: 0, description: 'Aerobic' },
        { zone: 3, lowBoundary_bpm: 0, highBoundary_bpm: 0, description: 'Tempo' },
        { zone: 4, lowBoundary_bpm: 0, highBoundary_bpm: 0, description: 'Threshold' },
        { zone: 5, lowBoundary_bpm: 0, highBoundary_bpm: 0, description: 'VO2max' },
    ];

    if (sport === Sport.SWIMMING) {
        return {
            heartRate: hrZones,
            swimPace: [
                { zone: 1, lowBoundary_m_s: 0, description: 'Recovery' },
                { zone: 2, lowBoundary_m_s: 0, description: 'Endurance' },
                { zone: 3, lowBoundary_m_s: 0, description: 'CSS / Tempo' },
                { zone: 4, lowBoundary_m_s: 0, description: 'Threshold' },
                { zone: 5, lowBoundary_m_s: 0, description: 'VO2max' },
            ],
        };
    }

    return {
        heartRate: hrZones,
        pace: [
            { zone: 1, lowBoundary_m_s: 0, description: 'Recovery' },
            { zone: 2, lowBoundary_m_s: 0, description: 'Easy' },
            { zone: 3, lowBoundary_m_s: 0, description: 'Tempo' },
            { zone: 4, lowBoundary_m_s: 0, description: 'Threshold' },
            { zone: 5, lowBoundary_m_s: 0, description: 'Interval' },
        ],
    };
}

// Convert m/s to min:sec per km for display
function msToMinPerKm(ms: number): string {
    if (!ms || ms <= 0) return '';
    const secPerKm = 1000 / ms;
    const mins = Math.floor(secPerKm / 60);
    const secs = Math.round(secPerKm % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Convert min:sec per km to m/s
function minPerKmToMs(value: string): number {
    if (!value) return 0;
    const parts = value.split(':');
    if (parts.length !== 2) return 0;
    const mins = parseInt(parts[0]) || 0;
    const secs = parseInt(parts[1]) || 0;
    const totalSecs = mins * 60 + secs;
    if (totalSecs <= 0) return 0;
    return 1000 / totalSecs;
}

// Convert m/s to min:sec per 100m for swim display
function msToMinPer100m(ms: number): string {
    if (!ms || ms <= 0) return '';
    const secPer100 = 100 / ms;
    const mins = Math.floor(secPer100 / 60);
    const secs = Math.round(secPer100 % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Convert min:sec per 100m to m/s
function minPer100mToMs(value: string): number {
    if (!value) return 0;
    const parts = value.split(':');
    if (parts.length !== 2) return 0;
    const mins = parseInt(parts[0]) || 0;
    const secs = parseInt(parts[1]) || 0;
    const totalSecs = mins * 60 + secs;
    if (totalSecs <= 0) return 0;
    return 100 / totalSecs;
}

export function StepAthleteProfile({ data, onChange, sport, errors, swimmingEnabled = false, integrationSources }: StepAthleteProfileProps) {
    // If swimming is disabled, treat the sport as running for zone display purposes
    const effectiveSport = (!swimmingEnabled && sport === Sport.SWIMMING) ? Sport.RUNNING : sport;
    const showZoneToggle = data.experience_level !== 'beginner';
    const showCustomZones = showZoneToggle && !data.use_calculated_zones;

    const customZones = data.custom_zones || defaultCustomZones(effectiveSport);
    const hrZones: any[] = customZones.heartRate || [];
    const paceKey = effectiveSport === Sport.SWIMMING ? 'swimPace' : 'pace';
    const paceZones: any[] = customZones[paceKey] || [];

    const updateHrZone = (zoneIndex: number, field: 'lowBoundary_bpm' | 'highBoundary_bpm', value: number) => {
        const updated = hrZones.map((z: any, i: number) =>
            i === zoneIndex ? { ...z, [field]: value } : z
        );
        onChange({
            custom_zones: { ...customZones, heartRate: updated },
        });
    };

    const updatePaceZone = (zoneIndex: number, rawValue: string) => {
        const ms = effectiveSport === Sport.SWIMMING
            ? minPer100mToMs(rawValue)
            : minPerKmToMs(rawValue);
        const updated = paceZones.map((z: any, i: number) =>
            i === zoneIndex ? { ...z, lowBoundary_m_s: ms } : z
        );
        onChange({
            custom_zones: { ...customZones, [paceKey]: updated },
        });
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-slate-900 mb-1">Athlete Profile</h2>
                <p className="text-sm text-slate-500">Tell us about yourself so we can tailor your plan.</p>
            </div>

            {integrationSources && <IntegrationBanner sources={integrationSources} />}

            {/* Experience level */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Experience Level</label>
                <div className="grid grid-cols-3 gap-3">
                    {(['beginner', 'intermediate', 'advanced'] as ExperienceLevel[]).map(level => (
                        <button
                            key={level}
                            type="button"
                            onClick={() => {
                                const updates: Partial<WizardAthleteProfile> = { experience_level: level };
                                // Beginners always use calculated zones
                                if (level === 'beginner') {
                                    updates.use_calculated_zones = true;
                                    updates.custom_zones = undefined;
                                }
                                onChange(updates);
                            }}
                            className={`
                                p-2.5 rounded-lg border text-sm font-medium transition-all
                                ${data.experience_level === level
                                    ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                            `}
                        >
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                        </button>
                    ))}
                </div>
                <p className="mt-1.5 text-xs text-slate-400">
                    {data.experience_level === 'beginner' && 'New to the sport or returning after a long break.'}
                    {data.experience_level === 'intermediate' && 'Regularly training, completed a few events.'}
                    {data.experience_level === 'advanced' && 'Experienced athlete with structured training history.'}
                </p>
            </div>

            {/* Age and weight */}
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Age</label>
                    <input
                        type="number"
                        min={10}
                        max={100}
                        value={data.age}
                        onChange={e => onChange({ age: parseInt(e.target.value) || 0 })}
                        className={`w-full p-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            errors.age ? 'border-red-400' : 'border-slate-300'
                        }`}
                    />
                    {errors.age && (
                        <p className="mt-1 text-xs text-red-500">{errors.age}</p>
                    )}
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Weight (kg)</label>
                    <input
                        type="number"
                        min={30}
                        max={200}
                        step={0.5}
                        value={data.weight_kg}
                        onChange={e => onChange({ weight_kg: parseFloat(e.target.value) || 0 })}
                        className="w-full p-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
            </div>

            {/* Events completed */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                    Events completed at this distance
                </label>
                <input
                    type="number"
                    min={0}
                    max={999}
                    value={data.events_completed}
                    onChange={e => onChange({ events_completed: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            {/* Preferred time of day */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                    Preferred training time
                </label>
                <div className="grid grid-cols-3 gap-3">
                    {([
                        { value: 'AM' as const, label: 'Morning (AM)' },
                        { value: 'PM' as const, label: 'Evening (PM)' },
                        { value: undefined, label: 'No preference' },
                    ] as const).map(option => (
                        <button
                            key={option.label}
                            type="button"
                            onClick={() => onChange({ preferred_time_of_day: option.value })}
                            className={`
                                p-2.5 rounded-lg border text-sm font-medium transition-all
                                ${data.preferred_time_of_day === option.value
                                    ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                            `}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
                <p className="mt-1.5 text-xs text-slate-400">
                    Sets the default time of day for all workouts in your plan.
                </p>
            </div>

            {/* Preferred training days */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                    Preferred training days
                </label>
                <div className="grid grid-cols-7 gap-2">
                    {(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const).map((dayLabel, dayIndex) => {
                        const isSelected = data.preferred_training_days?.includes(dayIndex) ?? false;
                        return (
                            <button
                                key={dayLabel}
                                type="button"
                                onClick={() => {
                                    const current = data.preferred_training_days ?? [];
                                    let next: number[];
                                    if (isSelected) {
                                        next = current.filter(d => d !== dayIndex);
                                        // Also clear long run day if it was this day
                                        const updates: Partial<WizardAthleteProfile> = {
                                            preferred_training_days: next.length > 0 ? next : undefined,
                                        };
                                        if (data.preferred_long_run_day === dayIndex) {
                                            updates.preferred_long_run_day = undefined;
                                        }
                                        onChange(updates);
                                    } else {
                                        next = [...current, dayIndex].sort((a, b) => a - b);
                                        onChange({ preferred_training_days: next });
                                    }
                                }}
                                className={`
                                    p-2 rounded-lg border text-sm font-medium transition-all
                                    ${isSelected
                                        ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                                `}
                            >
                                {dayLabel}
                            </button>
                        );
                    })}
                </div>
                <p className="mt-1.5 text-xs text-slate-400">
                    Select the days you prefer to train. Leave blank to use the template defaults.
                </p>
            </div>

            {/* Preferred long run day */}
            {effectiveSport === Sport.RUNNING && (
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                        Preferred long run day
                    </label>
                    <div className="grid grid-cols-7 gap-2">
                        {(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const).map((dayLabel, dayIndex) => {
                            const isSelected = data.preferred_long_run_day === dayIndex;
                            const isTrainingDay = data.preferred_training_days?.includes(dayIndex) ?? true;
                            return (
                                <button
                                    key={dayLabel}
                                    type="button"
                                    disabled={!isTrainingDay}
                                    onClick={() => {
                                        onChange({
                                            preferred_long_run_day: isSelected ? undefined : dayIndex,
                                        });
                                    }}
                                    className={`
                                        p-2 rounded-lg border text-sm font-medium transition-all
                                        ${!isTrainingDay
                                            ? 'border-slate-100 bg-slate-50 text-slate-300 cursor-not-allowed'
                                            : isSelected
                                                ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                                    `}
                                >
                                    {dayLabel}
                                </button>
                            );
                        })}
                    </div>
                    <p className="mt-1.5 text-xs text-slate-400">
                        {data.preferred_training_days
                            ? 'Choose from your selected training days. Leave blank for Sunday (default).'
                            : 'Defaults to Sunday. Select training days above first, or leave blank.'}
                    </p>
                </div>
            )}

            {/* Zone toggle (intermediate/advanced only) */}
            {showZoneToggle && (
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-slate-700">Training Zones</p>
                            <p className="text-xs text-slate-500 mt-0.5">
                                Auto-calculated from your age and experience, or enter your own.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => {
                                if (data.use_calculated_zones) {
                                    // Switching to custom: initialise with empty zones
                                    onChange({
                                        use_calculated_zones: false,
                                        custom_zones: data.custom_zones || defaultCustomZones(effectiveSport),
                                    });
                                } else {
                                    // Switching back to auto-calculated
                                    onChange({
                                        use_calculated_zones: true,
                                    });
                                }
                            }}
                            className={`
                                relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full
                                border-2 border-transparent transition-colors duration-200 ease-in-out
                                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                                ${data.use_calculated_zones ? 'bg-blue-600' : 'bg-slate-300'}
                            `}
                        >
                            <span className="sr-only">Use auto-calculated zones</span>
                            <span
                                className={`
                                    pointer-events-none inline-block h-5 w-5 transform rounded-full
                                    bg-white shadow ring-0 transition duration-200 ease-in-out
                                    ${data.use_calculated_zones ? 'translate-x-5' : 'translate-x-0'}
                                `}
                            />
                        </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        {data.use_calculated_zones
                            ? 'Zones will be calculated automatically for your plan.'
                            : 'Enter your known training zones below.'}
                    </p>
                </div>
            )}

            {/* Custom zone inputs (shown when toggle is off) */}
            {showCustomZones && (
                <div className="space-y-5">
                    {/* HR Zones */}
                    <div>
                        <h3 className="text-sm font-medium text-slate-700 mb-2">Heart Rate Zones (bpm)</h3>
                        <div className="space-y-2">
                            {hrZones.map((zone: any, i: number) => (
                                <div key={zone.zone} className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 w-24 shrink-0">
                                        Z{zone.zone} {zone.description}
                                    </span>
                                    <input
                                        type="number"
                                        min={0}
                                        max={250}
                                        placeholder="Low"
                                        value={zone.lowBoundary_bpm || ''}
                                        onChange={e => updateHrZone(i, 'lowBoundary_bpm', parseInt(e.target.value) || 0)}
                                        className="w-20 p-1.5 border border-slate-300 rounded text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                    <span className="text-xs text-slate-400">-</span>
                                    <input
                                        type="number"
                                        min={0}
                                        max={250}
                                        placeholder="High"
                                        value={zone.highBoundary_bpm || ''}
                                        onChange={e => updateHrZone(i, 'highBoundary_bpm', parseInt(e.target.value) || 0)}
                                        className="w-20 p-1.5 border border-slate-300 rounded text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                    <span className="text-xs text-slate-400">bpm</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Pace Zones */}
                    <div>
                        <h3 className="text-sm font-medium text-slate-700 mb-1">
                             {effectiveSport === Sport.SWIMMING ? 'Swim Pace Zones (per 100m)' : 'Pace Zones (per km)'}
                         </h3>
                         <p className="text-xs text-slate-500 mb-2">
                             Enter the lower boundary pace for each zone as min:sec
                             {effectiveSport === Sport.SWIMMING ? ' per 100m' : ' per km'}.
                            Slower paces for lower zones, faster for higher.
                        </p>
                        <div className="space-y-2">
                            {paceZones.map((zone: any, i: number) => {
                                const displayValue = effectiveSport === Sport.SWIMMING
                                    ? msToMinPer100m(zone.lowBoundary_m_s)
                                    : msToMinPerKm(zone.lowBoundary_m_s);
                                return (
                                    <div key={zone.zone} className="flex items-center gap-2">
                                        <span className="text-xs text-slate-500 w-24 shrink-0">
                                            Z{zone.zone} {zone.description}
                                        </span>
                                        <input
                                            type="text"
                                            placeholder={effectiveSport === Sport.SWIMMING ? '2:00' : '6:00'}
                                            defaultValue={displayValue}
                                            onBlur={e => updatePaceZone(i, e.target.value)}
                                            className="w-20 p-1.5 border border-slate-300 rounded text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                        <span className="text-xs text-slate-400">
                                             {effectiveSport === Sport.SWIMMING ? '/100m' : '/km'}
                                         </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
