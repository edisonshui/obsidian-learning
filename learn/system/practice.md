# Practice: getting taught ideas to come to mind on their own

This file is the method for `/learn-practice`. `tutor.md` still governs grading, feedback, notation, and reliability. This file says what changes when the job is practice instead of teaching. The skill holds the file mechanics.

## What practice is for

A check during a lesson asks about an idea the learner saw minutes ago, so the idea is still in mind. Passing it shows the step landed. It does not show that the learner will think of the idea when a problem looks different and nothing names it. Practice trains that second thing. Every problem starts with the idea out of mind, and only what the problem shows can bring it back.

Three rules follow from that:

- A problem is worth the number of places where the learner has to decide which idea applies, not its length. A long problem that follows one obvious chain has one such place.
- Asking the same thing again right after feedback trains little, because the answer is still in mind. A retest waits until other problems have come between, and it uses a new setting.
- Switch targets between problems. Two consecutive problems on one idea work like one long problem.

Practice teaches nothing new and never re-teaches. When a node clearly needs teaching again, name it for the next `/learn-resume` and move on.

## What it records

Practice records evidence and moves no status (decided 2026-10-25). Each problem gets a full entry in the practice note and one `[practice]` evidence line in `record.md` (`records.md`, *Evidence rule*). No node status, *Last checked* date, `plan.md` row, or reward changes because of practice. The record still learns from it through the evidence log, misconception candidates, and the next step `/learn-end` writes.

## Picking the target

Targets are taught nodes only: `introduced`, `checked`, `solid`, or `decayed`. A `skipped` node may be an ingredient in a combined problem. A `planned` node never is.

If the learner named nodes, a focus, or a problem source, that decides. Otherwise rank:

1. By status: `decayed`, then `introduced`, then `checked` nodes the dashboard lists as recall-only, then other `checked`, then `solid`.
2. Within a status, a node that more later nodes depend on (the prerequisite column in `plan.md`) comes first.
3. Then the node checked longest ago, from `learn-status.py --due --subject <slug> --per-subject 0`.

Before posing on a target, read its evidence lines and the subject's misconceptions. They show which version of the idea failed before and which ideas it gets confused with.

## Three kinds of problem

| Kind | What it trains | Shape |
| --- | --- | --- |
| Recall | The idea comes to mind from a problem that does not name it | One idea, one or two decisions, short |
| Tell apart | The right idea wins over one it gets confused with | Two setups that look alike, where one feature decides which idea applies |
| Combine | Several ideas run in a row | Two or three nodes, with a decision at each join |

On one target, go recall, then tell apart, then combine. Each kind needs the one before it: a learner who cannot recall an idea cannot pick it over a look-alike, and cannot chain steps they cannot recall. When a later kind fails, go back one kind on that target, because the earlier result overstated what the learner has.

Combine problems follow the plan's *Chains*: a chain is a set of nodes a real final problem uses together. Look-alike pairs come from the record's misconceptions, this subject's misconception candidates, and plan nodes whose problems look the same on the surface.

## Two dials

Within a kind, two dials set the difficulty:

- **Setting.** A *lesson setting* looks like the lesson's own examples. A *new setting* keeps the field but changes the story, names, and numbers. A *far setting* is an applied or real case, or hides the idea inside a bigger problem.
- **Ideas.** How many nodes the problem needs: one, two, or three.

After each problem, set the dials for that target's next problem from the result:

- Right with no hint: turn one dial up.
- Right after a hint: keep both.
- Wrong, or given up: turn one dial down, and consider going back one kind.
- Two consecutive misses on one target: the next problem goes to a different target.

Aim for problems the learner gets right with effort. A string of quick clean answers means the dials are too low, and a string of misses means they are too high.

## Session shape

1. **Warm-up.** One to three short recall problems in the lesson setting, on the weakest targets. They bring the subject back to mind and show where to set the dials.
2. **Main run.** Rotate targets. The kind follows the order above, the dials follow the last result, and settings move further from the lesson as answers come back right.
3. **Retests.** Before `/learn-end`, retest every miss, every problem that needed rung 3 or higher, and every problem given up, each in a new setting (`tutor.md`, *Ask every miss again*). If the learner stops first, list the ones left under *Next step*.

## Before posing

1. Pick the target, the kind, and the dials.
2. Write the problem, then solve it completely in thinking, every move in order. The solution is fixed before posing, so no later hint or verdict can contradict it.
3. Look for a way around the target: a route to the answer that never uses the idea. If one exists, the problem trains that route instead. Change the problem.
4. Check that it needs nothing the subject has not taught. If a fact in the problem or the solution is in doubt, run the `fact-checker` before posing (`tutor.md`, *Reliability rules*).
5. Pose it in chat as free response, standing alone (`tutor.md`, *Self-containment*). Never say which idea, node, or lesson it draws on. Ask for the work, the answer, and a confidence percent (`tutor.md`, *Confidence on every check*).

The solution goes into no file and no reply before the verdict. During practice the subject's `log.md` shows thinking folded closed, so solving in thinking keeps the solution out of sight.

## Hints in practice

A hint gives away part of the problem for good, while more thinking time costs nothing. So give the least that gets them moving, one rung per request, however hard they are struggling.

Read their work first and find the first decision they got wrong or could not make. It is often earlier than where they feel stuck: someone grinding through algebra may have chosen the wrong idea at the start. Hint at that decision. To flag a wrong choice, ask them to check the assumption behind it; do not say what the right one is while they can still find it.

| Rung | Hint | What it gives away |
| --- | --- | --- |
| 1 | **Look again.** Point at a given they have not used. | Nothing |
| 2 | **Name the kind.** Describe the kind of situation ("an amount built up from many small pieces") without naming the idea. | Part of the search |
| 3 | **Name the idea.** `tutor.md` rung 1, *Point*. | Bringing the idea to mind |
| 4 | **Narrow.** `tutor.md` rung 2. | Most of the choice |
| 5 | **Start.** `tutor.md` rung 3. | Running the idea |
| 6 | **Show.** `tutor.md` rung 4. | Everything except checking it |

When the learner only says they are stuck and shows no work, start at rung 1. Explaining what the question asks is not a hint. If the wording confused them, fix it at once and in full.

The highest rung a problem needed says how hard it was. Rungs 1 and 2 mean about right. Rung 3 or higher means it was too hard, and the dials go down.

## Grading

- An answer does not end the problem by itself. Read the work to find the ideas they reached for, the sequence, and the first step that failed.
- Right: say so, and name the move that made it work, in one line.
- Wrong: say it is wrong and where the first break is, without the fix. Then wait. Keep going, one nudge per try, until they solve it or ask for the answer. The number of tries, the time spent, and frustration are never reasons to reveal it.
- Sort each miss into one of five types. *Nothing came*: no idea surfaced. *Mix-up*: a look-alike idea won. *Slip*: the right idea, carried out wrong. *Careless*: fixed on sight once pointed at. *Wrong idea held*: the idea itself is wrong, which makes it a misconception candidate (`tutor.md`, *Feedback*).
- Grade honestly in both directions. A wrong answer is not softened and a right one is not inflated. Read confidence against the result as `tutor.md` says.

## Between problems

After a verdict, stop. The learner may ask about the problem. Answer briefly and only what was asked, then stop again. The next problem comes only when the learner says next. A question is never a go-ahead.

## Problems from outside

When the learner arrives with a problem from elsewhere (an old exam, homework they could not finish, a file), solve it first and list the nodes any correct solution has to use. From there it is handled like any other problem: hints, grading, the entry, the evidence line, and a retest if it was missed.
