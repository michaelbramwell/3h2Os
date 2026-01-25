import { AuthProvider as OidcAuthProvider } from 'react-oidc-context';
import { userManager } from '../lib/auth';
import type { ReactNode } from 'react';

// Sync token on user load (initial load from storage or after signin)
// Note: We don't strictly need to sync it to api.ts anymore if api.ts reads from userManager directly,
// but it doesn't hurt to keep 'addUserLoaded' listeners if we want other side effects later.

const onSigninCallback = () => {
    window.history.replaceState({}, document.title, window.location.pathname);
};

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <OidcAuthProvider userManager={userManager} onSigninCallback={onSigninCallback}>
      {children}
    </OidcAuthProvider>
  );
}
