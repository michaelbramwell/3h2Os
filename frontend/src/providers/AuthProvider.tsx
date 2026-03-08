import { AuthProvider as OidcAuthProvider } from 'react-oidc-context';
import { userManager } from '../lib/auth';
import type { ReactNode } from 'react';

const onSigninCallback = () => {
    window.history.replaceState({}, document.title, window.location.pathname);
};

// Paths where ?code=&state= belong to a third-party OAuth flow, not OIDC.
const OIDC_SKIP_PATHS = ['/strava/callback'];

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <OidcAuthProvider
      userManager={userManager}
      skipSigninCallback={OIDC_SKIP_PATHS.includes(window.location.pathname)}
      onSigninCallback={onSigninCallback}
    >
      {children}
    </OidcAuthProvider>
  );
}
