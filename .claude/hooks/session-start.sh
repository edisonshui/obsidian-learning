#!/bin/bash
# SessionStart hook: prints the date and every subject's resume summary so the
# tutor starts each session already knowing where each learning project stands.
# Output goes into Claude's context as plain text.

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SUBJECTS="$ROOT/learn/subjects"

# Refresh the generated dashboard and progress notes so Obsidian is current the
# moment a session opens. Never allowed to fail the hook: the views are derived,
# so a stale dashboard is a cosmetic problem and a blocked session start is not.
python3 "$ROOT/.claude/hooks/learn-status.py" --quiet >/dev/null 2>&1 || true

echo "## Learning vault — session start"
echo "Now: $(date '+%A %Y-%m-%d %H:%M %Z')"
echo

# Any session note still missing an `end:` is reported before anything else. The
# staleness rule in learn/system/records.md tells /learn-resume to finalize a
# stale note before opening the next one, but a skipped finalize left no trace in
# any file -- so the rule was unenforceable and s03 sat open for twenty-five
# hours. This is that trace. Read-only and never allowed to fail the hook: a
# missing warning is worse than no session, but a blocked session start is worse
# than both.
OPEN_NOTES="$(python3 "$ROOT/.claude/hooks/learn-status.py" --open-notes 2>/dev/null || true)"
if [ -n "$OPEN_NOTES" ]; then
  echo "> [!] Unfinished session notes"
  echo "$OPEN_NOTES" | sed 's/^/- /'
  echo
  echo "Finalize a stale or cut-off note (learn/system/records.md, *Closing an open note*)"
  echo "before teaching anything new. A live break inside the bound is reopened, not finalized."
  echo
fi

if [ ! -d "$SUBJECTS" ] || [ -z "$(ls -A "$SUBJECTS" 2>/dev/null)" ]; then
  echo "No subjects yet. Offer /learn-start <subject>."
  exit 0
fi

for dir in "$SUBJECTS"/*/; do
  slug="$(basename "$dir")"
  record="$dir/record.md"
  resume="$dir/resume.md"
  echo "### $slug"
  if [ -f "$record" ]; then
    # Pull the frontmatter index fields from record.md.
    awk '/^---$/{c++; next} c==1 && /^(title|status|last_session|sessions|next):/{print "- " $0}' "$record"
  fi
  if [ -f "$resume" ]; then
    echo
    echo "resume.md:"
    # Print the body of resume.md (skip frontmatter), capped so a runaway file can't flood context.
    awk '/^---$/{c++; next} c>=2{print}' "$resume" | head -40
  else
    echo "- no resume.md yet"
  fi
  echo
done

echo "Ask which subject to /learn-resume or /learn-start before teaching anything."
