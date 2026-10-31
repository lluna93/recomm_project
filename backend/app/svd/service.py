from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import coo_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
)
from tqdm import tqdm

from app.svd import repository
from app.svd.model import SVDModel


CHECKPOINT_DIR = Path(__file__).resolve().parents[2] / "checkpoint"
MODEL_PATH = CHECKPOINT_DIR / "svd_model.joblib"

N_COMPONENTS = 30
TEST_RATIO = 0.1
RANDOM_STATE = 42

_model = None


def train():
    """
    PostgreSQL 데이터를 읽어 희소 행렬 기반 SVD 학습.
    기존 movies/ratings 테이블은 변경하지 않음.
    """

    print("사용자 및 영화 ID 조회 중...")

    user_ids = repository.get_user_ids()
    movie_ids = repository.get_movie_ids()

    if len(user_ids) < 2 or len(movie_ids) < 2:
        raise ValueError("SVD 학습을 위한 사용자/영화 수가 부족합니다.")

    # ID가 정렬되어 있으므로 searchsorted로 인덱스 변환
    # 1,000만 행에 대한 Python 딕셔너리 조회를 피함
    row_parts = []
    col_parts = []
    rating_parts = []

    print("평점 데이터 읽는 중...")

    for chunk in tqdm(
        repository.iter_ratings(),
        desc="DB 평점 조회",
        unit="batch",
    ):
        users = chunk["user_id"].to_numpy(dtype=np.int64)
        movies = chunk["movie_id"].to_numpy(dtype=np.int64)
        ratings = chunk["rating"].to_numpy(dtype=np.float32)

        rows = np.searchsorted(user_ids, users)
        cols = np.searchsorted(movie_ids, movies)

        # ratings에 존재하지만 movies에는 없는 영화는 제외
        valid = (
            (cols < len(movie_ids))
            & (movie_ids[np.minimum(cols, len(movie_ids) - 1)] == movies)
        )

        row_parts.append(rows[valid].astype(np.int32))
        col_parts.append(cols[valid].astype(np.int32))
        rating_parts.append(ratings[valid])

    if not rating_parts:
        raise ValueError("학습할 평점 데이터가 없습니다.")

    rows = np.concatenate(row_parts)
    cols = np.concatenate(col_parts)
    values = np.concatenate(rating_parts)

    del row_parts, col_parts, rating_parts

    n_users = len(user_ids)
    n_movies = len(movie_ids)
    shape = (n_users, n_movies)

    print(f"사용자: {n_users:,}")
    print(f"영화: {n_movies:,}")
    print(f"평점: {len(values):,}")

    # 전체 관측 여부: 추천 시 이미 본 영화 제외
    seen_matrix = coo_matrix(
        (
            np.ones(len(values), dtype=np.float32),
            (rows, cols),
        ),
        shape=shape,
    ).tocsr()

    seen_matrix.data[:] = 1.0

    # 검증 데이터 분리
    rng = np.random.default_rng(RANDOM_STATE)
    test_mask = rng.random(len(values)) < TEST_RATIO

    # 학습 평점이 없는 사용자를 최소화하기 위해
    # 사용자별 첫 관측 평점은 학습에 남김
    first_positions = np.unique(
        rows,
        return_index=True,
    )[1]
    test_mask[first_positions] = False

    train_mask = ~test_mask

    train_rows = rows[train_mask]
    train_cols = cols[train_mask]
    train_values = values[train_mask]

    test_rows = rows[test_mask]
    test_cols = cols[test_mask]
    test_values = values[test_mask]

    if len(test_values) == 0:
        raise ValueError("검증 평점이 부족합니다.")

    # 사용자 평균 평점 계산
    counts = np.bincount(
        train_rows,
        minlength=n_users,
    )

    sums = np.bincount(
        train_rows,
        weights=train_values,
        minlength=n_users,
    )

    global_mean = float(train_values.mean())

    user_means = np.full(
        n_users,
        global_mean,
        dtype=np.float32,
    )

    np.divide(
        sums,
        counts,
        out=user_means,
        where=counts > 0,
    )

    # 평균 중심화: 평점 - 사용자 평균
    centered_values = (
        train_values - user_means[train_rows]
    ).astype(np.float32)

    # 고객×영화 Dense Pivot 생성하지 않음
    train_matrix = coo_matrix(
        (
            centered_values,
            (train_rows, train_cols),
        ),
        shape=shape,
    ).tocsr()

    # 잠재 차원 30개
    k = min(N_COMPONENTS, min(shape) - 1)

    print(f"TruncatedSVD 학습 시작 (차원={k})")

    svd = TruncatedSVD(
        n_components=k,
        n_iter=7,
        random_state=RANDOM_STATE,
    )

    # (사용자 수 × k) — Dense지만 전체 평점 행렬은 아님
    user_factors = svd.fit_transform(train_matrix).astype(
        np.float32
    )

    # (영화 수 × k)
    item_factors = svd.components_.T.astype(np.float32)

    print("검증 데이터 평가 중...")

    # 예측 = 사용자 평균 + 사용자벡터 · 영화벡터
    predictions = (
        user_means[test_rows]
        + np.sum(
            user_factors[test_rows]
            * item_factors[test_cols],
            axis=1,
        )
    )

    predictions = np.clip(predictions, 1.0, 5.0)

    mae = float(mean_absolute_error(test_values, predictions))
    mse = float(mean_squared_error(test_values, predictions))
    rmse = float(np.sqrt(mse))

    model = SVDModel(
        user_ids=user_ids,
        movie_ids=movie_ids,
        user_factors=user_factors,
        item_factors=item_factors,
        user_means=user_means,
        global_mean=global_mean,
        seen_matrix=seen_matrix,
        mae=mae,
        mse=mse,
        rmse=rmse,
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH, compress=3)

    global _model
    _model = model

    print(f"모델 저장 완료: {MODEL_PATH}")
    print(f"MAE={mae:.4f}, MSE={mse:.4f}, RMSE={rmse:.4f}")

    return model


