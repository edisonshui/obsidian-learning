# Diagrams — rules for pictures in lessons and plans

Obsidian renders mermaid blocks and LaTeX natively, so a diagram written into a note is a diagram the learner sees. A diagram earns its place when the *shape* of an idea is the point: a dependency order, a decision, a flow, a two-axis tradeoff. It does not earn its place as decoration. A diagram makes a plan inspectable; it does not make it correct, so it never replaces a check question.

## When to draw which

| The idea is about… | Draw | Mermaid type |
| --- | --- | --- |
| What depends on what (the plan itself, prerequisite chains) | Dependency graph | `flowchart TD` |
| A process or algorithm's steps | Flow chart | `flowchart TD` or `LR` |
| A choice with conditions ("if X then…") | Decision tree | `flowchart TD` with `{diamond}` nodes |
| Two independent tradeoffs | Quadrant chart | `quadrantChart` |
| Objects and their relationships (classes, tables, entities) | Class diagram | `classDiagram` |
| Order of events between parties | Sequence diagram | `sequenceDiagram` |
| A state that changes on events | State diagram | `stateDiagram-v2` |

If a type fails to render in Obsidian (its bundled mermaid can lag the newest release), fall back to `flowchart`, which always renders.

## Rules that keep diagrams rendering

- Fence with three backticks and `mermaid`, nothing else on the fence line.
- Twelve nodes or fewer. If it needs more, it is two diagrams.
- Node ids: letters and digits only (`n1`, `Base`, `Step2`). Put the human text in the label.
- Quote any label containing parentheses, colons, quotes, or `#`: `A["f(x): the input"]`. Unquoted, these characters break the parser.
- Edge labels: `A -- "label" --> B` or `A -->|"label"| B`.
- No `%%{init}` directives, no `click` handlers, no HTML in labels except `<br/>` for a line break. One level of `subgraph` at most.
- No `classDef` or `style` lines. The vault's CSS colours every diagram to match the log and flips it for dark mode; an inline colour overrides both.
- Re-read the block after writing it: balanced brackets and quotes, every id defined before it is styled, arrows pointing the way the reasoning flows.

## Diagrams in chat replies

When a reply teaches something with a shape, draw it as a mermaid block in the reply, not as box-drawing characters. The reply is mirrored into the subject's `log.md`, where the learner reads along and Obsidian draws it in the log's style. The terminal shows only the mermaid source (2026-10-13).

- Mark the one node the reply is about with `class <id> key` on its own line. The log's CSS draws every other node as translucent glass and this one solid with an ink outline. One per diagram, two at most, or nothing stands out.
- Keep decision (`{diamond}`) labels to about four words. A diamond grows with its label, and a long one swamps the diagram.
- Side-by-side comparisons (compile time vs run time, before vs after) read best as `flowchart LR` with one `subgraph` per side. Chains of decisions read best as `TD`.
- Two cases keep box-drawing characters in a ` ```text ` block. Any picture inside a question-picker probe, because the picker shows mermaid as raw source. And grids that must line up cell by cell (array slots, a memory layout next to the code), because mermaid cannot align cells.

```mermaid
flowchart LR
    subgraph CT["Compile time asks: does Pet have this method?"]
        p["variable p<br/>type: Pet"]
    end
    subgraph RT["Run time asks: which version runs?"]
        d["Dog object<br/>speak() returns woof<br/>fetch()"]
    end
    p -- "points to" --> d
    class d key
```

## Math

Inline math `$x^2$`, display math on its own lines with `$$ … $$`. Obsidian uses MathJax; standard LaTeX commands work, `\text{}` for words inside math.

## Code

Fenced code blocks with a language tag (` ```java `, ` ```python `). Keep example code under 20 lines; a check question about a 40-line example is a reading test, not a concept test.

Lay code out the way the learner's editor does: 4-space indents, one statement per line, and a method or `if` body on lines of its own, never `void speak() { ... }` on one line. The learner copies examples into the Code runner and their IDE, and 2-space one-liners read as wrong there (2026-10-13).

## A minimal example

```mermaid
flowchart TD
    A["Unconditional truth"] --> B["First derived step"]
    B --> C{"Check: can they predict the next case?"}
    C -- yes --> D["Next node"]
    C -- no --> E["Smaller step, new representation"]
    E --> B
```
