#!/usr/bin/env python3
"""Place a multiple-choice key before display and return the matching log field."""

import argparse
import fcntl
import json
import os
import re
import tempfile
from pathlib import Path

KEY = re.compile(r"\bkey:\s*(\d+)/(\d+)")


def logged_slots(vault, scope, subject):
    if scope == "review":
        files = sorted((vault / "learn/reviews").glob("*.md"))
    else:
        files = sorted((vault / "learn/subjects" / subject / "sessions").glob("*.md"))
    return [int(match.group(1)) for path in files for match in KEY.finditer(path.read_text())]


def allowed(slot, history):
    if history and history[-1] == slot:
        return False
    window = history[-4:] + [slot]
    return window.count(slot) <= 2


def prepare(vault, scope, subject, question, correct, distractors):
    options = [correct, *distractors]
    if len(options) < 3 or len(options) > 26 or any(not option.strip() or " / " in option for option in options):
        raise ValueError("provide 3–26 nonempty options without the evidence separator ' / '")
    if len(set(options)) != len(options) or not question.strip():
        raise ValueError("question must be nonempty and options must be distinct")
    runtime = vault / "learn/.mc-runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "placement.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = runtime / "placement.json"
        try:
            prepared = json.loads(state_path.read_text())
        except FileNotFoundError:
            prepared = []
        history = logged_slots(vault, scope, subject) + [entry["slot"] for entry in prepared]
        candidates = [slot for slot in range(1, len(options) + 1) if allowed(slot, history)]
        if not candidates:
            raise ValueError("no key slot satisfies the current sequence; inspect the logged history")
        slot = min(candidates, key=lambda candidate: (history[-4:].count(candidate), candidate))
        ordered = [*distractors]
        ordered.insert(slot - 1, correct)
        result = {
            "slot": slot,
            "options": ordered,
            "display": question + "\n" + "\n".join(f"{chr(65 + index)}. {option}" for index, option in enumerate(ordered)),
            "evidence": f"key: {slot}/{len(ordered)} — options: " + " / ".join(ordered),
        }
        prepared.append({"scope": scope, "subject": subject, "slot": slot})
        with tempfile.NamedTemporaryFile("w", dir=runtime, delete=False) as temporary:
            json.dump(prepared, temporary)
            temporary_path = temporary.name
        os.replace(temporary_path, state_path)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--scope", choices=("lesson", "review"), required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--correct", required=True)
    parser.add_argument("--distractor", action="append", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.subject):
        parser.error("subject must be a lowercase hyphenated slug")
    print(json.dumps(prepare(args.vault, args.scope, args.subject, args.question,
                             args.correct, args.distractor), ensure_ascii=False))


if __name__ == "__main__":
    main()