def get_model():
    global _model

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "SVD 모델이 없습니다. 먼저 학습을 실행하세요."
        )

    _model = joblib.load(MODEL_PATH)
    return _model


def get_kpi():
    model = get_model()

    return {
        "mae": round(model.mae, 4),
        "mse": round(model.mse, 4),
        "rmse": round(model.rmse, 4),
    }


GENRE_KO = {
    "Action": "액션",
    "Adventure": "모험",
    "Animation": "애니메이션",
    "Children": "어린이",
    "Children's": "어린이",
    "Comedy": "코미디",
    "Crime": "범죄",
    "Documentary": "다큐멘터리",
    "Drama": "드라마",
    "Fantasy": "판타지",
    "Film-Noir": "필름 누아르",
    "Horror": "공포",
    "Musical": "뮤지컬",
    "Mystery": "미스터리",
    "Romance": "로맨스",
    "Sci-Fi": "SF",
    "Thriller": "스릴러",
    "War": "전쟁",
    "Western": "서부극",
    "(no genres listed)": "장르 미상",
}


def translate_genres(genres):
    if not genres:
        return "장르 미상"

    return ", ".join(
        GENRE_KO.get(genre, genre)
        for genre in genres.split("|")
    )


def get_recommendations(user_id: int):
    model = get_model()

    # 원본 사용자 ID → 내부 행 인덱스
    index = int(np.searchsorted(model.user_ids, user_id))

    if (
        index >= len(model.user_ids)
        or int(model.user_ids[index]) != user_id
    ):
        raise ValueError("존재하지 않는 사용자 ID입니다.")

    # 모든 영화에 대한 예측 평점
    # 영화 수 크기의 1차원 벡터만 생성
    scores = (
        model.user_means[index]
        + model.item_factors @ model.user_factors[index]
    )

    scores = np.clip(scores, 1.0, 5.0)

    # 학습 당시 관측한 영화 제외
    start = model.seen_matrix.indptr[index]
    end = model.seen_matrix.indptr[index + 1]
    seen_indices = model.seen_matrix.indices[start:end]

    scores[seen_indices] = -np.inf

    # 현재 DB에 기록된 관람 영화도 제외
    db_seen_ids = repository.get_seen_movie_ids(user_id)

    for movie_id in db_seen_ids:
        col = int(np.searchsorted(model.movie_ids, movie_id))
        if (
            col < len(model.movie_ids)
            and int(model.movie_ids[col]) == movie_id
        ):
            scores[col] = -np.inf

    # 상위 5개 인덱스 선택
    available = np.flatnonzero(np.isfinite(scores))
    top_indices = available[
        np.argsort(-scores[available], kind="stable")[:5]
    ]

    top_movie_ids = [
        int(model.movie_ids[i])
        for i in top_indices
    ]

    movie_info = repository.get_movies_by_ids(top_movie_ids)

    recommendations = []

    for i, col in enumerate(top_indices, start=1):
        movie_id = int(model.movie_ids[col])
        movie = movie_info.get(movie_id)

        if movie is None:
            continue

        recommendations.append({
            "rank": len(recommendations) + 1,
            "movie_id": movie_id,
            "title": movie["title"],
            "genres": translate_genres(movie["genres"]),
            "predicted_rating": round(float(scores[col]), 2),
        })

    return {
        "user_id": user_id,
        "recommendations": recommendations,
    }