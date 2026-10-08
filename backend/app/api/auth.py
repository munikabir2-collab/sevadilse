from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user_model import User
from app.models.provider_model import Provider
from app.schemas.auth_schema import (
    UserCreate,
    UserOut,
    LoginRequest,
    Token,
    CurrentUserOut,
)


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ============================================================
# JWT SETTINGS
# ============================================================

SECRET_KEY = "servicehub-change-this-secret-key-in-production"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# ============================================================
# OAUTH2
# ============================================================
# Swagger Authorize ke liye /auth/token use hoga.
#
# IMPORTANT:
# /auth/login = JSON login
# /auth/token = Swagger OAuth2 form login
# ============================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token"
)


# ============================================================
# PASSWORD HELPERS
# ============================================================

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def get_password_hash(
    password: str,
) -> str:
    return pwd_context.hash(password)


# ============================================================
# JWT HELPERS
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update(
        {
            "exp": expire,
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


# ============================================================
# SIGNUP
# ============================================================

@router.post(
    "/signup",
    response_model=UserOut,
)
def signup(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email pehle se registered hai",
        )

    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        phone=user.phone,
        is_provider=user.is_provider,
        is_admin=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ============================================================
# LOGIN - JSON
# ============================================================
# Existing frontend/mobile login.
#
# Request:
# {
#   "email": "...",
#   "password": "..."
# }
# ============================================================

@router.post(
    "/login",
    response_model=Token,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == login_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ya password galat hai",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ya password galat hai",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    provider = (
        db.query(Provider)
        .filter(Provider.owner_id == user.id)
        .first()
    )

    provider_id = provider.id if provider else None

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_provider": user.is_provider,
            "is_admin": user.is_admin,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "provider_id": provider_id,
        "is_provider": user.is_provider,
        "is_admin": user.is_admin,
    }


# ============================================================
# OAUTH2 TOKEN LOGIN
# ============================================================
# Swagger UI ke Authorize button ke liye.
#
# Swagger internally:
# username = email
# password = password
#
# Content-Type:
# application/x-www-form-urlencoded
# ============================================================

@router.post(
    "/token",
    response_model=Token,
)
def token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Swagger ka "username" field hum email ke liye use kar rahe hain.
    user = (
        db.query(User)
        .filter(User.email == form_data.username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ya password galat hai",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ya password galat hai",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    provider = (
        db.query(Provider)
        .filter(Provider.owner_id == user.id)
        .first()
    )

    provider_id = provider.id if provider else None

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_provider": user.is_provider,
            "is_admin": user.is_admin,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "provider_id": provider_id,
        "is_provider": user.is_provider,
        "is_admin": user.is_admin,
    }


# ============================================================
# GET CURRENT USER
# ============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid ya expired authentication token",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


# ============================================================
# CURRENT USER API
# ============================================================

@router.get(
    "/me",
    response_model=CurrentUserOut,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user

