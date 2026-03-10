from fastapi import APIRouter, Depends, Body
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.portfolio_service import PortfolioService
from app.providers.market_provider import MarketProvider
from app.core.auth_deps import get_current_user_id
import logging

logger = logging.getLogger("portfolio_router")
router = APIRouter(prefix="/portfolio", tags=["Portfolio"])
service = PortfolioService()
market = MarketProvider()

@router.get("")
def get_portfolio(db=Depends(get_db), user_id: str = Depends(get_current_user_id)):
    logger.info(f"FETCH: Portfolio pour user_id={user_id}")
    return service.get_portfolio_summary(db, user_id)

@router.get("/positions")
def get_positions(db=Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return {"positions": service.get_detailed_positions(db, user_id)}

@router.get("/history")
def get_history(db=Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return {"historique": service.repo.get_history(db, user_id)}

@router.get("/trades/{symbol}")
def get_symbol_trades(symbol: str, db=Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return service.trade_repo.get_trades_by_symbol(db, user_id, symbol)

# ─── Trading Manuel ───────────────────────────────────────────────────────────

@router.post("/buy")
def buy_manual(
    symbol: str = Body(...),
    quantity: Optional[float] = Body(None),
    stop_loss: Optional[float] = Body(None),
    take_profit: Optional[float] = Body(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Achat manuel d'une action au prix actuel."""
    price = market.get_current_price(symbol.upper())
    if not price:
        return {"success": False, "error": f"Impossible de récupérer le prix de {symbol}"}
    result = service.open_position(
        db, user_id, symbol.upper(), price,
        qty=quantity, sl=stop_loss, tp=take_profit,
        justification="Achat manuel par l'utilisateur"
    )
    return result

@router.post("/sell/{trade_id}")
def sell_manual(trade_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Vente manuelle d'une position au prix actuel."""
    return service.close_position(db, user_id, trade_id)

@router.post("/position/{trade_id}/add")
def add_to_position(
    trade_id: int,
    quantity: Optional[float] = Body(None, embed=True),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Ajouter des unités à une position existante au prix actuel."""
    return service.add_to_position(db, user_id, trade_id, extra_qty=quantity)

@router.patch("/position/{trade_id}/targets")
def update_targets(
    trade_id: int,
    stop_loss: Optional[float] = Body(None),
    take_profit: Optional[float] = Body(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Modifier le Stop Loss et/ou le Take Profit d'une position ouverte."""
    return service.update_targets(db, user_id, trade_id, sl=stop_loss, tp=take_profit)

@router.post("/withdraw")
def withdraw(
    amount: float = Body(..., embed=True),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retirer des fonds du capital liquide."""
    return service.withdraw(db, user_id, amount)

@router.post("/deposit")
def deposit(
    amount: float = Body(..., embed=True),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Ajouter des fonds au solde liquide (sans toucher aux positions)."""
    return service.deposit(db, user_id, amount)

@router.get("/activity")
def get_activity_logs(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Récupère les derniers logs d'activité de l'IA."""
    logger.info(f"FETCH: Activity logs pour user_id={user_id}")
    from app.database import ActivityLog
    logs = db.query(ActivityLog).filter(ActivityLog.user_id == user_id).order_by(ActivityLog.timestamp.desc()).limit(20).all()
    return logs

@router.get("/transactions")
def get_transactions(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Récupère l'historique détaillé des achats et ventes."""
    from app.database import Trade
    trades = db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.entry_date.desc()).all()
    
    transactions = []
    for t in trades:
        # Achat
        transactions.append({
            "id": f"buy-{t.id}",
            "type": "ACHAT",
            "symbol": t.symbol,
            "date": t.entry_date,
            "price": t.entry_price,
            "quantity": t.quantity,
            "total": round(t.entry_price * t.quantity, 2)
        })
        # Vente (si fermé)
        if t.status == "CLOSED" and t.exit_date:
            transactions.append({
                "id": f"sell-{t.id}",
                "type": "VENTE",
                "symbol": t.symbol,
                "date": t.exit_date,
                "price": t.exit_price,
                "quantity": t.quantity,
                "total": round((t.exit_price or 0) * t.quantity, 2)
            })
    
    # Trier par date décroissante (les plus récents en premier)
    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions
