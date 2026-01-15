import type { ContextData, RunnerContext } from '../types/schema';
import { WeightChart } from './WeightChart';
import { ContextSection } from './ContextSection';

interface SidebarProps {
    context: ContextData;
    markdown?: string;
}

function GoalCard({ project }: { project: ContextData['project'] }) {
    if (!project) return null;
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Goal</h2>
            <p className="text-2xl font-bold text-slate-900">{project.goal}</p>
            <p className="text-sm text-slate-500 mt-1">{project.event} • {new Date(project.eventDate).toLocaleDateString('en-AU', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
        </div>
    );
}

function PhaseCard({ status }: { status: ContextData['status'] }) {
    if (!status) return null;
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Current Phase</h2>
            <p className="text-lg font-bold text-slate-900">{status.phase}</p>
            <p className="text-sm text-slate-500 mt-1">{status.nextAction || 'Ongoing'}</p>
        </div>
    );
}

function WeightCard({ weight }: { weight: RunnerContext['weight_kg'] }) {
    if (!weight) return null;
    
    // Better progress calculation: (Start - Current) / (Start - Target)
    // Assuming history[0] is start. Or just context.weight_kg.history[0] if available.
    // Actually let's just use current vs target for display.
    
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Weight Tracker</h2>
            <div className="flex items-end gap-2">
                <p className="text-2xl font-bold text-slate-900">{weight.current}kg</p>
                <p className="text-sm text-slate-500 mb-1">/ {weight.target}kg target</p>
            </div>
            {/* <div className="w-full bg-slate-100 h-2 rounded-full mt-3">
                <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${progress}%` }}></div>
            </div> */} 
            {/* Progress bar seems tricky without consistent start weight. Skipping specific percent for now, just chart. */}
            
            <div className="mt-4 h-32">
                <WeightChart data={weight} />
            </div>
        </div>
    );
}

function FuelingCard() {
    // Hardcoded for now based on legacy HTML as it doesn't seem to be in JSON fully structured
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Fueling Audit</h2>
            <div className="space-y-3">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <p className="text-xs text-slate-600">90g Carbs / hour (Long Runs)</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <p className="text-xs text-slate-600">900mg Sodium / hour</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <p className="text-xs text-slate-600">Pre-run: 50g Carbs</p>
                </div>
            </div>
        </div>
    );
}

function formatPace(speedMs: number | undefined): string {
    if (!speedMs || speedMs === 0) return '--:--';
    const secondsPerKm = 1000 / speedMs;
    const min = Math.floor(secondsPerKm / 60);
    const sec = Math.floor(secondsPerKm % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
}

function ZonesCard({ zones }: { zones: RunnerContext['trainingZones'] }) {
    if (!zones) return null;

    const renderPaceRow = (z: any, idx: number, all: any[]) => {
        // Current Zone Start (Slowest speed for this zone)
        const currentZoneStartSpeed = z.lowBoundary_m_s;
        
        // Next Zone Start (Fastest speed for this zone - effectively)
        const nextZone = all[idx + 1];
        const nextZoneStartSpeed = nextZone?.lowBoundary_m_s;

        // Calculate Paces (min/km)
        // Speed = m/s. Pace = 1000/Speed s/km.
        // Higher speed = Lower Pace number.
        
        // Z1: 0.5 m/s. Next: 2.688 m/s.
        // Z1 is everything from 0.5 to 2.688. 
        // Display: "> 6:12 min/km" (slower than Z2 start).
        
        let rangeLabel = '';
        
        if (z.zone === 1 && nextZoneStartSpeed) {
             const limit = formatPace(nextZoneStartSpeed);
             rangeLabel = `> ${limit}`;
        } else if (!nextZone) {
            // Last Zone (Z6)
             const limit = formatPace(currentZoneStartSpeed);
             rangeLabel = `< ${limit}`;
        } else {
            // Middle Zones
            const slowerLimit = formatPace(currentZoneStartSpeed);
            const fasterLimit = formatPace(nextZoneStartSpeed);
            rangeLabel = `${fasterLimit} - ${slowerLimit}`;
        }

        return (
            <tr key={z.zone} className="border-b border-slate-100 last:border-0 text-sm">
                <td className="py-2 pl-2 font-bold text-slate-500">Z{z.zone}</td>
                <td className="py-2 pr-2 text-left font-mono text-slate-700">{rangeLabel} min/km</td>
            </tr>
        );
    };

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Training Zones (Pace)</h2>
            <table className="w-full">
                <thead>
                    <tr className="border-b border-slate-200 text-xs uppercase text-slate-400">
                        <th className="py-2 pl-2 text-left font-semibold">Zone</th>
                        <th className="py-2 pr-2 text-left font-semibold">Pace Range</th>
                    </tr>
                </thead>
                <tbody>
                    {zones.pace.map((z, i) => renderPaceRow(z, i, zones.pace))}
                </tbody>
            </table>
        </div>
    );
}

function GarminStatusCard() {
    // Static for now, requires live check or separate query
    return (
       <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Garmin Status</h2>
            <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <p className="text-sm font-medium text-slate-900">Synced</p>
            </div>
        </div>
    );
}

export function Sidebar({ context, markdown }: SidebarProps) {
    return (
        <div className="space-y-6">
            <GoalCard project={context.project} />
            <PhaseCard status={context.status} />
            <WeightCard weight={context.runner.weight_kg} />
            <FuelingCard />
            <ZonesCard zones={context.runner.trainingZones} />
            <GarminStatusCard />
            {markdown && <ContextSection markdown={markdown} />}
        </div>
    );
}
