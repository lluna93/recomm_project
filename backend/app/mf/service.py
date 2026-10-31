
from pathlib import Path
from threading import Lock
import math
import os
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from . import repository
from .model import MFModel


# =========================================================
# 1. 기본 설정
# =========================================================

CHECKPOINT = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "mf.pt"
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available()
    else "cpu"
)

MODEL_DIM = 30
RATING_MIN = 0.5
RATING_MAX = 5.0

_model = None
_user_map = None
_movie_map = None

# 같은 서버 프로세스에서 KPI 중복 계산 방지
_kpi_lock = Lock()


def log(message):
    print(f"[MF] {message}", flush=True)


# =========================================================
# 2. 체크포인트 관리
# =========================================================

def read_checkpoint():
    if not CHECKPOINT.exists():
        raise FileNotFoundError(
            f"MF 체크포인트가 없습니다: {CHECKPOINT}"
        )

    return torch.load(
        CHECKPOINT,
        map_location="cpu",
        weights_only=True
    )


def save_checkpoint(ckpt):
    CHECKPOINT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = CHECKPOINT.with_suffix(".pt.tmp")

    try:
        torch.save(ckpt, temp_path)
        os.replace(temp_path, CHECKPOINT)
    finally:
        if temp_path.exists():
            temp_path.unlink()


# =========================================================
# 3. 평가 공통 함수
# =========================================================

def evaluate_model(model, loader):
    """
    배치 단위로 예측하여 MAE, MSE, RMSE 계산
    """

    model.eval()

    abs_sum = 0.0
    sq_sum = 0.0
    count = 0

    total_batches = len(loader)
    start = time.perf_counter()

    log(
        f"평가 시작: {total_batches:,}개 배치, "
        f"device={DEVICE}"
    )

    with torch.inference_mode():
        for batch_no, (u, m, y) in enumerate(
            loader,
            start=1
        ):
            u = u.to(DEVICE)
            m = m.to(DEVICE)

            pred = model(u, m).clamp(
                RATING_MIN,
                RATING_MAX
            )

            error = (
                pred.cpu().to(torch.float64)
                - y.to(torch.float64)
            )

            abs_sum += error.abs().sum().item()
            sq_sum += error.square().sum().item()
            count += error.numel()

            # 평가 진행 상황 출력
            if (
                batch_no == 1
                or batch_no % 20 == 0
                or batch_no == total_batches
            ):
                elapsed = time.perf_counter() - start

                log(
                    f"평가 진행: "
                    f"{batch_no:,}/{total_batches:,} 배치, "
                    f"{count:,}건, "
                    f"{elapsed:.2f}초"
                )

    if count == 0:
        raise ValueError(
            "평가 가능한 검증 데이터가 없습니다."
        )

    mse = sq_sum / count

    kpi = {
        "mae": abs_sum / count,
        "mse": mse,
        "rmse": math.sqrt(mse)
    }

    log(f"평가 완료: {kpi}")

    return kpi


# =========================================================
# 4. 모델 학습
# =========================================================

