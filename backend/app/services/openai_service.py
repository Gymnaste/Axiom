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
            client = OpenAI(api_key=OPENAI_API_KEY)
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
                max_tokens=500
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

        # Insérer ou mettre à jour le message système
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            messages[0]["content"] = system_prompt

        chat_tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_market_data",
                    "description": "Recherche un ticker officiel (Yahoo Finance) ou des informations de marché à partir d'un nom d'entreprise ou d'un secteur (ex: pétrole).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "La recherche de l'utilisateur (nom d'entreprise, secteur, etc.)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_trade",
                    "description": "Exécute un ordre d'achat (buy) ou de vente (sell) sur le marché pour l'utilisateur.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Le ticker boursier officiel (ex: AAPL, TSLA)."
                            },
                            "action": {
                                "type": "string",
                                "enum": ["buy", "sell"],
                                "description": "L'action à effectuer : 'buy' pour acheter, 'sell' pour vendre."
                            },
                            "amount": {
                                "type": "number",
                                "description": "Le montant en dollars ($) de l'opération ou la quantité si l'utilisateur précise des unités (dans le doute, considère que ce sont des dollars)."
                            }
                        },
                        "required": ["ticker", "action", "amount"]
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
                max_tokens=500
            )
            return response.choices[0].message
        except Exception as e:
            logger.error(f"Erreur OpenAI Tool Calling : {e}")
            error_msg = str(e).lower()
            if "insufficient_quota" in error_msg:
                return {"role": "assistant", "content": "Erreur OpenAI : Vous n'avez plus de crédits (quota dépassé)."}
            elif "invalid_api_key" in error_msg:
                return {"role": "assistant", "content": "Erreur OpenAI : Votre clé API est invalide."}
            return {"role": "assistant", "content": f"Désolé, erreur technique lors de l'analyse ({type(e).__name__}) : {str(e)}."}

    def analyze_market_signal(self, symbol: str, indicators: dict, sentiment: float, portfolio_context: str) -> dict:
        """Demande à l'IA d'analyser le marché et de retourner une décision au format JSON."""
        if not AI_ENABLED:
            logger.info(f"[IA désactivée] Analyse de {symbol} ignorée (HOLD par défaut)")
            return {"recommendation": "HOLD", "confidence": 0.0, "justification": "IA désactivée (AI_ENABLED=false)", "take_profit": 0, "stop_loss": 0}
        try:
            system_prompt = (
                "Tu es un algorithme de trading expert quantitatif et psychologique. "
                "Ton rôle est d'analyser les données de marché qu'on te fournit et de renvoyer UNIQUEMENT un objet JSON valide. "
                "Le format JSON doit obéir à ce schéma exact : \n"
                '{"recommendation": "BUY" | "SELL" | "HOLD", "confidence": float (entre 0.0 et 1.0), "justification": "string courte", "take_profit": float, "stop_loss": float}'
                "\nSi la recommandation est BUY ou SELL, tu DOIS fournir un take_profit et un stop_loss logiques. Sinon, mets-les à 0. "
                "IMPORTANT: Réponds uniquement avec du JSON."
            )

            user_message = (
                f"Analyse l'action {symbol} avec les données suivantes :\n"
                f"- Indicateurs techniques : {json.dumps(indicators)}\n"
                f"- Score de sentiment des actualités récentes : {sentiment} (-1 très négatif, +1 très positif)\n\n"
                f"Contexte du portefeuille actuel : {portfolio_context}\n\n"
                "Donne ta recommandation finale au format JSON strict."
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={ "type": "json_object" },
                temperature=0.4,
                max_tokens=200
            )

            result_str = response.choices[0].message.content
            result_json = json.loads(result_str)
            return result_json
        except Exception as e:
            logger.error(f"Erreur OpenAI lors de l'analyse pour {symbol} : {e}")
            # Fallback en cas d'erreur de l'IA
            return {"recommendation": "HOLD", "confidence": 0.0, "justification": f"Erreur IA : {str(e)}", "take_profit": 0, "stop_loss": 0}

    def discover_opportunities(self, news_summary: str) -> list[str]:
        """Analyse l'actualité globale et propose des symboles boursiers prometteurs."""
        if not AI_ENABLED:
            logger.info("[IA désactivée] Découverte d'opportunités ignorée")
            return []
        try:
            prompt = (
                "Tu es un analyste financier expert. Voici les dernières actualités mondiales du marché financier :\n"
                f"{news_summary}\n\n"
                "Identifie 3 entreprises très prometteuses ou très risquées dont on parle actuellement "
                "et qui pourraient représenter une excellente opportunité de trade à court terme. "
                "IMPORTANT : Propose un spectre TRÈS LARGE d'actions (Small caps, Mid caps, et Large caps). Ne te limite pas aux GAFAM ou aux géants technologiques. Cherche des pépites sur tout le marché. "
                "Tu DOIS retourner UNIQUEMENT des TICKERS OFFICIELS VALIDES sur Yahoo Finance (ex: GTLB et non GITLAB). "
                "Retourne UNIQUEMENT une liste JSON de ces symboles boursiers sous ce format exact : "
                '{"symbols": ["AAPL", "NVDA", "PLTR"]}'
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0.7,
                max_tokens=150
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("symbols", [])
        except Exception as e:
            logger.error(f"Erreur découverte OpenAI : {e}")
            return []

    def get_ticker_suggestion(self, query: str) -> str:
        """Utilise l'IA pour mapper un nom d'entreprise ou une recherche vers un ticker valide."""
        if not query: return ""
        q = query.strip().upper()
        
        # Mapping manuel de base en cas d'échec IA ou pour vitesse
        manual_map = {
            "APPLE": "AAPL", "MICROSOFT": "MSFT", "TESLA": "TSLA", "GOOGLE": "GOOGL", 
            "ALPHABET": "GOOGL", "AMAZON": "AMZN", "META": "META", "FACEBOOK": "META",
            "NVIDIA": "NVDA", "NETFLIX": "NFLX", "BITCOIN": "BTC-USD", "ETH": "ETH-USD",
            "TOTAL": "TTE.PA", "LVMH": "MC.PA", "AIRBUS": "AIR.PA", "RENAULT": "RNO.PA",
            "BNP": "BNP.PA", "SOCIETE GENERALE": "GLE.PA", "ORANGE": "ORA.PA"
        }
        if q in manual_map: return manual_map[q]

        if not AI_ENABLED:
            return q
        try:
            prompt = (
                f"L'utilisateur recherche une action avec ce texte : '{query}'.\n"
                "Identifie l'entreprise probable et son TICKER boursier officiel (Yahoo Finance).\n"
                "Réponds UNIQUEMENT avec le ticker en majuscules (ex: AAPL, BTC-USD, MSFT).\n"
                "Si tu ne trouves rien, renvoie UNIQUEMENT le texte original en majuscules."
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10
            )
            return response.choices[0].message.content.strip().upper()
        except Exception as e:
            logger.error(f"Erreur suggestion ticker OpenAI : {e}")
            return q

    def get_autonomous_decision(self, ticker: str, history: list, news: list, balance: float, performance_history: str = "") -> dict:
        """
        Analyse les données OHLC et les news pour prendre une décision de trading 100% autonome.
        Prend en compte l'historique de performance pour ne pas répéter les erreurs passées.
        """
        if not AI_ENABLED:
            return {"action": "HOLD", "reasoning": "IA désactivée"}

        try:
            perf_context = f"\n--- TON HISTORIQUE DE PERFORMANCE RÉCENT ---\n{performance_history}\n" if performance_history else ""
            
            system_prompt = (
                "Tu es le gestionnaire de fonds principal de Axiom. "
                "Ton objectif est de maximiser les profits tout en gérant strictement le risque. "
                "Tu reçois des données techniques (OHLC), les dernières news, et ton historique récent. \n"
                f"{perf_context}"
                "\nAnalyses tes erreurs passées pour ne pas les reproduire. Si tu as subi des pertes sur des trades similaires, "
                "sois plus prudent ou ajuste tes seuils de Stop Loss et Take Profit.\n"
                "Règles strictes :\n"
                "1. Investissement max : 5% du balance actuel par trade.\n"
                "2. Réponds UNIQUEMENT en JSON structuré.\n"
                "3. Si tu achètes, définis obligatoirement un stop_loss (SL) et un take_profit (TP) cohérents.\n"
                "Format attendu :\n"
                "{\n"
                '  "action": "BUY" | "SELL" | "HOLD",\n'
                '  "amount_pct": float (0.0 à 0.05),\n'
                '  "stop_loss": float,\n'
                '  "take_profit": float,\n'
                '  "reasoning": "explication détaillée du choix incluant une auto-critique si nécessaire"\n'
                "}"
            )

            user_message = (
                f"--- DONNÉES POUR {ticker} ---\n"
                f"Balance actuel : ${balance:.2f}\n"
                f"Historique récent (OHLC) : {json.dumps(history[-20:])}\n"
                f"Dernières news : {json.dumps(news)}\n\n"
                "Quelle est ta décision ?"
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=400
            )

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Erreur get_autonomous_decision pour {ticker}: {e}")
            return {"action": "HOLD", "reasoning": f"Erreur technique: {str(e)}"}
