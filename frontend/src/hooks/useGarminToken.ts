import { useState, useEffect } from 'react';

export const GARMIN_TOKEN_KEY = 'garmin_token';
const EVENT_KEY = 'garmin-token-change';

export function useGarminToken() {
    const [token, setToken] = useState<string | null>(() => {
        return localStorage.getItem(GARMIN_TOKEN_KEY);
    });

    useEffect(() => {
        const handleStorageChange = () => {
             setToken(localStorage.getItem(GARMIN_TOKEN_KEY));
        };

        // Listen for custom event within the same window
        window.addEventListener(EVENT_KEY, handleStorageChange);
        // Listen for storage events across tabs
        window.addEventListener('storage', handleStorageChange);

        return () => {
            window.removeEventListener(EVENT_KEY, handleStorageChange);
            window.removeEventListener('storage', handleStorageChange);
        };
    }, []);

    const saveToken = (newToken: string) => {
        localStorage.setItem(GARMIN_TOKEN_KEY, newToken);
        setToken(newToken);
        window.dispatchEvent(new Event(EVENT_KEY));
    };

    const removeToken = () => {
        localStorage.removeItem(GARMIN_TOKEN_KEY);
        setToken(null);
        window.dispatchEvent(new Event(EVENT_KEY));
    };

    return { token, hasToken: !!token, saveToken, removeToken };
}
