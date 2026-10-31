import pandas as pd
from sqlalchemy import text

from app.database import engine


def get_user_ids():
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT DISTINCT user_id FROM ratings ORDER BY user_id"),
            conn,
        )["user_id"].to_numpy(dtype="int64")


def get_movie_ids():
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT movie_id FROM movies ORDER BY movie_id"),
            conn,
        )["movie_id"].to_numpy(dtype="int64")


def iter_ratings(chunk_size=100_000):
    """
    PostgreSQL에서 평점을 일정 크기로 읽음.
    한 번에 전체 DataFrame을 만들지 않음.
    """
    with engine.connect().execution_options(
        stream_results=True
    ) as conn:
        query = text("""
            SELECT user_id, movie_id, rating
            FROM ratings
            ORDER BY source_row
        """)

        for chunk in pd.read_sql(
            query,
            conn,
            chunksize=chunk_size,
        ):
            yield chunk


def get_movies_by_ids(movie_ids):
    if not movie_ids:
        return {}

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT movie_id, title, genres
                FROM movies
                WHERE movie_id = ANY(:movie_ids)
            """),
            {"movie_ids": movie_ids},
        ).mappings().all()

    return {
        int(row["movie_id"]): {
            "title": row["title"],
            "genres": row["genres"],
        }
        for row in rows
    }


def get_seen_movie_ids(user_id):
    """실제 DB 기준으로 사용자가 평가한 영화 조회."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT movie_id
                FROM ratings
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        ).scalars().all()

    return set(map(int, rows))