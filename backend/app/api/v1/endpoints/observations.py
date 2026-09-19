from typing import Any
from uuid import UUID
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import MarketSnapshot
from app.schemas.schemas import (
    ObservationBatchItem,
    ObservationBatchResponse,
    CsvBatchUploadRequest,
    MarketSnapshotRead,
)
from app.services.observation_service import ObservationService

router = APIRouter(prefix="/observations", tags=["Observations"])


@router.post("", response_model=ObservationBatchResponse)
def record_observations(
    payload: Any = Body(
        ...,
        description="Pode ser um único objeto de observação ou uma lista em lote (batch).",
        examples=[
            [
                {"player": "Exemplo Jogador", "rating": 84, "price": 1200, "type": "bid", "club": "Exemplo FC", "position": "CM"},
            ]
        ],
    ),
    db: Session = Depends(get_db),
):
    """Ingestão rápida de observações de preços manuais ou em lote por CardVersion."""
    items: list[ObservationBatchItem] = []
    if isinstance(payload, list):
        items = [ObservationBatchItem.model_validate(item) for item in payload]
    elif isinstance(payload, dict):
        items = [ObservationBatchItem.model_validate(payload)]
    else:
        raise ValueError("Payload deve ser um objeto ou lista de objetos de observação")

    service = ObservationService(db=db)
    return service.process_batch(items)


@router.post("/batch/csv", response_model=ObservationBatchResponse)
def record_observations_csv(
    payload: CsvBatchUploadRequest,
    db: Session = Depends(get_db),
):
    """Ingestão em lote de observações via texto CSV com cabeçalho."""
    service = ObservationService(db=db)
    return service.process_csv_batch(payload.csv_content, data_origin=payload.data_origin)


@router.get("/snapshots/{card_id}", response_model=list[MarketSnapshotRead])
def get_card_snapshots(
    card_id: UUID,
    platform: str = Query("console"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Histórico de snapshots quantitativos auditáveis computados para a carta."""
    return (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.card_id == card_id, MarketSnapshot.platform == platform)
        .order_by(MarketSnapshot.calculated_at.desc())
        .limit(limit)
        .all()
    )
