from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from asset_registry.errors import AppError
from asset_registry.auth.deps import get_current_user, require_admin
from asset_registry.auth.security import create_access_token, hash_password, verify_password
from asset_registry.db.models import User
from asset_registry.db.session import get_db
from asset_registry.domain.constants import VALID_ROLES
from asset_registry.schemas import LoginRequest, TokenResponse, UserCreateRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in and receive a credential",
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == body.username).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(
            status_code=401,
            error="not_authenticated",
            message="Username or password is not recognised.",
        )
    token, expires_in = create_access_token(user.username, user.role)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        role=user.role,
        username=user.username,
    )


@router.post(
    "/users",
    response_model=UserPublic,
    status_code=201,
    summary="Create a user account (administrator only)",
)
def create_user(
    body: UserCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserPublic:
    role = body.role.strip().lower()
    if role not in VALID_ROLES:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": "role", "reason": "must be 'surveyor' or 'admin'"}],
        )
    existing = db.query(User).filter(User.username == body.username).one_or_none()
    if existing is not None:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": "username", "reason": "is already in use"}],
        )
    user = User(
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserPublic(username=user.username, role=user.role, created_at=user.created_at)


@router.get("/me", response_model=UserPublic, summary="Current signed-in user")
def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(username=user.username, role=user.role, created_at=user.created_at)