def train(epochs=20, batch_size=4096, lr=0.001):
    global _model, _user_map, _movie_map

    start = time.perf_counter()

    log("학습 데이터 조회 시작")

    rows = repository.get_ratings()

    log(f"학습 데이터 조회 완료: {len(rows):,}건")

    if len(rows) < 2:
        raise ValueError(
            "학습할 평점이 부족합니다."
        )

    # 학습 80%, 검증 20%
    rng = np.random.default_rng(42)
    indices = rng.permutation(len(rows))

    valid_size = max(
        1,
        int(len(rows) * 0.2)
    )

    valid_rows = [
        rows[i]
        for i in indices[:valid_size]
    ]

    train_rows = [
        rows[i]
        for i in indices[valid_size:]
    ]

    users = sorted({
        r["user_id"]
        for r in train_rows
    })

    movies = sorted({
        r["movie_id"]
        for r in train_rows
    })

    user_map = {
        user_id: i
        for i, user_id in enumerate(users)
    }

    movie_map = {
        movie_id: i
        for i, movie_id in enumerate(movies)
    }

    def encode(data):
        data = [
            r for r in data
            if r["user_id"] in user_map
            and r["movie_id"] in movie_map
        ]

        u = torch.tensor(
            [user_map[r["user_id"]] for r in data],
            dtype=torch.long
        )

        m = torch.tensor(
            [movie_map[r["movie_id"]] for r in data],
            dtype=torch.long
        )

        y = torch.tensor(
            [float(r["rating"]) for r in data],
            dtype=torch.float32
        )

        return TensorDataset(u, m, y)

    train_ds = encode(train_rows)
    valid_ds = encode(valid_rows)

    if len(valid_ds) == 0:
        raise ValueError(
            "평가 가능한 검증 데이터가 없습니다."
        )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        pin_memory=(DEVICE.type == "cuda"),
        num_workers=0
    )

    valid_loader = DataLoader(
        valid_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    model = MFModel(
        len(users),
        len(movies),
        MODEL_DIM
    ).to(DEVICE)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=lr,
        weight_decay=1e-5
    )

    log(
        f"학습 시작: "
        f"train={len(train_ds):,}, "
        f"valid={len(valid_ds):,}, "
        f"device={DEVICE}"
    )

    for epoch in range(epochs):
        model.train()

        total_loss = 0.0
        total_count = 0

        for u, m, y in train_loader:
            u = u.to(DEVICE)
            m = m.to(DEVICE)
            y = y.to(DEVICE)

            optimizer.zero_grad(set_to_none=True)

            pred = model(u, m)
            loss = torch.mean((pred - y) ** 2)

            loss.backward()
            optimizer.step()

            total_loss += (
                loss.detach().item() * y.size(0)
            )
            total_count += y.size(0)

        epoch_loss = total_loss / total_count

        log(
            f"Epoch {epoch + 1}/{epochs} "
            f"Loss={epoch_loss:.6f}"
        )

    kpi = evaluate_model(
        model,
        valid_loader
    )

    ckpt = {
        "state_dict": {
            k: v.detach().cpu()
            for k, v in model.state_dict().items()
        },
        "users": users,
        "movies": movies,
        "dim": MODEL_DIM,
        "kpi": kpi
    }

    save_checkpoint(ckpt)

    _model = model
    _model.eval()

    _user_map = user_map
    _movie_map = movie_map

    log(
        f"학습 및 저장 완료: "
        f"{time.perf_counter() - start:.2f}초"
    )

    return kpi


# =========================================================
# 5. 기존 모델 로드
# =========================================================

def load_model():
    global _model, _user_map, _movie_map

    if _model is not None:
        return

    start = time.perf_counter()

    log("모델 로드 시작")

    ckpt = read_checkpoint()

    _user_map = {
        v: i
        for i, v in enumerate(ckpt["users"])
    }

    _movie_map = {
        v: i
        for i, v in enumerate(ckpt["movies"])
    }

    _model = MFModel(
        len(_user_map),
        len(_movie_map),
        ckpt["dim"]
    ).to(DEVICE)

    _model.load_state_dict(
        ckpt["state_dict"]
    )

    _model.eval()

    log(
        f"모델 로드 완료: "
        f"users={len(_user_map):,}, "
        f"movies={len(_movie_map):,}, "
        f"device={DEVICE}, "
        f"{time.perf_counter() - start:.2f}초"
    )


# =========================================================
# 6. KPI 조회
# =========================================================

