#!/usr/bin/env python3
"""Generate the learning dashboard and per-subject progress notes from the records.

Everything here is derived, never authored. `record.md` and `plan.md` are the
source of truth; this script only re-presents them, so the dashboard cannot drift
out of step with the evidence the way a hand-maintained table does. That is also
why it takes no arguments and asks no questions: run it and the views are current.

It is deliberately a generator rather than a set of Dataview queries. Dataview can
only read frontmatter, and the node-level state lives in Markdown tables; querying
data you could simply render also adds a plugin dependency to a file that has to
open on a phone. Where Dataview does fit -- subject and session frontmatter -- see
`learn/Queries.md`.

Run: python3 .claude/hooks/learn-status.py [--vault PATH]
     python3 .claude/hooks/learn-status.py --next [--host claude|codex]  (read-only)
     python3 .claude/hooks/learn-status.py --rewards --subject SLUG --session NN  (read-only)
     python3 .claude/hooks/learn-status.py --rewards --review NN  (read-only)
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import session_note  # noqa: E402
import slot_rotation  # noqa: E402
from vaultlib import STALE_HOURS, frontmatter, section, strip_frontmatter  # noqa: E402

# Teaching order, worst to best. The order drives the summary table and the legend.
STATUSES = ["decayed", "planned", "introduced", "checked", "solid", "skipped"]

# A node counts toward progress once it has passed a check, or was skipped because
# diagnosis showed the learner already had it. `introduced` is taught but unproven,
# so it is shown as partial: claiming it as progress would overstate the evidence.
COVERED = {"checked", "solid", "skipped"}
PARTIAL = {"introduced"}

# Light fills with dark text stay legible in both Obsidian themes.
COLOURS = {
    "solid":      "fill:#c6f6d5,stroke:#2f855a,color:#1a202c",
    "checked":    "fill:#bee3f8,stroke:#2b6cb0,color:#1a202c",
    "introduced": "fill:#feebc8,stroke:#b7791f,color:#1a202c",
    "planned":    "fill:#edf2f7,stroke:#a0aec0,color:#4a5568",
    "decayed":    "fill:#fed7d7,stroke:#c53030,color:#1a202c",
    "skipped":    "fill:#e9d8fd,stroke:#6b46c1,color:#1a202c",
}

NODE_ID = re.compile(r"\bn\d+\b")
MERMAID = re.compile(r"```mermaid\n(.*?)```", re.S)
CELL_BREAK = re.compile(r"(?<!\\)\|")
EDGE = re.compile(r"\b(n\d+)\b[^\n]*?-->[^\n]*?\b(n\d+)\b")


# --------------------------------------------------------------------- reading

def table_rows(text):
    """Pipe-table body rows as lists of stripped cells, skipping header and rule."""
    return pipe_rows(text)[1:]


def table_by_header(text):
    """Pipe-table body rows as dicts keyed by the header cells, so a column can
    be added or moved without shifting what every other lookup reads."""
    rows = pipe_rows(text)
    return [dict(zip(rows[0], cells)) for cells in rows[1:]] if rows else []


def pipe_rows(text):
    """Every pipe-table row, header included, as lists of stripped cells."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # "\|" is a literal pipe inside a cell, as in |a|² in a math plan.
        cells = [cell.strip() for cell in CELL_BREAK.split(line.strip("|"))]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the |---|---| separator
        rows.append(cells)
    return rows


def read_nodes(record_text, plan_text):
    """Merge the node tables from record.md and plan.md, keyed by node id.

    record.md is authoritative for status (statuses move only on evidence, and the
    evidence lives there); plan.md supplies the name and declared prerequisites.
    """
    nodes = {}
    for cells in table_rows(section(record_text, "Nodes")):
        match = NODE_ID.search(cells[0])
        if not match:
            continue
        node = match.group(0)
        nodes[node] = {
            "id": node,
            # The live records separate a node id from its name three ways --
            # "n1 — Memory address", "n1 encapsulation", "n1. static vs. instance"
            # -- so the em and en dashes belong in the strip set with the ASCII one.
            "name": NODE_ID.sub("", cells[0], count=1).strip(" .,-\u2013\u2014"),
            "status": (cells[1] if len(cells) > 1 else "").strip().lower(),
            "checked": cells[2].strip() if len(cells) > 2 else "",
            "evidence": cells[3].strip() if len(cells) > 3 else "",
            "prereqs": [],
            "plan_status": "",
        }
    for row in table_by_header(section(plan_text, "Nodes")):
        node = row.get("Id", "")
        if not NODE_ID.fullmatch(node):
            continue
        entry = nodes.setdefault(node, {"id": node, "name": row.get("Node", ""),
                                        "status": "", "checked": "", "evidence": "",
                                        "prereqs": [], "plan_status": ""})
        if not entry["name"]:
            entry["name"] = row.get("Node", "")
        entry["can_do"] = row.get("Can do", "")
        entry["prereqs"] = NODE_ID.findall(row.get("Prereqs", ""))
        entry["plan_status"] = row.get("Status", "").lower()
    # A prereq naming the node itself or an id not in the table is no edge.
    # It is dropped here and kept aside for consistency() to report.
    for node, entry in nodes.items():
        entry["can_do"] = entry.get("can_do") or entry["name"]
        entry["bad_prereqs"] = [p for p in entry["prereqs"] if p == node or p not in nodes]
        entry["prereqs"] = [p for p in entry["prereqs"] if p not in entry["bad_prereqs"]]
    return nodes


def read_notes(folder, now):
    """Every note in `folder` that has frontmatter, parsed, oldest first."""
    notes = [session_note.read(path, now=now)
             for path in (sorted(folder.glob("*.md")) if folder.is_dir() else [])]
    return [note for note in notes if note.fields]


def load_subjects(vault, now):
    """Every subject folder with a record.md, read once.

    Returns (subjects, missing): one dict per subject holding what the ranking,
    the rewards, and every view read, and the names of folders with no
    record.md, which are not subjects.
    """
    root = Path(vault) / "learn" / "subjects"
    subjects, missing = [], []
    for folder in sorted(path for path in root.glob("*") if path.is_dir()) if root.is_dir() else []:
        record, plan = folder / "record.md", folder / "plan.md"
        if not record.is_file():
            missing.append(folder.name)
            continue
        record_text = record.read_text()
        plan_text = plan.read_text() if plan.is_file() else ""
        subjects.append({
            "slug": folder.name, "folder": folder, "fields": frontmatter(record),
            "record_text": record_text, "plan_text": plan_text,
            "nodes": read_nodes(record_text, plan_text),
            "notes": read_notes(folder / "sessions", now),
            "events": evidence_events(record_text, note_starts(folder)),
        })
    return subjects, missing


def rank_inputs(subjects):
    """The (slug, nodes, fields, events) tuples `rank()` and `rewards()` take."""
    return [(s["slug"], s["nodes"], s["fields"], s["events"]) for s in subjects]


def note_inputs(subjects):
    """The (slug, session note) pairs `rank()` takes."""
    return [(s["slug"], note) for s in subjects for note in s["notes"]]


# ------------------------------------------------------ transition markers

# The node table keeps only a node's current status, so its history -- when it
# reached solid, how often it lapsed -- is read from the `→ nN <status>` endings
# on evidence lines (spec section 1, `CONTEXT.md`, *Transition marker*).

MARKER = re.compile(r"(n\d+) (%s)" % "|".join(STATUSES))
EVIDENCE_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2})\b\W*([sr]\d+\b)?")
NOTE_STEM = re.compile(r"^(\d{4}-\d{2}-\d{2})-([sr]\d+)$")

# On since the marker backfill (ticket 04) gave every existing evidence line its
# marker. Switching it off hides a proven node whose markers were never written.
MARKERS_REQUIRED = True


def markers(line):
    """The (node, status) pairs in the trailing run of markers, in line order.

    Nothing may follow the last marker, so a line whose final `→` segment is not
    a marker has none, even if a marker appears earlier in it.
    """
    found = []
    for segment in reversed(line.split("→")[1:]):
        match = MARKER.fullmatch(segment.strip())
        if not match:
            break
        found.append((match.group(1), match.group(2)))
    return found[::-1]


