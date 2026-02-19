import json
import logging
import re
import sys
import unittest
from unittest.mock import patch

from llm import split_intents
from notion import DEAD_LETTER_PATH, write_to_notion
from schema import INTENT_SCHEMA

_THIS_MODULE = __name__
logger = logging.getLogger(__name__)


def _validate_intent(intent: dict) -> dict | None:
    intent_type = intent.get("type")
    schema = INTENT_SCHEMA.get(intent_type)
    if schema is None:
        logger.warning('REJECTED Unknown intent type: "%s"', intent_type)
        return None

    title = (intent.get("title") or "").strip()
    if not title:
        logger.warning("REJECTED %s has empty title", intent_type)
        return None

    structured_fields = {}
    for field_name, rules in schema["valid_fields"].items():
        value = intent.get(field_name)

        if value is None:
            structured_fields[field_name] = None
            continue

        if "allowed" in rules and value not in rules["allowed"]:
            logger.warning('REJECTED %s has invalid %s: "%s"', intent_type, field_name, value)
            return None

        if "pattern" in rules and not re.match(rules["pattern"], str(value)):
            logger.warning('REJECTED %s has malformed %s: "%s"', intent_type, field_name, value)
            return None

        structured_fields[field_name] = value

    return {
        "type": intent_type,
        "title": title,
        "structured_fields": structured_fields,
    }


def triage(user_input: str) -> None:
    """
    Phase 2 router: decompose raw input into typed intents, validate each,
    and write to the appropriate Notion database.
    """
    intents = split_intents(user_input)

    logger.info('INPUT: "%s"', user_input[:120])

    if not intents:
        logger.warning('REJECTED No classifiable intents in: "%s"', user_input[:80])
        return

    for intent in intents:
        item = _validate_intent(intent)
        if item is None:
            continue

        write_to_notion(item, user_input)
        logger.info('OK %s created: "%s"', item["type"], item["title"])


def flush_dead_letter() -> None:
    if not DEAD_LETTER_PATH.exists():
        logger.info("Dead-letter queue is empty.")
        return

    lines = DEAD_LETTER_PATH.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    if not entries:
        logger.info("Dead-letter queue is empty.")
        return

    logger.info("Flushing %d dead-letter item(s)...", len(entries))
    # Clear the file before replaying — failures will re-append themselves
    DEAD_LETTER_PATH.write_text("", encoding="utf-8")

    ok = failed = 0
    for entry in entries:
        try:
            write_to_notion(entry["item"], entry["raw_input"])
            ok += 1
        except Exception:
            failed += 1  # write_to_notion already re-appended to DLQ

    logger.info("DLQ flush complete: %d OK, %d re-queued", ok, failed)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateTask(unittest.TestCase):

    def test_valid_full(self):
        result = _validate_intent({"type": "Task", "title": "Write report", "priority": "High", "due_date": "2026-02-15"})
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Task")
        self.assertEqual(result["title"], "Write report")
        self.assertEqual(result["structured_fields"]["priority"], "High")
        self.assertEqual(result["structured_fields"]["due_date"], "2026-02-15")

    def test_valid_null_optional_fields(self):
        result = _validate_intent({"type": "Task", "title": "Buy groceries", "priority": None, "due_date": None})
        self.assertIsNotNone(result)
        self.assertIsNone(result["structured_fields"]["priority"])
        self.assertIsNone(result["structured_fields"]["due_date"])

    def test_title_whitespace_only_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Task", "title": "   ", "priority": None, "due_date": None}))

    def test_invalid_priority_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Task", "title": "Do something", "priority": "Urgent", "due_date": None}))

    def test_malformed_date_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Task", "title": "Do something", "priority": None, "due_date": "next Friday"}))

    def test_all_valid_priorities_accepted(self):
        for p in ("High", "Medium", "Low"):
            with self.subTest(priority=p):
                self.assertIsNotNone(_validate_intent({"type": "Task", "title": "Do something", "priority": p, "due_date": None}))


class TestValidateProject(unittest.TestCase):

    def test_valid_full(self):
        result = _validate_intent({"type": "Project", "title": "Launch website", "success_criteria": "1000 signups", "review_frequency": "Weekly"})
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Project")
        self.assertEqual(result["structured_fields"]["review_frequency"], "Weekly")
        self.assertEqual(result["structured_fields"]["success_criteria"], "1000 signups")

    def test_valid_null_optional_fields(self):
        result = _validate_intent({"type": "Project", "title": "Redesign dashboard", "success_criteria": None, "review_frequency": None})
        self.assertIsNotNone(result)

    def test_empty_title_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Project", "title": "", "success_criteria": None, "review_frequency": None}))

    def test_invalid_review_frequency_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Project", "title": "Some project", "review_frequency": "Daily"}))

    def test_valid_review_frequencies_accepted(self):
        for freq in ("Weekly", "Monthly"):
            with self.subTest(freq=freq):
                self.assertIsNotNone(_validate_intent({"type": "Project", "title": "Some project", "review_frequency": freq}))


