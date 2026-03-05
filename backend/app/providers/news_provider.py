import feedparser
from datetime import datetime
from app.core.logger import setup_logger

logger = setup_logger("news_provider")

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app.core.logger import setup_logger

logger = setup_logger("news_provider")

RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://www.investing.com/rss/news.rss",
    "https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=stock%20market",
]

class NewsProvider:
    def fetch_rss_news(self, max_articles: int = 50):
        articles = []
        for url in RSS_FEEDS:
            try:
                logger.info(f"Fetching news from {url}")
                # Plus robuste : on utilise requests avec un User-Agent pour éviter d'être bloqué
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    for entry in feed.entries[:max_articles]:
                        articles.append({
                            "title": entry.get("title", ""),
                            "source": feed.feed.get("title", "Finance News"),
                            "url": entry.get("link", ""),
                            "summary": entry.get("description" if "description" in entry else "summary", ""),
                            "published_at": entry.get("published", datetime.utcnow().isoformat())
                        })
                else:
                    logger.error(f"HTTP Error {response.status_code} on {url}")
            except Exception as e:
                logger.error(f"Error fetching RSS {url}: {e}")
                continue
        logger.info(f"Total articles fetched: {len(articles)}")
        return articles

    def detect_symbol(self, text, symbols):
        if not text: return None
        t = text.upper()
        # On cherche le premier symbole qui apparaît dans le titre ou le résumé
        for s in symbols:
            if f" {s} " in f" {t} " or t.startswith(s) or t.endswith(s):
                return s
        return None