def note_starts(folder):
    """{(date, "sNN" or "rNN"): start time} for a subject's session notes and the
    vault's review notes, the notes an evidence line can name."""
    starts = {}
    for notes in (folder / "sessions", folder.parent.parent / "reviews"):
        for path in sorted(notes.glob("*.md")) if notes.is_dir() else []:
            stem = NOTE_STEM.match(path.stem)
            start = frontmatter(path).get("start", "")
            if stem and start:
                starts[(stem.group(1), stem.group(2))] = start
    return starts


def evidence_events(record_text, starts):
    """One event per marker in the *Evidence log*, in the order they happened.

    Order is (date, the `start:` of the note the line names, position in the
    log): the log is append-only, but a review can be logged above a session
    from earlier the same day. A line whose note is missing has no start time,
    so it sorts by date then position, ahead of that day's timed lines.
    """
    events = []
    bullets = [line for line in section(record_text, "Evidence log").splitlines()
               if line.startswith("- ")]
    for position, line in enumerate(bullets):
        head = EVIDENCE_LINE.match(line)
        date, source = (head.group(1), head.group(2) or "") if head else ("", "")
        for node, status in markers(line):
            events.append({"date": date, "source": source, "position": position,
                           "start": starts.get((date, source), ""),
                           "node": node, "status": status})
    events.sort(key=lambda event: (event["date"], event["start"], event["position"]))
    return events


def lapses(events):
    """Each `decayed` event whose previous marker for that node is not `decayed`
    (`CONTEXT.md`, *Lapse*). A check that leaves a decayed node decayed is not
    a new lapse."""
    found, last = [], {}
    for event in events:
        if event["status"] == "decayed" and last.get(event["node"]) != "decayed":
            found.append(event)
        last[event["node"]] = event["status"]
    return found


# ------------------------------------------------------ the review picker (Phase 5)

# A node reaches `solid` only by passing a retrieval check in a later session, and
# until `/learn-review` existed the only path to one ran through `/learn-resume` of
# that single subject. A `done` subject never gets resumed, so its `checked` nodes
# could never move -- eight of them across three subjects when this was written.
#
# `due()` is the seam the two callers share. Both ask the same question, "which
# node has gone longest without evidence", and differ only in scope: `/learn-check`
# asks it of the subject in front of it, `/learn-review` asks it of the whole
# vault. Nothing about it goes to Jev: PLAN-2026-09-22.md is explicit that a date
# comparison stays in code, and this one was previously being done by eye across
# five `record.md` files.

# Only these have ever produced a check, so "time since the last one" is a question
# about them and about nothing else. A `planned` or `introduced` node is not stale,
# it is unstarted, and putting one in a review would ask the learner to retrieve
# something they were never taught.
DECAYABLE = ("checked", "solid", "decayed")

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def days_since(checked, today):
    """Days between a *Last checked* cell and `today`, or None if it holds no date.

    The cell is written three ways across the live records: a bare `2026-09-17`,
    a `2026-09-18 s01` carrying its session, and an em dash for a node with no
    check yet. Only the date is load-bearing, so everything around it is ignored
    rather than parsed. A cell with no usable date returns None so the caller can
    report it -- treating it as zero days would quietly rank an unchecked node as
    the freshest thing in the vault.
    """
    when = to_date(checked)
    return (today - when).days if when else None


def due(subjects, today, subject=None, per_subject=2, limit=None):
    """Nodes ranked by time since their last check, most stale first.

    `subjects` is a list of (slug, nodes) as `read_nodes` returns them, which is
    what makes this pure and testable without a vault on disk.

    `per_subject` caps how many nodes one subject contributes, applied *before*
    `limit` so a single long-neglected subject cannot fill an entire review set
    and crowd out the spacing across the others. `per_subject=None` lifts the cap.

    Returns `(rows, undated)`. `undated` holds every eligible node whose *Last
    checked* has no date in it: reported, never ranked, because a node whose
    status says it passed a check and whose date cell is empty is a record defect
    (G5 flags it too) and not something to silently order.
    """
    rows, undated = [], []
    for slug, nodes in subjects:
        if subject is not None and slug != subject:
            continue
        for node in sorted(nodes.values(), key=lambda entry: sort_key(entry["id"])):
            if node.get("status") not in DECAYABLE:
                continue
            row = {"subject": slug, "id": node["id"], "name": node.get("name", ""),
                   "status": node["status"], "checked": node.get("checked", ""),
                   "evidence": node.get("evidence", "")}
            days = days_since(node.get("checked", ""), today)
            if days is None:
                undated.append(row)
                continue
            rows.append(dict(row, days=days))

    if per_subject is not None:
        kept, seen = [], {}
        for row in sorted(rows, key=lambda row: (-row["days"], row["subject"], sort_key(row["id"]))):
            if seen.get(row["subject"], 0) >= per_subject:
                continue
            seen[row["subject"]] = seen.get(row["subject"], 0) + 1
            kept.append(row)
        rows = kept

    rows.sort(key=lambda row: (-row["days"], row["subject"], sort_key(row["id"])))
    return (rows[:limit] if limit else rows), undated


# --------------------------------------------- the due rule and the ranking

# `due()` above ranks staleness for picking questions; `is_due()` answers the
# yes-or-no question the ranking and the streak ask (spec section 3, `CONTEXT.md`,
# *Due*). A decayed node is never due: it needs repair, not review.
DUE_DAYS = {"checked": 3, "solid": 7}

# A deadline counts from 7 days ahead through the deadline day. The same span
# opens the due window and lists the subject under Deadline, so a subject is
# never in one and not the other.
DEADLINE_DAYS = 7


def to_date(text):
    """The first ISO date in `text` as a date, or None."""
    match = ISO_DATE.search(text or "")
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%Y-%m-%d").date()
    except ValueError:
        return None  # well-shaped but impossible, e.g. 2026-13-45


def days_to_deadline(deadline, today):
    """Days from `today` to a `deadline:` value, or None if it holds no date."""
    when = to_date(deadline)
    return (when - today).days if when else None


def in_deadline_window(deadline, today):
    """Whether `today` falls from 7 days before `deadline` through the deadline."""
    left = days_to_deadline(deadline, today)
    return left is not None and 0 <= left <= DEADLINE_DAYS


def is_due(node, today, deadline=None):
    """Whether a node should be checked again on `today`."""
    if node.get("status") not in DUE_DAYS:
        return False
    checked = to_date(node.get("checked"))
    if checked is None:
        return False
    if (today - checked).days >= DUE_DAYS[node["status"]]:
        return True
    if in_deadline_window(deadline, today):
        return checked < to_date(deadline) - timedelta(days=DEADLINE_DAYS)
    return False


def short_date(when):
    """`22 Sep`, the form every reason and welcome phrase uses."""
    return "%d %s" % (when.day, when.strftime("%b"))


def next_node(nodes):
    """The first `planned` node in plan order whose prereqs are all proven,
    else the first `planned` node, else None."""
    planned = [nodes[node] for node in sorted(nodes, key=sort_key) if nodes[node]["status"] == "planned"]
    ready = [entry for entry in planned
             if all(nodes.get(p, {}).get("status") in COVERED for p in entry.get("prereqs", []))]
    return (ready or planned or [None])[0]


def plural(count, word):
    return "%d %s%s" % (count, word, "" if count == 1 else "s")


def candidate(kind, slug, title, command, reason, welcome):
    return {"kind": kind, "subject": slug, "title": title, "command": command,
            "reason": reason, "welcome": welcome}


