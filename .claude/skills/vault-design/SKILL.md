---
name: vault-design
description: Brand rules for the Vault learning app (the native iOS and macOS tutor app built on this vault, not the Obsidian notes). Use when designing, building, restyling, or reviewing any Vault app screen or UI part, or when picking a Vault app color, font, size, texture, light, or motion.
---

# Vault app design

The Vault app is mostly near-neutral paper, white cards, and warm ink text. Every page sits in its subject's light, a soft gradient in the subject's colors that says where you are. Cards, the dock, and buttons stay solid on top of it. Status color appears only when it carries a fact from the learning record: a skill passed, the node up next, or a week of reviews. Proof of learning (skill discs, count tiles, badges) is the only thing drawn as a physical object, with a lip and a sheen. Everything else is flat.

The sources are "Vault brand guideline v0.1" (16 Oct 2026) at `.scratch/vault-brand/brand-guideline.pdf`, and "v0.2: Holo light" (18 Oct 2026) at `.scratch/vault-brand/holo-guideline.pdf`. Where they disagree, v0.2 wins; Edison approved all six of its decisions on 18 Oct 2026. The PDF is built from `brand-guideline.html` in the same folder. That file's CSS holds a few values that the PDF's token table leaves out. The PDF mockups are the visual target.

To change a color, font, size, rule, or component, use the brand-guideline skill's change flow.

Use the vault's words in designs and copy: subject, node, skill, check, review, session, record, plan, and can-do line.

## Design a screen

