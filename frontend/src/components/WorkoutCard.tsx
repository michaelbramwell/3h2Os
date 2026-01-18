import type { Workout } from '../types/schema'

// Extend Workout to include optional description as found in legacy code usage
type WorkoutWithDescription = Workout & { description?: string };

interface WorkoutCardProps {
    workout: WorkoutWithDescription
    isToday: boolean
    isMarathonDay: boolean
}

export function WorkoutCard({ workout, isToday, isMarathonDay }: WorkoutCardProps) {
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
        <div className={workoutCardStyle}>
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
}
