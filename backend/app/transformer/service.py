from collections import defaultdict
from pathlib import Path
from threading import Lock
import math
import os
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from . import repository
from .model import TransformerModel


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available()
    else "cpu"
)

DIM = 30
MAX_LEN = 15
MIN_RATING = 0.5
MAX_RATING = 5.0

CHECKPOINT = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "transformer.pt"
)

_model = None
_movie_map = None
_kpi_lock = Lock()


def log(message):
    print(f"[Transformer] {message}", flush=True)


def read_checkpoint():
    if not CHECKPOINT.exists():
        raise FileNotFoundError(f"Transformer 체크포인트가 없습니다: {CHECKPOINT}")
    return torch.load(CHECKPOINT, map_location="cpu", weights_only=True)


def save_checkpoint(ckpt):
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    temp_path = CHECKPOINT.with_suffix(".pt.tmp")
    try:
        torch.save(ckpt, temp_path)
        os.replace(temp_path, CHECKPOINT)
    finally:
        if temp_path.exists():
            temp_path.unlink()


# --------------------------------------------------
# 2. 고객별 시간순 학습/검증 분할
# --------------------------------------------------

def split_histories(rows):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["user_id"]].append(row)

    train_histories = {}
    valid_histories = {}

    for user_id, history in grouped.items():
        n = len(history)

        if n < 3:
            continue

        valid_count = max(1, math.ceil(n * 0.1))
        split_idx = n - valid_count

        if split_idx < 2:
            continue

        # movie_id 순서 기준 분할
        train_histories[user_id] = history[:split_idx]
        valid_histories[user_id] = history[split_idx:]

    return train_histories, valid_histories
# --------------------------------------------------
# 3. 학습 샘플 생성
# --------------------------------------------------

def build_samples(
    train_histories,
    valid_histories,
    movie_map,
):
    train_samples = []
    valid_samples = []

    def make_sample(history, target):
        # 모델에 학습된 영화만 사용
        if target["movie_id"] not in movie_map:
            return None

        history = history[-MAX_LEN:]

        if not history:
            return None

        movie_ids = [
            movie_map[r["movie_id"]]
            for r in history
            if r["movie_id"] in movie_map
        ]

        ratings = [
            float(r["rating"])
            for r in history
            if r["movie_id"] in movie_map
        ]

        if not movie_ids:
            return None

        # 오른쪽 padding
        pad = MAX_LEN - len(movie_ids)

        movie_ids += [0] * pad
        ratings += [0.0] * pad

        return (
            movie_ids,
            ratings,
            movie_map[target["movie_id"]],
            float(target["rating"]),
        )

    for user_id, train_history in train_histories.items():

        # 학습: 과거 영화들 → 바로 다음 영화 평점
        for i in range(1, len(train_history)):
            sample = make_sample(
                train_history[:i],
                train_history[i],
            )

            if sample:
                train_samples.append(sample)

        # 검증: 학습 구간의 이력만 입력
        # 검증 구간 평점은 입력하지 않음
        for target in valid_histories[user_id]:
            sample = make_sample(
                train_history,
                target,
            )

            if sample:
                valid_samples.append(sample)

    return train_samples, valid_samples


# --------------------------------------------------
# 4. Dataset
# --------------------------------------------------

class RatingDataset(Dataset):
    def __init__(self, samples):
        movies, ratings, targets, scores = zip(*samples)

        # Tensor를 최초 한 번만 생성
        self.movies = torch.tensor(
            np.asarray(movies), dtype=torch.long
        )
        self.ratings = torch.tensor(
            np.asarray(ratings), dtype=torch.float32
        )
        self.targets = torch.tensor(
            targets, dtype=torch.long
        )
        self.scores = torch.tensor(
            scores, dtype=torch.float32
        )

    def __len__(self):
        return len(self.scores)

    def __getitem__(self, idx):
        return (
            self.movies[idx],
            self.ratings[idx],
            self.targets[idx],
            self.scores[idx],
        )

# --------------------------------------------------
# 5. 검증 오차
# --------------------------------------------------

