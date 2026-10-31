from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix


@dataclass
class SVDModel:
    user_ids: np.ndarray
    movie_ids: np.ndarray

    user_factors: np.ndarray
    item_factors: np.ndarray
    user_means: np.ndarray
    global_mean: float

    seen_matrix: csr_matrix

    mae: float
    mse: float
    rmse: float