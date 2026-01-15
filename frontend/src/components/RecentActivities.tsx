import { useState } from 'react';
import type { Activity } from '../types/schema';
import { ActivityModal } from './ActivityModal';

interface RecentActivitiesProps {
    activities: Activity[];
}

export function RecentActivities({ activities }: RecentActivitiesProps) {
    const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

    // Debug logging
    console.log('RecentActivities Rendered. Activities count:', activities?.length);

    if (!activities || activities.length === 0) {
        return <div className="text-gray-500 text-sm">No recent activities found.</div>;
    }

    // Sort by date descending
    const sortedActivities = [...activities].sort((a, b) => 
        new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    return (
        <>
            <div 
                className="bg-white rounded-lg shadow p-6 border border-slate-200 relative z-50 pointer-events-auto"
                onClick={() => console.log('Container clicked')}
            >
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Recent Activities</h3>
                    {/* Debug indicator with inline styles to guarantee visibility */}
                    <div 
                        style={{ width: '20px', height: '20px', backgroundColor: 'red', display: 'block', cursor: 'pointer' }}
                        onClick={(e) => {
                            e.stopPropagation();
                            console.error('🔴 RED DOT CLICKED');
                            alert('Red Dot Clicked!');
                        }} 
                        title="Debug Click"
                    ></div>
                </div>

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
                        <tbody className="font-mono relative z-10">
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
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            console.log('Row clicked for activity:', activity.activityId, activity.name);
                                            setSelectedActivity(activity);
                                        }}
                                        className="border-b last:border-0 hover:bg-slate-50 cursor-pointer transition-colors group relative z-20"
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
