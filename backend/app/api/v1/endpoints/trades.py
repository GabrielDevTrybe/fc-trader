from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.entities import Trade
from app.schemas.schemas import TradeCreate, TradeClose, TradeRead
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.post("", response_model=TradeRead)
def open_trade(
    payload: TradeCreate,
    db: Session = Depends(get_db),
):
    """Abre uma nova operação de compra (suporta is_paper_trade=true)."""
    service = TradeService(db=db)
    trade = service.open_trade(payload)
    return (
        db.query(Trade)
        .options(joinedload(Trade.card), joinedload(Trade.player))
        .filter(Trade.id == trade.id)
        .first()
    )


@router.post("/{trade_id}/close", response_model=TradeRead)
def close_trade(
    trade_id: UUID,
    payload: TradeClose,
    db: Session = Depends(get_db),
):
    """Encerra uma operação de venda, calculando taxa de 5%, valor líquido recebido, lucro e ROI."""
    service = TradeService(db=db)
    try:
        trade = service.close_trade(trade_id, payload)
        return (
            db.query(Trade)
            .options(joinedload(Trade.card), joinedload(Trade.player))
            .filter(Trade.id == trade.id)
            .first()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[TradeRead])
def list_trades(
    is_paper: bool | None = Query(None, description="Filtro por paper trade"),
    status: str | None = Query(None, description="Filtro por status: open, sold, cancelled"),
    goal_id: UUID | None = Query(None, description="Filtro por trading_goal_id"),
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista histórico de trades abertos e concluídos."""
    query = (
        db.query(Trade)
        .options(joinedload(Trade.card), joinedload(Trade.player))
        .filter(Trade.data_origin == data_origin)
    )
    if is_paper is not None:
        query = query.filter(Trade.is_paper_trade == is_paper)
    if status is not None:
        query = query.filter(Trade.status == status)
    if goal_id is not None:
        query = query.filter(Trade.trading_goal_id == goal_id)

    return query.order_by(Trade.bought_at.desc()).limit(limit).all()
