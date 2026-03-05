import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.core.logger import setup_logger

load_dotenv(override=True)
logger = setup_logger("openai_service")

AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if AI_ENABLED else None

class OpenAIService:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    def get_chat_response(self, message: str, context: str = ""):
        if not AI_ENABLED:
            return "[IA désactivée] Ajoutez AI_ENABLED=true dans le .env et redémarrez pour utiliser le chatbot."
        try:
            system_prompt = (
                "Tu es Trading Bach Bot, un assistant expert en bourse et trading. "
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
            return "Désolé, je rencontre une difficulté technique pour répondre à votre question pour le moment."

    def get_actionable_response(self, message: str, context: str = "") -> dict:
        """Version évoluée du chat qui détecte des intentions d'action."""
        if not AI_ENABLED:
            return {"response": "[IA désactivée] Ajoutez AI_ENABLED=true dans le .env pour activer le chatbot.", "intent": None, "params": {}}
        try:
            system_prompt = (
                "Tu es Trading Bach Bot, un assistant expert en bourse et trading. Tu aides l'utilisateur à"
                " comprendre les marchés et à gérer son portefeuille.\n"
                f"Contexte actuel : {context}\n"
                "Si l'utilisateur exprime une intention d'action (vendre, acheter, modifier TP/SL, changer le profil de risque, retirer des fonds),"
                " tu DOIS retourner un JSON avec ce format :\n"
                '{"response": "<ta réponse naturelle>", "intent": "<action|null>", "params": {<params>}}\n'
                "Actions possibles et leurs params :\n"
                '- "sell": {"symbol": "XXX"} ou {"trade_id": 123}\n'
                '- "update_targets": {"symbol": "XXX", "stop_loss": float|null, "take_profit": float|null}\n'
                '- "set_risk_profile": {"profile": "aggressive"|"moderate"|"conservative"}\n'
                '- "withdraw": {"amount": float}\n'
                '- "reset": {}\n'
                "Si aucune action n'est demandée, mets intent à null et params à {}."
                " Sois précis, professionnel, en français."
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                response_format={"type": "json_object"},
                temperature=0.6,
                max_tokens=400
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"Erreur OpenAI chat actionnable : {e}")
            return {"response": "Désolé, erreur technique.", "intent": None, "params": {}}

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
                "\nSi la recommandation est BUY ou SELL, tu DOIS fournir un take_profit et un stop_loss logiques. Sinon, mets-les à 0."
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
        if not AI_ENABLED:
            return query.upper()
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
        except Exception:
            return query.upper()
