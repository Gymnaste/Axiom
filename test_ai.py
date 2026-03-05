import sys
import os

# Set working directory to backend
os.chdir("c:/Users/bonas/Documents/Projet TradingBOT/backend")
sys.path.append(os.getcwd())

from app.services.openai_service import OpenAIService

svc = OpenAIService()

print("Testing get_autonomous_decision...")
res = svc.get_autonomous_decision("AAPL", [{"close": 150}], [{"title": "Apple is doing well"}], 1000)
print(res)

print("Testing analyze_market_signal...")
res2 = svc.analyze_market_signal("AAPL", {"current_price": 150, "rsi": 50}, 0.5, "Capital: 1000, Positions: 0")
print(res2)