1. Pick the screen pattern and its shell (phone or desktop) in [screens.md](screens.md). Keep the pattern's layout and its hard rule.
2. Name the one next step. Give it the screen's only Ink button. On Home, the one next step is the recommended action. Fold every other option into a plain list or a row of chips.
3. Give the screen its one light form from [Holo light](#holo-light), or none. Then give every other color one job from the color table below. If a color is only decoration, remove it.
4. Build from the pieces in [components.md](components.md). Take every color, font, size, radius, shadow, and duration from [tokens.css](tokens.css). A raw hex value in a component is a bug.
5. Design every state. Each control needs hover, focus, disabled, and loading states. Each screen needs a light and a night version. On desktop, give every action a keyboard shortcut, and show it in the control's hover tip and the command palette. Never print a key chip beside a button.
6. Write the copy by the voice rules below.
7. Run the checklist at the end of this file. The screen is done when every line passes.

## Five principles, in priority order

When two rules conflict, follow the one higher in this list.

1. **One next step.** A screen has at most one Ink button.
2. **Proof, not points.** Gold, green, and badges come only from passed checks. The app has no XP, leagues, or confetti.
3. **Color has a job.** Each color means one thing everywhere in the app.
4. **The subject's light fills the room.** Home gets the full wash (or the bloom on phone); every other page sits in the ambient light at 40%; the progress card and a waiting check sit in a lit card. Edison chose this ("option A") on 18 Oct 2026, replacing "one light per screen".
5. **Calm where you read.** Long text (tutor replies, notes, code, math) sits on solid Surface or on the ambient light, which is soft enough for every text color to pass 4.5:1. Gold and foil stay the only warm reward colors. This replaced "Calm by default, warm when earned" on 18 Oct 2026.

## Color

[tokens.css](tokens.css) holds every value. This table holds each color's job. Page 19 of the guideline sets the night values its first table left out.

| Color | Token | Light | Night | Its one job |
|---|---|---|---|---|
| Paper | `color-paper` | #F6F5F2 | #141416 | App background |
| Paper 2 | `color-paper-2` | #EEECE7 | #0E0E10 | Sidebar, insets, neutral buttons, and disabled controls |
| Surface | `color-surface` | #FFFFFF | #1C1C1F | Cards, panels, and answer options |
| Line | `color-line` | #E4E1DA | #303035 | Hairlines and card borders. Never text. |
| Line strong | `color-line-strong` | #CFCBC2 | #46464C | Inputs, tile lips, and dividers. Never text. |
| Ink | `color-ink` | #1B1A17 | #F2F1EE | Text and the Ink button |
| Ink 2 | `color-ink-2` | #4A4741 | #B9B7B1 | Secondary text |
| Ink 3 | `color-ink-3` | #646059 | #8F8D87 | Captions and placeholders. The lightest color allowed for text. Darkened on 18 Oct 2026 so it passes on the ambient light. |
| Indigo | `color-indigo` | #4D3EE2 | #9890FF | Interaction: the selected answer, links, citations, and focus |
| Gold | `color-gold` | #F6CF5F | #F6CF5F | Solid skills. For gold text, use `color-gold-deep` (#8A600A). |
| Green | `color-green` | #17865F | #3FB98A | Checked skills, the right answer, and the heatmap |
| Ember | `color-ember` | #E5603A | #F07A52 | The Up next node, the streak, and the deadline line on Home that says why a node is up next. For ember text, use `color-ember-text` (#C2482A). |
| Untaught | `color-untaught` | #D9D5CC | #3A3A40 | The dashed outline of a Not yet node |

Follow these color rules:

- Use status colors (gold, green, and ember) only on skill discs, count tiles, the heatmap, and badges, and only where the record put them. Home has two exceptions, both from the page 7 mockup and approved by Edison on 16 Oct 2026: the deadline line on the recommended action ("Deadline in 4 days") is Ember text, and the streak row's icon is Ember.
- Show a subject color only as an 8px dot, an icon tint, a 6% wash behind a subject header, or its light (see [Holo light](#holo-light)). The All skills map is the one exception, approved by Edison on 17 Oct 2026: there the domain color also runs along its branches and constellation lines and glows behind each subject. Subject colors measure 3.3 to 4.0:1 on graphite, so they never color text. Each subject takes the color of its `theme:` in `record.md`: Code #4A6FA5, Math #267C88, Circuits #8E4FA0, Literature #B5505F, Design #66762E, or Calm #7A746A. Subject colors are the same in night mode.
- Build hierarchy from size and weight. Keep body text in Ink, Ink 2, or Ink 3, because color carries meaning.
- Leave a wrong answer neutral and make "Not yet" grey. The app has no red.
- Aim for about 60% paper, 22% surface, 12% ink, 4% status color, and 2% indigo. If a screen looks colorful, look for a status color outside its job.

## Typography

The app bundles three open-source faces, so every platform renders the same text. It never uses the system font.

| Face | Weights | Job |
|---|---|---|
| Bricolage Grotesque | 600, 700 | Titles, section heads, the focus timer, and count tiles |
| Atkinson Hyperlegible Next | 400, 600, 700 | Everything you read and tap: body text, labels, buttons, and chat |
| Atkinson Hyperlegible Mono | 400, 600 | Code, the Code runner, key chips, and citations |

| Style | Face | Phone | Desktop | Use |
|---|---|---|---|---|
| Timer | Bricolage 700, tracking -3% | 72/72 | 120/120 | Focus mode only |
| Title | Bricolage 700, tracking -2% | 30/34 | 36/40 | Screen title and Home greeting |
| Heading | Bricolage 600 | 22/28 | 22/28 | Card and section heads |
| Number | Bricolage 700 | 28/30 | 28/30 | Count tiles |
| Subhead | Atkinson 700 | 17/24 | 15/22 | Question text and list titles |
| Reading | Atkinson 400 | 17/27 | 16/26 | Tutor replies and notes |
| UI | Atkinson 400 or 600 | 15/22 | 13/18 | Rows, buttons, and inputs |
| Caption | Atkinson 400 | 12/16 | 11.5/16 | Dates, hints, and metadata |
| Code | Mono 400 | 14/22 | 13/20 | Code blocks and the runner |
| Key | Mono 600 | 11 | 10.5 | Shortcut chips |

Sizes are size over line height. Follow these type rules:

- Read sizes as points on Apple platforms and pixels elsewhere. Line heights are fixed values, so stacked text lands on the 4-point grid. Dynamic Type scales each style from its base size.
- Use sentence case everywhere. Put no all-caps label above a heading.
- Set numbers that change (timers, counts, and dates) in tabular figures.
- Keep reading text 60 to 72 characters wide. On desktop, cap chat and notes at 720px.
- Use at most two weights in one region of a screen.
- Use Bricolage only for headings and numbers. Use Mono only for real code and keys.

## Spacing and shape

| | Phone (pt) | Desktop (px) |
|---|---|---|
| Grid | 8pt rhythm, 4 columns, 20 margins, 12 gutters | 4px grid |
| Row height | 44 | 28 |
| Card radius | 20 | 10 |
| Row radius | 16 | not set |
| Input radius | 14 | 8 |
| Answer option radius | 12 | 12 |
| Button | Pill, 44 tall | Pill, 32 to 40 tall |
| Touch target | 44 minimum | not set |

[tokens.css](tokens.css) has the full list, including the desktop sidebar and panel widths. When no token fits, ask Edison for a value.

## Textures

Most of the app is flat paper and hairlines. A texture marks something special, so each texture has exactly one place. A texture anywhere else is a bug.

| Texture | Look | Its one place |
|---|---|---|
| Gold wash | A vertical fade from Gold soft to Paper | The top of the Map, and the cover of a goal-met moment |
| Coin and lip | A highlight at the top left, a 2 to 3pt darker lip below, and a soft drop shadow | Skill discs and count tiles |
| Foil | A conic sheen in peach, gold, lilac, and mint, inside an octagon | Earned badges |
| Dot grid | A graphite background with dots 14 to 18pt apart | The skill map, the All skills map, and the lesson graph |
| Organic shapes | Large soft blobs in Ink, Ember soft (called blush here), and Indigo soft | Focus mode |
| Subject glow | A radial fade of the subject color from `--glow-subject` to clear, reaching `--glow-reach` past the subject; in Ink at `--glow-you` behind You | The All skills map |

Resting things, such as cards and panels, get a 1px Line border and no shadow. Floating things (the input dock, the command palette, menus, and popovers) get `shadow-float`. Proof objects get the lip. The only blur is the scrim behind the command palette. The only gradients are the four Holo light forms, the subject glow on the All skills map, the gold wash, and the proof objects.

### Holo light

The gradient is light. Each subject's light is its `--holo-<theme>` token (`code`, `math`, `circuits`, `literature`, `design`, `calm`), from `theme:` in its `record.md`. A screen with no subject uses `--holo-calm`. At night the tokens switch to the Aurora glows and drop to 38%, so white text on a lit card still measures 6.4:1 or more.

| Form | Look | Its one place |
|---|---|---|
| Bloom | A round blur, `--holo-bloom-size` wide (200 on phone), blurred `--holo-bloom-blur`, turning once every `--duration-holo` | Home on phone, above the greeting |
| Wash | The light across the whole content area at `--holo-wash-strength`, fading to Paper at the bottom | Home on desktop |
| Ambient | The light behind the whole page at `--holo-ambient-strength`, fading to `--holo-ambient-floor` Paper at the bottom so the color reaches the input dock | Every screen except Home, the maps, and Focus: tutor chat, notes, plan, record, Dashboard, progress, Review, Settings. Replaced the corner glow on 18 Oct 2026. |
| Lit card | A Surface card with the light blurred inside it, radius `--holo-card-radius-*`, Ink text only | The subject's progress card, above the count tiles, and the frame around a check question |

Follow these light rules:

- Put only Ink text on a lit card. Ink measures 8.7:1 or more on every light stop. Ink 2 measures 4.6:1, too close to the floor.
- Keep captions on the ambient light in Ink 3 or darker. Ink 3 (#646059) measures 4.56:1 where the light is strongest.
- Let the input dock's backdrop show the light through it: a fade to 55% Paper, never a solid strip.
- Keep the light off buttons and proof objects. The Ink button stays the one solid thing; discs, tiles, and badges keep their lip and foil.
- Keep foil badges crisp and octagonal, so they never read as the light, which is always soft or inside a card.
- Stop the bloom's turn with Reduce motion on. It is the app's only ambient motion.
- Use solid Surface for cards on the light. Frosted glass is still only for the command palette scrim.

Hover and press take 140ms, and panels, sheets, and the cross-fade between screens take 220ms, all on `ease-out`. The app's one signature motion is a disc that becomes Solid, in 320ms. [components.md](components.md#skill-discs) describes it. With Reduce motion on, nothing animates.

Never move what the learner is looking at. Edison asked for this on 17 Oct 2026 ("buttery"):

- A refresh that changes nothing repaints nothing. A refresh that changes something keeps the scroll position.
- A control repaints only its own region. A tab switch in the right panel leaves the chat alone.
- A new screen opens at the top. Coming back to a screen returns to where the learner was.
- Load what the learner is about to open: hovering a subject starts loading its session.
- Load heavy pieces (the math and diagram renderers) only on the screen that needs them.

## Icons

The app's icons are the 20 drawn in the guideline, saved as SVG files in [icons/](icons/): book, cards, chart, check, chev, code, down, flag, gear, home, map, note, play, refresh, search, send, star, stop, week, and x. Each is on a 24pt grid with a 1.8 stroke, round ends, and no fill, and takes its color from the text around it. Edison picked this set over Lucide, Tabler, and Iconoir on 16 Oct 2026.

To show an icon, use the drawn one when it fits. When the set has no icon for the job, follow these steps:

1. Copy Lucide's version from github.com/lucide-icons/lucide, and set its `stroke-width` to 1.8.
2. Simplify it to match the drawn set: open shapes and little detail inside.
3. Save it in [icons/](icons/) with a one-word name. Add Lucide's ISC license to `icons/LUCIDE-LICENSE` if that file does not exist yet, because the license requires its notice in every copy.
4. In your report, name the new icon so Edison can check it.

## Voice

App copy reads like an entry in the learning record: a fact, a date, or the next step.

Text is there only when the learner needs it. Each line carries a fact they need or names an action. Cut any caption that explains how to read the screen ("Each column is a week"), any label that repeats what is already on screen, and any count or date nobody acts on. A hover tip can hold the detail instead. The Home greeting ("Good afternoon, Edison") stays, because it is the one line there to make the app feel personal. Edison set this rule on 17 Oct 2026.

Keep the tutor's internal words out of app copy: diagnosis, probe, strand, gate, and Jev. Say what happens instead. "A few more questions to find where you start", not "Finish the diagnosis, then build the plan".

| Do | Don't |
|---|---|
| "Solid: encapsulation, 22 Sep 2026" | "Fantastic!" or any other praise word |
| "You can now trace a constructor call." | Exclamation marks |
| "Worth a refresh: shadowing." | "You forgot 3 skills" |
| "4 weeks of reviews." | "Don't lose your streak" |
| "Nothing due this week. Next review Sunday." | XP, levels, leagues, or ranks |
| A button that names its action: Resume, Check, Reveal, or Done | "OK" or "Continue" when a more exact verb fits |
| "Could not save the session note. Retry, or copy it to the clipboard." | An error that names the problem and gives no fix |

Write dates out (16 Oct 2026), and show times on the learner's clock. When a skill decays, say what to do next and never what was lost.

## Design do and don't

| Do | Don't |
|---|---|
| One Ink button, with every other option folded into a list | A second filled button on the screen |
| Indigo on the selected answer, links, citations, and focus | Indigo on a button, a heading, or a selected sidebar row |
| Turn the right answer green and put the explanation under it | Fill a wrong answer red |
| A 1px Line border on a resting card | A drop shadow on a card |
| A dashed outline for an untaught node | A padlock on anything |
| Wrap a long skill name to two lines | Cut a skill name with an ellipsis |
| Color the heatmap by checks passed | Count minutes or activity as progress |
| Drawn icons with a 1.8 stroke | Emoji, mascots, confetti, or sparkles |

## Gaps in the guideline

Versions 0.1 and 0.2 do not settle the items below. When a design needs one, either ask Edison or pick a value. If you pick, say so in your report.

1. The guideline names two open decisions: the app's name and wordmark, and the Windows and Linux shell.

## Checklist

Run this checklist on every new or changed screen. Report each line as pass or fail.

- [ ] The screen has at most one Ink button.
- [ ] Indigo appears only on selection, links, citations, and focus.
- [ ] Gold, green, and ember appear only where the record put them.
- [ ] The screen uses the Holo light form its row in the light table names, and every text color on it passes 4.5:1.
- [ ] Text on a lit card is Ink.
- [ ] Subject color appears only as a dot, an icon tint, a 6% wash, or its light (or, on All skills, a branch, line, or glow), and never on a button or text.
- [ ] Each texture is in its one place, and only floating things have a shadow.
- [ ] Text uses only the three faces, the type scale, sentence case, and tabular numbers.
- [ ] Every value is a token with a night value, or the report names the gap.
- [ ] Every control has hover, focus, disabled, and loading states.
- [ ] On desktop, every action has a keyboard shortcut, shown in its hover tip and the command palette.
- [ ] Every piece of text carries a needed fact or names an action. Nothing explains how to read the screen or repeats what is already on it.
- [ ] The copy passes the voice rules: no praise words, no exclamation marks, and no loss language.
- [ ] The screen respects reduced motion, larger text, and high contrast.