def evaluate(model, loader):
    model.eval()

    abs_sum = 0.0
    sq_sum = 0.0
    count = 0

    total_batches = len(loader)
    started = time.perf_counter()
    log(f"평가 시작: {total_batches:,}개 배치, device={DEVICE}")

    with torch.inference_mode():
        for batch_no, (hm, hr, target, actual) in enumerate(loader, start=1):
            hm = hm.to(DEVICE)
            hr = hr.to(DEVICE)
            target = target.to(DEVICE)

            pred = model(hm, hr, target)
            pred = pred.clamp(MIN_RATING, MAX_RATING)

            # CPU로 이동한 뒤 float64 연산
            error = (
                pred.cpu().to(torch.float64)
                - actual.to(torch.float64)
            )

            abs_sum += error.abs().sum().item()
            sq_sum += error.square().sum().item()
            count += error.numel()

            if batch_no == 1 or batch_no % 20 == 0 or batch_no == total_batches:
                log(
                    f"평가 진행: {batch_no:,}/{total_batches:,} 배치, "
                    f"{count:,}건, {time.perf_counter() - started:.2f}초"
                )

    if count == 0:
        raise ValueError("검증 가능한 평점이 없습니다.")

    return {
        "mae": abs_sum / count,
        "mse": sq_sum / count,
        "rmse": math.sqrt(sq_sum / count),
    }


# --------------------------------------------------
# 6. 모델 학습
# --------------------------------------------------

def train(
    epochs=20,
    batch_size=512,
    lr=0.001,
):
    global _model, _movie_map

    torch.manual_seed(42)
    np.random.seed(42)

    rows = repository.get_ratings()

    train_histories, valid_histories = split_histories(rows)

    # 검증 영화의 ID는 후보로 사용할 수 있지만,
    # 검증 평점은 학습에 사용하지 않음
    movie_ids = sorted({
        row["movie_id"]
        for row in rows
    })

    movie_map = {
        movie_id: idx + 1
        for idx, movie_id in enumerate(movie_ids)
    }

    train_samples, valid_samples = build_samples(
        train_histories,
        valid_histories,
        movie_map,
    )

    if not train_samples or not valid_samples:
        raise ValueError("학습 또는 검증 데이터가 부족합니다.")
    train_loader = DataLoader(
        RatingDataset(train_samples),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=(DEVICE.type == "cuda"),
        num_workers=0,
    )

    valid_loader = DataLoader(
        RatingDataset(valid_samples),
        batch_size=1024,
        shuffle=False,
        pin_memory=(DEVICE.type == "cuda"),
        num_workers=0,
    )

    model = TransformerModel(
        num_movies=len(movie_map),
        dim=DIM,
        max_len=MAX_LEN,
    ).to(DEVICE)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=1e-5,
    )

    criterion = nn.MSELoss()

    print(f"DEVICE: {DEVICE}")
    print(f"TRAIN: {len(train_samples):,}")
    print(f"VALID: {len(valid_samples):,}")

    for epoch in range(epochs):
        model.train()

        total_loss = torch.zeros((), device=DEVICE)
        total_count = 0

        for hm, hr, target, actual in train_loader:
            hm = hm.to(DEVICE, non_blocking=True)
            hr = hr.to(DEVICE, non_blocking=True)
            target = target.to(DEVICE, non_blocking=True)
            actual = actual.to(DEVICE, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)

            pred = model(hm, hr, target)
            loss = criterion(pred, actual)

            loss.backward()
            optimizer.step()

            total_loss += loss.detach() * actual.size(0)
            total_count += actual.size(0)

        train_loss = total_loss.cpu().item() / total_count

        # 검증은 5 Epoch마다 수행
        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            kpi = evaluate(model, valid_loader)
            valid_text = f"Valid_RMSE={kpi['rmse']:.6f}"
        else:
            valid_text = "Valid_RMSE=SKIP"

        print(
            f"Epoch {epoch + 1}/{epochs} "
            f"Loss={train_loss:.6f} "
            f"{valid_text}",
            flush=True,
        )
    # 모델, 추론에 필요한 매핑 및 검증 KPI를 함께 저장
    CHECKPOINT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    torch.save({
        "state_dict": {
            k: v.detach().cpu()
            for k, v in model.state_dict().items()
        },
        "movie_ids": movie_ids,
        "dim": DIM,
        "max_len": MAX_LEN,
        "kpi": kpi,
    }, CHECKPOINT)

    _model = model
    _movie_map = movie_map

    return kpi


# --------------------------------------------------
# 7. 체크포인트 로드
# --------------------------------------------------

def load_model():
    global _model, _movie_map

    if _model is not None:
        return

    ckpt = read_checkpoint()

    _movie_map = {
        movie_id: idx + 1
        for idx, movie_id in enumerate(ckpt["movie_ids"])
    }

    _model = TransformerModel(
        num_movies=len(_movie_map),
        dim=ckpt["dim"],
        max_len=ckpt["max_len"],
    ).to(DEVICE)

    _model.load_state_dict(ckpt["state_dict"])
    _model.eval()


# --------------------------------------------------
# 8. KPI 조회 (재학습 없음)
# --------------------------------------------------

