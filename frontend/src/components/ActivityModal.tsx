import { createPortal } from 'react-dom';
import type { Activity, HrZone } from '../types/schema';

interface ActivityModalProps {
    activity: Activity | null;
    onClose: () => void;
}

// Helper: Format Pace (min/km)
function formatPace(secondsPerKm: number | undefined): string {
    if (!secondsPerKm || isNaN(secondsPerKm) || secondsPerKm === Infinity) return '--:--';
    let mins = Math.floor(secondsPerKm / 60);
    let secs = Math.round(secondsPerKm % 60);
    if (secs === 60) {
        mins++;
        secs = 0;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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

function ZoneList({ zones, type }: { zones?: HrZone[], type: 'pace' | 'hr' | 'power' }) {
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
                     if (z.avgValue && z.avgValue > 0) {
                        valStr = formatPace(1000 / z.avgValue);
                     } else if (low > 0 || high > 0) {
                        // Fallback: Use zone boundaries
                        // Note: Zone 1 is slowest. 
                        // Z1 Low Boundary = 0.5 m/s. High Boundary = 2.6 m/s.
                        // Pace: 1000/0.5 = 2000s/km (33:00/km) -> 1000/2.6 (6:24/km)
                        if (lowPace && highPace) valStr = `${lowPace} - ${highPace}`;
                        else if (highPace) valStr = `< ${highPace}`; // Faster than X
                        else if (lowPace) valStr = `> ${lowPace}`; // Slower than Y
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
        </div>
    );
}

export function ActivityModal({ activity, onClose }: ActivityModalProps) {
    if (!activity) return null;

    const dateStr = new Date(activity.date).toLocaleDateString('en-AU', { weekday: 'long', day: 'numeric', month: 'long' });
    const distKm = (activity.distance_m / 1000).toFixed(2);
    const paceMinKm = activity.average_pace_m_s && activity.average_pace_m_s > 0 
        ? formatPace(1000 / activity.average_pace_m_s) 
        : '--:--';
    
    // Training Effect
    const aeScore = activity.aerobic_te || 0;
    const anScore = activity.anaerobic_te || 0;
    const aeData = getTEData(aeScore);
    const anData = getTEData(anScore);

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
                            <div className="text-lg font-black text-slate-900">{paceMinKm}/k</div>
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
                        {activity.pace_zones && activity.pace_zones.length > 0 && (
                            <div>
                                <div className="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                                    <h4 className="text-[10px] font-black uppercase text-slate-400 tracking-wider">Pace Zones</h4>
                                    <span className="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                                </div>
                                <ZoneList zones={activity.pace_zones} type="pace" />
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
                    </div>
                </div>
            </div>
        </div>,
        document.body
    );
}
