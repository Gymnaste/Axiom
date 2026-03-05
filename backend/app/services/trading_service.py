from app.providers.market_provider import MarketProvider
from app.domain.market.indicators import compute_all_indicators
from app.services.portfolio_service import PortfolioService
from app.services.news_service import NewsService
from app.services.openai_service import OpenAIService
from app.core.logger import setup_logger

logger = setup_logger("trading_service")

class TradingService:
    _discovered_symbols = [] # Cache de classe pour persistance simple
    _cached_signals = {} # Structure : { "user_id": [ { signal1 }, { signal2 } ] }

    def __init__(self):
        self.market = MarketProvider()
        self.portfolio = PortfolioService()
        self.news = NewsService()
        self.openai = OpenAIService()

    def generate_signals_for_all(self, db, user_id, symbols_list):
        signals = []
        portfolio_summary = self.portfolio.get_portfolio_summary(db, user_id)
        
        # Formater le contexte du portefeuille en texte simple pour l'IA
        context = f"Capital liquide: {portfolio_summary['capital']}$, Valeur totale: {portfolio_summary['valeur_totale']}$. "
        context += f"Positions ouvertes: {len(portfolio_summary['positions_ouvertes'])} (maximum autorisé généralement 5)."

        for s in symbols_list:
            df = self.market.get_historical_data(s)
            if df is None or df.empty:
                logger.warning(f"[{s}] Données historiques introuvables. Symbole ignoré.")
                continue
                
            ind = compute_all_indicators(df)
            if not ind or "current_price" not in ind:
                logger.warning(f"[{s}] Indicateurs insuffisants. Symbole ignoré.")
                continue
                
            sent = self.news.get_sentiment_for_symbol(db, s)
            
            # Demande à ChatGPT d'analyser ce marché précis
            ai_decision = self.openai.analyze_market_signal(s, ind, sent, context)
            
            rec = ai_decision.get("recommendation", "HOLD")
            logger.info(f"[{s}] Décision IA : {rec} (Confiance: {ai_decision.get('confidence', 0.5)})")
            
            # On inclut tous les signaux (même HOLD) pour montrer à l'utilisateur que l'IA travaille
            signals.append({
                "symbol": s,
                "recommendation": rec,
                "probability_up": ai_decision.get("confidence", 0.5),
                "confidence_score": ai_decision.get("confidence", 0.5),
                "score_technique": 0.5, # Valeur ignorée par le nouveau layout si on s'appuie sur la justification IA
                "score_sentiment": sent,
                "justification": ai_decision.get("justification", "Pas de justification fournie."),
                "take_profit": ai_decision.get("take_profit"),
                "stop_loss": ai_decision.get("stop_loss"),
                "current_price": ind.get("current_price"),
                "rsi": ind.get("rsi"), "sma20": ind.get("sma20"), "sma50": ind.get("sma50")
            })
            
        # Mise en cache des signaux générés
        if user_id:
            TradingService._cached_signals[user_id] = signals
            
        return signals

    def get_user_signals(self, user_id):
        """Retourne les signaux mis en cache pour éviter de spammer OpenAI."""
        return TradingService._cached_signals.get(user_id, [])

    def run_trading_cycle(self, db, user_id: str = None):
        if not user_id:
            logger.warning("run_trading_cycle appelé sans user_id. Annulation.")
            return {"success": False, "error": "user_id required"}
            
        # 1. Scraping des news
        self.news.fetch_and_analyze_news(db)
        
        # 1.5. Découverte d'opportunités via OpenAI
        from app.config import MARKET_SYMBOLS
        recent_news = self.news.get_recent_news(db, limit=20)
        news_summary = " ".join([n.title for n in recent_news])if recent_news else ""
        
        logger.info(f"Découverte d'opportunités à partir de {len(recent_news)} articles...")
        dynamic_symbols = self.openai.discover_opportunities(news_summary) if news_summary else []
        TradingService._discovered_symbols = dynamic_symbols # On mémorise les trouvailles
        logger.info(f"Symboles générés par l'IA : {dynamic_symbols}")
        
        # Combiner les symboles fixes et les trouvailles de l'IA (en enlevant les doublons)
        all_symbols = list(set(MARKET_SYMBOLS + dynamic_symbols))
        logger.info(f"Analyse de {len(all_symbols)} symboles au total : {all_symbols}")
        
        # 2. Génération des signaux (filtrés BUY/SELL uniquement)
        signals = self.generate_signals_for_all(db, user_id, all_symbols)
        
        # 3. Exécution des trades basés sur les signaux
        for sig in signals:
            if sig['recommendation'] == 'BUY':
                # On vérifie si on n'a pas déjà une position ouverte pour ce symbole
                summary = self.portfolio.get_portfolio_summary(db, user_id)
                already_open = any(pos['symbol'] == sig['symbol'] for pos in summary['positions_ouvertes'])
                
                if not already_open:
                    self.portfolio.open_position(
                        db, user_id, sig['symbol'], sig['current_price'], 
                        sl=sig.get('stop_loss'), tp=sig.get('take_profit'),
                        justification=sig.get('justification')
                    )
        
        # 4. Enregistrement d'un point d'historique pour le graphique
        final_summary = self.portfolio.get_portfolio_summary(db, user_id)
        self.portfolio.repo.add_history_point(
            db, user_id,
            total_value=final_summary['valeur_totale'], 
            capital_liquide=final_summary['capital']
        )
        
        return {"success": True, "signals_generated": len(signals)}
