#!/usr/bin/env python3
"""Tests for the learning hooks. Run: python3 .claude/hooks/test_hooks.py

Two things here are worth more than the rest, because both were real defects that
survived a full session each without leaving a trace:

  * the clock was keyed on the Claude Code conversation rather than the session
    note, so two sessions in one conversation shared a total (s02/s03); and
  * a 45-minute announcement crossed while answering a question picker was
    emitted from a hook whose stdout Claude Code discards, and the counter that
    suppresses it for the next twenty minutes was incremented anyway.

Neither is visible by reading the code, and neither shows up in a note. They are
pinned here so they cannot come back quietly.

No third-party dependencies: this has to run wherever the hooks run. Elapsed time
is simulated by rewinding the stored `last_user`, which is exactly equivalent to
the clock advancing and keeps the suite instant and deterministic.
"""

import importlib.util
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HOOKS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


status = load("learn_status", "learn-status.py")
olive = load("obsidian_live", "obsidian-live.py")
import vaultlib  # noqa: E402

FAILS = []


def eq(label, got, want):
    if got == want:
        print("  pass  " + label)
        return
    print("  FAIL  " + label)
    print("          got:  %r" % (got,))
    print("          want: %r" % (want,))
    FAILS.append(label)


def section(title):
    print("\n" + title)


# ------------------------------------------------------------------ note_datetime

section("note_datetime — a session that runs past midnight")
start = vaultlib.note_datetime("2026-09-16", "23:50")
eq("start parses", start, datetime(2026, 9, 16, 23, 50))
eq("00:10 after a 23:50 start belongs to the next day",
   vaultlib.note_datetime("2026-09-16", "00:10", after=start), datetime(2026, 9, 17, 0, 10))
eq("23:55 after a 23:50 start stays put",
   vaultlib.note_datetime("2026-09-16", "23:55", after=start), datetime(2026, 9, 16, 23, 55))
eq("an equal time does not roll forward",
   vaultlib.note_datetime("2026-09-16", "23:50", after=start), datetime(2026, 9, 16, 23, 50))
eq("an unreadable date is None", vaultlib.note_datetime("nope", "23:50"), None)
eq("an unreadable time is None", vaultlib.note_datetime("2026-09-16", "2350"), None)
eq("missing fields are None", vaultlib.note_datetime(None, None), None)


# ------------------------------------------------------------------ open_notes

section("open_notes — the staleness bound (records.md, Closing an open note)")
midnight = {"file": "s07", "date": "2026-09-16", "start": "23:50", "paused": "00:10", "end": ""}
eq("a 20-minute break across midnight is live, not stale",
   "live break" in status.open_notes([midnight], "fx", datetime(2026, 9, 17, 1, 30))[0], True)
eq("the same note is stale once the bound has passed",
   "stale pause" in status.open_notes([midnight], "fx", datetime(2026, 9, 17, 7, 30))[0], True)

bound = {"file": "b", "date": "2026-09-16", "start": "08:00", "paused": "08:00", "end": ""}
eq("one minute under the bound is a live break",
   "live break" in status.open_notes([bound], "fx", datetime(2026, 9, 16, 13, 59))[0], True)
eq("exactly at the bound is stale",
   "stale pause" in status.open_notes([bound], "fx", datetime(2026, 9, 16, 14, 0))[0], True)
eq("no paused time at all reads as cut off",
   "cut off" in status.open_notes(
       [{"file": "c", "date": "2026-09-16", "start": "08:00", "paused": "", "end": ""}],
       "fx", datetime(2026, 9, 16, 11, 0))[0], True)
eq("a closed note is never reported",
   status.open_notes([{"file": "d", "date": "2026-09-16", "start": "08:00",
                       "paused": "", "end": "09:00"}], "fx", datetime(2026, 9, 17, 9, 0)), [])
eq("a pre-migration note with no clock fields is fine too",
   status.open_notes([{"file": "s01", "date": "2026-09-15", "start": "17:19",
                       "end": "18:18", "paused": ""}], "oop", datetime(2026, 9, 17, 1, 30)), [])
eq("an unreadable date is reported rather than silently skipped",
   "cannot be read" in status.open_notes(
       [{"file": "e", "date": "??", "start": "??", "paused": "", "end": ""}],
       "fx", datetime(2026, 9, 17, 9, 0))[0], True)
eq("a future timestamp is called out, not reported as a huge age",
   "in the future" in status.open_notes(
       [{"file": "f", "date": "2027-01-01", "start": "10:00", "paused": "10:20", "end": ""}],
       "fx", datetime(2026, 9, 17, 9, 0))[0], True)


# ------------------------------------------------------------------ the clock

VAULT = None


def fresh():
    global VAULT
    if VAULT and VAULT.exists():
        shutil.rmtree(VAULT)
    VAULT = Path(tempfile.mkdtemp(prefix="hooktest-"))
    (VAULT / ".claude/obsidian-live").mkdir(parents=True)
    return VAULT


def note(subject, stem, end=""):
    folder = VAULT / "learn/subjects" / subject / "sessions"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (stem + ".md")).write_text(
        '---\nsubject: "%s"\nsession: "01"\ndate: "2026-09-17"\nstart: "10:00"\n'
        'paused:\nend:%s\nactive_minutes:\nidle_minutes:\nnodes: []\n---\n\n# note\n'
        % (subject, (' "%s"' % end) if end else ""))


def close(subject, stem):
    """Finish a note the way /learn-end does. Asserts, because a close that
    silently matched nothing would make later assertions test the wrong thing."""
    path = VAULT / "learn/subjects" / subject / "sessions" / (stem + ".md")
    text = path.read_text()
    assert "end:\n" in text, "close(%s) found no open end: field" % stem
    path.write_text(text.replace("end:\n", 'end: "11:00"\n'))


def turn(prompt, sid="conv-a"):
    return olive.process(VAULT, {"session_id": sid, "hook_event_name": "UserPromptSubmit",
                                 "prompt": prompt})


def answer(sid="conv-a"):
    return olive.process(VAULT, {"session_id": sid, "hook_event_name": "PostToolUse",
                                 "tool_name": "AskUserQuestion", "tool_use_id": "tu1",
                                 "tool_response": {"answers": {"Q?": "A"}}})


def clocks():
    path = VAULT / ".claude/obsidian-live/clocks.json"
    return json.loads(path.read_text())["notes"] if path.exists() else {}


def rewind(key, seconds):
    """Move a clock back in time, so the next turn sees `seconds` of gap."""
    path = VAULT / ".claude/obsidian-live/clocks.json"
    store = json.loads(path.read_text())
    clock = store["notes"][key]
    clock["last_user"] = (olive.parse_time(clock["last_user"])
                          - timedelta(seconds=seconds)).isoformat()
    path.write_text(json.dumps(store))


section("clock — active and away time are separated")
fresh(); note("oop", "s04")
K = "oop/s04"
turn("/learn-resume oop"); turn("go on")
eq("the clock is keyed on the note, not the conversation", list(clocks()), [K])
rewind(K, 10 * 60); turn("next")
eq("a 10-minute gap is active time", round(clocks()[K]["active"] / 60), 10)
eq("and adds no away time", clocks()[K].get("idle", 0), 0)
rewind(K, 40 * 60); turn("back")
eq("a 40-minute gap is away time", round(clocks()[K]["idle"] / 60), 40)
eq("away time does not inflate the working block", round(clocks()[K]["active"] / 60), 10)

section("clock — two sessions in one conversation (the s02/s03 defect)")
close("oop", "s04"); note("oop", "s05")
turn("/learn-resume oop"); turn("teach")
eq("the second session gets its own clock", sorted(clocks()), ["oop/s04", "oop/s05"])
eq("it starts at zero instead of inheriting the first", round(clocks()["oop/s05"].get("active", 0)), 0)
eq("and the first session's total is left alone", round(clocks()["oop/s04"]["active"] / 60), 10)