def repair(slug, title, nodes, events):
    """The Repair candidate for a subject, with its sort key, or None."""
    decayed = [entry for entry in nodes.values() if entry["status"] == "decayed"]
    if not decayed:
        return None
    lapsed = lapses(events)
    slipped = []
    for entry in decayed:
        own = [event for event in lapsed if event["node"] == entry["id"]]
        when = to_date(own[-1]["date"]) if own else to_date(entry["checked"])
        slipped.append((when or datetime.max.date(), sort_key(entry["id"]), entry, len(own)))
    slipped.sort(key=lambda item: item[:2])
    first, entry = slipped[0][0], slipped[0][2]
    name, date = "*%s*" % entry["name"], short_date(first)
    reason = ("%s slipped on %s" % (name, date) if len(slipped) == 1 else
              "%s and %d more slipped, the first on %s" % (name, len(slipped) - 1, date))
    welcome = ("bring back %s in %s. It slipped on %s, and one short session puts it back"
               % (name, title, date))
    key = (-len(slipped), first, -max(item[3] for item in slipped), slug)
    return candidate("Repair", slug, title, "learn-resume " + slug, reason, welcome), key


def review(due_nodes, titles, slug=None):
    """The Review candidate over `due_nodes`, a list of (slug, node), or None."""
    if not due_nodes:
        return None
    oldest_slug, oldest = min(due_nodes, key=lambda item: (to_date(item[1]["checked"]), item[0],
                                                           sort_key(item[1]["id"])))
    count = len(due_nodes)
    spread = sorted({item[0] for item in due_nodes})
    where = ("in %s" % titles[spread[0]] if len(spread) == 1
             else "across %d subjects" % len(spread))
    reason = ("%s %s due %s, oldest *%s* (last checked %s)"
              % (plural(count, "node"), "is" if count == 1 else "are", where, oldest["name"],
                 short_date(to_date(oldest["checked"]))))
    welcome = ("review the %s that %s due, oldest *%s* from %s"
               % (plural(count, "node"), "is" if count == 1 else "are", oldest["name"],
                  titles[oldest_slug]))
    command = "learn-review" + (" " + slug if slug else "")
    return candidate("Review", slug, titles[slug] if slug else None, command, reason, welcome)


def resume(slug, title, nodes, fields, open_stem, today):
    """The Resume candidate, naming a passed deadline or an open note if any."""
    upcoming = next_node(nodes)
    reason = "*%s* is next" % upcoming["name"] if upcoming else "continue the plan"
    welcome = ("continue %s, where *%s* is next" % (title, upcoming["name"]) if upcoming
               else "continue %s" % title)
    extra = []
    left = days_to_deadline(fields.get("deadline"), today)
    if left is not None and left < 0:
        extra.append("The deadline (%s) has passed." % short_date(to_date(fields["deadline"])))
    if open_stem:
        extra.append("Its open %s note is closed out first." % open_stem)
    if extra:
        reason = " ".join([reason + "."] + extra)
    return candidate("Resume", slug, title, "learn-resume " + slug, reason, welcome)


def rank(subjects, notes, today):
    """The recommended actions, best first (spec section 3, `CONTEXT.md`,
    *Recommended action*).

    `subjects` is a list of (slug, nodes, fields, events): `read_nodes`, the
    record's frontmatter, and `evidence_events`. `notes` is a list of (slug,
    session note) as `session_note.read` returns them. Reads nothing else, so
    rewards cannot move it and running it changes nothing.
    """
    titles = {slug: fields.get("title", slug) for slug, _, fields, _ in subjects}
    listed, ranked = set(), []

    breaks = sorted(((note.hours, slug, note) for slug, note in notes if note.status == "live break"),
                    key=lambda item: item[:2])
    for _, slug, note in breaks:
        paused = note.fields.get("paused", "")
        ranked.append(candidate("Continue a break", slug, titles.get(slug, slug), "learn-resume " + slug,
                                "your session paused at %s" % paused,
                                "pick your %s session back up; the break started at %s"
                                % (titles.get(slug, slug), paused)))
        listed.add(slug)

    open_stems = {}
    for slug, note in notes:
        if note.status in ("open", "stale pause"):
            open_stems[slug] = note.name.rsplit("-", 1)[-1]

    deadlines = []
    for slug, nodes, fields, events in subjects:
        if not in_deadline_window(fields.get("deadline"), today):
            continue
        left = days_to_deadline(fields.get("deadline"), today)
        title = titles[slug]
        repaired = repair(slug, title, nodes, events)
        found = repaired[0] if repaired else review(
            [(slug, entry) for entry in nodes.values() if is_due(entry, today, fields.get("deadline"))],
            titles, slug)
        if not found and fields.get("status") in ("active", "paused"):
            found = resume(slug, title, nodes, fields, open_stems.get(slug), today)
        if not found:
            continue
        when = "today" if left == 0 else "in " + plural(left, "day")
        found = dict(found, kind="Deadline",
                     reason="deadline %s: %s" % (when, found["reason"]),
                     welcome="%s's deadline is %s, so %s" % (title, when, found["welcome"]))
        deadlines.append(((left, slug), found))
    for _, found in sorted(deadlines, key=lambda item: item[0]):
        ranked.append(found)
        listed.add(found["subject"])

    # Only a Deadline listing takes a subject out of Repair: a break and a
    # decayed node are two different things to do.
    on_deadline = {found["subject"] for _, found in deadlines}
    repairs = [repair(slug, titles[slug], nodes, events)
               for slug, nodes, fields, events in subjects if slug not in on_deadline]
    for found, _ in sorted((item for item in repairs if item), key=lambda item: item[1]):
        ranked.append(found)
        listed.add(found["subject"])

    across_subjects = review([(slug, entry) for slug, nodes, fields, _ in subjects
                         for entry in nodes.values() if is_due(entry, today, fields.get("deadline"))],
                        titles)
    if across_subjects:
        ranked.append(across_subjects)

    resumes = []
    for slug, nodes, fields, _ in subjects:
        if slug in listed or fields.get("status") not in ("active", "paused"):
            continue
        left = days_to_deadline(fields.get("deadline"), today)
        last = to_date(fields.get("last_session"))
        key = (left is not None and left < 0, -(last.toordinal() if last else 0), slug)
        resumes.append((key, resume(slug, titles[slug], nodes, fields, open_stems.get(slug), today)))
    ranked += [found for _, found in sorted(resumes, key=lambda item: item[0])]

    ranked.append(candidate("Start", None, None, "learn-start", "start something new", ""))
    return ranked


def next_report(ranked, host="claude"):
    """`--next`: one candidate per line, commands in the host's form."""
    sigil = "$" if host == "codex" else "/"
    return "\n".join("%d. %s · %s · %s%s · %s"
                     % (number, found["kind"], found["title"] or "any subject", sigil,
                        found["command"], found["reason"])
                     for number, found in enumerate(ranked, 1))


# ------------------------------------------------------------ derived rewards

# Rewards are read from the records every time and never stored (spec section 2,
# `CONTEXT.md`, *Reward*). Only markers dated on or before `today` count, and a
# caller can drop marker lines to get the state without them.

BADGE_ORDER = ["Goal met", "Recovered", "Solid"]

REWARDS_ON, REWARDS_OFF = {"on", "true", "yes"}, {"off", "false", "no"}


def rewards_setting(vault):
    """(on, warning) from `rewards:` in `learn/me/preferences.md` (spec section 4).

    Missing means on. An unknown value means off, since showing rewards the
    learner may have tried to turn off is the worse mistake, and the warning
    puts it under *Record inconsistencies*. `frontmatter()` keeps a trailing
    `# comment`, and the file ships with one, so it is cut here.
    """
    raw = frontmatter(Path(vault) / "learn" / "me" / "preferences.md").get("rewards", "")
    value = re.sub(r"(^|\s+)#.*$", "", raw).strip().strip("\"'").lower()
    if not value or value in REWARDS_ON:
        return True, None
    if value in REWARDS_OFF:
        return False, None
    return False, ("learn/me/preferences.md: `rewards: %s` is not on or off, so rewards are off "
                   "(use on, true, yes, off, false, or no)" % value)


def badge(kind, slug, title, node, name, date):
    return {"kind": kind, "subject": slug, "title": title, "node": node, "name": name,
            "date": date, "text": "%s: %s, %s" % (kind, name, date)}


