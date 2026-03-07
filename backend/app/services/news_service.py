from app.domain.news.sentiment import analyze_sentiment
from app.repositories.news_repository import NewsRepository
from app.providers.news_provider import NewsProvider
from app.providers.twitter_provider import TwitterProvider
from app.config import MARKET_SYMBOLS, TWITTER_TARGETS, TWITTER_WEIGHTS

class NewsService:
    def __init__(self):
        self.repo = NewsRepository()
        self.provider = NewsProvider()
        self.twitter_provider = TwitterProvider()

    def fetch_and_analyze_news(self, db):
        articles = self.provider.fetch_rss_news()
        analyzed = []
        for a in articles:
            if not self.repo.news_exists(db, a['url']):
                score = analyze_sentiment(a['title'] + " " + a['summary'])
                symbol = self.provider.detect_symbol(a['title'] + " " + a['summary'], MARKET_SYMBOLS)
                
                news_item = self.repo.save_news(
                    db, a['title'], a['source'], a['url'], 
                    None, # published_at pourrait être parsé ici
                    score, symbol
                )
                analyzed.append(news_item)
        return analyzed

    async def fetch_twitter_news(self, db):
        """Récupère les tweets des cibles et les analyse."""
        all_tweets = []
        for target in TWITTER_TARGETS:
            tweets = await self.twitter_provider.scrape_tweets(target, limit=3)
            weight = TWITTER_WEIGHTS.get(target, 1.0)
            
            for t in tweets:
                if not self.repo.news_exists(db, t['url'] + t['content'][:20]): # Twitter URL n'est pas unique par tweet ici
                    # Analyse sentiment
                    score = analyze_sentiment(t['content'])
                    symbol = self.provider.detect_symbol(t['content'], MARKET_SYMBOLS)
                    
                    # Denoising & Trigger Priority
                    content_lower = t['content'].lower()
                    
                    # Bonus d'importance si mots-clés 2026 ou peur/euphorie détectés
                    trigger_bonus: float = 1.0
                    from app.config import MARKET_TRIGGERS
                    for category, keywords in MARKET_TRIGGERS.items():
                        if any(k.lower() in content_lower for k in keywords):
                            trigger_bonus += 0.5
                            print(f"TRIGGER DÉTECTÉ: {category} dans '{t['content'][:30]}...' (+0.5 weight)")
                    
                    if len(t['content']) < 15: continue # Trop court pour être pertinent
                    
                    news_item = self.repo.save_news(
                        db, 
                        title=t['content'][:100] + "...", 
                        source=t['source'], 
                        url=t['url'] + t['content'][:20], 
                        published_at=None,
                        sentiment_score=score, 
                        related_symbol=symbol,
                        source_type="TWITTER",
                        importance_weight=weight * trigger_bonus,
                        raw_content=t['content']
                    )
                    all_tweets.append(news_item)
        return all_tweets

    def get_recent_news(self, db, limit=20):
        return self.repo.get_recent_news(db, limit)

    def get_sentiment_for_symbol(self, db, symbol):
        news = self.repo.get_news_by_symbol(db, symbol)
        # Filtrer les scores None pour éviter les erreurs de calcul
        valid_scores = [n.sentiment_score for n in news if n.sentiment_score is not None]
        if not valid_scores: return 0.0
        return sum(valid_scores) / len(valid_scores)
