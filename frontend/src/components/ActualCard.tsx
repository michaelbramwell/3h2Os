import type { Activity } from '../types/schema'
import { formatPace, formatDistance } from '../lib/formatters'

interface ActualCardProps {
    activity: Activity
    onClick: (e: React.MouseEvent) => void
}

export function ActualCard({ activity, onClick }: ActualCardProps) {
    const paceMs = activity.average_pace_m_s || 0;
    const paceLabel = paceMs > 0 
        ? `${formatPace(1000 / paceMs)}/km` 
        : '-:--/km';

    return (
        <div 
            onClick={onClick}
            className="bg-emerald-50 p-2 rounded border border-emerald-100 shadow-sm relative overflow-hidden group hover:bg-emerald-100 hover:shadow-md transition-all cursor-pointer"
        >
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"></div>
            <div className="pl-2">
                <div className="font-bold text-[10px] text-emerald-600 uppercase tracking-wider mb-0.5">Actual {activity.type === 'running' ? '🏃' : '✓'}</div>
                <div className="font-bold text-sm text-slate-800 leading-tight">
                    {formatDistance(activity.distance_m, 2)}km
                </div>
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                    @ {paceLabel}
                </div>
            </div>
        </div>
    )
}
