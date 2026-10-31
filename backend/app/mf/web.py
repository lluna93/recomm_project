from fastapi import APIRouter, HTTPException

from . import service
from .schema import KPIResponse, Recommendation


router = APIRouter(prefix="/mf", tags=["MF"])


@router.get("/kpi", response_model=KPIResponse)
def kpi():
    try:
        return service.get_kpi()
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/recommendations",
    response_model=list[Recommendation]
)
def recommendations(user_id: int):
    try:
        return service.recommend(user_id, top_n=5)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))