
/**
 * Formats a pace value into a string "MM:SS".
 * Handles both seconds/km and meters/second input.
 * 
 * @param value - The pace value.
 * @param unit - 'ms' (meters/second) or 'skm' (seconds/km). Defaults to auto-detect if < 10 assumes m/s.
 * @returns Formatted string "MM:SS" or "--:--" if invalid.
 */
export function formatPace(value: number | undefined | null): string {
    if (!value || isNaN(value) || value === Infinity || value === 0) return '--:--';
    
    // Heuristic: If value is small (< 10), it's likely m/s (World Record pace is > 2.6 m/s).
    // If value is large (> 120), it's likely seconds/km (2:00/km).
    // Between 10 and 120 is ambiguous (10s/km is impossible, 10m/s is Usain Bolt).
    // Standardizing on: Input < 30 is treated as m/s. Input >= 30 is seconds/km.
    
    let secondsPerKm: number;
    if (value < 30) {
        secondsPerKm = 1000 / value;
    } else {
        secondsPerKm = value;
    }

    let mins = Math.floor(secondsPerKm / 60);
    let secs = Math.round(secondsPerKm % 60);
    
    if (secs === 60) {
        mins++;
        secs = 0;
    }
    
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Formats a swim pace (sec/100m) into "MM:SS/100m".
 * @param speedMs - Speed in meters/second
 */
export function formatSwimPace(speedMs: number | undefined | null): string {
    if (!speedMs || isNaN(speedMs) || speedMs === Infinity || speedMs === 0) return '--:--';
    
    // speed (m/s) -> pace (sec/100m)
    // 1 m/s = 100 seconds per 100m = 1:40/100m
    const secPer100m = 100 / speedMs;
    
    // Re-calc to be safe or just standard logic
    const totalSeconds = Math.round(secPer100m);
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    
    return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Formats distance in meters to kilometers with specified decimal places.
 * @param meters - Distance in meters.
 * @param decimals - Number of decimal places (default 1).
 * @returns Formatted string "X.X" (does not include "km" suffix).
 */
export function formatDistance(meters: number | undefined, decimals: number = 1): string {
    if (!meters && meters !== 0) return (0).toFixed(decimals);
    return (meters / 1000).toFixed(decimals);
}

/**
 * Formats a raw zone range (low m/s, high m/s) into a pace range string "MM:SS - MM:SS".
 * @param lowMs - Low boundary in m/s (slower pace for some definitions, but usually low m/s = slower speed).
 * @param highMs - High boundary in m/s (faster speed).
 * @returns String "MM:SS - MM:SS"
 */
export function formatZoneRange(lowMs?: number, highMs?: number): string {
    if (!lowMs || !highMs) return '--';
    // Note: m/s to pace is inverse. Lower m/s = Slower Pace (Higher MM:SS).
    // We typically want "Slower - Faster" or "Faster - Slower"?
    // Standard convention: "5:30 - 5:00" (Slower to Faster).
    // lowMs (e.g. 2.5) -> 6:40. highMs (e.g. 3.0) -> 5:33.
    // So formatPace(lowMs) will be the slower time.
    return `${formatPace(lowMs)} - ${formatPace(highMs)}`;
}
