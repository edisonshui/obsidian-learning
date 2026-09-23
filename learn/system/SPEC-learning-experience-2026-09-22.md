# Learning experience improvement spec

**Started, 2026-09-22.** This spec covers reliability, learner fit, context use, and the Obsidian view. It is separate from [[learn/system/PLAN-2026-09-22|the existing implementation plan]], whose earlier phases are complete.

**Closed, 2026-09-23.** All four priorities reached their main acceptance checks. This spec is superseded by a new revamp using the Matt Pocock skill workflow (`/setup-matt-pocock-skills`, `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`). The following items were still open when this spec closed and carry forward as input to that revamp:

- **Priority 1**: three visual checks were blocked and never completed: math rendering in the Codex chat client, the MATH 241 session note in Obsidian, and the Claude log in Obsidian.
- **Priority 3**: only the offline acceptance checks ran. Still unverified: live learner benefit from the operational summary, repeatability across more matched pairs or subjects, real model token counts and response latency, and a live startup/resume in each host after restarting it.
- **Priority 4**: Edison's verdict after using the styled prototype in real sessions is still open, and it decides whether to expand the CSS snippet to other subjects. The Live Preview editing view, narrow widths, and the `@media (max-width: 600px)` rule were never inspected.
- **Open decisions**: whether an Obsidian inbox is worth adding once a styled notebook has been used for a while, and which visual direction to commit to, restrained course colors or a more playful study dashboard.

## Goal

Make a learning session readable in Obsidian, complete as a record, and hard to corrupt with quiz or formatting mistakes. Keep the answer channel clear: Edison replies in the agent chat; Obsidian holds the notebook and progress view.

## Current evidence

| Concern | What the vault shows |
| --- | --- |
| Math display | [[learn/system/tutor|tutor.md]] requires MathJax delimiters, but the active MATH 241 note records two requests for a plain ASCII resend when rendered notation was invisible. The rule does not diagnose which display failed. |
| Codex log | `.codex/hooks/learning.py` stores submitted prompts and the `Stop` event's `last_assistant_message`. It does not collect intermediate assistant messages. Only one subject currently has a `codex-log.md`. Missing content needs a reproduced turn before its exact cause can be assigned. |
| Obsidian input | [[learn/system/workflow|workflow.md]] already says answers arrive in chat and the note is the notebook. There is no note-to-agent input path. |
| MC placement | [[learn/reviews/2026-09-22-r01|Review r01]] placed the key in slot 1 on five of six questions. The Dashboard reported the pattern after the review. |
| Learner preferences | [[learn/me/preferences|preferences.md]] is read at boot, checked by the plan reviewer, and updated at session end. Its stated preferences give concrete pacing and explanation rules. There is no measured comparison showing how much it changes teaching. |
| Context | Session start prints every subject's resume summary. The tutor also reads the system files and preferences, then the selected subject's records. No token or latency baseline exists yet. |
| Appearance | The Dashboard and progress notes already use status colors in Mermaid and Obsidian callouts. The vault has no CSS snippet configured. |

## Required behavior

### 1. Math that remains readable

Use one notation rule for chat, Claude's log, Codex's log, and session notes: `$...$` inline and `$$...$$` on separate lines for displayed math. Keep literal code and learner input in code formatting. When a learner reports an invisible expression, resend the same expression in plain ASCII before continuing the check. Record the display failure separately from evidence about the learner's math understanding.

First reproduce the failure in each affected host and view. A formatting linter can catch unmatched delimiters in records; it cannot prove that a chat client rendered the expression. The acceptance check therefore includes a visual pass on a small set of inline and displayed equations in both hosts and Obsidian.

### 2. Complete, honest logs

Define the log's promise precisely. Either capture every learner-facing assistant message, including intermediate messages, or label the Codex view as a completed-turn summary. Prefer the first option if a supported event or transcript provides a reliable source. Do not infer missing text from `last_assistant_message`.

Reproduce one affected Codex turn, compare the terminal transcript with `codex-log.md`, and identify the lost message type. Test subject selection as a separate case: a turn with no selected subject cannot appear in a subject log. Add a visible status when a selected subject has a prompt without a corresponding captured reply. Keep generated logs separate from learning state.

The old implementation plan says Codex has only three hook events. Current Codex hook documentation lists more events, including `PreToolUse` and `PostToolUse`. Recheck current host support before choosing the capture point. The configured hooks in this vault still use `SessionStart`, `UserPromptSubmit`, and `Stop`.

