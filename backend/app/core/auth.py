from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from jose import jwt, jwk, JWTError
import os
import logging
import httpx
from datetime import datetime, timedelta
import asyncio

# Constants
KEYCLOAK_URL = os.getenv("IDP_URL", "http://localhost:8080")
REALM_NAME = os.getenv("IDP_REALM", "running-realm")
# Remove trailing slash if present to avoid double slashes in constructed URL
if KEYCLOAK_URL.endswith("/"):
    KEYCLOAK_URL = KEYCLOAK_URL[:-1]

JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/certs"
ALGORITHMS = ["RS256"]

logger = logging.getLogger("auth")


class JWKSManager:
    """
    Manages fetching and caching of JSON Web Key Sets (JWKS) from the IdP.
    """

    def __init__(self, jwks_url: str, ttl_minutes: int = 60):
        self.jwks_url = jwks_url
        self.ttl = timedelta(minutes=ttl_minutes)
        self.keys = {}
        self.last_fetch = None
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str):
        """
        Retrieve a public key by its Key ID (kid).
        Refreshes cache if key is missing or cache is expired.
        """
        # First check (optimistic)
        if not self._needs_refresh() and kid in self.keys:
            return self.keys[kid]

        # Acquire lock to prevent thundering herd
        async with self._lock:
            # Double check after acquiring lock
            if not self._needs_refresh() and kid in self.keys:
                return self.keys[kid]

            await self._refresh_keys()

            if kid not in self.keys:
                # If still not found after refresh, force one more refresh IF it wasn't just refreshed
                # (handled by _needs_refresh logic, but explicit check helps if key rotated immediately)
                # For now, just raise error.
                logger.error(f"Key ID {kid} not found in JWKS from {self.jwks_url}")
                raise JWTError(f"Public key not found for kid: {kid}")

            return self.keys[kid]

    async def _refresh_keys(self):
        try:
            logger.info(f"Refreshing JWKS from {self.jwks_url}")
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.jwks_url, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()

                new_keys = {}
                for key_data in data.get("keys", []):
                    kid = key_data.get("kid")
                    if kid:
                        # Construct public key object
                        try:
                            new_keys[kid] = jwk.construct(key_data)
                        except Exception as e:
                            logger.warning(f"Failed to construct key {kid}: {e}")

                self.keys = new_keys
                self.last_fetch = datetime.now()
                logger.info(
                    f"Successfully refreshed JWKS. Loaded {len(self.keys)} keys."
                )

        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # If we have existing keys, we might want to keep using them?
            # For strict security, we might want to fail.
            # But transient network errors shouldn't kill auth if keys are old but potentially valid.
            if not self.keys:
                raise e

    def _needs_refresh(self):
        if not self.last_fetch:
            return True
        return datetime.now() - self.last_fetch > self.ttl


# Initialize singleton
jwks_manager = JWKSManager(JWKS_URL)

security = HTTPBearer(auto_error=False)


def allow_anonymous(func):
    """
    Decorator to mark an endpoint as allowing anonymous access.
    Used for endpoints that Strava (or other external services) hit without a JWT,
    e.g. the webhook verification and event endpoints.
    """
    setattr(func, "is_public", True)
    return func


def _is_public_path(request: Request) -> bool:
    """Path-based public check — belt-and-suspenders alongside @allow_anonymous."""
    path = request.url.path
    # Webhook paths are hit by Strava servers without a JWT
    return path.startswith("/strava/webhook") or path.startswith("/api/strava/webhook")


async def verify_jwt_middleware(request: Request):
    """
    Global dependency to verify JWT.
    If endpoint is public, allow missing token.
    If endpoint is protected (default), require valid token.
    """
    endpoint = request.scope.get("endpoint")
    is_public = _is_public_path(request) or getattr(endpoint, "is_public", False)

    # Extract Token — prefer Authorization header, fall back to ?token= query param
    # (query param fallback is used by EventSource which cannot set headers)
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    if not token:
        token = request.query_params.get("token") or None

    if not token:
        if is_public:
            return None  # Anonymous
        elif (
            os.getenv("DEFAULT_USERNAME")
            and os.getenv("ENVIRONMENT", "production") == "development"
        ):
            # Dev Mode: Allow request to proceed without token.
            # Downstream dependencies (get_current_user) will handle the fallback.
            return None
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Validate Token
    try:
        # Get Unverified Header to find 'kid'
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        kid = unverified_header.get("kid")

        # Development override: If verification is disabled
        verify_signature_env = os.getenv("JWT_VERIFY_SIGNATURE", "true").lower()
        verify_signature = verify_signature_env in ("1", "true", "yes")

        secret = None

        if verify_signature:
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token header missing 'kid' field",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Fetch public key dynamically
            try:
                public_key_obj = await jwks_manager.get_key(kid)
                secret = public_key_obj.to_pem().decode("utf-8")
            except Exception as e:
                logger.error(f"JWKS Error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not retrieve public key for token verification",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            logger.warning("JWT Signature verification disabled.")

        options = {
            "verify_signature": verify_signature,
            "verify_aud": False,
            "exp": True,
        }

        # If verification is disabled, secret is ignored by python-jose usually,
        # but we pass empty string or similar to satisfy signature
        if not verify_signature:
            # When skipping signature, we just decode
            payload = jwt.decode(token, "", algorithms=ALGORITHMS, options=options)
        else:
            payload = jwt.decode(token, secret, algorithms=ALGORITHMS, options=options)

        # Store user info in request state
        request.state.user = payload
        return payload

    except JWTError as e:
        logger.warning(f"JWT Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(role: str):
    """
    Returns a FastAPI dependency that enforces the caller has the given Keycloak
    realm role (checked in realm_access.roles of the JWT payload).

    The required role name can be overridden per-call via an env var if needed,
    but the default admin role is controlled by ADMIN_ROLE (default: 'app_admin').

    Usage:
        @router.put("/admin/something")
        async def my_endpoint(
            _: None = Depends(require_role("app_admin")),
            ...
        ):
    """

    async def _check(request: Request):
        payload = getattr(request.state, "user", None)

        # Dev mode: if no JWT is present and DEFAULT_USERNAME is set, allow through.
        if payload is None:
            if (
                os.getenv("DEFAULT_USERNAME")
                and os.getenv("ENVIRONMENT", "production") == "development"
            ):
                return  # Skip role check in local dev without auth
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        realm_roles: list = payload.get("realm_access", {}).get("roles", [])
        if role not in realm_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {role}",
            )

    return _check
