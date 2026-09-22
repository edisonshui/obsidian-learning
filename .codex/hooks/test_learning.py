"""Behavior checks for the Codex hook adapter; no real learning records touched."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name("learning.py")
spec = importlib.util.spec_from_file_location("codex_learning", HOOK)
learning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learning)


class LearningHookTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = Path(self.temp.name)
        for slug in ("oop", "pointers"):
            folder = self.vault / "learn" / "subjects" / slug
            (folder / "sessions").mkdir(parents=True)
            (folder / "record.md").write_text(
                f"---\ntitle: {slug}\nstatus: active\nlast_session: 2026-09-18\nsessions: 1\nnext: continue\n---\n\n# Record\n")
            (folder / "plan.md").write_text("---\n---\n\n# Plan\n")
            (folder / "resume.md").write_text("---\n---\n\nResume here.\n")
            (folder / "sessions" / "2026-09-18-s01.md").write_text(
                "---\ndate: 2026-09-18\nstart: 10:00\nend: \n---\n")

    def event(self, kind, turn, **extra):
        return learning.hook(self.vault, {
            "session_id": "test-session", "hook_event_name": kind,
            "turn_id": turn, "model": "test-model", **extra,
        })

    def test_start_prompt_reply_clock_and_subject_switch(self):
        start = self.event("SessionStart", "start")
        self.assertIn("oop", start)
        self.assertIn("pointers", start)
        dashboard = (self.vault / "learn/Dashboard.md").read_text()
        self.assertIn("Claude log", dashboard)
        self.assertIn("Codex log", dashboard)
        self.event("UserPromptSubmit", "t1", prompt="$learn-resume oop")
        self.event("Stop", "t1", last_assistant_message="OOP reply")
        self.event("Stop", "t1", last_assistant_message="OOP reply")
        oop_log = (self.vault / "learn/subjects/oop/codex-log.md").read_text()
        self.assertEqual(oop_log.count("OOP reply"), 1)
        self.assertIn("active_minutes: 0", learning.shared.clock_report(
            self.vault, self.vault / "learn/.codex-runtime", "oop"))

        self.event("UserPromptSubmit", "t2", prompt="$learn-resume pointers")
        self.event("Stop", "t2", last_assistant_message="Pointers reply")
        pointers_log = (self.vault / "learn/subjects/pointers/codex-log.md").read_text()
        self.assertIn("Pointers reply", pointers_log)
        self.assertNotIn("OOP reply", pointers_log)
        self.assertNotIn("Pointers reply", (self.vault / "learn/subjects/oop/codex-log.md").read_text())

    def test_select_routes_natural_prompt(self):
        self.event("SessionStart", "start")
        self.event("UserPromptSubmit", "t1", prompt="Teach me about classes")
        self.assertIn("Codex log selected", learning.select(self.vault, "oop"))
        self.event("Stop", "t1", last_assistant_message="Let's begin")
        log = (self.vault / "learn/subjects/oop/codex-log.md").read_text()
        self.assertIn("Teach me about classes", log)
        self.assertIn("Let's begin", log)


if __name__ == "__main__":
    unittest.main()