### 3. Multiple-choice keys varied before display

Put option ordering through one helper or preflight step that chooses a key slot before the question is shown. Across consecutive logged checks, do not reuse the previous key slot; within any five checks, no slot should hold the key more than twice. Keep the existing field that records the key slot and the options, plus the Dashboard's retrospective check. Apply the same construction path to lessons, retrieval checks, and cross-subject reviews.

Acceptance: a fresh review with at least six multiple-choice checks passes the slot rule, and its stored options match what Edison saw. This checks the mechanism before the learner answers, while the existing Dashboard check remains an audit.

### 4. Preferences with measurable effect

Keep `Stated`, `Observed`, and `Candidates` distinct. Use a short operational summary at session start: pacing, explanation order, check style, and display fallback. Keep the dated evidence in the full file for planning and updates. Run two matched lesson simulations with the same subject record, one with the operational summary and one without it. Judge only visible behavior: step size, example order, checks, hints, and whether math fallback occurs when requested. Do not claim a personalization gain until this comparison shows one.

### 5. Less repeated context

Measure the text loaded at session start and at resume before pruning it. Then change the start hook to show each subject's title, status, and next step, with the full resume for only the selected subject when selection is known. Keep the rule files available through pointers and read the selected subject's full record when teaching begins. Compare the new and old start output by length and run a cold-resume check: a fresh agent must still identify the current node, uncertain knowledge, and next action. Reject a shorter start message if that check fails.

### 6. More useful Obsidian view

Prototype a small CSS snippet scoped to learning notes. Use consistent colors for `solid`, `checked`, `introduced`, `decayed`, and `planned`; distinguish a question, hint, correction, and next action with callouts. Improve spacing and contrast in the Dashboard and progress view. Keep the underlying Markdown legible with the snippet disabled and in both light and dark themes. Do not encode status only by color.

The first visual milestone is a styled Dashboard and one subject progress page. A custom plugin or editable chat pane is outside this milestone. Obsidian documents CSS snippets and custom callouts as supported styling tools: https://obsidian.md/help/snippets and https://obsidian.md/help/callouts.

## Input decision

Keep chat as the primary answer channel for now. Editing a generated log would be overwritten and would leave the agent unsure which text is a new answer versus an annotation. If Obsidian input becomes valuable, prototype an explicit inbox note with a submit action and acknowledgement, not typing into the generated log. Test ordering, duplicate submissions, and interrupted turns before treating inbox text as graded evidence.

## Order of work

1. Reproduce math visibility and Codex log loss. These affect whether Edison can see the lesson and whether the record is complete.
2. Add pre-display MC placement and verify it in a real review. The existing after-the-fact gate already shows the failure.
3. Measure preference effect and context load. Keep only reductions that preserve a cold resume.
4. Style the Dashboard and one progress page. Expand the visual system after Edison has used the prototype.

## Verification checkpoint, 2026-09-22

- The current Codex rollout contains five completed assistant commentary messages from a fresh live turn. The updated transcript parser found all five, and a temporary-vault `codex-log.md` reproduced all five in order without a missing-reply warning. This checked the parser against a live rollout without adding a diagnostic turn to a subject log. The subject-selection case remains separate: this engineering turn has no selected learning subject.
- In the existing MATH 241 rollout, the parser found 46 assistant messages across 24 turns. Every captured message appears in the subject's `codex-log.md`. The five hook tests pass, including the existing intermediate-message, unselected-prompt, and missing-reply cases. The live turn has not yet reached `Stop`, so its final-reply path still needs an end-to-end check after completion.
- Claude chat visibly rendered inline chain-rule notation and displayed derivatives. Obsidian's MATH 241 Codex log visibly rendered inline equations, a displayed tangent-plane equation, and the previously reported limit block. The limit block is present but small at the current zoom; it was not invisible in this pass. The Codex chat client did not expose this turn's messages during the check, so its inline and display rendering remains unverified. The affected session-note and Claude-log views still need direct visual inspection. No new formatting failure was confirmed here.
- Before priority 2, finish those visual checks and compare the completed live turn, including its final reply, with the generated log. The transcript format is documented as unstable, so retain the completed-turn fallback and its visible label.

### Follow-up verification, 2026-09-22

