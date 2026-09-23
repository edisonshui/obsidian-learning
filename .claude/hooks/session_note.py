#!/usr/bin/env python3
"""Reading one session note or review note: the one parser for the format.

The format used to be parsed by separate regexes in `learn-status.py`, `jev.py`
and `mc-preflight.py`, and they disagreed on live data: G2 found four node
entries in `pointers-and-references` s01 where J5 found five, and J5 judged a
`### n7` that G2 never saw because it was filed under *Misconception
candidates*. Two readers of one file that disagree produce two records of one
session, so the format is read here once.

Facts only. `parse` says what is in the note -- its node entries and where they
are filed, its logged checks in one normalised shape, every key field, whether
it is open -- plus a `malformed` list of lines it recognised but could not
read. It decides nothing: the rules, thresholds and warning text, with their
`tutor.md` and `records.md` citations, stay in the gates (`learn-status.py`)
and the judges (`jev.py`), so a rule is never split between a reader and its
enforcer. The one exception is the MC slot-rotation rule, which gate G4 and
`mc-preflight.py` share, so it lives in `slot_rotation.py` with its thresholds.

`parse` takes a string so tests never touch a live note; `read` is the thin
wrapper for a path. Dependency-free for the same reason `vaultlib` is.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

from vaultlib import STALE_HOURS, note_datetime, section, split_frontmatter

NODE_ID = re.compile(r"\bn\d+\b")

# A node entry: `### nN` and whatever follows on its line. A repeated id (`### n7
# continued`) is a second entry for the same node, not a defect.
ENTRY = re.compile(r"^###\s+(n\d+)\b(.*)$")

# A logged check is `Q: <question> / A: <answer> / Verdict: <verdict>`, with the
# separators varying by note (`/`, an arrow, or plain whitespace) and the Q
# sometimes numbered or annotated (`Q1:`, `Q (free response):`). Everything from
# `Q:` up to the answer or verdict marker is the question as the learner saw it,
# options included when they were logged inline.
CHECK_Q = re.compile(
    r"\bQ\s*\d*\s*(?:\([^)]*\))?\s*:\s*"
    r"(?P<text>.+?)"
    r"(?=(?:\s*[/→])?\s+A(?:\s*\([^)]*\))?\s*:"
    r"|(?:\s*[/→])?\s*Verdict\s*:"
    r"|$)"
)

# The two legacy formats that carry option text. Format A: `(options: x / y /
# z)`, the correct one identified by matching the logged answer. Format B:
# `(options, slot order: x / y [correct, slot N] / z)`, marked inline.
LEGACY = re.compile(
    r'Q:\s*"(?P<q>[^"]+)"\s*'
    r'\(options(?:,\s*slot order)?\s*:\s*(?P<opts>[^)]+)\)\s*'
    r'/\s*A:\s*"(?P<a>[^"]+)"'
)
SLOT_MARK = re.compile(r"\s*\[correct,\s*slot\s*\d+\]\s*$")

# The key field, the only format written going forward:
#
#   key: 2/3 — options: `*p = b` / `p = &b` / `&p = b`
#
# `fence` is the code span a review note wraps the field in, so its closing
# backticks can be kept out of the last option.
KEY = re.compile(r"(?P<fence>`*)\bkey:\s*(?P<slot>\d+)\s*/\s*(?P<count>\d+)")
OPTIONS = re.compile(r"\s*[—–-]\s*options:\s*(?P<opts>\S.*?)\s*$")


@dataclass(frozen=True)
class NodeEntry:
    node: str
    title: str         # the rest of the `### nN` line
    section: str       # the `## ` heading it is filed under, "" if none
    line: int          # 1-based, in the whole note
    body: str          # up to the next node entry or `## ` heading
    has_diagram: bool  # carries the canonical `**Diagram.**` marker
    has_check: bool    # carries `**Check.**`


@dataclass(frozen=True)
class LoggedCheck:
    line: int
    text: str             # the question as the learner saw it (J1's probe)
    question: str         # the question without an inline option list
    options: tuple = ()   # in slot order; empty when none were logged or readable
    correct: int = None   # index into `options`


@dataclass(frozen=True)
class Key:
    line: int
    slot: int
    count: int


@dataclass(frozen=True)
class Malformed:
    line: int
    reason: str


@dataclass(frozen=True)
class Note:
    name: str
    kind: str                # "session" or "review"
    fields: MappingProxyType
    body: str                # everything below the frontmatter
    declared_nodes: tuple    # the ids in `nodes:`
    entries: tuple           # node entries under *Lesson*
    gate_entries: tuple      # node entries under *Retrieval checks*
    misplaced: tuple         # node entries anywhere else
    retrieval: str           # the *Retrieval checks* section body
    retrieval_nodes: tuple   # node ids named there, first mention first
    checks: tuple
    keys: tuple              # every key field, well-formed or not, in order
    malformed: tuple
    status: str              # "closed", "open", "live break" or "stale pause"
    hours: float = None      # since the pause, or the start; None if closed or unreadable
    anchor: str = None       # "paused" or "start": which time `hours` counts from


def _open_status(fields, now):
    """(status, hours, anchor) by elapsed hours, never calendar date.

    Open means `end:` is empty -- the same test `vaultlib.open_session_note`
    uses. An open note with no readable `paused:` is "open" (a cut-off); with
    one, `vaultlib.STALE_HOURS` separates a live break from a stale pause. The
    rule is in records.md under *Closing an open note*.
    """
    if fields.get("end"):
        return "closed", None, None
    start = note_datetime(fields.get("date"), fields.get("start"))
    paused_text = fields.get("paused")
    paused = note_datetime(fields.get("date"), paused_text, after=start) if paused_text else None
    anchor = paused or start
    if anchor is None:
        return "open", None, None
    hours = (now - anchor).total_seconds() / 3600.0
    if paused is None:
        return "open", hours, "start"
    return ("stale pause" if hours >= STALE_HOURS else "live break"), hours, "paused"


def _split_options(raw):
    """Format A/B option text as (options, index of the `[correct]` marker or None)."""
    options, correct = [], None
    for index, part in enumerate(raw.split(" / ")):
        part = part.strip()
        marked = SLOT_MARK.search(part)
        if marked:
            correct = index
            part = part[: marked.start()].strip()
        options.append(part)
    return options, correct


def _read_line(line, number, checks, keys, malformed, pending):
    """Collect one line's logged checks and key fields. Returns the new `pending`.

    `pending` is the check a key field on a later line of the same list item
    belongs to, as in a review note where the options sit on their own lines
    under the question. A blank line ends the item.
    """
    first = len(checks)
    for match in CHECK_Q.finditer(line):
        text = match.group("text").strip().strip("/→ ").strip()
        checks.append({"line": number, "start": match.start(), "text": text,
                       "question": text, "options": (), "correct": None})
    here = checks[first:]

    keyed = None
    for key in KEY.finditer(line):
        keys.append(Key(number, int(key.group("slot")), int(key.group("count"))))
        options = OPTIONS.match(line, key.end())
        if options and keyed is None:
            keyed = (key, options)

    if keyed:
        key, options = keyed
        raw, fence = options.group("opts"), key.group("fence")
        if fence and raw.endswith(fence):
            raw = raw[: -len(fence)].rstrip()
        options = tuple(part.strip() for part in raw.split(" / "))
        slot, count = int(key.group("slot")), int(key.group("count"))
        before = [check for check in here if check["start"] < key.start()]
        if before:
            owner = before[-1]
        elif not here and pending is not None and not pending["options"]:
            owner = pending
        else:
            owner = None
        if owner is None:
            malformed.append(Malformed(number, "key field with no logged question to belong to"))
        elif len(options) != count:
            malformed.append(Malformed(number, "key says %d options, %d logged" % (count, len(options))))
        elif not 1 <= slot <= count:
            malformed.append(Malformed(number, "key slot %d is outside 1-%d" % (slot, count)))
        else:
            owner["options"], owner["correct"] = options, slot - 1
    else:
        for match in LEGACY.finditer(line):
            options, correct = _split_options(match.group("opts"))
            if correct is None:
                answer = match.group("a").strip().strip("`").lower()
                correct = next((index for index, option in enumerate(options)
                                if option.strip("`").lower() == answer), None)
            if correct is None:
                malformed.append(Malformed(number, "logged answer matches none of its options"))
                continue
            owner = [check for check in here if check["start"] <= match.start()]
            if owner:
                owner[-1].update(question=match.group("q").strip(), options=tuple(options),
                                 correct=correct)
    return here[-1] if here else pending


def parse(text, name="", now=None):
    """Everything in one note, as one frozen `Note`. `now` dates the open status."""
    fields, start = split_frontmatter(text or "")
    lines = (text or "").splitlines()
    heading, current, pending = "", None, None
    entries, checks, keys, malformed = [], [], [], []
    for number, line in enumerate(lines[start:], start=start + 1):
        if line.startswith("## "):
            heading, current, pending = line[3:].strip(), None, None
            continue
        found = ENTRY.match(line)
        if found:
            current = {"node": found.group(1), "title": found.group(2).strip(),
                       "section": heading, "line": number, "lines": []}
            entries.append(current)
            pending = None
            continue
        if current is not None:
            current["lines"].append(line)
        if not line.strip():
            pending = None
            continue
        pending = _read_line(line, number, checks, keys, malformed, pending)

    placed = {"lesson": [], "gate": [], "misplaced": []}
    for entry in entries:
        body = "\n".join(entry["lines"]).strip()
        lowered = entry["section"].lower()
        where = ("lesson" if lowered.startswith("lesson")
                 else "gate" if lowered.startswith("retrieval checks") else "misplaced")
        placed[where].append(NodeEntry(entry["node"], entry["title"], entry["section"],
                                       entry["line"], body, "**Diagram.**" in body,
                                       "**Check.**" in body))

    body = "\n".join(lines[start:])
    retrieval = section(body, "Retrieval checks")
    status, hours, anchor = _open_status(fields, now or datetime.now())
    return Note(
        name=name,
        kind="review" if fields.get("kind") == "review" else "session",
        fields=MappingProxyType(dict(fields)),
        body=body,
        declared_nodes=tuple(NODE_ID.findall(fields.get("nodes", ""))),
        entries=tuple(placed["lesson"]),
        gate_entries=tuple(placed["gate"]),
        misplaced=tuple(placed["misplaced"]),
        retrieval=retrieval,
        retrieval_nodes=tuple(dict.fromkeys(NODE_ID.findall(retrieval))),
        checks=tuple(LoggedCheck(check["line"], check["text"], check["question"],
                                 check["options"], check["correct"]) for check in checks),
        keys=tuple(keys),
        malformed=tuple(malformed),
        status=status,
        hours=hours,
        anchor=anchor,
    )


def read(path, now=None):
    """`parse` for a note on disk, named by its file stem."""
    path = Path(path)
    return parse(path.read_text(), name=path.stem, now=now)
