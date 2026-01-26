import requests
import json
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-1.5-flash:generateContent"
)

def route_input(user_input):
    with open("router_prompt.txt", "r") as f:
        system_prompt = f.read()

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": system_prompt},
                    {"text": "\nUSER INPUT:\n" + user_input}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800
        }
    }

    response = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    response.raise_for_status()
    raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]

    return json.loads(raw_text)
