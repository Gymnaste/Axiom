import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Trade, Portfolio, ActivityLog, NewsItem, ChatMessage
from app.providers.market_provider import MarketProvider
from app.domain.market.indicators import compute_all_indicators
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
        """Lance la boucle autonome avec résilience accrue (Watchdog)."""
        if self.running:
            return
        self.running = True
        logger.info(">>> AXIOM AUTONOMOUS AGENT STARTED <<<")
        
        await asyncio.sleep(10) # Safe boot delay
        
        while self.running:
            try:
                # Cycle de l'agent
                await self.run_cycle()
                
                logger.info("Cycle autonome terminé. Prochain scan dans 30 minutes.")
                await asyncio.sleep(1800)
                
            except asyncio.CancelledError:
                logger.info("Agent autonome arrêté (Tâche annulée).")
                self.running = False
                break
            except Exception as e:
                logger.error(f"ERREUR INATTENDUE dans le loop : {str(e)}")
                # Watchdog : on attend 2 minutes et on recommence
                await asyncio.sleep(120)
            except BaseException as e:
                logger.critical(f"EXCEPTION CRITIQUE (BaseException) : {str(e)}")
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    self.running = False
                    raise e
                await asyncio.sleep(120)

    async def run_cycle(self):
        """Un cycle complet d'analyse et de trading."""
        from app.services.news_service import NewsService
        news_service = NewsService()
        
        db = SessionLocal()
        try:
            # Heartbeat système visible
            self.log_activity(db, "system", "Axiom Heartbeat: Début d'un cycle d'analyse autonome.", "INFO")
            
            # 0. Récupérer les dernières news (RSS + Twitter) avec des timeouts stricts
            logger.info(">>> ÉTAPE 0: Mise à jour des flux d'actualités...")
            try:
                # 0a. RSS (Sync mais rapide)
                news_service.fetch_and_analyze_news(db)
                
                # 0b. Twitter (Async Playwright) — Timeout global strict de 120s
                try:
                    await asyncio.wait_for(news_service.fetch_twitter_news(db), timeout=120.0)
                except asyncio.TimeoutError:
                    logger.warning("Timeout GLOBAL lors du scraping Twitter (120s).")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des news : {e}")
                db.rollback()

            # On boucle sur tous les portefeuilles existants
            all_portfolios = db.query(Portfolio).all()
            if not all_portfolios:
                logger.warning("Aucun portefeuille trouvé pour le trading autonome.")
                return

            for user_portfolio in all_portfolios:
                try:
                    await self.process_user_portfolio(db, user_portfolio)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du portfolio {user_portfolio.user_id}: {e}")
                    db.rollback()

        finally:
            db.close()

    async def process_user_portfolio(self, db: Session, user_portfolio: Portfolio):
        """Traite un utilisateur spécifique."""
        logger.info(f"--- Cycle d'analyse pour {user_portfolio.user_id} ---")
        cycle_results = []
        
        # 1. Découverte d'opportunités (IA)
        try:
            global_news_items = db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(15).all()
            news_summary = "\n".join([f"- {n.title}" for n in global_news_items])
            
            # IA Discovery avec timeout
            discovered = await asyncio.wait_for(
                asyncio.to_thread(self.openai_service.discover_opportunities, news_summary),
                timeout=30.0
            )
            active_tickers = list(set(self.tickers_to_watch + discovered))
        except Exception as e:
            logger.error(f"Erreur lors de la découverte : {e}")
            active_tickers = self.tickers_to_watch

        # On limite le nombre de tickers par cycle pour la performance
        for ticker_symbol in active_tickers[:15]:
            # 2. Vérifier position
            existing_trade = db.query(Trade).filter(
                Trade.user_id == user_portfolio.user_id,
                Trade.symbol == ticker_symbol,
                Trade.status == "OPEN"
            ).first()
            
            price = self.market_provider.get_current_price(ticker_symbol)
            if not price: continue

            # 3. Vérification SL/TP
            if existing_trade:
                closed_reason = None
                if existing_trade.take_profit and price >= existing_trade.take_profit:
                    closed_reason = "Take Profit atteint"
                elif existing_trade.stop_loss and price <= existing_trade.stop_loss:
                    closed_reason = "Stop Loss atteint"
                    
                if closed_reason:
                    existing_trade.status = "CLOSED"
                    existing_trade.exit_price = price
                    existing_trade.exit_date = datetime.utcnow()
                    trade_pnl = (price - existing_trade.entry_price) * existing_trade.quantity
                    existing_trade.pnl = trade_pnl
                    user_portfolio.capital += (price * existing_trade.quantity)
                    db.commit()
                    self.log_activity(db, user_portfolio.user_id, f"Axiom a fermé {ticker_symbol} au prix de ${price:.2f} ({closed_reason})", "SELL")
                    continue

            # 4. Consultation IA avec timeout
            try:
                # Collecter contexte technique
                df = self.market_provider.get_historical_data(ticker_symbol, period="1mo")
                if df.empty: continue
                
                # Collecter historique perf
                from app.repositories.portfolio_repository import TradeRepository
                trade_repo = TradeRepository()
                closed_trades = trade_repo.get_closed_trades(db, user_portfolio.user_id, limit=5)
                perf_history = "".join([f"- {ct.symbol}: {'PROFIT' if (ct.pnl or 0) > 0 else 'PERTE'}\n" for ct in closed_trades])

                # IA Decision avec timeout
                decision = await asyncio.wait_for(
                    asyncio.to_thread(self.openai_service.get_autonomous_decision, 
                        ticker_symbol, [], [], user_portfolio.capital, performance_history=perf_history
                    ),
                    timeout=40.0
                )
                
                action = decision.get("action", "HOLD")
                reasoning = decision.get("reasoning", "")

                if action in ["BUY", "SELL"]:
                    cycle_results.append({"symbol": ticker_symbol, "action": action, "reasoning": reasoning})

                if action == "BUY" and not existing_trade:
                    amount_to_invest = user_portfolio.capital * min(decision.get("amount_pct", 0.02), 0.05)
                    if amount_to_invest > 10:
                        qty = amount_to_invest / price
                        new_trade = Trade(
                            user_id=user_portfolio.user_id, symbol=ticker_symbol, quantity=qty,
                            entry_price=price, stop_loss=decision.get("stop_loss"),
                            take_profit=decision.get("take_profit"), justification=reasoning,
                            ai_reasoning=reasoning, status="OPEN"
                        )
                        user_portfolio.capital -= amount_to_invest
                        db.add(new_trade)
                        db.commit()
                        self.log_activity(db, user_portfolio.user_id, f"Axiom a acheté {ticker_symbol} (${amount_to_invest:.2f}) : {reasoning}", "BUY")

                elif action == "SELL" and existing_trade:
                    existing_trade.status = "CLOSED"
                    existing_trade.exit_price = price
                    existing_trade.exit_date = datetime.utcnow()
                    proceeds = price * existing_trade.quantity
                    user_portfolio.capital += proceeds
                    db.commit()
                    self.log_activity(db, user_portfolio.user_id, f"Axiom a vendu {ticker_symbol} sur décision de l'IA (${proceeds:.2f}) : {reasoning}", "SELL")

            except asyncio.TimeoutError:
                logger.warning(f"Timeout OpenAI pour {ticker_symbol}. Ignoré.")
            except Exception as e:
                logger.error(f"Erreur analyse {ticker_symbol}: {e}")

        # 7. Rapport final pour le chatbot (Toujours généré, même si vide)
        try:
            report_text = await asyncio.wait_for(
                asyncio.to_thread(self.openai_service.get_cycle_report_summary, cycle_results),
                timeout=40.0
            )
            if report_text:
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                new_msg = ChatMessage(
                    user_id=user_portfolio.user_id,
                    role="assistant",
                    content=f"🤖 **Rapport de cycle autonome ({now_str})** :\n{report_text}"
                )
                db.add(new_msg)
                db.commit()
                # On récupère l'ID du message pour le lier au log d'activité
                self.log_activity(db, user_portfolio.user_id, f"Nouveau rapport d'analyse disponible ({now_str}).", "INFO", reference_id=new_msg.id)
        except Exception as e:
            logger.error(f"Erreur publication rapport: {e}")

    def log_activity(self, db: Session, user_id: str, message: str, type: str, reference_id: int = None):
        try:
            log = ActivityLog(user_id=user_id, message=message, type=type, reference_id=reference_id)
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Erreur log_activity: {e}")
            db.rollback()

# Instance globale
trading_agent = AutonomousTradingAgent()