def rewards(subjects, today):
    """The learner's reward state on `today`.

    `subjects` is a list of (slug, nodes, fields, events), the same shape
    `rank()` takes. Returns a dict of badges and the rest; writes nothing.
    """
    stamp = today.isoformat()
    badges, recoveries = [], []
    counts = {"nodes_proven": 0, "checks_passed": 0, "goals_met": 0}
    for slug, nodes, fields, events in subjects:
        title = fields.get("title", slug)
        goal = to_date(fields.get("goal_met"))
        if goal and goal <= today:
            counts["goals_met"] += 1
            badges.append(badge("Goal met", slug, title, None, title, goal.isoformat()))
        dated = [event for event in events if event["date"] and event["date"] <= stamp]
        lapse_events = [id(event) for event in lapses(dated)]
        solid, lapsed, proven = set(), {}, set()  # lapsed: node -> date of its open lapse
        for event in dated:
            node, name = event["node"], nodes.get(event["node"], {}).get("name") or event["node"]
            if event["status"] in ("checked", "solid"):
                proven.add(node)
            if id(event) in lapse_events:
                lapsed[node] = event["date"]
            elif event["status"] == "solid":
                counts["checks_passed"] += 1
                if node not in solid:
                    solid.add(node)
                    badges.append(badge("Solid", slug, title, node, name, event["date"]))
                if lapsed.pop(node, None):
                    badges.append(badge("Recovered", slug, title, node, name, event["date"]))
        # A node is proven from its first checked or solid marker, and a decay
        # after that takes nothing away (spec section 2, *Counts*). A skipped
        # node has no check to mark, and a status with no marker at all is
        # counted from the table, which marker_warnings() already reports.
        marked = {event["node"] for event in events}
        counts["nodes_proven"] += sum(
            1 for node, entry in nodes.items()
            if node in proven or entry.get("status") == "skipped"
            or (entry.get("status") in DECAYABLE and node not in marked))
        recoveries += [{"subject": slug, "title": title, "node": node,
                        "name": nodes.get(node, {}).get("name") or node, "date": date}
                       for node, date in sorted(lapsed.items(), key=lambda item: sort_key(item[0]))]
    # Newest first; on one date a goal, then a recovery, then a solid (spec section 8).
    badges.sort(key=lambda found: (BADGE_ORDER.index(found["kind"]), found["title"],
                                   sort_key(found["node"]) if found["node"] else 0))
    badges.sort(key=lambda found: found["date"], reverse=True)
    streak = review_streak(subjects, today)
    counts.update(current_streak=streak["current"], best_streak=streak["best"])
    return {"badges": badges, "open_recoveries": recoveries, "counts": counts, "streak": streak}


# A missed week is forgiven unless another forgiven miss fell this many weeks
# before it, so one miss in any four weeks costs nothing.
FORGIVE_WEEKS = 3


def review_streak(subjects, today):
    """The weekly review streak on `today` (spec section 2, `CONTEXT.md`,
    *Review streak*).

    A node is due on a day by `is_due()` applied to its last marker on or
    before that day, so the streak and the ranking share one due rule. Each
    week is `pass`, `neutral`, `repaired`, `forgiven`, `miss`, or `pending`;
    only a miss resets the current streak, and only a pass adds to it.
    """
    history, deadlines, solids = {}, {}, {}
    for slug, _, fields, events in subjects:
        deadlines[slug] = fields.get("deadline")
        for event in events:
            when = to_date(event["date"])
            if not when or when > today:
                continue
            key = (slug, event["node"])
            history.setdefault(key, []).append((when, event["status"]))
            if event["status"] == "solid":
                solids.setdefault(monday(when), set()).add(key)
    if not history:
        return {"current": 0, "best": 0, "alive": False, "weeks": []}

    first = min(when for markers in history.values() for when, _ in markers)
    this_week = monday(today)
    starts, weeks, start = [], [], monday(first)
    while start <= this_week:
        days = [start + timedelta(days=offset) for offset in range(7)]
        starts.append(start)
        weeks.append({"start": start.isoformat(), "due": sorted(
            key for key, markers in history.items()
            if any(is_due_on(markers, day, deadlines[key[0]]) for day in days if first <= day <= today))})
        start += timedelta(days=7)

    current = best = 0
    forgiven = []
    for index, (start, week) in enumerate(zip(starts, weeks)):
        if start in solids:
            result = "pass"
            current += 1
        elif start == this_week:
            result = "pending"  # it can still pass
        elif not week["due"]:
            result = "neutral"
        elif set(week["due"]) & solids.get(start + timedelta(days=7), set()):
            result = "repaired"
        elif start == this_week - timedelta(days=7):
            result = "pending"  # it can still be repaired this week
        elif any(index - FORGIVE_WEEKS <= earlier < index for earlier in forgiven):
            result = "miss"
            current = 0
        else:
            result = "forgiven"
            forgiven.append(index)
        best = max(best, current)
        week["result"] = result
    return {"current": current, "best": best, "alive": current > 0, "weeks": weeks}


def monday(day):
    """The Monday that starts `day`'s week."""
    return day - timedelta(days=day.weekday())


def is_due_on(markers, day, deadline):
    """Whether a node with these (date, status) markers, in event order, was
    due on `day`. Its state is its last marker on or before that day."""
    state = None
    for when, status in markers:
        if when > day:
            break
        state = {"status": status, "checked": when.isoformat()}
    return bool(state) and is_due(state, day, deadline)


# ------------------------------------------------------------ reward lines

# `--rewards` prints the only reward text the tutor may show, pasted verbatim
# into the `/learn-end` or `/learn-review` closing block (spec section 11,
# `CONTEXT.md`, *Reward line*). It compares the reward state with and without
# the scope's marker lines, so it can only name what that session or review
# added. Record voice: dated facts, no praise, no exclamation marks, no emoji.

MAX_REWARD_LINES = 4
COUNT_LABELS = [("nodes_proven", "Nodes proven"), ("checks_passed", "Retrieval checks passed"),
                ("goals_met", "Goals met")]


def same_source(source, letter, number):
    """Whether an evidence line's `sNN` or `rNN` names this session or review.
    `number` may be written `3`, `03`, or `s03`."""
    digits = re.sub(r"\D", "", str(number))
    return bool(digits) and bool(re.fullmatch(r"%s0*%d" % (letter, int(digits)), source or ""))


def weeks_word(count):
    return plural(count, "week")


def reward_lines(subjects, today, subject=None, session=None, review=None, session_date=None):
    """The closing block's reward lines, at most four, or [] (spec section 11).

    `subjects` is the (slug, nodes, fields, events) list `rewards()` takes. With
    `review`, the scope is that review's lines in every subject; otherwise it
    is session `session` of `subject`, and a Goal met badge is in scope when
    `goal_met:` equals `session_date`. The rewards setting is the caller's to
    check: this always answers as if rewards were on.
    """
    if review is not None:
        in_scope = lambda slug, event: same_source(event["source"], "r", review)  # noqa: E731
    else:
        in_scope = lambda slug, event: slug == subject and same_source(event["source"], "s", session)  # noqa: E731
    before_inputs = []
    for slug, nodes, fields, events in subjects:
        kept = dict(fields)
        if (review is None and slug == subject and session_date
                and to_date(fields.get("goal_met")) == to_date(session_date)):
            kept.pop("goal_met", None)
        outside = [e for e in events if not in_scope(slug, e)]
        # A node the scope moved stands, before it, where its last marker
        # outside the scope left it. Its table status is the after state.
        moved = {e["node"] for e in events if in_scope(slug, e)}
        last = {e["node"]: e["status"] for e in outside}
        before_nodes = {node: (dict(entry, status=last.get(node, "planned")) if node in moved else entry)
                        for node, entry in nodes.items()}
        before_inputs.append((slug, before_nodes, kept, outside))
    before, after = rewards(before_inputs, today), rewards(subjects, today)

    def key(found):
        return (found["kind"], found["subject"], found["node"], found["date"])
    had = {key(found) for found in before["badges"]}
    earned = sorted((found for found in after["badges"] if key(found) not in had),
                    key=lambda found: (found["date"], BADGE_ORDER.index(found["kind"])))
    was_open = {(r["subject"], r["node"], r["date"]) for r in before["open_recoveries"]}
    opened = [r for r in after["open_recoveries"] if (r["subject"], r["node"], r["date"]) not in was_open]

    badge_lines = [found["text"] for found in earned]
    recovery = (["Recovery open: %s. Passing it in a later session earns Recovered."
                 % ", ".join(r["name"] for r in opened)] if opened else [])
    changed = ["%s: %d → %d" % (label, before["counts"][name], after["counts"][name])
               for name, label in COUNT_LABELS if before["counts"][name] != after["counts"][name]]
    counts = [" · ".join(changed)] if changed and review is None else []

    weeks_before, weeks_after = before["streak"]["weeks"], after["streak"]["weeks"]
    streak_now = after["streak"]["current"]
    if review is not None:
        turned = bool(weeks_after) and weeks_after[-1]["result"] == "pass" and (
            not weeks_before or weeks_before[-1]["result"] != "pass")
        repaired = (len(weeks_after) > 1 and weeks_after[-2]["result"] == "repaired"
                    and (len(weeks_before) < 2 or weeks_before[-2]["result"] != "repaired"))
        streak = ["Review streak: %s" % weeks_word(streak_now)] if (turned or repaired) and streak_now else []
    else:
        due_now = sum(1 for _, nodes, fields, _ in subjects for entry in nodes.values()
                      if is_due(entry, today, fields.get("deadline")))
        this_week_passed = bool(weeks_after) and weeks_after[-1]["result"] == "pass"
        if due_now and not this_week_passed:
            streak = ["This week isn't counted yet: %s %s due"
                      % (plural(due_now, "check"), "is" if due_now == 1 else "are")]
        elif after["streak"]["alive"]:
            streak = ["Review streak: %s" % weeks_word(streak_now)]
        else:
            streak = []
        if not badge_lines and not counts:
            return recovery  # nothing earned: only an opened recovery is ever named

    if len(earned) > 2 or len(badge_lines + recovery + counts + streak) > MAX_REWARD_LINES:
        if len(earned) > 1:
            badge_lines = ["%d badges: %s" % (len(earned), " · ".join(
                "%s: %s" % (found["kind"], found["name"]) for found in earned))]
    return (badge_lines + recovery + counts + streak)[:MAX_REWARD_LINES]


