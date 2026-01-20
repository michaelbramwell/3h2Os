import { useState } from 'react';
import type { Activity } from '../types/schema';
import { ActivityModal } from './ActivityModal';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { syncActivities } from '../lib/api';
import { RefreshCw, Loader2 } from 'lucide-react';

interface RecentActivitiesProps {
    activities: Activity[];
}

export function RecentActivities({ activities }: RecentActivitiesProps) {
    const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
    const queryClient = useQueryClient();

    const syncMutation = useMutation({
        mutationFn: () => syncActivities(7),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['actuals'] });
        }
    });

    // Debug logging
    console.log('RecentActivities Rendered. Activities count:', activities?.length);

    // Sort by date descending, default to empty array if null
    const sortedActivities = activities ? [...activities].sort((a, b) => 
        new Date(b.date).getTime() - new Date(a.date).getTime()
    ) : [];

    return (
        <>
            <div className="bg-white rounded-lg shadow p-6 border border-slate-200 relative z-0">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Recent Activities</h3>
                    <button 
                        onClick={() => syncMutation.mutate()} 
                        disabled={syncMutation.isPending}
                        className="flex items-center gap-2 text-xs font-medium text-blue-600 hover:text-blue-800 disabled:opacity-50 transition-colors"
                        title="Fetch latest activities from Garmin"
                    >
                        {syncMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                        {syncMutation.isPending ? 'Syncing...' : 'Scan for new runs'}
                    </button>
                </div>
                
                {sortedActivities.length === 0 ? (
                    <div className="text-gray-500 text-sm italic py-4 text-center">No recent activities found. Click scan to sync from Garmin.</div>
                ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="border-b text-left text-xs uppercase text-gray-500">
                                <th className="pb-2 font-medium">Date</th>
                                <th className="pb-2 font-medium">Activity</th>
                                <th className="pb-2 font-medium">Dist</th>
                                <th className="pb-2 font-medium">Pace</th>
                                <th className="pb-2 font-medium">HR</th>
                            </tr>
                        </thead>
                        <tbody className="font-mono">
                            {sortedActivities.slice(0, 5).map((activity, idx) => {
                                const date = new Date(activity.date);
                                const distanceKm = activity.distance_m / 1000;
                                // Pace calculation: seconds per km
                                const paceSeconds = distanceKm > 0 ? activity.duration_s / distanceKm : 0;
                                const paceMin = Math.floor(paceSeconds / 60);
                                const paceSec = Math.floor(paceSeconds % 60);
                                const pace = `${paceMin}:${paceSec.toString().padStart(2, '0')}`;

                                return (
                                    <tr 
                                        key={activity.activityId || idx} 
                                        onClick={() => setSelectedActivity(activity)}
                                        className="border-b last:border-0 hover:bg-slate-50 cursor-pointer transition-colors group"
                                    >
                                        <td className="py-3 text-gray-600">
                                            {date.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric' })}
                                        </td>
                                        <td className="py-3 font-semibold text-gray-800 group-hover:text-blue-600 transition-colors">
                                            {activity.name}
                                        </td>
                                        <td className="py-3 text-gray-600">
                                            {distanceKm.toFixed(1)} km
                                        </td>
                                        <td className="py-3 text-gray-600">
                                            {pace} /km
                                        </td>
                                        <td className="py-3 text-gray-600">
                                            {activity.average_hr ? Math.round(activity.average_hr) : '-'} bpm
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
                )}
            </div>

            {selectedActivity && (
                <ActivityModal 
                    activity={selectedActivity} 
                    onClose={() => setSelectedActivity(null)} 
                />
            )}
        </>
    );
}
