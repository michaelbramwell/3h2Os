import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Global Auth Mock
const mockAuth = {
    isAuthenticated: true,
    user: {
        profile: {
            preferred_username: "testuser",
            sub: "test-id"
        },
        access_token: "mock-token"
    },
    isLoading: false,
    signinRedirect: vi.fn(),
    removeUser: vi.fn(),
    error: null
};

vi.mock('react-oidc-context', () => ({
    useAuth: () => mockAuth,
    AuthProvider: ({ children }: { children: any }) => children
}));