def due_report(rows, undated):
    """`--due` as the tutor and Edison read it. One node per line, stalest first."""
    out = []
    for row in rows:
        out.append("%4dd  %-34s %-4s [%s] last %s — %s"
                   % (row["days"], row["subject"], row["id"], row["status"],
                      row["checked"] or "?", row["name"] or "?"))
        if row["evidence"]:
            out.append("        last evidence: %s" % row["evidence"])
    for row in undated:
        out.append("   ??  %-34s %-4s [%s] Last checked holds no date — fix the record "
                   "before reviewing it" % (row["subject"], row["id"], row["status"]))
    if not out:
        out.append("nothing is due: no node has a logged check to be stale.")
    return "\n".join(out)


# --------------------------------------------------------------------- checking

def command_form(command, host):
    """A skill command as a host types it: `/learn-...` for Claude, `$learn-...`
    for Codex, and bare for `host=None`, the form Home and the Dashboard print
    because both hosts read them."""
    return {"claude": "/", "codex": "$"}.get(host, "") + command


def open_notes(notes, subject, host="claude"):
    """Report every session note whose `end:` is still empty.

    `/learn-resume` is required to finalize a stale or cut-off note before opening
    the next one (records.md, *Closing an open note*). Nothing used to force it:
    skipping the finalize left no mark in any file, so an abandoned note simply
    stayed open and the next resume orphaned it silently -- which is how s03 sat
    open for twenty-five hours. Surfacing every open note is what turns that rule
    from prose into something whose violation is visible.

    `session_note` computes the status against the `now` it was parsed with; this
    only words it. It reports and never repairs, for the same reason
    `consistency` does: the fix is a judgement about what the session actually
    covered, and a generator that closed notes on its own would manufacture
    exactly the false record the system is built to prevent.
    """
    reports = []
    for note in notes:
        if note.status == "closed":
            continue
        label = "%s %s" % (subject, note.name or "?")
        if note.hours is None:
            reports.append("%s: `end:` is empty and its `date:`/`start:` cannot be read, "
                           "so its age is unknown -- finalize it by hand" % label)
        elif note.hours < 0:
            reports.append("%s: `end:` is empty and its %s time is %.1f h in the future -- "
                           "check the note's `date:` field" % (label, note.anchor, -note.hours))
        elif note.status == "open":
            reports.append("%s: `end:` is empty with no `paused:` -- cut off %.1f h ago without "
                           "`%s`. `%s` must finalize it before opening the next note."
                           % (label, note.hours, command_form("learn-end", host),
                              command_form("learn-resume", host)))
        elif note.status == "stale pause":
            reports.append("%s: paused %.1f h ago, past the %d h bound -- a stale pause, not a break. "
                           "`%s` must finalize it before opening the next note."
                           % (label, note.hours, STALE_HOURS, command_form("learn-resume", host)))
        else:
            reports.append("%s: paused %.1f h ago, inside the %d h bound -- a live break. "
                           "`%s` reopens this note and skips the decay check."
                           % (label, note.hours, STALE_HOURS, command_form("learn-resume " + subject, host)))
    return reports


def g1_resume_bounds(slug, resume_path, plan_path):
    """G1: resume.md stays under 200 words, and it and plan.md carry subject/updated.

    `workflow.md` step 4 and `records.md:13` say `resume.md` is rewritten from
    scratch every time under a 200-word bound; `records.md:96` requires `subject`
    and `updated` in both files. A missing `subject` broke `session-start.sh`'s
    frontmatter counter silently for math241 (PLAN-2026-09-22.md) -- this is
    what would have caught it.
    """
    warnings = []
    if resume_path.is_file():
        count = len(strip_frontmatter(resume_path.read_text()).split())
        if count > 200:
            warnings.append("%s: resume.md is %d words, over the 200-word bound "
                            "(workflow.md step 4, records.md:13)" % (slug, count))
        fields = frontmatter(resume_path)
        for key in ("subject", "updated"):
            if not fields.get(key):
                warnings.append("%s: resume.md frontmatter is missing `%s:` (records.md:96)" % (slug, key))
    if plan_path.is_file():
        fields = frontmatter(plan_path)
        for key in ("subject", "updated"):
            if not fields.get(key):
                warnings.append("%s: plan.md frontmatter is missing `%s:` (records.md:96)" % (slug, key))
    return warnings


def g5_record_index(slug, fields, sessions, nodes):
    """G5: record.md's frontmatter index agrees with the session notes and node table.

    `records.md:16` bans a reused `sNN`, and its frontmatter reference says
    `sessions`/`last_session` are what the dashboard and SessionStart hook read
    -- so they must agree with what is actually on disk, not just what was true
    when someone last edited them by hand.
    """
    warnings = []
    declared_count = fields.get("sessions", "")
    if declared_count.isdigit() and int(declared_count) != len(sessions):
        warnings.append("%s: record.md says sessions: %s, but %d session note(s) exist"
                        % (slug, declared_count, len(sessions)))
    if sessions:
        newest = max((entry.get("date", "") for entry in sessions), default="")
        last_session = fields.get("last_session", "")
        if last_session and newest and last_session != newest:
            warnings.append("%s: record.md last_session is %s, but the newest session note is dated %s"
                            % (slug, last_session, newest))
    seen = {}
    for entry in sessions:
        num = entry.get("session")
        if num:
            seen.setdefault(num, []).append(entry.get("file", "?"))
    for num, files in seen.items():
        if len(files) > 1:
            warnings.append("%s: session number %s is reused across %s (records.md:16)"
                            % (slug, num, ", ".join(files)))
    for node in sorted(nodes, key=sort_key):
        entry = nodes[node]
        if entry["status"] in ("checked", "solid", "decayed") and not entry["checked"]:
            warnings.append("%s %s: status is '%s' but Last checked is empty" % (slug, node, entry["status"]))
    return warnings


