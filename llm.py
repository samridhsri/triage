import logging
import re
import requests
import json
import os
from datetime import date
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Strip markdown code fences that Gemini sometimes adds despite instructions."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1)
    return text

client = genai.Client()


def split_intents(user_input: str) -> list:
    with open("splitter_prompt.txt", "r") as f:
        system_prompt = f.read()

    today = date.today().isoformat()
    message = f"TODAY: {today}\n\nUSER INPUT:\n{user_input}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": system_prompt},
                    {"text": message},
                ],
            }
        ],
        config={"temperature": 0.2, "max_output_tokens": 8192},
    )

    raw_text = response.text
    logger.debug("Raw splitter response: %s", raw_text)
    try:
        parsed = json.loads(_extract_json(raw_text))
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        logger.error("Raw response was: %s", raw_text)
        return []
    intents = parsed.get("intents", [])
    logger.info("Parsed %d intent(s) from LLM", len(intents))
    return intents


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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=payload["contents"],
    )

    raw_text = response.text
    logger.debug("Raw route_input response: %s", raw_text)
    return json.loads(_extract_json(raw_text))

