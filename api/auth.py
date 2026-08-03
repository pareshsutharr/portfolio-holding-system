"""Password, signed-session, and FastAPI authorization helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from market_etl.models import UserAccount

SESSION_SECONDS = 12 * 60 * 60
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return "pbkdf2_sha256$310000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds)
        )
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


def _secret() -> bytes:
    value = os.getenv("AUTH_SECRET", "")
    if len(value) >= 32:
        return value.encode()
    # Local installations get a stable, private generated key. Deployments should
    # supply AUTH_SECRET so sessions remain valid across multiple instances.
    secret_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime", ".auth-secret")
    os.makedirs(os.path.dirname(secret_path), exist_ok=True)
    try:
        with open(secret_path, "rb") as source:
            stored = source.read().strip()
            if len(stored) >= 32:
                return stored
    except FileNotFoundError:
        pass
    stored = secrets.token_urlsafe(48).encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(secret_path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(stored)
    except FileExistsError:
        with open(secret_path, "rb") as source:
            stored = source.read().strip()
    return stored


def issue_token(user: UserAccount, *, acting_as: str | None = None) -> str:
    payload = {"sub": user.id, "role": user.role, "exp": int(time.time()) + SESSION_SECONDS}
    if acting_as:
        payload["act"] = acting_as
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(_secret(), body, hashlib.sha256).digest()
    return body.decode() + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


def decode_token(token: str) -> dict:
    try:
        body_text, signature_text = token.split(".", 1)
        body = body_text.encode()
        signature = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
        if not hmac.compare_digest(signature, hmac.new(_secret(), body, hashlib.sha256).digest()):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(body_text + "=" * (-len(body_text) % 4)))
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError
        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Session is invalid or expired")


@dataclass
class Principal:
    user: UserAccount
    owner: UserAccount
    is_impersonating: bool = False


def principal_dependency(engine):
    def get_principal(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> Principal:
        if not credentials:
            raise HTTPException(status_code=401, detail="Please sign in")
        payload = decode_token(credentials.credentials)
        with Session(engine) as session:
            user = session.get(UserAccount, payload["sub"])
            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="Account is unavailable")
            owner = user
            acting_as = payload.get("act")
            if acting_as:
                if user.role != "admin":
                    raise HTTPException(status_code=403, detail="Impersonation is restricted to admins")
                owner = session.get(UserAccount, acting_as)
                if not owner or owner.role != "client" or not owner.is_active:
                    raise HTTPException(status_code=404, detail="Client account is unavailable")
            session.expunge(user)
            if owner is not user:
                session.expunge(owner)
            return Principal(user=user, owner=owner, is_impersonating=bool(acting_as))
    return get_principal


def require_admin(principal: Principal) -> Principal:
    if principal.user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return principal
