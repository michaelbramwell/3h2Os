import { createPortal } from 'react-dom';
import type { Activity, HrZone, ContextData, TrainingZone } from '../types/schema';
import { ActivityType } from '../types/schema';
import { formatPace, formatSwimPace, formatDistance } from '../lib/formatters';

/** Case-insensitive activity type check (backend stores lowercase, frontend enum is TitleCase). */
function isType(actual: string | undefined, expected: string): boolean {
    return actual?.toLowerCase() === expected.toLowerCase();
}

interface ActivityModalProps {
    activity: Activity | null;
    context?: ContextData;
    onClose: () => void;
}

// Helper: Get Training Effect Data (colors)
function getTEData(score: number): { label: string; color: string } {
    if (score < 1.0) return { label: 'None', color: 'text-slate-500 bg-slate-200 ring-slate-300' };
    if (score < 2.0) return { label: 'Minor', color: 'text-blue-600 bg-blue-50 ring-blue-200' };
    if (score < 3.0) return { label: 'Main', color: 'text-emerald-600 bg-emerald-50 ring-emerald-200' };
    if (score < 4.0) return { label: 'Impr', color: 'text-amber-600 bg-amber-50 ring-amber-200' };
    if (score < 5.0) return { label: 'High', color: 'text-orange-600 bg-orange-50 ring-orange-200' };
    return { label: 'Over', color: 'text-red-600 bg-red-50 ring-red-200' };
}

/**
 * Derives HrZone-shaped pace zone buckets from splits + training zone thresholds.
 * Each split's averageSpeed (m/s) is classified into the appropriate zone.
 * Returns one entry per zone that had at least one split, with:
 *   - secsInZone: total time of matching splits
 *   - avgValue: distance-weighted average speed (m/s) across matching splits
 *   - zoneLow / zoneHigh: speed boundaries (m/s)
 */
function derivePaceZonesFromSplits(
    splits: Record<string, any>[],
    thresholds: TrainingZone[]
): HrZone[] {
    if (!splits?.length || !thresholds?.length) return [];

    const sorted = [...thresholds].sort((a, b) => (a.lowBoundary_m_s ?? 0) - (b.lowBoundary_m_s ?? 0));

    // Build zone boundary pairs
    const zones = sorted.map((t, i) => ({
        zone: t.zone,
        low: t.lowBoundary_m_s ?? 0,
        high: sorted[i + 1]?.lowBoundary_m_s ?? Infinity,
    }));

    // Accumulators per zone number
    const acc: Record<number, { secs: number; distWeightedSpeed: number; totalDist: number; low: number; high: number }> = {};
    for (const z of zones) {
        acc[z.zone] = { secs: 0, distWeightedSpeed: 0, totalDist: 0, low: z.low, high: z.high };
    }

    for (const split of splits) {
        const speed: number = split.averageSpeed;
        const dist: number = split.distance ?? 1000;
        if (!speed || speed <= 0) continue;

        // Find matching zone (highest lower boundary that speed exceeds)
        let matched: number | null = null;
        for (const z of [...zones].reverse()) {
            if (speed >= z.low) { matched = z.zone; break; }
        }
        if (matched === null) matched = zones[0].zone; // below all thresholds → Z1

        const splitSecs = dist / speed;
        acc[matched].secs += splitSecs;
        acc[matched].distWeightedSpeed += speed * dist;
        acc[matched].totalDist += dist;
    }

    return zones
        .filter(z => acc[z.zone].secs > 0)
        .map(z => {
            const data = acc[z.zone];
            return {
                zoneNumber: z.zone,
                secsInZone: Math.round(data.secs),
                avgValue: data.totalDist > 0 ? data.distWeightedSpeed / data.totalDist : 0,
                zoneLow: data.low,
                zoneHigh: data.high === Infinity ? 0 : data.high,
                percentInZone: 0,
            };
        });
}

