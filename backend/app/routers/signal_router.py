from fastapi import APIRouter, Depends
from app.database import get_db
from app.services.trading_service import TradingService
from app.core.auth_deps import get_current_user_id

router = APIRouter(tags=["Trading"])
service = TradingService()

@router.get("/signals")
def get_signals(db=Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return {"signals": service.get_user_signals(user_id)}

@router.post("/run-cycle")
def run_cycle(db=Depends(get_db), user_id: str = Depends(get_current_user_id)):
    # Cycle is now user-specific for this manual trigger
    return service.run_trading_cycle(db, user_id)
