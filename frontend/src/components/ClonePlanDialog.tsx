import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { X, Copy, Loader2 } from 'lucide-react';
import { clonePlan } from '../lib/api';

interface ClonePlanDialogProps {
    isOpen: boolean;
    onClose: () => void;
    planId: number;
    planTitle: string;
}

export function ClonePlanDialog({ isOpen, onClose, planId, planTitle }: ClonePlanDialogProps) {
    const queryClient = useQueryClient();
    const [newTitle, setNewTitle] = useState(`${planTitle} (copy)`);
    const [dateOffsetWeeks, setDateOffsetWeeks] = useState(0);

    const mutation = useMutation({
        mutationFn: () => clonePlan(planId, {
            new_title: newTitle.trim(),
            date_offset_days: dateOffsetWeeks * 7,
        }),
        onSuccess: (result) => {
            toast.success(`Plan "${result.title}" cloned successfully.`);
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            queryClient.invalidateQueries({ queryKey: ['plan'] });
            queryClient.invalidateQueries({ queryKey: ['context'] });
            onClose();
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || 'Failed to clone plan.');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTitle.trim()) return;
        mutation.mutate();
    };

    if (!isOpen) return null;

    const content = (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                        <Copy size={16} className="text-slate-500" />
                        <h2 className="text-base font-semibold text-slate-900">Clone Plan</h2>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <form onSubmit={handleSubmit} className="p-5 space-y-4">
                    <div>
                        <label htmlFor="clone-title" className="block text-sm font-medium text-slate-700 mb-1">
                            New Plan Title
                        </label>
                        <input
                            id="clone-title"
                            type="text"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Enter plan title"
                            autoFocus
                        />
                    </div>

                    <div>
                        <label htmlFor="clone-offset" className="block text-sm font-medium text-slate-700 mb-1">
                            Date Offset (weeks)
                        </label>
                        <p className="text-xs text-slate-500 mb-2">
                            Shift all dates forward or backward by whole weeks to keep Monday alignment.
                        </p>
                        <div className="flex items-center gap-3">
                            <input
                                id="clone-offset"
                                type="number"
                                value={dateOffsetWeeks}
                                onChange={(e) => setDateOffsetWeeks(parseInt(e.target.value) || 0)}
                                className="w-28 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <span className="text-xs text-slate-400">
                                {dateOffsetWeeks === 0
                                    ? 'Same dates'
                                    : dateOffsetWeeks > 0
                                    ? `${dateOffsetWeeks} week${dateOffsetWeeks !== 1 ? 's' : ''} later`
                                    : `${Math.abs(dateOffsetWeeks)} week${Math.abs(dateOffsetWeeks) !== 1 ? 's' : ''} earlier`}
                            </span>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="flex justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={mutation.isPending || !newTitle.trim()}
                            className="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                        >
                            {mutation.isPending && (
                                <Loader2 size={14} className="animate-spin" />
                            )}
                            Clone Plan
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );

    return createPortal(content, document.body);
}
