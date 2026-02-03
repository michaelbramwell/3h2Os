import { type Activity } from '../types/schema'
import { formatPace, formatSwimPace, formatDistance } from '../lib/formatters'

interface ActualCardProps {
    activity: Activity
    onClick: (e: React.MouseEvent) => void
}

export function ActualCard({ activity, onClick }: ActualCardProps) {
    const isSwim = activity.type === 'swimming';
    const paceMs = activity.average_pace_m_s || 0;
    
    let paceLabel = '-:--/km';
    if (paceMs > 0) {
        if (isSwim) {
            // paceMs is m/s. formatSwimPace handles m/s -> min:sec/100m
            paceLabel = `${formatSwimPace(paceMs)}/100m`;
        } else {
             paceLabel = `${formatPace(1000 / paceMs)}/km`;
        }
    }

    const isRunning = activity.type === 'running' || activity.type === 'trail_running';
    
    // Style differentiation
    let bgColor = 'bg-emerald-50';
    let borderColor = 'border-emerald-100';
    let hoverColor = 'hover:bg-emerald-100';
    let barColor = 'bg-emerald-500';
    let textColor = 'text-emerald-600';
    
    if (isSwim) {
        bgColor = 'bg-cyan-50';
        borderColor = 'border-cyan-100';
        hoverColor = 'hover:bg-cyan-100';
        barColor = 'bg-cyan-500';
        textColor = 'text-cyan-600';
    }

    return (
        <div 
            onClick={onClick}
            className={`${bgColor} p-2 rounded border ${borderColor} shadow-sm relative overflow-hidden group ${hoverColor} hover:shadow-md transition-all cursor-pointer`}
        >
            <div className={`absolute left-0 top-0 bottom-0 w-1 ${barColor}`}></div>
            <div className="pl-2">
                <div className={`font-bold text-[10px] ${textColor} uppercase tracking-wider mb-0.5`}>
                    Actual {isRunning ? '🏃' : (isSwim ? '🏊' : '✓')}
                </div>
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