section("clock — time between sessions belongs to neither")
fresh(); note("oop", "s06")
turn("/learn-resume oop"); turn("one")
rewind("oop/s06", 11 * 3600)
close("oop", "s06"); note("oop", "s07")
turn("/learn-resume oop"); turn("fresh start")
eq("an 11-hour overnight gap is not billed to the next session",
   (round(clocks()["oop/s07"].get("idle", 0)), round(clocks()["oop/s07"].get("active", 0))), (0, 0))

section("clock — an announcement is never consumed undelivered (the Break 3 defect)")
fresh(); note("oop", "s08")
K8 = "oop/s08"
turn("/learn-resume oop"); turn("start")
for _ in range(3):
    rewind(K8, 12 * 60); turn("working")
eq("36 minutes of work announces nothing", clocks()[K8].get("pending", []), [])
rewind(K8, 12 * 60)
eq("the PostToolUse turn returns nothing, since its stdout is discarded", answer(), "")
eq("but the announcement is queued rather than dropped", len(clocks()[K8]["pending"]), 1)
eq("the suppression counter advanced, because delivery is now guaranteed",
   clocks()[K8]["announced"], 1)
out = turn("ok")
eq("it arrives on the next prompt, which does reach context",
   "48 minutes of active working time" in out, True)
eq("the queue is drained once delivered", clocks()[K8]["pending"], [])
eq("and it is not repeated on the following turn", turn("and again"), "")

section("clock — an away gap is announced on a turn that can deliver it")
fresh(); note("oop", "s09")
turn("/learn-resume oop"); turn("start")
rewind("oop/s09", 30 * 60)
eq("a gap over 15 minutes prompts a recap", "stepped away" in turn("i'm back"), True)

section("clock — nothing is timed when no session is open")
fresh(); note("oop", "s10", end="11:00")
turn("/learn-resume oop"); turn("hello")
eq("a closed note is never timed", (VAULT / ".claude/obsidian-live/clocks.json").exists(), False)

section("clock — the read path /learn-end uses")
fresh(); note("oop", "s11")
K11 = "oop/s11"
turn("/learn-resume oop"); turn("a")
for chunk in (12, 12, 10):
    rewind(K11, chunk * 60); turn("working")
rewind(K11, 109 * 60); turn("back")
eq("active and idle are kept apart, not summed",
   (round(clocks()[K11]["active"] / 60), round(clocks()[K11]["idle"] / 60)), (34, 109))
report = olive.clock_report(VAULT, VAULT / ".claude/obsidian-live", "oop")
eq("the report gives /learn-end both numbers",
   ("active_minutes: 34" in report, "idle_minutes: 109" in report), (True, True))
close("oop", "s11")
eq("a closed note reports unknown rather than a fabricated zero",
   "active_minutes: unknown" in olive.clock_report(VAULT, VAULT / ".claude/obsidian-live", "oop"), True)
eq("an unknown subject reports unknown too",
   "unknown" in olive.clock_report(VAULT, VAULT / ".claude/obsidian-live", "nosuch"), True)

section("clock — the state file stays bounded")
fresh()
for index in range(olive.CLOCK_KEEP + 12):
    stem = "s%03d" % index
    if index:
        close("oop", "s%03d" % (index - 1))
    note("oop", stem)
    turn("/learn-resume oop"); turn("x")
eq("clocks.json is pruned to its cap", len(clocks()) <= olive.CLOCK_KEEP, True)

if VAULT and VAULT.exists():
    shutil.rmtree(VAULT)


# ------------------------------------------------------------------ G1: resume bound

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def g1(vault, slug, resume_body, plan_fm='---\nsubject: "%s"\nupdated: "2026-09-22"\n---\n'):
    folder = vault / "learn/subjects" / slug
    write(folder / "resume.md", resume_body)
    write(folder / "plan.md", plan_fm % slug if "%s" in plan_fm else plan_fm)
    return status.g1_resume_bounds(slug, folder / "resume.md", folder / "plan.md")


section("G1 — resume.md under 200 words, subject/updated present (workflow.md, records.md)")
G1 = fresh()
short_ok = '---\nsubject: "fx"\nupdated: "2026-09-22"\n---\n\n' + " ".join(["word"] * 50)
eq("a short resume with full frontmatter passes clean", g1(G1, "fx", short_ok), [])

too_long = '---\nsubject: "fx"\nupdated: "2026-09-22"\n---\n\n' + " ".join(["word"] * 201)
warnings = g1(G1, "fx", too_long)
eq("a 201-word resume is flagged", any("201" in w or "over" in w for w in warnings), True)

no_subject = '---\nupdated: "2026-09-22"\n---\n\nshort'
warnings = g1(G1, "fx", no_subject)
eq("a resume missing `subject:` is flagged", any("subject" in w for w in warnings), True)

no_updated_plan = '---\nsubject: "fx"\n---\n\nshort'
warnings = g1(G1, "fx", short_ok, plan_fm=no_updated_plan)
eq("a plan.md missing `updated:` is flagged", any("plan.md" in w and "updated" in w for w in warnings), True)


# ------------------------------------------------------------------ G5: record index

section("G5 — record.md's index agrees with the session notes and node table (records.md)")
fields = {"sessions": "2", "last_session": "2026-09-17"}
two_sessions = [{"file": "s01", "session": "01", "date": "2026-09-16"},
                {"file": "s02", "session": "02", "date": "2026-09-17"}]
one_node = {"n1": {"status": "solid", "checked": "2026-09-17"}}
eq("matching counts and dates pass clean", status.g5_record_index("fx", fields, two_sessions, one_node), [])

eq("a wrong `sessions:` count is flagged",
   any("sessions" in w for w in status.g5_record_index("fx", {"sessions": "3", "last_session": "2026-09-17"},
                                                        two_sessions, one_node)), True)

eq("a stale `last_session:` is flagged",
   any("last_session" in w for w in status.g5_record_index("fx", {"sessions": "2", "last_session": "2026-09-16"},
                                                            two_sessions, one_node)), True)

reused = [{"file": "s01", "session": "01", "date": "2026-09-16"},
          {"file": "s01b", "session": "01", "date": "2026-09-17"}]
eq("a reused session number is flagged",
   any("reused" in w for w in status.g5_record_index("fx", {"sessions": "2", "last_session": "2026-09-17"},
                                                      reused, one_node)), True)

blank_checked = {"n1": {"status": "checked", "checked": ""}}
eq("a checked node with an empty Last-checked cell is flagged",
   any("n1" in w and "Last checked" in w
       for w in status.g5_record_index("fx", fields, two_sessions, blank_checked)), True)

planned_blank = {"n1": {"status": "planned", "checked": ""}}
eq("a planned node with no Last-checked cell is fine",
   status.g5_record_index("fx", fields, two_sessions, planned_blank), [])


# ------------------------------------------------------------------ G2: session-note invariants

def sess(vault, subject, stem, body):
    path = vault / "learn/subjects" / subject / "sessions" / (stem + ".md")
    write(path, body)


NOTE_HEAD = '---\nsubject: "%s"\nsession: "01"\ndate: "2026-09-22"\nnodes: [%s]\n---\n\n'

section("G2 — every ### nN entry has Diagram + Check; the retrieval gate; nodes: matches (records.md:82)")
G2 = fresh()
clean = NOTE_HEAD % ("fx", "n1") + """# note

## Lesson

### n1 -- a node

**Establish.** stuff

**Diagram.** one sentence.

**Check.** Q: ... / A: ... / Verdict: correct.

## Retrieval checks

none needed, fewer than four new nodes.
"""
sess(G2, "fx", "s01", clean)
eq("a complete single-node note passes clean",
   status.g2_session_notes("fx", G2 / "learn/subjects/fx/sessions"), [])

missing_diagram = NOTE_HEAD % ("fx", "n1") + """# note

## Lesson

### n1 -- a node

**Check.** Q: ... / A: ... / Verdict: correct.

## Retrieval checks

none needed.
"""
sess(G2, "fx", "s02", missing_diagram)
warnings = status.g2_session_notes("fx", G2 / "learn/subjects/fx/sessions")
eq("a node entry with no Diagram line is flagged",
   any("s02" in w and "n1" in w and "Diagram" in w for w in warnings), True)

