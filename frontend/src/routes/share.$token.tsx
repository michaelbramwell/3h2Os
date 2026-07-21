import { useState, useEffect } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import type { Activity, HrZone } from '../types/schema';
import { ActivityType } from '../types/schema';
import { formatPace, formatSwimPace, formatDistance } from '../lib/formatters';
import { AppBrand, AppDescription, AppFooter } from '../components/AppShell';
import { formatCalendarDate } from '../lib/dateTime';

export const Route = createFileRoute('/share/$token')({
    component: SharePage,
});

// --------------------------------------------------------------------------
// Helpers shared with ActivityModal (duplicated to keep share page standalone
// and avoid coupling to modal-specific code)
// --------------------------------------------------------------------------

function isType(actual: string | undefined, expected: string): boolean {
    return actual?.toLowerCase() === expected.toLowerCase();
}

function getTEData(score: number): { label: string; color: string } {
    if (score < 1.0) return { label: 'None', color: 'text-slate-500 bg-slate-200 ring-slate-300' };
    if (score < 2.0) return { label: 'Minor', color: 'text-blue-600 bg-blue-50 ring-blue-200' };
    if (score < 3.0) return { label: 'Main', color: 'text-emerald-600 bg-emerald-50 ring-emerald-200' };
    if (score < 4.0) return { label: 'Impr', color: 'text-amber-600 bg-amber-50 ring-amber-200' };
    if (score < 5.0) return { label: 'High', color: 'text-orange-600 bg-orange-50 ring-orange-200' };
    return { label: 'Over', color: 'text-red-600 bg-red-50 ring-red-200' };
}

