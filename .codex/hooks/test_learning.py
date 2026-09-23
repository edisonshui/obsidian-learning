"""Behavior checks for the Codex hook adapter; no real learning records touched."""

import importlib.util
import json
import os
import subprocess
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

    def test_start_defers_resumes_but_keeps_index_and_open_note_warning(self):
        for slug in ("oop", "pointers"):
            (self.vault / f"learn/subjects/{slug}/resume.md").write_text(
                f"---\n---\n\nPrivate {slug} resume detail.\n")
        outputs = [self.event("SessionStart", "start"), subprocess.check_output(
            ["bash", str(HOOK.parents[2] / ".claude/hooks/session-start.sh")],
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.vault)},
            input='{"session_id":"fresh"}', text=True)]
        for output in outputs:
            with self.subTest(output=output[:40]):
                self.assertNotIn("Private oop resume detail", output)
                self.assertNotIn("Private pointers resume detail", output)
                for term in ("oop", "pointers", "active", "continue", "2026-09-18",
                             "Unfinished session notes", "learn/system/records.md",
                             "learn/system/tutor.md", "record.md", "plan.md"):
                    self.assertIn(term, output)

    def test_start_recovers_only_this_conversations_selected_full_resume(self):
        detail = "Selected detail.\n" * 250 + "Uncertain: limit conclusion. Next: ask for proof."
        (self.vault / "learn/subjects/oop/resume.md").write_text("---\n---\n\n" + detail)
        (self.vault / "learn/subjects/pointers/resume.md").write_text("Other resume secret.")
        self.event("UserPromptSubmit", "t1", prompt="$learn-resume oop")
        claude_state = self.vault / ".claude/obsidian-live/test-session.json"
        claude_state.parent.mkdir(parents=True)
        claude_state.write_text(json.dumps({"subject": "oop"}))
        def claude(sid):
            return subprocess.check_output(
                ["bash", str(HOOK.parents[2] / ".claude/hooks/session-start.sh")],
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.vault)},
                input=json.dumps({"session_id": sid}), text=True)
        for output in (self.event("SessionStart", "resume"), claude("test-session")):
            self.assertIn(detail, output)
            self.assertNotIn("Other resume secret", output)
        for output in (learning.hook(self.vault, {"session_id": "new-session",
                       "hook_event_name": "SessionStart"}), claude("new-session")):
            self.assertNotIn("Selected detail", output)

    def test_start_prints_operational_preferences_without_promoting_candidates(self):
        preferences = self.vault / "learn/me/preferences.md"
        preferences.parent.mkdir(parents=True)
        preferences.write_text("# Preferences\n\n## Stated\nStated history.\n\n"
                               "## Operational summary\nOne step then check. Resend in ASCII.\n\n"
                               "## Observed\nDated evidence.\n\n## Candidates\nUnconfirmed preference.\n")
        outputs = [self.event("SessionStart", "start"), subprocess.check_output(
            ["bash", str(HOOK.parents[2] / ".claude/hooks/session-start.sh")],
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.vault)}, input="{}", text=True)]
        for output in outputs:
            self.assertIn("One step then check. Resend in ASCII.", output)
            self.assertNotIn("Dated evidence", output)
            self.assertNotIn("Unconfirmed preference", output)

    def test_start_prompt_reply_clock_and_subject_switch(self):
        start = self.event("SessionStart", "start")
        self.assertIn("oop", start)
        self.assertIn("pointers", start)
        dashboard = (self.vault / "learn/Dashboard.md").read_text()
        self.assertIn("Learning dashboard", dashboard)
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

    def test_selected_prompt_without_reply_has_visible_status(self):
        self.event("UserPromptSubmit", "t1", prompt="$learn-resume oop")
        log = (self.vault / "learn/subjects/oop/codex-log.md").read_text()
        self.assertIn("Completed-turn summary", log)
        self.assertIn("final reply only", log)
        self.assertIn("Reply not captured for this prompt", log)
        self.event("Stop", "t1", last_assistant_message="Final reply")
        log = (self.vault / "learn/subjects/oop/codex-log.md").read_text()
        self.assertIn("Final reply", log)
        self.assertNotIn("Reply not captured for this prompt", log)

    def test_unselected_prompt_stays_out_of_subject_log(self):
        self.event("UserPromptSubmit", "t1", prompt="Hello")
        self.assertFalse((self.vault / "learn/subjects/oop/codex-log.md").exists())

    def test_transcript_includes_intermediate_message_once(self):
        transcript = self.vault / "turn.jsonl"
        transcript.write_text("\n".join(json.dumps(row) for row in [
            {"type": "session_meta", "payload": {"session_id": "test-session"}},
            {"type": "event_msg", "timestamp": "2026-09-22T12:00:00Z", "payload": {
                "type": "item_completed", "turn_id": "t1", "item": {"type": "AgentMessage",
                "content": [{"type": "Text", "text": "Intermediate $x^2$"}]}}},
            {"type": "event_msg", "timestamp": "2026-09-22T12:01:00Z", "payload": {
                "type": "item_completed", "turn_id": "t1", "item": {"type": "AgentMessage",
                "content": [{"type": "Text", "text": "Final reply"}]}}},
        ]) + "\n")
        self.event("UserPromptSubmit", "t1", prompt="$learn-resume oop")
        self.event("Stop", "t1", transcript_path=str(transcript), last_assistant_message="Final reply")
        log = (self.vault / "learn/subjects/oop/codex-log.md").read_text()
        self.assertIn("Transcript messages", log)
        self.assertIn("Intermediate $x^2$", log)
        self.assertEqual(log.count("Final reply"), 1)
        self.assertNotIn("Reply not captured for this prompt", log)


if __name__ == "__main__":
    unittest.main()
