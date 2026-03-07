import { describe, it, expect } from 'vitest';
import { formatPace, formatSwimPace, formatDistance, formatZoneRange } from '../../lib/formatters';

// ---------------------------------------------------------------------------
// formatPace
// ---------------------------------------------------------------------------

describe('formatPace', () => {
    it('returns --:-- for undefined', () => {
        expect(formatPace(undefined)).toBe('--:--');
    });

    it('returns --:-- for null', () => {
        expect(formatPace(null)).toBe('--:--');
    });

    it('returns --:-- for 0', () => {
        expect(formatPace(0)).toBe('--:--');
    });

    it('returns --:-- for NaN', () => {
        expect(formatPace(NaN)).toBe('--:--');
    });

    it('returns --:-- for Infinity', () => {
        expect(formatPace(Infinity)).toBe('--:--');
    });

    it('converts m/s to pace: 3.0 m/s = 5:33', () => {
        // 1000 / 3.0 = 333.33s/km = 5m 33s
        expect(formatPace(3.0)).toBe('5:33');
    });

    it('converts m/s to pace: 2.5 m/s = 6:40', () => {
        // 1000 / 2.5 = 400s/km = 6m 40s
        expect(formatPace(2.5)).toBe('6:40');
    });

    it('treats values < 30 as m/s (4.0 m/s = 4:10)', () => {
        // 1000 / 4.0 = 250s = 4m 10s
        expect(formatPace(4.0)).toBe('4:10');
    });

    it('treats values >= 30 as sec/km (300 s/km = 5:00)', () => {
        expect(formatPace(300)).toBe('5:00');
    });

    it('handles sec/km with rounding (359 s/km = 5:59)', () => {
        expect(formatPace(359)).toBe('5:59');
    });

    it('handles minute rollover: 60 seconds rounds to next minute (360 s/km = 6:00)', () => {
        expect(formatPace(360)).toBe('6:00');
    });

    it('pads single-digit seconds with leading zero', () => {
        // 303 s/km = 5m 3s → "5:03"
        expect(formatPace(303)).toBe('5:03');
    });
});

// ---------------------------------------------------------------------------
// formatSwimPace
// ---------------------------------------------------------------------------

describe('formatSwimPace', () => {
    it('returns --:-- for undefined', () => {
        expect(formatSwimPace(undefined)).toBe('--:--');
    });

    it('returns --:-- for null', () => {
        expect(formatSwimPace(null)).toBe('--:--');
    });

    it('returns --:-- for 0', () => {
        expect(formatSwimPace(0)).toBe('--:--');
    });

    it('converts 1.0 m/s to 1:40/100m', () => {
        // 100 / 1.0 = 100s = 1m 40s
        expect(formatSwimPace(1.0)).toBe('1:40');
    });

    it('converts 1.5 m/s to 1:07/100m', () => {
        // 100 / 1.5 = 66.67s ≈ 67s = 1m 7s
        expect(formatSwimPace(1.5)).toBe('1:07');
    });

    it('converts 0.5 m/s to 3:20/100m', () => {
        // 100 / 0.5 = 200s = 3m 20s
        expect(formatSwimPace(0.5)).toBe('3:20');
    });

    it('pads single-digit seconds', () => {
        // 100 / (100/63) = 63s = 1m 3s → "1:03"
        const speedForExactly63s = 100 / 63;
        expect(formatSwimPace(speedForExactly63s)).toBe('1:03');
    });
});

// ---------------------------------------------------------------------------
// formatDistance
// ---------------------------------------------------------------------------

describe('formatDistance', () => {
    it('formats 5000m as "5.0"', () => {
        expect(formatDistance(5000)).toBe('5.0');
    });

    it('formats 10000m as "10.0"', () => {
        expect(formatDistance(10000)).toBe('10.0');
    });

    it('formats 21097m as "21.1" (1 decimal)', () => {
        expect(formatDistance(21097)).toBe('21.1');
    });

    it('respects custom decimal places', () => {
        expect(formatDistance(5000, 2)).toBe('5.00');
        expect(formatDistance(5000, 0)).toBe('5');
    });

    it('returns "0.0" for undefined', () => {
        expect(formatDistance(undefined)).toBe('0.0');
    });

    it('returns "0.0" for 0', () => {
        expect(formatDistance(0)).toBe('0.0');
    });
});

// ---------------------------------------------------------------------------
// formatZoneRange
// ---------------------------------------------------------------------------

describe('formatZoneRange', () => {
    it('returns "--" when lowMs is undefined', () => {
        expect(formatZoneRange(undefined, 3.0)).toBe('--');
    });

    it('returns "--" when highMs is undefined', () => {
        expect(formatZoneRange(2.5, undefined)).toBe('--');
    });

    it('returns "--" when both are undefined', () => {
        expect(formatZoneRange()).toBe('--');
    });

    it('formats a valid range as "pace1 - pace2"', () => {
        // 2.5 m/s = 6:40, 3.0 m/s = 5:33
        const result = formatZoneRange(2.5, 3.0);
        expect(result).toBe('6:40 - 5:33');
    });

    it('includes " - " separator between the two paces', () => {
        const result = formatZoneRange(3.0, 4.0);
        expect(result).toContain(' - ');
    });
});
