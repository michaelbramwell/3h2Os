import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { type Workout, ActivityType } from '../types/schema'
import { updateWorkout } from '../lib/api'
import { X } from 'lucide-react'

interface EditWorkoutDialogProps {
    workout: Workout
    isOpen: boolean
    onOpenChange: (open: boolean) => void
}

export function EditWorkoutDialog({ workout, isOpen, onOpenChange }: EditWorkoutDialogProps) {
    const queryClient = useQueryClient()
    const [name, setName] = useState(workout.name)
    const [description, setDescription] = useState(workout.description || '') // Use empty string if undefined
    const [type, setType] = useState(workout.type)
    const [timeOfDay, setTimeOfDay] = useState(workout.timeOfDay || 'AM')
    const [distance, setDistance] = useState((workout.distance_m / 1000).toString())

    // Update state when workout changes or dialog opens
    useEffect(() => {
        if (isOpen) {
            setName(workout.name)
            setDescription(workout.description || '')
            setType(workout.type)
            setTimeOfDay(workout.timeOfDay || 'AM')
            setDistance((workout.distance_m / 1000).toString())
        }
    }, [isOpen, workout])

    const mutation = useMutation({
        mutationFn: async (updatedWorkout: { name: string; description: string; type: string; distance_m: number; timeOfDay: string }) => {
            if (!workout.id) throw new Error("Workout ID is missing")
            return updateWorkout(workout.id, updatedWorkout)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plan'] })
            onOpenChange(false)
        },
        onError: (error) => {
            console.error(error);
            alert("Failed to save workout. Ensure backend is running and workout has an ID.");
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

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden border border-slate-200">
                <div className="flex items-center justify-between p-4 border-b border-slate-100">
                    <h2 className="text-lg font-semibold text-slate-900">Edit Workout</h2>
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
                            {Object.values(ActivityType).map((t) => (
                                <option key={t} value={t}>{t}</option>
                            ))}
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

                <div className="p-4 bg-slate-50 flex justify-end gap-2 border-t border-slate-100">
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
    )
}