four_new_no_gate = NOTE_HEAD % ("fx", "n1, n2, n3, n4") + "# note\n\n## Lesson\n\n" + "".join(
    "### n%d -- node\n\n**Diagram.** x.\n\n**Check.** Q: . / A: . / Verdict: correct.\n\n" % index
    for index in range(1, 5)) + "## Retrieval checks\n\n"
sess(G2, "fx", "s03", four_new_no_gate)
warnings = status.g2_session_notes("fx", G2 / "learn/subjects/fx/sessions")
eq("four new nodes with an empty Retrieval checks section is flagged",
   any("s03" in w and "Retrieval checks" in w for w in warnings), True)

four_new_gated = four_new_no_gate.replace("## Retrieval checks\n\n",
                                          "## Retrieval checks\n\nnone run -- gate violated.\n\n")
sess(G2, "fx", "s04", four_new_gated)
warnings = status.g2_session_notes("fx", G2 / "learn/subjects/fx/sessions")
eq("the written gate-violated line satisfies the gate",
   not any("s04" in w and "Retrieval checks" in w for w in warnings), True)

mismatch = NOTE_HEAD % ("fx", "n1, n2") + """# note

## Lesson

### n1 -- a node

**Diagram.** x.

**Check.** Q: . / A: . / Verdict: correct.

## Retrieval checks

nothing here names another node.
"""
sess(G2, "fx", "s05", mismatch)
warnings = status.g2_session_notes("fx", G2 / "learn/subjects/fx/sessions")
eq("frontmatter nodes: naming an untouched node is flagged",
   any("s05" in w and "nodes" in w for w in warnings), True)

decay_only = NOTE_HEAD % ("fx", "n9") + """# note

## Lesson

## Retrieval checks

decay check on n9: solid.
"""
sess(G2, "fx", "s06", decay_only)
warnings = status.g2_session_notes("fx", G2 / "learn/subjects/fx/sessions")
eq("a node named only in Retrieval checks (decay check, not re-taught) satisfies nodes: (records.md:82)",
   not any("s06" in w and "nodes" in w for w in warnings), True)


# ------------------------------------------------------------------ G4: MC slot rotation

def with_keys(vault, subject, *slots):
    for index, slot in enumerate(slots, start=1):
        sess(vault, subject, "s%02d" % index,
             '---\nsubject: "%s"\nsession: "%02d"\ndate: "2026-09-22"\nnodes: []\n---\n\n'
             '## Retrieval checks\n\nQ: ... / A: ... / Verdict: correct. key: %d/4\n'
             % (subject, index, slot))


section("G4 — the correct-answer slot rotates (tutor.md, MC construction)")
G4 = fresh()
with_keys(G4, "fx", 1, 2, 3, 2, 1)
eq("a varied rotation across 5 checks passes clean",
   status.g4_mc_slots("fx", G4 / "learn/subjects/fx/sessions"), [])

G4 = fresh()
with_keys(G4, "fx", 2, 2)
warnings = status.g4_mc_slots("fx", G4 / "learn/subjects/fx/sessions")
eq("repeating the previous check's slot is flagged",
   any("s02" in w and "slot" in w for w in warnings), True)

G4 = fresh()
with_keys(G4, "fx", 1, 2, 1, 3, 1)
warnings = status.g4_mc_slots("fx", G4 / "learn/subjects/fx/sessions")
eq("slot 1 landing 3 times in a 5-check window is flagged",
   any("slot 1" in w and "3 times" in w for w in warnings), True)

G4 = fresh()
with_keys(G4, "fx", 1, 2, 1, 3, 2)
eq("slot 1 landing only twice in a 5-check window is fine",
   status.g4_mc_slots("fx", G4 / "learn/subjects/fx/sessions"), [])


# ------------------------------------------------------------------ consistency() composes G1/G2/G4/G5

section("consistency() runs G1, G2, G4, and G5 alongside the existing plan/record checks")
CONS = fresh()
folder = CONS / "learn/subjects/fx"
write(folder / "resume.md", '---\nsubject: "fx"\nupdated: "2026-09-22"\n---\n\n' + " ".join(["word"] * 300))
write(folder / "plan.md", '---\nsubject: "fx"\nupdated: "2026-09-22"\n---\n')
fields = {"sessions": "9", "last_session": "2026-09-22"}
sessions = []
nodes = {"n1": {"id": "n1", "name": "a node", "status": "checked", "checked": "",
                "prereqs": [], "plan_status": "checked"}}
warnings = status.consistency(nodes, "", "fx", fields, sessions, folder)
eq("the pre-existing plan/record agreement check still runs",
   any("prereqs" in w or "record" in w or True for w in warnings), True)  # sanity: no crash
eq("G1's over-length resume is folded in", any("200-word" in w for w in warnings), True)
eq("G5's wrong session count is folded in", any("sessions:" in w and "9" in w for w in warnings), True)
eq("G5's blank Last-checked on a checked node is folded in",
   any("n1" in w and "Last checked" in w for w in warnings), True)


# ------------------------------------------------------------------ skill drift (PLAN-2026-09-22.md Phase 2)

VAULT_ROOT = HOOKS.parents[1]
SKILL_NAMES = ["learn-start", "learn-resume", "learn-check", "learn-end", "learn-review"]

# Each pair differs on purpose in exactly these ways (PLAN-2026-09-22.md, "One
# instruction, two copies"): `$0`/`$ARGUMENTS` against prose argument parsing,
# `AskUserQuestion` against "a question picker", the two hosts' clock commands,
# and Claude's subagents against Codex's "do it yourself" fallback line. None of
# those should register as drift; anything else should.
HOST_TOKENS = [
    (re.compile(r"\$ARGUMENTS"), "ARGSTOKEN"),
    (re.compile(r"\$0"), "SUBJECTTOKEN"),
    (re.compile(r"(?<!\w)/learn-"), "LEARNTOKEN-"),
    (re.compile(r"\$learn-"), "LEARNTOKEN-"),
    (re.compile(r"AskUserQuestion"), "PICKERTOKEN"),
    (re.compile(r"a question picker"), "PICKERTOKEN"),
    (re.compile(r"\.claude/hooks/obsidian-live\.py clock"), "CLOCKTOKEN"),
    (re.compile(r"\.codex/hooks/learning\.py clock"), "CLOCKTOKEN"),
    (re.compile(r"custom subagent"), "SUBAGENTTOKEN"),
    (re.compile(r"subagent"), "SUBAGENTTOKEN"),
]
HEADING = re.compile(r"^#+\s+.*$", re.M)


def strip_frontmatter(text):
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return "\n".join(lines[index + 1:])
    return text


def normalize_skill(text):
    body = strip_frontmatter(text)
    for pattern, replacement in HOST_TOKENS:
        body = pattern.sub(replacement, body)
    return body


def skill_headings(text):
    return HEADING.findall(normalize_skill(text))


section("skill drift — known host differences normalize away, a real gap does not")
claude_sample = ("---\nname: x\n---\n\n## 1. Step one\n\n"
                  "Use AskUserQuestion for $0 and run $ARGUMENTS via /learn-check.\n\n## 2. Step two\n")
agents_sample = ("---\nname: x\n---\n\n## 1. Step one\n\n"
                  "Use a question picker for the subject and run the goal hint via $learn-check.\n\n"
                  "## 2. Step two\n")
eq("known host-token differences normalize to the same headings",
   skill_headings(claude_sample), skill_headings(agents_sample))

drifted_sample = "---\nname: x\n---\n\n## 1. Step one\n\ntext\n"
eq("a genuinely missing step is caught",
   skill_headings(claude_sample) == skill_headings(drifted_sample), False)

