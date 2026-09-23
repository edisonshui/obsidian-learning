#!/usr/bin/env python3
"""Jev: TypeSafe System One calls for the semantic checks `learn-status.py`'s
deterministic gates cannot make (PLAN-2026-09-22.md, "Where Jev fits").

Every rule that is a count, a presence test, or a date comparison stays in
`learn-status.py` as plain Python -- Jev buys nothing there and would make it
slower, non-deterministic, and network-dependent. What lives here is the
question-answering half: is a probe self-contained, does an option set leak
its answer through shape, is a candidate the same claim as an existing one,
does a resume actually let a cold session continue. None of that is a count.

Contract this module holds to, because both hosts' hooks set a 5-second
timeout and a blocked session is worse than a missing warning:

  * `available()` is instant and offline -- it never imports the network stack
    just to check whether it could.
  * Every call that can reach the network is wrapped so that any failure
    (no key, package missing, no network, a bad response, a timeout) returns
    `None` rather than raising. Nothing here ever blocks a session or a lesson.
  * A cache keyed by the content hash of (state, questions) means an unchanged
    note is judged once, not on every run.
  * This module makes no gate decisions and repairs nothing. Whoever calls it
    (a `--semantic` pass in `learn-status.py`, or a one-off diagnostic like
    `calibrate-j2` below) applies the policy; this module only asks Jev and
    hands back what it said.

Run standalone: python3 .claude/hooks/jev.py status
                 python3 .claude/hooks/jev.py match-candidate --kind preference --new "..."
                 python3 .claude/hooks/jev.py calibrate-j2

J1 (probe self-containment) is not a subcommand here: it runs over every logged
check in the records, so it belongs to the generator that already reads them --
`python3 .claude/hooks/learn-status.py --semantic`.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import session_note  # noqa: E402 -- sibling modules, same directory as this file
import vaultlib  # noqa: E402

VAULT = Path(__file__).resolve().parents[2]
CACHE_DIR = VAULT / ".claude" / "jev"
CACHE_FILE = CACHE_DIR / "cache.json"
CACHE_KEEP = 2000  # generous; each entry is a few hundred bytes of JSON


# --------------------------------------------------------------------- setup

def _load_dotenv(vault=VAULT):
    """Load TYPESAFE_API_KEY from `.env` into the environment if not already set.

    `.env` is gitignored (checked at the top of PLAN-2026-09-22.md Phase 3), so
    reading it here is not reading the key from a tracked file -- the rule that
    forbids that is about the key never landing in git, not about this module
    being unable to find it. Silent on any problem: a malformed or missing
    `.env` is exactly the "no key" case `available()` already handles.
    """
    import os
    if os.environ.get("TYPESAFE_API_KEY"):
        return
    path = Path(vault) / ".env"
    try:
        text = path.read_text()
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def available(vault=VAULT):
    """True if a semantic call could be attempted. Instant, offline, no import
    of the SDK's network stack -- only its top-level package presence."""
    import importlib.util
    import os
    if importlib.util.find_spec("typesafe_sdk") is None:
        return False
    _load_dotenv(vault)
    return bool(os.environ.get("TYPESAFE_API_KEY"))


_WARNED = False


def _warn_once(message):
    global _WARNED
    if not _WARNED:
        print("jev: " + message, file=sys.stderr)
        _WARNED = True


# --------------------------------------------------------------------- cache

def _cache_load():
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _cache_save(store):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if len(store) > CACHE_KEEP:
            # Drop oldest by insertion order (dicts preserve it); simplest bound
            # that keeps the file from growing without limit.
            for key in list(store)[: len(store) - CACHE_KEEP]:
                del store[key]
        CACHE_FILE.write_text(json.dumps(store))
    except OSError:
        pass  # a cache write failing is never fatal; the next call just re-asks


