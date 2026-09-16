from typing import Any
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import (
    ObservationBatchItem,
    ObservationBatchResponse,
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
                {"player": "Palhinha", "rating": 82, "price": 600, "type": "bid"},
                {"player": "Savinho", "rating": 80, "price": 650, "type": "buy_now"},
            ]
        ],
    ),
    db: Session = Depends(get_db),
):
    """Ingestão rápida de observações de preços manuais ou em lote.

    Processa o pipeline em poucos milissegundos:
    1. Validação dos dados
    2. Identificação/Criação do jogador
    3. Registro da observação
    4. Atualização estatística de mercado (MarketPriceEngine)
    5. Avaliação do TradingEngine
    6. Cálculo do OpportunityScore
    7. Atualização de oportunidade no banco
    8. Retorno imediato da análise
    """
    items: list[ObservationBatchItem] = []
    if isinstance(payload, list):
        items = [ObservationBatchItem.model_validate(item) for item in payload]
    elif isinstance(payload, dict):
        items = [ObservationBatchItem.model_validate(payload)]
    else:
        raise ValueError("Payload deve ser um objeto ou lista de objetos de observação")

    service = ObservationService(db=db)
    return service.process_batch(items)
