# Vault UI pieces

The app has two families of pieces. Controls are flat: pills for actions, soft rectangles for choices, and mono chips for keys and citations. Proof objects (skill discs, count tiles, the weekly streak, the heatmap, and badges) are the only pieces with a lip and a status color. Their values always come from the record, never from activity.

Token names refer to [tokens.css](tokens.css). The source is guideline pages 11 and 12.

## Controls

Every control has hover, focus, disabled, and loading states. Focus is always `--focus-ring`, a 2pt Indigo ring with a 2pt offset.

| Piece | Look | Rule |
|---|---|---|
| Ink button | Ink pill with white text, Atkinson 700 14. 44 tall on phone, 32 to 40 on desktop. | One per screen. The label names the action: Resume, Check, Reveal, or Done. |
| Secondary button | Surface pill, 1px Line strong border, Ink text | The second choice, such as "Other options". |
| Text button | Text only, in Ink 2 | Low-weight actions: Skip, Why?, and Hint. |
| Disabled button | Paper 2 fill, Ink 3 text | Any button that cannot act yet. |
| Answer option | Surface, 1px Line, radius 12. A radio circle on the left and the number key on the right in Ink 3 Mono. | The learner answers with number keys. |
| Selected option | 2px Indigo border, radio filled Indigo | Before grading. |
| Right option | 2px Green border, radio filled Green. The explanation is text directly under the option. | After grading. Wrong answers stay neutral, with no red fill. |
| Key chip | Surface, 1px Line strong border with a 2px bottom edge, radius 5, Mono 600 10.5 to 11, Ink 2 | Shows a keyboard shortcut inside hover tips, menus, and the command palette. Never printed beside a button. |
| Citation chip | Indigo soft fill, Indigo Mono text, radius 6 | Links a claim to the record line or file behind it, such as `record.md:42`. It is Indigo because it is a link. |
| Input dock | Surface pill with `--shadow-float`, floating at the bottom of the tutor column | The one floating piece in the tutor view. Text buttons sit below it: Hint, Check me, Break, and End. Their keys are in their hover tips. The placeholder is one word: "Reply". |
| Sidebar row | 28 tall, 13pt text, count or date right-aligned | The selected row is Surface on Paper 2, never Indigo. |
| Card | Surface, 1px Line, radius 20 on phone and 10 on desktop | Cards rest on the page, so they get no shadow. |
| Popover, menu, and command palette | Surface with `--shadow-float` | Only floating pieces get a shadow. |

These CSS rules show how the table maps to tokens:

```css
.button-ink {
  height: 40px;
  padding: 0 20px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--color-ink);
  color: #fff;
  font: 700 14px var(--font-sans);
  transition: background var(--duration-fast) var(--ease-out);
}
.button-ink:focus-visible { box-shadow: var(--focus-ring); }
.button-ink:disabled { background: var(--color-paper-2); color: var(--color-ink-3); }

.key-chip {
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border: 1px solid var(--color-line-strong);
  border-bottom-width: 2px;
  border-radius: 5px;
  background: var(--color-surface);
  color: var(--color-ink-2);
  font: 600 10.5px var(--font-mono);
}

.option { border: 1px solid var(--color-line); border-radius: var(--radius-option); background: var(--color-surface); }
.option[aria-checked="true"] { border: 2px solid var(--color-indigo); }
.option.is-right { border: 2px solid var(--color-green); }
```

This SwiftUI snippet is the same Ink button. It assumes a `Theme` type built from the tokens. Read each font's PostScript name from the bundled font file instead of guessing it.

```swift
Button("Resume") { resume() }
    .font(Theme.ui(weight: .bold))   // Atkinson, 15pt on phone, scales with Dynamic Type
    .foregroundStyle(.white)
    .frame(maxWidth: .infinity, minHeight: 44)
    .background(Theme.ink, in: Capsule())
```

## Proof objects

### Skill discs

A disc is 44pt on phone and 36 to 56 on desktop. Its icon is a drawn stroke, never an emoji.

| State | Look | Meaning |
|---|---|---|
| Solid | Gold coin. The `--coin-gold` gradient, a 3pt lip in `--coin-gold-lip`, a `0 6 12` drop shadow in Gold deep at 22%, and an Ink star. | Passed again later. |
| Checked | Green coin. The `--coin-green` gradient, a 3pt lip in `--coin-green-lip`, a drop shadow in Green at 22%, and a white check. | Passed a check. "You can now." |
| Worth a refresh | Keeps its color and adds a small white refresh badge at the top right | Decayed. The app never takes progress away. |
| Up next | Surface fill, a 3pt Ember ring, and a 6pt Ember soft halo | The one node to do next. One per subject. |
| Learning | Surface fill and a 3pt Ink 3 ring | Introduced, not yet checked. |
| Not yet | Transparent, with a 2pt dashed Untaught outline | Not taught. No padlock, because nothing is locked. |

The gradient and lip values come from the source HTML, not the token table. They look the same in night mode.

When a node becomes Solid, the disc fills from the bottom and the star settles in `--duration-proof` (320ms) with `--ease-out`. This fill is the app's one signature motion. With reduced motion on, the fill becomes a cross-fade.

### Count tiles

A count tile is Surface with a 1px Line strong border, radius 14, and a 2pt Line strong lip below. The number is Bricolage 700 28 in its status color: Skills solid in Gold deep, Checks passed in Green, Week streak in Ember text, and Best streak in Ink. The label is Atkinson 11 to 12 in Ink 2. Counts never go down.

### Weekly streak

The weekly streak is a row on Surface. It shows the count in Ember text, the words "weeks of reviews", and one Ember disc with a check for each week. The streak counts weeks, not days. A week with nothing due shows a dashed disc and does not break the streak. The streak forgives one missed week in four. The row does not explain that rule.

### Heatmap

Each column is a week and each square is a day. Squares are 9pt with radius 2 and 3pt gaps. A square's color shows checks passed (`--heat-0` to `--heat-4`), never minutes spent.

### Badges

A badge is a 64pt octagon with a conic foil sheen and a white highlight over its top left. An Ink stroke icon sits in the middle. Under the octagon, the name is in Atkinson 700 and the date is in Mono, written out ("22 Sep 2026").

| Badge | Foil | Icon |
|---|---|---|
| Solid: <skill> | Gold, `--foil-gold` | Star |
| Recovered: <skill> | Mint, `--foil-mint` | Refresh |
| Goal met: <subject> | Peach through lilac to mint, `--foil-goal` | Flag |

Foil appears only on earned badges. When the learner turns rewards off in Settings, the app hides every badge.
