import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Trade, Portfolio, ActivityLog, NewsItem
from app.providers.market_provider import MarketProvider
from app.services.openai_service import OpenAIService
from app.core.logger import setup_logger

logger = setup_logger("trading_agent")

class AutonomousTradingAgent:
    def __init__(self):
        self.market_provider = MarketProvider()
        self.openai_service = OpenAIService()
        self.tickers_to_watch = ["AAPL", "TSLA", "MSFT", "NVDA", "BTC-USD", "GC=F", "CL=F"]
        self.running = False

    async def start_loop(self):
        """Lance la boucle autonome."""
        if self.running:
            return
        self.running = True
        logger.info("Axiom Autonomous Agent démarré.")
        
        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Erreur dans le cycle autonome : {e}")
            
            # Attendre 30 minutes
            logger.info("Cycle terminé. Prochain scan dans 30 minutes.")
            await asyncio.sleep(1800)

    async def run_cycle(self):
        """Un cycle complet d'analyse et de trading."""
        db = SessionLocal()
        try:
            # On boucle sur tous les portefeuilles existants
            all_portfolios = db.query(Portfolio).all()
            if not all_portfolios:
                logger.warning("Aucun utilisateur/portefeuille trouvé pour le trading autonome.")
                return

            for user_portfolio in all_portfolios:
                logger.info(f"--- Nouveau cycle d'analyse pour {user_portfolio.user_id} (Capital: ${user_portfolio.capital:.2f}) ---")

                # 1. Étendre la liste des tickers via la découverte IA (basée sur les news globales)
                try:
                    # On récupère les news globales pour la découverte
                    global_news_items = db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(15).all()
                    news_summary = "\n".join([f"- {n.title}" for n in global_news_items])
                    discovered = self.openai_service.discover_opportunities(news_summary)
                    
                    # Fusionner avec les tickers de base (en évitant les doublons)
                    active_tickers = list(set(self.tickers_to_watch + discovered))
                    logger.info(f"Tickers à analyser pour {user_portfolio.user_id} : {active_tickers}")
                except Exception as e:
                    logger.error(f"Erreur lors de la découverte pour {user_portfolio.user_id} : {e}")
                    active_tickers = self.tickers_to_watch

                for ticker_symbol in active_tickers:
                    # 2. Vérifier si on a déjà une position ouverte pour ce ticker
                    existing_trade = db.query(Trade).filter(
                        Trade.user_id == user_portfolio.user_id,
                        Trade.symbol == ticker_symbol,
                        Trade.status == "OPEN"
                    ).first()
                    if existing_trade:
                        continue

                    # 3. Récupérer données techniques et news
                    history = self.market_provider.get_stock_history(ticker_symbol, period="5d")
                    news = self.market_provider.get_ticker_news(ticker_symbol)
                    
                    if not history:
                        continue

                    # 4. Demander à l'IA
                    decision = self.openai_service.get_autonomous_decision(
                        ticker_symbol, history, news, user_portfolio.capital
                    )

                    action = decision.get("action", "HOLD")
                    reasoning = decision.get("reasoning", "")

                    if action == "BUY":
                        amount_pct = decision.get("amount_pct", 0.02)
                        amount_to_invest = user_portfolio.capital * amount_pct
                        
                        # Vérification sécurité (max 5%)
                        amount_to_invest = min(amount_to_invest, user_portfolio.capital * 0.05)
                        
                        price = self.market_provider.get_current_price(ticker_symbol)
                        if price and amount_to_invest > 10: # Minimum $10
                            qty = amount_to_invest / price
                            
                            # Créer le trade
                            new_trade = Trade(
                                user_id=user_portfolio.user_id,
                                symbol=ticker_symbol,
                                quantity=qty,
                                entry_price=price,
                                stop_loss=decision.get("stop_loss"),
                                take_profit=decision.get("take_profit"),
                                justification=reasoning,
                                ai_reasoning=reasoning,
                                status="OPEN"
                            )
                            
                            # Mettre à jour le balance
                            user_portfolio.capital -= amount_to_invest
                            
                            db.add(new_trade)
                            db.commit()

                            # Logger l'activité (BUY uniquement dans le dashboard)
                            msg = f"Axiom a acheté {ticker_symbol} (${amount_to_invest:.2f}) : {reasoning}"
                            self.log_activity(db, user_portfolio.user_id, msg, "BUY")
                            logger.info(f"[AUTONOMOUS] ACHAT de {ticker_symbol} pour {user_portfolio.user_id} : {reasoning}")

                    elif action == "SELL":
                        logger.info(f"[AUTONOMOUS] Signal de VENTE pour {ticker_symbol} mais pas de position à fermer pour {user_portfolio.user_id}.")
                    
                    else: # HOLD
                        logger.info(f"[AUTONOMOUS] Scan {ticker_symbol} ({user_portfolio.user_id}) : Aucun signal fort (HOLD).")

        finally:
            db.close()

    def log_activity(self, db: Session, user_id: str, message: str, type: str):
        log = ActivityLog(user_id=user_id, message=message, type=type)
        db.add(log)
        db.commit()

# Instance globale
trading_agent = AutonomousTradingAgent()
