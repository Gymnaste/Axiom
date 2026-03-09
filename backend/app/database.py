from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, Boolean, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import DATABASE_URL

# Engine et session (Fix pour Railway/Heroku postgres:// -> postgresql://)
parsed_url = DATABASE_URL
if parsed_url.startswith("postgres://"):
    parsed_url = parsed_url.replace("postgres://", "postgresql://", 1)

# Configuration de l'Engine adaptée au moteur
is_sqlite = parsed_url.startswith("sqlite")
engine_args = {}
if is_sqlite:
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(parsed_url, **engine_args)

# Activation du mode WAL pour SQLite (permet lecture/écriture concurrentes)
if is_sqlite:
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────────────────────
# MODÈLES
# ─────────────────────────────────────────────────────────────

class Portfolio(Base):
    """Portefeuille principal — capital et état global."""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True, unique=True)
    capital = Column(Float, nullable=False, default=10000.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    """Enregistrement d'un trade (ouvert ou fermé)."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    status = Column(String(10), nullable=False, default="OPEN")  # OPEN | CLOSED
    entry_date = Column(DateTime, default=datetime.utcnow)
    exit_date = Column(DateTime, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    justification = Column(Text, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    pnl = Column(Float, nullable=True)  # Profit & Loss en $


class ActivityLog(Base):
    """Journal d'activité de l'IA Axiom."""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    type = Column(String(20), default="INFO")  # INFO | BUY | SELL | ERROR
    timestamp = Column(DateTime, default=datetime.utcnow)
    reference_id = Column(Integer, nullable=True) # ID du ChatMessage lié pour navigation


class PortfolioHistory(Base):
    """Historique de la valeur du portefeuille dans le temps."""
    __tablename__ = "portfolio_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_value = Column(Float, nullable=False)
    capital_liquide = Column(Float, nullable=True)


class NewsItem(Base):
    """Article de presse financière avec score de sentiment."""
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)
    url = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    sentiment_score = Column(Float, nullable=True)   # -1.0 à +1.0
    related_symbol = Column(String(10), nullable=True, index=True)
    source_type = Column(String(20), default="RSS") # RSS | TWITTER
    importance_weight = Column(Float, default=1.0)
    raw_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    """Historique des messages du chatbot."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────
# INITIALISATION
# ─────────────────────────────────────────────────────────────

def init_db() -> None:
    """Crée toutes les tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dépendance FastAPI — fournit une session DB par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