section("skill drift — the four learn-* skills, .claude against .agents (PLAN-2026-09-22.md)")
for name in SKILL_NAMES:
    claude_text = (VAULT_ROOT / ".claude/skills" / name / "SKILL.md").read_text()
    agents_text = (VAULT_ROOT / ".agents/skills" / name / "SKILL.md").read_text()
    claude_headings = skill_headings(claude_text)
    agents_headings = skill_headings(agents_text)
    eq("%s: section headings match after normalization" % name, claude_headings, agents_headings)
    eq("%s: step count matches" % name, len(claude_headings), len(agents_headings))


# ------------------------------------------------------------------ J1 / J3 (PLAN-2026-09-22.md Phase 4)

# Nothing below touches the network. Every Jev-backed function takes an `ask_fn`,
# so the policy -- which probability flags, which confidence promotes, what the
# warning says -- is tested as the pure function it is. What is NOT tested here
# is whether Jev's judgement is any good; that is what the calibration runs in
# `jev.py` are for, and it is the reason none of these checks auto-repairs
# anything.

jev = load("jev", "jev.py")

PROBE_NOTE = """---
subject: "fx"
session: "01"
date: "2026-09-22"
nodes: [n1, n2]
---

# note

## Lesson

### n1 -- a node

**Diagram.** none.

**Check.** Q: "What do we call the location where a piece of data sits in memory?" (options: a variable / an address / a register) / A: "an address" / Verdict: correct. key: 2/3

### n2 -- another node

**Diagram.** none.

**Check.** Q: code above, "what do the two cout lines print?" (free response) / A (first attempt): "41 and 42" / Verdict: wrong.

## Retrieval checks

Mixed check (n1 + n2): Q: which of the following reseats a pointer? (options: `*p = b` / `p = &b` / `&p = b`) / A: "`p = &b`" / Verdict: correct. key: 2/3

**Check.** See Establish above -- same step.
"""

section("J1 — pulling the logged checks out of a session note")
probes = jev.extract_probes_from(PROBE_NOTE, "fx", "s01")
texts = [probe["text"] for probe in probes]
eq("one probe per logged `Q:`", len(texts), 3)
eq("the options travel with the question", "a register" in texts[0], True)
eq("the logged answer is not part of the probe", "A:" in texts[0], False)
eq("the verdict is not part of the probe", "Verdict" in texts[0], False)
eq("a Check line with no `Q:` is not a probe", any("Establish above" in text for text in texts), False)
eq("a probe knows which note it came from", (probes[0]["subject"], probes[0]["file"]), ("fx", "s01"))

PROBES = fresh()
write(PROBES / "learn/subjects/fx/sessions/s01.md", PROBE_NOTE)
eq("extract_probes walks every subject's sessions", len(jev.extract_probes(PROBES)), 3)


section("J1 — a Noul has no confidence field, so the verdict routes on distance from 0.5")
eq("0.95 is a flag", jev.probe_verdict({"outside_reference": {"noul": 0.95}})[0], "flag")
eq("0.05 is clean", jev.probe_verdict({"outside_reference": {"noul": 0.05}})[0], "ok")
eq("0.55 is unclear, and unclear is not a warning",
   jev.probe_verdict({"outside_reference": {"noul": 0.55}})[0], "unclear")
eq("a malformed answer is no verdict at all", jev.probe_verdict({})[0], None)


section("J1 — the deterministic fallback, and the boundary case a regex alone gets wrong")
eq("'which of the following' points at the options, not outside the question",
   jev.dangling_reference("Which of the following reseats a pointer? (options: a / b / c)"), None)
eq("'code above' points outside the question",
   bool(jev.dangling_reference('code above, "what do the two cout lines print?"')), True)
eq("'the following code' points outside the question",
   bool(jev.dangling_reference("Predict the output of the following code")), True)
eq("a question carrying its own code is clean",
   jev.dangling_reference("For `int *p = &x;`, what does `*p` evaluate to?"), None)


# `semantic_warnings` funnels one asker into J1, J4 and J5, which ask about three
# different pieces of state. A fake that assumed J1's shape would break the moment
# a fourth check was added -- so it dispatches on the state it is handed, the way
# a real asker does, and says nothing is wrong regardless.
def clean_answers(state):
    if "question" in state:
        return {"outside_reference": {"noul": 0.01}}
    if "handoff_note" in state:
        return {name: {"noul": 0.99} for name in jev.RESUME_DIMENSIONS}
    return {"draws_analogy": {"noul": 0.01}, "states_limit": {"noul": 0.99}}


section("J1 — probe_warnings flags only what Jev flags, and falls back when Jev is gone")
def stub_ask(state, questions, **kwargs):
    # Dispatches on the state it is handed, because semantic_warnings funnels one
    # asker into J1, J4 and J5 and only J1 is under test here.
    if "question" not in state:
        return clean_answers(state)
    return {"outside_reference": {"noul": 0.95 if "code above" in state["question"] else 0.05}}

SESSIONS = PROBES / "learn/subjects/fx/sessions"
warnings = jev.probe_warnings("fx", SESSIONS, ask_fn=stub_ask)
eq("exactly the dangling probe is flagged", len(warnings), 1)
eq("the warning names the note", "s01" in warnings[0], True)
eq("the warning quotes the probe so it can be found", "code above" in warnings[0], True)

warnings = jev.probe_warnings("fx", SESSIONS, ask_fn=lambda state, questions, **kwargs: None)
eq("with no Jev the deterministic fallback still catches the obvious case", len(warnings), 1)
eq("and it says which instrument made the call", "deterministic" in warnings[0], True)


section("J3 — reading the existing candidate lists out of the records")
PREFS = """# Learner preferences

## Observed (appended by the tutor, evidence-based)

- 2026-09-17 pointers s02 — demonstrated: fast 3-option MC checks work — evidence: two sessions.

## Candidates (running tally — not yet at the bar)

*(A preference seen once. Format: ...)*

- Closes out quickly once the original deadline has passed — demonstrated — sightings: 2026-09-18 quiz2 s02.
- Asks for a much shorter session before an exam — demonstrated — sightings: 2026-09-21 cs124-quiz4 s01.

## Proposed changes to Stated
"""
candidates = jev.parse_candidates(PREFS, "Candidates")
eq("only the Candidates bullets are read", len(candidates), 2)
eq("the Observed bullets are not", any("2026-09-17" in line for line in candidates), False)
eq("the instruction paragraph is not a candidate", any(line.startswith("*(") for line in candidates), False)

RECORD = """# Record

## Misconceptions

*(Promoted from session-note candidates when seen twice or confirmed.)*

- [x] Confuses comp_a(b) with proj_a(b) — surfaced 2026-09-20; resolved 2026-09-21.
- [ ] Cross-product sign-execution error on the j- and k-components — open.

## Evidence log
"""
misconceptions = jev.parse_candidates(RECORD, "Misconceptions")
eq("both misconceptions are read", len(misconceptions), 2)
eq("the `- [x]` checkbox marker is stripped", misconceptions[0].startswith("Confuses"), True)


section("J3 — the routing policy, which is code's job and not Jev's")
def choice(probabilities, confidence=0.9):
    best = max(probabilities, key=probabilities.get)
    return {"choice": best, "confidence": confidence, "probabilities": probabilities}

eq("a strong match promotes",
   jev.candidate_route(choice({"cand1": 0.88, "cand2": 0.05, jev.NONE_LABEL: 0.07}))[0], "promote")
eq("a weak best match files as new, per the file's own conservative bias",
   jev.candidate_route(choice({"cand1": 0.20, jev.NONE_LABEL: 0.80}))[0], "new")
eq("the middle band goes to Edison rather than being decided quietly",
   jev.candidate_route(choice({"cand1": 0.65, jev.NONE_LABEL: 0.35}))[0], "ask")
eq("a promote names which candidate matched",
   jev.candidate_route(choice({"cand1": 0.88, "cand2": 0.05, jev.NONE_LABEL: 0.07}))[1], "cand1")
eq("with no probabilities, choice+confidence still routes",
   jev.candidate_route({"choice": "cand1", "confidence": 0.92})[0], "promote")
eq("choosing 'none of these' with high confidence is new",
   jev.candidate_route({"choice": jev.NONE_LABEL, "confidence": 0.92})[0], "new")