def get_kpi():
    """저장된 KPI를 즉시 반환하고, 없으면 기존 모델로 한 번만 평가한다."""
    with _kpi_lock:
        log("KPI 요청 수신")
        ckpt = read_checkpoint()

        if ckpt.get("kpi") is not None:
            log("저장된 KPI 즉시 반환")
            return ckpt["kpi"]

        started = time.perf_counter()
        log("체크포인트에 KPI가 없어 최초 평가를 시작합니다.")

        load_model()
        log("DB 평점 조회 시작")
        db_started = time.perf_counter()
        rows = repository.get_ratings()
        log(f"DB 조회 완료: {len(rows):,}건, {time.perf_counter() - db_started:.2f}초")

        log("검증 이력 및 샘플 구성 시작")
        train_histories, valid_histories = split_histories(rows)
        _, valid_samples = build_samples(
            train_histories,
            valid_histories,
            _movie_map,
        )
        log(f"검증 샘플 생성 완료: {len(valid_samples):,}건")

        if not valid_samples:
            raise ValueError("평가 가능한 Transformer 검증 데이터가 없습니다.")

        loader = DataLoader(
            RatingDataset(valid_samples),
            batch_size=512,
            shuffle=False,
            pin_memory=(DEVICE.type == "cuda"),
            num_workers=0,
        )

        kpi = evaluate(_model, loader)

        # 기존 가중치와 매핑을 그대로 보존하고 KPI만 추가한다.
        ckpt["kpi"] = kpi
        log("체크포인트 KPI 저장 시작")
        save_checkpoint(ckpt)
        log(f"KPI 저장 완료: {CHECKPOINT}")
        log(f"총 소요시간: {time.perf_counter() - started:.2f}초")
        return kpi


# --------------------------------------------------
# 9. 장르 한글 변환
# --------------------------------------------------

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
    "Film-Noir": "필름 누아르",
    "Horror": "공포",
    "Musical": "뮤지컬",
    "Mystery": "미스터리",
    "Romance": "로맨스",
    "Sci-Fi": "SF",
    "Thriller": "스릴러",
    "War": "전쟁",
    "Western": "서부극",
    "IMAX": "아이맥스",
    "(no genres listed)": "장르 미상",
}


def translate_genres(genres):
    if not genres:
        return "장르 미상"

    return ", ".join(
        GENRE_KO.get(g.strip(), g.strip())
        for g in genres.split("|")
    )


# --------------------------------------------------
# 10. 안 본 영화 TOP 5 추천
# --------------------------------------------------

def recommend(user_id, top_n=5):
    load_model()

    history = repository.get_user_history(user_id)

    if not history:
        raise ValueError("평점 이력이 없는 고객입니다.")

    candidates = repository.get_unwatched_movies(user_id)

    candidates = [
        movie for movie in candidates
        if movie["id"] in _movie_map
    ]

    if not candidates:
        return []

    recent = [
        row for row in history
        if row["movie_id"] in _movie_map
    ][-MAX_LEN:]

    if not recent:
        raise ValueError("모델이 인식하는 시청 이력이 없습니다.")

    hm = [_movie_map[r["movie_id"]] for r in recent]
    hr = [float(r["rating"]) for r in recent]

    pad = MAX_LEN - len(hm)

    hm += [0] * pad
    hr += [0.0] * pad

    results = []

    _model.eval()

    with torch.inference_mode():
        for start in range(0, len(candidates), 512):
            batch = candidates[start:start + 512]
            size = len(batch)

            history_movies = torch.tensor(
                [hm] * size,
                dtype=torch.long,
                device=DEVICE,
            )

            history_ratings = torch.tensor(
                [hr] * size,
                dtype=torch.float32,
                device=DEVICE,
            )

            target_movies = torch.tensor(
                [_movie_map[m["id"]] for m in batch],
                dtype=torch.long,
                device=DEVICE,
            )

            scores = _model(
                history_movies,
                history_ratings,
                target_movies,
            )

            for movie, score in zip(
                batch, scores.cpu().tolist()
            ):
                results.append((movie, float(score)))

    ranked = sorted(
        results,
        key=lambda x: (-x[1], x[0]["id"]),
    )[:top_n]

    return [
        {
            "rank": rank,
            "movie_id": movie["id"],
            "title": movie["title"],
            "genres": translate_genres(movie["genres"]),
            "predicted_rating": round(
                float(max(MIN_RATING, min(MAX_RATING, score))), 3
            ),
        }
        for rank, (movie, score)
        in enumerate(ranked, start=1)
    ]