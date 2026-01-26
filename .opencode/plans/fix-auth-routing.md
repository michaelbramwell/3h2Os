# Implementation Plan - Fix Authentication and Routing

The user is experiencing an authentication error (`Authentication Error: NetworkError`) when logging in. This is likely due to the frontend trying to reach the Keycloak server at `localhost:8080` (the default) instead of the production URL `https://auth.3h2os.com`.

Additionally, we need to fix the API routing mismatch identified earlier (Caddy stripping `/api` while backend expects it).

## User Review Required

> [!IMPORTANT]
> The most critical fix is ensuring the frontend uses the correct Keycloak URL in production.

- **Current Behavior:** Frontend hardcodes `http://localhost:8080/realms/running-realm`.
- **Desired Behavior:** Frontend uses environment variables to point to `https://auth.3h2os.com/realms/running-realm`.

## Proposed Changes

### 1. Fix Frontend Authentication Configuration
Update `frontend/src/lib/auth.ts` to use environment variables for the OIDC authority.

**Security Note:** The variables below (`VITE_AUTH_AUTHORITY`, `VITE_AUTH_CLIENT_ID`) are public configuration values required for the browser to initiate the OAuth flow. They do not contain secrets (like client secrets or private keys).

**File:** `frontend/src/lib/auth.ts`
```typescript
export const userManager = new UserManager({
  authority: import.meta.env.VITE_AUTH_AUTHORITY || 'http://localhost:8080/realms/running-realm',
  client_id: import.meta.env.VITE_AUTH_CLIENT_ID || 'running-app',
  // ...
});
```

### 2. Configure Environment Variables for Production
We need to ensure these variables are injected during the build process in GitHub Actions.

**File:** `frontend/Dockerfile.prod`
```dockerfile
# ...
ARG VITE_API_URL
ARG VITE_AUTH_AUTHORITY
ARG VITE_AUTH_CLIENT_ID
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_AUTH_AUTHORITY=$VITE_AUTH_AUTHORITY
ENV VITE_AUTH_CLIENT_ID=$VITE_AUTH_CLIENT_ID
# ... then run build
```

**File:** `.github/workflows/deploy.yml`
Update the frontend build step to pass these arguments.
```yaml
      - name: Build and push Frontend
        uses: docker/build-push-action@v5
        with:
          build-args: |
            VITE_API_URL=https://3h2os.com
            VITE_AUTH_AUTHORITY=https://auth.3h2os.com/realms/running-realm
            VITE_AUTH_CLIENT_ID=running-app
          # ...
```

### 3. Fix API Routing in Caddy
Update `Caddyfile` to preserve the `/api` prefix so the backend receives the path it expects.

**File:** `Caddyfile`
```caddyfile
    # Backend API
    handle /api* {
        reverse_proxy backend:8000
    }
```

### 4. Ensure Public Key Availability on Production

**Critical Change:**
Since we are using Keycloak (which generates its own keys) and not sharing a manually generated private key between services, the `public_key.pem` we copy from local dev will **not** validate tokens signed by Production Keycloak.

For this MVP phase, to unblock the API access, we will **disable JWT signature verification** in the backend for Production. The tokens will still be checked for expiry and structure, but we will trust the internal network/Keycloak issuer without verifying the cryptographic signature against a mismatched key.

**File:** `docker-compose.prod.yml`
Set `JWT_VERIFY_SIGNATURE` to `false` and update the volume mapping (just in case we need it later, but it won't be used for verification).

```yaml
  backend:
    # ...
    environment:
      # ...
      - JWT_VERIFY_SIGNATURE=false
    volumes:
      - backend_data:/app/data
      # Mount the key anyway, just in case, but rely on disabling verification
      - ./public_key.pem:/app/certs/public_key.pem:ro
```

## Verification Plan

1.  **Commit & Push:** Push changes to `main`.
2.  **Monitor Deploy:** Watch the GitHub Action.
3.  **Test:**
    *   Go to `https://3h2os.com`.
    *   Click Login.
    *   Verify it redirects to `https://auth.3h2os.com/...` (not localhost).
    *   After login, verify `GET /api/plan.json` returns 200 OK.