def _hash(state, questions_spec):
    canonical = json.dumps({"state": state, "questions": questions_spec}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------- calls

def _build_question(spec):
    import typesafe_sdk as ts
    kind = spec["kind"]
    if kind == "noul":
        return ts.Noul(instructions=spec["instructions"])
    if kind == "choice":
        return ts.Choice(instructions=spec["instructions"], criteria=spec["criteria"])
    if kind == "score":
        return ts.Score(instructions=spec["instructions"], criteria=spec["criteria"])
    raise ValueError("unknown question kind: %r" % kind)


def ask(state, questions_spec, *, vault=VAULT, use_cache=True):
    """Ask a batch of questions against one piece of state.

    `questions_spec` maps a name to a plain JSON-safe dict: {"kind": "noul",
    "instructions": "..."} / {"kind": "choice", "instructions": "...",
    "criteria": {...}} / {"kind": "score", "instructions": "...", "criteria": [...]}.

    Returns a dict of name -> plain-dict answer, or None if the call could not
    be made or failed for any reason. Never raises.
    """
    cache_key = _hash(state, questions_spec)
    store = _cache_load() if use_cache else {}
    if use_cache and cache_key in store:
        return store[cache_key]["answers"]

    if not available(vault):
        return None

    try:
        import typesafe_sdk as ts
        client = ts.TypeSafeClient()
        questions = {name: _build_question(spec) for name, spec in questions_spec.items()}
        response = client.system_one(state=state, questions=questions)
        answers = {name: answer.model_dump() for name, answer in response.answers.items()}
    except Exception as error:  # noqa: BLE001 -- fail open on literally anything
        _warn_once("call failed, treating as no answer (%s: %s)" % (type(error).__name__, error))
        return None

    if use_cache:
        store[cache_key] = {"answers": answers}
        _cache_save(store)
    return answers


# ------------------------------------------------- the within-item control

# Two checks in this file were written, calibrated, and then not shipped for the
# same reason, recorded twice in PLAN-2026-09-22.md: an absolute probability on a
# single run cannot separate "the thing I am looking for is present" from "this
# question runs high on anything I hand it".
#
#   * J2 flagged 7 of 7 logged checks at confidence >= 0.7. "Every option set
#     leaks" and "Jev knows C++" predict that equally well.
#   * J4's `what_is_shaky` never fell below 0.98 across all 8 `resume.md` files
#     in git, and bottomed out at 0.70 on a note with every weak point stripped
#     out -- still far above its 0.30 flag threshold.
#
# The remedy both wanted is the same: ask twice about one item, varying exactly
# one thing, and read the *gap*. Whatever inflates a lone run -- Jev's own
# subject knowledge, a Noul's bias toward yes on any prose, the length or
# polish of a particular note -- is present in both runs and subtracts out.
#
# What kept this unbuilt was the word "rewrite". Both plan entries describe the
# control as a rewritten version of the item, and nothing here can rewrite text:
# Jev returns typed judgements, not prose, and asking the tutor to write the
# control for its own question is asking the thing under test to grade itself.
# Both controls below are therefore *subtractive and mechanical* -- they delete
# one input, they never author a replacement:
#
#   * J2 removes the question and keeps the options (`blind_choice_spec`).
#   * J4 keeps the note and flips the question's polarity (`RESUME_POLARITY`).
#
# Neither needs a writer, so neither needs a judgement call to produce.


def read_noul(name):
    """A reader for `paired_drop`: the probability a named Noul came back with."""
    def reader(answers):
        value = (answers or {}).get(name, {}).get("noul")
        return value if isinstance(value, (int, float)) else None
    return reader


def read_choice_mass(name, label):
    """A reader for `paired_drop`: the probability mass on one Choice label.

    Mass, not confidence, and for the same reason `candidate_route` gives: a
    confident "some other option" and an unsure "this option" are different
    findings and must not collapse into one number. Falls back to the reported
    confidence only when no per-choice probabilities came back at all.
    """
    def reader(answers):
        answer = (answers or {}).get(name) or {}
        probabilities = answer.get("probabilities") or {}
        if label in probabilities:
            return probabilities[label]
        if probabilities:
            return 0.0
        confidence = answer.get("confidence")
        if answer.get("choice") == label and isinstance(confidence, (int, float)):
            return confidence
        return None
    return reader


def paired_drop(left, right, *, ask_fn=None, vault=VAULT):
    """Score one item twice under a within-item control and return the gap.

    `left` and `right` are each `(state, questions_spec, reader)`. Everything
    about the item that is not the single varied input is identical across the
    two, which is the whole point: the confound cancels in the difference.

    Returns `(left_p, right_p, drop)` with `drop = left_p - right_p`, or
    `(None, None, None)` if either call could not be made. Never raises. Two
    calls rather than one batched request on purpose -- jaggedness #8 says
    unrelated context lowers accuracy, and batching would put the control's
    state into the item's own judgement and destroy the thing being measured.
    """
    asker = ask_fn or ask
    scores = []
    for state, spec, reader in (left, right):
        try:
            value = reader(asker(state, spec, vault=vault))
        except Exception:  # noqa: BLE001 -- a malformed answer is "no answer"
            value = None
        if not isinstance(value, (int, float)):
            return None, None, None
        scores.append(float(value))
    return scores[0], scores[1], scores[0] - scores[1]


# ------------------------------------------------------- J1: probe self-containment

# `tutor.md`, *Self-containment*: a probe stands alone. The learner sees the
# question text and its options and nothing else, so a question that points at
# code, a diagram, or an earlier message produces "a wrong answer that is
# evidence about the interface, not about the learner" -- and it gets logged in
# `record.md` as evidence about the learner anyway. That is why this is the
# highest-stakes check in the vault and why the audit's regex was the wrong
# instrument: "which of the following" points at the options, which the learner
# can see, while "the code above" points at something they cannot.

# What counts as a logged check, and what text it showed the learner, is
# `session_note`'s to say (its `CHECK_Q`): the whole `Q:` up to the answer or
# verdict marker, options included when they were logged inline.

# Below this a "probe" is a logging fragment, not a question -- asking Jev
# whether a six-character string stands alone is noise, not a check.
MIN_PROBE_CHARS = 12

PROBE_FLAG_AT = 0.7
PROBE_CLEAR_AT = 0.3

PROBE_INSTRUCTIONS = (
    "The state holds the complete text of one quiz question as a learner saw it, "
    "including its answer options if it had any. The learner saw nothing else: no "
    "lesson text, no earlier chat message, no code or diagram outside this text. "
    "Is this question impossible to answer because it refers to material that is "
    "not included in the state? "
    "Answer yes only when the question points at something outside itself -- code, "
    "a diagram, a passage, an earlier example, or a previous question -- that the "
    "state does not contain. "
    "The phrase 'which of the following' refers to the answer options listed in the "
    "state itself; it is not a reference to outside material, so it is not a yes. "
    "A question that is merely difficult, or that assumes subject knowledge the "
    "learner is expected to have studied, is not a reference to outside material "
    "either, so it is not a yes."
)

# The deterministic half of J1: the small set of phrases that point outside a
# question no matter what the subject is. It is strictly weaker than the Noul --
# that is the point of it being the fallback -- but it keeps the rule alive with
# no key, no network, and no SDK.
DANGLING = [
    re.compile(r"\b(?:the\s+)?(?:code|snippet|example|diagram|figure|passage|program|output|image)"
               r"\s+(?:above|below|earlier|shown|from before)\b", re.I),
    re.compile(r"\bthe\s+following\s+(?:code|snippet|example|diagram|passage|program|output)\b", re.I),
    re.compile(r"\bsee\s+above\b|\bas\s+shown\s+above\b|\bas\s+above\b", re.I),
    re.compile(r"\b(?:earlier|previous|last)\s+(?:example|scenario|question|problem|code)\b", re.I),
]
# Removed before the patterns run: it looks like a dangling reference and is not.
NOT_DANGLING = re.compile(r"which\s+of\s+the\s+following", re.I)


def extract_probes_from(text, subject="", file=""):
    """Every logged check in one session note, as the learner would have seen it."""
    return [{"subject": subject, "file": file, "line": check.line, "text": check.text}
            for check in session_note.parse(text).checks if len(check.text) >= MIN_PROBE_CHARS]


def extract_probes(vault=VAULT):
    """Every logged check across every subject's session notes."""
    probes = []
    root = Path(vault) / "learn" / "subjects"
    for folder in sorted(path for path in root.glob("*") if path.is_dir()) if root.is_dir() else []:
        sessions = folder / "sessions"
        if not sessions.is_dir():
            continue
        for path in sorted(sessions.glob("*.md")):
            probes += extract_probes_from(path.read_text(), folder.name, path.stem)
    return probes


def probe_spec():
    return {"outside_reference": {"kind": "noul", "instructions": PROBE_INSTRUCTIONS}}


def probe_verdict(answers):
    """('flag' | 'ok' | 'unclear' | None, probability).

    A Noul reports a probability and no separate confidence, so the routing is
    distance from 0.5: near 1 the question points outside itself, near 0 it does
    not, and the band in between is Jev saying it cannot tell. Only a flag is
    ever reported -- a warning list that fires on uncertainty is noise, and
    noise is how a warning list stops being read.
    """
    probability = (answers or {}).get("outside_reference", {}).get("noul")
    if not isinstance(probability, (int, float)):
        return None, None
    if probability >= PROBE_FLAG_AT:
        return "flag", probability
    if probability <= PROBE_CLEAR_AT:
        return "ok", probability
    return "unclear", probability


def dangling_reference(text):
    """The phrase that points outside this question, or None. Deterministic."""
    scrubbed = NOT_DANGLING.sub(" ", text)
    for pattern in DANGLING:
        match = pattern.search(scrubbed)
        if match:
            return match.group(0).strip()
    return None


def _quote(text, width=90):
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def probe_warnings(slug, folder, ask_fn=None, vault=VAULT):
    """J1 over one subject's session notes. Reports; never repairs anything.

    One call per probe rather than one batched call for the whole note: jaggedness
    #8 says unrelated context lowers accuracy, and a batch would put every other
    question in the note into the state of each judgement. The content-hash cache
    in `ask` is what keeps the cost of that down -- an unchanged note is judged
    once, ever.
    """
    warnings = []
    folder = Path(folder)
    if not folder.is_dir():
        return warnings
    asker = ask_fn or ask
    for path in sorted(folder.glob("*.md")):
        for probe in extract_probes_from(path.read_text(), slug, path.stem):
            answers = asker({"question": probe["text"]}, probe_spec(), vault=vault)
            if answers is None:
                phrase = dangling_reference(probe["text"])
                if phrase:
                    warnings.append(
                        "%s %s: logged check may not stand alone -- it says \"%s\" "
                        "(deterministic fallback, Jev unavailable; tutor.md, Self-containment): \"%s\""
                        % (slug, probe["file"], phrase, _quote(probe["text"])))
                continue
            verdict, probability = probe_verdict(answers)
            if verdict == "flag":
                warnings.append(
                    "%s %s: logged check may not stand alone (Jev p=%.2f; tutor.md, "
                    "Self-containment): \"%s\"" % (slug, probe["file"], probability,
                                                   _quote(probe["text"])))
    return warnings


# --------------------------------------- J1 inline: a probe, before it is asked

# `probe_warnings` above reads a check out of a session note, which is always
# *after* the learner answered it and after `record.md` recorded that answer as
# evidence about the learner. The value is in catching it one step earlier, and
# PLAN-2026-09-22.md declined to build that twice -- for a reason about the live
# log rather than about Jev. `obsidian-live.py` rewrites each `log.md` in full
# from its own state on every hook, and `promote_or_reconcile` replaces that
# state wholesale with the JSONL transcript, so there was nowhere for a second
# process to put a notice that would still be there on the next keystroke. That
# seam now exists (`obsidian-live.py`, `state["notices"]`); this is the
# judgement it carries, and it is the same Noul `probe_warnings` already uses.
#
# Parity rule 2, stated rather than papered over: Codex has no `PreToolUse`
# event and no question picker to hook, so it gets the record-layer check and
# not this one. This is never the only copy of the rule.

# Only a Jev probability at or above this withdraws a question the learner is
# waiting on. `PROBE_FLAG_AT` (0.7) still writes the notice into the log. The
# gap between the two is deliberate: the record layer only ever reports, so a
# false positive there costs a line someone reads and dismisses, while a false
# positive here costs a question. Calibration on 2026-09-22 flagged 4 of 42
# logged checks, all four true on inspection, at p between 0.96 and 0.98.
PROBE_BLOCK_AT = 0.9


def probe_text(question):
    """One question-picker entry, flattened to what the learner will actually see.

    `PROBE_INSTRUCTIONS` tells Jev the state holds a question "including its
    answer options if it had any", which is true of the `Q:` lines the record
    layer reads. Here the options are still structured, so they are flattened
    into the same shape. Dropping them would make every multiple-choice probe
    look like it pointed at options the learner could not see, and J1 would then
    flag all of them.
    """
    parts = [str(question.get("question", "")).strip()]
    for option in question.get("options") or []:
        label = str(option.get("label", "")).strip()
        description = str(option.get("description") or "").strip()
        if label or description:
            parts.append("- " + label + (" — " + description if description else ""))
    return "\n".join(part for part in parts if part).strip()


def inline_probe_check(text, ask_fn=None, vault=VAULT):
    """Judge one probe before it is asked: ("block" | "warn" | None, reason).

    Never raises. With no key, no network, or no SDK this falls straight through
    to `dangling_reference`, which is offline and instant -- the same fallback
    `probe_warnings` uses, for the same reason.

    The deterministic half can only ever "warn". It is the strictly weaker
    instrument, and withdrawing a question is the one intervention in this module
    with a cost when it is wrong, so a regex does not get to make it.
    """
    text = (text or "").strip()
    if len(text) < MIN_PROBE_CHARS:
        return None, ""
    answers = (ask_fn or ask)({"question": text}, probe_spec(), vault=vault)
    if answers is None:
        phrase = dangling_reference(text)
        if not phrase:
            return None, ""
        return "warn", ('This probe says "%s", which points at something outside the '
                        "question itself (deterministic check -- Jev was not reachable). "
                        "tutor.md, Self-containment: every probe stands alone." % phrase)
    verdict, probability = probe_verdict(answers)
    if verdict != "flag":
        return None, ""
    level = "block" if probability >= PROBE_BLOCK_AT else "warn"
    return level, ("This probe may not stand alone: it appears to point at material the "
                   "learner cannot see from the question and its options alone (Jev "
                   "p=%.2f). tutor.md, Self-containment." % probability)


# ------------------------------------------------------- J3: candidate matching

# `learn-end` step 5 asks for a semantic identity judgement once per session --
# is this new observation the same claim as one already on file -- and supplies
# its own tie-break: "if you are not sure they are the same claim, they are not."
# Every line in preferences.md's *Observed* turned on that judgement, and until
# now it happened in the tutor's head and left no trace. This does not take the
# judgement away: it asks the same question in a form that records an answer and
# a number, and hands the middle band back to Edison.

NONE_LABEL = "none_of_these"
CANDIDATE_PROMOTE_AT = 0.80
CANDIDATE_NEW_AT = 0.50

CANDIDATE_INSTRUCTIONS = (
    "The state holds one new observation about a learner, written at the end of a "
    "tutoring session. Each choice is an observation about the same learner that was "
    "recorded earlier. Choose the recorded observation that makes the same claim as "
    "the new one, even if the two are worded differently. "
    "Two observations make the same claim only when either one could stand in for the "
    "other as evidence of the same thing. The same topic, the same subject, or similar "
    "wording is not enough. "
    "Choose %s when the new observation makes a claim that none of the recorded ones "
    "make." % NONE_LABEL
)

CHECKBOX = re.compile(r"^\[[ xX]\]\s*")
STOPWORDS = {
    "a", "an", "and", "the", "to", "of", "in", "on", "for", "is", "it", "that", "this",
    "with", "as", "at", "by", "or", "was", "were", "be", "been", "than", "then", "when",
    "he", "his", "they", "them", "their", "not", "but", "one", "into", "out", "over",
}


def parse_candidates(text, heading):
    """The bullet lines of one '## heading' section, checkbox markers stripped.

    Covers both shapes the records use: preferences.md's *Candidates* tally and a
    record.md *Misconceptions* list with `- [ ]` / `- [x]` boxes. The italic
    format note each section opens with is not a bullet, so it is not a candidate.
    """
    out = []
    for line in vaultlib.section(text, heading).splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        out.append(CHECKBOX.sub("", line[2:].strip()).strip())
    return [line for line in out if line]


def _words(text):
    return {word for word in re.findall(r"[a-z']+", text.lower()) if word not in STOPWORDS}


def closest_by_overlap(text, existing):
    """(index, score) of the existing line sharing the most content words.

    The no-key fallback. Word overlap is not a semantic judgement and is not
    treated as one: `match_candidate` returns it as a pointer for the tutor to
    look at, never as a verdict.
    """
    target = _words(text)
    best_index, best_score = None, 0.0
    for index, line in enumerate(existing):
        other = _words(line)
        if not target or not other:
            continue
        score = len(target & other) / len(target | other)
        if score > best_score:
            best_index, best_score = index, score
    return best_index, best_score


def candidate_spec(new_text, existing):
    criteria = {"cand%d" % (index + 1): line for index, line in enumerate(existing)}
    criteria[NONE_LABEL] = ("None of the recorded observations makes the same claim as the "
                            "new one; it is a first sighting of something else.")
    return {"match": {"kind": "choice", "instructions": CANDIDATE_INSTRUCTIONS, "criteria": criteria}}


def candidate_route(answer):
    """('promote' | 'new' | 'ask', label, probability).

    Routes on the probability mass sitting on the best *existing* candidate, not
    on the reported confidence, so "confidently none of these" and "unsure about
    a match" cannot collapse into the same number. High promotes, low files as
    new, and the middle band goes to Edison -- which is `learn-end` step 5's own
    conservative bias ("if you are not sure they are the same claim, they are
    not") expressed as a threshold instead of a feeling.
    """
    answer = answer or {}
    probabilities = answer.get("probabilities") or {}
    best_label, best_probability = None, 0.0
    for label, probability in probabilities.items():
        if label == NONE_LABEL:
            continue
        if probability > best_probability:
            best_label, best_probability = label, probability
    if not probabilities:
        # No per-choice probabilities came back: fall back to the chosen label and
        # its confidence, which carries the same information more coarsely.
        choice, confidence = answer.get("choice"), answer.get("confidence")
        if not choice or not isinstance(confidence, (int, float)):
            return "ask", None, None
        if choice == NONE_LABEL:
            return ("new" if confidence >= CANDIDATE_PROMOTE_AT else "ask"), None, confidence
        best_label, best_probability = choice, confidence
    if best_probability >= CANDIDATE_PROMOTE_AT:
        return "promote", best_label, best_probability
    if best_probability <= CANDIDATE_NEW_AT:
        return "new", best_label, best_probability
    return "ask", best_label, best_probability


def existing_candidates(kind, vault=VAULT, subject=None, skip_note=None):
    """The lines a new candidate is compared against, per kind.

    `skip_note` drops one session note by stem. `/learn-end` writes the session
    note (step 1) before it does the candidate tally (step 5), so without this
    the new candidate would be compared against the copy of itself that was just
    written, and every first sighting would match and promote.
    """
    vault = Path(vault)
    if kind == "preference":
        path = vault / "learn" / "me" / "preferences.md"
        return parse_candidates(path.read_text(), "Candidates") if path.is_file() else []
    if kind == "misconception":
        folder = vault / "learn" / "subjects" / str(subject)
        lines = []
        record = folder / "record.md"
        if record.is_file():
            lines += parse_candidates(record.read_text(), "Misconceptions")
        sessions = folder / "sessions"
        for path in sorted(sessions.glob("*.md")) if sessions.is_dir() else []:
            if skip_note and path.stem == skip_note:
                continue
            lines += parse_candidates(path.read_text(), "Misconception candidates")
        return lines
    raise ValueError("unknown candidate kind: %r" % kind)


def match_candidate(kind, new_text, existing, ask_fn=None, vault=VAULT):
    """Is this new observation the same claim as one already on file?

    Returns {"verdict", "match", "score", "compared", "instrument"}. The verdict
    is one of promote / new / ask / judge-yourself. It writes nothing: the caller
    applies `learn-end` step 5, which is where the rule lives.
    """
    existing = list(existing or [])
    if not existing:
        return {"verdict": "new", "match": None, "score": None,
                "compared": 0, "instrument": "none needed"}
    answers = (ask_fn or ask)({"new_observation": new_text}, candidate_spec(new_text, existing),
                              vault=vault)
    if answers is None:
        index, score = closest_by_overlap(new_text, existing)
        return {"verdict": "judge-yourself",
                "match": existing[index] if index is not None else None,
                "score": score, "compared": len(existing), "instrument": "word overlap"}
    verdict, label, score = candidate_route(answers.get("match"))
    match = None
    if label and label.startswith("cand"):
        try:
            match = existing[int(label[4:]) - 1]
        except (ValueError, IndexError):
            match = None
    return {"verdict": verdict, "match": match, "score": score,
            "compared": len(existing), "instrument": "jev"}



# ------------------------------------------------------- J4: the resume acceptance test

# G1 counts words, which is the easy half. `records.md` states the test that
# actually matters and that nothing checked: "could a fresh session with no
# transcript continue the lesson from these files alone?" `resume.md` is the
# first thing the next session reads, so when it fails that test the failure is
# silent -- the next session simply asks the learner what happened, and nobody
# ever learns the file was the reason.
#
# Asking "could a fresh session continue" as one Noul is the wrong shape:
# jaggedness #1 says the model reads literally, and that question is a judgement
# about a hypothetical reader rather than about the text in front of it. So it is
# three concrete presence questions, batched into one request, with code owning
# the policy over the three answers -- the `composite-scoring` pattern.

RESUME_PRESENT_AT = 0.7
RESUME_MISSING_AT = 0.3

RESUME_DIMENSIONS = {
    "next_action": (
        "the next concrete action",
        "The state holds the full text of a hand-off note, written at the end of one "
        "tutoring session to be read at the start of the next one. Does it state a "
        "specific next action -- a named topic, node, or task to do first -- rather "
        "than only describing what has already happened? Answer yes only if a reader "
        "who knew nothing else could tell from this text what to do first."),
    "node_standing": (
        "where each node stands",
        "The state holds the full text of a hand-off note, written at the end of one "
        "tutoring session to be read at the start of the next one. Teaching is broken "
        "into numbered concept nodes (n1, n2, and so on). Does this text say which "
        "specific nodes are in which state -- done, checked, solid, shaky, or not yet "
        "started? Answer yes only if individual nodes or named concepts are placed in "
        "a state, not merely counted or summarised in aggregate."),
}

# The plan's third dimension. Written and calibrated in session 5, deferred
# there because on an absolute threshold it could not produce a finding, and
# asked from session 6 onward under the control below.
#
# Session 5, absolute: measured against all 8 resume.md files in git it never
# dropped below 0.98, and on a note with every trace of a weak point removed it
# still read 0.70 -- against a 0.30 flag threshold. A question whose answer is
# always "yes" is not a check.
#
# Session 6, paired against `RESUME_POLARITY` on a minimal ablation of
# `pointers-and-references/resume.md` -- only the clauses naming a weak point
# altered, node standings, next action, voice and length held fixed:
#
#             what_is_shaky   all_settled     gap    absolute verdict
#   real           0.98          0.01        +0.97   no finding
#   ablated        0.41          0.77        -0.36   no finding  <- the miss
#
# The five live resume.md files all sit at +0.92 to +0.98. So the gap separates
# what the level could not: 1.33 points between the real note and its own
# ablation, where the absolute reading put both on the same side of its line.
# `SHAKY_GAP_AT` is 0.5 -- 0.42 clear of the nearest true pass and 0.86 clear of
# the nearest true flag.
RESUME_DEFERRED = {
    "what_is_shaky": (
        "what is shaky or unproven",
        "The state holds the full text of a hand-off note, written at the end of one "
        "tutoring session to be read at the start of the next one. Does it identify "
        "something the learner is uncertain about, got wrong, has not been tested on, "
        "or has not yet proven -- as distinct from listing what they have mastered? "
        "Answer yes only if some specific weak point, gap, or open question is named. "
        "A note that says everything is solid, with no weak point named, is a yes only "
        "if it says so explicitly."),
}

# The control for the dimension above: the same note, the same reading, the
# question turned around. A judgement that has actually read the note answers
# these two nearly opposite ways, so `p(names) - p(settled)` lands near +1 or
# near -1. A Noul that is simply agreeing with whatever it is handed answers yes
# to both and the gap collapses toward 0 -- which is the exact failure mode
# 0.98-on-everything was a symptom of. Nothing is rewritten and nothing is
# authored: the state is byte-identical between the two runs.
RESUME_POLARITY = {
    "all_settled": (
        "everything settled",
        "The state holds the full text of a hand-off note, written at the end of one "
        "tutoring session to be read at the start of the next one. Does this note "
        "present the learner's progress as entirely settled -- everything it covers "
        "described as understood, confirmed, correct, or finished, with nothing named "
        "as uncertain, wrong, shaky, untested, or still unproven? Answer yes only if "
        "no weak point, gap, or open question is named anywhere in the text."),
}

# Flag when the gap between the two polarities is no wider than this. A note that
# genuinely names a weak point should be far above it in both directions at once.
SHAKY_GAP_AT = 0.5


def shaky_spec(name=None):
    """The `what_is_shaky` Noul, or its opposite. One instruction each way."""
    source = RESUME_DEFERRED if name in (None, "what_is_shaky") else RESUME_POLARITY
    key = name or "what_is_shaky"
    return {key: {"kind": "noul", "instructions": source[key][1]}}


def shaky_gap(body, ask_fn=None, vault=VAULT):
    """J4's deferred dimension, under the within-item control.

    Returns `(p_names_a_weak_point, p_all_settled, gap)`, or three Nones. The
    finding is a *narrow* gap: the note does not name anything shaky, or the
    question could not tell. It is the sign and size of the difference that
    carries the information, never either level on its own.
    """
    return paired_drop(
        ({"handoff_note": body}, shaky_spec("what_is_shaky"), read_noul("what_is_shaky")),
        ({"handoff_note": body}, shaky_spec("all_settled"), read_noul("all_settled")),
        ask_fn=ask_fn, vault=vault)


# The deterministic half of J4. Deliberately one-directional and nothing more: a
# note that never mentions a node cannot be saying where each node stands, so its
# absence is a real finding, while its presence proves nothing. G1 already owns
# the word count and the frontmatter, so this does not repeat them.
NODE_MENTION = re.compile(r"\bn\d+\b")


def resume_spec():
    return {name: {"kind": "noul", "instructions": instructions}
            for name, (_, instructions) in RESUME_DIMENSIONS.items()}


def resume_verdict(answers):
    """The dimensions the note is missing, as (name, label) pairs.

    Only a confident *absence* is reported. A dimension Jev puts in the middle
    band is one it could not decide, and a warning list that fires on uncertainty
    stops being read -- the same routing rule J1 uses, pointed the other way,
    because here a low probability is the finding.
    """
    missing = []
    for name, (label, _) in RESUME_DIMENSIONS.items():
        probability = (answers or {}).get(name, {}).get("noul")
        if isinstance(probability, (int, float)) and probability <= RESUME_MISSING_AT:
            missing.append((name, label))
    return missing


def resume_body(text):
    """The note without its frontmatter -- the part a reader actually reads."""
    return vaultlib.strip_frontmatter(text).strip()


def names_no_node(text):
    """True when the body never mentions a node id. Deterministic."""
    return not NODE_MENTION.search(text or "")


def resume_warnings(slug, resume_path, ask_fn=None, vault=VAULT):
    """J4 over one subject's resume.md. Reports; never rewrites the note."""
    resume_path = Path(resume_path)
    if not resume_path.is_file():
        return []
    body = resume_body(resume_path.read_text())
    if not body:
        return ["%s resume.md: empty below the frontmatter" % slug]
    answers = (ask_fn or ask)({"handoff_note": body}, resume_spec(), vault=vault)
    if answers is None:
        if names_no_node(body):
            return ["%s resume.md: names no node, so it cannot say where each node stands "
                    "(deterministic fallback, Jev unavailable; records.md, the fresh-session test)"
                    % slug]
        return []
    missing = resume_verdict(answers)
    # The third dimension, asked separately because it needs its own control.
    # Two extra calls per resume rather than one more slot in the batch above:
    # the control has to see the same state with nothing else in it, and a
    # batched question would carry the other two dimensions into the judgement.
    _, _, gap = shaky_gap(body, ask_fn=ask_fn, vault=vault)
    if gap is not None and gap <= SHAKY_GAP_AT:
        missing = missing + [("what_is_shaky", RESUME_DEFERRED["what_is_shaky"][0])]
    if not missing:
        return []
    return ["%s resume.md: does not state %s -- a cold session could not continue from it "
            "(records.md, the fresh-session test)" % (slug, ", ".join(label for _, label in missing))]


# ------------------------------------------------------- J5: analogy boundary

# `tutor.md`: "Always say where the analogy breaks; an analogy without its
# boundary teaches a misconception." Audit X7 rejected gating this because it
# "requires deciding what counts as an analogy; cost exceeds the violation."
# Deciding what counts as an analogy is a semantic judgement, which is the thing
# that just got cheap -- so this is the clearest case of Jev changing which rules
# are gateable at all, rather than making an existing gate fancier.
#
# Two Nouls, batched, because they are independently useful dimensions: is there
# an analogy, and is its limit stated. Code applies the rule, and the rule flags
# exactly one combination -- yes then no. An explanation with no analogy is fine.
# An analogy with its boundary drawn is the behaviour the rule wants.

# Calibrated against the live records on 2026-09-22, not guessed. Over 35 node
# entries, 0.70 flagged three: pointers s01 n1 ("like a house number on one very
# long street", p=0.96) and math241 s01 n2 ("the flashlight-shadow picture",
# p=0.93) are both true -- and the shadow one matters, because the analogy breaks
# on exactly the sign question that entry goes on to ask. The third,
# math241 s02 n7 at p=0.70, is a grading log with no analogy in it at all.
#
# So the threshold is 0.80: it drops the one false positive and keeps both true
# ones, with the nearest true positive 13 points clear of it. Three flags is a
# thin basis for a cutoff and this comment is the honest record of that. What
# makes it different from J2's null result is the contrast: 32 of 35 entries were
# not flagged, so the check can be shown to discriminate rather than to fire on
# everything.
ANALOGY_AT = 0.8
BOUNDARY_MISSING_AT = 0.3

ANALOGY_INSTRUCTIONS = (
    "The state holds one entry from a tutoring notebook: how a single concept was "
    "explained to a learner. Does this explanation compare the concept to something "
    "from outside its own subject -- an everyday object, a sport, a game, a physical "
    "situation, a story -- in order to make it easier to understand? "
    "An example drawn from the subject itself, such as a code snippet for a "
    "programming concept or a worked problem for a mathematics one, is not an "
    "analogy to something outside the subject, so it is not a yes."
)

BOUNDARY_INSTRUCTIONS = (
    "The state holds one entry from a tutoring notebook: how a single concept was "
    "explained to a learner, possibly using a comparison to something outside the "
    "subject. Does the text say where that comparison stops holding -- naming a way "
    "the two things differ, a limit of the comparison, or something it would mislead "
    "the learner about? "
    "Answer yes only if a limit is actually stated. Merely using the comparison "
    "carefully, or hedging with a word like 'roughly', is not stating a limit."
)

# The deterministic half of J5: the ordinary English that introduces a comparison,
# against the ordinary English that marks its edge. Much blunter than the pair of
# Nouls, which is why it is the fallback and not the check.
ANALOGY_MARKS = re.compile(
    r"\b(?:think\s+of\s+it\s+(?:as|like)|it'?s\s+like|is\s+like\s+a|are\s+like\s+a"
    r"|imagine\s+a|picture\s+a|same\s+way\s+(?:that\s+)?a|analogy|metaphor)\b", re.I)
BOUNDARY_MARKS = re.compile(
    r"\b(?:breaks?\s+down|stops?\s+(?:holding|working)|falls?\s+apart|unlike"
    r"|where\s+(?:this|the)\s+analogy|the\s+analogy\s+(?:ends|breaks|stops)"
    r"|only\s+goes\s+so\s+far|does\s+not\s+carry|doesn'?t\s+carry)\b", re.I)


def extract_node_entries_from(text, subject="", file=""):
    """Every node entry in one session note, with its body.

    Node entries are the `### nN` blocks filed under *Lesson* and, for a gate
    node, under *Retrieval checks* (records.md:97), in note order. One filed
    anywhere else is misplaced: G2 reports it, and it is not judged here as if
    it were the teaching of that node.
    """
    note = session_note.parse(text)
    entries = sorted(note.entries + note.gate_entries, key=lambda entry: entry.line)
    found = []
    for entry in entries:
        body = (entry.title + "\n" + entry.body).strip()
        if body:
            found.append({"subject": subject, "file": file, "node": entry.node, "text": body})
    return found


def analogy_spec():
    return {"draws_analogy": {"kind": "noul", "instructions": ANALOGY_INSTRUCTIONS},
            "states_limit": {"kind": "noul", "instructions": BOUNDARY_INSTRUCTIONS}}


def analogy_verdict(answers):
    """('flag' | 'ok' | 'unclear' | None, analogy_p, limit_p).

    Flags one combination only: an analogy Jev is confident is there, whose limit
    Jev is confident is absent. Anything less certain on either half is 'unclear'
    and stays out of the warning list.
    """
    answers = answers or {}
    analogy = answers.get("draws_analogy", {}).get("noul")
    limit = answers.get("states_limit", {}).get("noul")
    if not isinstance(analogy, (int, float)) or not isinstance(limit, (int, float)):
        return None, None, None
    if analogy < ANALOGY_AT:
        return "ok", analogy, limit  # no analogy, so the rule does not apply
    if limit <= BOUNDARY_MISSING_AT:
        return "flag", analogy, limit
    if limit >= ANALOGY_AT:
        return "ok", analogy, limit
    return "unclear", analogy, limit


def unbounded_analogy(text):
    """The comparison marker with no boundary marker anywhere near it, or None."""
    match = ANALOGY_MARKS.search(text or "")
    if not match or BOUNDARY_MARKS.search(text or ""):
        return None
    return match.group(0).strip()


def analogy_warnings(slug, folder, ask_fn=None, vault=VAULT):
    """J5 over one subject's session notes. Reports; never edits a note."""
    warnings = []
    folder = Path(folder)
    if not folder.is_dir():
        return warnings
    asker = ask_fn or ask
    for path in sorted(folder.glob("*.md")):
        for entry in extract_node_entries_from(path.read_text(), slug, path.stem):
            answers = asker({"explanation": entry["text"]}, analogy_spec(), vault=vault)
            if answers is None:
                marker = unbounded_analogy(entry["text"])
                if marker:
                    warnings.append(
                        "%s %s %s: draws an analogy (\"%s\") without saying where it breaks "
                        "(deterministic fallback, Jev unavailable; tutor.md, Explaining)"
                        % (slug, entry["file"], entry["node"], marker))
                continue
            verdict, analogy, limit = analogy_verdict(answers)
            if verdict == "flag":
                warnings.append(
                    "%s %s %s: draws an analogy (p=%.2f) without saying where it breaks "
                    "(p=%.2f); tutor.md: an analogy without its boundary teaches a "
                    "misconception" % (slug, entry["file"], entry["node"], analogy, limit))
    return warnings


# --------------------------------------------------------------------- J2 calibration

# A check's option text survives in three formats -- legacy A and B, and the
# `key:` field written going forward -- and `session_note` normalises all three
# into one shape (question, options, correct index). Most older checks log only
# a slot or a prose summary, which carries too little to ask Jev the question.


def extract_mc_checks_from(text, subject="", file=""):
    """Every logged MC check in one note whose option text survives, any format.

    Returns `(checks, skipped)`, where `skipped` counts the lines the parser
    recognised as a check or key field and could not read. A malformed field is
    reported, never repaired and never guessed at: G2 and G4 own "is the field
    well-formed", not this.
    """
    note = session_note.parse(text)
    found = [{"subject": subject, "file": file, "question": check.question,
              "options": list(check.options), "correct_index": check.correct}
             for check in note.checks if check.options]
    return found, len(note.malformed)


def find_mc_checks_with_options(vault=VAULT):
    """Every logged check across all session notes with recoverable option text.

    Reports, rather than assumes, how much of the record this covers. Everything
    that logs only a slot number or a prose summary is skipped, not guessed at.
    """
    found, skipped_no_match = [], 0
    root = Path(vault) / "learn" / "subjects"
    for folder in sorted(p for p in root.glob("*") if p.is_dir()):
        sessions = folder / "sessions"
        if not sessions.is_dir():
            continue
        for path in sorted(sessions.glob("*.md")):
            checks, skipped = extract_mc_checks_from(path.read_text(), folder.name, path.stem)
            found += checks
            skipped_no_match += skipped
    return found, skipped_no_match


def leak_warnings(slug, folder, ask_fn=None, vault=VAULT):
    """J2 over one subject's session notes, under the blind control.

    Reports; repairs nothing and re-grades nothing. A flag says the option set
    could be solved without the question, which `tutor.md` calls "a record of
    nothing" -- but the check has already been logged as evidence by the time
    this runs, so the only honest output is a line for a human to read.

    There is no deterministic fallback here, and that is a real gap rather than
    an oversight: "could these options be picked without reading the question"
    has no offline form. With no key this check simply does not run, which is
    why it is a `--semantic` extra and never the only thing standing between a
    leaky option set and `record.md`.
    """
    warnings = []
    folder = Path(folder)
    if not folder.is_dir():
        return warnings
    for path in sorted(folder.glob("*.md")):
        checks, _ = extract_mc_checks_from(path.read_text(), slug, path.stem)
        for check in checks:
            chance = 1.0 / max(len(check["options"]), 1)
            _, blind, drop = leak_gap(check["question"], check["options"],
                                      check["correct_index"], ask_fn=ask_fn, vault=vault)
            if blind is None or blind - chance < LEAK_MARGIN:
                continue
            warnings.append(
                "%s %s: this option set may give the answer away -- with the question "
                "removed, Jev still put %.2f on the logged-correct option against %.2f "
                "by chance (question adds only %+.2f; tutor.md, MC construction): \"%s\""
                % (slug, check["file"], blind, chance, drop, _quote(check["question"], 70)))
    return warnings


BLIND_INSTRUCTIONS = (
    "Below is the list of answer options from a multiple-choice question. The "
    "question itself has been withheld and you will not be shown it. Exactly one "
    "of these options is the correct answer to it. Judging only from the options "
    "themselves -- their wording, their length, how they relate to one another -- "
    "which one is the correct answer?"
)


def sighted_spec(question, options):
    """J2's item run: the learner's own question, with no lesson material."""
    labels = ["opt%d" % (index + 1) for index in range(len(options))]
    return labels, {"answer": {
        "kind": "choice", "criteria": dict(zip(labels, options)),
        "instructions": "Answer the multiple-choice question below using only the "
                        "information given here. Question: %s" % question}}


def blind_spec(options):
    """J2's control run: the same options with the question deleted.

    This is the within-item control PLAN-2026-09-22.md asked for, in the one form
    that needs no writer. The two causes a lone confidence score cannot separate
    come apart here cleanly. Jev knowing the subject requires the question, so
    removing it drops that run to chance. Options that leak the answer through
    shape -- the longest one, the odd one out, the only grammatical one -- leak it
    just as well with the question gone, because none of that was ever about the
    question. Whatever Jev happens to know about C++ is present in both runs and
    subtracts out.
    """
    labels = ["opt%d" % (index + 1) for index in range(len(options))]
    return labels, {"answer": {"kind": "choice", "criteria": dict(zip(labels, options)),
                               "instructions": BLIND_INSTRUCTIONS}}


# A blind run must beat chance by this much before the option set is called a
# leak. Chance is 1/n for that item's own option count, so the bar moves with the
# item rather than being one number applied to questions of different widths.
LEAK_MARGIN = 0.25


def leak_gap(question, options, correct_index, ask_fn=None, vault=VAULT):
    """J2 under the within-item control.

    Returns `(p_sighted, p_blind, drop)` for the logged-correct option, or three
    Nones. A leak is `p_blind` beating `1/len(options)` by `LEAK_MARGIN`; the
    drop is what says the question was doing any work at all.
    """
    labels, sighted = sighted_spec(question, options)
    _, blind = blind_spec(options)
    label = labels[correct_index]
    return paired_drop(({}, sighted, read_choice_mass("answer", label)),
                       ({}, blind, read_choice_mass("answer", label)),
                       ask_fn=ask_fn, vault=vault)


def calibrate_j2(vault=VAULT):
    """Run J2 (PLAN-2026-09-22.md) over every check with recoverable option
    text: ask Jev the learner's own question with no lesson material, and flag
    any case where Jev picks the logged-correct option with high confidence --
    a candidate for "the option set leaks the answer through shape."

    This is the calibration run Phase 3 asks for, against real data. It is
    explicitly a proof-of-concept, not a verdict on J2 as a gate: see the
    caveats printed at the end.
    """
    checks, skipped = find_mc_checks_with_options(vault)
    if not available(vault):
        print("jev: no key/package available -- clean no-op, nothing calibrated")
        return
    print("jev: found %d checks with recoverable option text (skipped %d with no "
          "recoverable option text: slot-only or prose-summary logs)" % (len(checks), skipped))
    flagged, results = [], []
    for check in checks:
        labels = ["opt%d" % (i + 1) for i in range(len(check["options"]))]
        criteria = dict(zip(labels, check["options"]))
        spec = {"answer": {"kind": "choice",
                            "instructions": "Answer the multiple-choice question below using only "
                                            "the information given here. Question: %s" % check["question"],
                            "criteria": criteria}}
        answers = ask({}, spec, vault=vault)
        if answers is None:
            results.append((check, None, None, None))
            continue
        answer = answers["answer"]
        jev_index = labels.index(answer["choice"]) if answer["choice"] in labels else None
        correct_label = labels[check["correct_index"]]
        matches_logged = jev_index == check["correct_index"]
        confidence = answer["confidence"]
        is_flag = matches_logged and confidence >= 0.7
        if is_flag:
            flagged.append(check)
        results.append((check, correct_label, answer, is_flag))
    for check, correct_label, answer, is_flag in results:
        tag = "FLAG" if is_flag else "ok  "
        if answer is None:
            print("  err   %-28s %s" % (check["subject"], check["question"][:60]))
            continue
        print("  %s  %-28s logged=%s jev=%s conf=%.2f  %s"
              % (tag, check["subject"], correct_label, answer["choice"], answer["confidence"],
                 check["question"][:55]))
    print()
    print("%d of %d checks flagged (Jev picked the logged-correct option, "
          "confidence >= 0.7, having never seen the lesson)" % (len(flagged), len(checks)))
    print()
    print("Caveats, read before acting on this:")
    print("- All %d recoverable checks are from one subject (pointers-and-references); "
          "no other session note preserved full option text." % len(checks))
    print("- The option text is the tutor's after-the-fact summary in the session note, "
          "not a guaranteed verbatim transcript of what the learner saw live.")
    print("- A flag may mean Jev knows the subject matter, not that the options leak the "
          "answer (tutor.md's own caveat on J2). Treat every flag as a prompt for human "
          "review, never a verdict.")
    print("- This is a proof-of-concept over the best-preserved historical subset, not the "
          "~40-check corpus Phase 3 describes -- most logged checks record only a slot "
          "number (key: N/M) or a prose summary, neither of which carries the option text "
          "J2 needs. Going forward this is moot only if checks start preserving it verbatim.")


# --------------------------------------------------------------------- CLI

# What each verdict means in terms of the write the caller now has to make. Kept
# next to the CLI rather than inside the routing, because the routing is the same
# judgement for both kinds and only the paperwork differs.
ACTIONS = {
    "preference": {
        "promote": ("this is sighting two -- promote it: append one line to *Observed* carrying "
                    "both sightings, and delete the matched line from *Candidates*."),
        "new": ("first sighting -- append it to *Candidates* in preferences.md with today's "
                "sighting. Write nothing to *Observed*."),
        "ask": ("middle band -- Jev is not sure these are the same claim. Carry the question "
                "into the closing block for Edison, and default to `new` if he does not decide."),
    },
    "misconception": {
        "promote": ("this is sighting two -- promote it into record.md's *Misconceptions* with "
                    "the evidence from both sightings."),
        "new": ("first sighting -- leave it as a candidate in this session's note. It does not "
                "go into record.md yet."),
        "ask": ("middle band -- Jev is not sure these are the same claim. Carry the question "
                "into the closing block for Edison, and default to `new` if he does not decide."),
    },
}

# The same in either kind: Jev was unreachable, so the judgement is the tutor's,
# under the rule learn-end step 5 already states.
JUDGE_YOURSELF = ("Jev could not be reached, so this is your judgement to make, under learn-end "
                  "step 5's own rule: if you are not sure they are the same claim, they are not.")


def print_match(result, kind):
    print("jev: kind=%s, compared against %d recorded observation(s) [%s]"
          % (kind, result["compared"], result["instrument"]))
    score = "" if result["score"] is None else " (p=%.2f)" % result["score"]
    print("verdict: %s%s" % (result["verdict"], score))
    if result["match"]:
        label = "match" if result["verdict"] == "promote" else "closest"
        print("%s: %s" % (label, result["match"]))
    if result["verdict"] == "judge-yourself":
        print("action: %s" % JUDGE_YOURSELF)
    else:
        print("action: %s" % ACTIONS[kind].get(result["verdict"], "no action defined"))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", type=Path, default=VAULT)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="report whether a semantic call could be made at all")
    sub.add_parser("calibrate-j2", help="J2 proof-of-concept over the historical checks")

    match = sub.add_parser("match-candidate",
                           help="J3: is this new observation the same claim as one on file?")
    match.add_argument("--kind", choices=["preference", "misconception"], required=True)
    match.add_argument("--new", required=True, metavar="TEXT",
                       help="the candidate as written in this session's note")
    match.add_argument("--subject", help="subject slug (required for --kind misconception)")
    match.add_argument("--skip-note", metavar="STEM",
                       help="session note to exclude, normally the one just written -- "
                            "without it a first sighting matches the copy of itself that "
                            "step 1 wrote and promotes on one sighting")

    args = parser.parse_args()
    vault = args.vault.resolve()

    if args.command in (None, "status"):
        if available(vault):
            print("jev: available (typesafe-sdk installed, TYPESAFE_API_KEY set)")
        else:
            print("jev: not available (no key or typesafe-sdk not installed) -- clean no-op")
        return 0

    if args.command == "calibrate-j2":
        calibrate_j2(vault)
        return 0

    if args.command == "match-candidate":
        if args.kind == "misconception" and not args.subject:
            print("jev: --kind misconception needs --subject <slug>", file=sys.stderr)
            return 2
        try:
            existing = existing_candidates(args.kind, vault=vault, subject=args.subject,
                                           skip_note=args.skip_note)
        except OSError as error:
            # Fail open: a missing or unreadable record is the tutor's own
            # judgement call again, not a crash inside /learn-end.
            print("jev: could not read the existing candidates (%s) -- judge it yourself"
                  % error, file=sys.stderr)
            return 0
        print_match(match_candidate(args.kind, args.new, existing, vault=vault), args.kind)
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