- The previously live Codex conversation is complete. Its rollout has two turns with nine assistant messages total: seven in the first turn, including its final reply, and two in the handoff turn, including its final reply. A generated log in a temporary vault contained all nine messages exactly once and in order, with no missing-reply warning. The real conversation has no selected learning subject, so it correctly has no subject log. The five Codex hook tests pass. No log failure was reproduced, so the hook and its fallback were left alone.
- Direct visual inspection in the Codex chat client is blocked: computer use reports that the Codex app is unavailable for inspection. Direct Obsidian inspection of the affected session note and Claude log is also blocked: the accessibility tree switches to the requested note, but the screenshot remains on `AGENTS`; subsequent Obsidian actions report invalid elements or no available window. A fresh computer-use session showed the same mismatch. Neither rendered view can be claimed as verified from these attempts. The session note contains inline equations but no displayed equation; the Claude log contains inline equations and one `$$...$$` expression on a single line. Their source text was inspected, but that does not establish how Obsidian renders them.
- Priority 1 is complete where checkable and explicitly blocked for those three visual views. No formatting failure was visually reproduced, so no math or learning-record edit was made. Continue to priority 2 while preserving the visual checks as open acceptance evidence.

### Multiple-choice checkpoint, 2026-09-22

- Added `.claude/hooks/mc-preflight.py` as the shared pre-display step for diagnostic, lesson, retrieval, and review checks. It reads the relevant logged slot history, includes prepared questions, chooses an allowed key slot, and returns the displayed options with a matching `key:` evidence field. `tutor.md` now calls it, and the Claude learning skills permit that command. The pending placement ledger is generated runtime state under `learn/.mc-runtime/`, not a learning record.
- The command's temporary-vault tests went red when the command was absent and now pass. They cover a lesson after an existing subject key and six prepared review questions after an existing review key. The six-question sequence has no adjacent repeat or slot used more than twice in five, and each returned evidence field matches the displayed option order. The five Codex hook tests and the existing Claude hook assertions also pass.
- The required fresh review with Edison has not occurred. Its real displayed questions and saved review note cannot yet be compared, so priority 2 remains open for that acceptance check. No review or learner record was fabricated for the test.

### Priority 2 live acceptance, 2026-09-22

- Completed [[learn/reviews/2026-09-22-r02|r02]] with six fresh multiple-choice checks, each passed through `.claude/hooks/mc-preflight.py` before display and asked one at a time. Edison answered five correctly. The EALC 275 n3 check and follow-up were wrong; that node moved to `decayed` and its recurring misconception was recorded. All six answers and their status moves appear in the review note and subject records.
- Compared the saved A/B/C options and keys with the six questions shown in chat. They match in wording and order; two `score` occurrences received code formatting in chat. A saved-note check independently matched each option list to its `key:` field. The slots were **3, 2, 1, 2, 1, 3**: no adjacent repeat and no slot more than twice in either five-check window wholly within r02. The fresh-review acceptance check for priority 2 is complete.
- Ran `python3 .claude/hooks/learn-status.py` for the retrospective G4 slot check. G4 still reports the pre-existing r01 concentration in slot 1 and three five-check windows that begin in r01 and end at the start of r02. Those warnings are inherited from r01 and cannot be removed by changing later questions. No r02-only window failed. The full historical G4 report therefore remains unclean; retain the r01 evidence rather than rewriting it.
- `r02.md` was re-read on disk after closing. It is local learner data under the existing `learn/reviews/` Git ignore rule, so `git status --porcelain` does not list it. The spec and four subject records are listed. No existing uncommitted change was reset or staged.

### Priority 3 measurement checkpoint, 2026-09-23

Priority 3 uses required behaviors 4 and 5 above. Priorities 1 and 2 were not reopened. This was an engineering evaluation against copied records, not a learning session. No synthetic answer was added to a learner record, session note, review, or preference evidence.

#### Matched preference simulations

Two separate agents received the same complete MATH 241 `record.md`, `resume.md`, `plan.md`, s03 note, and `tutor.md`. Neither inherited the parent conversation or read the full preferences file. Both used the same model configuration inherited from the parent; no model or effort override was requested. Arm A received no operational summary. Arm B additionally received the exact `Operational summary` now in [[learn/me/preferences|preferences.md]]. That summary is 155 whitespace-separated words and 1,068 characters including its heading and trailing newline. It replaces the former application bullets; it does not change Stated, Observed, Candidates, or proposed changes.

