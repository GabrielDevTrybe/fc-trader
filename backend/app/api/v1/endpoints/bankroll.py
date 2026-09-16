from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import BankrollSummary
from app.services.bankroll_service import BankrollService

router = APIRouter(prefix="/bankroll", tags=["Bankroll"])


@router.get("", response_model=BankrollSummary)
def get_bankroll(
    is_paper: bool = Query(False, description="Consultar métricas de Paper Trading ou banca real"),
    db: Session = Depends(get_db),
):
    """Retorna saldo atual da banca, lucros de hoje/total, win rate, ROI médio e progresso nas metas."""
    service = BankrollService(db=db)
    return service.get_summary(is_paper=is_paper)
