from sqlalchemy import text
from app.database import SessionLocal


# 전체 평점 조회
def get_ratings():
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT
                user_id,
                movie_id,
                rating
            FROM ratings
            WHERE rating IS NOT NULL
            ORDER BY user_id, movie_id
        """)).mappings().all()

        return [dict(row) for row in rows]


# 특정 고객의 평점 이력
def get_user_history(user_id):
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT
                movie_id,
                rating
            FROM ratings
            WHERE user_id = :user_id
              AND rating IS NOT NULL
            ORDER BY movie_id
        """), {
            "user_id": user_id
        }).mappings().all()

        return [dict(row) for row in rows]


# 고객이 평가하지 않은 영화 조회
def get_unwatched_movies(user_id):
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT
                m.movie_id AS id,
                m.title,
                m.genres
            FROM movies m
            WHERE NOT EXISTS (
                SELECT 1
                FROM ratings r
                WHERE r.movie_id = m.movie_id
                  AND r.user_id = :user_id
            )
            ORDER BY m.movie_id
        """), {"user_id": user_id}).mappings().all()

        return [dict(row) for row in rows]