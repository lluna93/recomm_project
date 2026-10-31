from fastapi import APIRouter, HTTPException, Query

from . import service
from .schema import KPIResponse, Recommendation


router = APIRouter(
    prefix="/transformer",
    tags=["Transformer"],
)


@router.get("/kpi", response_model=KPIResponse)
def get_kpi():
    try:
        return service.get_kpi()
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/recommendations",
    response_model=list[Recommendation],
)
def get_recommendations(
    user_id: int = Query(...),
):
    try:
        return service.recommend(user_id, top_n=5)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )