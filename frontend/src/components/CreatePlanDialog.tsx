import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createPlan } from '../lib/api';
import { Plus, X, Loader2 } from 'lucide-react';

interface CreatePlanDialogProps {
    onClose: () => void;
}

export function CreatePlanDialog({ onClose }: CreatePlanDialogProps) {
    const [title, setTitle] = useState('');
    const [type, setType] = useState('running');
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: async () => {
            await createPlan(title, type);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plan'] });
            onClose();
        },
    });

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
                <div className="bg-slate-50 border-b border-slate-100 p-4 flex justify-between items-center">
                    <h3 className="font-bold text-slate-800 flex items-center gap-2">
                        <Plus size={18} className="text-blue-500" />
                        Create New Plan
                    </h3>
                    <button 
                        onClick={onClose}
                        className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-200 rounded-full"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                            Plan Title
                        </label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="e.g. Winter Training 2026"
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                            autoFocus
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                            Plan Type
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                type="button"
                                onClick={() => setType('running')}
                                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                                    type === 'running'
                                        ? 'bg-blue-50 border-blue-200 text-blue-700 ring-2 ring-blue-500 ring-offset-1'
                                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                                }`}
                            >
                                Running
                            </button>
                            <button
                                type="button"
                                onClick={() => setType('swimming')}
                                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                                    type === 'swimming'
                                        ? 'bg-cyan-50 border-cyan-200 text-cyan-700 ring-2 ring-cyan-500 ring-offset-1'
                                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                                }`}
                            >
                                Swimming
                            </button>
                        </div>
                    </div>

                    <div className="pt-2 flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => mutation.mutate()}
                            disabled={!title || mutation.isPending}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {mutation.isPending && <Loader2 size={16} className="animate-spin" />}
                            Create Plan
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
