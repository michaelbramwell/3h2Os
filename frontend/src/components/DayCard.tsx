import { type Day, type Activity, type Workout, ActivityType } from '../types/schema'
import { WorkoutCard } from './WorkoutCard'
import { ActualCard } from './ActualCard'

interface DayCardProps {
    dayName: string
    day: Day
    actuals: Activity[]
    todayStr: string
    weekStatus: string
    onActivityClick: (activity: Activity) => void
}

export function DayCard({ dayName, day, actuals, todayStr, weekStatus, onActivityClick }: DayCardProps) {
    const hasWorkouts = day.workouts && day.workouts.length > 0;
    const isToday = day.date === todayStr;
    const isPast = day.date < todayStr;
    const hasActuals = actuals && actuals.length > 0;

    // Check for Race/Marathon in Workouts
    let isRaceDay = false;
    let isMarathonDay = false;
    
    if (day.workouts) {
        day.workouts.forEach((w: Workout) => {
            if (w.type === ActivityType.RACE) {
                if (weekStatus.toLowerCase() === 'marathon') isMarathonDay = true;
                else isRaceDay = true;
            }
        });
    }

    // Styles
    let dayStyle = isToday 
        ? 'ring-2 ring-orange-500 shadow-md border-orange-200 bg-white' 
        : 'border-slate-100 bg-white hover:border-blue-200';
        
    let dayBadge = isToday 
        ? <div className="absolute top-0 right-0 bg-orange-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-bl-lg rounded-tr-lg z-10">TODAY</div> 
        : null;

    if (isMarathonDay) {
        dayStyle = 'bg-gradient-to-br from-yellow-50 to-amber-100 border-yellow-400 ring-4 ring-yellow-200 shadow-xl scale-[1.02] z-20';
        dayBadge = <div className="absolute top-0 right-0 bg-yellow-500 text-white text-[9px] font-bold px-2 py-1 rounded-bl-lg rounded-tr-lg z-10 shadow-sm flex items-center gap-1"><span>👑</span> RACE DAY</div>;
    } else if (isRaceDay) {
        dayStyle = 'bg-amber-50 border-amber-300 ring-2 ring-amber-100 shadow-md';
        dayBadge = <div className="absolute top-0 right-0 bg-amber-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-bl-lg rounded-tr-lg z-10 flex items-center gap-1"><span>🏁</span> RACE</div>;
    }

    return (
        <div className={`p-3 rounded-lg border flex flex-col h-full relative transition-all duration-300 ${dayStyle}`}>
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

                {day.workouts?.map((workout: Workout, idx: number) => (
                    <WorkoutCard 
                        key={`plan-${idx}`} 
                        workout={workout} 
                        isToday={isToday} 
                        isMarathonDay={isMarathonDay}
                        isPast={isPast || (isToday && hasActuals)}
                    />
                ))}

                {actuals.map((act: Activity, idx: number) => (
                    <ActualCard 
                        key={`act-${idx}`} 
                        activity={act} 
                        onClick={(e) => {
                            e.stopPropagation();
                            onActivityClick(act);
                        }} 
                    />
                ))}
            </div>
        </div>
    )
}
