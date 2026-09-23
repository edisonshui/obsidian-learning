"""Public CLI checks for pre-display multiple-choice placement."""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SCRIPT = Path(__file__).with_name("mc-preflight.py")


class MultipleChoicePreflightTest(unittest.TestCase):
    def test_lesson_starts_after_logged_subject_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            sessions = vault / "learn/subjects/oop/sessions"
            sessions.mkdir(parents=True)
            (sessions / "2026-09-22-s01.md").write_text("key: 2/3 — options: a / b / c\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--vault", str(vault), "--scope", "lesson",
                 "--subject", "oop", "--question", "Which?", "--correct", "yes",
                 "--distractor", "no", "--distractor", "maybe"],
                text=True, capture_output=True, check=True,
            )
            self.assertNotEqual(json.loads(result.stdout)["slot"], 2)

    def test_six_review_questions_rotate_and_preserve_displayed_options(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            reviews = vault / "learn/reviews"
            reviews.mkdir(parents=True)
            (reviews / "2026-09-22-r01.md").write_text("key: 1/3 — options: old a / old b / old c\n")
            slots = [1]
            for number in range(6):
                correct = f"correct {number}"
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--vault", str(vault), "--scope", "review",
                     "--subject", "oop", "--question", f"Question {number}?", "--correct", correct,
                     "--distractor", f"wrong a {number}", "--distractor", f"wrong b {number}"],
                    text=True, capture_output=True, check=True,
                )
                item = json.loads(result.stdout)
                slots.append(item["slot"])
                self.assertEqual(item["options"][item["slot"] - 1], correct)
                self.assertEqual(item["evidence"],
                                 f"key: {item['slot']}/3 — options: " + " / ".join(item["options"]))
                self.assertEqual(item["display"].splitlines()[0], f"Question {number}?")
                for index, option in enumerate(item["options"]):
                    self.assertIn(f"{chr(65 + index)}. {option}", item["display"])
            self.assertTrue(all(left != right for left, right in zip(slots, slots[1:])))
            self.assertTrue(all(max(window.count(slot) for slot in window) <= 2
                                for window in (slots[i:i + 5] for i in range(len(slots) - 4))))

    def test_lesson_ignores_review_placements_and_drops_legacy_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            runtime = vault / "learn/.mc-runtime"
            runtime.mkdir(parents=True)
            review = {"scope": "review", "subject": "oop", "slot": 1,
                      "evidence": "key: 1/3 — options: r / s / t",
                      "prepared": datetime.now().isoformat(timespec="seconds")}
            legacy = {"scope": "lesson", "subject": "oop", "slot": 1}
            (runtime / "placement.json").write_text(json.dumps([legacy, review]))
            item = json.loads(prepare(vault, "lesson", "Which?", "yes").stdout)
            self.assertEqual(item["slot"], 1)
            written = json.loads((runtime / "placement.json").read_text())
            self.assertEqual(written[0], review)
            self.assertEqual(len(written), 2)
            self.assertEqual({key: written[1][key] for key in ("scope", "subject", "slot", "evidence")},
                             {"scope": "lesson", "subject": "oop", "slot": 1, "evidence": item["evidence"]})
            datetime.fromisoformat(written[1]["prepared"])

    def test_placement_copied_into_a_note_leaves_the_file_and_counts_once(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            reviews = vault / "learn/reviews"
            reviews.mkdir(parents=True)
            first = json.loads(prepare(vault, "review", "First?", "one").stdout)
            (reviews / "2026-09-23-r01.md").write_text(
                "- Q: First? / A: one / Verdict: correct. `%s`\n" % first["evidence"])
            second = json.loads(prepare(vault, "review", "Second?", "two").stdout)
            self.assertNotEqual(second["slot"], first["slot"])
            written = json.loads((vault / "learn/.mc-runtime/placement.json").read_text())
            self.assertEqual([entry["evidence"] for entry in written], [second["evidence"]])


def prepare(vault, scope, question, correct):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--vault", str(vault), "--scope", scope, "--subject", "oop",
         "--question", question, "--correct", correct, "--distractor", "no", "--distractor", "maybe"],
        text=True, capture_output=True, check=True,
    )


if __name__ == "__main__":
    unittest.main()
