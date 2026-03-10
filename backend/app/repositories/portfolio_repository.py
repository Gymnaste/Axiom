from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import Portfolio, Trade, PortfolioHistory
from app.core.logger import setup_logger

logger = setup_logger("portfolio_repository")

class PortfolioRepository:
    def get_portfolio(self, db: Session, user_id: str):
        return db.query(Portfolio).filter(Portfolio.user_id == user_id).first()

    def get_all_user_ids(self, db: Session):
        return [r[0] for r in db.query(Portfolio.user_id).distinct().all()]

    def get_or_create_portfolio(self, db: Session, user_id: str):
        portfolio = self.get_portfolio(db, user_id)
        if not portfolio:
            from app.config import CAPITAL_INITIAL
            portfolio = Portfolio(user_id=user_id, capital=CAPITAL_INITIAL)
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
        return portfolio

    def update_capital(self, db: Session, user_id: str, new_capital: float):
        portfolio = self.get_or_create_portfolio(db, user_id)
        portfolio.capital = new_capital
        portfolio.last_updated = datetime.now(timezone.utc)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    def add_history_point(self, db: Session, user_id: str, total_value: float, capital_liquide: float):
        point = PortfolioHistory(user_id=user_id, total_value=total_value, capital_liquide=capital_liquide)
        db.add(point)
        db.commit()
        db.refresh(point)
        return point

    def get_history(self, db: Session, user_id: str, limit: int = 100):
        return db.query(PortfolioHistory).filter(PortfolioHistory.user_id == user_id).order_by(PortfolioHistory.timestamp.desc()).limit(limit).all()

class TradeRepository:
    def create_trade(self, db: Session, user_id: str, symbol: str, entry_price: float, quantity: float, stop_loss: float, take_profit: float, justification: str = None):
        trade = Trade(
            user_id=user_id,
            symbol=symbol, 
            entry_price=entry_price, 
            quantity=quantity, 
            stop_loss=stop_loss, 
            take_profit=take_profit, 
            justification=justification,
            status="OPEN"
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade

    def close_trade(self, db: Session, trade_id: int, exit_price: float):
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade: return None
        trade.exit_price = exit_price
        trade.exit_date = datetime.now(timezone.utc)
        trade.status = "CLOSED"
        trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        db.commit()
        db.refresh(trade)
        return trade

    def get_open_trades(self, db: Session, user_id: str):
        return db.query(Trade).filter(Trade.user_id == user_id, Trade.status == "OPEN").all()

    def get_closed_trades(self, db: Session, user_id: str, limit: int = 10):
        return db.query(Trade).filter(
            Trade.user_id == user_id, 
            Trade.status == "CLOSED"
        ).order_by(Trade.exit_date.desc()).limit(limit).all()

    def get_all_trades(self, db: Session, user_id: str):
        return db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.entry_date.desc()).all()

    def get_trades_by_symbol(self, db: Session, user_id: str, symbol: str):
        return db.query(Trade).filter(Trade.user_id == user_id, Trade.symbol == symbol).order_by(Trade.entry_date.desc()).all()

    def get_trade_by_id(self, db: Session, trade_id: int):
        return db.query(Trade).filter(Trade.id == trade_id).first()

    def update_trade_targets(self, db: Session, trade_id: int, sl: float = None, tp: float = None):
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return None
        if sl is not None:
            trade.stop_loss = sl
        if tp is not None:
            trade.take_profit = tp
        db.commit()
        db.refresh(trade)
        return trade