Each agent produced one response to each of five identical scripted beats. These are independent scenario responses, not a fabricated continuous learner conversation:

1. "Continue the unfinished limit problem. I want to understand the reasoning."
2. Reset to the same point: "I am stuck. I do not see how the bound tells me the limit. Give me a hint."
3. "I cannot see that expression. Type the same math in plain ASCII."
4. "I can see 0 <= y^4/(x^2+y^2) <= y^2 now."
5. "Before another problem, show me why taking two paths to zero is not enough."

The common instructions required only the next learner-facing message for each beat, no invented answers, no learning-state writes, and free-response checks in both arms. The session lifecycle was excluded from these beats and tested separately below. The full tutor rules and subject-specific preferences remained in both arms. This tests the summary's additional effect under the existing rules, not personalization against a generic tutor with no learner context.

| Visible behavior | A: without summary | B: with summary | Decision |
| --- | --- | --- | --- |
| Step size and pacing | Beat 5 calculates both axis paths and the diagonal, concludes nonexistence, then checks explanation. 115 words. | Beat 5 calculates the axes, then asks the learner to evaluate the diagonal. 80 words. | B leaves a smaller next step in this example. No repeated trial establishes reliability. |
| Example order | Concrete bound before the squeeze check; concrete counterexample follows a short general warning. | Same order. | No observed advantage. |
| Checks | Four math checks and one visibility check across five beats. | Same counts; beat 5 asks for a calculation A already supplied. | Both preserve checks. B preserves more independent work on beat 5. |
| Hints | Points to the established bound, then asks what the outer bounds approach. | Supplies that both outer bounds approach zero, then asks for the squeeze conclusion. | B gives more intermediate information. Both withhold the final fraction limit, but B is not uniformly less directive. |
| Display fallback | Resends the exact inequality in ASCII, asks whether it is visible, then re-asks the math check after visibility confirmation. | Same behavior. | No observed advantage. Display failures produce no knowledge verdict in either arm. |

Response word counts for beats 1 through 5 were A: **57, 36, 14, 35, 115** and B: **65, 39, 12, 31, 80**, counting code and question text by whitespace. Both use ASCII from beat 1 because the common subject state already records that need. This is one matched pair with synthetic learner prompts, no learner answers, and an unblinded human-readable assessment by the parent agent. The independent agents did not see each other's outputs. The result supports a visible difference in one example, not a causal or demonstrated-understanding gain. Keep the short summary as an operational reminder and a way to defer the dated evidence; do not claim that it improves learning.

<details>
<summary>Exact simulation outputs for inspection</summary>

#### A: without the operational summary

````text
# Beat 1

We already have this bound for every point except the origin:

```text
0 <= y^4/(x^2+y^2) <= y^2
```

The fraction stays inside that interval regardless of the path taken toward the origin. We stopped before you gave the conclusion.

Using `0 <= y^4/(x^2+y^2) <= y^2`, what limit must the fraction approach as `(x,y) -> (0,0)`, and why?

# Beat 2

Use the bound we established:

```text
0 <= y^4/(x^2+y^2) <= y^2
```

Look at the two outside expressions. Their behavior is what the squeeze theorem uses. What do `0` and `y^2` approach as `(x,y) -> (0,0)`?

# Beat 3

```text
0 <= y^4/(x^2+y^2) <= y^2
```

Can you see the whole inequality now?

# Beat 4

Using the visible bound:

```text
0 <= y^4/(x^2+y^2) <= y^2
```

What does the squeeze theorem tell you about the limit of `y^4/(x^2+y^2)` as `(x,y) -> (0,0)`? Explain how the outside expressions justify your answer.

# Beat 5

Two paths only tell us what happens on those two paths. To see the gap, use this example:

```text
f(x,y) = x*y/(x^2+y^2), for (x,y) != (0,0)

Along y = 0: f(x,0) = 0.
Along x = 0: f(0,y) = 0.
Along y = x: f(x,x) = x^2/(2*x^2) = 1/2, for x != 0.
```

Both axis paths approach `0`, but the diagonal approaches `1/2`. A limit must work for every approach through the domain, so this function has no limit at the origin. That is why we sought a bound covering every nearby point for the unfinished problem.

For `f(x,y) = x*y/(x^2+y^2)`, why does the diagonal invalidate the conclusion that the two axis paths suggested?
````

#### B: with the operational summary

````text
## Beat 1

We already established this bound for every point near the origin except the origin itself:

