import type { Week, ContextData } from '../types/schema'
import { formatPace, formatDistance } from '../lib/formatters'
import { calculateWeekVolume, getZoneLabel } from '../lib/calculations'

interface FridgeWeekProps {
  week: Week;
  weekIndex: number;
  context?: ContextData;
}

export function FridgeWeek({ week, weekIndex, context }: FridgeWeekProps) {
    const dateStr = new Date(week.weekStarting).toLocaleDateString('en-AU', { month: 'long', day: 'numeric', year: 'numeric' });
    const dayOrder = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    const totalTargetM = calculateWeekVolume(week);

    // Zone Logic
    let easyLabel = "Easy: 5:45-6:15";
    let tempoLabel = "Tempo: 4:50-5:20";
    let thresholdLabel = "Threshold: 4:40-4:50";
    let vo2Label = "VO2 Max: < 4:40";
    
    // MP is derived or hardcoded for now, assuming 3h20ish goal (4:44/km)
    const mpLabel = "MP: 5:30-5:40"; 

    if (context?.runner?.trainingZones?.pace) {
        const zones = context.runner.trainingZones.pace;
        easyLabel = getZoneLabel('Easy', zones).replace('Easy (Z2): ', 'Easy (Z2): '); // Keep pure string or format if needed
        tempoLabel = getZoneLabel('Tempo', zones);
        thresholdLabel = getZoneLabel('Threshold', zones);
        vo2Label = getZoneLabel('VO2 Max', zones);
   }


    return (
        <div id="print-section" className="p-6 border-4 border-slate-900 min-h-screen bg-white text-sm print:border-2 print:p-4 print:min-h-0 print:text-xs">
            <div className="flex justify-between items-end mb-6 border-b-4 border-slate-900 pb-3 print:mb-2 print:pb-2 print:border-b-2">
                <div>
                    <div className="flex items-baseline gap-3">
                        <h1 className="text-3xl font-black uppercase print:text-2xl">Week {weekIndex + 1}</h1>
                        <span className="text-2xl font-bold text-slate-400 print:text-xl">{formatDistance(totalTargetM, 0)}km</span>
                    </div>
                </div>
                <p className="text-lg font-bold text-slate-600">Starting {dateStr}</p>
            </div>

            <div className="space-y-3 print:space-y-1">
                {dayOrder.map(dayName => {
                    const dayData = week.days[dayName];
                    if (!dayData) return null;
                    
                    const workouts = dayData.workouts || [];
                    const date = new Date(dayData.date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' });
                    
                    return (
                        <div key={dayName} className="flex items-start gap-6 border-b border-slate-100 pb-2 print:gap-4 print:pb-1">
                            <div className="w-20 flex-shrink-0 print:w-16">
                                <p className="text-lg font-black uppercase leading-none print:text-base">{dayName}</p>
                                <p className="text-[11px] font-bold text-slate-400 mt-1 print:text-[10px]">{date}</p>
                            </div>
                            <div className="flex-grow">
                                {workouts.length > 0 ? workouts.map((w, idx) => (
                                    <div key={idx} className={`flex items-center gap-3 ${idx < workouts.length - 1 ? 'mb-4 pb-4 border-b border-dashed border-slate-200 print:mb-2 print:pb-2' : 'mb-1'}`}>
                                        <div className="w-6 h-6 border-2 border-slate-900 flex-shrink-0 print:w-4 print:h-4 print:border-1.5"></div>
                                        <div>
                                            <p className="text-[11px] font-black uppercase text-slate-400 leading-none mb-1 print:text-[9px]">{w.timeOfDay || 'AM'}</p>
                                            <p className="text-lg font-black leading-tight print:text-sm">{w.name}</p>
                                            <div className="text-xs text-slate-500 mt-0.5 print:text-[10px]">{w.type} • {formatDistance(w.distance_m)}km</div>
                                            {w.description && (
                                                <p className="text-xs font-serif italic text-slate-600 mt-1 max-w-prose leading-snug">
                                                    {w.description}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                )) : (
                                    <div className="flex items-center gap-3">
                                        <div className="w-6 h-6 border border-slate-200 flex-shrink-0"></div>
                                        <p className="text-base font-bold text-slate-300 uppercase italic">Rest Day</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="mt-8 grid grid-cols-2 gap-8 pt-6 border-t-4 border-slate-900 print:mt-4 print:pt-2 print:border-t-2 print:gap-4">
                <div>
                    <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2 print:mb-1">Paces</h3>
                    <p className="font-bold print:leading-tight">{easyLabel} | {tempoLabel}</p>
                    <p className="font-bold print:leading-tight">{mpLabel} | <span className="text-red-600">{thresholdLabel}</span></p>
                    <p className="font-bold print:leading-tight text-purple-600">{vo2Label}</p>
                </div>
                <div>
                    <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2 print:mb-1">90/900 Rule</h3>
                    <p className="font-bold text-base print:text-sm">90g Carbs + 900mg Sodium / hr</p>
                    <p className="italic text-slate-500 text-xs">Practice on Sunday PLR.</p>
                </div>
            </div>
            
            <div className="mt-6 print:mt-2">
                <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2 print:mb-1">Notes / Vitals</h3>
                <div className="h-20 w-full border-2 border-dashed border-slate-200 print:h-12 print:border-1.5"></div>
            </div>
        </div>
    );
}
