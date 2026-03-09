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
        """Lance la boucle autonome avec résilience accrue."""
        if self.running:
            return
        self.running = True
        logger.info("Axiom Autonomous Agent démarré.")
        
        # Délai initial de sécurité pour laisser le serveur et la DB se stabiliser
        await asyncio.sleep(30)
        
        while self.running:
            try:
                # Heartbeat dans la DB pour prouver que l'agent est vivant
                db = SessionLocal()
                try:
                    self.log_activity(db, "system", "Axiom Heartbeat: Agent en ligne et prêt pour un cycle.", "INFO")
                finally:
                    db.close()

                await self.run_cycle()
                
            except Exception as e:
                logger.error(f"Erreur dans le cycle autonome : {e}")
            except BaseException as e:
                # Capture les erreurs fatales pour éviter que la boucle ne meure sans log
                logger.critical(f"ERREUR FATALE (BaseException) dans le loop : {e}")
                self.running = False # On arrête proprement si c'est vraiment critique
                raise e
            
            # Attendre 30 minutes
            logger.info("Cycle terminé. Prochain scan dans 30 minutes.")
            await asyncio.sleep(1800)

    async def run_cycle(self):
        """Un cycle complet d'analyse et de trading."""
        from app.services.news_service import NewsService
        news_service = NewsService()
        
        db = SessionLocal()
        try:
            # 0. Récupérer les dernières news (RSS + Twitter)
            logger.info(">>> ÉTAPE 0: Mise à jour des flux d'actualités (RSS + Twitter)...")
            try:
                news_service.fetch_and_analyze_news(db)
                # Timeout de 60s pour éviter les blocages infinis lors du scraping
                await asyncio.wait_for(news_service.fetch_twitter_news(db), timeout=60.0)
                logger.info("Flux d'actualités mis à jour avec succès.")
            except asyncio.TimeoutError:
                logger.warning("Timeout lors du scraping Twitter. Passage à la suite.")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des news : {e}")
                db.rollback() # CRITIQUE: Évite d'empoisonner la session pour la suite

            # On boucle sur tous les portefeuilles existants
            all_portfolios = db.query(Portfolio).all()
            if not all_portfolios:
                logger.warning("Aucun utilisateur/portefeuille trouvé pour le trading autonome.")
                return

            for user_portfolio in all_portfolios:
                logger.info(f"--- Nouveau cycle d'analyse pour {user_portfolio.user_id} (Capital: ${user_portfolio.capital:.2f}) ---")
                cycle_results = []

                # 1. Étendre la liste des tickers via la découverte IA (basée sur les news globales)
                logger.info(f">>> ÉTAPE 1: Découverte d'opportunités pour {user_portfolio.user_id}...")
                try:
                    # On récupère les news globales pour la découverte
                    global_news_items = db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(15).all()
                    news_summary = "\n".join([f"- {n.title}" for n in global_news_items])
                    discovered = self.openai_service.discover_opportunities(news_summary)
                    
                    # Fusionner avec les tickers de base (en évitant les doublons)
                    active_tickers = list(set(self.tickers_to_watch + discovered))
                    logger.info(f"Tickers à analyser : {active_tickers}")
                except Exception as e:
                    logger.error(f"Erreur lors de la découverte : {e}")
                    active_tickers = self.tickers_to_watch

                for ticker_symbol in active_tickers:
                    # 2. Vérifier si on a déjà une position ouverte pour ce ticker
                    existing_trade = db.query(Trade).filter(
                        Trade.user_id == user_portfolio.user_id,
                        Trade.symbol == ticker_symbol,
                        Trade.status == "OPEN"
                    ).first()
                    
                    price = self.market_provider.get_current_price(ticker_symbol)
                    if not price:
                        continue

                    # 3. Vérification SL/TP si position ouverte
                    if existing_trade:
                        closed_reason = None
                        if existing_trade.take_profit and price >= existing_trade.take_profit:
                            closed_reason = "Take Profit atteint"
                        elif existing_trade.stop_loss and price <= existing_trade.stop_loss:
                            closed_reason = "Stop Loss atteint"
                            
                        if closed_reason:
                            # Fermer la position (logique simplifiée répliquant portfolio_service.close_position)
                            existing_trade.status = "CLOSED"
                            existing_trade.exit_price = price
                            existing_trade.exit_date = datetime.utcnow()
                            trade_pnl = (price - existing_trade.entry_price) * existing_trade.quantity
                            existing_trade.pnl = trade_pnl
                            proceeds = price * existing_trade.quantity
                            user_portfolio.capital += proceeds
                            db.commit()
                            
                            msg = f"Axiom a fermé {ticker_symbol} au prix de ${price:.2f} ({closed_reason})"
                            self.log_activity(db, user_portfolio.user_id, msg, "SELL")
                            logger.info(f"[AUTONOMOUS] VENTE (Auto-close) de {ticker_symbol} pour {user_portfolio.user_id} : {closed_reason}")
                            continue # Passer au ticker suivant
                            
                    # 4. Récupérer données techniques et news pour l'IA
                    df = self.market_provider.get_historical_data(ticker_symbol, period="1mo")
                    if df.empty:
                        continue
                    
                    indicators = compute_all_indicators(df)
                    history = self.market_provider.get_stock_history(ticker_symbol, period="5d")
                    news = self.market_provider.get_ticker_news(ticker_symbol)

                    # 5. Récupérer l'historique de performance pour l'apprentissage
                    from app.repositories.portfolio_repository import TradeRepository
                    trade_repo = TradeRepository()
                    closed_trades = trade_repo.get_closed_trades(db, user_portfolio.user_id, limit=10)
                    perf_history = ""
                    for ct in closed_trades:
                        status_str = "PROFIT" if (ct.pnl or 0) > 0 else "PERTE"
                        perf_history += f"- {ct.symbol}: {status_str} (${ct.pnl:.2f}), Jusitification: {ct.justification}\n"

                    # 6. Demander à l'IA
                    logger.info(f">>> ÉTAPE 6: Consultation IA pour {ticker_symbol}...")
                    try:
                        decision = self.openai_service.get_autonomous_decision(
                            ticker_symbol, history, news, user_portfolio.capital, performance_history=perf_history
                        )
                    except Exception as e:
                        logger.error(f"Erreur lors de la consultation OpenAI pour {ticker_symbol}: {e}")
                        continue
                    
                    cycle_results.append({
                        "symbol": ticker_symbol,
                        "action": decision.get("action"),
                        "reasoning": decision.get("reasoning")
                    })

                    action = decision.get("action", "HOLD")
                    reasoning = decision.get("reasoning", "")

                    if action == "BUY":
                        if existing_trade:
                            logger.info(f"[AUTONOMOUS] Signal d'ACHAT ignoré car position déjà ouverte pour {ticker_symbol} ({user_portfolio.user_id}).")
                            continue
                            
                        amount_pct = decision.get("amount_pct", 0.02)
                        amount_to_invest = user_portfolio.capital * amount_pct
                        
                        # Vérification sécurité (max 5%)
                        amount_to_invest = min(amount_to_invest, user_portfolio.capital * 0.05)
                        
                        if amount_to_invest > 10: # Minimum $10
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

                            # Logger l'activité
                            msg = f"Axiom a acheté {ticker_symbol} (${amount_to_invest:.2f}) : {reasoning}"
                            self.log_activity(db, user_portfolio.user_id, msg, "BUY")
                            logger.info(f"[AUTONOMOUS] ACHAT de {ticker_symbol} pour {user_portfolio.user_id} : {reasoning}")

                    elif action == "SELL":
                        if existing_trade:
                            # L'IA a décidé de vendre la position ouverte
                            existing_trade.status = "CLOSED"
                            existing_trade.exit_price = price
                            existing_trade.exit_date = datetime.utcnow()
                            proceeds = price * existing_trade.quantity
                            user_portfolio.capital += proceeds
                            db.commit()
                            
                            msg = f"Axiom a vendu {ticker_symbol} sur décision de l'IA (${proceeds:.2f}) : {reasoning}"
                            self.log_activity(db, user_portfolio.user_id, msg, "SELL")
                            logger.info(f"[AUTONOMOUS] VENTE (Décision IA) de {ticker_symbol} pour {user_portfolio.user_id} : {reasoning}")
                        else:
                            logger.info(f"[AUTONOMOUS] Signal de VENTE ignoré car aucune position ouverte pour {ticker_symbol} ({user_portfolio.user_id}).")
                    
                    else: # HOLD
                        logger.info(f"[AUTONOMOUS] Scan {ticker_symbol} ({user_portfolio.user_id}) : Aucun signal fort (HOLD).")

                # 7. Générer et sauvegarder le compte-rendu pour le chatbot
                if cycle_results:
                    logger.info(f">>> ÉTAPE 7: Génération du rapport de cycle pour {user_portfolio.user_id}...")
                    try:
                        report_text = self.openai_service.get_cycle_report_summary(cycle_results)
                        if report_text:
                            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                            new_msg = ChatMessage(
                                user_id=user_portfolio.user_id,
                                role="assistant",
                                content=f"🤖 **Rapport de cycle autonome ({now_str})** :\n{report_text}"
                            )
                            db.add(new_msg)
                            db.commit()
                            
                            # On loggue aussi dans l'ActivityLog qu'un rapport est dispo
                            self.log_activity(db, user_portfolio.user_id, f"Nouveau rapport d'analyse disponible dans le chatbot ({now_str}).", "INFO")
                            
                            logger.info(f"Rapport de cycle envoyé au chatbot pour {user_portfolio.user_id}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la publication du rapport : {e}")
                        db.rollback()

        finally:
            db.close()

    def log_activity(self, db: Session, user_id: str, message: str, type: str):
        log = ActivityLog(user_id=user_id, message=message, type=type)
        db.add(log)
        db.commit()

# Instance globale
trading_agent = AutonomousTradingAgent()