def g2_session_notes(slug, folder):
    """G2: per session note, every taught node has its Diagram/Check lines, a
    fourth consecutive new node never opens without a logged retrieval check,
    frontmatter `nodes:` matches the union of Lesson entries and node ids
    named in *Retrieval checks* (`records.md:82`, decided 2026-09-22 after
    cs124-quiz4 s01 and math241-exam1-review s02 both had nodes with evidence
    that lived only in *Retrieval checks*, not a `### nN` header), and no node
    entry is filed outside *Lesson* or *Retrieval checks* (records.md:97).
    """
    warnings = []
    if not folder.is_dir():
        return warnings
    for path in sorted(folder.glob("*.md")):
        note = session_note.read(path)
        label = "%s %s" % (slug, note.name)
        for entry in note.entries:
            if not entry.has_diagram:
                warnings.append("%s: %s has no Diagram line (tutor.md, CLAUDE.md)" % (label, entry.node))
            if not entry.has_check:
                warnings.append("%s: %s has no Check line" % (label, entry.node))
        for entry in note.misplaced:
            warnings.append("%s: %s is filed under *%s*, not *Lesson* or *Retrieval checks* "
                            "(records.md:97)" % (label, entry.node, entry.section or "no heading"))
        if len(note.entries) >= 4 and not note.retrieval:
            warnings.append("%s: %d new nodes opened with *Retrieval checks* left empty "
                            "(workflow.md, the gate)" % (label, len(note.entries)))
        touched = {entry.node for entry in note.entries} | set(note.retrieval_nodes)
        declared = set(note.declared_nodes)
        if declared != touched:
            warnings.append("%s: frontmatter nodes: %s does not match Lesson + Retrieval-checks nodes %s "
                            "(records.md:82)" % (label, sorted(declared, key=sort_key) or "none",
                                                 sorted(touched, key=sort_key) or "none"))
    return warnings


def g4_mc_slots(slug, folder):
    """G4: the correct-answer slot on logged MC checks rotates, per the rule
    stated in `slot_rotation.py`. Reads the folder's key fields in session
    order and words each break the module finds.
    """
    keys = slot_rotation.logged(folder)
    warnings = []
    for found in slot_rotation.breaks(keys):
        if isinstance(found, slot_rotation.Repeat):
            warnings.append("%s: %s repeats the previous check's correct-answer slot %d "
                            "(slot_rotation.py)" % (slug, found.name, found.slot))
        else:
            warnings.append("%s: slot %d holds the correct answer %d times in the %d checks ending at %s "
                            "(slot_rotation.py)" % (slug, found.slot, found.count,
                                                    slot_rotation.WINDOW, found.name))
    return warnings


def marker_warnings(slug, nodes, events):
    """Where the transition markers disagree with the node table (spec section 15).

    Rewards are read from markers, so a marker that drifts from the table is a
    wrong reward. `events` must already be in order, as `evidence_events` returns.
    """
    warnings, latest = [], {}
    for event in events:
        latest[event["node"]] = event
    for node in sorted(latest, key=sort_key):
        event = latest[node]
        if node not in nodes:
            warnings.append("%s %s: a transition marker names %s, which is not in the node table"
                            % (slug, node, node))
            continue
        entry = nodes[node]
        if entry["status"] and event["status"] != entry["status"]:
            warnings.append("%s %s: last transition marker says '%s' (%s), node table says '%s'"
                            % (slug, node, event["status"], event["date"], entry["status"]))
        checked = ISO_DATE.search(entry["checked"] or "")
        if (entry["status"] in DECAYABLE and checked and event["date"]
                and checked.group(0) != event["date"]):
            warnings.append("%s %s: latest transition marker is dated %s, Last checked says %s"
                            % (slug, node, event["date"], checked.group(0)))
    if MARKERS_REQUIRED:
        for node in sorted(nodes, key=sort_key):
            if nodes[node]["status"] in DECAYABLE and node not in latest:
                warnings.append("%s %s: status is '%s' but it has no transition marker "
                                "on any evidence line" % (slug, node, nodes[node]["status"]))
    return warnings


def consistency(nodes, plan_text, subject, fields, sessions, folder):
    """Warn where the records contradict each other. Report; never auto-fix.

    A generator that silently repaired the source would hide exactly the drift it
    exists to surface, and these files are reviewed by a human and a subagent.

    Composes the plan/record node checks below with the four deterministic gates
    from PLAN-2026-09-22.md Phase 1: G1 (resume bound), G5 (record index), G2
    (session-note invariants), G4 (MC slot rotation).
    """
    warnings = []
    warnings += g1_resume_bounds(subject, folder / "resume.md", folder / "plan.md")
    warnings += g5_record_index(subject, fields, sessions, nodes)
    warnings += g2_session_notes(subject, folder / "sessions")
    warnings += g4_mc_slots(subject, folder / "sessions")
    record = folder / "record.md"
    if record.is_file():
        warnings += marker_warnings(subject, nodes,
                                    evidence_events(record.read_text(), note_starts(folder)))
    for node in sorted(nodes, key=sort_key):
        entry = nodes[node]
        if entry["plan_status"] and entry["status"] and entry["plan_status"] != entry["status"]:
            warnings.append("%s %s: record says '%s', plan says '%s' (records.md: the two must agree)"
                            % (subject, node, entry["status"], entry["plan_status"]))
        if not entry["status"]:
            warnings.append("%s %s: in plan.md but missing from the record.md node table" % (subject, node))
    for node in sorted(nodes, key=sort_key):
        for prereq in nodes[node].get("bad_prereqs", []):
            reason = "names the node itself" if prereq == node else "is not in the node table"
            warnings.append("%s %s: prereq %s %s, so it is left out of the graph"
                            % (subject, node, prereq, reason))
    edges = set()
    for block in MERMAID.findall(plan_text):
        for line in block.splitlines():
            found = EDGE.search(line)
            if found:
                edges.add((found.group(1), found.group(2)))
    for node in sorted(nodes, key=sort_key):
        declared = set(nodes[node]["prereqs"])
        drawn = {parent for parent, child in edges if child == node}
        if not declared and not drawn:
            continue
        if declared != drawn and (declared or drawn):
            warnings.append("%s %s: prereqs column says %s, graph edges say %s"
                            % (subject, node, sorted(declared) or "none", sorted(drawn) or "none"))
    return warnings


# --------------------------------------------------------------------- rendering

def sort_key(node):
    return int(node[1:])


def bar(done, partial, total, width=16):
    """A progress bar that distinguishes proven nodes from merely taught ones."""
    if not total:
        return "`" + "░" * width + "` 0%"
    filled = int(round(width * done / float(total)))
    half = int(round(width * (done + partial) / float(total))) - filled
    cells = "█" * filled + "▒" * max(half, 0)
    return "`" + cells + "░" * max(width - len(cells), 0) + "` " + str(int(round(100.0 * done / total))) + "%"


def by_status(nodes):
    groups = {}
    for node in sorted(nodes, key=sort_key):
        groups.setdefault(nodes[node]["status"] or "unknown", []).append(node)
    return groups


def colour_graphs(plan_text, nodes):
    """Re-emit the plan's mermaid graphs with each node filled by its status.

    classDef is plain mermaid, so this stays inside the rules in diagrams.md: no
    init directives, no HTML in labels, and it degrades to a normal graph if a
    renderer ignores the class lines.
    """
    blocks = []
    for block in MERMAID.findall(plan_text):
        body = block.rstrip()
        if not body.lstrip().startswith(("flowchart", "graph")):
            continue
        present = [node for node in sorted(set(NODE_ID.findall(body)), key=sort_key) if node in nodes]
        if not present:
            continue
        lines = [body]
        used = [status for status in STATUSES
                if any(nodes[node]["status"] == status for node in present)]
        for status in used:
            lines.append("    classDef %s %s" % (status, COLOURS[status]))
            members = [node for node in present if nodes[node]["status"] == status]
            lines.append("    class %s %s" % (",".join(members), status))
        blocks.append("```mermaid\n" + "\n".join(lines) + "\n```")
    return blocks


def log_links(slug, folder):
    # log.md and codex-log.md are gitignored, hook-written mirrors of the live
    # conversation, not records -- link only the ones that actually exist so the
    # generated view never ships a dead wikilink.
    names = [("log", "Claude log"), ("codex-log", "Codex log")]
    return " · ".join("[[learn/subjects/%s/%s|%s]]" % (slug, name, label)
                       for name, label in names if (folder / (name + ".md")).is_file())


