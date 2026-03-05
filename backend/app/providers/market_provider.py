import pandas as pd
import yfinance as yf
from app.config import MARKET_DATA_PERIOD
from app.core.logger import setup_logger

logger = setup_logger("market_provider")

class MarketProvider:
    def get_historical_data(self, symbol: str, period: str = MARKET_DATA_PERIOD):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if df.empty: return pd.DataFrame()
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            logger.error(f"Error fetch {symbol}: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str):
        try:
            ticker = yf.Ticker(symbol)
            # fast_info est souvent instable (retourne None), on préfère history(1d)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            
            # Fallback ultime sur fast_info au cas où
            price = ticker.fast_info.get("last_price")
            return float(price) if price else None
        except Exception as e:
            logger.error(f"Error get_current_price {symbol}: {e}")
            return None

    def get_multiple_prices(self, symbols: list[str]) -> dict:
        """Récupère les prix actuels pour une liste de symboles en une seule requête."""
        if not symbols:
            return {}
        try:
            logger.info(f"Fetching multiple prices for: {symbols}")
            data = yf.download(symbols, period="1d", interval="1m", progress=False)
            if data.empty:
                logger.warning("yf.download returned empty data.")
                return {s: self.get_current_price(s) for s in symbols if self.get_current_price(s)}
            
            prices = {}
            for s in symbols:
                try:
                    if len(symbols) > 1:
                        # yf.download can return MultiIndex or simple Index depending on data availability
                        if isinstance(data.columns, pd.MultiIndex):
                            price = data['Close'][s].dropna().iloc[-1]
                        else:
                            price = data['Close'].dropna().iloc[-1]
                    else:
                        price = data['Close'].dropna().iloc[-1]
                    
                    if not pd.isna(price):
                        prices[s] = float(price)
                except Exception as e:
                    logger.warning(f"Failed to extract price for {s} from batch: {e}. Falling back.")
                    p = self.get_current_price(s)
                    if p: prices[s] = p
            
            logger.info(f"Successfully fetched prices: {list(prices.keys())}")
            return prices
        except Exception as e:
            logger.error(f"Error in get_multiple_prices: {e}")
            return {s: self.get_current_price(s) for s in symbols if self.get_current_price(s)}

    def get_stock_info(self, symbol: str) -> dict:
        """Récupère les informations de base de l'entreprise via yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            # ticker.info est très lent et plante souvent sur les serveurs distants
            # On essaie de récupérer le nom via fast_info d'abord
            fast = ticker.fast_info
            name = fast.get("shortName") or symbol
            
            # Si on veut vraiment les détails, on tente info avec un timeout implicite court
            try:
                info = ticker.info
                name = info.get("shortName", name)
                return {
                    "symbol": symbol,
                    "name": name,
                    "sector": info.get("sector", "Marché financier"),
                    "industry": info.get("industry", "Finance"),
                    "marketCap": info.get("marketCap", None),
                    "summary": info.get("longBusinessSummary", "Données descriptives temporairement indisponibles.")
                }
            except:
                return {
                    "symbol": symbol,
                    "name": name,
                    "sector": "Marché financier",
                    "industry": "Finance",
                    "summary": f"Informations sur {symbol}."
                }
        except Exception as e:
            logger.error(f"Error fetch info {symbol}: {e}")
            return {"symbol": symbol, "name": symbol, "error": str(e)}

    def get_stock_history(self, symbol: str, period: str = "6mo") -> list:
        """Récupère l'historique des prix pour le graphique, retourne une liste de dicts."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            if hist.empty:
                return []
            
            # Formater les données pour le frontend
            result = []
            for date_val, row in hist.iterrows():
                # Pour 1j, on garde l'heure. Pour le reste, seulement la date.
                fmt = "%H:%M" if period == "1d" else "%Y-%m-%d"
                result.append({
                    "date": date_val.strftime(fmt),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"])
                })
            return result
        except Exception as e:
            logger.error(f"Error fetch history {symbol}: {e}")
            return []

    def get_ticker_news(self, symbol: str, limit: int = 5) -> list[str]:
        """Récupère les dernières actualités pour un ticker spécifique."""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            if not news:
                return []
            # Retourne juste les titres pour le prompt IA
            return [n.get("title") for n in news[:limit] if n.get("title")]
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []
