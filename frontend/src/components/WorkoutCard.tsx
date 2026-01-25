import { useState } from 'react'
import { Pencil, Sun, Moon } from 'lucide-react'
import { type Workout, ActivityType } from '../types/schema'
import { EditWorkoutDialog } from './EditWorkoutDialog'
import { formatDistance } from '../lib/formatters'

// Extend Workout to include optional description as found in legacy code usage
type WorkoutWithDescription = Workout & { description?: string };

interface WorkoutCardProps {
    workout: WorkoutWithDescription
    isToday: boolean
    isMarathonDay: boolean
    isPast: boolean
}

export function WorkoutCard({ workout, isToday, isMarathonDay, isPast }: WorkoutCardProps) {
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const isRaceWorkout = workout.type === ActivityType.RACE;
    const isPM = workout.timeOfDay === 'PM';
    const TimeIcon = isPM ? Moon : Sun;
    
    let workoutCardStyle = `bg-white p-2 rounded border border-slate-100 shadow-sm relative overflow-hidden group hover:border-blue-200 transition-colors cursor-default ${isToday ? 'bg-orange-50/30' : ''}`;
    let borderBarColor = 'bg-blue-500';

    if (isRaceWorkout && isMarathonDay) {
        workoutCardStyle = 'bg-yellow-100/80 p-3 rounded-lg border-2 border-yellow-400 shadow-md relative overflow-hidden group';
        borderBarColor = 'bg-yellow-600';
    } else if (isRaceWorkout) {
        workoutCardStyle = 'bg-amber-100/50 p-2 rounded border border-amber-300 shadow-sm relative overflow-hidden group';
        borderBarColor = 'bg-amber-500';
    }

    return (
        <>
            <div className={workoutCardStyle} onClick={() => !isPast && setIsDialogOpen(true)}>
                <div className={`absolute left-0 top-0 bottom-0 w-1 ${borderBarColor}`}></div>
                
                {/* Edit Icon Overlay */}
                {!isPast && (
                    <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white/80 p-1 rounded-full cursor-pointer hover:bg-white z-10">
                        <Pencil size={20} className="text-slate-400 hover:text-blue-500" />
                    </div>
                )}

                <div className={isRaceWorkout && isMarathonDay ? 'pl-3' : 'pl-2'}>
                    <div className={`font-bold ${isRaceWorkout && isMarathonDay ? 'text-lg uppercase text-yellow-900' : 'text-sm text-slate-700'} leading-tight`}>{workout.type}</div>
                    <div className={`${isRaceWorkout && isMarathonDay ? 'text-sm font-bold text-yellow-800' : 'text-xs text-slate-500'} mt-0.5 line-clamp-2`}>{workout.description || workout.name}</div>
                    <div className={`mt-1.5 flex justify-between text-[10px] items-center font-mono ${isRaceWorkout ? 'text-slate-600' : 'text-slate-400'}`}>
                        <span>{formatDistance(workout.distance_m)}km</span>
                        <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full ${isPM ? 'bg-indigo-50 text-indigo-400' : 'bg-orange-50 text-orange-400'}`}>
                            <TimeIcon size={10} />
                            <span className="font-bold">{workout.timeOfDay}</span>
                        </div>
                    </div>
                </div>
            </div>

            <EditWorkoutDialog 
                workout={workout} 
                isOpen={isDialogOpen} 
                onOpenChange={setIsDialogOpen} 
            />
        </>
    );
}

