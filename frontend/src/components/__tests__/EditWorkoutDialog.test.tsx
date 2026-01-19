import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EditWorkoutDialog } from '../EditWorkoutDialog'
import { ActivityType } from '../../types/schema'
import * as api from '../../lib/api'

// Mock react-query
const mockInvalidateQueries = vi.fn()
vi.mock('@tanstack/react-query', () => ({
    useQueryClient: () => ({
        invalidateQueries: mockInvalidateQueries
    }),
    useMutation: (options: any) => {
        return {
            mutate: (variables: any) => {
                // Simulate async API call
                Promise.resolve(options.mutationFn(variables))
                    .then((res: any) => {
                        options.onSuccess && options.onSuccess(res)
                    })
                    .catch((err: any) => {
                        options.onError && options.onError(err)
                    })
            },
            isPending: false
        }
    }
}))

// Mock API functions
vi.mock('../../lib/api', () => ({
    updateWorkout: vi.fn().mockResolvedValue({}),
    createWorkout: vi.fn().mockResolvedValue({}),
    deleteWorkout: vi.fn().mockResolvedValue({})
}))

// Mock sonner
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn()
    }
}))

// Mock lucide icons to avoid issues
vi.mock('lucide-react', () => ({
    X: () => <div data-testid="icon-x" />,
    Trash2: () => <div data-testid="icon-trash" />,
    AlertTriangle: () => <div data-testid="icon-alert" />
}))

const mockWorkout = {
    id: 123,
    name: "Existing Run",
    type: ActivityType.RUN,
    distance_m: 5000,
    timeOfDay: "AM",
    description: "Notes"
}

describe('EditWorkoutDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders correctly in Edit mode', () => {
        render(<EditWorkoutDialog workout={mockWorkout} isOpen={true} onOpenChange={vi.fn()} />)
        
        expect(screen.getByText('Edit Workout')).toBeDefined()
        expect(screen.getByDisplayValue('Existing Run')).toBeDefined()
        expect(screen.getByDisplayValue('5')).toBeDefined() // 5000m -> 5km
        
        // Check for delete button
        expect(screen.getByTitle('Delete Workout')).toBeDefined()
    })

    it('renders correctly in Create mode', () => {
        render(<EditWorkoutDialog date="2026-01-01" isOpen={true} onOpenChange={vi.fn()} />)
        
        expect(screen.getByText('Add Workout')).toBeDefined()
        // Delete button should not exist
        expect(screen.queryByTitle('Delete Workout')).toBeNull()
    })

    it('calls updateWorkout on save', async () => {
        render(<EditWorkoutDialog workout={mockWorkout} isOpen={true} onOpenChange={vi.fn()} />)
        
        // Change name
        fireEvent.change(screen.getByDisplayValue('Existing Run'), { target: { value: 'Updated Run' } })
        
        // Click Save
        fireEvent.click(screen.getByText('Save Changes'))
        
        expect(api.updateWorkout).toHaveBeenCalledWith(
            123, 
            expect.objectContaining({ name: 'Updated Run', distance_m: 5000 }), 
            false
        )
        await waitFor(() => {
             expect(mockInvalidateQueries).toHaveBeenCalled()
        })
    })

    it('opens confirm dialog on delete click', () => {
        render(<EditWorkoutDialog workout={mockWorkout} isOpen={true} onOpenChange={vi.fn()} />)
        
        fireEvent.click(screen.getByTitle('Delete Workout'))
        
        expect(screen.getByText('Delete Workout')).toBeDefined() // Dialog Title
        expect(screen.getByText(/Are you sure/)).toBeDefined() // Description
    })

    it('calls deleteWorkout when confirmed', async () => {
        render(<EditWorkoutDialog workout={mockWorkout} isOpen={true} onOpenChange={vi.fn()} />)
        
        // Open delete confirmaton
        fireEvent.click(screen.getByTitle('Delete Workout'))
        
        // Confirm - The ConfirmDialog uses a button with text "Confirm" by default
        const confirmBtn = screen.getByRole('button', { name: "Confirm" })
        fireEvent.click(confirmBtn)
        
        expect(api.deleteWorkout).toHaveBeenCalledWith(123)
        await waitFor(() => {
             expect(mockInvalidateQueries).toHaveBeenCalled()
        })
    })
})
