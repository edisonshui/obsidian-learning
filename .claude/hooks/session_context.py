"""Shared startup index; full learning state is loaded after subject selection."""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from vaultlib import frontmatter


def learn_status():
    """learn-status.py as a module; its file name has a hyphen, so no plain import."""
    spec = importlib.util.spec_from_file_location("learn_status", Path(__file__).with_name("learn-status.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_context(vault, subject=None, host="claude"):
    status = Path(__file__).with_name("learn-status.py")
    command = [sys.executable, str(status), "--vault", str(vault)]
    refresh = subprocess.run(command + ["--quiet"], cwd=vault, text=True,
                             capture_output=True, check=False)
    lines = ["## Learning vault session start", "Now: " + datetime.now().astimezone().strftime(
        "%A %Y-%m-%d %H:%M %Z"), ""]
    if refresh.returncode:
        lines += ["Dashboard refresh failed: " + refresh.stderr.strip()[:300], ""]
    # The one block the agent shows the learner as it stands; everything after
    # it is for the agent alone.
    try:
        module = learn_status()
        now = datetime.now()
        loaded, _ = module.load_subjects(vault, now)
        lines += module.startup_block(module.rank_inputs(loaded), module.note_inputs(loaded),
                                      module.rewards_setting(vault)[0], now.date(),
                                      selected=subject, host=host) + [""]
    except Exception as error:  # the index below still lets the agent work
        lines += ["Startup block failed: %s" % error, ""]
    notes = subprocess.run(command + ["--open-notes", "--host", host], cwd=vault, text=True,
                           capture_output=True, check=False)
    if notes.stdout.strip():
        lines += ["Unfinished session notes:", notes.stdout.strip(),
                  "Read the closing rule in learn/system/records.md before teaching.", ""]
    elif notes.returncode:
        lines += ["Open-note check failed; inspect the selected subject's latest session note.", ""]

    subjects = vault / "learn/subjects"
    folders = sorted(path for path in subjects.iterdir() if path.is_dir()) if subjects.is_dir() else []
    for folder in folders:
        fields = frontmatter(folder / "record.md")
        lines.append(f"- {folder.name}: {fields.get('title', folder.name)} | "
                     f"{fields.get('status', 'unknown')} | last: {fields.get('last_session', 'unknown')} | "
                     f"next: {fields.get('next', 'read record.md')}")
    if not folders:
        lines.append("No subjects yet. Offer learn-start <subject>.")
    selected = next((folder for folder in folders if folder.name == subject), None)
    if selected:
        resume = selected / "resume.md"
        lines += ["", f"Selected subject: {selected.name}"]
        if resume.is_file():
            lines += [f"learn/subjects/{selected.name}/resume.md:", resume.read_text().strip()]
        else:
            lines.append("Resume missing; recover state from record.md, plan.md, and the latest session note.")
    preferences = vault / "learn/me/preferences.md"
    if preferences.is_file():
        text = preferences.read_text()
        marker = "## Operational summary\n"
        if marker in text:
            summary = text.split(marker, 1)[1].split("\n## ", 1)[0].strip()
            lines += ["", "Operational preferences:", summary]
        else:
            lines += ["", "Read learn/me/preferences.md before teaching; operational summary is missing."]
    else:
        lines += ["", "Learner preferences unavailable; confirm preferences before teaching."]
    lines += ["", "Before teaching: read learn/system/tutor.md and learn/system/workflow.md.",
              "After selection: read learn/subjects/<slug>/resume.md, record.md, plan.md, and the latest sessions/ note in full.",
              "Read learn/system/records.md before writing learning state.",
              ("Continue the selected subject only when the learner requests it."
               if selected else "Ask which subject to resume or start before teaching.")]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    args = parser.parse_args()
    vault = args.vault.resolve()
    # Claude's SessionStart payload identifies this conversation. Never borrow
    # another conversation's selection from a global active-session pointer.
    subject = None
    try:
        payload = json.load(sys.stdin)
        sid = payload.get("session_id", "")
        if isinstance(sid, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", sid):
            state = json.loads((vault / ".claude/obsidian-live" / (sid + ".json")).read_text())
            subject = state.get("subject")
    except (OSError, ValueError, AttributeError):
        pass
    print(start_context(vault, subject))
