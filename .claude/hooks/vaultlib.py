#!/usr/bin/env python3
"""Reading the learning records: the parts more than one hook needs.

`learn-status.py` renders the records and `obsidian-live.py` times them, and both
have to answer the same two questions -- what is in a note's frontmatter, and
which note is currently open. Those answers were about to exist twice. Two copies
of a parser drift, and a clock that disagrees with the dashboard about which
session is open is worse than either being wrong alone, so they live here once.

Deliberately dependency-free and side-effect-free: it is imported by a hook that
runs on every prompt, so it may not be slow, and it may not fail in a way that
blocks a session.
"""

from datetime import datetime, timedelta
from pathlib import Path

# How long a `paused:` note may stand before it stops being a live break and
# becomes a cut-off. The rule, and why it is elapsed hours rather than a calendar
# day, are in learn/system/records.md under *Closing an open note*. That section
# and this constant must be changed together.
STALE_HOURS = 6


def frontmatter(path):
    """Parse the leading --- block as flat key: value pairs. No YAML dependency.

    Flat is enough: every field the records index on is a scalar, and the one
    list (`nodes:`) is only ever echoed back as text. Indented and `-` lines are
    skipped rather than parsed, so a hand-written block cannot make this raise.
    """
    fields = {}
    path = Path(path)
    if not path.is_file():
        return fields
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return fields
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"')
    return fields


def note_datetime(date_text, time_text, after=None):
    """Combine a note's `date:` with one of its `HH:MM` fields into a local datetime.

    A note keeps the date it was opened on, so a time that lands before `after`
    (normally the note's own `start`) belongs to the following day: a session
    started 23:50 and paused 00:10 is a twenty-minute gap, not a twenty-three-hour
    one. Getting this backwards is the exact failure the elapsed-hours rule in
    records.md exists to avoid, so it is handled here rather than left to whoever
    reads the number.
    """
    try:
        stamp = datetime.strptime("%s %s" % (str(date_text).strip(), str(time_text).strip()),
                                  "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None
    if after is not None and stamp < after:
        stamp += timedelta(days=1)
    return stamp


def section(text, heading):
    """The body of one '## heading' section, up to the next '## ' heading.

    Stops only at another level-2 heading, so a '### nN' subheading (as in every
    session note's Lesson section) stays inside the body rather than truncating
    it. Lives here rather than in one hook because `learn-status.py` reads the
    records' sections and `jev.py` reads the same sections to build its prompts;
    two parsers that disagreed about where a section ends would produce two
    different views of the same file.
    """
    rows, collecting = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if collecting:
                break
            collecting = line[3:].strip().lower().startswith(heading.lower())
            continue
        if collecting:
            rows.append(line)
    return "\n".join(rows).strip()


def session_notes(vault, subject):
    """Every session note for a subject, oldest first, as (path, frontmatter)."""
    folder = Path(vault) / "learn" / "subjects" / str(subject) / "sessions"
    if not folder.is_dir():
        return []
    return [(path, frontmatter(path)) for path in sorted(folder.glob("*.md"))]


def open_session_note(vault, subject):
    """The note a session is currently being written into, or None.

    Open means `end:` is empty, which is the same test `/learn-resume` and the
    dashboard use -- so the clock, the resume branch and the open-note report can
    never disagree about which session is in progress. With more than one open
    note the newest wins and the others are left to the dashboard's open-note
    report: guessing quietly here would hide the very state that report exists to
    surface.
    """
    open_ones = [(path, fields) for path, fields in session_notes(vault, subject)
                 if not fields.get("end")]
    return open_ones[-1] if open_ones else None
