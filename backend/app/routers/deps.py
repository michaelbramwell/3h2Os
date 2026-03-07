from fastapi import APIRouter, Depends, Request
import os
import logging
from sqlmodel import Session, select
from app.core.database import get_session, User

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    # 1. Get Payload from verify_jwt_middleware
    user_payload = getattr(request.state, "user", None)

    username = "runner"  # Default fallback
    email = "runner@example.com"

    if user_payload:
        # Keycloak usually sends 'preferred_username'
        username = user_payload.get(
            "preferred_username", user_payload.get("sub", "runner")
        )
        email = user_payload.get("email", f"{username}@example.com")
    else:
        # Fallback to Env if set (for local dev without auth header)
        if os.environ.get("DEFAULT_USERNAME"):
            username = os.environ.get("DEFAULT_USERNAME")

    # 2. Find or Create User in DB
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        logger.info(f"User {username} not found in DB. Auto-provisioning new user.")
        # Auto-provision (JIT)
        user = User(username=username, email=email)
        session.add(user)
        session.commit()
        session.refresh(user)

    return user
