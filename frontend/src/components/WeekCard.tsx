import { useState } from 'react'
import type { Week, Activity, Day } from '../types/schema'
import { WeekStats } from './WeekStats'
import { DayCard } from './DayCard'
import { calculateWeekVolume, calculateWeekActuals, calculateRemainingWeekVolume } from '../lib/calculations'
import { EditWeekDialog } from './EditWeekDialog'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateWeek } from '../lib/api'
import { toast } from 'sonner'

interface WeekCardProps {
    week: Week
    actuals: Activity[]
    todayStr: string
    isFridgeMode: boolean
    onFridgeClick: (weekId: string) => void
    onActivityClick: (activity: Activity) => void
}

export function WeekCard({ week, actuals, todayStr, isFridgeMode, onFridgeClick, onActivityClick }: WeekCardProps) {
    const [isEditOpen, setIsEditOpen] = useState(false);
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: async ({ id, data }: { id: number, data: { status: string } }) => {
            return updateWeek(id, data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plan'] });
            toast.success('Week updated successfully');
        },
        onError: (error: any) => {
            console.error(error);
            toast.error("Failed to update week. " + (error.response?.data?.detail || error.message));
        }
    });

    const handleWeekSave = (id: number, data: { status: string }) => {
        if (!id) {
            console.error("Cannot save week without ID");
            toast.error("Cannot save week: Missing Week ID");
            return;
        }
        mutation.mutate({ id, data });
    };

    // Check if current week by seeing if today is in this week's days
    const weekDatesSet = new Set(Object.values(week.days).map((d: Day) => d.date));
    const isCurrentWeek = weekDatesSet.has(todayStr);

    const status = week.status?.toLowerCase() || 'normal';
    const isCompleted = status === 'completed' || (!isCurrentWeek && new Date(week.weekStarting) < new Date(todayStr));
    
    // Helper to determine week status color
     const getWeekStyle = (status: string, isCurrentWeek: boolean) => {
        const s = status?.toLowerCase() || 'normal';
        
        // Special Phases
        if (s.includes('marathon')) return 'bg-yellow-50/50 border-yellow-400 ring-2 ring-yellow-200 shadow-md';
        if (s.includes('race')) return 'bg-amber-50/50 border-amber-300 ring-1 ring-amber-100';
        if (s.includes('taper')) return 'bg-purple-50/30 border-purple-200';
        if (s.includes('peak')) return 'bg-rose-50/30 border-rose-200 ring-1 ring-rose-100';
        
        // Temporal States
        if (s === 'completed') return 'bg-slate-50 border-slate-200 opacity-70 grayscale-[0.5]'; 
        if (isCurrentWeek) return 'bg-white border-orange-400 ring-4 ring-orange-100 shadow-lg scale-[1.01]'; 

        return 'bg-white border-slate-200'; // upcoming/normal
    }

    const weekStyle = getWeekStyle(status, isCurrentWeek);
    
    // --- Stats Calculation ---
    const weekTargetM = calculateWeekVolume(week);
    const weekActualM = calculateWeekActuals(actuals, week);
    const weekRemainingM = calculateRemainingWeekVolume(week, todayStr);

    const projectedM = weekActualM + weekRemainingM;
    const diffM = projectedM - weekTargetM;
    const diffKm = diffM / 1000;

    return (
        <div 
            className={`rounded-xl p-5 border shadow-sm transition-all duration-200 ${weekStyle}`}
        >
            <WeekStats 
                weekStarting={week.weekStarting}
                status={status}
                isCurrentWeek={isCurrentWeek}
                weekTargetM={weekTargetM}
                weekActualM={weekActualM}
                projectedM={projectedM}
                diffKm={diffKm}
                isCompleted={isCompleted}
                onFridgeClick={isFridgeMode ? undefined : () => onFridgeClick(week.weekStarting)}
                onEditClick={isFridgeMode ? undefined : () => setIsEditOpen(true)}
            />
            
            {/* Days Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                {Object.entries(week.days)
                    .sort((a,b) => new Date(a[1].date).getTime() - new Date(b[1].date).getTime())
                    .map(([dayName, day]: [string, Day]) => {
                    
                    const dayActuals = actuals?.filter((a: Activity) => a.date === day.date) || [];

                    return (
                        <div key={dayName} className="h-full">
                            <DayCard 
                                dayName={dayName}
                                day={day}
                                actuals={dayActuals}
                                todayStr={todayStr}
                                weekStatus={status}
                                onActivityClick={onActivityClick}
                            />
                        </div>
                    )
                })}
            </div>

            <EditWeekDialog 
                week={week}
                isOpen={isEditOpen}
                onOpenChange={setIsEditOpen}
                onSave={handleWeekSave}
            />
        </div>
    )
}
