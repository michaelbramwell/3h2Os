export interface IntegrationSources {
    hasStrava: boolean;
    hasGarmin: boolean;
    /** True when this wizard was opened in create mode and defaults were fetched. */
    hasDefaults: boolean;
}

/**
 * Shown at the top of wizard steps that can be pre-filled from connected
 * integrations. Only renders when at least one integration is connected.
 */
export function IntegrationBanner({ sources }: { sources: IntegrationSources }) {
    // hasGarmin is already gated by the feature flag in PlanWizard
    const { hasStrava, hasGarmin, hasDefaults } = sources;
    const anyConnected = hasStrava || hasGarmin;

    if (!anyConnected) return null;

    let message: string;
    if (hasStrava && hasGarmin) {
        message = hasDefaults
            ? 'Fields pre-filled from your Strava profile. Garmin is also connected; Strava takes precedence.'
            : 'Strava and Garmin are connected. Sync activities from the header to update these fields.';
    } else if (hasStrava) {
        message = hasDefaults
            ? 'Fields pre-filled from your Strava profile.'
            : 'Strava is connected. Sync activities from the header to update these fields.';
    } else {
        message = hasDefaults
            ? 'Fields pre-filled from your Garmin profile.'
            : 'Garmin is connected. Sync activities from the header to update these fields.';
    }

    return (
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2.5 text-xs text-blue-700">
            {message}
        </div>
    );
}
