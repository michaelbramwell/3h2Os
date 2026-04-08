import { useState, useEffect } from 'react';
import type { Activity, Week } from '../types/schema';
import { ActivityModal } from './ActivityModal';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { syncActivities, syncStravaActivities, syncBothActivities } from '../lib/api';
import { RefreshCw, Loader2 } from 'lucide-react';
import { useGarminToken } from '../hooks/useGarminToken';
import { useStravaStatus } from '../hooks/useStravaStatus';
import { useFeatureFlags } from '../hooks/useFeatureFlags';
import { formatDistance, formatPace } from '../lib/formatters'

interface RecentActivitiesProps {
    activities: Activity[];
    plan?: Week[];
}

function SourceBadge({ source, garminEnabled }: { source?: string; garminEnabled: boolean }) {
    if (garminEnabled && (!source || source === 'garmin')) {
        return (
            <span className="inline-block text-[9px] font-bold px-1 py-0.5 rounded bg-blue-100 text-blue-700 leading-none">
                G
            </span>
        );
    }
    if (source === 'strava') {
        return (
            <span
                className="inline-block text-[9px] font-bold px-1 py-0.5 rounded text-white leading-none"
                style={{ backgroundColor: '#FC4C02' }}
            >
                S
            </span>
        );
    }
    return null;
}

export function RecentActivities({ activities, plan }: RecentActivitiesProps) {
    const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
    const queryClient = useQueryClient();
    const { hasToken: hasGarminToken } = useGarminToken();
    const { connected: stravaConnected } = useStravaStatus();
    const flags = useFeatureFlags();

    // Only consider Garmin connected when the feature is enabled
    const garminActive = flags.isGarminEnabled && hasGarminToken;

    // Keep selectedActivity in sync when the actuals prop updates (e.g. after a rename)
    useEffect(() => {
        if (!selectedActivity) return;
        const fresh = activities?.find(a => a.id === selectedActivity.id);
        if (fresh && (fresh.name !== selectedActivity.name || fresh.custom_name !== selectedActivity.custom_name)) {
            setSelectedActivity(fresh);
        }
    }, [activities, selectedActivity]);

    const garminSyncMutation = useMutation({
        mutationFn: () => syncActivities(7),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['actuals'] });
        }
    });

    const stravaSyncMutation = useMutation({
        mutationFn: () => syncStravaActivities(7),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['actuals'] });
        }
    });

    const bothSyncMutation = useMutation({
        mutationFn: () => syncBothActivities(7),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['actuals'] });
        }
    });

    // Sort by date descending, default to empty array if null
    const sortedActivities = activities ? [...activities].sort((a, b) =>
        new Date(b.date).getTime() - new Date(a.date).getTime()
    ) : [];

    const bothConnected = stravaConnected && garminActive;
    const showBothSyncButton = bothConnected;
    const showStravaSyncButton = !bothConnected && stravaConnected;
    const showGarminSyncButton = !bothConnected && !stravaConnected && garminActive;

    return (
        <>
            <div className="bg-white rounded-lg shadow p-6 border border-slate-200 relative z-0">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Recent Activities</h3>
                    <div className="flex items-center gap-3">
                        {showBothSyncButton && (
                            <button
                                onClick={() => bothSyncMutation.mutate()}
                                disabled={bothSyncMutation.isPending}
                                className="flex items-center gap-2 text-xs font-medium text-white disabled:opacity-50 transition-colors px-2 py-1 rounded"
                                style={{ backgroundColor: '#FC4C02' }}
                                title="Fetch latest activities from Strava and enrich with Garmin data"
                            >
                                {bothSyncMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                                {bothSyncMutation.isPending ? 'Syncing...' : 'Scan activities'}
                            </button>
                        )}
                        {showStravaSyncButton && (
                            <button
                                onClick={() => stravaSyncMutation.mutate()}
                                disabled={stravaSyncMutation.isPending}
                                className="flex items-center gap-2 text-xs font-medium text-white disabled:opacity-50 transition-colors px-2 py-1 rounded"
                                style={{ backgroundColor: '#FC4C02' }}
                                title="Fetch latest activities from Strava"
                            >
                                {stravaSyncMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                                {stravaSyncMutation.isPending ? 'Syncing...' : 'Scan activities'}
                            </button>
                        )}
                        {showGarminSyncButton && (
                            <button
                                onClick={() => garminSyncMutation.mutate()}
                                disabled={garminSyncMutation.isPending}
                                className="flex items-center gap-2 text-xs font-medium text-blue-600 hover:text-blue-800 disabled:opacity-50 transition-colors"
                                title="Fetch latest activities from Garmin"
                            >
                                {garminSyncMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                                {garminSyncMutation.isPending ? 'Syncing...' : 'Scan activities'}
                            </button>
                        )}
                    </div>
                </div>

                {sortedActivities.length === 0 ? (
                    <div className="text-gray-500 text-sm italic py-4 text-center">No recent activities found. Click scan to sync from {flags.isGarminEnabled ? 'Garmin or Strava' : 'Strava'}.</div>
                ) : (
                    <div className="divide-y divide-slate-100">
                        {sortedActivities.slice(0, 5).map((activity, idx) => {
                            const date = new Date(activity.date);
                            const distanceKm = activity.distance_m / 1000;

                            return (
                                <div
                                    key={activity.stravaActivityId ?? activity.activityId ?? idx}
                                    onClick={() => setSelectedActivity(activity)}
                                    className="py-2.5 hover:bg-slate-50 cursor-pointer transition-colors group px-1 -mx-1 rounded"
                                >
                                    {/* Top line: date + name + source badge */}
                                    <div className="flex items-center gap-2 min-w-0">
                                        <span className="text-xs text-slate-400 shrink-0">
                                            {date.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric' })}
                                        </span>
                                        <span className="text-xs font-semibold text-slate-800 group-hover:text-blue-600 transition-colors truncate">
                                            {activity.custom_name ?? activity.name}
                                        </span>
                                        <SourceBadge source={activity.source} garminEnabled={flags.isGarminEnabled} />
                                    </div>
                                    {/* Bottom line: stats + View on Strava */}
                                    <div className="flex items-center gap-3 mt-0.5">
                                        <span className="font-mono text-xs text-slate-500">
                                            {formatDistance(activity.distance_m)} km
                                        </span>
                                        <span className="font-mono text-xs text-slate-400">
                                            {formatPace(distanceKm > 0 ? activity.duration_s / distanceKm : 0)}/km
                                        </span>
                                        {activity.average_hr && (
                                            <span className="font-mono text-xs text-slate-400">
                                                {Math.round(activity.average_hr)} bpm
                                            </span>
                                        )}
                                        {activity.stravaActivityId && (
                                            <a
                                                href={`https://www.strava.com/activities/${activity.stravaActivityId}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                onClick={e => e.stopPropagation()}
                                                className="ml-auto text-[10px] font-bold shrink-0"
                                                style={{ color: '#FC5200' }}
                                            >
                                                View on Strava
                                            </a>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {selectedActivity && (
                <ActivityModal
                    activity={selectedActivity}
                    plan={plan}
                    onClose={() => setSelectedActivity(null)}
                />
            )}
        </>
    );
}
