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
    "https://news.google.com/rss/search?q=stock+market+finance&hl=en-US&gl=US&ceid=US:en",
    "https://www.investing.com/rss/news.rss",
]

# Application
APP_NAME: str = "Axiom"
APP_VERSION: str = "1.0.0"
# Twitter Configuration (Vitesse & Influence)
TWITTER_TARGETS: list[str] = [
    # 1. Vitesse Pure (News & Breaking)
    "WatcherGuru", "whale_alert", "business", "ReutersBiz", "unusual_whales",
    # 2. Market Movers (Insiders)
    "elonmusk", "saylor", "VitalikButerin", "balajis",
    # 3. Analystes & Stratèges
    "charliebilello", "intocryptoverse", "scottmelker",
    # 4. Surveillance Macro-Economique
    "ecb", "federalreserve", "Lagarde"
]

TWITTER_WEIGHTS: dict[str, float] = {
    # News (Priorité rapidité)
    "WatcherGuru": 2.0, "whale_alert": 2.2, "unusual_whales": 2.0,
    # Insiders (Priorité impact)
    "elonmusk": 3.0, "saylor": 2.5, "VitalikButerin": 2.5, "balajis": 2.0,
    # Macro (Priorité structurelle)
    "federalreserve": 3.5, "ecb": 3.0, "Lagarde": 3.0,
    # Analystes (Poids standard)
    "charliebilello": 1.5, "intocryptoverse": 1.2, "scottmelker": 1.2
}

# 2026 Trends & Triggers (Mots-clés pour l'IA)
MARKET_TRIGGERS: dict[str, list[str]] = {
    "PEUR": ["crash", "dump", "sell", "inflation spike", "Fed rate hike", "recession", "scare trade"],
    "EUPHORIE": ["moon", "bullish", "buy the dip", "Fed rate cut", "ETF approval", "mass adoption"],
    "TRENDS_2026": ["Agentic Finance", "Global Liquidity Index", "Stablecoin Payment Layer", "RWA", "DeFi"]
}

DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
