from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import CurrentActionResponse, ActionFeedbackCreate
from app.services.action_service import ActionService

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.get("/current", response_model=CurrentActionResponse)
def get_current_action(
    is_paper: bool = Query(False, description="Modalidade Paper ou Real"),
    data_origin: str = Query("user", description="Isolamento de origem: 'user' ou 'test'"),
    db: Session = Depends(get_db),
):
    """Retorna a melhor ação quantitativa do momento ('FAÇA ISSO AGORA') ou status NO_ACTION."""
    service = ActionService(db)
    return service.get_current_action(is_paper=is_paper, data_origin=data_origin)


@router.post("/feedback")
def submit_action_feedback(
    payload: ActionFeedbackCreate,
    data_origin: str = Query("user", description="Isolamento de origem"),
    db: Session = Depends(get_db),
):
    """Registra feedback da recomendação:

    - Se BOUGHT: cria os trades correspondentes para cada compra com seu preço real exato.
    - Se MISSED: registra o motivo e invalida a recomendação para gerar nova oportunidade.
    """
    service = ActionService(db)
    try:
        feedback = service.record_feedback(payload, data_origin=data_origin)
        return {
            "status": "success",
            "feedback_id": feedback.id,
            "action_result": feedback.action_result,
            "quantity_bought": feedback.quantity_bought,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