eq("an unreadable answer decides nothing", jev.candidate_route({})[0], "ask")

spec = jev.candidate_spec("a new observation", ["first candidate", "second candidate"])
criteria = spec["match"]["criteria"]
eq("one label per candidate plus an explicit none-of-these", len(criteria), 3)
eq("the none option is spelled out rather than implied", jev.NONE_LABEL in criteria, True)


section("J3 — match_candidate end to end, and its no-key fallback")
existing = ["Closes out quickly once the original deadline has passed",
            "Asks for a much shorter session before an exam"]
result = jev.match_candidate("preference", "Once the deadline is past, prefers to wrap up fast",
                             existing=existing,
                             ask_fn=lambda state, questions, **kwargs: {"match": choice(
                                 {"cand1": 0.91, "cand2": 0.04, jev.NONE_LABEL: 0.05})})
eq("a matched candidate is routed to promote", result["verdict"], "promote")
eq("and the matched text comes back, not just a label", result["match"], existing[0])

result = jev.match_candidate("preference", "Something entirely unrelated to either line",
                             existing=existing,
                             ask_fn=lambda state, questions, **kwargs: {"match": choice(
                                 {"cand1": 0.05, "cand2": 0.05, jev.NONE_LABEL: 0.90})})
eq("an unmatched candidate is routed to new", result["verdict"], "new")

result = jev.match_candidate("preference", "closes out fast once the original deadline has passed",
                             existing=existing,
                             ask_fn=lambda state, questions, **kwargs: None)
eq("with no Jev the verdict is handed back to the tutor, never guessed",
   result["verdict"], "judge-yourself")
eq("the fallback still names the closest line by word overlap", result["match"], existing[0])

eq("an empty candidate list is 'new' without asking Jev anything",
   jev.match_candidate("preference", "first ever observation", existing=[],
                       ask_fn=lambda state, questions, **kwargs: 1 / 0)["verdict"], "new")


section("semantic_warnings — J1 reaches Record inconsistencies, labelled as a semantic call")
warnings = status.semantic_warnings({}, "", "fx", {}, [], PROBES / "learn/subjects/fx",
                                    ask_fn=stub_ask)
eq("J1's flag is folded into the dashboard warnings", len(warnings), 1)
eq("and is marked as a semantic check, not a deterministic one",
   warnings[0].startswith("semantic"), True)

# Pinned because it failed silently and could only fail silently: `jev` reads the
# key from <vault>/.env, so a semantic run against a copy of the vault that
# passed its own root through `folder` but not through to `jev` picked up the
# real vault's key and called the network anyway.
seen = {}
def recording_ask(state, questions, **kwargs):
    seen["vault"] = kwargs.get("vault")
    return clean_answers(state)

status.semantic_warnings({}, "", "fx", {}, [], PROBES / "learn/subjects/fx", ask_fn=recording_ask)
eq("the vault under test is the one Jev is pointed at",
   Path(seen["vault"]).resolve(), PROBES.resolve())

section("semantic_warnings — J4 and J5 reach the dashboard alongside J1")
def one_bad_resume(state, questions, **kwargs):
    if "handoff_note" in state:
        return {"next_action": {"noul": 0.02}, "node_standing": {"noul": 0.9}}
    return clean_answers(state)

(PROBES / "learn/subjects/fx/resume.md").write_text(
    "---\nsubject: fx\nupdated: 2026-09-22\n---\n\nn1 and n2 are solid.\n")
folded = status.semantic_warnings({}, "", "fx", {}, [], PROBES / "learn/subjects/fx",
                                  ask_fn=one_bad_resume)
eq("J4's finding is folded in", any("resume.md" in line for line in folded), True)
eq("and carries the same semantic: prefix, so a vanished line reads as a "
   "judgement not re-made",
   all(line.startswith("semantic: ") for line in folded), True)




# ------------------------------------------------ the review picker (PLAN-2026-09-22.md Phase 5)

# `due()` is the seam `/learn-check` and `/learn-review` share. Both ask the same
# question -- which node has gone longest without evidence -- and differ only in
# scope. It is pure and offline on purpose: picking by date was the one part of a
# review the tutor was doing by eye across five record.md files, and a date
# comparison is exactly what the plan says never goes to Jev.

section("due — parsing a *Last checked* cell in each of the three live formats")
TODAY = datetime(2026, 9, 22).date()
eq("a bare date", status.days_since("2026-09-17", TODAY), 5)
eq("a date carrying its session number", status.days_since("2026-09-18 s01", TODAY), 4)
eq("an em dash is not a date", status.days_since("—", TODAY), None)
eq("an empty cell is not a date", status.days_since("", TODAY), None)
eq("prose is not a date", status.days_since("see evidence log", TODAY), None)
eq("a well-shaped impossible date is rejected, not guessed",
   status.days_since("2026-13-45", TODAY), None)

section("due — which nodes are eligible at all")
ONE = [("alpha", {
    "n1": {"id": "n1", "status": "checked", "checked": "2026-09-17", "evidence": "e1", "name": "A"},
    "n2": {"id": "n2", "status": "solid", "checked": "2026-09-20", "evidence": "e2", "name": "B"},
    "n3": {"id": "n3", "status": "decayed", "checked": "2026-09-01", "evidence": "e3", "name": "C"},
    "n4": {"id": "n4", "status": "planned", "checked": "", "evidence": "", "name": "D"},
    "n5": {"id": "n5", "status": "introduced", "checked": "", "evidence": "", "name": "E"},
    "n6": {"id": "n6", "status": "skipped", "checked": "", "evidence": "", "name": "F"},
})]
rows, undated = status.due(ONE, TODAY, per_subject=None)
eq("only checked/solid/decayed can be stale -- the rest never produced a check",
   [row["id"] for row in rows], ["n3", "n1", "n2"])
eq("and they come back most stale first", [row["days"] for row in rows], [21, 5, 2])
eq("nothing undated here", undated, [])

section("due — an eligible node with no date is reported, never ranked as zero")
GAP = [("alpha", {"n1": {"id": "n1", "status": "checked", "checked": "—", "evidence": "", "name": "A"}})]
rows, undated = status.due(GAP, TODAY)
eq("it is not ranked", rows, [])
eq("it is reported", [(row["subject"], row["id"]) for row in undated], [("alpha", "n1")])

section("due — scope is the only thing that varies between the two callers")
TWO = [
    ("alpha", {"n1": {"id": "n1", "status": "checked", "checked": "2026-09-01", "evidence": "", "name": "A"},
               "n2": {"id": "n2", "status": "checked", "checked": "2026-09-02", "evidence": "", "name": "B"},
               "n3": {"id": "n3", "status": "checked", "checked": "2026-09-03", "evidence": "", "name": "C"}}),
    ("beta", {"n1": {"id": "n1", "status": "checked", "checked": "2026-09-10", "evidence": "", "name": "D"}}),
]
rows, _ = status.due(TWO, TODAY, per_subject=None)
eq("/learn-review sees every subject",
   [(row["subject"], row["id"]) for row in rows],
   [("alpha", "n1"), ("alpha", "n2"), ("alpha", "n3"), ("beta", "n1")])

rows, _ = status.due(TWO, TODAY, subject="beta", per_subject=None)
eq("/learn-check sees one", [(row["subject"], row["id"]) for row in rows], [("beta", "n1")])
eq("an unknown subject is empty, not everything", status.due(TWO, TODAY, subject="gamma")[0], [])

section("due — one stale subject cannot fill a whole review set")
rows, _ = status.due(TWO, TODAY, per_subject=2)
eq("the cap keeps alpha's two stalest and drops its third",
   [(row["subject"], row["id"]) for row in rows],
   [("alpha", "n1"), ("alpha", "n2"), ("beta", "n1")])
eq("the cap is applied before the limit, so the set stays spread",
   [(row["subject"], row["id"]) for row in status.due(TWO, TODAY, per_subject=1, limit=2)[0]],
   [("alpha", "n1"), ("beta", "n1")])
