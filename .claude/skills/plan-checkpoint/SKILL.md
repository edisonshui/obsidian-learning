---
name: plan-checkpoint
description: End an engineering session on the vault's improvement plan, mark what got done, then print a three-part handoff (next prompt, model and effort, tech fit) for the next session. Use when Edison says checkpoint, wrap up, or ends a session that was building the plan itself, not tutoring.
argument-hint: "[done: session N | phase name]"
allowed-tools: Read, Edit, Glob, Bash(git status*), Bash(git diff --stat*)
---

This is not `/learn-end`. That skill closes a *tutoring* session and writes a learner's `resume.md`. This skill closes an *engineering* session on `learn/system/PLAN-*.md`, the vault-improvement work itself, and writes nothing to any subject's records.

Token budget for this skill: one plan file read, one `git status`/`git diff --stat`, at most one clarifying question. Never re-read the vault or re-derive the Jev fit or skill picks. They are already written in the plan; quote them.

## 1. Find the plan

`Glob` for `learn/system/PLAN-*.md`, take the most recent by the date in the filename. If none exists, say so and stop because there is nothing to checkpoint.

## 2. Find what changed

Run `git status --short` and `git diff --stat`. Match changed paths against the plan's phase descriptions (Phase 0 touches `resume.md`/session notes/`.gitignore`; Phase 1 touches `learn-status.py` and `test_hooks.py`; Phase 2 touches the skill pairs and the log-link code; Phase 3/4 touch `.claude/hooks/jev.py` and `.env`; Phase 5 is design). If `$ARGUMENTS` already names what got done, use that instead of inferring. If neither the diff nor the argument makes it clear, ask one short question. Do not guess silently because a wrong status here corrupts every future handoff.

## 3. Update the plan file

In the `## Suggested order and sizing` table, set the `Status` cell for each session row touched this session: `in progress` if some but not all of its listed content changed, `done` if all of it did and (for Phase 1/2/3) the relevant tests pass. Do not touch rows nothing this session touched. This is the only edit this skill makes to the plan file.

## 4. Print the handoff with exactly these three things

**Next prompt.** One copy-pasteable block that works unchanged in Claude Code or Codex. Name the plan file and the next `not started` or `in progress` row by its Phase content, and tell it explicitly not to re-audit or re-read the whole vault. The plan already has the file inventory, the measured violations, and the constraints for that phase. Carry forward only what is still open from the row just closed, such as a failing test or a deferred decision. Do not restate finished work. If every row is `done`, say the plan is complete and do not invent follow-on work.

**Model and effort.** Print a Claude Code choice and a Codex choice for the same work. Apply this fixed rule, do not re-derive it:
- Work that is mechanical and has a test or a clear diff to check it against (file edits to a spec, parsing/consistency-check code, anything Phase 0-2): **Claude Code: Sonnet 5, medium effort. Codex: GPT-6 Sol, medium effort.**
- Work that sets a threshold, designs a seam, or decides something with no test to check it against (the Jev calibration call in Phase 3, the `/learn-review` seam in Phase 5, any drift-test *design* rather than its implementation): **Claude Code: Opus, high effort. Codex: GPT-6 Astra, high effort.**
- If the next row mixes both, say which parts are mechanical and which require design judgment. If the plan is complete, say no model is needed.

**Tech fit.** Quote the plan's own `Where Jev fits` and `Which Matt Pocock skills apply` sections for whatever the next row covers. Do not re-research them. If the next row is Phase 0-2, the honest answer is "none yet, Jev work starts at Phase 3". Say that rather than reaching for a use. If the plan is complete, say there is no next-row tech fit.

Send this as one block and stop. Do not restate the checklist from step 3 separately or re-print the whole plan.
