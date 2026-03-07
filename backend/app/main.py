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

trading_service = TradingService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> DÉMARRAGE DE L'APPLICATION AXIOM <<<")
    try:
        print(">>> DB DOCTOR: Exécution des migrations et initialisation...")
        migrate_db()
        print("Initialisation des tables via Base.metadata (Sécurité)...")
        init_db()
        print("Base de données initialisée avec succès.")
    except Exception as e:
        print(f"ERREUR CRITIQUE lors de init_db: {e}")
    
    # Lancement de la boucle autonome dans une tâche séparée
    try:
        print("Lancement de la boucle autonome Axiom...")
        asyncio.create_task(trading_agent.start_loop())
        print("Boucle autonome lancée en arrière-plan.")
    except Exception as e:
        print(f"ERREUR lors du lancement de la boucle: {e}")
    
    try:
        def run_multi_user_cycle(db):
            user_ids = trading_service.portfolio.repo.get_all_user_ids(db)
            for uid in user_ids:
                try:
                    trading_service.run_trading_cycle(db, uid)
                except Exception as e:
                    print(f"Erreur cycle pour {uid}: {e}")
                    
        start_scheduler(run_multi_user_cycle, SessionLocal)
        print("Scheduler démarré.")
    except Exception as e:
        print(f"ERREUR lors du démarrage du scheduler: {e}")

    yield
    print("Arrêt de l'application...")
    stop_scheduler()

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

app.include_router(portfolio_router.router)
app.include_router(signal_router.router)
app.include_router(news_router.router)
app.include_router(system_router.router)
app.include_router(chat_router.router)
app.include_router(market_router.router)
