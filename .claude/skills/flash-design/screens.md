# Flash screens

This file gives each screen's layout and its one hard rule. Every screen sits in the [window](components.md#window): the sidebar, the white panel, and on Session the plan panel. The guideline draws Home and Session (pages 11 and 12). The other screens are not drawn yet. Lay them out from the patterns below, and mark each one as a judgment call in your report until Edison has seen it.

`paintX()` names the function in `app/renderer/app.js` that draws the screen today.

## Home (`paintHome`)

Content column, 900px, centered in the panel:

1. The greeting in `--type-greeting`, with the weekday and date under it in caption type.
2. Four [count tiles](components.md#home-parts): to repair, deadlines this week, reviews due, remembered in the last 7 days. Each number comes from `learn-status.py --json`.
3. Two columns. The recommended action card (subject wash, discs, Resume) on the left. This week on the right: one row per deadline in the next 7 days, today's in bold.
4. Subjects: up to three cards with progress bars, and "View all", which opens the Dashboard.
5. The one-line composer, docked at the bottom. Typing a subject's name there starts or resumes that subject.

Hard rule: Resume is the only filled button and the recommended card holds the only wash. The tiles stay at `--tile-tint`.

## Session (`paintSession`, `paintLog`, `paintPlan`)

The thread runs at 660px, centered, under the [header islands](components.md#header-islands). The [composer](components.md#composer) docks at the bottom. The [plan panel](components.md#plan-panel) sits on the right, and the right island's panel button hides it. The terminal still runs the tutor. It opens in a drawer from the Terminal button and never shows by default.

- The composer is always live. With no tutor running, Enter starts the tutor with the resume command and sends the message once the terminal has been quiet for 1.5s.
- A `/learn-*` command in the log reads as a centered caption ("Session saved · 17:56"), not as a message bubble.
- The thread renders `log.md`: tutor text, your bubbles, questions as cards, and the step list. Thinking folds into the first step ("Thinking · 14s"). Each record write the tutor makes becomes a "✓" step. The hook does not log record writes yet. Until it does, show only Thinking.
- The status line in the right island says what was saved and when.
- The model and effort in the composer come from the same source as the terminal's status bar.

Hard rule: never move what the learner is reading. A streaming reply grows in place. A new message never jumps the scroll position when the learner has scrolled up. Show a "New messages" pill instead.

## Skill map (`paintMap`) and Progress (`paintProgress`)

The second and third tabs in the left island. Not drawn in the guideline; built 27 Oct 2026 and reviewed in three rounds.

- Both maps sit in a dark sky: a viewport inset 60px from the panel's top and 8px from its sides, with `data-theme="night"` on the viewport only. The header islands, search box, and map controls keep the app theme. Edison asked for the dark look from his constellation reference (27 Oct 2026). Setting `mapTheme: "light"` in the config turns the sky off.
- Skill map: the subject's nodes as cards on the dot grid, with the subject's glow behind them. A node with a can-do line is a full card; a not-yet node is a compact pill. Edges end at each node's measured height. It opens at the fit view, or on the up-next node when the fit is too small to read.
- Progress: the content column, with the can-do statements, then counts, then the session list, newest first.

Hard rule: a disc's state comes from the record, and nothing else on these screens uses status color.

## All skills (`paintSystem`)

A constellation, from Edison's reference (27 Oct 2026). Each subject is a petal of its skills reaching out from the center, foundations nearest the middle, in a soft glow of its subject color. Domains keep sectors sized by how much they hold, with at least 11 degrees per petal; subjects keep their orbits (active, paused, done). Subject titles hold about 12px on screen at any zoom; skill names appear past zoom 1.05. Titles that would overlap wait for hover or zoom, active subjects first. A search box finds a skill and flies to it. Clicking a petal flies the camera into it, then opens its Skill map; coming back restores the view.

Hard rule: subject color stays in the glows. Stars carry status color only, and lines and labels stay neutral.

## Dashboard (`paintDashboard`)

The Dashboard uses the content column, with every subject as a row: tile, title, progress bar, last session, and deadline chip. Under the rows, "Recently earned" with [badges](components.md#badges) stacked by day. Not drawn yet beyond the badge card on guideline page 10.

Hard rule: no locked or greyed badges, and no "3 more to go".

## Setup and errors (`paintSetup`, `paintError`)

First run and an empty vault use the [empty state](components.md#empty-state-menu-and-switcher): a drawn icon, a title, one line on what will appear, and one action. An error names what failed and the one step that fixes it.

Hard rule: one action per state.

## Settings

Settings opens as a sheet over the current screen on the scrim, with a float shadow (`openSettings`). It has sections of label, control, and a one-line caption: appearance, your name, tutor, rewards, and the vault folder. Flash cannot switch rewards itself. The rewards row says to ask the tutor, who edits the `rewards:` line in `learn/me/preferences.md`.

Hard rule: every setting takes effect at once, without a save button. The appearance thumbnails draw from the tokens, never from raw hex.
