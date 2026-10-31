import torch
from torch import nn


class MFModel(nn.Module):
    def __init__(self, num_users, num_movies, dim=30):
        super().__init__()

        self.user_embedding = nn.Embedding(num_users, dim)
        self.movie_embedding = nn.Embedding(num_movies, dim)

        self.user_bias = nn.Embedding(num_users, 1)
        self.movie_bias = nn.Embedding(num_movies, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        nn.init.normal_(self.user_embedding.weight, std=0.05)
        nn.init.normal_(self.movie_embedding.weight, std=0.05)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.movie_bias.weight)

    def forward(self, user_ids, movie_ids):
        user_vec = self.user_embedding(user_ids)
        movie_vec = self.movie_embedding(movie_ids)

        dot = (user_vec * movie_vec).sum(dim=1)

        return (
            dot
            + self.user_bias(user_ids).squeeze(-1)
            + self.movie_bias(movie_ids).squeeze(-1)
            + self.global_bias
        )