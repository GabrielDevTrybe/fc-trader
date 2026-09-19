from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import (
    Trade,
    BankrollHistory,
    TradingGoal,
    ActionRecommendation,
    ActionFeedback,
    PriceObservation,
    MarketOpportunity,
    Player,
)

router = APIRouter(prefix="/dev", tags=["Development / Testing"])


@router.post("/cleanup-test-data")
def cleanup_test_data(db: Session = Depends(get_db)):
    """Remove estritamente dados marcados com data_origin == 'test'.

    Proibido em produção. Nunca remove registros com data_origin == 'user' (sejam REAL ou PAPER).
    """
    if settings.APP_ENV == "production" or not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Operação de limpeza restrita ao ambiente de desenvolvimento com DEBUG habilitado.",
        )

    deleted_counts = {}

    # Deleta apenas registros expressamente com data_origin == 'test'
    deleted_counts["feedbacks"] = db.query(ActionFeedback).filter(ActionFeedback.data_origin == "test").delete()
    deleted_counts["recommendations"] = db.query(ActionRecommendation).filter(ActionRecommendation.data_origin == "test").delete()
    deleted_counts["trades"] = db.query(Trade).filter(Trade.data_origin == "test").delete()
    deleted_counts["bankroll_history"] = db.query(BankrollHistory).filter(BankrollHistory.data_origin == "test").delete()
    deleted_counts["goals"] = db.query(TradingGoal).filter(TradingGoal.data_origin == "test").delete()
    deleted_counts["opportunities"] = db.query(MarketOpportunity).filter(MarketOpportunity.data_origin == "test").delete()
    deleted_counts["observations"] = db.query(PriceObservation).filter(PriceObservation.data_origin == "test").delete()
    deleted_counts["players"] = db.query(Player).filter(Player.data_origin == "test").delete()

    db.commit()

    return {
        "status": "success",
        "message": "Dados marcados estritamente como 'test' foram removidos com sucesso.",
        "deleted_records": deleted_counts,
    }
