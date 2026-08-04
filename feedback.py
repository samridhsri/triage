import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "feedback_config.json"
FEEDBACK_LOG_PATH = BASE_DIR / "feedback.jsonl"

DEFAULT_CONFIG = {
    "feedback_enabled": True,
    "max_few_shot_examples": 5,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # Merge with default keys if missing
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception as e:
        logger.error("Error reading feedback config: %s", e)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error("Error saving feedback config: %s", e)


def is_feedback_enabled() -> bool:
    return load_config().get("feedback_enabled", True)


def set_feedback_enabled(enabled: bool) -> None:
    cfg = load_config()
    cfg["feedback_enabled"] = bool(enabled)
    save_config(cfg)


def log_feedback(
    raw_input: str,
    predicted_intents: list,
    corrected_intents: list,
    notes: str = "",
) -> dict:
    """Save a feedback entry recording user corrections."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "raw_input": raw_input,
        "predicted_intents": predicted_intents,
        "corrected_intents": corrected_intents,
        "notes": notes,
    }
    try:
        with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("Saved user feedback entry for input: '%s'", raw_input[:50])
    except Exception as e:
        logger.error("Failed to write feedback log: %s", e)
    return entry


def get_feedback_entries() -> list[dict]:
    """Retrieve all logged feedback entries."""
    if not FEEDBACK_LOG_PATH.exists():
        return []
    entries = []
    try:
        lines = FEEDBACK_LOG_PATH.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.strip():
                entries.append(json.loads(line))
    except Exception as e:
        logger.error("Failed to read feedback log: %s", e)
    return entries


def get_few_shot_prompt(limit: int = 5) -> str:
    """
    Format the most recent feedback corrections into a few-shot exemplars section
    for insertion into the LLM system prompt.
    """
    entries = get_feedback_entries()
    if not entries:
        return ""

    # Select recent entries with corrected_intents
    relevant = [e for e in entries if e.get("corrected_intents") is not None][-limit:]
    if not relevant:
        return ""

    lines = [
        "\n--- USER FEEDBACK CORRECTIONS (FEW-SHOT EXAMPLES) ---",
        "Learn from these previous user corrections when classifying similar inputs:",
    ]

    for idx, item in enumerate(relevant, 1):
        inp = item.get("raw_input", "")
        corr = item.get("corrected_intents", [])
        notes = item.get("notes", "")
        corr_json = json.dumps({"intents": corr})
        entry_str = f"Example {idx}:\n  Input: \"{inp}\"\n  Corrected Intents JSON: {corr_json}"
        if notes:
            entry_str += f"\n  User Correction Note: {notes}"
        lines.append(entry_str)

    lines.append("--- END OF FEEDBACK EXAMPLES ---\n")
    return "\n".join(lines)