def status_label(status, styled=False):
    # Literal text survives with the prototype snippet disabled. Only known
    # statuses enter the HTML attribute; other values keep the existing format.
    if styled and status in STATUSES:
        return '<code data-learning-status="%s">%s</code>' % (status, status)
    return "`%s`" % status


def progress_note(slug, folder, fields, nodes, plan_text, record_text, sessions, today):
    prototype = slug == "oop"  # First visual milestone, expand after learner use.
    total = len(nodes)
    done = sum(1 for node in nodes.values() if node["status"] in COVERED)
    partial = sum(1 for node in nodes.values() if node["status"] in PARTIAL)
    groups = by_status(nodes)
    title = fields.get("title", slug)

    out = ["---", "type: learning-progress", 'subject: "%s"' % slug,
           'updated: "%s"' % today, "generated: true",
           *(["cssclasses: [learning-note]"] if prototype else []), "---", "",
           "# %s — progress" % title, "",
           "> [!warning] Generated file",
           "> Written by `.claude/hooks/learn-status.py` from `record.md` and `plan.md`.",
           "> Anything edited here is overwritten on the next run.", "",
           "**%d of %d nodes proven** %s · %s session%s · status **%s**"
           % (done, total, bar(done, partial, total), fields.get("sessions", "0"),
              "" if fields.get("sessions") == "1" else "s", fields.get("status", "unknown")), "",
           (("> [!todo] Next action\n> " if prototype else "Next: ")
            + fields.get("next", "—")), "",
           " · ".join(part for part in [
               "[[learn/subjects/%s/record|Record]]" % slug,
               "[[learn/subjects/%s/plan|Plan]]" % slug,
               log_links(slug, folder),
               "[[learn/Dashboard|Dashboard]]",
           ] if part), "",
           "## Where each node stands", "", "| Status | Meaning | Nodes |", "| --- | --- | --- |"]
    meanings = {"solid": "passed a retrieval check in a later session",
                "checked": "passed a check when taught", "introduced": "taught, not yet proven",
                "planned": "not yet taught", "decayed": "failed a later retrieval check",
                "skipped": "diagnosis showed it was already there", "unknown": "no status recorded"}
    for status in STATUSES + ["unknown"]:
        if status in groups or (prototype and status not in ("skipped", "unknown")):
            out.append("| %s | %s | %s |" % (status_label(status, prototype), meanings[status],
                                             ", ".join(groups.get(status, [])) or "None"))
    out += ["", "## Dependency graph", "",
            "Filled by status, so the plan doubles as the progress view.", ""]
    graphs = colour_graphs(plan_text, nodes)
    out += (["\n\n".join(graphs), ""] if graphs
            else ["*No flowchart found in `plan.md`.*", ""])
    out += ["## Nodes", "", "| Id | Node | Status | Last checked |", "| --- | --- | --- | --- |"]
    for node in sorted(nodes, key=sort_key):
        entry = nodes[node]
        out.append("| %s | %s | %s | %s |" % (entry["id"], entry["name"],
                    status_label(entry["status"] or "unknown", prototype), entry["checked"] or "—"))
    strands = section(record_text, "Strands")
    if strands:
        out += ["", "## Strands — floor and ceiling", "", strands]
    if sessions:
        out += ["", "## Sessions", "", "| # | Date | Active | Ended | Nodes | Note |",
                "| --- | --- | --- | --- | --- | --- |"]
        for entry in sessions:
            # An open note is called open here rather than shown as a blank cell: a
            # missing end time is a state someone has to act on, not a gap in the data.
            ended = entry.get("end") or ("**open** (paused %s)" % entry["paused"]
                                         if entry.get("paused") else "**open**")
            out.append("| %s | %s | %s | %s | %s | [[learn/subjects/%s/sessions/%s\\|note]] |"
                       % (entry.get("session", "?"), entry.get("date", "?"),
                          (entry.get("active_minutes") or "—") + (" min" if entry.get("active_minutes") else ""),
                          ended, entry.get("nodes", "—"), slug, entry["file"]))
    if prototype:
        out += ["", "## Callout key", "",
                "Visual examples only. These are not questions or evidence from a lesson.", "",
                "> [!question] Question", "> A prompt to answer in the agent chat.", "",
                "> [!hint] Hint", "> A known fact to use for the next reasoning step.", "",
                "> [!failure] Correction", "> What was wrong and what replaces it.", "",
                "> [!todo] Next action", "> The next step to take. Your current action is at the top of this page.", ""]
    return "\n".join(out) + "\n"


def dashboard(subjects, today, warnings, openings):
    out = ["---", "type: learning-dashboard", 'updated: "%s"' % today, "generated: true",
           "cssclasses: [learning-note]", "---", "",
           "# Learning dashboard", "",
           "> [!warning] Generated file",
           "> Written by `.claude/hooks/learn-status.py` at every session start and learning session end.",
           "> Anything edited here is overwritten. Edit `record.md` instead.", "",
           "Node status key: " + " · ".join(status_label(status, True) for status in
               ("solid", "checked", "introduced", "decayed", "planned")), ""]
    if not subjects:
        out += ["No subjects yet. Use `/learn-start <subject>` in Claude Code or `$learn-start <subject>` in Codex.", ""]
    for slug, data in subjects:
        fields, nodes, folder = data["fields"], data["nodes"], data["folder"]
        total = len(nodes)
        done = sum(1 for node in nodes.values() if node["status"] in COVERED)
        partial = sum(1 for node in nodes.values() if node["status"] in PARTIAL)
        out += ["## %s" % fields.get("title", slug), "",
                "%s **%d/%d nodes proven** · %s · %s session%s · last %s"
                % (bar(done, partial, total), done, total, fields.get("status", "unknown"),
                   fields.get("sessions", "0"), "" if fields.get("sessions") == "1" else "s",
                   fields.get("last_session", "never")), "",
                "> [!todo] Next action\n> %s" % fields.get("next", "—"), "",
                " · ".join(part for part in [
                    "[[learn/subjects/%s/progress|Progress]]" % slug,
                    "[[learn/subjects/%s/resume|Resume]]" % slug,
                    "[[learn/subjects/%s/record|Record]]" % slug,
                    "[[learn/subjects/%s/plan|Plan]]" % slug,
                    log_links(slug, folder),
                ] if part), ""]
    if openings:
        out += ["## Open session notes", "",
                "> [!warning] A session note has no `end:`",
                "> A note stays open until `/learn-resume` finalizes it "
                "(`learn/system/records.md`, *Closing an open note*). While it is open its "
                "nodes stay unproven and the next session can orphan it."]
        out += ["> - " + report for report in openings]
        out += [""]
    if warnings:
        out += ["## Record inconsistencies", "",
                "> [!bug] The records disagree with each other",
                "> Fix these in `record.md` or `plan.md`; this file is regenerated, not edited."]
        out += ["> - " + warning for warning in warnings]
        out += [""]
    out += ["## Running a session", "",
            "From this vault, run `claude` or `codex`. In Claude Code use `/learn-start`, "
            "`/learn-resume`, `/learn-check`, and `/learn-end`. In Codex use the matching "
            "`$learn-start`, `$learn-resume`, `$learn-check`, and `$learn-end` skills.", "",
            "Open the subject's Claude or Codex chat log in Obsidian. Claude's log streams; "
            "Codex's log updates after each completed turn. Keep replies in chat.", "",
            "## The system", "",
            "- [[learn/Queries|Queries]] — live Dataview views across subjects and sessions",
            "- [[learn/system/tutor|tutor.md]] — teaching philosophy and behaviour rules",
            "- [[learn/system/workflow|workflow.md]] — the phases every subject goes through",
            "- [[learn/system/records|records.md]] — what the records contain and how they update",
            "- [[learn/system/diagrams|diagrams.md]] — mermaid and math rules for notes",
            "- [[learn/me/preferences|preferences.md]] — how Edison learns, and what the evidence shows",
            "- [[learn/README|README]] — how the whole thing fits together", ""]
    return "\n".join(out)