```text
0 <= y^4/(x^2+y^2) <= y^2
```

That is why the bound helps: it controls the expression regardless of which path you take.

As `(x,y) -> (0,0)`, both outer bounds approach `0`. What limit does the squeeze theorem force for `y^4/(x^2+y^2)`, and why can it not approach a different value?

## Beat 2

Use the fact we established before the break: in

```text
0 <= y^4/(x^2+y^2) <= y^2
```

both outer bounds approach `0` as `(x,y) -> (0,0)`. What does the squeeze theorem tell you about an expression trapped between those bounds?

## Beat 3

```text
0 <= y^4/(x^2+y^2) <= y^2
```

Can you see this version?

## Beat 4

Given

```text
0 <= y^4/(x^2+y^2) <= y^2
```

and both outer bounds approaching `0` as `(x,y) -> (0,0)`, what is the limit of `y^4/(x^2+y^2)`? Explain how the bound forces your conclusion.

## Beat 5

Two paths can miss behavior on another path. Let's test that with a function you have worked with:

```text
f(x,y) = x*y/(x^2+y^2)
```

Along either axis, the numerator is `0`, so both paths give a limit of `0`:

```text
x = 0: f(0,y) = 0      for y != 0
y = 0: f(x,0) = 0      for x != 0
```

Now check the diagonal. For `f(x,y) = x*y/(x^2+y^2)` along `y = x`, what does `f(x,x)` approach as `x -> 0`?
````

</details>

The common subject-record SHA-256 was `585554d2c431d167b4a5227d478ec9955b914c953d3c7d77d9b4be3c0d156cc8`; s03 was `d5f258afd894dbfe0728fbdec429e73f58da39dbdb17982a89c1266d8a2d1929`; tutor rules were `59db79f4590dad1314ff242bb18e3b099e57c63b0ca93b5bc0c78a118fdd651a`. The packets and raw measurements were saved locally in `/var/folders/ks/6tn7cg8j7pqc22hc38c9xv7m0000gn/T/learning-p3-2umadsve`. The outputs and decision evidence are embedded here so this checkpoint does not depend on temporary files surviving.

#### Context measured before changing the hooks

Captured the existing output and source files before editing either start hook. Measured both old hooks against a temporary copy of the current subjects. The new hooks used the same copy, with only the operational summary updated. Dashboard refreshes and open-note scans ran against that copy. No production generated view was refreshed for this evaluation.

Counts below are Unicode characters and whitespace-separated words, not estimated model tokens. A model tokenizer was unavailable. Five local executions per case measured elapsed hook time with `time.perf_counter`; these are local hook timings, not model response latency. Codex was measured at its Python start function and Claude through its shell entrypoint, so only within-host comparisons are meaningful.

| Hook case | Before chars / words | After chars / words | Before / after median ms |
| --- | --- | --- | --- |
| Codex, no selected subject | 7,900 / 1,170 | 3,043 / 455 | 60.5 / 62.2 |
| Claude, no selected subject | 8,065 / 1,192 | 3,044 / 455 | 87.2 / 91.5 |
| Codex, MATH 241 selected | 7,900 / 1,170 | 4,096 / 598 | 60.5 / 61.6 |
| Claude, MATH 241 selected | 8,065 / 1,192 | 4,097 / 598 | 87.2 / 91.4 |

Old startup printed every resume regardless of selection. New startup prints every subject's title, status, last session and next action, open-note warnings, the operational preferences, and file pointers. When the current conversation has a selected subject, it also prints that subject's full `resume.md`, including frontmatter. It does not silently truncate the selected resume. The no-selection output is 61.5% shorter for Codex and 62.3% shorter for Claude by characters. Hook latency did not improve in this sample.

Measured the documented load through a full MATH 241 resume as well, to distinguish removed text from deferred text:

| Host and stage | Before chars / words | After chars / words |
| --- | --- | --- |
| Codex boot | 39,650 / 6,137 | 7,085 / 1,022 |
| Codex through resume | 96,930 / 14,902 | 85,352 / 13,143 |
| Claude boot | 42,540 / 6,508 | 9,721 / 1,353 |
| Claude through resume | 99,715 / 15,250 | 87,883 / 13,451 |

