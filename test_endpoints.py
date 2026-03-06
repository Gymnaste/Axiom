import requests

# Test search endpoint
try:
    res = requests.get("http://127.0.0.1:8000/market/search-ticker?query=Apple")
    print("Search Apple:", res.json())
except Exception as e:
    print("Search Error:", e)

# Test chat endpoint with a null message
try:
    payload = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": None},
            {"role": "user", "content": "Achète Apple"}
        ]
    }
    # Wait, the frontend sends {"messages": [...] } to Fastapi. Let's trace it.
    res2 = requests.post("http://127.0.0.1:8000/chat", headers={"Authorization": "Bearer TEST_TOKEN"}, json=payload)
    print("Chat:", res2.status_code, res2.text)
except Exception as e:
    print("Chat Error:", e)
