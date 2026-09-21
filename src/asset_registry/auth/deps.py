from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from asset_registry.errors import AppError
from asset_registry.auth.security import decode_access_token
from asset_registry.db.models import User
from asset_registry.db.session import get_db
from asset_registry.domain.constants import ROLE_ADMIN

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError(
            status_code=401,
            error="not_authenticated",
            message="Sign in is required to access asset data.",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        username = payload.get("sub")
        if not username:
            raise InvalidTokenError("missing subject")
    except InvalidTokenError:
        raise AppError(
            status_code=401,
            error="not_authenticated",
            message="The sign-in credential is missing, invalid or has expired.",
        ) from None

    user = db.query(User).filter(User.username == username).one_or_none()
    if user is None:
        raise AppError(
            status_code=401,
            error="not_authenticated",
            message="The sign-in credential is missing, invalid or has expired.",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin():
        raise AppError(
            status_code=403,
            error="forbidden",
            message="Only an administrator may perform this action.",
            details=[{"field": "role", "reason": f"role '{user.role}' cannot delete or administer"}],
        )
    return user


def admin_role() -> str:
    return ROLE_ADMIN
