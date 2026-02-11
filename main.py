import re
import unittest
from unittest.mock import patch

from llm import split_intents
from notion import write_to_notion

_THIS_MODULE = __name__

VALID_PRIORITIES = {"High", "Medium", "Low"}
VALID_REVIEW_FREQS = {"Weekly", "Monthly"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_task(intent: dict) -> dict | None:
    """Apply Phase 1 validation rules to a Task intent."""
    title = (intent.get("title") or "").strip()
    if not title:
        print("[REJECTED] Task has empty title")
        return None

    priority = intent.get("priority")
    if priority is not None and priority not in VALID_PRIORITIES:
        print(f'[REJECTED] Task has unknown priority: "{priority}"')
        return None

    due_date = intent.get("due_date")
    if due_date is not None and not _DATE_RE.match(str(due_date)):
        print(f'[REJECTED] Task has malformed due date: "{due_date}"')
        return None

    return {
        "type": "Task",
        "title": title,
        "structured_fields": {
            "priority": priority,
            "due_date": due_date,
        },
    }


def _validate_project(intent: dict) -> dict | None:
    title = (intent.get("title") or "").strip()
    if not title:
        print("[REJECTED] Project has empty title")
        return None

    review_frequency = intent.get("review_frequency")
    if review_frequency is not None and review_frequency not in VALID_REVIEW_FREQS:
        print(f'[REJECTED] Project has unknown review_frequency: "{review_frequency}"')
        return None

    return {
        "type": "Project",
        "title": title,
        "structured_fields": {
            "success_criteria": intent.get("success_criteria"),
            "review_frequency": review_frequency,
        },
    }


def _validate_idea(intent: dict) -> dict | None:
    title = (intent.get("title") or "").strip()
    if not title:
        print("[REJECTED] Idea has empty title")
        return None

    potential_impact = intent.get("potential_impact")
    if potential_impact is not None and potential_impact not in VALID_PRIORITIES:
        print(f'[REJECTED] Idea has unknown potential_impact: "{potential_impact}"')
        return None

    return {
        "type": "Idea",
        "title": title,
        "structured_fields": {
            "category": intent.get("category"),
            "potential_impact": potential_impact,
        },
    }


_VALIDATORS = {
    "Task": _validate_task,
    "Project": _validate_project,
    "Idea": _validate_idea,
}


def triage(user_input: str) -> None:
    """
    Phase 2 router: decompose raw input into typed intents, validate each,
    and write to the appropriate Notion database.
    """
    intents = split_intents(user_input)

    if not intents:
        print(f'[REJECTED] No classifiable intents in: "{user_input[:80]}"')
        return

    for intent in intents:
        intent_type = intent.get("type")
        validator = _VALIDATORS.get(intent_type)

        if validator is None:
            print(f'[REJECTED] Unknown intent type: "{intent_type}"')
            continue

        item = validator(intent)
        if item is None:
            continue

        write_to_notion(item, user_input)
        print(f'[OK] {item["type"]} created: "{item["title"]}"')


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateTask(unittest.TestCase):

    def test_valid_full(self):
        result = _validate_task({"title": "Write report", "priority": "High", "due_date": "2026-02-15"})
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Task")
        self.assertEqual(result["title"], "Write report")
        self.assertEqual(result["structured_fields"]["priority"], "High")
        self.assertEqual(result["structured_fields"]["due_date"], "2026-02-15")

    def test_valid_null_optional_fields(self):
        result = _validate_task({"title": "Buy groceries", "priority": None, "due_date": None})
        self.assertIsNotNone(result)
        self.assertIsNone(result["structured_fields"]["priority"])
        self.assertIsNone(result["structured_fields"]["due_date"])

    def test_title_whitespace_only_rejected(self):
        self.assertIsNone(_validate_task({"title": "   ", "priority": None, "due_date": None}))

    def test_invalid_priority_rejected(self):
        self.assertIsNone(_validate_task({"title": "Do something", "priority": "Urgent", "due_date": None}))

    def test_malformed_date_rejected(self):
        self.assertIsNone(_validate_task({"title": "Do something", "priority": None, "due_date": "next Friday"}))

    def test_all_valid_priorities_accepted(self):
        for p in ("High", "Medium", "Low"):
            with self.subTest(priority=p):
                self.assertIsNotNone(_validate_task({"title": "Do something", "priority": p, "due_date": None}))


class TestValidateProject(unittest.TestCase):

    def test_valid_full(self):
        result = _validate_project({"title": "Launch website", "success_criteria": "1000 signups", "review_frequency": "Weekly"})
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Project")
        self.assertEqual(result["structured_fields"]["review_frequency"], "Weekly")
        self.assertEqual(result["structured_fields"]["success_criteria"], "1000 signups")

    def test_valid_null_optional_fields(self):
        result = _validate_project({"title": "Redesign dashboard", "success_criteria": None, "review_frequency": None})
        self.assertIsNotNone(result)

    def test_empty_title_rejected(self):
        self.assertIsNone(_validate_project({"title": "", "success_criteria": None, "review_frequency": None}))

    def test_invalid_review_frequency_rejected(self):
        self.assertIsNone(_validate_project({"title": "Some project", "review_frequency": "Daily"}))

    def test_valid_review_frequencies_accepted(self):
        for freq in ("Weekly", "Monthly"):
            with self.subTest(freq=freq):
                self.assertIsNotNone(_validate_project({"title": "Some project", "review_frequency": freq}))


class TestValidateIdea(unittest.TestCase):

    def test_valid_full(self):
        result = _validate_idea({"title": "AI writing assistant", "category": "Product", "potential_impact": "High"})
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Idea")
        self.assertEqual(result["structured_fields"]["category"], "Product")
        self.assertEqual(result["structured_fields"]["potential_impact"], "High")

    def test_valid_null_optional_fields(self):
        result = _validate_idea({"title": "Use dark mode", "category": None, "potential_impact": None})
        self.assertIsNotNone(result)

    def test_empty_title_rejected(self):
        self.assertIsNone(_validate_idea({"title": "", "category": None, "potential_impact": None}))

    def test_invalid_potential_impact_rejected(self):
        self.assertIsNone(_validate_idea({"title": "Cool idea", "potential_impact": "Huge"}))


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
    # unittest.main()
    triage("Finish ML assignment by Friday and think about an AI music startup")
