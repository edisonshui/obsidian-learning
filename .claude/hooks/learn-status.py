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
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import session_note  # noqa: E402
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
EDGE = re.compile(r"\b(n\d+)\b[^\n]*?-->[^\n]*?\b(n\d+)\b")


# --------------------------------------------------------------------- reading

def table_rows(text):
    """Pipe-table body rows as lists of stripped cells, skipping header and rule."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the |---|---| separator
        rows.append(cells)
    return rows[1:] if rows else []


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
    for cells in table_rows(section(plan_text, "Nodes")):
        if not cells or not NODE_ID.fullmatch(cells[0].strip()):
            continue
        node = cells[0].strip()
        entry = nodes.setdefault(node, {"id": node, "name": cells[1] if len(cells) > 1 else "",
                                        "status": "", "checked": "", "evidence": "",
                                        "prereqs": [], "plan_status": ""})
        if not entry["name"] and len(cells) > 1:
            entry["name"] = cells[1]
        if len(cells) >= 8:
            entry["prereqs"] = NODE_ID.findall(cells[-2])
            entry["plan_status"] = cells[-1].strip().lower()
    return nodes


def read_notes(folder, now):
    """Every note in `folder` that has frontmatter, parsed, oldest first."""
    notes = [session_note.read(path, now=now)
             for path in (sorted(folder.glob("*.md")) if folder.is_dir() else [])]
    return [note for note in notes if note.fields]


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
    match = ISO_DATE.search(checked or "")
    if not match:
        return None
    try:
        when = datetime.strptime(match.group(0), "%Y-%m-%d").date()
    except ValueError:
        return None  # well-shaped but impossible, e.g. 2026-13-45
    return (today - when).days


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

def open_notes(notes, subject):
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
                           "`/learn-end`. `/learn-resume` must finalize it before opening the next note."
                           % (label, note.hours))
        elif note.status == "stale pause":
            reports.append("%s: paused %.1f h ago, past the %d h bound -- a stale pause, not a break. "
                           "`/learn-resume` must finalize it before opening the next note."
                           % (label, note.hours, STALE_HOURS))
        else:
            reports.append("%s: paused %.1f h ago, inside the %d h bound -- a live break. "
                           "`/learn-resume %s` reopens this note and skips the decay check."
                           % (label, note.hours, STALE_HOURS, subject))
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
    """G4: the correct-answer slot on logged MC checks varies, per `tutor.md`'s
    construction rule -- never the same slot as the previous check, and across
    any five consecutive checks no slot holds the answer more than twice. Reads
    the `key: <slot>/<count>` field a logged check carries, in session order.
    """
    warnings = []
    if not folder.is_dir():
        return warnings
    keys = [(path.stem, key.slot) for path in sorted(folder.glob("*.md"))
            for key in session_note.read(path).keys]
    for index in range(1, len(keys)):
        prev_file, prev_slot = keys[index - 1]
        file, slot = keys[index]
        if slot == prev_slot:
            warnings.append("%s: %s repeats the previous check's correct-answer slot %d "
                            "(tutor.md, MC construction)" % (slug, file, slot))
    for index in range(4, len(keys)):
        window = keys[index - 4:index + 1]
        slots = [slot for _, slot in window]
        for slot in sorted(set(slots)):
            count = slots.count(slot)
            if count > 2:
                warnings.append("%s: slot %d holds the correct answer %d times in the 5 checks ending at %s "
                                "(tutor.md, MC construction)" % (slug, slot, count, window[-1][0]))
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
    for node in sorted(nodes, key=sort_key):
        entry = nodes[node]
        if entry["plan_status"] and entry["status"] and entry["plan_status"] != entry["status"]:
            warnings.append("%s %s: record says '%s', plan says '%s' (records.md: the two must agree)"
                            % (subject, node, entry["status"], entry["plan_status"]))
        if not entry["status"]:
            warnings.append("%s %s: in plan.md but missing from the record.md node table" % (subject, node))
    edges = set()
    for block in MERMAID.findall(plan_text):
        for line in block.splitlines():
            found = EDGE.search(line)
            if found:
                edges.add((found.group(1), found.group(2)))
    for node in sorted(nodes, key=sort_key):
        declared = set(nodes[node]["prereqs"]) - {node}
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
    parser.add_argument("--subject", help="with --due, restrict to one subject slug")
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

    vault = args.vault.resolve()
    root = vault / "learn" / "subjects"
    stamp = datetime.now()
    today = stamp.strftime("%Y-%m-%d")
    subjects, warnings, openings, written = [], [], [], []
    ranked = []  # (slug, nodes) for --due, collected before the write half of the loop

    if args.semantic:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import jev  # noqa: E402 -- only imported when explicitly asked for
        if not jev.available(vault) and not args.quiet:
            print("learn-status: --semantic requested but jev is not available "
                  "(no TYPESAFE_API_KEY or typesafe-sdk not installed) -- running the "
                  "deterministic fallback half of each semantic check instead")

    for folder in sorted(path for path in root.glob("*") if path.is_dir()) if root.is_dir() else []:
        slug = folder.name
        record, plan = folder / "record.md", folder / "plan.md"
        if not record.is_file():
            warnings.append("%s: no record.md" % slug)
            continue
        record_text = record.read_text()
        plan_text = plan.read_text() if plan.is_file() else ""
        fields = frontmatter(record)
        nodes = read_nodes(record_text, plan_text)
        notes = read_notes(folder / "sessions", stamp)
        sessions = [dict(note.fields, file=note.name) for note in notes]
        openings += open_notes(notes, slug)
        ranked.append((slug, nodes))
        if args.open_notes or args.due:
            continue  # read-only modes: report, write nothing
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
        rows, undated = due(ranked, stamp.date(), subject=args.subject,
                            per_subject=args.per_subject or None, limit=args.limit)
        print(due_report(rows, undated))
        return 0

    # A review note is not a session note and deliberately lives outside
    # learn/subjects/, so the per-subject loop above never sees it -- but its
    # multiple-choice checks carry the same `key:` field and must obey the same
    # slot-rotation rule. Without this line a review would be the one place in
    # the vault where MC slots were ungated, which is precisely the kind of
    # silent gap PLAN-2026-09-22.md exists to close.
    warnings += g4_mc_slots("review", vault / "learn" / "reviews")

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
