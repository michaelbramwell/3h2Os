from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
import logging
from functools import wraps

# Constants
# In production, these should be environment variables
KEYCLOAK_URL = os.getenv("IDP_URL", "http://localhost:8080")
REALM_NAME = os.getenv("IDP_REALM", "running-realm")
ALGORITHMS = ["RS256"]

logger = logging.getLogger("auth")

class AuthManager:
    """
    Handles JWT validation and anonymous access control.
    """
    def __init__(self):
        self.jwks_client = None
        self.public_key = None
        
    def get_public_key(self):
        """
        In a real scenario, this should fetch JWKS from Keycloak:
        GET {KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/certs
        For simplicity in this MVP, we might rely on the library to fetch or cache it.
        Or, we assume standard OIDC discovery.
        """
        # For now, we'll let python-jose handle JWKS fetching if provided, 
        # or just fail if not configured. 
        # Ideally, we use a library like 'PyJWKClient' or fetch manually.
        pass

security = HTTPBearer(auto_error=False)

def allow_anonymous(func):
    """
    Decorator to mark an endpoint as allowing anonymous access.
    """
    setattr(func, "is_public", True)
    return func

async def verify_jwt_middleware(request: Request):
    """
    Global dependency to verify JWT.
    If endpoint is public, allow missing token.
    If endpoint is protected (default), require valid token.
    """
    # Check if the endpoint handler is marked as public
    # This logic depends on how the dependency is attached.
    # If attached to APIRouter, 'request.scope["endpoint"]' gives us the function.
    
    endpoint = request.scope.get("endpoint")
    is_public = getattr(endpoint, "is_public", False)

    # Extract Token
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    if not token:
        if is_public:
            return None # Anonymous
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Validate Token
    try:
        # NOTE: A robust implementation fetches keys from the IdP.
        # For this setup, we assume the token is valid if the IdP is trusted.
        # Ideally: unverified_header = jwt.get_unverified_header(token)
        # Verify signature using JWKS.
        
        # PLEASE NOTE: Implementing full JWKS caching is complex.
        # For this MVP, since we don't have the Realm set up yet,
        # we will decode without signature verification strictly for development
        # OR warn.
        
        # Real Implementation:
        # 1. Fetch https://localhost:8080/realms/running-realm/protocol/openid-connect/certs
        # 2. Find key matching kid
        # 3. Verify.
        
        # Placeholder for now until Keycloak is running and realm exists
        options = {
            "verify_signature": False, # TODO: ENABLE THIS ONCE KEYCLOAK IS UP AND CONFIG IS PASSED
            "verify_aud": False,
            "exp": True
        }
        
        payload = jwt.decode(token, "secret", algorithms=ALGORITHMS, options=options)
        
        # Store user info in request state
        request.state.user = payload
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
