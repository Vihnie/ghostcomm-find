from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash("a-dummy-password-for-timing")
bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def issue_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": "campus-lost-found",
            "aud": "campus-api",
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def current_user(token: str = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer="campus-lost-found",
            audience="campus-api",
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        user = db.get(User, claims["sub"])
        if user is not None:
            return user
    except jwt.InvalidTokenError:
        pass
    raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


class RateLimiter:
    # In-process limits are intended for a single-worker deployment.
    def __init__(self):
        self.events = defaultdict(deque)
        self.lock = Lock()

    def check(self, key: str, limit: int, seconds: int = 60):
        now = monotonic()
        with self.lock:
            for stale in [key for key, times in self.events.items() if times[-1] <= now - seconds]:
                del self.events[stale]
            events = self.events[key]
            while events and events[0] <= now - seconds:
                events.popleft()
            if len(events) >= limit:
                raise HTTPException(429, "Too many requests", headers={"Retry-After": str(seconds)})
            events.append(now)


limiter = RateLimiter()


def limit_auth(request: Request):
    host = request.client.host if request.client else "unknown"
    limiter.check(f"auth:{host}", 10)
