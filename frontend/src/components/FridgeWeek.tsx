import type { Week } from '../types/schema'

interface FridgeWeekProps {
  week: Week;
  weekIndex: number;
}

export function FridgeWeek({ week, weekIndex }: FridgeWeekProps) {
    const dateStr = new Date(week.weekStarting).toLocaleDateString('en-AU', { month: 'long', day: 'numeric', year: 'numeric' });
    const dayOrder = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    return (
        <div id="print-section" className="p-6 border-4 border-slate-900 min-h-screen bg-white text-sm print:border-4 print:p-6">
            <div className="flex justify-between items-baseline mb-6 border-b-4 border-slate-900 pb-3">
                <h1 className="text-3xl font-black uppercase">Week {weekIndex + 1}</h1>
                <p className="text-lg font-bold text-slate-600">Starting {dateStr}</p>
            </div>

            <div className="space-y-3">
                {dayOrder.map(dayName => {
                    const dayData = week.days[dayName];
                    if (!dayData) return null;
                    
                    const workouts = dayData.workouts || [];
                    const date = new Date(dayData.date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' });
                    
                    return (
                        <div key={dayName} className="flex items-start gap-6 border-b border-slate-100 pb-2">
                            <div className="w-20 flex-shrink-0">
                                <p className="text-lg font-black uppercase leading-none">{dayName}</p>
                                <p className="text-[11px] font-bold text-slate-400 mt-1">{date}</p>
                            </div>
                            <div className="flex-grow">
                                {workouts.length > 0 ? workouts.map((w, idx) => (
                                    <div key={idx} className={`flex items-center gap-3 ${idx < workouts.length - 1 ? 'mb-4 pb-4 border-b border-dashed border-slate-200' : 'mb-1'}`}>
                                        <div className="w-6 h-6 border-2 border-slate-900 flex-shrink-0"></div>
                                        <div>
                                            <p className="text-[11px] font-black uppercase text-slate-400 leading-none mb-1">{w.timeOfDay || 'AM'}</p>
                                            <p className="text-lg font-black leading-tight">{w.name}</p>
                                            <div className="text-xs text-slate-500 mt-0.5">{w.type} • {(w.distance_m / 1000).toFixed(1)}km</div>
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

            <div className="mt-8 grid grid-cols-2 gap-8 pt-6 border-t-4 border-slate-900">
                <div>
                    <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">Paces</h3>
                    <p className="font-bold">Easy: 5:45-6:15 | Steady: 5:10-5:20</p>
                    <p className="font-bold">MP: 5:30-5:40 | <span className="text-red-600">Threshold: 4:40-4:50</span></p>
                </div>
                <div>
                    <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">90/900 Rule</h3>
                    <p className="font-bold text-base">90g Carbs + 900mg Sodium / hr</p>
                    <p className="italic text-slate-500 text-xs">Practice on Sunday PLR.</p>
                </div>
            </div>
            
            <div className="mt-6">
                <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">Notes / Vitals</h3>
                <div className="h-20 w-full border-2 border-dashed border-slate-200"></div>
            </div>
        </div>
    );
}
