from fastapi import APIRouter, HTTPException, Query

from app.svd import service
from app.svd.schema import (
    KPISchema,
    RecommendationResponse,
)


router = APIRouter(prefix="/svd", tags=["SVD"])


@router.get("/kpi", response_model=KPISchema)
def get_kpi():
    try:
        return service.get_kpi()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )


@router.get(
    "/recommendations",
    response_model=RecommendationResponse,
)
def get_recommendations(
    user_id: int = Query(..., ge=1),
):
    try:
        return service.get_recommendations(user_id)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )