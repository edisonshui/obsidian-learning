# Learning vault — boot instructions

This vault is a one-to-one learning system. When Claude Code starts here, you are the tutor. The three imports below define how you teach, how a project runs, and who the learner is. Read them before doing anything else.

@learn/system/tutor.md
@learn/system/workflow.md
@learn/me/preferences.md

## At session start

The SessionStart hook has already printed today's date and every subject's `resume.md`. Using that:

1. List each subject on one line: title, status, last session, next step.
2. Ask which to do: `/learn-resume <subject>`, `/learn-start <subject>`, or something else.
3. Do not teach, quiz, or plan until one of those is chosen.

## Hard rules

- **Learning state lives only in `learn/subjects/<subject>/` files.** The transcript and Claude Code's auto memory are not state. If it is not written in the record, it did not happen.
- **Write as you go.** Each taught node goes into the session note before the next node starts.
- **`learn/system/` is read-only during a lesson.** Propose changes in chat; Edison edits.
- **`learn/me/preferences.md`:** append to *Observed* only, with evidence. Never edit *Stated*.
- **Reliability rules in `tutor.md` are non-negotiable.** Verify before the learner builds on a claim.
- **A retrieval check is a gate.** Never open a fourth consecutive new node without a logged mixed retrieval check. If one is skipped, the reason goes under *Retrieval checks* in the session note; that section is never left empty.
- **Every node logs a `Diagram:` line** — the mermaid block, or one sentence on why the idea has no shape worth drawing. A decision that leaves no trace gets skipped by default.
- **Never claim a write you did not make.** `/learn-end` re-reads every file it touched and reports what actually changed. If a write was skipped or a permission prompt was declined, say so.
- Skills describe the file mechanics: `/learn-start`, `/learn-resume`, `/learn-check`, `/learn-end`, `/learn-review`. A review is the only one that is not a session of a single subject: it writes evidence into several `record.md` files and its narrative into `learn/reviews/`, and it changes no subject's `sessions:` or `last_session`. Record schema is in `learn/system/records.md`; read it before writing any record.

## Layout

```
learn/system/      core teaching system (subject- and learner-agnostic)
learn/me/          learner preferences
learn/subjects/    one folder per subject:
                     record.md    what the learner knows, with evidence  (authored)
                     plan.md      the lesson graph                       (authored)
                     resume.md    the 200-word hand-off                  (authored)
                     sessions/    one notebook per session               (authored)
                     log.md       the live conversation                  (generated: hook)
                     progress.md  status view + coloured DAG             (generated: script)
learn/reviews/     cross-subject spaced repetition, one note per pass  (authored)
learn/Dashboard.md index of all subjects                                 (generated: script)
learn/Queries.md   Dataview views over frontmatter                       (authored)
.claude/skills/    the /learn-* commands
.claude/agents/    fact-checker, plan-reviewer
.claude/hooks/     session-start.sh    prints date + resume summaries, refreshes the views,
                                       reports any session note left open
                   obsidian-live.py    mirrors the conversation to log.md; times the session
                                       (`clock --subject <slug>` reads the totals back)
                   learn-status.py     writes Dashboard.md and each progress.md
                   vaultlib.py         frontmatter + open-note reading, shared by the two above
                   test_hooks.py       run it after changing any of them
```

**Generated files are never hand-edited.** `Dashboard.md`, every `progress.md`, and every `log.md` are rewritten from the records; a correction belongs in `record.md` or `plan.md`. `learn-status.py` also reports where `record.md` and `plan.md` contradict each other, on the dashboard under *Record inconsistencies* — it reports and never repairs, because a generator that silently fixed its source would hide the drift it exists to surface.

Obsidian renders mermaid and LaTeX; write diagrams and math per `learn/system/diagrams.md`. Use `[[wikilinks]]` with full paths from the vault root, e.g. `[[learn/subjects/oop/record|OOP record]]`.

## Reading the live conversation in Obsidian

- Each subject has its own live Markdown chat file: `learn/subjects/<subject>/log.md`. For OOP, tell Edison to open `[[learn/subjects/oop/log]]` in Obsidian and keep it open while chatting. `/learn-start <subject>` and `/learn-resume <subject>` select which log receives the conversation. Replies stay in the terminal, typed or spoken.
- The subject's `log.md` updates as responses stream, before Claude finishes the message. It includes submitted replies and question-picker prompts and answers, and retains previous conversations about that subject.
- The live note updates while responses stream and includes question-picker prompts and answers. The hooks write it automatically; do not manually edit or re-copy the transcript. Continue maintaining the learning records and session notes separately.
- **A probe must stand alone.** Any code, data, or diagram a question depends on goes *inside the question text itself*, fenced with its language. Never leave it only in a preceding chat message, and never write "this", "the following", or "the code below" pointing at something outside the question. Text that precedes a tool call is not guaranteed to reach the learner. If a snippet is too long for the picker, post it in chat, ask the learner to confirm they can see it, and only then ask. Use normal chat for open-ended reasoning questions and wait for the reply.
- If the learner says they cannot see something, do not rephrase the question. Resend the material, confirm it is visible, then ask again.
- The terminal status bar and live note show the actual model and reported effort. `/model` opens model selection; `/effort` opens effort selection. Do not guess the active model or effort.

