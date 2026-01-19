import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DayCard } from '../DayCard'

// Mock sub-components to isolate DayCard logic
vi.mock('../WorkoutCard', () => ({
    WorkoutCard: ({ workout }: any) => <div data-testid="workout-card">{workout.name}</div>
}))
vi.mock('../ActualCard', () => ({
    ActualCard: ({ activity }: any) => <div data-testid="actual-card">{activity.name}</div>
}))
vi.mock('../EditWorkoutDialog', () => ({
    EditWorkoutDialog: ({ isOpen }: any) => isOpen ? <div data-testid="edit-dialog">Dialog Open</div> : null
}))

describe('DayCard Integration', () => {
    const mockDay = {
        date: '2026-06-01',
        workouts: []
    }
    
    it('shows add button for future dates', async () => {
        const futureDate = '2026-06-01'
        const today = '2026-05-01' // Day is in future
        
        render(
            <DayCard 
                dayName="Mon" 
                day={{ ...mockDay, date: futureDate }} 
                actuals={[]} 
                todayStr={today} 
                weekStatus="normal" 
                onActivityClick={vi.fn()} 
            />
        )
        
        // Find add button
        const addButton = screen.getByTitle('Add Workout')
        expect(addButton).toBeInTheDocument()
        
        // Click and verify dialog opens
        fireEvent.click(addButton)
        expect(await screen.findByTestId('edit-dialog')).toBeInTheDocument()
    })

    it('hides add button for past dates', () => {
        const pastDate = '2026-04-01' 
        const today = '2026-05-01' // Day is in past
        
        render(
            <DayCard 
                dayName="Mon" 
                day={{ ...mockDay, date: pastDate }} 
                actuals={[]} 
                todayStr={today} 
                weekStatus="normal" 
                onActivityClick={vi.fn()} 
            />
        )
        
        const addButton = screen.queryByTitle('Add Workout')
        expect(addButton).not.toBeInTheDocument()
    })
})