# --------------------------------------------------------------------- driver

def semantic_warnings(nodes, plan_text, subject, fields, sessions, folder, ask_fn=None,
                      vault=None):
    """Jev-backed checks (PLAN-2026-09-22.md Phases 4 and 5).

    J1: does every logged check stand on its own without the lesson around it.
    J2: could a logged check's options be picked without reading the question.
    J4: does `resume.md` actually let a cold session continue -- the test
    `records.md` states and G1's word count cannot make.
    J5: does any node entry draw an analogy without saying where it breaks,
    the rule audit X7 rejected as ungateable before a semantic judgement was
    cheap.

    Kept as its own function, alongside the deterministic `consistency()`, so a
    semantic check is never the only copy of a rule and never runs unless
    `--semantic` asked for it. J3 (candidate matching) is deliberately not here:
    it is a once-per-session judgement `/learn-end` makes about a candidate that
    exists only in that session's note, so it lives behind
    `python3 .claude/hooks/jev.py match-candidate`, which both hosts call the
    same way.

    Every line comes back prefixed `semantic:` because these warnings appear and
    disappear with the flag: a `--semantic` run writes them into the dashboard's
    *Record inconsistencies* and the next plain session-start run drops them
    again. The prefix is what tells a reader that a vanished line was a judgement
    that was not re-made, not a problem that was fixed.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import jev  # noqa: E402 -- only reached under --semantic

    folder = Path(folder)
    # The vault under test, not the one this file happens to live in: `jev` reads
    # `.env` relative to it, so a `--vault` run against a copy must not pick up
    # the real vault's key. `folder` is <vault>/learn/subjects/<slug>.
    vault = vault or folder.resolve().parents[2]
    warnings = jev.probe_warnings(subject, folder / "sessions", ask_fn=ask_fn, vault=vault)
    warnings += jev.resume_warnings(subject, folder / "resume.md", ask_fn=ask_fn, vault=vault)
    warnings += jev.analogy_warnings(subject, folder / "sessions", ask_fn=ask_fn, vault=vault)
    warnings += jev.leak_warnings(subject, folder / "sessions", ask_fn=ask_fn, vault=vault)
    return ["semantic: " + warning for warning in warnings]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--open-notes", action="store_true", dest="open_notes",
                        help="print open session notes and write nothing "
                             "(read-only; used by the SessionStart hook)")
    parser.add_argument("--due", action="store_true",
                        help="print nodes ranked by time since their last check and "
                             "write nothing (read-only). The pick for /learn-review, "
                             "and for /learn-check's older spacing node with --subject")
    parser.add_argument("--next", action="store_true", dest="next_action",
                        help="print the recommended actions, best first, and write "
                             "nothing (read-only)")
    parser.add_argument("--host", choices=("claude", "codex"), default="claude",
                        help="with --next or --open-notes, print /learn-... (claude) or "
                             "$learn-... (codex)")
    parser.add_argument("--rewards", action="store_true",
                        help="print the reward lines for one session (--subject and "
                             "--session) or one review (--review), and write nothing "
                             "(read-only). Prints nothing when rewards are off")
    parser.add_argument("--session", help="with --rewards and --subject, the session number")
    parser.add_argument("--review", help="with --rewards, the review number")
    parser.add_argument("--subject", help="with --due, restrict to one subject slug; "
                                          "with --rewards, the session's subject")
    parser.add_argument("--limit", type=int, default=None,
                        help="with --due, keep only the N stalest nodes")
    parser.add_argument("--per-subject", type=int, default=2, dest="per_subject",
                        help="with --due, how many nodes one subject may contribute "
                             "before --limit (0 lifts the cap). Default 2, so one "
                             "long-neglected subject cannot fill a whole review set")
    parser.add_argument("--semantic", action="store_true",
                        help="also run Jev-backed semantic checks (Phase 4). Off by "
                             "default: session start must stay offline, fast, and "
                             "deterministic (PLAN-2026-09-22.md, Engineering constraints)")
    args = parser.parse_args()
    if args.rewards and not (args.review or (args.subject and args.session)):
        parser.error("--rewards needs --subject and --session, or --review")

    vault = args.vault.resolve()
    stamp = datetime.now()
    today = stamp.strftime("%Y-%m-%d")
    loaded, missing = load_subjects(vault, stamp)
    warnings = ["%s: no record.md" % slug for slug in missing]
    openings, written = [], []
    for subject in loaded:
        openings += open_notes(subject["notes"], subject["slug"], host=args.host)

    if args.open_notes:
        # Printed into the tutor's context by session-start.sh. Silence means every
        # note is closed, which is the state the system expects at session start.
        for report in openings:
            print(report)  # the caller supplies the heading; a prefix here reads twice
        return 0

    if args.due:
        # Read-only like --open-notes: a review picks from the records without
        # touching them, so running this to decide what to ask never itself
        # changes what the dashboard says.
        rows, undated = due([(s["slug"], s["nodes"]) for s in loaded], stamp.date(),
                            subject=args.subject, per_subject=args.per_subject or None,
                            limit=args.limit)
        print(due_report(rows, undated))
        return 0

    if args.next_action:
        print(next_report(rank(rank_inputs(loaded), note_inputs(loaded), stamp.date()), host=args.host))
        return 0

    if args.rewards:
        # Read-only, and silent when rewards are off or nothing qualifies: the
        # closing skills paste whatever this prints, so no output is no lines.
        if rewards_setting(vault)[0]:
            session_date = None
            if not args.review:
                chosen = next((s for s in loaded if s["slug"] == args.subject), None)
                for note in chosen["notes"] if chosen else []:
                    if same_source(note.name.rsplit("-", 1)[-1], "s", args.session):
                        session_date = note.fields.get("date")
            for line in reward_lines(rank_inputs(loaded), stamp.date(), subject=args.subject,
                                     session=args.session, review=args.review,
                                     session_date=session_date):
                print(line)
        return 0

    if args.semantic:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import jev  # noqa: E402 -- only imported when explicitly asked for
        if not jev.available(vault) and not args.quiet:
            print("learn-status: --semantic requested but jev is not available "
                  "(no TYPESAFE_API_KEY or typesafe-sdk not installed) -- running the "
                  "deterministic fallback half of each semantic check instead")

    subjects = []
    for subject in loaded:
        slug, folder, fields, nodes = subject["slug"], subject["folder"], subject["fields"], subject["nodes"]
        plan_text, record_text = subject["plan_text"], subject["record_text"]
        sessions = [dict(note.fields, file=note.name) for note in subject["notes"]]
        warnings += consistency(nodes, plan_text, slug, fields, sessions, folder)
        if args.semantic:
            # Not gated on `jev.available()`: with no key each semantic check
            # falls back to its deterministic half rather than vanishing, which
            # is the rule for every Jev check in PLAN-2026-09-22.md Phase 4.
            warnings += semantic_warnings(nodes, plan_text, slug, fields, sessions, folder,
                                          vault=vault)
        note = folder / "progress.md"
        note.write_text(progress_note(slug, folder, fields, nodes, plan_text,
                                      record_text, sessions, today))
        written.append(str(note.relative_to(vault)))
        subjects.append((slug, {"fields": fields, "nodes": nodes, "folder": folder}))

    # A review note is not a session note and deliberately lives outside
    # learn/subjects/, so the per-subject loop above never sees it -- but its
    # multiple-choice checks carry the same `key:` field and must obey the same
    # slot-rotation rule. Without this line a review would be the one place in
    # the vault where MC slots were ungated, which is precisely the kind of
    # silent gap PLAN-2026-09-22.md exists to close.
    warnings += g4_mc_slots("review", vault / "learn" / "reviews")
    _, setting_warning = rewards_setting(vault)
    warnings += [setting_warning] if setting_warning else []

    board = vault / "learn" / "Dashboard.md"
    board.write_text(dashboard(subjects, today, warnings, openings))
    written.append(str(board.relative_to(vault)))

    if not args.quiet:
        print("learn-status: wrote " + ", ".join(written))
        for report in openings:
            print("learn-status: open session note: " + report)
        for warning in warnings:
            print("learn-status: inconsistency: " + warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
