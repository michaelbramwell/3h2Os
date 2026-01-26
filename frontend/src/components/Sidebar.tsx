import type { ContextData, RunnerContext, FuelingStrategy } from '../types/schema';
import { WeightChart } from './WeightChart';
import { ContextSection } from './ContextSection';
import { getZoneLabel } from '../lib/calculations';

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
    
    // Display recent weight history chart
    
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Weight Tracker</h2>
            <div className="flex items-end gap-2">
                <p className="text-2xl font-bold text-slate-900">{weight.current}kg</p>
                <p className="text-sm text-slate-500 mb-1">/ {weight.target}kg target</p>
            </div>
            
            <div className="mt-4 h-32">
                <WeightChart data={weight} />
            </div>
        </div>
    );
}

function FuelingCard({ fueling }: { fueling?: FuelingStrategy }) {
    if (!fueling) return null;
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Fueling Audit</h2>
            <div className="space-y-3">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <p className="text-xs text-slate-600">{fueling.carbsPerHr}g Carbs / hour (Long Runs)</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <p className="text-xs text-slate-600">{fueling.sodiumPerHr}mg Sodium / hour</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <p className="text-xs text-slate-600">Pre-run: {fueling.preRunCarbs}g Carbs</p>
                </div>
            </div>
        </div>
    );
}

function ZonesCard({ zones }: { zones: RunnerContext['trainingZones'] }) {
    if (!zones || !zones.pace || zones.pace.length === 0) return null;

    // Helper to strip the prefix label "Easy (Z2): " -> "5:30-6:00"
    const getRangeOnly = (label: string) => {
        const parts = label.split(': ');
        return parts.length > 1 ? parts[1] : '--';
    };

    // Use pure calculation function
    const easyRange = getRangeOnly(getZoneLabel('Easy', zones.pace));
    const tempoRange = getRangeOnly(getZoneLabel('Tempo', zones.pace));
    const threshRange = getRangeOnly(getZoneLabel('Threshold', zones.pace));
    const vo2Range = getRangeOnly(getZoneLabel('VO2 Max', zones.pace));

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Training Paces</h2>
            <div className="space-y-3">
                 <div className="flex justify-between items-center border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                    <div className="flex flex-col">
                        <span className="text-sm font-bold text-slate-700">Easy</span>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wide">Zone 2</span>
                    </div>
                    <span className="font-mono text-sm text-slate-600">{easyRange}</span>
                 </div>

                 <div className="flex justify-between items-center border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                    <div className="flex flex-col">
                        <span className="text-sm font-bold text-slate-700">Tempo</span>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wide">Zone 3</span>
                    </div>
                    <span className="font-mono text-sm text-slate-600">{tempoRange}</span>
                 </div>

                 <div className="flex justify-between items-center border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                    <div className="flex flex-col">
                        <span className="text-sm font-bold text-slate-700">Threshold</span>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wide">Zone 4 (LT)</span>
                    </div>
                    <span className="font-mono text-sm text-red-600">{threshRange}</span>
                 </div>

                 <div className="flex justify-between items-center border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                    <div className="flex flex-col">
                        <span className="text-sm font-bold text-slate-700">VO2 Max</span>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wide">Zone 5</span>
                    </div>
                    <span className="font-mono text-sm text-purple-600">{vo2Range}</span>
                 </div>
            </div>
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
            <div className="flex items-center gap-3 px-1 mb-2 opacity-80">
                <img src="/3h2os-waves.svg" alt="3h2Os Logo" className="w-10 h-10" />
                <span className="text-2xl font-bold text-slate-700 tracking-tight">3h2Os</span>
            </div>
            <GoalCard project={context.project} />
            <PhaseCard status={context.status} />
            <WeightCard weight={context.runner.weight_kg} />
            <FuelingCard fueling={context.runner.fueling} />
            <ZonesCard zones={context.runner.trainingZones} />
            <GarminStatusCard />
            {markdown && <ContextSection markdown={markdown} />}
        </div>
    );
}
