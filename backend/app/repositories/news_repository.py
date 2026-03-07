from datetime import datetime
from sqlalchemy.orm import Session
from app.database import NewsItem
from app.core.logger import setup_logger

logger = setup_logger("news_repository")

class NewsRepository:
    def save_news(self, db: Session, title: str, source: str, url: str, published_at: datetime, sentiment_score: float, related_symbol: str, source_type: str = "RSS", importance_weight: float = 1.0, raw_content: str = None):
        news = NewsItem(
            title=title, 
            source=source, 
            url=url, 
            published_at=published_at, 
            sentiment_score=sentiment_score, 
            related_symbol=related_symbol,
            source_type=source_type,
            importance_weight=importance_weight,
            raw_content=raw_content
        )
        db.add(news)
        db.commit()
        db.refresh(news)
        return news

    def get_recent_news(self, db: Session, limit: int = 20):
        return db.query(NewsItem).order_by(NewsItem.created_at.desc()).limit(limit).all()

    def news_exists(self, db: Session, url: str):
        return db.query(NewsItem).filter(NewsItem.url == url).first() is not None

    def get_news_by_symbol(self, db: Session, symbol: str, limit: int = 10):
        return db.query(NewsItem).filter(NewsItem.related_symbol == symbol).order_by(NewsItem.created_at.desc()).limit(limit).all()
