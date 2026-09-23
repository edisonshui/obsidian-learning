---
subject: "{{slug}}"
session: "{{NN}}"
date: "{{YYYY-MM-DD}}"
start: "{{HH:MM}}"
end:
paused:
active_minutes:
idle_minutes:
nodes: []
---

# {{Title}} — session {{NN}} ({{YYYY-MM-DD}})

## Plan for this session

*(Which nodes, from `plan.md`. Decay check result if this is a resume.)*

## Lesson

*(Appended node by node as taught. For each node: the motivation, the explanation as given, diagrams, the check question, the learner's answer, the verdict. Write it so that re-reading this section alone re-teaches the node.)*

### {{node id}} — {{node name}}

**Motivate.**

**Establish.**

**Connect.**

**Diagram.** *(The mermaid block as drawn, or one sentence on why this idea has no shape worth drawing. Required — never leave blank.)*

**Check.** Q: … / A: … / Verdict: … *(multiple choice: append `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>` — the slot the correct option landed in, out of how many, then every option verbatim in slot order. The rotation rule is in `.claude/hooks/slot_rotation.py`; G4 reads the slot, `--semantic` reads the options)*

## Retrieval checks

*(Mixed checks from `/learn-check`: question, node, answer, verdict, and for multiple choice `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>`. Never left empty: if no check ran before a fourth new node opened, write "none run — gate violated" and why.)*

## Misconception candidates

*(Wrong answers that suggest a pattern. Promote to `record.md` when seen twice or confirmed.)*

## Preference candidates

*(How this learner learns, as shown by this session — not what was taught. One line each: `enjoyed | demonstrated: <observation> — evidence: <what happened>`. A sighting goes here even when it is the first; that is the whole point of the section, since the bar in `preferences.md` is two sightings and they may fall in different sessions. Leave empty if nothing showed.)*

## Corrections

*(Anything the tutor got wrong and corrected, with what was affected.)*

## What worked / what didn't

*(Which representations landed, where pace was off, what to change next session.)*

## Next step

*(One line: the first thing the next session should do.)*