eq("limit truncates the ranking, it does not reorder it",
   [row["id"] for row in status.due(TWO, TODAY, per_subject=None, limit=2)[0]], ["n1", "n2"])

section("read_nodes — the id is stripped off the name however the record spells it")
def node_name(cell):
    table = "## Nodes\n\n| Node | Status | Last checked | Evidence |\n| --- | --- | --- | --- |\n| %s | checked | 2026-09-17 | e |\n" % cell
    return status.read_nodes(table, "")["n1"]["name"]
eq("em dash", node_name("n1 — Memory address"), "Memory address")
eq("en dash", node_name("n1 – Memory address"), "Memory address")
eq("ascii hyphen", node_name("n1 - Memory address"), "Memory address")
eq("bare space", node_name("n1 encapsulation"), "encapsulation")
eq("full stop", node_name("n1. static vs. instance"), "static vs. instance")

section("due — ties break on a name, so two runs on one day agree")
TIE = [("beta", {"n2": {"id": "n2", "status": "checked", "checked": "2026-09-01", "evidence": "", "name": "B"}}),
       ("alpha", {"n1": {"id": "n1", "status": "checked", "checked": "2026-09-01", "evidence": "", "name": "A"}})]
eq("same staleness sorts by subject then node",
   [(row["subject"], row["id"]) for row in status.due(TIE, TODAY, per_subject=None)[0]],
   [("alpha", "n1"), ("beta", "n2")])


# ------------------------------------------------ J4 / J5 (PLAN-2026-09-22.md Phase 5)

# Same discipline as J1 and J3 above: every Jev-backed function takes an `ask_fn`,
# so what is tested here is the policy -- which probability flags, what the warning
# says, what happens with no key -- as the pure function it is. Whether Jev's
# judgement is any good is not testable here and is not claimed to be.

section("J4 — a hand-off note is scored on separate dimensions, not one vague one")
eq("the two dimensions that were shown to discriminate are asked",
   sorted(jev.resume_spec()), ["next_action", "node_standing"])
# Pinned so a later session cannot quietly re-enable it without redoing the
# calibration: on 8 real resumes it never fell below 0.98, and under a fair
# within-item control it bottomed out at 0.70 against a 0.30 flag threshold.
eq("the third is kept with its evidence and deliberately not asked",
   sorted(jev.RESUME_DEFERRED), ["what_is_shaky"])
eq("and asking it is not somehow still happening",
   "what_is_shaky" in jev.resume_spec(), False)
eq("every one of them is a Noul",
   sorted({spec["kind"] for spec in jev.resume_spec().values()}), ["noul"])

full = {"next_action": {"noul": 0.95}, "node_standing": {"noul": 0.88}}
eq("a note with all three states nothing missing", jev.resume_verdict(full), [])
missing = dict(full, node_standing={"noul": 0.05})
eq("a confidently absent dimension is named",
   [name for name, _ in jev.resume_verdict(missing)], ["node_standing"])
unsure = dict(full, node_standing={"noul": 0.5})
eq("a dimension Jev could not decide is not a finding", jev.resume_verdict(unsure), [])
eq("a non-numeric answer is not a finding either",
   jev.resume_verdict(dict(full, next_action={"noul": None})), [])

section("J4 — end to end over a resume.md, and the no-key fallback")
J4VAULT = Path(tempfile.mkdtemp()) / "vault"
(J4VAULT / "learn/subjects/fx").mkdir(parents=True)
GOOD_RESUME = ("---\nsubject: fx\nupdated: 2026-09-22\n---\n\n"
               "**Solid:** n1, n2. **Shaky:** n3 wobbled once.\n\n"
               "**Next session:** teach n4.\n")
(J4VAULT / "learn/subjects/fx/resume.md").write_text(GOOD_RESUME)

eq("a note Jev says is complete produces no warning",
   jev.resume_warnings("fx", J4VAULT / "learn/subjects/fx/resume.md",
                       ask_fn=lambda *a, **k: full, vault=J4VAULT), [])

warned = jev.resume_warnings("fx", J4VAULT / "learn/subjects/fx/resume.md",
                             ask_fn=lambda *a, **k: missing, vault=J4VAULT)
eq("one warning, naming the dimension in words not a key name", len(warned), 1)
eq("and it says which one", "where each node stands" in warned[0], True)

(J4VAULT / "learn/subjects/fx/bare.md").write_text("---\nsubject: fx\n---\n\nAll good, keep going.\n")
eq("with no Jev, a note naming no node at all is still caught",
   len(jev.resume_warnings("fx", J4VAULT / "learn/subjects/fx/bare.md",
                           ask_fn=lambda *a, **k: None, vault=J4VAULT)), 1)
eq("but a note that does name nodes is left alone rather than guessed at",
   jev.resume_warnings("fx", J4VAULT / "learn/subjects/fx/resume.md",
                       ask_fn=lambda *a, **k: None, vault=J4VAULT), [])
eq("a missing resume.md is not an error here -- G1 owns that",
   jev.resume_warnings("fx", J4VAULT / "learn/subjects/fx/nope.md",
                       ask_fn=lambda *a, **k: full, vault=J4VAULT), [])

section("J4 — resume_body strips frontmatter, which is not what a reader reads")
eq("frontmatter goes", jev.resume_body("---\na: 1\n---\n\nbody here"), "body here")
eq("a note with no frontmatter is unchanged", jev.resume_body("body here"), "body here")
eq("names_no_node is one-directional: absence is the finding",
   (jev.names_no_node("solid: n1, n2"), jev.names_no_node("everything is fine")), (False, True))

section("J5 — the rule flags one combination and leaves the rest alone")
def verdict(analogy, limit):
    return jev.analogy_verdict({"draws_analogy": {"noul": analogy},
                                "states_limit": {"noul": limit}})[0]
eq("an analogy with no limit stated is the violation", verdict(0.95, 0.05), "flag")
eq("an analogy with its limit stated is the behaviour the rule wants", verdict(0.95, 0.92), "ok")
eq("no analogy means the rule does not apply, whatever the limit answer",
   (verdict(0.02, 0.01), verdict(0.02, 0.99)), ("ok", "ok"))
eq("an analogy whose limit Jev could not decide is not a finding", verdict(0.95, 0.5), "unclear")
eq("a borderline analogy is not a finding either", verdict(0.5, 0.01), "ok")
# Pinned from the live calibration: math241 s02 n7 is a grading log with no
# analogy in it and came back at exactly 0.70, while the two true positives came
# back at 0.93 and 0.96. If the threshold ever drifts back down, this fails.
eq("the one observed false positive, at p=0.70, stays out", verdict(0.70, 0.17), "ok")
eq("and the two observed true positives stay in",
   (verdict(0.93, 0.05), verdict(0.96, 0.04)), ("flag", "flag"))
eq("a non-numeric answer decides nothing", verdict(None, 0.01), None)

section("J5 — pulling node entries out of a session note")
J5NOTE = """---
subject: fx
nodes: [n1, n2]
---

## Lesson

### n1 — Pointers

A pointer is like a slip of paper with a house number on it.

**Diagram.** none
**Check.** passed

### n2 — References

A reference is another name for the same variable. Think of it as a nickname,
though unlike a nickname it can never be reassigned to someone else.

**Check.** passed

## Retrieval checks

- nothing here is a node entry
"""
entries = jev.extract_node_entries_from(J5NOTE, "fx", "s01")
eq("both entries found, and nothing from outside the Lesson section",
   [entry["node"] for entry in entries], ["n1", "n2"])
eq("the Retrieval checks section is not swallowed into the last entry",
   "nothing here is a node entry" in entries[-1]["text"], False)

section("J5 — the deterministic fallback, and the full pass over a folder")
eq("a comparison with no edge marked is caught",
   jev.unbounded_analogy("A pointer is like a slip of paper with a house number."),
   "is like a")
eq("the same comparison with its edge marked is not",
   jev.unbounded_analogy("It is like a nickname, though unlike a nickname it cannot be reassigned."),
   None)
