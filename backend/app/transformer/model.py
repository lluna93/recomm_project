import torch
from torch import nn


class TransformerModel(nn.Module):
    def __init__(
        self,
        num_movies,
        dim=30,
        max_len=30,
        nhead=3,
        num_layers=2,
    ):
        super().__init__()

        self.max_len = max_len

        # 0은 padding
        self.movie_embedding = nn.Embedding(
            num_movies + 1, dim, padding_idx=0
        )

        self.rating_embedding = nn.Linear(1, dim)

        self.position_embedding = nn.Embedding(
            max_len, dim
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=dim,
            nhead=nhead,
            dim_feedforward=120,
            dropout=0.1,
            batch_first=True,
            norm_first=True,
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            enable_nested_tensor=False,
        )

        # 과거 이력 + 후보 영화 → 평점
        self.predictor = nn.Sequential(
            nn.Linear(dim * 2, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(
        self,
        history_movies,
        history_ratings,
        target_movies,
    ):
        batch_size, seq_len = history_movies.shape
        device = history_movies.device

        positions = torch.arange(
            seq_len, device=device
        ).unsqueeze(0)

        mask = history_movies.eq(0)

        x = (
            self.movie_embedding(history_movies)
            + self.rating_embedding(
                history_ratings.unsqueeze(-1)
            )
            + self.position_embedding(positions)
        )

        # padding이 표현에 영향을 주지 않도록 처리
        x = x.masked_fill(mask.unsqueeze(-1), 0.0)

        encoded = self.encoder(
            x,
            src_key_padding_mask=mask,
        )

        # 유효한 이력만 평균 풀링
        valid = (~mask).unsqueeze(-1)
        pooled = (encoded * valid).sum(dim=1)
        pooled = pooled / valid.sum(dim=1).clamp(min=1)

        target_vec = self.movie_embedding(target_movies)

        combined = torch.cat(
            [pooled, target_vec], dim=1
        )

        return self.predictor(combined).squeeze(-1)