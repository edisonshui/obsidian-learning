# Moving the app to this theme

Until 27 Oct 2026, Flash's renderer ran the Vault v0.1 and v0.2 "Holo light" theme, with Bricolage Grotesque and Atkinson Hyperlegible. On that date it moved to this theme by the steps below. Read this file when you port code from an older branch, not when you design a screen.

## Steps

1. Copy [tokens.css](tokens.css) over `app/renderer/tokens.css`. Copy `figtree.woff2` and `geist-mono.woff2` from `.scratch/flash-brand/fonts/` into `app/renderer/fonts/`, and point the `@font-face` rules at them.
2. Rename each old token in `styles.css` and `app.js` by the table below. Delete every rule that uses a token marked "gone".
3. Replace the raw hex values in the code with tokens: 11 in `styles.css` and 43 in `app.js`, counted on 26 Oct 2026. Recount them with `grep -o '#[0-9A-Fa-f]\{6\}'`. The Settings theme thumbnails are among them.
4. Rebuild each screen from [components.md](components.md) and [screens.md](screens.md), then run the checklist in [SKILL.md](SKILL.md) on each one, in light and night.

The work is done when `grep` finds no old token name and no raw hex in `app/renderer/`, and every screen passes the checklist.

## Old token to new token

| Old token | New token |
|---|---|
| `--color-paper` | `--color-bg` |
| `--color-paper-2` | `--color-side` |
| `--color-raised` | `--color-selected` |
| `--color-surface`, `--color-line`, `--color-line-strong`, `--color-ink`, `--color-ink-2`, `--color-ink-3`, `--color-green`, `--color-green-soft`, `--color-gold`, `--color-untaught` | Same name, new value |
| `--color-indigo` | `--color-action` |
| `--color-indigo-soft` | `--color-action-soft` |
| `--color-ember` | `--color-amber` |
| `--color-ember-text` | `--color-amber-text` |
| `--color-ember-soft` | `--color-amber-soft` |
| `--color-gold-deep` | `--color-gold-ink` on a gold fill. Gold is never text. |
| `--color-gold-soft` | Gone |
| `--coin-*`, `--foil-*` | Gone. Discs and seals are flat (components.md, Skill discs and Badges). |
| `--holo-*`, `--glow-*`, `--duration-holo` | Gone. The only washes are `--subject-wash` on the recommended card and the subject card. |
| `--font-display` | `--font-sans` (Figtree 700) |
| `--font-sans` | `--font-sans`, now Figtree |
| `--font-mono` | `--font-mono`, now Geist Mono |
| `--rail-desktop` | Gone. The rail folds into the sidebar. |
| `--sidebar` | `--sidebar` (240px) |
| `--right-panel` | `--plan-panel` (290px) |
| `--reading-max` | `--reading-max` (660px) |
| `--radius-card-desktop`, `--radius-input-desktop`, `--radius-option`, `--radius-button`, `--radius-tile` | `--radius-card`, `--radius-input`, `--radius-option`, `--radius-pill`, `--radius-input` |
| `--button-height-desktop`, `--row-height-desktop` | `--button-height`, `--row-height` |
| `--duration-fast`, `--duration-base`, `--duration-proof`, `--ease-out` | Same names, new values |
| `--heat-0` to `--heat-4` | No token yet. See the gaps below. |
| Phone tokens (`*-phone`, `--margin-phone`, `--gutter-phone`, `--touch-min-phone`) | Gone. This guideline is desktop only. |

## Gaps the guideline does not cover

- The Dashboard heatmap. The old theme had five green steps. Since 27 Oct 2026 the app mixes `--color-green` into `--color-track` at four strengths, marked as a judgment call in `styles.css`. Ask Edison before changing it.
- The skill map was always graphite, even in light mode. The new skill map sits on the white panel with the dot grid (guideline page 6). That page does not draw nodes and edges at full size, so lay them out from screens.md and mark the screen as a judgment call.
