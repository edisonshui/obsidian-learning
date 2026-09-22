---
name: learn-check
description: Run a mixed retrieval check on the current learning subject — recent nodes plus one older one — grade it, and log the evidence. Use every 2–3 nodes, or when Edison asks to be quizzed.
---

Run a retrieval check. The user may name a subject slug and node IDs after `$learn-check`. If no subject is given, use the subject whose session note was opened in this conversation; if none was, ask which subject.

## Build the check

- Read the current session note and `record.md`.
- Pick nodes: every node taught this session that is not yet `checked`, plus one older node for spacing. If node ids were given, use those instead.
- The older node is not chosen by eye. Run `python3 .claude/hooks/learn-status.py --due --subject <slug> --per-subject 0 --limit 1` and take what it names — it is the same picker a review uses, restricted to this subject, and it reads *Last checked* out of `record.md` rather than out of your memory of the conversation. It also prints that node's last evidence line: ask the same idea a different way, never the logged question again.
- Write 3–5 questions total. Mix formats: at least one free-response ("explain in your own words", "predict what happens", "what breaks if…") and at most two multiple choice built by mutating the correct claim (rules in `tutor.md`, *Checks and quizzes*). Decide each rubric before asking.
- Ask one question at a time. Use a question picker for multiple-choice questions when one is available.
- **Every question stands alone.** Code, data, or a diagram the question depends on goes *inside the question text*, fenced with its language — never only in a preceding message, and never referred to as "this" or "the following". If the learner says they cannot see it, resend it, confirm visibility, re-ask, and do not log the failed attempt as evidence about them.

## Grade and log

- Grade each answer plainly: right, wrong, or partially right, then why. Wrong answers get the correct answer and why the wrong option was tempting; then hint ladder rung 1 on a related follow-up, not a lecture.
- Log every question, answer, and verdict under *Retrieval checks* in the session note, and append an evidence line per question to `record.md`. This section is the only proof the gate was honoured, so it is written before the teach loop resumes, not at `$learn-end`. For each multiple-choice question, also log `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>` — the slot the correct option landed in, out of how many, then every option verbatim in slot order, separated by ` / `. `learn-status.py`'s G4 gate reads the slot across the subject's session notes and reports a repeated or over-used slot; the option text is the only record of what the learner actually chose between, and without it no later pass can tell whether the options gave the answer away.
- Update node statuses: a node taught this session that passes becomes `checked`; an older node that passes becomes `solid`; an older node that fails becomes `decayed`. A wrong answer that suggests a pattern goes under *Misconception candidates*.
- Report the result in three lines and continue the teach loop. If two or more answers were wrong, slow down: the next node gets smaller steps and a different representation.
