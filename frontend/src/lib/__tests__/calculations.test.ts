import { describe, it, expect } from 'vitest';
import {
    calculateWeekVolume,
    calculateDayVolume,
    calculateRemainingWeekVolume,
    calculateWeekActuals,
    getZoneLabel,
} from '../../lib/calculations';
import type { Week, Day, Activity, TrainingZone } from '../../types/schema';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeDay(distances: number[], date = '2026-01-01'): Day {
    return {
        date,
        workouts: distances.map(d => ({
            name: 'Workout',
            type: 'Run',
            distance_m: d,
            timeOfDay: 'AM',
        })),
    };
}

function makeWeek(days: Record<string, Day>, weekStarting = '2026-01-01'): Week {
    return { weekStarting, status: 'normal', days };
}

function makeActivity(overrides: Partial<Activity> = {}): Activity {
    return {
        date: '2026-01-01',
        name: 'Run',
        type: 'running',
        distance_m: 5000,
        duration_s: 1500,
        activityId: 1,
        ...overrides,
    };
}

function makeZone(zone: number, low: number): TrainingZone {
    return { zone, lowBoundary_m_s: low };
}

// ---------------------------------------------------------------------------
// calculateDayVolume
// ---------------------------------------------------------------------------

describe('calculateDayVolume', () => {
    it('sums all workout distances in the day', () => {
        expect(calculateDayVolume(makeDay([3000, 2000]))).toBe(5000);
    });

    it('returns 0 for a day with no workouts', () => {
        expect(calculateDayVolume({ date: '2026-01-01', workouts: [] })).toBe(0);
    });

    it('treats undefined distance_m as 0', () => {
        const day: Day = {
            date: '2026-01-01',
            workouts: [{ name: 'Rest', type: 'Rest', distance_m: undefined as any, timeOfDay: 'AM' }],
        };
        expect(calculateDayVolume(day)).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// calculateWeekVolume
// ---------------------------------------------------------------------------

describe('calculateWeekVolume', () => {
    it('sums all days in the week', () => {
        const week = makeWeek({
            Mon: makeDay([5000], '2026-01-01'),
            Wed: makeDay([8000], '2026-01-03'),
            Sat: makeDay([15000], '2026-01-06'),
        });
        expect(calculateWeekVolume(week)).toBe(28000);
    });

    it('returns 0 for an empty week', () => {
        expect(calculateWeekVolume(makeWeek({}))).toBe(0);
    });

    it('returns 0 when week is falsy', () => {
        expect(calculateWeekVolume(null as any)).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// calculateRemainingWeekVolume
// ---------------------------------------------------------------------------

describe('calculateRemainingWeekVolume', () => {
    const week = makeWeek({
        Mon: makeDay([5000], '2026-01-05'),
        Wed: makeDay([8000], '2026-01-07'),
        Fri: makeDay([6000], '2026-01-09'),
    });

    it('includes only days strictly after todayStr', () => {
        // Today is Wednesday; Fri remains
        expect(calculateRemainingWeekVolume(week, '2026-01-07')).toBe(6000);
    });

    it('returns full week volume when todayStr is before all days', () => {
        expect(calculateRemainingWeekVolume(week, '2026-01-04')).toBe(19000);
    });

    it('returns 0 when all days are on or before today', () => {
        expect(calculateRemainingWeekVolume(week, '2026-01-09')).toBe(0);
    });

    it('returns 0 for an empty week', () => {
        expect(calculateRemainingWeekVolume(makeWeek({}), '2026-01-07')).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// calculateWeekActuals
// ---------------------------------------------------------------------------

describe('calculateWeekActuals', () => {
    const week = makeWeek({
        Mon: makeDay([5000], '2026-01-05'),
        Wed: makeDay([8000], '2026-01-07'),
    });

    it('sums running actuals matching week dates', () => {
        const actuals = [
            makeActivity({ date: '2026-01-05', type: 'running', distance_m: 4800 }),
            makeActivity({ date: '2026-01-07', type: 'running', distance_m: 7900 }),
        ];
        expect(calculateWeekActuals(actuals, week)).toBe(12700);
    });

    it('excludes actuals outside the week dates', () => {
        const actuals = [
            makeActivity({ date: '2026-01-05', distance_m: 5000 }),
            makeActivity({ date: '2026-01-10', distance_m: 9999 }), // outside week
        ];
        expect(calculateWeekActuals(actuals, week)).toBe(5000);
    });

    it('counts trail_running and run types for a running plan', () => {
        const actuals = [
            makeActivity({ date: '2026-01-05', type: 'trail_running', distance_m: 3000 }),
            makeActivity({ date: '2026-01-07', type: 'run', distance_m: 4000 }),
        ];
        expect(calculateWeekActuals(actuals, week)).toBe(7000);
    });

    it('excludes swimming actuals from a running plan', () => {
        const actuals = [
            makeActivity({ date: '2026-01-05', type: 'swimming', distance_m: 3000 }),
        ];
        expect(calculateWeekActuals(actuals, week)).toBe(0);
    });

    it('counts swimming actuals for a swim planType', () => {
        const actuals = [
            makeActivity({ date: '2026-01-05', type: 'swimming', distance_m: 1500 }),
            makeActivity({ date: '2026-01-07', type: 'lap_swimming', distance_m: 2000 }),
        ];
        expect(calculateWeekActuals(actuals, week, 'swimming')).toBe(3500);
    });

    it('excludes running actuals from a swim planType', () => {
        const actuals = [
            makeActivity({ date: '2026-01-05', type: 'running', distance_m: 5000 }),
        ];
        expect(calculateWeekActuals(actuals, week, 'swim')).toBe(0);
    });

    it('returns 0 when actuals list is empty', () => {
        expect(calculateWeekActuals([], week)).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// getZoneLabel
// ---------------------------------------------------------------------------

describe('getZoneLabel', () => {
    const zones: TrainingZone[] = [
        makeZone(2, 2.5),  // ~6:40/km
        makeZone(3, 3.0),  // ~5:33/km
        makeZone(4, 3.3),  // ~5:03/km
        makeZone(5, 3.6),  // ~4:37/km
        makeZone(6, 4.0),  // ~4:10/km
    ];

    it('returns fallback string when zones array is empty', () => {
        expect(getZoneLabel('Easy', [])).toBe('Easy: --');
        expect(getZoneLabel('Tempo', [])).toBe('Tempo: --');
    });

    it('returns fallback string when zones is null/undefined', () => {
        expect(getZoneLabel('Easy', null as any)).toBe('Easy: --');
    });

    it('formats Easy label using Z2 and Z3 boundaries', () => {
        const label = getZoneLabel('Easy', zones);
        expect(label).toMatch(/^Easy \(Z2\):/);
    });

    it('formats Tempo label using Z3 and Z4 boundaries', () => {
        const label = getZoneLabel('Tempo', zones);
        expect(label).toMatch(/^Tempo \(Z3\):/);
    });

    it('formats Threshold label using Z4 and Z5 boundaries', () => {
        const label = getZoneLabel('Threshold', zones);
        expect(label).toMatch(/^Threshold \(Z4\):/);
    });

    it('formats VO2 Max label with upper bound when Z6 exists', () => {
        const label = getZoneLabel('VO2 Max', zones);
        expect(label).toMatch(/^VO2 Max \(Z5\):/);
        expect(label).toContain('-');
    });

    it('formats VO2 Max label with "< " when Z6 is absent', () => {
        const zonesNoZ6 = zones.filter(z => z.zone !== 6);
        const label = getZoneLabel('VO2 Max', zonesNoZ6);
        expect(label).toMatch(/^VO2 Max \(Z5\): < /);
    });

    it('returns fallback string for Easy when Z2 or Z3 missing', () => {
        const label = getZoneLabel('Easy', [makeZone(2, 2.5)]);
        expect(label).toBe('Easy: 5:45-6:15');
    });
});
