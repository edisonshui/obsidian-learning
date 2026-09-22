---
type: learning-queries
---

# Queries

Live views built with **Dataview**, which reads the YAML frontmatter of every note in
the vault and lets you query it like a small database.

> [!info] What lives where, and why
> Dataview can only see **frontmatter** — the `key: value` block at the top of a note.
> It cannot read the rows of a Markdown table. Node statuses live in tables inside
> `record.md` and `plan.md`, so those are rendered by `.claude/hooks/learn-status.py`
> into [[learn/Dashboard|Dashboard]] and each subject's `progress.md` instead.
>
> The split is deliberate: **generate what you already know, query what you want to ask.**
> The dashboard always shows the same thing, so it is generated once and cannot drift.
> The questions on this page change as you think of new ones, which is what a query
> language is actually good for.

## Subjects

```dataview
TABLE WITHOUT ID
  link(file.folder + "/progress", title) AS Subject,
  status AS Status,
  sessions AS Sessions,
  last_session AS "Last session",
  next AS "Next step"
FROM "learn/subjects"
WHERE file.name = "record"
SORT last_session DESC
```

## Every session, newest first

```dataview
TABLE
  subject AS Subject,
  date AS Date,
  start AS Start,
  end AS End,
  active_minutes AS "Active (min)",
  nodes AS Nodes
FROM "learn/subjects"
WHERE session
SORT date DESC, session DESC
```

## Time spent per subject

Active minutes only — time you stepped away is tracked separately and excluded.

```dataview
TABLE WITHOUT ID
  Subject,
  length(rows) AS Sessions,
  sum(rows.active_minutes) AS "Active minutes"
FROM "learn/subjects"
WHERE session
GROUP BY subject AS Subject
```

## Sessions that were cut off

A session note with no `end:` and no `paused:` was interrupted rather than closed.
`/learn-resume` finalizes one of these before opening a new note, so this list should
normally be empty.

```dataview
LIST
FROM "learn/subjects"
WHERE session AND !end AND !paused
```

## Adding your own

The shape is always the same: `TABLE` or `LIST`, `FROM "folder"`, `WHERE <condition>`,
`SORT <field>`. Any frontmatter key in any note is a field you can use — `status`,
`sessions`, `nodes`, `active_minutes`, `subject`, `date`. Full reference:
[Dataview docs](https://blacksmithgu.github.io/obsidian-dataview/).
