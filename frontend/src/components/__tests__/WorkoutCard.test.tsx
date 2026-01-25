import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { WorkoutCard } from '../WorkoutCard'
import type { Workout } from '../../types/schema'

// Mock the dialog component to avoid provider issues and isolate unit test
vi.mock('../EditWorkoutDialog', () => ({
    EditWorkoutDialog: ({ isOpen }: { isOpen: boolean }) => (
        <div data-testid="edit-dialog" data-state={isOpen ? 'open' : 'closed'} />
    )
}))

// Mock lucide-react to verify icons
vi.mock('lucide-react', () => ({
    Pencil: () => <div data-testid="icon-pencil" />,
    Sun: () => <div data-testid="icon-sun" />,
    Moon: () => <div data-testid="icon-moon" />
}))

const mockWorkout: Workout = {
    id: 1,
    name: "Test Run",
    type: "General Aerobic",
    distance_m: 5000,
    timeOfDay: "AM",
    description: undefined // Undefined description to show Name
}

describe('WorkoutCard', () => {
    it('renders basic workout info', () => {
        render(<WorkoutCard workout={mockWorkout} isToday={false} isMarathonDay={false} isPast={false} />)
        expect(screen.getByText('General Aerobic')).toBeDefined() // The Type
        expect(screen.getByText('Test Run')).toBeDefined() // The Name (fallback)
        expect(screen.getByText(/5.0km/)).toBeDefined() // Distance
        expect(screen.getByText('AM')).toBeDefined()
        expect(screen.getByTestId('icon-sun')).toBeDefined()
    })

    it('shows PM icon when timeOfDay is PM', () => {
        const pmWorkout = { ...mockWorkout, timeOfDay: "PM" }
        render(<WorkoutCard workout={pmWorkout} isToday={false} isMarathonDay={false} isPast={false} />)
        expect(screen.getByText('PM')).toBeDefined()
        expect(screen.getByTestId('icon-moon')).toBeDefined()
    })

    it('shows Pencil icon when future (editable)', () => {
        render(<WorkoutCard workout={mockWorkout} isToday={false} isMarathonDay={false} isPast={false} />)
        expect(screen.getByTestId('icon-pencil')).toBeDefined()
    })

    it('hides Pencil icon when past (not editable)', () => {
        render(<WorkoutCard workout={mockWorkout} isToday={false} isMarathonDay={false} isPast={true} />)
        expect(screen.queryByTestId('icon-pencil')).toBeNull()
    })

    it('clicking opens dialog when future', () => {
        render(<WorkoutCard workout={mockWorkout} isToday={false} isMarathonDay={false} isPast={false} />)
        
        const card = screen.getByText('Test Run').closest('div')
        fireEvent.click(card!)
        
        const dialog = screen.getByTestId('edit-dialog')
        expect(dialog.getAttribute('data-state')).toBe('open')
    })

    it('clicking does NOT open dialog when past', () => {
        render(<WorkoutCard workout={mockWorkout} isToday={false} isMarathonDay={false} isPast={true} />)
        
        const card = screen.getByText('Test Run').closest('div')
        fireEvent.click(card!)
        
        const dialog = screen.getByTestId('edit-dialog')
        expect(dialog.getAttribute('data-state')).toBe('closed')
    })
})
