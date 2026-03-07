"""
config.py — Configuration centralisée du Trading Bach Bot V1
Toutes les variables de configuration sont ici. Ne jamais hardcoder ailleurs.
"""
import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")

# Capital & Trading
CAPITAL_INITIAL: float = 10000.0
MAX_POSITION_SIZE: float = 0.20       # Max 20% du capital par position
STOP_LOSS: float = 0.05               # -5% stop loss automatique
TAKE_PROFIT: float = 0.10             # +10% take profit

# Symboles suivis
MARKET_SYMBOLS: list[str] = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]

# Cycle automatique
# Fréquence d'analyse (en minutes) — Réduite pour économiser l'API OpenAI
SCHEDULER_INTERVAL_MINUTES: int = 60
  # Analyse toutes les 10 min
MARKET_DATA_PERIOD: str = "6mo"       # Période historique yfinance

# Algorithme de scoring IA
SCORE_TECHNIQUE_WEIGHT: float = 0.6
SCORE_SENTIMENT_WEIGHT: float = 0.4
BUY_THRESHOLD: float = 0.7
SELL_THRESHOLD: float = 0.3

# RSI
RSI_OVERBOUGHT: float = 70.0
RSI_OVERSOLD: float = 30.0

# News & Sentiment
NEWS_RSS_FEEDS: list[str] = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://www.investing.com/rss/news.rss",
]

# Application
APP_NAME: str = "Axiom"
APP_VERSION: str = "1.0.0"
# Twitter Configuration
TWITTER_TARGETS: list[str] = ["elonmusk", "federalreserve", "unusual_whales", "WuBlockchain", "WatcherGuru"]
TWITTER_WEIGHTS: dict[str, float] = {
    "elonmusk": 2.5,
    "federalreserve": 3.0,
    "unusual_whales": 1.5,
    "WuBlockchain": 1.2,
    "WatcherGuru": 1.1
}

DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
