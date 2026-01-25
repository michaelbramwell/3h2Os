import { render, screen, fireEvent } from '@testing-library/react';
import { RecentActivities } from '../RecentActivities';
import { describe, it, expect } from 'vitest';
import type { Activity } from '../../types/schema';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: false,
        },
    },
});

const renderWithClient = (ui: React.ReactElement) => {
    return render(
        <QueryClientProvider client={queryClient}>
            {ui}
        </QueryClientProvider>
    );
};

// Mock data
const mockActivities: Activity[] = [
    {
        activityId: 101,
        date: '2026-01-14',
        name: 'Morning Run',
        type: 'running',
        distance_m: 5000,
        duration_s: 1500, // 25 min -> 5:00/km
        average_hr: 145,
        training_load: 50
    },
    {
        activityId: 102,
        date: '2026-01-13',
        name: 'Intervals',
        type: 'running',
        distance_m: 8000,
        duration_s: 2400,
        average_hr: 160,
        training_load: 120
    }
];

describe('RecentActivities', () => {
    it('renders list of activities sorted by date', () => {
        renderWithClient(<RecentActivities activities={mockActivities} />);
        
        // Expect Morning Run (Jan 14) to be first
        const rows = screen.getAllByRole('row');
        // Row 0 is header. Row 1 is first data row.
        expect(rows[1]).toHaveTextContent('Morning Run');
        expect(rows[2]).toHaveTextContent('Intervals');
    });

    it('opens modal when a row is clicked', () => {
        renderWithClient(<RecentActivities activities={mockActivities} />);
        
        const runRow = screen.getByText('Morning Run').closest('tr');
        if (!runRow) throw new Error('Row not found');

        fireEvent.click(runRow);

        // Modal should appear. It renders "Morning Run" in h2.
        // Since ActivityModal logic is inside RecentActivities, simpler to check if text is visible in dialog info
        // ActivityModal puts content in a portal, but screen.getByText finds it in document.body
        const modalTitle = screen.getByRole('heading', { level: 2 });
        expect(modalTitle).toHaveTextContent('Morning Run');
    });
    
    it('renders empty state correctly', () => {
        renderWithClient(<RecentActivities activities={[]} />);
        expect(screen.getByText('No recent activities found. Click scan to sync from Garmin.')).toBeInTheDocument();
    });
});
