import smtplib
import jwt

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from uuid import UUID

from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError

from app.auth import repository
from app.config import settings


password_hasher = PasswordHash.recommended()

DUMMY_PASSWORD_HASH = password_hasher.hash(
    "dummy-password-not-used-for-login"
)


# -------------------------
# Gmail HTML 메일
# -------------------------

def send_email(email, code):
    msg = EmailMessage()

    msg["Subject"] = "[Recomm Project] 이메일 인증번호"
    msg["From"] = settings.GMAIL_ADDRESS
    msg["To"] = email

    html = f"""
    <html>
      <body style="font-family:Arial,sans-serif;">
        <div style="max-width:480px;margin:auto;padding:24px;">
          <h2>Recomm Project 이메일 인증</h2>
          <p>아래 인증번호를 입력해주세요.</p>

          <div style="
            font-size:32px;
            font-weight:bold;
            letter-spacing:8px;
            text-align:center;
            padding:20px;
            background:#f5f7fb;
            border-radius:8px;
          ">
            {code}
          </div>

          <p>인증번호는 5분 동안 유효합니다.</p>
          <p>본인이 요청하지 않았다면 이 메일을 무시하세요.</p>
        </div>
      </body>
    </html>
    """

    msg.set_content(
        f"인증번호: {code}\n유효시간: 5분"
    )

    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=15,
    ) as smtp:
        smtp.login(
            settings.GMAIL_ADDRESS,
            settings.GMAIL_APP_PASSWORD,
        )
        smtp.send_message(msg)


# -------------------------
# 인증번호 발송
# -------------------------

def issue_verification_code(email):
    status, wait_seconds = repository.reserve_email_send(email)

    if status == 0:
        raise HTTPException(
            status_code=429,
            detail=f"{wait_seconds}초 후 재전송할 수 있습니다.",
        )

    if status == 1:
        raise HTTPException(
            status_code=429,
            detail="한 시간에 최대 5번까지 발송할 수 있습니다.",
        )

    code = repository.generate_code()

    try:
        send_email(email, code)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="인증 메일 발송에 실패했습니다. 잠시 후 다시 시도하세요.",
        )

    return repository.save_verification_code(email, code)


# -------------------------
# 회원가입
# -------------------------

def signup(db, data):
    email = repository.normalize_email(str(data.email))

    existing = repository.get_user_by_email(db, email)

    if existing:
        raise HTTPException(
            status_code=409,
            detail="이미 가입된 이메일입니다.",
        )

    password_hash = password_hasher.hash(data.password)

    try:
        repository.create_user(
            db,
            name=data.name,
            email=email,
            password_hash=password_hash,
        )
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="이미 가입된 이메일입니다.",
        )

    return {
        "message": "인증 메일을 발송했습니다.",
        **issue_verification_code(email),
    }


# -------------------------
# 인증번호 재전송
# -------------------------

def resend_code(db, data):
    email = repository.normalize_email(str(data.email))
    user = repository.get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="가입되지 않은 이메일입니다.",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="이미 인증된 이메일입니다.",
        )

    return {
        "message": "인증번호를 다시 발송했습니다.",
        **issue_verification_code(email),
    }


# -------------------------
# 이메일 인증
# -------------------------

def verify_email(db, data):
    email = repository.normalize_email(str(data.email))
    user = repository.get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="가입되지 않은 이메일입니다.",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="이미 인증된 이메일입니다.",
        )

    result = repository.verify_code(email, data.code)

    if result == -1:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 만료되었거나 존재하지 않습니다.",
        )

    if result == -2:
        raise HTTPException(
            status_code=429,
            detail="인증 시도 5회를 초과했습니다. 다시 발급받으세요.",
        )

    if result == 0:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 일치하지 않습니다.",
        )

    repository.mark_user_verified(db, user)

    return {
        "message": "이메일 인증이 완료되었습니다."
    }


# -------------------------
# JWT 발급
# -------------------------

def create_access_token(user_id):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# -------------------------
# 로그인
# -------------------------

def login(db, data):
    email = repository.normalize_email(str(data.email))
    user = repository.get_user_by_email(db, email)

    if not user:
        password_hasher.verify(
            data.password,
            DUMMY_PASSWORD_HASH,
        )

        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not password_hasher.verify(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="이메일 인증을 먼저 완료해주세요.",
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


# -------------------------
# JWT 검증
# -------------------------

def get_current_user(db, token):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "require": ["sub", "exp", "iat"]
            },
        )

        user_id = UUID(payload["sub"])

    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="유효하지 않거나 만료된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = repository.get_user_by_id(db, user_id)

    if not user or not user.is_verified:
        raise HTTPException(
            status_code=401,
            detail="인증할 수 없는 사용자입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user