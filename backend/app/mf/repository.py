from sqlalchemy import text
from app.database import SessionLocal


def get_ratings():
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT user_id, movie_id, rating
            FROM ratings
        """)).mappings().all()

        return [dict(row) for row in rows]


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