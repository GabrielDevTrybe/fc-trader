from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.entities import MarketOpportunity, Player
from app.schemas.schemas import MarketOpportunityRead

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


@router.get("", response_model=list[MarketOpportunityRead])
def list_opportunities(
    player: str | None = Query(None, description="Filtro por nome do jogador"),
    min_rating: int | None = Query(None, ge=40, le=99),
    min_profit: int | None = Query(None, ge=0),
    min_roi: float | None = Query(None, ge=0.0),
    min_liquidity: int | None = Query(None, ge=0, le=100),
    confidence: str | None = Query(None, description="LOW, MEDIUM, HIGH"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista oportunidades de mercado vivas, ordenadas por Opportunity Score decrescente."""
    now = datetime.now(timezone.utc)
    query = (
        db.query(MarketOpportunity)
        .join(Player)
        .options(joinedload(MarketOpportunity.player))
        .filter(
            (MarketOpportunity.expires_at.is_(None)) | (MarketOpportunity.expires_at > now)
        )
    )

    if player:
        query = query.filter(Player.name.ilike(f"%{player}%"))
    if min_rating is not None:
        query = query.filter(Player.rating >= min_rating)
    if min_profit is not None:
        query = query.filter(MarketOpportunity.estimated_profit >= min_profit)
    if min_roi is not None:
        query = query.filter(MarketOpportunity.roi >= min_roi)
    if min_liquidity is not None:
        query = query.filter(MarketOpportunity.liquidity_score >= min_liquidity)
    if confidence:
        query = query.filter(MarketOpportunity.confidence == confidence.upper())

    return query.order_by(MarketOpportunity.opportunity_score.desc()).limit(limit).all()
