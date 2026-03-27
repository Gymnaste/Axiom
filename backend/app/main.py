from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, SessionLocal
from app.core.scheduler import start_scheduler, stop_scheduler
from app.services.trading_service import TradingService
from app.routers import portfolio_router, signal_router, news_router, system_router, chat_router, market_router

from app.services.trading_agent import trading_agent
from app.migrate_db import migrate_db
import asyncio
import logging

logger = logging.getLogger(__name__)

trading_service = TradingService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(">>> DÉMARRAGE DE L'APPLICATION AXIOM (LIFESPAN) <<<")
    try:
        logger.info(">>> DB DOCTOR: Exécution des migrations et initialisation...")
        migrate_db()
        init_db()
        logger.info("Base de données initialisée avec succès.")
    except Exception as e:
        logger.error(f"ERREUR CRITIQUE lors de init_db: {e}")
    
    # Lancement de la boucle autonome dans une tâche séparée
    try:
        logger.info("Lancement de la boucle autonome Axiom...")
        # On stocke la tâche dans un état persistant pour éviter la garbage collection
        app.state.autonomous_agent_task = asyncio.create_task(trading_agent.start_loop())
        logger.info("Boucle autonome lancée en arrière-plan avec succès.")
    except Exception as e:
        logger.error(f"ERREUR lors du lancement de la boucle: {e}")
    
    # NOTE: L'ancien scheduler est désactivé au profit de l'AutonomousTradingAgent
    # qui est plus complet et gère les rapports de cycle automatiques.
    
    yield
    logger.info("Arrêt de l'application...")
    if hasattr(app.state, "autonomous_agent_task"):
        app.state.autonomous_agent_task.cancel()

import os
app = FastAPI(title="Trading Bot", lifespan=lifespan)
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "*"
]
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root_welcome():
    return {"message": "Axiom API is running", "status": "online"}

app.include_router(portfolio_router.router)
app.include_router(signal_router.router)
app.include_router(news_router.router)
app.include_router(system_router.router)
app.include_router(chat_router.router)
app.include_router(market_router.router)