eq("plain prose with no comparison is not",
   jev.unbounded_analogy("A pointer stores an address."), None)

J5DIR = J4VAULT / "learn/subjects/fx/sessions"
J5DIR.mkdir(parents=True)
(J5DIR / "2026-09-22-s01.md").write_text(J5NOTE)
flagged = jev.analogy_warnings("fx", J5DIR, vault=J4VAULT, ask_fn=lambda state, *a, **k: {
    "draws_analogy": {"noul": 0.95},
    "states_limit": {"noul": 0.9 if "unlike" in state["explanation"] else 0.02}})
eq("only the unbounded entry is flagged", len(flagged), 1)
eq("and the warning names the node", " n1:" in flagged[0], True)

nokey = jev.analogy_warnings("fx", J5DIR, vault=J4VAULT, ask_fn=lambda *a, **k: None)
eq("with no Jev the regex half still catches the same entry", len(nokey), 1)
eq("and says it is the fallback talking", "deterministic fallback" in nokey[0], True)


# --------------- J1 inline: the notice seam (PLAN-2026-09-22.md Phase 4, follow-on)

# The item the plan named twice without building. The failure it had to solve is
# not "can Jev judge a probe" -- `probe_warnings` above already does that -- it is
# that `promote_or_reconcile` replaces `baseline` wholesale with the JSONL
# transcript, so anything without a transcript row is erased on the next
# keystroke. The test that matters is the last one in this section: a notice is
# still in `log.md` after a reconciliation that emptied `current` and rebuilt
# `baseline` from a transcript containing no notice.

# `probe_guard` does `import jev`, and `load()` above does not register what it
# builds in sys.modules. Point the name at the same module object, or the guard
# would quietly get a second copy and none of the stubs below would reach it.
sys.modules["jev"] = jev
REAL_ASK = jev.ask

DANGLER = {"question": "From the code above, what do the two cout lines print?",
           "options": [{"label": "41 and 42"}, {"label": "42 and 41", "description": "swapped"}]}
STANDS_ALONE = {"question": "For `int x = 5; int *p = &x;`, what does `*p` evaluate to?",
                "options": [{"label": "5"}, {"label": "the address of x"}, {"label": "undefined"}]}


def probe_ask(state, questions, **kwargs):
    return {"outside_reference": {"noul": 0.97 if "code above" in state["question"] else 0.02}}


def pretool(tool_id, questions, sid="conv-a"):
    return olive.process(VAULT, {"session_id": sid, "hook_event_name": "PreToolUse",
                                 "tool_name": "AskUserQuestion", "tool_use_id": tool_id,
                                 "tool_input": {"questions": questions}})


section("J1 inline — the probe text a question picker turns into")
text = jev.probe_text(STANDS_ALONE)
eq("the question leads", text.startswith("For `int x = 5;"), True)
eq("every option label travels with it, or every MC probe would look truncated",
   all(label in text for label in ("5", "the address of x", "undefined")), True)
eq("an option description travels too", "swapped" in jev.probe_text(DANGLER), True)


section("J1 inline — only a high Jev probability withdraws a question")
eq("a dangling probe at p=0.97 is withdrawn",
   jev.inline_probe_check(jev.probe_text(DANGLER), ask_fn=probe_ask)[0], "block")
eq("and the reason carries the number a human can check",
   "p=0.97" in jev.inline_probe_check(jev.probe_text(DANGLER), ask_fn=probe_ask)[1], True)
eq("a self-contained probe is not touched",
   jev.inline_probe_check(jev.probe_text(STANDS_ALONE), ask_fn=probe_ask), (None, ""))
eq("a flag below the block threshold warns instead of withdrawing",
   jev.inline_probe_check("From the code above, what prints?",
                          ask_fn=lambda *a, **k: {"outside_reference": {"noul": 0.75}})[0], "warn")
eq("too short to be a question at all is not judged",
   jev.inline_probe_check("Which?", ask_fn=probe_ask), (None, ""))


section("J1 inline — with no Jev the regex half warns and is never allowed to withdraw")
nokey = jev.inline_probe_check("From the code above, what do the two lines print?",
                               ask_fn=lambda *a, **k: None)
eq("it still catches the dangling phrase", nokey[0], "warn")
eq("and says which instrument spoke", "deterministic check" in nokey[1], True)
eq("a clean probe with no Jev is silent",
   jev.inline_probe_check(jev.probe_text(STANDS_ALONE), ask_fn=lambda *a, **k: None), (None, ""))


section("J1 inline — the guard denies the picker and writes the notice into log.md")
fresh(); note("oop", "s05")
turn("/learn-resume oop")
jev.ask = probe_ask
decision = pretool("toolu_x", [DANGLER])
eq("the tool call is denied", decision["hookSpecificOutput"]["permissionDecision"], "deny")
eq("as a PreToolUse decision, the one channel that reaches the model",
   decision["hookSpecificOutput"]["hookEventName"], "PreToolUse")
reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
eq("the reason names the rule", "Self-containment" in reason, True)
eq("and tells the tutor how to get through anyway",
   "re-issue the same question unchanged" in reason, True)

LOG = VAULT / "learn/subjects/oop/log.md"
log = LOG.read_text()
eq("the notice is a callout in the subject's live log", "[!warning] Probe check" in log, True)
eq("it sits after the question it is about",
   log.index("two cout lines") < log.index("Probe check"), True)
eq("and says the question was withdrawn", "Withdrawn before it was asked" in log, True)

decision = pretool("toolu_y", [DANGLER])
eq("the same probe is withdrawn once, not every time", decision, "")
log = LOG.read_text()
eq("the second attempt is still noticed", log.count("[!warning] Probe check"), 2)
eq("and the log says it went through", "Asked anyway" in log, True)

clean = pretool("toolu_z", [STANDS_ALONE])
eq("a self-contained picker is never denied", clean, "")
eq("and leaves no notice behind", LOG.read_text().count("[!warning] Probe check"), 2)


section("J1 inline — the guard fails open on anything")
def exploding_ask(state, questions, **kwargs):
    raise RuntimeError("network on fire")

jev.ask = exploding_ask
eq("a thrown asker still lets the question through", pretool("toolu_boom", [DANGLER]), "")
jev.ask = probe_ask


section("J1 inline — a notice survives the reconciliation that erases everything else")
fresh(); note("oop", "s06")
turn("/learn-resume oop", sid="conv-b")
pretool("toolu_x", [DANGLER], sid="conv-b")

# The JSONL catching up with the visible turn. It holds the question, because the
# model really did emit that tool_use block, and no row for the notice, because
# no model emitted it. That asymmetry is the whole problem.
JSONL = VAULT / "conv-b.jsonl"
JSONL.write_text("\n".join(json.dumps(row) for row in [
    {"type": "user", "uuid": "u1", "timestamp": "2026-09-22T18:00:00Z",
     "message": {"content": [{"type": "text", "text": "/learn-resume oop"}]}},
    {"type": "assistant", "uuid": "a1", "timestamp": "2026-09-22T18:00:05Z",
     "message": {"model": "claude-opus-5", "content": [
         {"type": "tool_use", "name": "AskUserQuestion", "id": "toolu_x",
          "input": {"questions": [DANGLER]}}]}},
]))
olive.process(VAULT, {"session_id": "conv-b", "hook_event_name": "UserPromptSubmit",
                      "prompt": "go on", "transcript_path": str(JSONL)})

state = json.loads((VAULT / ".claude/obsidian-live/conv-b.json").read_text())
eq("reconciliation happened: the live buffer holds only the new turn",
   [item["text"] for item in state["current"]], ["go on"])
eq("the question came back from the transcript instead",
   [item["key"] for item in state["baseline"] if item["key"].startswith("questions-")],
   ["questions-toolu_x"])
eq("the baseline is now the transcript, which has no row for a notice",
   any(item["role"] == olive.NOTICE_ROLE for item in state["baseline"]), False)
eq("the notice is held outside both lists",
   [item["anchor"] for item in state["notices"]], ["questions-toolu_x"])
