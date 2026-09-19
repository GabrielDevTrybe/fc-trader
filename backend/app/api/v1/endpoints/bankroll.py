from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import (
    BankrollSummary,
    BankrollCapitalSummary,
    BankrollAdjustmentCreate,
    BankrollOnboardingCreate,
    BankrollSyncCreate,
)
from app.services.bankroll_service import BankrollService

router = APIRouter(prefix="/bankroll", tags=["Bankroll"])


@router.get("", response_model=BankrollSummary)
def get_bankroll(
    is_paper: bool = Query(False, description="Consultar métricas de Paper Trading ou banca real"),
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    db: Session = Depends(get_db),
):
    """Retorna saldo atual da banca, lucros de hoje/total, win rate, ROI médio e progresso nas metas."""
    service = BankrollService(db=db)
    return service.get_summary(is_paper=is_paper, data_origin=data_origin)


@router.get("/capital", response_model=BankrollCapitalSummary)
def get_capital_breakdown(
    is_paper: bool = Query(False, description="Consultar métricas patrimoniais de Paper Trading ou banca real"),
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    db: Session = Depends(get_db),
):
    """Retorna o detalhamento contábil exato: total_equity, cash_balance, available_cash, inventory_cost."""
    service = BankrollService(db=db)
    return service.get_capital_summary(is_paper=is_paper, data_origin=data_origin)


@router.post("/onboarding", response_model=BankrollCapitalSummary)
def onboard_real_bankroll(
    payload: BankrollOnboardingCreate,
    data_origin: str = Query("user", description="Isolamento de origem"),
    db: Session = Depends(get_db),
):
    """Configura o saldo inicial real e a meta inicial do usuário sem herdar dados de mock ou testes."""
    service = BankrollService(db=db)
    try:
        return service.onboard_bankroll(payload, data_origin=data_origin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync")
def sync_real_balance(
    payload: BankrollSyncCreate,
    data_origin: str = Query("user", description="Isolamento de origem"),
    db: Session = Depends(get_db),
):
    """Sincroniza o saldo real informado sem jamais transformar diferença de reconciliação em lucro de trading."""
    service = BankrollService(db=db)
    cap = service.get_capital_summary(is_paper=payload.is_paper, data_origin=data_origin)
    if not payload.is_paper and not cap.is_configured:
        raise HTTPException(
            status_code=400,
            detail="A banca real deve ser configurada via onboarding antes de sincronizar o saldo.",
        )
    try:
        entry = service.sync_balance(payload, data_origin=data_origin)
        return {
            "status": "success",
            "entry_id": entry.id,
            "new_balance": entry.balance,
            "reconciliation_delta": entry.amount,
            "reason": entry.reason,
            "is_paper": entry.is_paper,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/adjustments")
def record_adjustment(
    payload: BankrollAdjustmentCreate,
    data_origin: str = Query("user", description="Isolamento de origem"),
    db: Session = Depends(get_db),
):
    """Registra ajuste manual de moedas (recompensa do jogo ou compra externa) sem alterar lucro de trading."""
    service = BankrollService(db=db)
    cap = service.get_capital_summary(is_paper=payload.is_paper, data_origin=data_origin)
    if not payload.is_paper and not cap.is_configured:
        raise HTTPException(
            status_code=400,
            detail="A banca real deve ser configurada via onboarding antes de registrar ajustes.",
        )
    try:
        entry = service.record_adjustment(payload, data_origin=data_origin)
        return {
            "status": "success",
            "entry_id": entry.id,
            "amount": entry.amount,
            "new_balance": entry.balance,
            "entry_type": entry.entry_type,
            "adjustment_type": entry.adjustment_type,
            "reason": entry.reason,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
