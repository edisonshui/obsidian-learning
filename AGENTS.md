# Learning vault for Codex

This vault is a one-to-one learning system. When tutoring here, read these files before teaching or changing a learning record:

1. `learn/system/tutor.md`
2. `learn/system/workflow.md`
3. The operational preferences printed by SessionStart. If missing, read the `Operational summary` in `learn/me/preferences.md`. Read that file in full for planning, preference updates, or conflicting guidance.

Codex does not expand Claude Code's `@file` imports, so read the files themselves. `CLAUDE.md` and `.claude/` remain the Claude Code setup. Both tutors share the records under `learn/`.

## At session start

The Codex `SessionStart` hook prints the date, each subject's title, status, last session and next step, operational preferences, and open-note warnings. It includes a full resume only when this conversation already has a selected subject. If the hook did not run, use `date`, `python3 .claude/hooks/learn-status.py --open-notes`, the subjects' record frontmatter, and the operational preference summary.

After selection, read that subject's `resume.md`, `record.md`, `plan.md`, and latest session note in full. Read `learn/system/records.md` before writing learning state.

List each subject on one line with title, status, last session, and next step. Ask which subject to resume with `$learn-resume <slug>`, whether to start one with `$learn-start <slug>`, or whether Edison wants something else. Do not teach, quiz, or plan until a subject is chosen.

## Hard rules

- Learning state lives in `learn/subjects/<slug>/` files. Neither the chat transcript nor Codex memory is a learning record.
- Write each taught node into the session note before starting the next node.
- During a lesson, treat `learn/system/` as read-only. Propose changes in chat for Edison to edit.
- In `learn/me/preferences.md`, append to *Observed* only when the stated evidence bar is met. Never edit *Stated*.
- Follow the reliability rules in `tutor.md`. Verify uncertain claims before the learner builds on them.
- Log a mixed retrieval check before opening a fourth consecutive new node. If skipped, record the reason under *Retrieval checks*; never leave that section empty.
- Each node entry needs a `Diagram:` line with its diagram or a sentence explaining why none helps.
- Never claim a write that did not happen. `$learn-end` re-reads the files it was meant to update and reports their actual state.
- The five learning skills under `.agents/skills/` describe file mechanics. Read `learn/system/records.md` before writing any learning record.

## Files and generated views

`learn/system/` holds the teaching rules, `learn/me/` holds learner preferences, and `learn/subjects/<slug>/` holds each subject's `record.md`, `plan.md`, `resume.md`, and `sessions/`. `learn/reviews/` holds cross-subject spaced-repetition notes, which belong to no single subject. `python3 .claude/hooks/learn-status.py` generates `learn/Dashboard.md` and each `progress.md` for both tutors. Do not hand-edit those views.

Claude Code writes each subject's `log.md`. Codex writes `codex-log.md` through `.codex/hooks/learning.py`. The separate logs prevent one tool's hook from overwriting the other's conversation. They are generated views, not learning state. Codex updates its log after submitted prompts and completed turns; it does not stream partial answers into Obsidian.

The Codex hook keeps its runtime state under `learn/.codex-runtime/`. `$learn-end` reads the clock with `python3 .codex/hooks/learning.py clock --subject <slug>`. If hooks are unavailable or not trusted, report `unknown` for the minute fields and continue maintaining the learning records.

Obsidian renders mermaid and LaTeX. Follow `learn/system/diagrams.md` and use full-root wikilinks such as `[[learn/subjects/oop/record|OOP record]]`.

For probes, put any code, data, or diagram inside the question itself. If a picker cannot display a long snippet, show it in chat, confirm Edison can see it, then ask. If he cannot see something, resend it before grading.
