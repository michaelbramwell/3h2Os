import { useEffect } from 'react'
import { CheckCircle, LogOut, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { getStravaAuthUrl, disconnectStrava } from '../lib/api'
import { useStravaStatus } from '../hooks/useStravaStatus'

/**
 * Strava connection widget for the header.
 *
 * Disconnected: "Connect with Strava" button — initiates OAuth redirect.
 * Connected: green badge + athlete ID + Disconnect button.
 *
 * On mount, checks if the URL contains ?strava_error= (set by the callback
 * redirect on failure) and shows an error toast if present.
 */
export function StravaSettings() {
    const { connected, athleteId, isLoading } = useStravaStatus();
    const queryClient = useQueryClient();

    // Show toast if Strava OAuth callback returned an error
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const stravaError = params.get('strava_error');
        if (stravaError) {
            toast.error(`Strava connection failed: ${stravaError}`);
            // Remove the query param without a page reload
            params.delete('strava_error');
            const newSearch = params.toString();
            const newUrl = window.location.pathname + (newSearch ? `?${newSearch}` : '');
            window.history.replaceState({}, '', newUrl);
        }
    }, []);

    const handleConnect = async () => {
        try {
            const url = await getStravaAuthUrl();
            window.location.href = url;
        } catch {
            toast.error('Could not get Strava authorization URL');
        }
    };

    const handleDisconnect = async () => {
        try {
            await disconnectStrava();
            queryClient.invalidateQueries({ queryKey: ['stravaStatus'] });
            toast.info('Strava disconnected');
        } catch {
            toast.error('Failed to disconnect Strava');
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-1.5">
                <Loader2 className="animate-spin text-slate-400" size={16} />
            </div>
        );
    }

    if (connected) {
        return (
            <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 text-xs text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
                    <CheckCircle size={12} />
                    <span>Strava{athleteId ? ` #${athleteId}` : ''}</span>
                </div>
                <button
                    onClick={handleDisconnect}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors"
                    title="Disconnect Strava"
                >
                    <LogOut size={13} />
                </button>
            </div>
        );
    }

    return (
        <button
            onClick={handleConnect}
            className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium text-white transition-colors"
            style={{ backgroundColor: '#FC4C02' }}
            title="Connect with Strava"
        >
            Connect Strava
        </button>
    );
}
