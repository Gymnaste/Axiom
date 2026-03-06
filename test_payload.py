import sys
import os

os.chdir("c:/Users/bonas/Documents/Projet TradingBOT/backend")
sys.path.append(os.getcwd())

from app.services.openai_service import OpenAIService

svc = OpenAIService()

# Reproduire un historique de tool calling
messages = [
    {"role": "user", "content": "Achete Apple"},
    {"role": "assistant", "content": None, "tool_calls": [{"id": "call_123", "type": "function", "function": {"name": "execute_trade", "arguments": '{"ticker": "AAPL", "action": "buy", "amount": 10}'}}]},
    {"role": "tool", "tool_call_id": "call_123", "name": "execute_trade", "content": '{"success": true}'},
    {"role": "user", "content": "Ok fais le."}
]

# Sanitization (what the router does)
for msg in messages:
    if "content" not in msg or msg["content"] is None:
        msg["content"] = ""

print("Test with sanitization...")
try:
    res = svc.get_tool_calling_response(messages, "Context")
    print("Success:")
    print(res)
except Exception as e:
    print(f"Error: {e}")
