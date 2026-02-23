import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPlans, activatePlan, deletePlan, getWizardSettings } from '../lib/api';
import { ChevronDown, Check, Loader2, Calendar, Trash2, Copy, Pencil } from 'lucide-react';
import { ClonePlanDialog } from './ClonePlanDialog';
import { toast } from 'sonner';
import type { WizardInput } from '../types/wizard';

interface PlanSwitcherProps {
    onEditPlan?: (planId: number, wizardData: WizardInput) => void;
}

export function PlanSwitcher({ onEditPlan }: PlanSwitcherProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [clonePlan, setClonePlan] = useState<{ id: number; title: string } | null>(null);
    const [loadingEditId, setLoadingEditId] = useState<number | null>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const queryClient = useQueryClient();

    const { data: plans, isLoading } = useQuery({
        queryKey: ['plans'],
        queryFn: getPlans,
    });

    const activateMutation = useMutation({
        mutationFn: activatePlan,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plan'] }); // Active plan content
            queryClient.invalidateQueries({ queryKey: ['plans'] }); // Plan list (active status)
            queryClient.invalidateQueries({ queryKey: ['actuals'] }); // Refetch actuals based on new plan type
            queryClient.invalidateQueries({ queryKey: ['context'] }); // Refresh sidebar project context
            setIsOpen(false);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: deletePlan,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            queryClient.invalidateQueries({ queryKey: ['plan'] });
        },
    });

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleClone = (e: React.MouseEvent, planId: number, planTitle: string) => {
        e.stopPropagation();
        setClonePlan({ id: planId, title: planTitle });
        setIsOpen(false);
    };

    const handleEdit = async (e: React.MouseEvent, planId: number) => {
        e.stopPropagation();
        if (!onEditPlan) return;
        setLoadingEditId(planId);
        try {
            const wizardData = await getWizardSettings(planId);
            setIsOpen(false);
            onEditPlan(planId, wizardData);
        } catch (err: any) {
            const detail = err?.response?.data?.detail;
            if (err?.response?.status === 404) {
                toast.error(detail || 'This plan was not created with the wizard and cannot be edited here.');
            } else {
                toast.error(detail || 'Failed to load plan settings.');
            }
        } finally {
            setLoadingEditId(null);
        }
    };

    const handleDelete = (e: React.MouseEvent, planId: number, planTitle: string) => {
        e.stopPropagation();
        if (window.confirm(`Are you sure you want to delete "${planTitle}"? This cannot be undone.`)) {
            deleteMutation.mutate(planId);
        }
    };

    const activePlan = plans?.find(p => p.is_active);

    if (isLoading) return <div className="w-32 h-8 bg-slate-100 rounded-full animate-pulse border border-slate-200"></div>;

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 bg-white/50 backdrop-blur px-3 py-1.5 rounded-full border border-slate-200 hover:bg-white/80 transition"
            >
                <span className="text-xs font-medium text-slate-700 max-w-[150px] truncate">
                    {activePlan ? activePlan.title : "Select Plan"}
                </span>
                <ChevronDown size={14} className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute top-full right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-100 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100">
                    <div className="max-h-[300px] overflow-y-auto py-1">
                        {!plans || plans.length === 0 ? (
                            <div className="px-4 py-3 text-sm text-slate-500 text-center italic">
                                No saved plans found.
                            </div>
                        ) : (
                            plans.map((plan) => {
                                const isManual = plan.wizard_input_json?.includes('"event_type":"none"') || plan.wizard_input_json?.includes('"event_type": "none"');
                                return (
                                <div 
                                    key={plan.id}
                                    className="relative group/item hover:bg-slate-50 transition"
                                >
                                    <button
                                        onClick={() => activateMutation.mutate(plan.id)}
                                        disabled={plan.is_active || activateMutation.isPending}
                                        className="w-full text-left px-4 py-3 flex items-center justify-between"
                                    >
                                        <div className="min-w-0 pr-16">
                                            <div className={`font-medium text-sm truncate ${plan.is_active ? 'text-blue-600' : 'text-slate-700'}`}>
                                                {plan.title}
                                            </div>
                                            <div className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                                                <span className={`capitalize ${plan.type === 'swimming' ? 'text-cyan-600' : ''}`}>{plan.type}</span>
                                                <span>•</span>
                                                <Calendar size={10} />
                                                <span>{new Date(plan.created_at).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                        {plan.is_active && (
                                            <Check size={16} className="text-blue-500 shrink-0 ml-2" />
                                        )}
                                        {activateMutation.isPending && activateMutation.variables === plan.id && (
                                            <Loader2 size={16} className="animate-spin text-blue-500 shrink-0 ml-2" />
                                        )}
                                    </button>
                                    
                                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-all">
                                        {onEditPlan && !isManual && (
                                            <button
                                                onClick={(e) => handleEdit(e, plan.id)}
                                                className="p-2 text-slate-300 hover:text-amber-500 hover:bg-amber-50 rounded-md transition-all"
                                                title="Edit Plan Settings"
                                                disabled={loadingEditId === plan.id}
                                            >
                                                {loadingEditId === plan.id ? (
                                                    <Loader2 size={14} className="animate-spin" />
                                                ) : (
                                                    <Pencil size={14} />
                                                )}
                                            </button>
                                        )}
                                        <button
                                            onClick={(e) => handleClone(e, plan.id, plan.title)}
                                            className="p-2 text-slate-300 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-all"
                                            title="Clone Plan"
                                        >
                                            <Copy size={14} />
                                        </button>
                                        {!plan.is_active && (
                                            <button
                                                onClick={(e) => handleDelete(e, plan.id, plan.title)}
                                                className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-md transition-all"
                                                title="Delete Plan"
                                                disabled={deleteMutation.isPending}
                                            >
                                                {deleteMutation.isPending && deleteMutation.variables === plan.id ? (
                                                    <Loader2 size={14} className="animate-spin" />
                                                ) : (
                                                    <Trash2 size={14} />
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                            })
                        )}
                    </div>
                </div>
            )}

            <ClonePlanDialog
                isOpen={!!clonePlan}
                onClose={() => setClonePlan(null)}
                planId={clonePlan?.id ?? 0}
                planTitle={clonePlan?.title ?? ''}
            />
        </div>
    );
}
