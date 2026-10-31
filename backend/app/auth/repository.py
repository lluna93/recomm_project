import hashlib
import hmac
import secrets

from datetime import datetime, timedelta, timezone

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.model import User
from app.config import settings


redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    socket_timeout=5,
)


# -------------------------
# PostgreSQL
# -------------------------

def get_user_by_email(db: Session, email: str):
    return db.scalar(
        select(User).where(User.email == email)
    )


def get_user_by_id(db: Session, user_id):
    return db.get(User, user_id)


def create_user(db: Session, name, email, password_hash):
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def mark_user_verified(db: Session, user: User):
    user.is_verified = True
    db.commit()
    db.refresh(user)

    return user


# -------------------------
# Redis key
# -------------------------

def normalize_email(email: str):
    return email.strip().lower()


def code_key(email):
    return f"auth:code:{email}"


def resend_key(email):
    return f"auth:resend:{email}"


def hourly_key(email):
    return f"auth:hourly:{email}"


def make_code_hash(email, code):
    value = f"{email}:{code}".encode()

    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        value,
        hashlib.sha256,
    ).hexdigest()


def generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


# -------------------------
# Redis 발송 제한
# -------------------------

RESERVE_SCRIPT = """
local cooldown = redis.call('TTL', KEYS[1])

if cooldown > 0 then
    return {0, cooldown}
end

local count = tonumber(redis.call('GET', KEYS[2]) or '0')

if count >= 5 then
    return {1, redis.call('TTL', KEYS[2])}
end

redis.call('SET', KEYS[1], '1', 'EX', 60)

local new_count = redis.call('INCR', KEYS[2])

if new_count == 1 then
    redis.call('EXPIRE', KEYS[2], 3600)
end

return {2, 0}
"""


def reserve_email_send(email):
    result = redis_client.eval(
        RESERVE_SCRIPT,
        2,
        resend_key(email),
        hourly_key(email),
    )

    return int(result[0]), int(result[1])


# -------------------------
# Redis 인증번호
# -------------------------

def save_verification_code(email, code):
    now = datetime.now(timezone.utc)

    key = code_key(email)

    redis_client.hset(
        key,
        mapping={
            "hash": make_code_hash(email, code),
            "attempts": 0,
        },
    )

    redis_client.expire(key, 300)

    return {
        "server_time": now,
        "expires_at": now + timedelta(minutes=5),
        "resend_available_at": now + timedelta(seconds=60),
    }


VERIFY_SCRIPT = """
local stored = redis.call('HGET', KEYS[1], 'hash')

if not stored then
    return -1
end

local attempts = tonumber(
    redis.call('HGET', KEYS[1], 'attempts') or '0'
)

if attempts >= 5 then
    return -2
end

if stored == ARGV[1] then
    redis.call('DEL', KEYS[1])
    return 1
end

attempts = redis.call('HINCRBY', KEYS[1], 'attempts', 1)

if attempts >= 5 then
    redis.call('DEL', KEYS[1])
    return -2
end

return 0
"""


def verify_code(email, code):
    return int(
        redis_client.eval(
            VERIFY_SCRIPT,
            1,
            code_key(email),
            make_code_hash(email, code),
        )
    )


def delete_code(email):
    redis_client.delete(code_key(email))