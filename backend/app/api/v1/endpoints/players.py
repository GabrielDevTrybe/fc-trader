from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Player
from app.schemas.schemas import PlayerRead

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("", response_model=list[PlayerRead])
def list_players(
    query: str | None = Query(None, description="Busca por nome de jogador"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Player)
    if query:
        q = q.filter(Player.name.ilike(f"%{query}%"))
    return q.order_by(Player.rating.desc(), Player.name.asc()).limit(limit).all()
