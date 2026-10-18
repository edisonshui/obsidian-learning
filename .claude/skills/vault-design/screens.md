# Vault screens and layouts

Each screen copies one idea from a Mobbin reference that Edison picked. It copies the idea only, never the reference's colors, fonts, or styling. Token names refer to [tokens.css](tokens.css). The source is guideline pages 7 to 9 and 13 to 15, and the mockups on those pages are the visual target.

## Phone shell (iOS)

The phone app is one column with 20pt margins on an 8pt rhythm, using a 4-column grid with 12pt gutters. It has four tabs: Today, Map, Review, and Progress. The selected tab is bold Ink, and the other tabs are Ink 3. Cards have radius 20, rows have radius 16, and touch targets are at least 44pt.

## Desktop shell (macOS first, Windows and Linux later)

The desktop app puts Dropbox Dash's shell around Fibery's workspace, on a 4px grid.

- The rail is 48 wide and the sidebar is 230 to 280 wide. Both are Paper 2. The sidebar lists subjects. A button beside the window controls folds it, and so does Cmd \.
- The tutor column sits in the middle. It is fluid, and its text is capped at 720.
- The input dock floats at the bottom of the tutor column. It has the only soft shadow on the screen.
- The right panel is 320 to 420 wide, with the tabs Note, Code, and Cards. A button at the right end of the title bar folds it. The Code tab copies Grok's layout: Run at the top right and a console drawer below.
- Rows are 28 tall, cards have radius 10, inputs have radius 8, and buttons are pills.
- Windows, menus, and sheets are native. The app's colors, fonts, and components go inside them.
- On Windows and Linux, use Ctrl where macOS uses Cmd, and show the right key.

## Screen patterns

| Screen | Reference | Layout | Hard rule |
|---|---|---|---|
| Home, phone | Uxcel | The title ("Good evening"), then the recommended action as the only large card. The card holds the reason in Ember text ("Deadline in 4 days"), a heading, one line of next step, a progress bar, and the Ink button. Below the card are a small review-streak row and an "Other options" list with subject dots. | No second button. |
| Home, desktop | Dropbox Dash | A centered greeting, the recommended action as the dock card, and the other options as chips under it (Review 12 due, Repair 2, Start a subject, More). Nothing else: no date line, no recents, no streak row. The Dashboard holds those. | One large card, as on phone. |
| Map, phone | Liven | The path grows upward from the bottom. Each label sits beside its disc and wraps to two lines. Chapter dividers name each strand. The gold wash is at the top. | Never cut a skill name. One Up next node per subject. |
| Skill map, desktop | Higgsfield | Always graphite with the dot grid, even in light mode, so the map reads as a separate place. Each node card states its skill as the can-do line from `plan.md`. Cards sit where the vault's skill-tree layout puts them (`layered()` and `bk()` in `learn-status.py`), prerequisites below. 1.2px lines join the cards. The map opens centred on the Up next node. The learner can pan and zoom. | No padlocks. |
| All skills, desktop | Edison's merge, 17 Oct 2026: WRITER's branches, Stardust's constellations, Orbit's rings, Tolan's centre | You at the centre of the graphite dot grid. Branches in each domain's color grow from You to a domain chip, then to each subject. Subjects sit on three orbits: active, paused, done. Each subject is a constellation: its skills are stars in their disc colors joined by their prerequisites, ringed by one status dot per skill, with a glow of the domain color behind it. Dotted arcs join subjects whose skills overlap; hover lights them skill by skill, and a click opens the subject's skill map. ⌘3 and the rail's map icon open it. | Overlaps come only from the records. Until `plan.md` stores concepts, they are inferred. Labels stay Ink. |
| Tutor chat | Devin, Fibery | An answer column with citation chips that point to the record line or file. Code for the learner to try goes to the runner. The log folds into one section per tutor heading, and only the latest section is open. | Every claim based on the record gets a citation chip. |
| Check | Turo | The outline is on one side: done nodes green, the current node with an Ink outline, and older nodes grey. One question card is on the other side ("Question 3 of 4"). Any code or diagram the question needs is inside the question card. The explanation is text under the answer, every time. | One button, Next, at the lower right. |
| Spaced review | Headway | One centered card with the subject dot on top, the prompt "Answer in your head, then reveal", and a Reveal button. Then "Do you remember this?" with Not yet in neutral grey and Yes in Ink. Space reveals, 1 answers Not yet, and 2 answers Yes. | "Not yet" is never red. |
| Progress | Vocabulary, Cursor | The weekly streak row, count tiles, and the heatmap. A subject's heatmap spans its own weeks, 6 to 16 columns. | Counts come from the record, never from time spent. |
| Command palette | Magnific | Recents first, then actions with their shortcuts, then a footer of keys. Every /learn command is in the palette. | The scrim behind the palette is the app's only blur. |
| Focus timer | Toggl Track | A large Bricolage timer, the current node, one stop button, and organic shapes in Ink, Ember soft (blush), and Indigo soft. The 45-minute break shows as a quiet line ("break at 45:00"). | Organic shapes appear only here. No countdown alarm. |
| Settings | Cal.com | The learner picks a theme (System, Light, or Night) from preview thumbnails, and the selected one has an Ink ring. The rewards switch for badges and streak lines is here. | None beyond the main rules. |
| End of session | Mindvalley | "Session 3 saved" with the subject and minutes, "Earned today" badges with dates, "You can now" with the can-do line, "Up next", and one Done button. | Reads like a record entry, with no celebration. |

## Example: phone Home in tokens

The card padding, the progress bar height, and the caption weight below come from reading the page 7 mockup. The guideline does not state them, and the 700 caption weight differs from the 400 in the type scale.

```
paper background, 20pt margins
  Title        Bricolage 700 30/34, Ink        "Good evening"
  Card         surface, 1px line, radius 20, 16pt padding
    Caption    Atkinson 700 12/16, Ember text  "Deadline in 4 days"
    Heading    Bricolage 600 22/28, Ink        "Lagrange multipliers"
    UI         Atkinson 400 15/22, Ink 2       "Finish the diagnosis, then build the plan."
    Progress   4pt bar, Ink on Paper 2
    Button     Ink button, full width, 44 tall "Resume"
  Row          surface, radius 16, Ember icon  "4-week review streak" / "Next review due Sunday"
  Subhead      Atkinson 700 17/24              "Other options"
  List rows    44 tall, subject dot, chevron   "Repair: Pointers"
tab bar        surface, 1px line on top
```