function ZoneList({ zones, type, activityType, derived }: {
    zones?: HrZone[];
    type: 'pace' | 'hr' | 'power';
    activityType?: string;
    derived?: boolean;
}) {
    if (!zones || zones.length === 0) return null;
    const active = zones.filter(z => (z.secsInZone || 0) > 10);
    if (active.length === 0) return null;

    return (
        <div className="space-y-0.5">
            {active.map((z, idx) => {
                const mins = Math.floor(z.secsInZone / 60);
                const secs = Math.round(z.secsInZone % 60);
                const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
                const low = z.zoneLow ?? z.zoneLowBoundary ?? 0;
                const high = z.zoneHigh ?? z.zoneHighBoundary ?? 0;

                let valStr = '';
                if (type === 'pace') {
                    const isSwim = isType(activityType, ActivityType.SWIMMING);
                    const highIsOpen = high <= 0 || high >= 99999;
                    if (z.avgValue && z.avgValue > 0) {
                        valStr = isSwim
                            ? formatSwimPace(z.avgValue)
                            : formatPace(1000 / z.avgValue);
                    } else if (low > 0 || !highIsOpen) {
                        const lowPace = low > 0 ? (isSwim ? formatSwimPace(low) : formatPace(1000 / low)) : '';
                        const highPace = !highIsOpen ? (isSwim ? formatSwimPace(high) : formatPace(1000 / high)) : '';
                        if (lowPace && highPace) valStr = `${lowPace} - ${highPace}`;
                        else if (highPace) valStr = `< ${highPace}`;
                        // Top (fastest) zone: only a low-speed boundary exists; paces
                        // faster than this boundary have lower min/km values, so < not >
                        else if (lowPace) valStr = `< ${lowPace}`;
                    }
                } else if (z.avgValue && z.avgValue > 0) {
                    valStr = Math.round(z.avgValue) + (type === 'hr' ? 'bpm' : type === 'power' ? 'W' : '');
                } else if (type === 'hr') {
                    if (low > 0 || high > 0) {
                        valStr = high > 0 ? `${Math.round(low)}-${Math.round(high)}` : `${Math.round(low)}+`;
                    }
                } else if (type === 'power') {
                    if (low > 0 || high > 0) {
                        valStr = high > 0 ? `${Math.round(low)}-${Math.round(high)} W` : `${Math.round(low)}+ W`;
                    }
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

function SplitsList({ splits, activityType }: { splits?: any[]; activityType?: string }) {
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

// --------------------------------------------------------------------------
// Page component
// --------------------------------------------------------------------------

type PageState =
    | { status: 'loading' }
    | { status: 'not_found' }
    | { status: 'error'; message: string }
    | { status: 'loaded'; activity: Activity };

function resolveApiBase(): string {
    // Mirror the same logic as api.ts so requests reach the backend in both
    // local dev (port 8000) and production (same origin as the frontend).
    return (
        import.meta.env.VITE_API_URL ||
        (window.location.hostname === 'localhost'
            ? 'http://localhost:8000'
            : window.location.origin)
    );
}

function SharePage() {
    const { token } = Route.useParams();
    const [state, setState] = useState<PageState>({ status: 'loading' });

    useEffect(() => {
        const base = resolveApiBase();
        fetch(`${base}/api/share/${token}`)
            .then(async res => {
                if (res.status === 404) {
                    setState({ status: 'not_found' });
                    return;
                }
                if (!res.ok) {
                    setState({ status: 'error', message: `Server error ${res.status}` });
                    return;
                }
                const data: Activity = await res.json();
                setState({ status: 'loaded', activity: data });
            })
            .catch(err => {
                setState({ status: 'error', message: err.message ?? 'Network error' });
            });
    }, [token]);

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col">
            {/* Header */}
            <header className="bg-white border-b border-slate-100 px-4 py-4">
                <div className="max-w-lg mx-auto flex items-center justify-between">
                    <a href="/" className="hover:opacity-80 transition-opacity">
                        <AppBrand />
                    </a>
                    <a
                        href="/"
                        className="text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
                    >
                        Sign in
                    </a>
                </div>
            </header>

            {/* Body */}
            <main className="flex-1 px-4 py-8">
                <div className="max-w-lg mx-auto">
                    {state.status === 'loading' && (
                        <div className="text-center py-16 text-slate-400 text-sm">Loading activity...</div>
                    )}

                    {state.status === 'not_found' && (
                        <div className="text-center py-16 space-y-2">
                            <p className="text-slate-700 font-semibold">Activity not found</p>
                            <p className="text-slate-400 text-sm">This share link may be invalid or the activity may have been deleted.</p>
                        </div>
                    )}

                    {state.status === 'error' && (
                        <div className="text-center py-16 space-y-2">
                            <p className="text-slate-700 font-semibold">Something went wrong</p>
                            <p className="text-slate-400 text-sm">{state.message}</p>
                        </div>
                    )}

                    {state.status === 'loaded' && <ActivityDetail activity={state.activity} />}
                </div>
            </main>

            {/* About blurb */}
            <section className="bg-white border-t border-slate-100 px-4 py-8">
                <div className="max-w-lg mx-auto space-y-4">
                    <AppDescription />
                    <div className="flex items-center gap-4 text-xs text-slate-400">
                        <a href="/" className="hover:underline">Home</a>
                        <a href="/" className="hover:underline">Sign in</a>
                        <a href="/privacy" className="hover:underline">Privacy policy</a>
                    </div>
                    <AppFooter />
                </div>
            </section>
        </div>
    );
}

function ActivityDetail({ activity }: { activity: Activity }) {
    const dateStr = formatCalendarDate(activity.date, {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    });
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

    const aeScore = activity.aerobic_te ?? null;
    const anScore = activity.anaerobic_te ?? null;
    const hasTE = aeScore !== null || anScore !== null;
    const aeData = aeScore !== null ? getTEData(aeScore) : null;
    const anData = anScore !== null ? getTEData(anScore) : null;

    const displayName = activity.custom_name ?? activity.name
    const sourceNameDiffers = !!activity.custom_name && activity.custom_name !== activity.name

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            {/* Activity header */}
            <div className="p-6 border-b border-slate-100">
                <h1 className="text-xl font-bold text-slate-900">{displayName}</h1>
                <p className="text-sm text-slate-500 mt-0.5">
                    {dateStr} &bull; {activity.type}
                    {sourceNameDiffers && activity.name && (
                        <span className="text-slate-400"> &bull; originally "{activity.name}"</span>
                    )}
                </p>
            </div>

            <div className="p-6 space-y-6">
                {/* Top stats */}
                <div className="grid grid-cols-3 gap-4">
                    <div className="bg-slate-50 p-3 rounded-lg">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Distance</div>
                        <div className="text-lg font-black text-slate-900">{distKm}k</div>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Avg Pace</div>
                        <div className="text-lg font-black text-slate-900">
                            {paceValue}
                            <span className="text-xs text-slate-400 font-normal ml-0.5">{paceLabel}</span>
                        </div>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Avg HR</div>
                        <div className="text-lg font-black text-slate-900">
                            {activity.average_hr ? Math.round(activity.average_hr) : '--'} bpm
                        </div>
                    </div>
                </div>

                {/* Load & Effect */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-50 p-3 rounded-lg">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Training Load</div>
                        <div className="text-lg font-black text-slate-900">{Math.round(activity.training_load || 0)}</div>
                    </div>
                    {hasTE && (
                    <div className="bg-slate-50 p-3 rounded-lg">
                        <div className="text-[10px] font-bold text-slate-400 uppercase mb-2">Training Effect</div>
                        <div className="grid grid-cols-1 gap-2">
                            {aeScore !== null && aeData && (
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-black text-slate-700 w-8">Ae</span>
                                    <span className="text-sm font-bold text-slate-900">{aeScore.toFixed(1)}</span>
                                </div>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${aeData.color}`}>
                                    {aeData.label}
                                </span>
                            </div>
                            )}
                            {anScore !== null && anData && (
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-black text-slate-700 w-8">An</span>
                                    <span className="text-sm font-bold text-slate-900">{anScore.toFixed(1)}</span>
                                </div>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${anData.color}`}>
                                    {anData.label}
                                </span>
                            </div>
                            )}
                        </div>
                    </div>
                    )}
                </div>

                {/* Zones & splits */}
                <div className="space-y-6">
                    {activity.pace_zones && activity.pace_zones.length > 0 && (
                        <div>
                            <div className="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                                <h4 className="text-[10px] font-black uppercase text-slate-400 tracking-wider">Pace Zones</h4>
                                <span className="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                            </div>
                            <ZoneList zones={activity.pace_zones} type="pace" activityType={activity.type} />
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
    );
}
