import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import feedback
import llm


class TestFeedbackSystem(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.patch_config = patch("feedback.CONFIG_PATH", Path(self.tmp_dir) / "feedback_config.json")
        self.patch_log = patch("feedback.FEEDBACK_LOG_PATH", Path(self.tmp_dir) / "feedback.jsonl")
        self.mock_config = self.patch_config.start()
        self.mock_log = self.patch_log.start()

    def tearDown(self):
        self.patch_config.stop()
        self.patch_log.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_default_config_creation(self):
        cfg = feedback.load_config()
        self.assertTrue(cfg["feedback_enabled"])
        self.assertEqual(cfg["max_few_shot_examples"], 5)
        self.assertTrue(self.mock_config.exists())

    def test_toggle_feedback(self):
        feedback.set_feedback_enabled(False)
        self.assertFalse(feedback.is_feedback_enabled())

        feedback.set_feedback_enabled(True)
        self.assertTrue(feedback.is_feedback_enabled())

    def test_log_and_retrieve_feedback(self):
        raw = "read chapter 5 and prepare slides"
        pred = [{"type": "Task", "title": "Read chapter 5 and prepare slides"}]
        corr = [
            {"type": "Task", "title": "Read chapter 5"},
            {"type": "Project", "title": "Prepare slides"},
        ]
        notes = "Split into task and project"

        feedback.log_feedback(raw, pred, corr, notes)

        entries = feedback.get_feedback_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["raw_input"], raw)
        self.assertEqual(entries[0]["corrected_intents"], corr)
        self.assertEqual(entries[0]["notes"], notes)

    def test_get_few_shot_prompt(self):
        self.assertEqual(feedback.get_few_shot_prompt(), "")

        raw = "email boss about budget"
        corr = [{"type": "Task", "title": "Email boss about budget", "priority": "High"}]
        feedback.log_feedback(raw, [], corr, "Needs high priority tag")

        prompt_part = feedback.get_few_shot_prompt()
        self.assertIn("USER FEEDBACK CORRECTIONS", prompt_part)
        self.assertIn("email boss about budget", prompt_part)
        self.assertIn("Email boss about budget", prompt_part)
        self.assertIn("Needs high priority tag", prompt_part)

    def test_llm_prompt_few_shot_injection(self):
        raw = "organize team offsite"
        corr = [{"type": "Project", "title": "Organize team offsite"}]
        feedback.log_feedback(raw, [], corr, "Multi-step effort")

        with patch("llm.is_feedback_enabled", return_value=True):
            with patch.object(llm.client.models, "generate_content") as mock_gen:
                mock_response = unittest.mock.MagicMock()
                mock_response.text = '{"intents": []}'
                mock_gen.return_value = mock_response

                llm.split_intents("organize team offsite")

                mock_gen.assert_called_once()
                call_args = mock_gen.call_args[1]
                user_parts = call_args["contents"][0]["parts"]
                system_prompt_text = user_parts[0]["text"]

                self.assertIn("USER FEEDBACK CORRECTIONS", system_prompt_text)
                self.assertIn("organize team offsite", system_prompt_text)

    def test_llm_prompt_no_few_shot_when_disabled(self):
        raw = "organize team offsite"
        corr = [{"type": "Project", "title": "Organize team offsite"}]
        feedback.log_feedback(raw, [], corr, "Multi-step effort")

        with patch("llm.is_feedback_enabled", return_value=False):
            with patch.object(llm.client.models, "generate_content") as mock_gen:
                mock_response = unittest.mock.MagicMock()
                mock_response.text = '{"intents": []}'
                mock_gen.return_value = mock_response

                llm.split_intents("organize team offsite")

                mock_gen.assert_called_once()
                call_args = mock_gen.call_args[1]
                user_parts = call_args["contents"][0]["parts"]
                system_prompt_text = user_parts[0]["text"]

                self.assertNotIn("USER FEEDBACK CORRECTIONS", system_prompt_text)


if __name__ == "__main__":
    unittest.main()
