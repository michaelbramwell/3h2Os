import type { Week, Activity, Day, TrainingZone } from '../types/schema';
import { formatPace } from './formatters';

/**
 * Calculates the total planned distance for a week, excluding non-running activities if needed.
 * Currently sums all workouts.
 */
export function calculateWeekVolume(week: Week, _planType?: string): number {
    if (!week || !week.days) return 0;
    
    // Use the explicit planType if available
    // const normalizedPlanType = planType?.toLowerCase();
    
    // We assume default is running unless 'swimming' or 'swim' is detected in planType
    // const isSwimWeek =
    //     normalizedPlanType === 'swim' ||
    //     normalizedPlanType === 'swimming' ||
    //     (normalizedPlanType !== undefined && normalizedPlanType.includes('swim'));

    return Object.values(week.days).reduce((acc, day) => {
        return acc + calculateDayVolume(day);
    }, 0);
}

/**
 * Calculates volume for a single day, adhering to the same filters as the week volume.
 */
export function calculateDayVolume(day: Day): number {
    if (!day.workouts) return 0;
    
    return day.workouts.reduce((wAcc, w) => {
        // We accept all types now since the backend separates plans by type.
        // If a Swim plan has a "Run" workout, maybe we still count it in meters?
        // Or should we filter? For now, count all meters.
        return wAcc + (w.distance_m || 0);
    }, 0);
}

/**
 * Calculates the remaining planned distance for the week from "tomorrow" onwards.
 * (i.e. days strictly after todayStr)
 */
export function calculateRemainingWeekVolume(week: Week, todayStr: string): number {
    if (!week || !week.days) return 0;

    return Object.values(week.days).reduce((acc, day) => {
        if (day.date > todayStr) {
            return acc + calculateDayVolume(day);
        }
        return acc;
    }, 0);
}

/**
 * Calculates the actual distance run/swum in a given week.
 * Filters based on the dominant activity type of the plan.
 */
export function calculateWeekActuals(actuals: Activity[], week: Week, planType?: string): number {
    if (!actuals || !week) return 0;
    
    const weekDatesSet = new Set(Object.values(week.days).map((d: Day) => d.date));

    // Determine plan type from explicit `planType` parameter instead of inferring from workouts.
    const normalizedPlanType = planType?.toLowerCase();
    const isSwimWeek =
        normalizedPlanType === 'swim' ||
        normalizedPlanType === 'swimming' ||
        (normalizedPlanType !== undefined && normalizedPlanType.includes('swim'));

    return actuals.reduce((acc, act) => {
        if (weekDatesSet.has(act.date)) {
             const type = act.type?.toLowerCase();
             if (isSwimWeek) {
                 if (type === 'swimming' || type === 'pool' || type === 'lap_swimming') return acc + (act.distance_m || 0);
             } else {
                 // Default to Running logic
                 if (type === 'running' || type === 'trail_running' || type === 'run') {
                     return acc + (act.distance_m || 0);
                 }
             }
        }
        return acc;
    }, 0);
}

/**
 * Generates the formatted label for a training zone (e.g., "Easy (Z2): 5:45-6:15").
 * Uses logic shared between FridgeWeek and Sidebar.
 */
export function getZoneLabel(
    zoneType: 'Easy' | 'Tempo' | 'Threshold' | 'VO2 Max',
    zones: TrainingZone[]
): string {
    if (!zones || zones.length === 0) return `${zoneType}: --`;

    const zp = zones;
    const z2 = zp.find(z => z.zone === 2);
    const z3 = zp.find(z => z.zone === 3);
    const z4 = zp.find(z => z.zone === 4);
    const z5 = zp.find(z => z.zone === 5);
    const z6 = zp.find(z => z.zone === 6);

    // Helper
    const range = (low?: number, high?: number) => {
        if (!low || !high) return '--';
        return `${formatPace(low)}-${formatPace(high)}`;
    };

    switch (zoneType) {
        case 'Easy':
            // Z2 Low -> Z3 Low
            if (z2 && z3) return `Easy (Z2): ${range(z2.lowBoundary_m_s, z3.lowBoundary_m_s)}`;
            return "Easy: 5:45-6:15"; // Default fallback
        case 'Tempo':
            // Z3 Low -> Z4 Low
            if (z3 && z4) return `Tempo (Z3): ${range(z3.lowBoundary_m_s, z4.lowBoundary_m_s)}`;
             return "Tempo: 4:50-5:20";
        case 'Threshold':
            // Z4 Low -> Z5 Low
            if (z4 && z5) return `Threshold (Z4): ${range(z4.lowBoundary_m_s, z5.lowBoundary_m_s)}`;
            return "Threshold: 4:40-4:50";
        case 'VO2 Max':
            if (z5) {
                const lower = formatPace(z5.lowBoundary_m_s);
                const upper = z6 ? formatPace(z6.lowBoundary_m_s) : null;
                return upper ? `VO2 Max (Z5): ${lower}-${upper}` : `VO2 Max (Z5): < ${lower}`;
            }
            return "VO2 Max: < 4:40";
        default:
            return `${zoneType}: --`;
    }
}