def get_kpi():
    """
    KPI가 이미 mf.pt에 있으면 즉시 반환한다.

    KPI가 없다면:
    1. 기존 모델 로드
    2. 검증 데이터 구성
    3. 배치 평가
    4. 기존 mf.pt에 KPI 추가 저장

    재학습하지 않는다.
    """

    start = time.perf_counter()

    # 중복 요청이 들어와도 한 번만 계산
    with _kpi_lock:

        log("KPI 요청 수신")

        ckpt = read_checkpoint()

        # 저장된 KPI가 있다면 바로 반환
        if ckpt.get("kpi") is not None:
            log("저장된 KPI 즉시 반환")
            return ckpt["kpi"]

        log(
            "체크포인트에 KPI가 없어 "
            "최초 평가를 시작합니다."
        )

        # 기존 학습 모델 로드
        load_model()

        # DB 조회
        log("DB 평점 조회 시작")

        db_start = time.perf_counter()

        rows = repository.get_ratings()

        log(
            f"DB 조회 완료: {len(rows):,}건, "
            f"{time.perf_counter() - db_start:.2f}초"
        )

        if len(rows) < 2:
            raise ValueError(
                "평가할 평점 데이터가 부족합니다."
            )

        # 학습 당시와 동일한 분할 규칙
        log("검증 데이터 분할 시작")

        rng = np.random.default_rng(42)
        indices = rng.permutation(len(rows))

        valid_size = max(
            1,
            int(len(rows) * 0.2)
        )

        valid_rows = [
            rows[i]
            for i in indices[:valid_size]
        ]

        valid_rows = [
            r for r in valid_rows
            if r["user_id"] in _user_map
            and r["movie_id"] in _movie_map
        ]

        log(
            f"검증 데이터 분할 완료: "
            f"{len(valid_rows):,}건"
        )

        if not valid_rows:
            raise ValueError(
                "평가 가능한 검증 데이터가 없습니다."
            )

        # 텐서 변환
        log("검증 텐서 생성 시작")

        users = torch.tensor(
            [
                _user_map[r["user_id"]]
                for r in valid_rows
            ],
            dtype=torch.long
        )

        movies = torch.tensor(
            [
                _movie_map[r["movie_id"]]
                for r in valid_rows
            ],
            dtype=torch.long
        )

        ratings = torch.tensor(
            [
                float(r["rating"])
                for r in valid_rows
            ],
            dtype=torch.float32
        )

        valid_loader = DataLoader(
            TensorDataset(
                users,
                movies,
                ratings
            ),
            batch_size=4096,
            shuffle=False,
            num_workers=0
        )

        log(
            f"검증 텐서 생성 완료: "
            f"{len(valid_loader):,}개 배치"
        )

        # 배치 단위 평가
        kpi = evaluate_model(
            _model,
            valid_loader
        )

        # 기존 모델 가중치는 그대로 유지
        ckpt["kpi"] = kpi

        log("체크포인트 KPI 저장 시작")

        save_checkpoint(ckpt)

        log(
            f"KPI 저장 완료: {CHECKPOINT}"
        )

        log(
            f"KPI 처리 총 소요시간: "
            f"{time.perf_counter() - start:.2f}초"
        )

        return kpi


# =========================================================
# 7. 장르 한글 변환
# =========================================================

GENRE_KO = {
    "Action": "액션",
    "Adventure": "모험",
    "Animation": "애니메이션",
    "Children": "어린이",
    "Comedy": "코미디",
    "Crime": "범죄",
    "Documentary": "다큐멘터리",
    "Drama": "드라마",
    "Fantasy": "판타지",
    "Film-Noir": "공포",
    "Horror": "공포",
    "Musical": "뮤지컬",
    "Mystery": "미스터리",
    "Romance": "로맨스",
    "Sci-Fi": "SF",
    "Thriller": "스릴러",
    "War": "전쟁",
    "Western": "서부극",
    "IMAX": "아이맥스",
    "(no genres listed)": "장르 미상"
}


def translate_genres(genres):
    if not genres:
        return "장르 미상"

    return ", ".join(
        GENRE_KO.get(g.strip(), g.strip())
        for g in genres.split("|")
    )


# =========================================================
# 8. 영화 추천
# =========================================================

def recommend(user_id, top_n=5):
    load_model()

    if user_id not in _user_map:
        raise ValueError(
            "학습되지 않은 고객입니다."
        )

    candidates = repository.get_unwatched_movies(
        user_id
    )

    candidates = [
        movie
        for movie in candidates
        if movie["id"] in _movie_map
    ]

    if not candidates:
        return []

    user_idx = _user_map[user_id]

    user_tensor = torch.full(
        (len(candidates),),
        user_idx,
        dtype=torch.long,
        device=DEVICE
    )

    movie_tensor = torch.tensor(
        [
            _movie_map[movie["id"]]
            for movie in candidates
        ],
        dtype=torch.long,
        device=DEVICE
    )

    with torch.inference_mode():
        # 원본 예측값으로 정렬
        scores = (
            _model(user_tensor, movie_tensor)
            .cpu()
            .tolist()
        )

    ranked = sorted(
        zip(candidates, scores),
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    return [
        {
            "rank": rank,
            "movie_id": movie["id"],
            "title": movie["title"],
            "genres": translate_genres(
                movie["genres"]
            ),
            "predicted_rating": round(
                float(
                    max(
                        RATING_MIN,
                        min(RATING_MAX, score)
                    )
                ),
                3
            )
        }
        for rank, (movie, score)
        in enumerate(ranked, start=1)
    ]
