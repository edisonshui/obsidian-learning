# Obsidian rendering

Edison reads the session note and the live `log.md` in Obsidian, which renders mermaid diagrams, callouts (`> [!info]`, `> [!quote]`), LaTeX, and Dataview queries in `learn/Queries.md`. This surface is optional. Use it only when a change affects how a note looks, not what it says.

## Sub-features

- `or-mermaid` renders a `flowchart TD` block in `plan.md` and session notes as a diagram.
- `or-callout` renders the live log's `> [!info] Live note` and `> [!quote] You · HH:MM` blocks as callouts.
- `or-links` resolves full-root wikilinks such as `[[learn/subjects/vfx-binary-search/record|Record]]`.

## How to get to it (user POV)

- Open a note in Obsidian, in the vault opened as an Obsidian vault.

## Driving it with obsidian:// and screencapture

Preconditions:

- The sandbox must be opened as its own Obsidian vault first. An `obsidian://open?path=...` URI only opens files inside a vault Obsidian already knows about. Registering a new vault takes a click in Obsidian's vault switcher ("Open folder as vault"), so a person does this step once per sandbox.
- Never point Obsidian at the real vault for a verification run.

- **Open a note.** Run `open "obsidian://open?path=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$SANDBOX/learn/subjects/vfx-binary-search/plan.md")"`. Obsidian shows `plan.md` with the n1 to n2 diagram.
- **Capture.** Run `screencapture -x "$EVIDENCE/obsidian-plan.png"`. The image shows the rendered diagram and the vault name `vault-verify-...` in the title bar.
- **Proof.** The PNG plus the note's source from `files/` of the step that wrote it.

## Gotchas

- Not yet driven. Every command here is a recipe, not a proven path.
- `screencapture` needs Screen Recording permission for the terminal app. Without it the PNG is the desktop wallpaper.
- Cleanup deletes the sandbox but Obsidian keeps it in its vault list. Remove it from the switcher by hand.
- `.obsidian/plugins/` is copied into the sandbox, so Dataview renders. `workspace.json` is not, so Obsidian opens with a default layout.
