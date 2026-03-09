import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.core.logger import setup_logger

load_dotenv(override=True)
logger = setup_logger("openai_service")

AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if AI_ENABLED:
    if OPENAI_API_KEY:
        try:
            # On définit un timeout global par défaut de 60s
            client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client OpenAI: {e}")
            AI_ENABLED = False
    else:
        logger.warning("OPENAI_API_KEY manquante. L'IA sera désactivée.")
        AI_ENABLED = False

class OpenAIService:
    def __init__(self):
        env_model = os.getenv("OPENAI_MODEL", "").strip()
        self.model = env_model if env_model else "gpt-4o-mini"

    def get_chat_response(self, message: str, context: str = ""):
        if not AI_ENABLED:
            return "[IA désactivée] Ajoutez AI_ENABLED=true dans le .env et redémarrez pour utiliser le chatbot."
        try:
            system_prompt = (
                "Tu es Axiom, un assistant expert en bourse et trading. "
                "Tu aides l'utilisateur à comprendre les marchés, analyser les actions et gérer son portefeuille. "
                "Sois précis, professionnel et utilise des termes financiers corrects. "
                f"Voici le contexte actuel du portefeuille : {context}"
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=45.0
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erreur OpenAI : {e}")
            error_msg = str(e).lower()
            if "insufficient_quota" in error_msg:
                return "Erreur OpenAI : Vous n'avez plus de crédits sur votre compte OpenAI."
            elif "invalid_api_key" in error_msg:
                return "Erreur OpenAI : Votre clé API est invalide."
            return f"Désolé, erreur technique IA ({type(e).__name__}) : {str(e)}. Vérifiez votre configuration OpenAI."

    def get_tool_calling_response(self, messages: list, context: str = ""):
        """Envoie l'historique des messages à OpenAI avec les outils définis."""
        if not AI_ENABLED:
            return {"role": "assistant", "content": "[IA désactivée] Activez AI_ENABLED=true."}
        
        system_prompt = (
            "Tu es Axiom, un assistant expert en bourse et trading. Tu aides l'utilisateur à"
            " comprendre les marchés et à gérer son portefeuille de manière autonome.\n"
            f"Contexte actuel : {context}\n"
            "Tu as accès à des outils (tools) pour chercher des actions (search_market_data) et exécuter des trades (execute_trade).\n"
            "N'hésite pas à utiliser ces outils quand l'utilisateur te demande d'agir ou de chercher des informations. "
            "Si tu as besoin de plus de précisions pour un trade (quantité, ticker exact), pose la question à l'utilisateur."
        )

        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            messages[0]["content"] = system_prompt

        chat_tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_market_data",
                    "description": "Recherche un ticker officiel (Yahoo Finance) ou des informations de marché à partir d'un nom d'entreprise ou d'un secteur.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "La recherche de l'utilisateur"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_trade",
                    "description": "Exécute un ordre d'achat (buy) ou de vente (sell).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Le ticker boursier officiel."},
                            "action": {"type": "string", "enum": ["buy", "sell"], "description": "L'action à effectuer."},
                            "amount": {"type": "number", "description": "Le montant en dollars ($) ou la quantité."}
                        },
                        "required": ["ticker", "action", "amount"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_news",
                    "description": "Récupère les dernières actualités financières.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Le ticker boursier optionnel."}
                        }
                    }
                }
            }
        ]

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=chat_tools,
                temperature=0.6,
                max_tokens=500,
                timeout=60.0
            )
            return response.choices[0].message
        except Exception as e:
            logger.error(f"Erreur OpenAI Tool Calling : {e}")
            return {"role": "assistant", "content": f"Désolé, erreur technique IA ({type(e).__name__}) : {str(e)}."}

    def analyze_market_signal(self, symbol: str, indicators: dict, sentiment: float, portfolio_context: str) -> dict:
        if not AI_ENABLED:
            return {"recommendation": "HOLD", "confidence": 0.0, "justification": "IA désactivée", "take_profit": 0, "stop_loss": 0}
        try:
            system_prompt = (
                "Tu es un algorithme de trading expert. "
                "Réponds UNIQUEMENT en JSON valide : \n"
                '{"recommendation": "BUY" | "SELL" | "HOLD", "confidence": float, "justification": "string", "take_profit": float, "stop_loss": float}'
            )

            user_message = (
                f"Analyse {symbol} :\n"
                f"- Indicateurs : {json.dumps(indicators)}\n"
                f"- Sentiment : {sentiment}\n"
                f"Contexte : {portfolio_context}"
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={ "type": "json_object" },
                temperature=0.4,
                max_tokens=200,
                timeout=45.0
            )

            result_str = response.choices[0].message.content
            return json.loads(result_str)
        except Exception as e:
            logger.error(f"Erreur analyze_market_signal pour {symbol} : {e}")
            return {"recommendation": "HOLD", "confidence": 0.0, "justification": f"Erreur IA : {str(e)}", "take_profit": 0, "stop_loss": 0}

    def discover_opportunities(self, news_summary: str) -> list[str]:
        if not AI_ENABLED: return []
        try:
            prompt = (
                "Analyse l'actualité financière et propose 3 symboles prometteurs (tickers Yahoo Finance).\n"
                'Format JSON : {"symbols": ["AAPL", "NVDA", "PLTR"]}'
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": news_summary + "\n\n" + prompt}],
                response_format={ "type": "json_object" },
                temperature=0.7,
                max_tokens=150,
                timeout=45.0
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("symbols", [])
        except Exception as e:
            logger.error(f"Erreur discover_opportunities: {e}")
            return []

    def get_ticker_suggestion(self, query: str) -> str:
        if not query: return ""
        if not AI_ENABLED: return query.strip().upper()
        try:
            prompt = f"Donne le ticker Yahoo Finance pour '{query}'. Réponds UNIQUEMENT avec le ticker (ex: AAPL)."
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
                timeout=20.0
            )
            return response.choices[0].message.content.strip().upper()
        except Exception as e:
            return query.strip().upper()

    def get_autonomous_decision(self, ticker: str, history: list, news: list, balance: float, performance_history: str = "") -> dict:
        if not AI_ENABLED: return {"action": "HOLD", "reasoning": "IA désactivée"}
        try:
            system_prompt = (
                "Tu es un gestionnaire de fonds. Décide si on doit BUY, SELL ou HOLD.\n"
                "Réponds UNIQUEMENT en JSON structuré :\n"
                '{"action": "BUY"|"SELL"|"HOLD", "amount_pct": float, "stop_loss": float, "take_profit": float, "reasoning": "string"}'
            )

            user_message = (
                f"Ticker: {ticker}\nBalance: ${balance:.2f}\n"
                f"History sample: {json.dumps(history[-5:])}\n"
                f"Perf context: {performance_history}"
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=400,
                timeout=60.0
            )

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Erreur get_autonomous_decision {ticker}: {e}")
            return {"action": "HOLD", "reasoning": f"Erreur technique: {str(e)}"}

    def get_cycle_report_summary(self, analysis_results: list) -> str:
        if not AI_ENABLED or not analysis_results: return ""
        try:
            prompt = (
                "Rédige un compte-rendu très court (3 phrases) pour un utilisateur sur les actions de trading effectuées :\n"
                f"{json.dumps(analysis_results)}"
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
                timeout=45.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return "Cycle d'analyse terminé. Les ajustements nécessaires ont été effectués."
