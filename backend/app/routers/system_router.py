from fastapi import APIRouter, Depends
from app.config import APP_NAME, APP_VERSION
from app.core.auth_deps import get_current_user_id
from app.services.trading_agent import trading_agent
import asyncio
import logging

logger = logging.getLogger("system_router")
router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health")
def health():
    return {"status": "healthy", "app": APP_NAME, "version": APP_VERSION}

@router.post("/trigger-cycle")
async def trigger_cycle(user_id: str = Depends(get_current_user_id)):
    """Lance manuellement un cycle complet d'analyse."""
    logger.info(f"TRIGGER: Manuel par {user_id}")
    asyncio.create_task(trading_agent.run_cycle())
    return {"success": True, "message": "Cycle d'analyse lancé en arrière-plan."}

@router.post("/force-restart-agent")
async def force_restart_agent(user_id: str = Depends(get_current_user_id)):
    """Arrête et relance l'agent autonome."""
    logger.info(f"RESTART: Agent forcé par {user_id}")
    trading_agent.running = False
    await asyncio.sleep(2)
    asyncio.create_task(trading_agent.start_loop())
    return {"success": True, "message": "Agent redémarré avec succès."}
