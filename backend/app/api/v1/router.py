from fastapi import APIRouter
from app.api.v1.endpoints import (
    players,
    observations,
    opportunities,
    trades,
    bankroll,
    goals,
    actions,
    dev,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(players.router)
api_router.include_router(observations.router)
api_router.include_router(opportunities.router)
api_router.include_router(trades.router)
api_router.include_router(bankroll.router)
api_router.include_router(goals.router)
api_router.include_router(actions.router)
api_router.include_router(dev.router)
