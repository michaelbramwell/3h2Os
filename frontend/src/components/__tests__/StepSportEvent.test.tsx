import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { StepSportEvent } from '../wizard/StepSportEvent';
import type { WizardSportEvent } from '../../types/wizard';
import type { StepErrors } from '../../hooks/useWizard';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeData(overrides: Partial<WizardSportEvent> = {}): WizardSportEvent {
    return {
        plan_name: 'Test Plan',
        sport: 'running',
        event_type: 'marathon',
        ...overrides,
    };
}

function makeErrors(overrides: Partial<StepErrors> = {}): StepErrors {
    return { ...overrides } as StepErrors;
}

function renderStep(props: {
    data?: WizardSportEvent;
    onChange?: (d: Partial<WizardSportEvent>) => void;
    errors?: StepErrors;
    swimmingEnabled?: boolean;
}) {
    const onChange = props.onChange ?? vi.fn();
    render(
        <StepSportEvent
            data={props.data ?? makeData()}
            onChange={onChange}
            errors={props.errors ?? makeErrors()}
            swimmingEnabled={props.swimmingEnabled}
        />
    );
    return { onChange };
}

// ---------------------------------------------------------------------------
// Swimming visibility
// ---------------------------------------------------------------------------

describe('StepSportEvent — swimming visibility', () => {
    it('only shows Running when swimmingEnabled is false (default)', () => {
        renderStep({});

        expect(screen.getByText('Running')).toBeDefined();
        expect(screen.queryByText('Swimming')).toBeNull();
    });

    it('shows both Running and Swimming when swimmingEnabled is true', () => {
        renderStep({ swimmingEnabled: true });

        expect(screen.getByText('Running')).toBeDefined();
        expect(screen.getByText('Swimming')).toBeDefined();
    });

    it('hides Swimming button when swimmingEnabled becomes false', () => {
        // Start enabled, rerender disabled
        const { rerender } = render(
            <StepSportEvent
                data={makeData()}
                onChange={vi.fn()}
                errors={makeErrors()}
                swimmingEnabled={true}
            />
        );
        expect(screen.getByText('Swimming')).toBeDefined();

        rerender(
            <StepSportEvent
                data={makeData()}
                onChange={vi.fn()}
                errors={makeErrors()}
                swimmingEnabled={false}
            />
        );
        expect(screen.queryByText('Swimming')).toBeNull();
    });

    it('falls back to running when swimming is selected but flag is disabled', () => {
        // If sport=swimming but swimmingEnabled=false, the component renders as running
        const data = makeData({ sport: 'swimming', event_type: 'pool_1500m' });
        renderStep({ data, swimmingEnabled: false });

        // Running button should be active (highlighted); swimming button absent
        expect(screen.queryByText('Swimming')).toBeNull();
        // Running events should be shown (not pool events)
        expect(screen.getByText('Marathon')).toBeDefined();
    });
});

// ---------------------------------------------------------------------------
// Sport selection
// ---------------------------------------------------------------------------

describe('StepSportEvent — sport selection', () => {
    it('calls onChange with new sport when running is selected', () => {
        const onChange = vi.fn();
        render(
            <StepSportEvent
                data={makeData({ sport: 'swimming', event_type: 'pool_1500m' })}
                onChange={onChange}
                errors={makeErrors()}
                swimmingEnabled={true}
            />
        );

        fireEvent.click(screen.getByText('Running'));
        expect(onChange).toHaveBeenCalledWith(
            expect.objectContaining({ sport: 'running' })
        );
    });

    it('calls onChange with swimming when swimming is selected', () => {
        const onChange = vi.fn();
        render(
            <StepSportEvent
                data={makeData({ sport: 'running', event_type: 'marathon' })}
                onChange={onChange}
                errors={makeErrors()}
                swimmingEnabled={true}
            />
        );

        fireEvent.click(screen.getByText('Swimming'));
        expect(onChange).toHaveBeenCalledWith(
            expect.objectContaining({ sport: 'swimming' })
        );
    });
});

// ---------------------------------------------------------------------------
// Plan name field
// ---------------------------------------------------------------------------

describe('StepSportEvent — plan name', () => {
    it('renders the plan name input with current value', () => {
        renderStep({ data: makeData({ plan_name: 'My Marathon' }) });

        const input = screen.getByPlaceholderText('e.g. My First Marathon') as HTMLInputElement;
        expect(input.value).toBe('My Marathon');
    });

    it('shows validation error when plan_name error is set', () => {
        renderStep({ errors: makeErrors({ plan_name: 'Plan name is required' }) });

        expect(screen.getByText('Plan name is required')).toBeDefined();
    });

    it('calls onChange when plan name is typed', () => {
        const onChange = vi.fn();
        render(
            <StepSportEvent
                data={makeData()}
                onChange={onChange}
                errors={makeErrors()}
            />
        );

        const input = screen.getByPlaceholderText('e.g. My First Marathon');
        fireEvent.change(input, { target: { value: 'New Name' } });
        expect(onChange).toHaveBeenCalledWith(
            expect.objectContaining({ plan_name: 'New Name' })
        );
    });
});

// ---------------------------------------------------------------------------
// Event date / name optional fields
// ---------------------------------------------------------------------------

describe('StepSportEvent — optional event fields', () => {
    it('shows event name and date fields when event_type is not none', () => {
        renderStep({ data: makeData({ event_type: 'marathon' }) });

        expect(screen.getByPlaceholderText('e.g. Perth City to Surf 2026')).toBeDefined();
        // The date input is present (type="date", value="")
        const dateInputs = document.querySelectorAll('input[type="date"]');
        expect(dateInputs.length).toBe(1);
    });

    it('hides event name and date fields when event_type is none', () => {
        renderStep({ data: makeData({ event_type: 'none' }) });

        expect(screen.queryByPlaceholderText('e.g. Perth City to Surf 2026')).toBeNull();
    });
});
