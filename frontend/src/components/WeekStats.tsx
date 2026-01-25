import { Printer, RefreshCw, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { syncActivities } from '../lib/api'
import { useGarminToken } from '../hooks/useGarminToken'

import { formatDistance } from '../lib/formatters'

interface WeekStatsProps {
    weekStarting: string
    status: string
    isCurrentWeek: boolean
    weekTargetM: number
    weekActualM: number
    projectedM: number
    diffKm: number
    isCompleted: boolean
    onFridgeClick?: () => void
}

export function WeekStats({
    weekStarting,
    status,
    isCurrentWeek,
    weekTargetM,
    weekActualM,
    projectedM,
    diffKm,
    isCompleted,
    onFridgeClick
}: WeekStatsProps) {
    const queryClient = useQueryClient();
    const { hasToken: hasGarminToken } = useGarminToken();
    const syncMutation = useMutation({
        mutationFn: () => syncActivities(7),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['actuals'] });
        }
    });

    return (
        <div className="sticky top-0 z-10 flex flex-col md:flex-row justify-between items-start md:items-center -mx-5 -mt-5 pt-5 px-5 pb-3 mb-4 border-b border-slate-100/50 gap-4 rounded-t-xl backdrop-blur-md bg-white/30">
            <div>
                <div className="flex items-center gap-3">
                    <h3 className={`text-lg font-bold flex items-center ${isCurrentWeek ? 'text-orange-900' : 'text-slate-800'}`}>
                        Week of {new Date(weekStarting).toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })}
                        {(status === 'race' || status === 'marathon') && <span className="ml-2 text-yellow-600">🏆</span>}
                        {status === 'taper' && <span className="ml-2 text-purple-600">📉</span>}
                    </h3>
                    {isCurrentWeek && hasGarminToken && (
                        <button
                            onClick={() => syncMutation.mutate()}
                            disabled={syncMutation.isPending}
                            className="p-1 rounded-full bg-orange-100 text-orange-600 hover:bg-orange-200 transition-colors"
                            title="Scan for new runs"
                        >
                            {syncMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                        </button>
                    )}
                </div>
                {isCurrentWeek && <span className="inline-block px-2 py-0.5 mt-1 text-[10px] font-bold uppercase tracking-wider text-orange-600 bg-orange-100 rounded-full">Current Week</span>}
                {(status === 'race' || status === 'marathon') && <span className="ml-2 inline-block px-2 py-0.5 mt-1 text-[10px] font-bold uppercase tracking-wider text-yellow-700 bg-yellow-100 rounded-full">Race Week</span>}
                {status === 'taper' && <span className="ml-2 inline-block px-2 py-0.5 mt-1 text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-100 rounded-full">Taper</span>}
            </div>
            
            {/* Progress Stats using flex for compact layout */}
            <div className="flex gap-4 md:gap-8 bg-white/50 p-2 rounded-lg border border-slate-100 text-xs md:text-sm">
                <div className="text-center">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Target</div>
                    <div className="font-bold text-slate-700">{formatDistance(weekTargetM, 0)}km</div>
                </div>
                <div className="text-center">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Actual</div>
                    <div className={`font-bold ${weekActualM > 0 ? 'text-green-600' : 'text-slate-300'}`}>{formatDistance(weekActualM)}km</div>
                </div>
                <div className="text-center border-l border-slate-200 pl-4">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Projected</div>
                    <div className="font-bold text-blue-600">{formatDistance(projectedM)}km</div>
                </div>
                <div className="text-center hidden sm:block">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Diff</div>
                    <div className={`font-bold ${diffKm >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                        {diffKm > 0 ? '+' : ''}{diffKm.toFixed(1)}km
                    </div>
                </div>
            </div>

            <div className="text-right hidden md:flex flex-col items-end gap-2">
                 <span className={`text-xs font-bold uppercase tracking-wider px-2 py-1 rounded ${isCompleted ? 'bg-emerald-100 text-emerald-700' : (isCurrentWeek ? 'bg-orange-100 text-orange-800' : 'bg-slate-100 text-slate-500')}`}>
                    {status === 'normal' ? (isCompleted ? 'Completed' : (isCurrentWeek ? 'Current' : 'Upcoming')) : status}
                 </span>
                 
                 {onFridgeClick && (
                     <button 
                        onClick={onFridgeClick}
                        className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider bg-slate-100 hover:bg-slate-200 text-slate-600 px-2 py-1 rounded transition-colors"
                     >
                        <Printer size={12} /> Fridge
                     </button>
                 )}
            </div>
        </div>
    )
}