Accounting: boot is the unselected hook output plus the host entrypoint. Before, it also includes the three mandated boot reads, `tutor.md`, `workflow.md`, and full `preferences.md`. Through-resume adds the selected subject's complete resume, record, plan and s03 note, the host's resume skill, and `records.md`. After, tutor and workflow are read at teaching time and added to that total. Each file read is counted once, while text emitted by the hook and then read again remains counted twice. Wrapper separators, tool metadata, global instructions, skill catalogs, reasoning, and unrelated engineering context are excluded. These are reproducible source-text budgets, not measurements of an entire live model prompt. Full preferences were 7,452 characters / 1,143 words before; their dated evidence remains available and must still be read for planning, updates, or conflicting guidance. That conditional full-file read is outside the ordinary-resume totals above.

#### Implementation and retention gate

Both hosts now use `.claude/hooks/session_context.py`. The Claude shell adapter supplies its vault and reads selection from the payload's session ID in Claude's existing runtime. Codex supplies selection from its own current-session state. Neither borrows selection from another conversation's global active-session pointer. A fresh conversation still asks for a subject. Missing preferences, a missing selected resume, or a failed open-note scan produces an explicit fallback instruction.

`AGENTS.md`, `CLAUDE.md`, and workflow boot instructions now point to full rule files for teaching and to full preference evidence for planning, updates, and conflicts. The selected subject's full record remains mandatory. No resume skill mechanics or subject state were changed.

A fresh third agent received only the compact unselected startup, the subject choice `math241-exam1-review`, and permission to follow its file pointers. It inherited no lesson transcript and did not read full preferences or either simulation. It recovered all three required fields:

| Cold-resume criterion | Recovered answer and evidence | Result |
| --- | --- | --- |
| Current node | n7, fourth-set problem 6; the squeeze bound is established and the independent conclusion is absent. Cited resume, record, and s03. | Pass |
| Uncertain knowledge | Final limit conclusion and the two-path misconception remain unverified; a display failure is separate from a math verdict. Cited s03 and record evidence. | Pass |
| Next action | Finalize the stale s03 pause without inventing evidence, open s04, run a logged decay check, then ask the independent squeeze conclusion in ASCII. Problem 7 follows only after retrieving its table; problem 4 waits for visible figures. Cited startup warning, closing rule, and resume skill. | Pass |

The startup warning correctly overrode old same-note-resume wording. The agent also recognized newer review evidence in the full record rather than treating the shorter summary as authoritative. This passes the retention gate, so keep the shorter startup. The selected-subject case adds its full resume to the same output; executable tests cover that addition and conversation isolation. The fresh-agent check used the harder unselected-start path followed by explicit selection. The shared renderer gives both hosts the same content apart from the shell's final newline.

The initial cold packet still contained the old workflow Phase 0, which the agent flagged. That copied file was then synchronized with the implemented pointer text and explicitly re-read in a follow-up. The initial recovery of node, uncertainty, and next action had already passed; this follow-up corrects the fixture's outdated boot claim rather than counting as a second independent cold test.

The agent followed one linked older MATH 241 note while locating the next problem. The required table values and quadric figures/options were not in the selected records. Those source dependencies predate the startup reduction. This check establishes recovery of the next action, not completion of every pending practice item. It made no learning-state writes and did not close the real stale note.

Verification at the public hook entrypoints used temporary vaults. The compact-start test first failed in both hosts because unrelated resumes were still printed. After the shared formatter change it passed. A second test first failed because the selected full resume was absent; after selection routing it passed, including content beyond the old 3,000-character cap and isolation from a new conversation. A regression check verifies that startup emits operational preferences while leaving dated observations and unconfirmed candidates out of the output. `python3 .codex/hooks/test_learning.py` passed all eight tests. `python3 .claude/hooks/test_hooks.py` reported all assertions passed. `bash -n .claude/hooks/session-start.sh` passed. These regression runs did not repeat priority 1's visual checks or priority 2's live review.

Priority 3's requested offline acceptance checks are complete: matched behavior comparison, pre-change context baseline, before/after start and resume budgets, and cold recovery of current work, uncertainty, and next action. Retain the compact startup and operational summary with the limitations above.

Still unverified: live learner benefit, repeatability across more matched pairs or subjects, actual model token counts and response latency, and live startup/resume in each host after this change. The public entrypoints were exercised with fixture payloads; this session did not restart either host. These are explicit limits, not claimed passes. Priority 1's already-open visual checks remain open; priority 2's recorded live acceptance remains unchanged.

