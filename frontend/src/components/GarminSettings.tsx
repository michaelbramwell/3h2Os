import { useState, useRef, useEffect } from 'react'
import { Settings, Loader2, LogOut, CheckCircle, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import { getGarminToken } from '../lib/api'
import { useGarminToken } from '../hooks/useGarminToken'

export function GarminSettings() {
    const [isOpen, setIsOpen] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { token, saveToken, removeToken } = useGarminToken();
    const dialogRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Click outside listener
        const handleClickOutside = (event: MouseEvent) => {
            if (dialogRef.current && !dialogRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        
        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        
        return () => {
             document.removeEventListener('mousedown', handleClickOutside);
        }
    }, [isOpen]);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            const tokenStr = await getGarminToken(email, password);
            saveToken(tokenStr);
            setEmail('');
            setPassword('');
            setIsOpen(false);
            toast.success("Garmin connected successfully");
        } catch (error: any) {
            console.error(error);
            toast.error(error.response?.data?.detail || "Failed to connect to Garmin");
        } finally {
            setIsLoading(false);
        }
    };

    const handleLogout = () => {
        removeToken();
        toast.info("Garmin disconnected");
    };

    return (
        <div className="relative">
             <button 
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center justify-center p-1.5 rounded-full transition-colors ${token ? 'text-blue-500 hover:bg-blue-50' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'}`}
                title={token ? "Garmin Connected" : "Connect Garmin"}
             >
                <Settings size={16} />
                {token && <span className="absolute top-0 right-0 w-2 h-2 bg-green-500 rounded-full border border-white"></span>}
             </button>

             {isOpen && (
                 <div ref={dialogRef} className="absolute top-full right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-slate-200 p-4 z-50 text-left">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="font-semibold text-slate-900 text-sm">Garmin Connection</h3>
                    </div>

                    {token ? (
                        <div className="space-y-4">
                            <div className="bg-green-50 border border-green-100 rounded-lg p-3 flex items-start gap-3">
                                <CheckCircle className="text-green-600 shrink-0 mt-0.5" size={16} />
                                <div>
                                    <p className="text-sm font-medium text-green-900">Connected</p>
                                    <p className="text-xs text-green-700 mt-1">Token stored in browser.</p>
                                </div>
                            </div>
                            
                            <button 
                                onClick={handleLogout}
                                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-sm font-medium transition"
                            >
                                <LogOut size={14} /> Disconnect
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={handleLogin} className="space-y-3">
                            <div className="bg-amber-50 border border-amber-100 rounded-lg p-3 flex items-start gap-2 mb-3">
                                <AlertTriangle className="text-amber-600 shrink-0 mt-0.5" size={14} />
                                <p className="text-[10px] text-amber-800 leading-tight">
                                    Unofficial API. Credentials are sent to server for initial login only and not stored. Token is saved in your browser locally.
                                </p>
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-slate-700 mb-1">Email</label>
                                <input 
                                    type="email" 
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    required
                                    placeholder="Garmin Email"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-700 mb-1">Password</label>
                                <input 
                                    type="password" 
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    required
                                    placeholder="********"
                                />
                            </div>

                            <button 
                                type="submit" 
                                disabled={isLoading}
                                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition disabled:opacity-50"
                            >
                                {isLoading ? <Loader2 className="animate-spin" size={14} /> : 'Connect'}
                            </button>
                        </form>
                    )}
                 </div>
             )}
        </div>
    )
}
