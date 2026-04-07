import { useState, useRef, useEffect } from 'react'
import { Plug, CheckCircle, LogOut, Loader2, AlertTriangle, ChevronDown } from 'lucide-react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { getStravaAuthUrl, disconnectStrava, getGarminToken } from '../lib/api'
import { useStravaStatus } from '../hooks/useStravaStatus'
import { useGarminToken } from '../hooks/useGarminToken'
import { useFeatureFlags } from '../hooks/useFeatureFlags'

/**
 * Single "Integrations" dropdown in the header.
 *
 * Shows Strava and Garmin rows with connection status.
 * Strava takes priority over Garmin for syncing — indicated visually.
 *
 * Strava: OAuth connect button, or connected badge + disconnect.
 * Garmin: connect form (email/password, unofficial API warning), or connected badge + disconnect.
 */
export function IntegrationsMenu() {
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    const queryClient = useQueryClient();
    const { connected: stravaConnected, athleteId, isLoading: stravaLoading } = useStravaStatus();
    const { token: garminToken, saveToken, removeToken } = useGarminToken();
    const flags = useFeatureFlags();

    const [garminEmail, setGarminEmail] = useState('');
    const [garminPassword, setGarminPassword] = useState('');
    const [garminLoading, setGarminLoading] = useState(false);
    const [showGarminForm, setShowGarminForm] = useState(false);
    const prevGarminTokenRef = useRef<string | null>(garminToken);

    // Detect when the token is cleared externally (e.g. by the auto-refresh interceptor
    // after the OAuth1 token has also expired) and notify the user.
    useEffect(() => {
        if (prevGarminTokenRef.current && !garminToken) {
            toast.error('Garmin session expired. Please reconnect.');
        }
        prevGarminTokenRef.current = garminToken;
    }, [garminToken]);

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        if (isOpen) document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isOpen]);

    // Reset Garmin form state when menu closes
    useEffect(() => {
        if (!isOpen) {
            setShowGarminForm(false);
            setGarminEmail('');
            setGarminPassword('');
        }
    }, [isOpen]);

    // Show toast if Strava OAuth callback returned an error
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const stravaError = params.get('strava_error');
        if (stravaError) {
            toast.error(`Strava connection failed: ${stravaError}`);
            params.delete('strava_error');
            const newSearch = params.toString();
            window.history.replaceState({}, '', window.location.pathname + (newSearch ? `?${newSearch}` : ''));
        }
    }, []);

    const handleStravaConnect = async () => {
        try {
            const url = await getStravaAuthUrl();
            window.location.href = url;
        } catch {
            toast.error('Could not get Strava authorization URL');
        }
    };

    const handleStravaDisconnect = async () => {
        try {
            await disconnectStrava();
            queryClient.invalidateQueries({ queryKey: ['stravaStatus'] });
            toast.info('Strava disconnected');
        } catch {
            toast.error('Failed to disconnect Strava');
        }
    };

    const handleGarminConnect = async (e: React.FormEvent) => {
        e.preventDefault();
        setGarminLoading(true);
        try {
            const tokenStr = await getGarminToken(garminEmail, garminPassword);
            saveToken(tokenStr);
            setGarminEmail('');
            setGarminPassword('');
            setShowGarminForm(false);
            toast.success('Garmin connected');
        } catch (error: unknown) {
            const errMsg = (error as any).response?.data?.detail || 'Failed to connect to Garmin';
            toast.error(errMsg);
        } finally {
            setGarminLoading(false);
        }
    };

    const handleGarminDisconnect = () => {
        removeToken();
        toast.info('Garmin disconnected');
    };

    // Pill indicator: green if anything connected, grey otherwise
    const anyConnected = stravaConnected || (flags.isGarminEnabled && !!garminToken);

    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium transition-colors hover:bg-slate-100 text-slate-600"
                title="Integrations"
            >
                <Plug size={14} className={anyConnected ? 'text-green-600' : 'text-slate-400'} />
                <span>Integrations</span>
                <ChevronDown size={12} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute top-full right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-slate-100">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Integrations</p>
                    </div>

                    {/* Strava row */}
                    <div className="px-4 py-3 border-b border-slate-100">
                        <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-slate-800">Strava</span>
                                <span className="text-[10px] font-medium text-white bg-orange-500 rounded px-1.5 py-0.5 leading-none">Priority</span>
                            </div>
                            {stravaLoading ? (
                                <Loader2 size={14} className="animate-spin text-slate-400" />
                            ) : stravaConnected ? (
                                <div className="flex items-center gap-2">
                                    <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
                                        <CheckCircle size={11} />
                                        {athleteId ? `#${athleteId}` : 'Connected'}
                                    </span>
                                    <button
                                        onClick={handleStravaDisconnect}
                                        className="text-slate-400 hover:text-slate-600 transition-colors"
                                        title="Disconnect Strava"
                                    >
                                        <LogOut size={13} />
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={handleStravaConnect}
                                    className="flex items-center transition-opacity hover:opacity-90"
                                    title="Connect with Strava"
                                >
                                    <img
                                        src="/btn_strava_connect_with_orange.svg"
                                        alt="Connect with Strava"
                                        className="h-7"
                                    />
                                </button>
                            )}
                        </div>
                        <p className="text-[11px] text-slate-400">Used for activity sync when connected</p>
                    </div>

                    {/* Garmin row — only shown when the feature flag is enabled */}
                    {flags.isGarminEnabled && (
                    <div className="px-4 py-3">
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="text-sm font-semibold text-slate-800">Garmin</span>
                            {garminToken ? (
                                <div className="flex items-center gap-2">
                                    <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
                                        <CheckCircle size={11} />
                                        Connected
                                    </span>
                                    <button
                                        onClick={handleGarminDisconnect}
                                        className="text-slate-400 hover:text-slate-600 transition-colors"
                                        title="Disconnect Garmin"
                                    >
                                        <LogOut size={13} />
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setShowGarminForm(!showGarminForm)}
                                    className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-white transition-colors"
                                >
                                    {showGarminForm ? 'Cancel' : 'Connect'}
                                </button>
                            )}
                        </div>
                        <p className="text-[11px] text-slate-400">
                            {stravaConnected ? 'Fallback — Strava takes priority' : 'Used for activity sync when Strava is not connected'}
                        </p>

                        {showGarminForm && !garminToken && (
                            <form onSubmit={handleGarminConnect} className="mt-3 space-y-2.5">
                                <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-lg p-2.5">
                                    <AlertTriangle size={12} className="text-amber-600 shrink-0 mt-0.5" />
                                    <p className="text-[10px] text-amber-800 leading-tight">
                                        Unofficial API. Credentials are sent to the server for initial login only and not stored. Token is saved in your browser locally.
                                    </p>
                                </div>
                                <input
                                    type="email"
                                    value={garminEmail}
                                    onChange={e => setGarminEmail(e.target.value)}
                                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    required
                                    placeholder="Garmin email"
                                />
                                <input
                                    type="password"
                                    value={garminPassword}
                                    onChange={e => setGarminPassword(e.target.value)}
                                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    required
                                    placeholder="Password"
                                />
                                <button
                                    type="submit"
                                    disabled={garminLoading}
                                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-medium transition disabled:opacity-50"
                                >
                                    {garminLoading ? <Loader2 size={12} className="animate-spin" /> : 'Connect Garmin'}
                                </button>
                            </form>
                        )}
                    </div>
                    )}

                    {/* Powered by Strava attribution — required by Strava API agreement */}
                    <div className="px-4 py-2.5 border-t border-slate-100 flex justify-end">
                        <img
                            src="/api_logo_pwrdBy_strava_horiz_black.svg"
                            alt="Powered by Strava"
                            className="h-4 opacity-50"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
