import type { WizardSportEvent, EventType, Sport } from '../../types/wizard';
import type { StepErrors } from '../../hooks/useWizard';
import { RunningEvents, SwimmingPoolEvents, SwimmingOWEvents, EventLabels } from '../../types/wizard';

interface StepSportEventProps {
    data: WizardSportEvent;
    onChange: (data: Partial<WizardSportEvent>) => void;
    errors: StepErrors;
}

export function StepSportEvent({ data, onChange }: StepSportEventProps) {
    const handleSportChange = (sport: Sport) => {
        // Reset event type when sport changes
        const defaultEvent: EventType = sport === 'running' ? 'marathon' : 'pool_1500m';
        onChange({ sport, event_type: defaultEvent });
    };

    const availableEvents = data.sport === 'running'
        ? RunningEvents
        : [...SwimmingPoolEvents, ...SwimmingOWEvents];

    const isPool = SwimmingPoolEvents.includes(data.event_type);
    const isOW = SwimmingOWEvents.includes(data.event_type);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-slate-900 mb-1">Sport & Event</h2>
                <p className="text-sm text-slate-500">Choose your sport and target event distance.</p>
            </div>

            {/* Sport selection */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Sport</label>
                <div className="grid grid-cols-2 gap-3">
                    {(['running', 'swimming'] as Sport[]).map(sport => (
                        <button
                            key={sport}
                            type="button"
                            onClick={() => handleSportChange(sport)}
                            className={`
                                p-3 rounded-lg border-2 text-sm font-medium transition-all
                                ${data.sport === sport
                                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                            `}
                        >
                            {sport === 'running' ? 'Running' : 'Swimming'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Event type selection */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Event Distance</label>
                {data.sport === 'swimming' && (
                    <div className="flex gap-2 mb-3">
                        <span className={`text-xs px-2 py-0.5 rounded ${isPool ? 'bg-blue-100 text-blue-700 font-medium' : 'text-slate-400'}`}>Pool</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${isOW ? 'bg-blue-100 text-blue-700 font-medium' : 'text-slate-400'}`}>Open Water</span>
                    </div>
                )}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {availableEvents.map(event => (
                        <button
                            key={event}
                            type="button"
                            onClick={() => onChange({ event_type: event })}
                            className={`
                                p-2.5 rounded-lg border text-sm font-medium transition-all
                                ${data.event_type === event
                                    ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600'
                                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}
                            `}
                        >
                            {EventLabels[event]}
                        </button>
                    ))}
                </div>
            </div>

            {/* Event name (optional) */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                    Event Name <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                    type="text"
                    value={data.event_name || ''}
                    onChange={e => onChange({ event_name: e.target.value || undefined })}
                    placeholder="e.g. Perth City to Surf 2026"
                    className="w-full p-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            {/* Event date (optional) */}
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                    Event Date <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                    type="date"
                    value={data.event_date || ''}
                    onChange={e => onChange({ event_date: e.target.value || undefined })}
                    className="w-full p-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>
        </div>
    );
}
