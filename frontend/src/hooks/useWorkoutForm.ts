import { useState, useEffect } from 'react'
import { type Workout, ActivityType } from '../types/schema'

export function useWorkoutForm(workout: Workout | undefined, isOpen: boolean) {
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [type, setType] = useState<ActivityType>(ActivityType.RUN)
    const [timeOfDay, setTimeOfDay] = useState('AM')
    const [distance, setDistance] = useState('0')

    useEffect(() => {
        if (isOpen) {
            if (workout) {
                setName(workout.name)
                setDescription(workout.description || '')
                setType(workout.type)
                setTimeOfDay(workout.timeOfDay || 'AM')
                setDistance((workout.distance_m / 1000).toString())
            } else {
                // Reset for creation
                setName("New Workout")
                setDescription('')
                setType(ActivityType.RUN)
                setTimeOfDay("AM")
                setDistance("0")
            }
        }
    }, [isOpen, workout])

    return {
        name, setName,
        description, setDescription,
        type, setType,
        timeOfDay, setTimeOfDay,
        distance, setDistance
    }
}
