"""
chat_router.py — Chatbot interactif ET actionnable d'Axiom.
Le bot peut non seulement répondre en langage naturel, mais aussi exécuter des actions
sur le portefeuille (vendre, modifier TP/SL, changer profil de risque, etc.)
"""
import os
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.openai_service import OpenAIService
from app.services.portfolio_service import PortfolioService
from app.core.auth_deps import get_current_user_id

router = APIRouter(prefix="/chat", tags=["Chat"])
openai_service = OpenAIService()
portfolio_service = PortfolioService()

import json

@router.post("")
def chat_with_bot(messages: list = Body(..., embed=True), db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """
    Communique avec Axiom via OpenAI.
    Supporte le chat avec historique et l'appel d'outils (Tool Calling).
    """
    summary = portfolio_service.get_portfolio_summary(db, user_id)
    open_positions = summary['positions_ouvertes']

    # Contexte enrichi pour l'IA
    positions_str = ", ".join([
        f"{p['symbol']} (id:{p['id']}, TP:{p.get('take_profit', 'N/A')}$, SL:{p.get('stop_loss', 'N/A')}$)"
        for p in open_positions
    ])
    risk_profile = os.getenv("RISK_PROFILE", "moderate")
    context = (
        f"Capital liquide: {summary['capital']}$, Valeur totale: {summary['valeur_totale']}$. "
        f"Positions ouvertes: {positions_str if positions_str else 'Aucune'}. "
        f"Profil de risque actuel: {risk_profile}."
    )

    # Sanitiser les messages pour éviter l'erreur "expected a string, got null"
    for msg in messages:
        if "content" in msg and msg["content"] is None:
            msg["content"] = ""

    # Premier appel à l'IA avec context et tools
    response_msg = openai_service.get_tool_calling_response(messages, context)

    # Si l'IA n'est pas activée ou renvoie un dictionnaire simple d'erreur
    if isinstance(response_msg, dict):
        return {"response": response_msg.get("content", "Erreur IA")}

    # Gestion de la boucle Tool Calling
    if getattr(response_msg, 'tool_calls', None):
        # On ajoute la réponse de l'assistant à l'historique
        messages.append({
            "role": response_msg.role,
            "content": response_msg.content,
            "tool_calls": [
                {
                    "id": t.id,
                    "type": "function",
                    "function": {"name": t.function.name, "arguments": t.function.arguments}
                } for t in response_msg.tool_calls
            ]
        })

        # On exécute chaque outil demandé
        for tool_call in response_msg.tool_calls:
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except Exception:
                arguments = {}

            tool_result = {"success": False, "error": "Unknown tool"}

            if function_name == "search_market_data":
                query = arguments.get("query", "")
                ticker = openai_service.get_ticker_suggestion(query)
                info = portfolio_service.market.get_stock_info(ticker)
                tool_result = {"suggested_ticker": ticker, "market_info": info}

            elif function_name == "execute_trade":
                ticker = arguments.get("ticker", "").upper()
                action = arguments.get("action", "").lower()
                amount = float(arguments.get("amount", 0))

                if action == "buy":
                    price = portfolio_service.market.get_current_price(ticker)
                    if not price:
                        tool_result = {"success": False, "error": f"Prix pour {ticker} indisponible."}
                    else:
                        qty = amount / price
                        tool_result = portfolio_service.open_position(db, user_id, symbol=ticker, price=price, qty=qty, justification="Achat via assistant IA")
                elif action == "sell":
                    # On cherche la première position ouverte pour ce ticker
                    trade = next((p for p in open_positions if p['symbol'] == ticker), None)
                    if trade:
                        tool_result = portfolio_service.close_position(db, user_id, trade['id'])
                    else:
                        tool_result = {"success": False, "error": f"Aucune position ouverte trouvée pour {ticker}."}

            # On ajoute le résultat de l'outil à l'historique
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(tool_result)
            })

        # Relance l'appel avec les résultats
        response_msg = openai_service.get_tool_calling_response(messages, context)
        if isinstance(response_msg, dict):
            response_text = response_msg.get("content", "Erreur IA après outil")
        else:
            response_text = response_msg.content

    else:
        response_text = response_msg.content

    return {
        "response": response_text
    }
