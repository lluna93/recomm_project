from pydantic import BaseModel, Field


class KPISchema(BaseModel):
    mae: float
    mse: float
    rmse: float


class RecommendationSchema(BaseModel):
    rank: int
    movie_id: int
    title: str
    genres: str
    predicted_rating: float = Field(ge=1.0, le=5.0)


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: list[RecommendationSchema]