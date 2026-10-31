from pydantic import BaseModel


class KPIResponse(BaseModel):
    mae: float
    mse: float
    rmse: float


class Recommendation(BaseModel):
    rank: int
    movie_id: int
    title: str
    genres: str
    predicted_rating: float