function ZoneList({ zones, type, activityType, derived }: { zones?: HrZone[], type: 'pace' | 'hr' | 'power', activityType?: string, derived?: boolean }) {
    if (!zones || zones.length === 0) return null;

    const active = zones.filter(z => (z.secsInZone || 0) > 10);
    if (active.length === 0) return null;

    return (
        <div className="space-y-0.5">
            {active.map((z, idx) => {
                const mins = Math.floor(z.secsInZone / 60);
                const secs = Math.round(z.secsInZone % 60);
                const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
                
                // Helper to resolve potentially aliased boundaries
                const low = z.zoneLow ?? z.zoneLowBoundary ?? 0;
                const high = z.zoneHigh ?? z.zoneHighBoundary ?? 0;

                let valStr = '';
                
                if (type === 'pace') {
                     const isSwim = isType(activityType, ActivityType.SWIMMING);
                     
                     if (z.avgValue && z.avgValue > 0) {
                        valStr = isSwim 
                            ? formatSwimPace(z.avgValue)
                            : formatPace(1000 / z.avgValue);
                     } else if (low > 0 || high > 0) {
                        const lowPace = low > 0 
                            ? (isSwim ? formatSwimPace(low) : formatPace(1000 / low)) 
                            : ''; 
                        const highPace = high > 0 
                            ? (isSwim ? formatSwimPace(high) : formatPace(1000 / high)) 
                            : '';

                        // Fallback: Use zone boundaries
                        if (lowPace && highPace) valStr = `${lowPace} - ${highPace}`;
                        else if (highPace) valStr = `< ${highPace}`;
                        else if (lowPace) valStr = `< ${lowPace}`; // Top zone: faster than this pace
                     }
                } else if (z.avgValue && z.avgValue > 0) {
                     valStr = Math.round(z.avgValue) + (type === 'hr' ? 'bpm' : (type === 'power' ? 'W' : ''));
                } else if (type === 'hr') {
                    valStr = `${Math.round(low)}-${Math.round(high)}`;
                } else if (type === 'power') {
                    valStr = `${Math.round(low)}-${Math.round(high)} W`;
                }

                return (
                    <div key={idx} className="grid grid-cols-3 gap-2 border-b border-slate-50 py-1 last:border-0 items-center">
                        <div className="text-[10px] font-black italic text-slate-400">Z{z.zoneNumber}</div>
                        <div className="text-xs font-bold text-slate-700 font-mono">{valStr}</div>
                        <div className="text-[10px] text-slate-500 text-right">{timeStr}</div>
                    </div>
                );
            })}
            {derived && (
                <div className="text-[9px] text-slate-300 pt-1">derived from splits</div>
            )}
        </div>
    );
}

function SplitsList({ splits, activityType }: { splits?: any[], activityType?: string }) {
    if (!splits || splits.length === 0) return null;

    const isSwim = isType(activityType, ActivityType.SWIMMING);

    return (
        <div className="space-y-0.5">
             <div className="grid grid-cols-4 gap-2 border-b border-slate-100 py-1 text-[9px] font-bold uppercase text-slate-400 text-right">
                <div className="text-left font-black">#</div>
                <div>Dist</div>
                <div>Pace</div>
                <div>HR</div>
            </div>
            {splits.map((split, idx) => {
                const dist = formatDistance(split.distance, 2);
                const pace = split.averageSpeed 
                    ? (isSwim ? formatSwimPace(split.averageSpeed) : formatPace(1000 / split.averageSpeed)) 
                    : '--:--';
                const hr = split.averageHR ? Math.round(split.averageHR) : '-';
                
                return (
                    <div key={idx} className="grid grid-cols-4 gap-2 border-b border-slate-50 py-1 last:border-0 items-center text-xs text-right">
                        <div className="text-[10px] font-black italic text-slate-400 text-left">{idx + 1}</div>
                        <div className="font-bold text-slate-700 font-mono">{dist}</div>
                        <div className="font-bold text-slate-700 font-mono">{pace}</div>
                        <div className="text-slate-500">{hr}</div>
                    </div>
                );
            })}
        </div>
    );
}

