#!/bin/bash
# Usage: doctor.sh <sandbox>
# Read-only. Answers "is this sandbox safe and worth driving?" Exit 0 = yes.
source "$(dirname "$0")/lib.sh"
require_sandbox "${1:-}"

fail=0
ok()  { echo "ok    $*"; }
bad() { echo "FAIL  $*"; fail=1; }
warn(){ echo "warn  $*"; }

ok "sandbox $SANDBOX (run $RUN_ID)"

others="$(find "$SANDBOX/learn/subjects" -mindepth 1 -maxdepth 1 -type d ! -name 'vfx-*' -exec basename {} \;)"
[ -z "$others" ] && ok "learn/subjects holds only vfx-* fixtures" || bad "non-fixture subjects present: $others"
grep -q "SYNTHETIC FIXTURE" "$SANDBOX/learn/me/preferences.md" && ok "preferences.md is the fixture" || bad "preferences.md is not the fixture"
[ -z "$(ls -A "$SANDBOX/learn/reviews")" ] && ok "learn/reviews empty" || warn "learn/reviews not empty (left by an earlier drive?)"
[ ! -e "$SANDBOX/.env" ] && ok "no .env (Jev stays offline)" || bad ".env present: Jev would make network calls"
[ -z "${TYPESAFE_API_KEY:-}" ] && ok "TYPESAFE_API_KEY unset" || bad "TYPESAFE_API_KEY is set in this shell"
grep -q 'CLAUDE_PROJECT_DIR' "$SANDBOX/.claude/settings.json" && ok "hooks resolve via CLAUDE_PROJECT_DIR" || bad "settings.json hooks not project-relative"
git -C "$SANDBOX" rev-parse -q --verify HEAD >/dev/null && ok "git baseline present" || bad "no git baseline"

if out="$(python3 "$SANDBOX/.claude/hooks/learn-status.py" --vault "$SANDBOX" --next 2>&1)"; then
  ok "learn-status --next: $(echo "$out" | head -1)"
else
  bad "learn-status --next failed: $out"
fi

command -v claude >/dev/null && ok "claude $(claude --version 2>/dev/null)" || warn "claude not on PATH: surface 2 unavailable"
git -C "$VAULT" check-ignore -q "$EVIDENCE_ROOT/x" && ok "evidence root is gitignored" || bad "evidence root $EVIDENCE_ROOT is NOT gitignored"
grep -q "$VAULT" "$SANDBOX/.claude/settings.json" && warn "statusLine in settings.json points at the real vault (interactive only; -p never runs it)"

exit $fail
