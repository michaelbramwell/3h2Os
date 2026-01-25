import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPortal } from 'react-dom'
import { toast } from 'sonner'
import { type Workout, ActivityType } from '../types/schema'
import { updateWorkout, createWorkout, deleteWorkout } from '../lib/api'
import { X, Trash2 } from 'lucide-react'
import { useWorkoutForm } from '../hooks/useWorkoutForm'
import { ConfirmDialog } from './ui/ConfirmDialog'

interface EditWorkoutDialogProps {
    workout?: Workout;
    date?: string;
    isOpen: boolean
    onOpenChange: (open: boolean) => void
}

export function EditWorkoutDialog({ workout, date, isOpen, onOpenChange }: EditWorkoutDialogProps) {
    const queryClient = useQueryClient();
    const isEditing = !!workout;
    const [confirmConfig, setConfirmConfig] = useState<{
        isOpen: boolean;
        title: string;
        description: string;
        variant: 'danger' | 'warning';
        onConfirm: () => void;
    }>({
        isOpen: false,
        title: '',
        description: '',
        variant: 'danger',
        onConfirm: () => {}
    });

    if (isEditing && !workout.id) {
        console.warn("EditWorkoutDialog opened with workout missing ID:", workout);
    }

    const {
        name, setName,
        description, setDescription,
        type, setType,
        timeOfDay, setTimeOfDay,
        distance, setDistance
    } = useWorkoutForm(workout, isOpen);

    const mutation = useMutation({
        mutationFn: async (data: { name: string; description: string; type: string; distance_m: number; timeOfDay: string; force?: boolean }) => {
            const force = data.force || false;
            const apiData = { ...data };
            if ('force' in apiData) delete (apiData as any).force;

            if (isEditing) {
                // If editing, try to use ID, but fallback to creating new if ID is missing (which shouldn't happen for existing workouts)
                // However, the error suggests workout.id is undefined.
                // In PlanWorkout model, id is optional but should be present for fetched data.
                if (workout?.id) {
                     return updateWorkout(workout.id, apiData, force)
                } else {
                     console.error("Attempting to edit workout without ID:", workout);
                     throw new Error("Cannot update workout: Missing ID. Try refreshing the page.");
                }
            } else if (!isEditing && date) {
                return createWorkout({ ...apiData, date }, force)
            } else {
                throw new Error("Invalid state: Missing ID for edit or Date for create")
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plan'] })
            toast.success(isEditing ? 'Workout updated successfully' : 'Workout created successfully')
            onOpenChange(false)
        },
        onError: (error: any) => {
            if (error.response && error.response.status === 409) {
                 const warningMsg = error.response.data.message || "Validation warning.";
                 
                 setConfirmConfig({
                     isOpen: true,
                     title: "Plan Validation Warning",
                     description: `${warningMsg}\n\nDo you want to save anyway?`,
                     variant: 'warning',
                     onConfirm: () => {
                         const distanceM = parseFloat(distance) * 1000
                         mutation.mutate({
                             name,
                             description,
                             type,
                             distance_m: distanceM,
                             timeOfDay,
                             force: true
                         })
                         setConfirmConfig(prev => ({ ...prev, isOpen: false }))
                     }
                 })
            } else {
                console.error(error);
                toast.error("Failed to save workout. " + (error.response?.data?.detail || error.message || error));
            }
        }
    })

    const handleSave = () => {
        const distanceM = parseFloat(distance) * 1000
        mutation.mutate({
            name,
            description,
            type,
            distance_m: distanceM,
            timeOfDay
        })
    }

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            return deleteWorkout(id)
        },
        onSuccess: () => {
             queryClient.invalidateQueries({ queryKey: ['plan'] })
             toast.success('Workout deleted successfully')
             onOpenChange(false)
        },
        onError: (error: any) => {
             console.error(error);
             toast.error("Failed to delete workout. " + (error.response?.data?.detail || error.message || error));
        }
    })

    const handleDelete = () => {
        if (!workout?.id) return;
        
        setConfirmConfig({
            isOpen: true,
            title: "Delete Workout",
            description: "Are you sure you want to delete this workout? This action cannot be undone.",
            variant: 'danger',
            onConfirm: () => {
                deleteMutation.mutate(workout.id!);
                setConfirmConfig(prev => ({ ...prev, isOpen: false }))
            }
        });
    }

    if (!isOpen) return null

    return createPortal(
        <>
            <ConfirmDialog
                isOpen={confirmConfig.isOpen}
                title={confirmConfig.title}
                description={confirmConfig.description}
                variant={confirmConfig.variant}
                onConfirm={confirmConfig.onConfirm}
                onCancel={() => setConfirmConfig(prev => ({ ...prev, isOpen: false }))}
            />

            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden border border-slate-200">
                <div className="flex items-center justify-between p-4 border-b border-slate-100">
                    <h2 className="text-lg font-semibold text-slate-900">{isEditing ? 'Edit Workout' : 'Add Workout'}</h2>
                    <button onClick={() => onOpenChange(false)} className="text-slate-400 hover:text-slate-600">
                        <X size={20} />
                    </button>
                </div>
                
                <div className="p-4 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">Type</label>
                        <select 
                            value={type} 
                            onChange={(e) => setType(e.target.value as ActivityType)}
                            className="w-full p-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value={ActivityType.RUN}>Running</option>
                            <option value={ActivityType.TRAIL}>Trail Running</option>
                            <option value={ActivityType.CYCLING}>Cycling</option>
                            <option value={ActivityType.SWIMMING}>Swimming</option>
                            
                            {/* Preserve current value if not in standard list to avoid data loss */}
                            {!( [ActivityType.RUN, ActivityType.TRAIL, ActivityType.CYCLING, ActivityType.SWIMMING] as ActivityType[] ).includes(type as ActivityType) && (
                                <option value={type}>{type} (Legacy)</option>
                            )}
                        </select>
                    </div>

                    <div className="flex gap-4">
                        <div className="space-y-2 flex-grow">
                            <label className="text-sm font-medium text-slate-700">Distance (km)</label>
                            <input
                                type="number"
                                step="0.1"
                                value={distance}
                                onChange={(e) => setDistance(e.target.value)}
                                className="w-full p-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div className="space-y-2 w-1/3">
                            <label className="text-sm font-medium text-slate-700">Time</label>
                            <select 
                                value={timeOfDay} 
                                onChange={(e) => setTimeOfDay(e.target.value)}
                                className="w-full p-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="AM">AM</option>
                                <option value="PM">PM</option>
                            </select>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full p-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">Notes</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="w-full p-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px]"
                        />
                    </div>
                </div>

                <div className="p-4 bg-slate-50 flex justify-between items-center border-t border-slate-100">
                    <div>
                        {isEditing && (
                            <button
                                onClick={handleDelete}
                                disabled={deleteMutation.isPending}
                                className="p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                                title="Delete Workout"
                            >
                                <Trash2 size={20} />
                            </button>
                        )}
                    </div>
                    <div className="flex gap-2">
                        <button 
                            onClick={() => onOpenChange(false)}
                            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 rounded-md transition-colors"
                        >
                            Cancel
                        </button>
                        <button 
                            onClick={handleSave}
                            disabled={mutation.isPending}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50"
                        >
                            {mutation.isPending ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </div>
            </div>
            </div>
        </>,
        document.body
    )
}
