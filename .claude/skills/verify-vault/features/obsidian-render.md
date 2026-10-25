# Obsidian rendering

Edison reads session notes, `plan.md`, `progress.md`, and the live `log.md` in Obsidian. Obsidian renders mermaid diagrams, embedded SVG figures, callouts, LaTeX, and the Dataview queries in `learn/Queries.md`. The `learn-live` plugin adds Run buttons on code fences, the Code runner pane, per-subject themes, and opens generated notes in Reading view. This surface is optional. Use it only when a change affects how a note looks, not what it says.

## Sub-features

- `or-mermaid` renders a `flowchart TD` block in `plan.md` and session notes, including the `class <id> key` highlight (`learn/system/diagrams.md`).
- `or-figure` renders a `![[<slug>-<topic>.svg]]` embed built from `learn/system/templates/figure.svg`, in ink-only classes with a dark-mode block.
- `or-callout` renders the live log's callouts: `[!info] Live note`, `[!quote] You · HH:MM`, `[!question] Question`, `[!quote] Your answer`, `[!code] Your code`, `[!warning]` probe notices, and `[!thinking]+` (open) or `[!thinking]-` (folded closed, in practice turns).
- `or-run` shows a Run button on each `java`, `python`, or `cpp` fence in Reading view, which opens the Code runner pane (`.obsidian/plugins/learn-live/main.js`, `addRunButtons`).
- `or-theme` gives a subject's notes the `lv-theme-<theme>` classes from `theme:` in `record.md` or the title, and the `vault-brand` snippet's ambient light.
- `or-generated` opens Home, Dashboard, `progress.md`, and `log.md` in Reading view with properties hidden, and draws the inline SVG skill tree in `progress.md`.
- `or-links` resolves full-root wikilinks such as `[[learn/subjects/vfx-binary-search/record|Record]]`.

## How to get to it (user POV)

- Open a note in Obsidian, in the vault opened as an Obsidian vault.

## Driving it with obsidian:// and screencapture

Preconditions:

- A person opens the sandbox once with "Open folder as vault" in Obsidian's vault switcher, and trusts it so community plugins (Dataview, `learn-live`) load. An `obsidian://open?path=...` URI only opens files inside a vault Obsidian already knows about.
- The terminal app has Screen Recording permission, or `screencapture` saves only the wallpaper.
- Never point Obsidian at the real vault for a verification run.

- **Open a note.** Run `open "obsidian://open?path=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$SANDBOX/learn/subjects/vfx-binary-search/plan.md")"`. Obsidian shows `plan.md` with the n1 to n2 diagram.
- **Capture.** Run `screencapture -x "$EVIDENCE/obsidian-plan.png"`. The image shows the rendered diagram and the vault name `vault-verify-...` in the title bar.
- **Headless proxies (no Obsidian).** These show well-formed input, not rendering. `$S/step.sh "$SANDBOX" figure-xml -- xmllint --noout learn/system/templates/figure.svg` exits 0, the vault's own figure rule (`diagrams.md`). `$S/step.sh "$SANDBOX" plugin-test -- node .obsidian/plugins/learn-live/test.js` loads `main.js` with `obsidian` stubbed and tests `paneTheme`, `opensInReading`, `runCode`, and `formatCode`.
- **Proof.** The PNG plus the note's source from `files/` of the step that wrote it. For a callout, take the `log.md` from a live-log step.

## Gotchas

- Rendering has never been driven. Every Obsidian command here is a recipe. It stays unreachable until a person registers and trusts the sandbox vault.
- The fixture has no figure, no code fence, and no `theme:`. To drive `or-figure`, `or-run`, or `or-theme`, add them to the sandbox copy first.
- Cleanup deletes the sandbox but Obsidian keeps it in its vault list. Remove it from the switcher by hand.
- `.obsidian/plugins/` and `.obsidian/snippets/` (including the untracked `vault-fonts`) are copied into the sandbox, so Dataview and the theme render. `workspace.json` and the plugin's `data.json` (the learner's code drafts) are not, so Obsidian opens with a default layout and the runner with default settings.
