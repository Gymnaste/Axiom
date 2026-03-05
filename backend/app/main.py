from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, SessionLocal
from app.core.scheduler import start_scheduler, stop_scheduler
from app.services.trading_service import TradingService
from app.routers import portfolio_router, signal_router, news_router, system_router, chat_router, market_router

from app.services.trading_agent import trading_agent
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    # Lancement de la boucle autonome dans une tâche séparée
    asyncio.create_task(trading_agent.start_loop())
    
    def run_multi_user_cycle(db):
        user_ids = trading_service.portfolio.repo.get_all_user_ids(db)
        for uid in user_ids:
            try:
                trading_service.run_trading_cycle(db, uid)
            except Exception as e:
                print(f"Erreur cycle pour {uid}: {e}")
                
    start_scheduler(run_multi_user_cycle, SessionLocal)
    yield
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
