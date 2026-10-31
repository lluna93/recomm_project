from fastapi import APIRouter, Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import schema, service


router = APIRouter(tags=["Auth"])

bearer_scheme = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    if credentials is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return service.get_current_user(
        db,
        credentials.credentials,
    )


@router.post(
    "/users",
    response_model=schema.VerificationResponse,
    status_code=201,
)
def signup(
    data: schema.SignupRequest,
    db: Session = Depends(get_db),
):
    return service.signup(db, data)


@router.post(
    "/auth/verify-email",
    response_model=schema.MessageResponse,
)
def verify_email(
    data: schema.VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    return service.verify_email(db, data)


@router.post(
    "/auth/resend-code",
    response_model=schema.VerificationResponse,
)
def resend_code(
    data: schema.EmailRequest,
    db: Session = Depends(get_db),
):
    return service.resend_code(db, data)


@router.post(
    "/auth/login",
    response_model=schema.TokenResponse,
)
def login(
    data: schema.LoginRequest,
    db: Session = Depends(get_db),
):
    return service.login(db, data)


@router.get(
    "/users/me",
    response_model=schema.UserResponse,
)
def me(user=Depends(current_user)):
    return user