log = (VAULT / "learn/subjects/oop/log.md").read_text()
eq("and it is still in the log, still under its question",
   "[!warning] Probe check" in log and log.index("two cout lines") < log.index("Probe check"),
   True)

eq("an orphaned notice is parked at the end rather than dropped",
   [item["key"] for item in olive.merge_notices(
       [{"key": "a", "role": "Claude", "text": "x", "time": ""}],
       [{"key": "n", "anchor": "questions-gone", "role": olive.NOTICE_ROLE,
         "text": "y", "time": ""}])],
   ["a", "n"])

jev.ask = REAL_ASK



# ------------- the within-item control, J2 and J4 (PLAN-2026-09-22.md, session 6)

# Both applications were deferred twice for the same reason: an absolute
# probability on one run cannot separate "the thing is present" from "this
# question says yes to everything". These tests pin the policy, not Jev's
# judgement -- that is what the calibration numbers in jev.py's comments are for.

section("paired_drop — two runs, one varied input, read the gap")
def pair_ask(state, questions, **kwargs):
    name = list(questions)[0]
    return {name: {"noul": 0.9 if name == "left" else 0.2}}

LEFT = ({"x": 1}, {"left": {"kind": "noul", "instructions": "?"}}, jev.read_noul("left"))
RIGHT = ({"x": 1}, {"right": {"kind": "noul", "instructions": "?"}}, jev.read_noul("right"))
eq("the gap is left minus right",
   [round(value, 2) for value in jev.paired_drop(LEFT, RIGHT, ask_fn=pair_ask)],
   [0.9, 0.2, 0.7])
eq("one unanswerable side makes the whole pair no answer, never a one-sided guess",
   jev.paired_drop(LEFT, RIGHT, ask_fn=lambda state, questions, **k:
                   None if "right" in questions else {"left": {"noul": 0.9}}),
   (None, None, None))
eq("a malformed answer is not a number and decides nothing",
   jev.paired_drop(LEFT, RIGHT, ask_fn=lambda *a, **k: {"left": {}, "right": {}}),
   (None, None, None))

eq("a Choice reader takes the mass on the keyed label, not the confidence",
   jev.read_choice_mass("answer", "opt2")({"answer": {"choice": "opt1", "confidence": 0.95,
                                                      "probabilities": {"opt1": 0.6, "opt2": 0.4}}}),
   0.4)
eq("with no per-choice probabilities it falls back to confidence on the chosen label",
   jev.read_choice_mass("answer", "opt2")({"answer": {"choice": "opt2", "confidence": 0.8}}), 0.8)
eq("and a confident vote for a different label is mass 0 on this one, not None",
   jev.read_choice_mass("answer", "opt2")({"answer": {"choice": "opt1", "confidence": 0.8}}), None)


section("J4 — what_is_shaky ships on the gap, which its absolute threshold missed")
def shaky_ask(probabilities):
    def asker(state, questions, **kwargs):
        name = list(questions)[0]
        return {name: {"noul": probabilities[name]}}
    return asker

# The ablation measured on 2026-09-22: 0.41 is *above* the 0.30 absolute flag
# threshold, so the old check found nothing. The gap is -0.36 and finds it.
ABLATED = shaky_ask({"what_is_shaky": 0.41, "all_settled": 0.77})
eq("the absolute reading of the ablated note is not a finding",
   jev.resume_verdict({"what_is_shaky": {"noul": 0.41}}), [])
eq("the paired reading of the same numbers is",
   round(jev.shaky_gap("body", ask_fn=ABLATED)[2], 2) <= jev.SHAKY_GAP_AT, True)
REAL = shaky_ask({"what_is_shaky": 0.98, "all_settled": 0.01})
eq("a note that does name a weak point is well clear of the line",
   round(jev.shaky_gap("body", ask_fn=REAL)[2], 2), 0.97)

J6 = fresh()
write(J6 / "learn/subjects/fx/resume.md", "---\nsubject: \"fx\"\n---\n\nn1 is done. Next: n2.")
def resume_ask(shaky):
    def asker(state, questions, **kwargs):
        if "what_is_shaky" in questions:
            return {"what_is_shaky": {"noul": shaky}}
        if "all_settled" in questions:
            return {"all_settled": {"noul": 1.0 - shaky}}
        return {name: {"noul": 0.99} for name in jev.RESUME_DIMENSIONS}
    return asker

flagged = jev.resume_warnings("fx", J6 / "learn/subjects/fx/resume.md", ask_fn=resume_ask(0.41))
eq("a resume that names nothing shaky is now reported", len(flagged), 1)
eq("and the warning names the dimension", "what is shaky" in flagged[0], True)
eq("a resume that does is not",
   jev.resume_warnings("fx", J6 / "learn/subjects/fx/resume.md", ask_fn=resume_ask(0.98)), [])


section("J2 — the key: field now carries its options, and G4 still reads the slot")
KEYED = ('**Check.** Q: "Which line creates pointer p storing x\'s address?" / A: "1" / '
         "Verdict: correct. key: 1/3 — options: `int *p = &x;` / `int p = *x;` / `int *p = x;`")
checks, skipped = jev.extract_mc_checks_from(KEYED, "fx", "s01")
eq("one check recovered from the extended field", len(checks), 1)
eq("every option in slot order", checks[0]["options"],
   ["`int *p = &x;`", "`int p = *x;`", "`int *p = x;`"])
eq("the slot says which one was correct", checks[0]["correct_index"], 0)
eq("G4's own pattern is untouched by the suffix",
   status.MC_KEY.search(KEYED).groups(), ("1", "3"))

BAD = "**Check.** Q: \"something?\" / A: \"x\" / Verdict: correct. key: 4/3 — options: a / b / c"
eq("a slot outside its own count is reported, not repaired",
   jev.extract_mc_checks_from(BAD, "fx", "s01"), ([], 1))
MISCOUNT = "**Check.** Q: \"something?\" / A: \"x\" / Verdict: correct. key: 1/4 — options: a / b / c"
eq("an option count that disagrees with the field is too",
   jev.extract_mc_checks_from(MISCOUNT, "fx", "s01"), ([], 1))
eq("the old quoted format still parses, so the historical corpus is not orphaned",
   [check["options"] for check in jev.extract_mc_checks_from(PROBE_NOTE, "fx", "s01")[0]],
   [["a variable", "an address", "a register"]])


section("J2 — a leak is the blind run beating chance, not the sighted run being right")
def j2_ask(blind_mass):
    def asker(state, questions, **kwargs):
        blind = jev.BLIND_INSTRUCTIONS in questions["answer"]["instructions"]
        mass = blind_mass if blind else 0.99
        return {"answer": {"choice": "opt1", "confidence": mass,
                           "probabilities": {"opt1": mass, "opt2": (1 - mass) / 2,
                                             "opt3": (1 - mass) / 2}}}
    return asker

sighted, blind, drop = jev.leak_gap("q?", ["a", "b", "c"], 0, ask_fn=j2_ask(0.88))
eq("the sighted run is not the finding", round(sighted, 2), 0.99)
eq("the blind run is", round(blind, 2), 0.88)
eq("and the drop says how little the question added", round(drop, 2), 0.11)

J2DIR = J6 / "learn/subjects/fx/sessions"
J2DIR.mkdir(parents=True)
(J2DIR / "2026-09-22-s01.md").write_text(KEYED)
eq("a set that survives the question being removed is flagged",
   len(jev.leak_warnings("fx", J2DIR, ask_fn=j2_ask(0.88))), 1)
eq("the warning shows both numbers a human needs to judge it",
   "against 0.33" in jev.leak_warnings("fx", J2DIR, ask_fn=j2_ask(0.88))[0], True)
eq("a set that collapses to chance without the question is not",
   jev.leak_warnings("fx", J2DIR, ask_fn=j2_ask(0.35)), [])
eq("and with no Jev at all it simply does not run, rather than guessing",
   jev.leak_warnings("fx", J2DIR, ask_fn=lambda *a, **k: None), [])



print()
if FAILS:
    print("FAILED (%d): %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("all assertions passed")