export function ActivityModal({ activity, context, onClose }: ActivityModalProps) {
    if (!activity) return null;

    const dateStr = new Date(activity.date).toLocaleDateString('en-AU', { weekday: 'long', day: 'numeric', month: 'long' });
    const distKm = formatDistance(activity.distance_m, 2);
    const isSwim = isType(activity.type, ActivityType.SWIMMING);
    
    let paceLabel = '/k';
    let paceValue = '--:--';

    if (activity.average_pace_m_s && activity.average_pace_m_s > 0) {
        if (isSwim) {
            paceValue = formatSwimPace(activity.average_pace_m_s);
            paceLabel = '/100m';
        } else {
            paceValue = formatPace(1000 / activity.average_pace_m_s);
        }
    }
    
    // Training Effect
    const aeScore = activity.aerobic_te || 0;
    const anScore = activity.anaerobic_te || 0;
    const aeData = getTEData(aeScore);
    const anData = getTEData(anScore);

    // Resolve pace zones: prefer telemetry-enriched zones, fall back to split-derived zones.
    const isRunning = isType(activity.type, ActivityType.RUN) || isType(activity.type, ActivityType.TRAIL);
    const telemetryPaceZones = activity.pace_zones && activity.pace_zones.length > 0 ? activity.pace_zones : null;
    const paceThresholds = context?.runner?.trainingZones?.pace?.length
        ? context.runner.trainingZones.pace
        : undefined;
    const derivedPaceZones = !telemetryPaceZones && isRunning && activity.splits?.length && paceThresholds?.length
        ? derivePaceZonesFromSplits(activity.splits, paceThresholds)
        : null;
    const resolvedPaceZones = telemetryPaceZones ?? derivedPaceZones ?? null;
    const paceZonesDerived = !telemetryPaceZones && !!derivedPaceZones;

    return createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div 
                className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            ></div>

            {/* Modal */}
            <div className="relative bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-white z-10 sticky top-0">
                    <div>
                        <h2 className="text-xl font-bold text-slate-900">{activity.name}</h2>
                        <p className="text-sm text-slate-500">{dateStr} • {activity.type}</p>
                    </div>
                    <button 
                        onClick={onClose}
                        className="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
                    {/* Top Stats Grid */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <div className="text-[10px] font-bold text-slate-400 uppercase">Distance</div>
                            <div className="text-lg font-black text-slate-900">{distKm}k</div>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <div className="text-[10px] font-bold text-slate-400 uppercase">Avg Pace</div>
                            <div className="text-lg font-black text-slate-900">{paceValue}<span className="text-xs text-slate-400 font-normal ml-0.5">{paceLabel}</span></div>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <div className="text-[10px] font-bold text-slate-400 uppercase">Avg HR</div>
                            <div className="text-lg font-black text-slate-900">{activity.average_hr ? Math.round(activity.average_hr) : '--'} bpm</div>
                        </div>
                    </div>

                    {/* Load & Effect Grid */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <div className="text-[10px] font-bold text-slate-400 uppercase">Training Load</div>
                            <div className="text-lg font-black text-slate-900">{Math.round(activity.training_load || 0)}</div>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <div className="text-[10px] font-bold text-slate-400 uppercase mb-2">Training Effect</div>
                            <div className="grid grid-cols-1 gap-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs font-black text-slate-700 w-8">Ae</span>
                                        <span className="text-sm font-bold text-slate-900">{aeScore.toFixed(1)}</span>
                                    </div>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${aeData.color}`}>
                                        {aeData.label}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs font-black text-slate-700 w-8">An</span>
                                        <span className="text-sm font-bold text-slate-900">{anScore.toFixed(1)}</span>
                                    </div>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${anData.color}`}>
                                        {anData.label}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Zones Sections */}
                    <div className="space-y-6">
                        {resolvedPaceZones && resolvedPaceZones.length > 0 && (
                            <div>
                                <div className="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                                    <h4 className="text-[10px] font-black uppercase text-slate-400 tracking-wider">Pace Zones</h4>
                                    <span className="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                                </div>
                                <ZoneList zones={resolvedPaceZones} type="pace" activityType={activity.type} derived={paceZonesDerived} />
                            </div>
                        )}

                        {activity.hr_zones && activity.hr_zones.length > 0 && (
                            <div>
                                <div className="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                                    <h4 className="text-[10px] font-black uppercase text-slate-400 tracking-wider">Heart Rate Zones</h4>
                                    <span className="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                                </div>
                                <ZoneList zones={activity.hr_zones} type="hr" />
                            </div>
                        )}
                        
                        {activity.power_zones && activity.power_zones.length > 0 && (
                             <div>
                                <div className="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                                    <h4 className="text-[10px] font-black uppercase text-slate-400 tracking-wider">Power Zones</h4>
                                    <span className="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                                </div>
                                <ZoneList zones={activity.power_zones} type="power" />
                            </div>
                        )}

                        {activity.splits && activity.splits.length > 0 && (
                             <div>
                                <div className="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                                    <h4 className="text-[10px] font-black uppercase text-slate-400 tracking-wider">Splits</h4>
                                </div>
                                <SplitsList splits={activity.splits} activityType={activity.type} />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>,
        document.body
    );
}
