import { useEffect } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Title } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import type { PlanPreview } from '../../types/wizard';
import { EventLabels } from '../../types/wizard';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Title);

interface StepReviewProps {
    preview: PlanPreview | null;
    previewLoading: boolean;
    previewError: string | null;
    onLoadPreview: () => void;
    submitting: boolean;
    submitError: string | null;
    onSubmit: () => void;
    isEditMode?: boolean;
}

export function StepReview({
    preview,
    previewLoading,
    previewError,
    onLoadPreview,
    submitError,
    isEditMode,
}: StepReviewProps) {
    // Load preview on mount
    useEffect(() => {
        if (!preview && !previewLoading) {
            onLoadPreview();
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    if (previewLoading) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <p className="mt-3 text-sm text-slate-500">Generating preview...</p>
            </div>
        );
    }

    if (previewError) {
        return (
            <div className="space-y-4">
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-700">{previewError}</p>
                </div>
                <button
                    type="button"
                    onClick={onLoadPreview}
                    className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!preview) return null;

    // Build chart data
    const chartData = {
        labels: preview.weekly_volumes_m.map((_, i) => `W${i + 1}`),
        datasets: [
            {
                label: 'Weekly Volume (km)',
                data: preview.weekly_volumes_m.map(v => Math.round(v / 100) / 10),
                backgroundColor: preview.weekly_volumes_m.map((_, i) => {
                    // Color by phase
                    let weekCount = 0;
                    for (const phase of preview.phases) {
                        weekCount += phase.weeks;
                        if (i < weekCount) {
                            switch (phase.name.toLowerCase()) {
                                case 'base': return 'rgba(59, 130, 246, 0.5)';
                                case 'build': return 'rgba(34, 197, 94, 0.5)';
                                case 'peak': return 'rgba(245, 158, 11, 0.5)';
                                case 'taper': return 'rgba(168, 85, 247, 0.5)';
                                case 'race': return 'rgba(239, 68, 68, 0.5)';
                                default: return 'rgba(148, 163, 184, 0.5)';
                            }
                        }
                    }
                    return 'rgba(148, 163, 184, 0.5)';
                }),
                borderColor: preview.weekly_volumes_m.map((_, i) => {
                    let weekCount = 0;
                    for (const phase of preview.phases) {
                        weekCount += phase.weeks;
                        if (i < weekCount) {
                            switch (phase.name.toLowerCase()) {
                                case 'base': return 'rgb(59, 130, 246)';
                                case 'build': return 'rgb(34, 197, 94)';
                                case 'peak': return 'rgb(245, 158, 11)';
                                case 'taper': return 'rgb(168, 85, 247)';
                                case 'race': return 'rgb(239, 68, 68)';
                                default: return 'rgb(148, 163, 184)';
                            }
                        }
                    }
                    return 'rgb(148, 163, 184)';
                }),
                borderWidth: 1,
                borderRadius: 3,
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: { display: false },
            tooltip: {
                callbacks: {
                    label: (ctx: any) => `${ctx.parsed.y} km`,
                },
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                title: { display: true, text: 'km' },
            },
        },
    };

    const phaseColors: Record<string, string> = {
        base: 'bg-blue-500',
        build: 'bg-green-500',
        peak: 'bg-amber-500',
        taper: 'bg-purple-500',
        race: 'bg-red-500',
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-slate-900 mb-1">Review & Confirm</h2>
                <p className="text-sm text-slate-500">
                    {isEditMode
                        ? 'Review the updated plan. This will regenerate all weeks and workouts.'
                        : 'Review your plan before creating it.'}
                </p>
            </div>

            {/* Plan summary */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <h3 className="font-semibold text-slate-900 text-sm">{preview.title}</h3>
                <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                        <p className="text-xs text-slate-500">Event</p>
                        <p className="text-sm font-medium text-slate-900">
                            {EventLabels[preview.event_type] || preview.event_type}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-500">Duration</p>
                        <p className="text-sm font-medium text-slate-900">{preview.total_weeks} weeks</p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-500">Sessions/week</p>
                        <p className="text-sm font-medium text-slate-900">{preview.sessions_per_week}</p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-500">Peak volume</p>
                        <p className="text-sm font-medium text-slate-900">
                            {(preview.peak_weekly_volume_m / 1000).toFixed(0)} km
                        </p>
                    </div>
                </div>
            </div>

            {/* Phase breakdown */}
            <div>
                <h3 className="text-sm font-medium text-slate-700 mb-2">Training Phases</h3>
                <div className="flex rounded-lg overflow-hidden h-3 bg-slate-100">
                    {preview.phases.map(phase => (
                        <div
                            key={phase.name}
                            className={`${phaseColors[phase.name.toLowerCase()] || 'bg-slate-400'}`}
                            style={{ width: `${(phase.weeks / preview.total_weeks) * 100}%` }}
                            title={`${phase.name}: ${phase.weeks} weeks`}
                        />
                    ))}
                </div>
                <div className="mt-2 flex flex-wrap gap-3">
                    {preview.phases.map(phase => (
                        <div key={phase.name} className="flex items-center gap-1.5">
                            <div className={`w-2.5 h-2.5 rounded-sm ${phaseColors[phase.name.toLowerCase()] || 'bg-slate-400'}`} />
                            <span className="text-xs text-slate-600">
                                {phase.name} ({phase.weeks}w)
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Volume chart */}
            <div>
                <h3 className="text-sm font-medium text-slate-700 mb-2">Weekly Volume</h3>
                <div className="h-48 bg-white border border-slate-200 rounded-lg p-3">
                    <Bar data={chartData} options={chartOptions} />
                </div>
            </div>

            {/* Submit error */}
            {submitError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-700">{submitError}</p>
                </div>
            )}
        </div>
    );
}
