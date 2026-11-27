from fastapi import APIRouter, Depends, Query

from app.api.deps import get_db, require_admin
from app.services.pipeline_metrics_service import (
    PipelineMetricsService,
)


router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)


@router.get("/pipeline")
def pipeline_metrics(
    window_days: int = Query(default=7, ge=1, le=90),
    _=Depends(require_admin),
    db=Depends(get_db),
):
    return PipelineMetricsService(db).collect(
        window_days=window_days,
    )
