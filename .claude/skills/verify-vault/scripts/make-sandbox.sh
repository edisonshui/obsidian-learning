#!/bin/bash
# Usage: make-sandbox.sh [--open-note]
# Copies the vault's system (no learner data, no .git, no .env) into a fresh
# /tmp directory, installs the synthetic fixture subject, and commits a git
# baseline so /learn-end's `git status --porcelain` step has something to read.
# --open-note also adds an open s02 session note dated today (for /learn-end).
# Prints SANDBOX= and EVIDENCE= lines; `eval "$(make-sandbox.sh)"` sets both.
source "$(dirname "$0")/lib.sh"

open_note=0
[ "${1:-}" = "--open-note" ] && open_note=1

run_id="$(date +%Y%m%d-%H%M%S)"
sandbox="$(cd "$(mktemp -d "/tmp/vault-verify-$run_id.XXXX")" && pwd -P)"

# Learner data is excluded rather than copied and deleted, so it never lands in /tmp.
rsync -a \
  --exclude '/.git' --exclude '/.env' --exclude '.DS_Store' --exclude '__pycache__' \
  --exclude '/learn/subjects/' --exclude '/learn/me/' --exclude '/learn/reviews/' \
  --exclude '/learn/Home.md' --exclude '/learn/Dashboard.md' \
  --exclude '/learn/.codex-runtime/' --exclude '/learn/.mc-runtime/' \
  --exclude '/Claude outputs/' --exclude '/.scratch/' \
  --exclude '/.claude/obsidian-live/' --exclude '/.claude/jev/' \
  --exclude '/.claude/worktrees/' --exclude '/.claude/verify-runs/' \
  --exclude '/.claude/skills/verify-vault/' \
  --exclude '/.obsidian/workspace.json' \
  "$VAULT/" "$sandbox/"

mkdir -p "$sandbox/learn/subjects" "$sandbox/learn/me" "$sandbox/learn/reviews"
cp -R "$SKILL_DIR/fixtures/subjects/." "$sandbox/learn/subjects/"
cp "$SKILL_DIR/fixtures/me/preferences.md" "$sandbox/learn/me/preferences.md"

if [ "$open_note" = 1 ]; then
  today="$(date +%Y-%m-%d)"
  start="$(date -v-20M +%H:%M)"
  sed -e "s/{{DATE}}/$today/g" -e "s/{{START}}/$start/g" \
    "$SKILL_DIR/fixtures/open-note/s02.md.tmpl" \
    > "$sandbox/learn/subjects/vfx-binary-search/sessions/$today-s02.md"
  # /learn-resume would have bumped these when it opened s02.
  sed -i '' -e "s/^sessions: 1$/sessions: 2/" -e "s/^last_session: .*/last_session: \"$today\"/" \
    "$sandbox/learn/subjects/vfx-binary-search/record.md"
fi

printf 'run_id=%s\nreal_vault=%s\nopen_note=%s\n' "$run_id" "$VAULT" "$open_note" > "$sandbox/.verify-sandbox"

git -C "$sandbox" init -q
git -C "$sandbox" add -A
git -C "$sandbox" -c user.name=verify-vault -c user.email=verify@localhost commit -qm "verify-vault baseline"

mkdir -p "$EVIDENCE_ROOT/$run_id"
echo "SANDBOX=$sandbox"
echo "EVIDENCE=$EVIDENCE_ROOT/$run_id"
