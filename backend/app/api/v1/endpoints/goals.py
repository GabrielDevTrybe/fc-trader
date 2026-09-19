from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import TradingGoalCreate, TradingGoalRead
from app.services.goal_service import GoalService
from app.services.bankroll_service import BankrollService

router = APIRouter(prefix="/goals", tags=["Trading Goals"])


@router.post("", response_model=TradingGoalRead)
def create_goal(
    payload: TradingGoalCreate,
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    db: Session = Depends(get_db),
):
    """Cria uma nova meta de trading. Rejeita se já existir meta ACTIVE na mesma modalidade."""
    goal_service = GoalService(db)
    bankroll_service = BankrollService(db)
    cap = bankroll_service.get_capital_summary(is_paper=payload.is_paper, data_origin=data_origin)
    if not payload.is_paper and not cap.is_configured:
        raise HTTPException(
            status_code=400,
            detail="A banca real deve ser configurada via onboarding antes de criar uma meta separadamente.",
        )
    try:
        goal = goal_service.create_goal(payload, current_total_equity=cap.total_equity, data_origin=data_origin)
        return goal_service.get_goal_read(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active", response_model=TradingGoalRead | None)
def get_active_goal(
    is_paper: bool = Query(False, description="Consultar modalidade Paper ou Real"),
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    db: Session = Depends(get_db),
):
    """Retorna a meta de trading atualmente ativa, com métricas consolidadas."""
    goal_service = GoalService(db)
    goal = goal_service.get_active_goal(is_paper=is_paper, data_origin=data_origin)
    if not goal:
        return None
    return goal_service.get_goal_read(goal)


@router.get("", response_model=list[TradingGoalRead])
def list_goals(
    is_paper: bool | None = Query(None, description="Filtro opcional por modalidade"),
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    db: Session = Depends(get_db),
):
    """Lista histórico completo de metas (ativas, concluídas e encerradas)."""
    goal_service = GoalService(db)
    return goal_service.list_goals(is_paper=is_paper, data_origin=data_origin)


@router.post("/{goal_id}/complete", response_model=TradingGoalRead)
def complete_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
):
    """Marca a meta ativa como concluída."""
    goal_service = GoalService(db)
    try:
        goal = goal_service.complete_goal(goal_id)
        return goal_service.get_goal_read(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{goal_id}/close", response_model=TradingGoalRead)
def close_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
):
    """Encerra manualmente a meta ativa antes de atingir o alvo, preservando todo o histórico."""
    goal_service = GoalService(db)
    try:
        goal = goal_service.close_goal(goal_id)
        return goal_service.get_goal_read(goal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
