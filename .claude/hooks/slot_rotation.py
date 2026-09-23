#!/usr/bin/env python3
"""The multiple-choice slot-rotation rule, and the history it runs on.

This docstring is the statement of the rule. The correct answer to a logged
multiple-choice check must not land in the same slot as the previous check's,
and across any `WINDOW` consecutive checks no slot may hold it more than
`MAX_IN_WINDOW` times. Drafting the correct claim first and leaving it in the
first slot is the most common way a question gets answered by position rather
than by knowing, and it fails invisibly: every question on its own still looks
well-formed. Only the sequence shows it.

The rule used to be written twice, in `mc-preflight.allowed()` and
`learn-status.g4_mc_slots()`. The predicates agreed; their inputs did not.
Preflight counted every entry in `placement.json`, whatever its scope or
subject, so a lesson for one subject rotated against review questions it never
saw, and a review counted its own already-logged checks twice. So the rule and
the history it runs on live here once:

  * `logged(folder)` is the sequence of `(note name, slot)` from every key
    field in a folder, in note order -- what G4 checks after the fact.
  * `pending(...)` is the prepared placements that are not logged yet -- what
    preflight adds on top before choosing a slot.
  * `breaks(sequence)` is every violation, as data; `allowed(slot, history)`
    is true when appending `slot` adds none.

Warning text stays in `learn-status.py`, and the lock, the `placement.json`
file and the choice among allowed slots stay in `mc-preflight.py`, so this
module decides and never prints or writes. Built on `session_note` for the key
fields and `vaultlib.STALE_HOURS` for when a placement was abandoned.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import session_note
from vaultlib import STALE_HOURS

WINDOW = 5
MAX_IN_WINDOW = 2


@dataclass(frozen=True)
class Repeat:
    index: int  # position in the sequence of the check that repeats
    name: str   # the note that check is logged in
    slot: int


@dataclass(frozen=True)
class Crowded:
    index: int  # position of the last check in the window
    name: str   # the note that check is logged in
    slot: int
    count: int  # checks in the window with the answer in `slot`


def logged(folder):
    """The `(note name, slot)` sequence of a folder's key fields, in note order.

    Every key field counts, well-formed or not: a key whose option count is off
    still put the answer in a slot the learner saw.
    """
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return [(path.stem, key.slot) for path in sorted(folder.glob("*.md"))
            for key in session_note.read(path).keys]


def breaks(sequence):
    """Every break in a `(name, slot)` sequence: each `Repeat`, then each
    `Crowded` window of `WINDOW` checks, one per slot per window."""
    found = []
    for index in range(1, len(sequence)):
        name, slot = sequence[index]
        if slot == sequence[index - 1][1]:
            found.append(Repeat(index, name, slot))
    for index in range(WINDOW - 1, len(sequence)):
        slots = [slot for _, slot in sequence[index - WINDOW + 1:index + 1]]
        for slot in sorted(set(slots)):
            if slots.count(slot) > MAX_IN_WINDOW:
                found.append(Crowded(index, sequence[index][0], slot, slots.count(slot)))
    return found


def allowed(slot, history):
    """True when appending `slot` to a history of slots adds no break.

    A break already in the history does not block the next check; only one the
    candidate itself completes does.
    """
    sequence = [("", earlier) for earlier in history] + [("", slot)]
    return not any(found.index == len(history) for found in breaks(sequence))


def _still_prepared(entry, bodies, now):
    evidence, stamp = entry.get("evidence"), entry.get("prepared")
    if not isinstance(evidence, str) or not evidence or not isinstance(stamp, str):
        return False
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return False
    if now - when >= timedelta(hours=STALE_HOURS):
        return False
    return not any(evidence in body for body in bodies)


def pending(prepared, scope, subject, bodies, now):
    """The prepared placements that still count for a `scope` and `subject`.

    An entry counts only for its own scope, and for `lesson` only for its own
    subject. It stops counting once its `evidence` string appears verbatim in
    one of `bodies`, the note bodies in that scope (`tutor.md` requires the
    copy be verbatim), since from then on `logged()` counts it; or once it is
    `STALE_HOURS` old, meaning it was prepared and never asked. An entry with
    no evidence or no readable `prepared` time never counts.
    """
    return [entry for entry in prepared
            if entry.get("scope") == scope and (scope != "lesson" or entry.get("subject") == subject)
            and _still_prepared(entry, bodies, now)]
