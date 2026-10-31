
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from sqlalchemy import text

from app.database import engine


DATA_DIR = Path(__file__).resolve().parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.pkl"
MOVIES_FILE = DATA_DIR / "movies.dat"

BATCH_SIZE = 100_000


def create_tables():
    """기존 테이블은 유지하고, 없는 테이블만 생성."""

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS movies (
                movie_id BIGINT PRIMARY KEY,
                title TEXT NOT NULL,
                genres TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ratings (
                source_row BIGINT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                movie_id BIGINT NOT NULL,
                rating REAL NOT NULL
            )
        """))

    print("테이블 확인 완료")


def load_movies():
    """movies.dat 적재. 이미 존재하는 영화는 건너뜀."""

    movies = []

    with open(MOVIES_FILE, "r", encoding="latin-1") as file:
        for line in tqdm(file, desc="영화 파일 읽기"):
            movie_id, title, genres = line.rstrip("\r\n").split("::", 2)
            movies.append((int(movie_id), title, genres))

    with engine.begin() as conn:
        for movie_id, title, genres in tqdm(movies, desc="영화 적재"):
            conn.execute(
                text("""
                    INSERT INTO movies (movie_id, title, genres)
                    VALUES (:movie_id, :title, :genres)
                    ON CONFLICT (movie_id) DO NOTHING
                """),
                {
                    "movie_id": movie_id,
                    "title": title,
                    "genres": genres,
                },
            )


def load_ratings():
    """
    ratings.pkl을 긴 표로 적재.
    중간에 중단되어도 다음 실행에서 이어서 적재.
    """

    df = pd.read_pickle(RATINGS_FILE)

    required = {"userID", "movieID", "ratings"}
    if not required.issubset(df.columns):
        raise ValueError(f"필수 컬럼 누락: {required - set(df.columns)}")

    # PostgreSQL에 이미 적재된 마지막 원본 행 번호
    with engine.connect() as conn:
        last_row = conn.execute(
            text("SELECT COALESCE(MAX(source_row), -1) FROM ratings")
        ).scalar_one()

    start = int(last_row) + 1
    total = len(df)

    print(f"원본 평점 수: {total:,}")
    print(f"적재 시작 위치: {start:,}")

    if start >= total:
        print("이미 모든 평점이 적재되어 있습니다.")
        return

    raw = df[["userID", "movieID", "ratings"]]

    # COPY는 대량 적재 시 INSERT보다 효율적
    with tqdm(
        total=total,
        initial=start,
        desc="평점 적재",
        unit="rows",
    ) as progress:

        for offset in range(start, total, BATCH_SIZE):
            end = min(offset + BATCH_SIZE, total)
            batch = raw.iloc[offset:end]

            # 배치별 트랜잭션: 성공한 배치만 커밋
            with engine.begin() as conn:
                raw_connection = conn.connection.driver_connection

                with raw_connection.cursor() as cursor:
                    with cursor.copy("""
                        COPY ratings
                        (source_row, user_id, movie_id, rating)
                        FROM STDIN
                    """) as copy:

                        for i, row in enumerate(
                            batch.itertuples(index=False, name=None),
                            start=offset,
                        ):
                            user_id, movie_id, rating = row
                            copy.write_row((
                                i,
                                int(user_id),
                                int(movie_id),
                                float(rating),
                            ))

            progress.update(end - offset)


def show_counts():
    """적재 완료 후 실제 DB 행 수 출력."""

    with engine.connect() as conn:
        movie_count = conn.execute(
            text("SELECT COUNT(*) FROM movies")
        ).scalar_one()

        rating_count = conn.execute(
            text("SELECT COUNT(*) FROM ratings")
        ).scalar_one()

    print("\n========== 적재 결과 ==========")
    print(f"영화 수 : {movie_count:,}")
    print(f"평점 수 : {rating_count:,}")
    print("===============================")


def main():
    create_tables()
    load_movies()
    load_ratings()
    show_counts()


if __name__ == "__main__":
    main()
