import { render, screen, fireEvent } from '@testing-library/react';
import { ActivityModal } from '../ActivityModal';
import { describe, it, expect, vi } from 'vitest';
import type { Activity } from '../../types/schema';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../hooks/useFeatureFlags', () => ({
    useFeatureFlags: () => ({ isSwimmingEnabled: false, isGarminEnabled: false }),
}));

const queryClient = new QueryClient({
    defaultOptions: {
        queries: { retry: false },
    },
});

const renderWithClient = (ui: React.ReactElement) => {
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

const mockActivityWithSplits: Activity = {
    activityId: 101,
    date: '2026-01-20',
    name: 'Splits Test Run',
    type: 'running',
    distance_m: 5000,
    duration_s: 1500,
    average_pace_m_s: 3.33,
    splits: [
        { distance: 1000, averageSpeed: 3.33, averageHR: 140 },
        { distance: 1000, averageSpeed: 3.40, averageHR: 145 },
        { distance: 1000, averageSpeed: 3.20, averageHR: 150 }
    ]
};

const mockActivityNoSplits: Activity = {
    activityId: 102,
    date: '2026-01-21',
    name: 'Simple Run',
    type: 'running',
    distance_m: 3000,
    duration_s: 900
};

describe('ActivityModal', () => {
    it('does not render when activity is null', () => {
        renderWithClient(<ActivityModal activity={null} onClose={() => {}} />);
        expect(screen.queryByText('Splits Test Run')).not.toBeInTheDocument();
    });

    it('renders basic details correctly', () => {
        renderWithClient(<ActivityModal activity={mockActivityNoSplits} onClose={() => {}} />);
        expect(screen.getByText('Simple Run')).toBeInTheDocument();
        // Distance 3000m -> 3.00 km. Use regex to be flexible with 'k' suffix
        expect(screen.getByText(/3\.00/)).toBeInTheDocument();
    });

    it('renders splits section when splits are present', () => {
        renderWithClient(<ActivityModal activity={mockActivityWithSplits} onClose={() => {}} />);
        
        expect(screen.getByText('Splits Test Run')).toBeInTheDocument();
        expect(screen.getByText('Splits')).toBeInTheDocument(); // Header
        
        // Check for split numbers
        expect(screen.getByText('1')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        
        // Check for HR values from splits
        expect(screen.getByText('140')).toBeInTheDocument();
        expect(screen.getByText('145')).toBeInTheDocument();
        expect(screen.getByText('150')).toBeInTheDocument();
    });

    it('invokes onClose when close button is clicked', () => {
        const onCloseMock = vi.fn();
        renderWithClient(<ActivityModal activity={mockActivityNoSplits} onClose={onCloseMock} />);
        
        // Find close button - usually an SVG icon button or similar. 
        // Based on typical modal designs, searching by role 'button' might find multiple.
        // Let's assume there is a button for closing. 
        // If ActivityModal code doesn't have accessible label, this might be tricky.
        // Checking the code: <button onClick={onClose} ...>
        
        const buttons = screen.getAllByRole('button');
        // Usually the first one or specifically styled one. 
        // If explicit ARIA label is missing, we might click the overlay or check class.
        // Let's click the first button found, assuming it's the close icon in the header.
        fireEvent.click(buttons[0]);
        
        expect(onCloseMock).toHaveBeenCalled();
    });
});