Before finishing, compared file hashes against the pre-edit snapshot. Only the two start adapters, shared formatter, Codex hook tests, host entrypoints, operational preference summary, workflow boot paragraph, and this spec changed during this task. Existing edits outside that scope, generated views, and subject learning state remained byte-for-byte unchanged. Stated, Observed, Candidates, and proposed preference changes were checked separately and preserved exactly. Nothing was staged or committed.

### Priority 4 visual checkpoint, 2026-09-23

Priority 4 uses required behavior 6. The milestone is the Dashboard and one progress page, `oop`. Both opt in with `cssclasses: [learning-note]`; other progress pages are unchanged. The uncommitted prototype was first committed as a checkpoint (`3e7d409`) before verification.

- `learn-status.py` writes each known status as `<code data-learning-status="x">x</code>`. The status name is always the visible text, so status is never encoded by color alone. An unrecorded status stays plain inline code and never enters the attribute. The oop status table lists all five core statuses, with `None` for empty ones. Each next action is a `todo` callout. The oop page ends with a callout key labelled as visual examples, not lesson evidence.
- `test_hooks.py` now covers that output: opt-in frontmatter, attribute and text agreement, the unknown-status fallback, the unstyled path for other subjects, the Dashboard status key, and next-action callouts. Two deliberate mutations of `learn-status.py` each failed a test and were reverted. The full suite passes.
- Edison inspected both notes in Obsidian's Reading view in light, dark, and snippet-disabled views. Status pills, tables, heading dividers, and page width passed in all three. With the snippet disabled, every status read as plain inline code and every callout fell back to Obsidian's default style with its title and icon. No raw HTML appeared, so this Obsidian build keeps the `data-` attribute on inline HTML.
- Defect found: with the snippet on, the four custom callouts lost their background tint and title color; only the snippet's own left border was colored. Screenshot pixels confirmed it: callout body equal to the page background and neutral title ink. Cause: this Obsidian build reads `--callout-color` as a full color through `color: var(--callout-color)` and `color-mix(in oklch, var(--callout-color) 10%, transparent)`, found in its bundled CSS. The snippet had set a bare `r, g, b` triple, the older format, which is invalid in both. Fix: the eight `--learning-*` colors are now `rgb(...)` values, and the border uses `var(--callout-color)` directly. A test now fails if a bare triple returns; it failed against the old snippet. As a side effect, built-in callouts on these notes, such as the Generated file warning, now also get the left border.
- Recheck after the fix, light and dark, snippet on: each callout has a tinted fill and a colored title and icon. Title contrast measured from screenshot pixels, against the callout fill: light 5.9 to 7.1:1, dark 7.5 to 8.6:1. All clear WCAG AA's 4.5:1 for normal text. These are antialiased pixel samples, so treat them as approximate.

Priority 4's first visual milestone passes. Still open: Edison's verdict after using the prototype in real sessions, which decides whether to expand it to other subjects and settles the visual-direction question below. The Live Preview editing view was not inspected, and neither were narrow widths or the `@media (max-width: 600px)` rule. The Obsidian inbox question remains open.

## Design approach

Use `encode-lessons` to turn the repeated MC and notation rules into checks or shared construction paths, not another paragraph of instructions. Use `codebase-design` to keep each host's hook adapter small and put shared validation behind one interface. Use `writing-for-agents` when editing the host instructions, keeping always-loaded pointers short. Use `tdd` for hook and validator changes. The spec itself is a proposal; these mechanisms count as implemented only when code and verification exist.

## Open decisions

- Resolved: the former Stop-only Codex log omitted intermediate commentary. The transcript path now captures it, including final replies. Turns before subject selection remain outside subject logs by design.
- Does Edison want an Obsidian inbox after seeing a styled notebook, or is chat plus notebook enough?
- Which visual direction should the first prototype use: restrained course colors or a more playful study dashboard?

## Sources checked

Local: `learn/system/tutor.md`, `workflow.md`, `records.md`, `PLAN-2026-09-22.md`, `learn/me/preferences.md`, `learn/reviews/2026-09-22-r01.md`, `.codex/hooks.json`, `.codex/hooks/learning.py`, `.claude/hooks/learn-status.py`, and `.obsidian/appearance.json`. External: [Codex hooks](https://learn.chatgpt.com/docs/hooks), [Obsidian CSS snippets](https://obsidian.md/help/snippets), and [Obsidian callouts](https://obsidian.md/help/callouts).
