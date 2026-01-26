import { UserManager, WebStorageStateStore } from 'oidc-client-ts';

export const userManager = new UserManager({
  authority:
    import.meta.env.VITE_AUTH_AUTHORITY ||
    (window.location.hostname === '3h2os.com'
      ? 'https://auth.3h2os.com/realms/running-realm'
      : 'http://localhost:8080/realms/running-realm'),
  client_id: import.meta.env.VITE_AUTH_CLIENT_ID || 'running-app',
  redirect_uri: window.location.origin,
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  monitorSession: true,
});