class TestValidateIdea(unittest.TestCase):

    def test_valid_full(self):
        result = _validate_intent({"type": "Idea", "title": "AI writing assistant", "category": "Product", "potential_impact": "High"})
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Idea")
        self.assertEqual(result["structured_fields"]["category"], "Product")
        self.assertEqual(result["structured_fields"]["potential_impact"], "High")

    def test_valid_null_optional_fields(self):
        result = _validate_intent({"type": "Idea", "title": "Use dark mode", "category": None, "potential_impact": None})
        self.assertIsNotNone(result)

    def test_empty_title_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Idea", "title": "", "category": None, "potential_impact": None}))

    def test_invalid_potential_impact_rejected(self):
        self.assertIsNone(_validate_intent({"type": "Idea", "title": "Cool idea", "potential_impact": "Huge"}))


class TestTriage(unittest.TestCase):

    def test_no_intents_nothing_written(self):
        with patch(f"{_THIS_MODULE}.split_intents", return_value=[]):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage("hmm")
                mock_write.assert_not_called()

    def test_single_valid_task_written(self):
        intents = [{"type": "Task", "title": "Submit report", "priority": "High", "due_date": "2026-02-14"}]
        with patch(f"{_THIS_MODULE}.split_intents", return_value=intents):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage("Submit report by tomorrow, high priority")
                mock_write.assert_called_once()
                item = mock_write.call_args[0][0]
                self.assertEqual(item["type"], "Task")
                self.assertEqual(item["title"], "Submit report")
                self.assertEqual(item["structured_fields"]["priority"], "High")

    def test_mixed_intents_all_written(self):
        intents = [
            {"type": "Task",    "title": "Send email",       "priority": None, "due_date": None},
            {"type": "Project", "title": "Build portfolio",  "success_criteria": None, "review_frequency": None},
            {"type": "Idea",    "title": "Try serverless",   "category": None, "potential_impact": None},
        ]
        with patch(f"{_THIS_MODULE}.split_intents", return_value=intents):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage("Send email, build portfolio, try serverless")
                self.assertEqual(mock_write.call_count, 3)
                types_written = [c[0][0]["type"] for c in mock_write.call_args_list]
                self.assertEqual(types_written, ["Task", "Project", "Idea"])

    def test_unknown_intent_type_skipped(self):
        intents = [{"type": "Reminder", "title": "Call dentist"}]
        with patch(f"{_THIS_MODULE}.split_intents", return_value=intents):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage("Call dentist next week")
                mock_write.assert_not_called()

    def test_invalid_task_not_written(self):
        intents = [{"type": "Task", "title": "", "priority": None, "due_date": None}]
        with patch(f"{_THIS_MODULE}.split_intents", return_value=intents):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage("something vague")
                mock_write.assert_not_called()

    def test_invalid_intent_does_not_block_valid_intent(self):
        intents = [
            {"type": "Task", "title": "",            "priority": None, "due_date": None},  # invalid
            {"type": "Task", "title": "Fix login bug", "priority": None, "due_date": None},  # valid
        ]
        with patch(f"{_THIS_MODULE}.split_intents", return_value=intents):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage("some input")
                mock_write.assert_called_once()
                self.assertEqual(mock_write.call_args[0][0]["title"], "Fix login bug")

    def test_raw_input_forwarded_to_writer(self):
        raw = "Finish the report by Friday, high priority"
        intents = [{"type": "Task", "title": "Finish report", "priority": "High", "due_date": "2026-02-13"}]
        with patch(f"{_THIS_MODULE}.split_intents", return_value=intents):
            with patch(f"{_THIS_MODULE}.write_to_notion") as mock_write:
                triage(raw)
                self.assertEqual(mock_write.call_args[0][1], raw)


if __name__ == "__main__":
    fmt = logging.Formatter(
        "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler("triage.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(fh)
    logging.root.addHandler(sh)

    logger.info("main.py started, argv: %s", sys.argv)
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "--flush":
                flush_dead_letter()
            else:
                triage(sys.argv[1])
            # print("Received input:", sys.argv[1])
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
    finally:
        input("\nPress Enter to close...")

