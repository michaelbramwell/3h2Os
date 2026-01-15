import { useEffect, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { getPlan, getContext, getActuals, getContextMarkdown } from '../lib/api'
import { Sidebar } from '../components/Sidebar'
import { RecentActivities } from '../components/RecentActivities'
import { FridgeWeek } from '../components/FridgeWeek'
import { ActivityModal } from '../components/ActivityModal'
import { Printer, X } from 'lucide-react'
import type { ContextData, Week, Activity } from '../types/schema'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

function Dashboard() {
  const [fridgeWeekId, setFridgeWeekId] = useState<string | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

  useEffect(() => {
    if (fridgeWeekId) {
        // Allow time for render
        const timer = setTimeout(() => {
            window.print();
        }, 100);
        return () => clearTimeout(timer);
    }
  }, [fridgeWeekId]);

  const { data: plan, isLoading: planLoading, error: planError } = useQuery({ 
    queryKey: ['plan'], 
    queryFn: getPlan 
  })
  
  const { data: context, isLoading: contextLoading } = useQuery({ 
    queryKey: ['context'], 
    queryFn: getContext 
  })

  // Start with a safe default for actuals to avoid breaking if file missing/empty
  const { data: actuals } = useQuery({ 
    queryKey: ['actuals'], 
    queryFn: getActuals,
    initialData: [] 
  })

  const { data: markdown } = useQuery({ 
    queryKey: ['markdown'], 
    queryFn: getContextMarkdown,
    initialData: ''
  })

  if (planLoading || contextLoading) return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
          <div className="text-center">
              <div className="w-8 h-8 border-4 border-slate-200 border-t-orange-500 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-slate-500 font-medium">Loading training data...</p>
          </div>
      </div>
  )

  if (planError) return <div className="p-8 text-center text-red-500">Error loading plan: {planError.message}</div>
  if (!plan || !context) return null

  // Helper to determine week status color
  const getWeekStyle = (status: string, isCurrentWeek: boolean) => {
      const s = status?.toLowerCase() || 'normal';
      
      // Special Phases
      if (s.includes('marathon')) return 'bg-yellow-50/50 border-yellow-400 ring-2 ring-yellow-200 shadow-md';
      if (s.includes('race')) return 'bg-amber-50/50 border-amber-300 ring-1 ring-amber-100';
      if (s.includes('taper')) return 'bg-purple-50/30 border-purple-200';
      
      // Temporal States
      if (s === 'completed') return 'bg-slate-50 border-slate-200 opacity-70 grayscale-[0.5]'; 
      if (isCurrentWeek) return 'bg-white border-orange-400 ring-4 ring-orange-100 shadow-lg scale-[1.01]'; 

      return 'bg-white border-slate-200'; // upcoming/normal
  }

  // Filter if in Fridge Mode
  const visibleWeeks = fridgeWeekId 
    ? plan.filter((w: Week) => w.weekStarting === fridgeWeekId)
    : plan;

  const todayDate = new Date();
  const todayStr = todayDate.toISOString().split('T')[0];

  return (
    <div className={`min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8 font-sans ${fridgeWeekId ? 'bg-white print:p-0' : ''}`}>
      {fridgeWeekId && (
        <div className="fixed top-4 right-4 z-50 print:hidden">
            <button 
                onClick={() => setFridgeWeekId(null)}
                className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-full shadow-lg hover:bg-slate-700 transition"
            >
                <X size={16} /> Exit Fridge Mode
            </button>
        </div>
      )}

      <div className="max-w-[1600px] mx-auto">
        
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 xl:gap-8">
            
            {/* Sidebar Column - Hide in Fridge Mode */}
            {!fridgeWeekId && (
                <div className="lg:col-span-1 space-y-6">
                    <Sidebar context={context as ContextData} markdown={markdown} />
                    <RecentActivities activities={actuals as Activity[]} />
                </div>
            )}

            {/* Main Content Column */}
            <div className={`${fridgeWeekId ? 'col-span-1 lg:col-span-4 max-w-[210mm] mx-auto w-full' : 'lg:col-span-3'} space-y-6`}>
                {visibleWeeks.map((week: Week) => {
                    // Match original index in plan
                    const originalIndex = plan.findIndex((w: Week) => w.weekStarting === week.weekStarting);
                    
                    if (fridgeWeekId === week.weekStarting) {
                        return (
                            <div key={week.weekStarting}>
                                <FridgeWeek week={week} weekIndex={originalIndex} />
                            </div>
                        )
                    }

                    // Check if current week by seeing if today is in this week's days
                    const weekDatesSet = new Set(Object.values(week.days).map((d: any) => d.date));
                    const isCurrentWeek = weekDatesSet.has(todayStr);

                    const status = week.status?.toLowerCase() || 'normal';
                    const isCompleted = status === 'completed' || (!isCurrentWeek && new Date(week.weekStarting) < new Date(todayStr));
                    
                    const weekStyle = getWeekStyle(status, isCurrentWeek);
                    
                    // --- Stats Calculation ---
                    let weekTargetM = 0;
                    let weekRemainingM = 0;

                    // 1. Calculate Target & Remaining from Plan
                    Object.values(week.days).forEach((day: any) => {
                        if (day.workouts) {
                            day.workouts.forEach((w: any) => {
                                const dist = w.distance_m || 0;
                                weekTargetM += dist;
                                if (day.date > todayStr) {
                                    weekRemainingM += dist;
                                }
                            });
                        }
                    });

                    // 2. Calculate Actuals from Activity Log
                    const weekActuals = (actuals || []).filter((a: Activity) => weekDatesSet.has(a.date));
                    
                    let weekActualM = 0;
                    weekActuals.forEach(a => {
                         // Sum running types
                         if (a.type === 'running' || a.type === 'trail_running' || a.name.toLowerCase().includes('run')) {
                            weekActualM += (a.distance_m || 0);
                        }
                    });

                    const projectedM = weekActualM + weekRemainingM;
                    const diffM = projectedM - weekTargetM;
                    const diffKm = diffM / 1000;
                    
                    return (
                        <div 
                            key={week.weekStarting} 
                            className={`rounded-xl p-5 border shadow-sm transition-all duration-200 ${weekStyle}`}
                        >
                            <div className="sticky top-0 z-10 flex flex-col md:flex-row justify-between items-start md:items-center -mx-5 -mt-5 pt-5 px-5 pb-3 mb-4 border-b border-slate-100/50 gap-4 rounded-t-xl backdrop-blur-md bg-white/30">
                                <div>
                                    <h3 className={`text-lg font-bold ${isCurrentWeek ? 'text-orange-900' : 'text-slate-800'}`}>
                                        Week of {new Date(week.weekStarting).toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })}
                                        {(status === 'race' || status === 'marathon') && <span className="ml-2 text-yellow-600">🏆</span>}
                                        {status === 'taper' && <span className="ml-2 text-purple-600">📉</span>}
                                    </h3>
                                    {isCurrentWeek && <span className="inline-block px-2 py-0.5 mt-1 text-[10px] font-bold uppercase tracking-wider text-orange-600 bg-orange-100 rounded-full">Current Week</span>}
                                    {(status === 'race' || status === 'marathon') && <span className="ml-2 inline-block px-2 py-0.5 mt-1 text-[10px] font-bold uppercase tracking-wider text-yellow-700 bg-yellow-100 rounded-full">Race Week</span>}
                                    {status === 'taper' && <span className="ml-2 inline-block px-2 py-0.5 mt-1 text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-100 rounded-full">Taper</span>}
                                </div>
                                
                                {/* Progress Stats using flex for compact layout */}
                                <div className="flex gap-4 md:gap-8 bg-white/50 p-2 rounded-lg border border-slate-100 text-xs md:text-sm">
                                    <div className="text-center">
                                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Target</div>
                                        <div className="font-bold text-slate-700">{(weekTargetM / 1000).toFixed(0)}km</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Actual</div>
                                        <div className={`font-bold ${weekActualM > 0 ? 'text-green-600' : 'text-slate-300'}`}>{(weekActualM / 1000).toFixed(1)}km</div>
                                    </div>
                                    <div className="text-center border-l border-slate-200 pl-4">
                                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Projected</div>
                                        <div className="font-bold text-blue-600">{(projectedM / 1000).toFixed(1)}km</div>
                                    </div>
                                    <div className="text-center hidden sm:block">
                                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Diff</div>
                                        <div className={`font-bold ${diffKm >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                                            {diffKm > 0 ? '+' : ''}{diffKm.toFixed(1)}km
                                        </div>
                                    </div>
                                </div>

                                <div className="text-right hidden md:flex flex-col items-end gap-2">
                                     <span className={`text-xs font-bold uppercase tracking-wider px-2 py-1 rounded ${isCompleted ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                                        {status === 'normal' ? (isCompleted ? 'Completed' : 'Upcoming') : status}
                                     </span>
                                     
                                     {!fridgeWeekId && (
                                         <button 
                                            onClick={() => setFridgeWeekId(week.weekStarting)}
                                            className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider bg-slate-100 hover:bg-slate-200 text-slate-600 px-2 py-1 rounded transition-colors"
                                         >
                                            <Printer size={12} /> Fridge
                                         </button>
                                     )}
                                </div>
                            </div>
                            
                            {/* Days Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                                {Object.entries(week.days)
                                    .sort((a,b) => new Date(a[1].date).getTime() - new Date(b[1].date).getTime())
                                    .map(([dayName, day]: [string, any]) => {
                                    
                                    const dayActuals = (actuals || []).filter((a: Activity) => a.date === day.date);
                                    const hasWorkouts = day.workouts && day.workouts.length > 0;
                                    const isToday = day.date === todayStr;

                                    // Check special day types
                                    let dayStyle = isToday ? 'ring-2 ring-orange-500 shadow-md border-orange-200 bg-white' : 'border-slate-100 bg-white hover:border-blue-200';
                                    let dayBadge = isToday ? <div className="absolute top-0 right-0 bg-orange-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-bl-lg rounded-tr-lg z-10">TODAY</div> : null;

                                    // Check for Race/Marathon in Workouts
                                    let isRaceDay = false;
                                    let isMarathonDay = false;
                                    
                                    if (day.workouts) {
                                        day.workouts.forEach((w: any) => {
                                            if (w.type === 'Race') {
                                                if (status === 'marathon') isMarathonDay = true;
                                                else isRaceDay = true;
                                            }
                                        });
                                    }

                                    if (isMarathonDay) {
                                        dayStyle = 'bg-gradient-to-br from-yellow-50 to-amber-100 border-yellow-400 ring-4 ring-yellow-200 shadow-xl scale-[1.02] z-20';
                                        dayBadge = <div className="absolute top-0 right-0 bg-yellow-500 text-white text-[9px] font-bold px-2 py-1 rounded-bl-lg rounded-tr-lg z-10 shadow-sm flex items-center gap-1"><span>👑</span> RACE DAY</div>;
                                    } else if (isRaceDay) {
                                        dayStyle = 'bg-amber-50 border-amber-300 ring-2 ring-amber-100 shadow-md';
                                        dayBadge = <div className="absolute top-0 right-0 bg-amber-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-bl-lg rounded-tr-lg z-10 flex items-center gap-1"><span>🏁</span> RACE</div>;
                                    }


                                    return (
                                        <div key={dayName} className={`p-3 rounded-lg border flex flex-col h-full relative transition-all duration-300 ${dayStyle}`}>
                                            {dayBadge}
                                            
                                            <div className="flex justify-between items-start mb-2">
                                                <span className={`text-xs font-bold uppercase ${(isToday || isRaceDay || isMarathonDay) ? 'text-slate-800' : 'text-slate-400'}`}>{dayName}</span>
                                                <span className={`text-[10px] font-mono ${(isToday || isRaceDay || isMarathonDay) ? 'text-slate-700 font-bold' : 'text-slate-400'}`}>{new Date(day.date).getDate()}</span>
                                            </div>
                                            
                                            <div className="space-y-2 flex-grow">
                                                {!hasWorkouts && (
                                                    <div className="flex items-center justify-center py-4">
                                                        <span className="text-xs uppercase font-bold text-slate-300 tracking-wider">Rest Day</span>
                                                    </div>
                                                )}

                                                {/* Planned Workouts - Special Styling for Race Entries */}
                                                {day.workouts?.map((workout: any, idx: number) => {
                                                    const isRaceWorkout = workout.type === 'Race';
                                                    let workoutCardStyle = `bg-white p-2 rounded border border-slate-100 shadow-sm relative overflow-hidden group hover:border-blue-200 transition-colors cursor-default ${isToday ? 'bg-orange-50/30' : ''}`;
                                                    let borderBarColor = 'bg-blue-500';

                                                    if (isRaceWorkout && isMarathonDay) {
                                                        workoutCardStyle = 'bg-yellow-100/80 p-3 rounded-lg border-2 border-yellow-400 shadow-md relative overflow-hidden';
                                                        borderBarColor = 'bg-yellow-600';
                                                    } else if (isRaceWorkout) {
                                                        workoutCardStyle = 'bg-amber-100/50 p-2 rounded border border-amber-300 shadow-sm relative overflow-hidden';
                                                        borderBarColor = 'bg-amber-500';
                                                    }

                                                    return (
                                                        <div key={`plan-${idx}`} className={workoutCardStyle}>
                                                            <div className={`absolute left-0 top-0 bottom-0 w-1 ${borderBarColor}`}></div>
                                                            <div className={isRaceWorkout && isMarathonDay ? 'pl-3' : 'pl-2'}>
                                                                <div className={`font-bold ${isRaceWorkout && isMarathonDay ? 'text-lg uppercase text-yellow-900' : 'text-sm text-slate-700'} leading-tight`}>{workout.type}</div>
                                                                <div className={`${isRaceWorkout && isMarathonDay ? 'text-sm font-bold text-yellow-800' : 'text-xs text-slate-500'} mt-0.5 line-clamp-2`}>{workout.description || workout.name}</div>
                                                                <div className={`mt-1.5 flex gap-2 text-[10px] items-center font-mono ${isRaceWorkout ? 'text-slate-600' : 'text-slate-400'}`}>
                                                                    <span>{(workout.distance_m / 1000).toFixed(1)}km</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    );
                                                })}

                                                {/* Actuals */}
                                                {dayActuals.map((act: Activity, idx: number) => {
                                                    const paceMs = act.average_pace_m_s || 0;
                                                    const paceLabel = paceMs > 0 
                                                        ? `${Math.floor(1000 / paceMs / 60)}:${Math.floor((1000 / paceMs % 60)).toFixed(0).padStart(2,'0')}/km` 
                                                        : '-:--/km';

                                                    return (
                                                        <div 
                                                            key={`act-${idx}`} 
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setSelectedActivity(act);
                                                            }}
                                                            className="bg-emerald-50 p-2 rounded border border-emerald-100 shadow-sm relative overflow-hidden group hover:bg-emerald-100 hover:shadow-md transition-all cursor-pointer"
                                                        >
                                                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"></div>
                                                            <div className="pl-2">
                                                                <div className="font-bold text-[10px] text-emerald-600 uppercase tracking-wider mb-0.5">Actual {act.type === 'running' ? '🏃' : '✓'}</div>
                                                                <div className="font-bold text-sm text-slate-800 leading-tight">
                                                                    {(act.distance_m / 1000).toFixed(2)}km
                                                                </div>
                                                                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                                                    @ {paceLabel}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>

                        </div>
                    );
                })}
            </div>
        </div>
      </div>

      {selectedActivity && (
        <ActivityModal 
            activity={selectedActivity} 
            onClose={() => setSelectedActivity(null)} 
        />
      )}
    </div>
  )
}
