import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useFeatureFlags } from '../../hooks/useFeatureFlags';
import type { FeatureFlags } from '../../types/schema';

// ---------------------------------------------------------------------------
// Mock api.ts so tests do not make real HTTP calls
// ---------------------------------------------------------------------------

vi.mock('../../lib/api', () => ({
    getFeatureFlags: vi.fn(),
}));

import { getFeatureFlags } from '../../lib/api';

const mockGetFeatureFlags = getFeatureFlags as ReturnType<typeof vi.fn>;

// ---------------------------------------------------------------------------
// Helper — wraps the hook in a fresh QueryClient for each test
// ---------------------------------------------------------------------------

function makeWrapper() {
    const qc = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useFeatureFlags', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('returns default flags (all false) before data resolves', () => {
        // Never resolves — simulates loading state
        mockGetFeatureFlags.mockReturnValue(new Promise(() => {}));

        const { result } = renderHook(() => useFeatureFlags(), {
            wrapper: makeWrapper(),
        });

        expect(result.current.isSwimmingEnabled).toBe(false);
    });

    it('returns resolved flags from the API', async () => {
        const serverFlags: FeatureFlags = { isSwimmingEnabled: true };
        mockGetFeatureFlags.mockResolvedValue(serverFlags);

        const { result } = renderHook(() => useFeatureFlags(), {
            wrapper: makeWrapper(),
        });

        await waitFor(() => {
            expect(result.current.isSwimmingEnabled).toBe(true);
        });
    });

    it('falls back to defaults when the API returns false values', async () => {
        const serverFlags: FeatureFlags = { isSwimmingEnabled: false };
        mockGetFeatureFlags.mockResolvedValue(serverFlags);

        const { result } = renderHook(() => useFeatureFlags(), {
            wrapper: makeWrapper(),
        });

        await waitFor(() => {
            // isSwimmingEnabled resolved to false from server (same as default)
            expect(result.current.isSwimmingEnabled).toBe(false);
        });
    });

    it('falls back to defaults when the API call throws', async () => {
        mockGetFeatureFlags.mockRejectedValue(new Error('network error'));

        const { result } = renderHook(() => useFeatureFlags(), {
            wrapper: makeWrapper(),
        });

        // After the error the hook returns DEFAULT_FLAGS
        await waitFor(() => {
            expect(result.current.isSwimmingEnabled).toBe(false);
        });
    });

    it('returns default flags when user is not authenticated', async () => {
        // The global mock in setupTests.ts registers useAuth as a plain object,
        // not a vi.fn(), so vi.mocked() won't work.  Use spyOn instead.
        const oidc = await import('react-oidc-context');
        const spy = vi.spyOn(oidc, 'useAuth').mockReturnValueOnce({
            isAuthenticated: false,
        } as any);

        mockGetFeatureFlags.mockResolvedValue({ isSwimmingEnabled: true });

        const { result } = renderHook(() => useFeatureFlags(), {
            wrapper: makeWrapper(),
        });

        // Query is disabled when not authenticated; default flags returned
        expect(result.current.isSwimmingEnabled).toBe(false);
        expect(mockGetFeatureFlags).not.toHaveBeenCalled();

        spy.mockRestore();
    });

    it('merges unknown flag keys returned by the server', async () => {
        const serverFlags: FeatureFlags = {
            isSwimmingEnabled: true,
            someFutureFlag: true,
        };
        mockGetFeatureFlags.mockResolvedValue(serverFlags);

        const { result } = renderHook(() => useFeatureFlags(), {
            wrapper: makeWrapper(),
        });

        await waitFor(() => {
            expect(result.current.someFutureFlag).toBe(true);
        });
    });
});
