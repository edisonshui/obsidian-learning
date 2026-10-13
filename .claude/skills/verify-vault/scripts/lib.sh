# Sourced by the other verify-vault scripts. Not run directly.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT="$(cd "$SKILL_DIR/../../.." && pwd)"          # the real vault: read from, never driven
EVIDENCE_ROOT="$VAULT/.claude/verify-runs"          # gitignored; survives cleanup
SANDBOX_PREFIX="/private/tmp/vault-verify-"         # mktemp under /tmp resolves here on macOS

die() { echo "verify-vault: $*" >&2; exit 1; }

# Refuse anything that is not a sandbox this skill made. Every script that
# writes or deletes calls this first, so a typo can never aim at the real vault.
require_sandbox() {
  local dir="${1:-}"
  [ -n "$dir" ] || die "no sandbox path given"
  [ -d "$dir" ] || die "sandbox not found: $dir"
  dir="$(cd "$dir" && pwd -P)"
  case "$dir" in "$SANDBOX_PREFIX"*) ;; *) die "refusing: $dir is not under $SANDBOX_PREFIX" ;; esac
  [ -f "$dir/.verify-sandbox" ] || die "refusing: $dir has no .verify-sandbox marker"
  SANDBOX="$dir"
  RUN_ID="$(sed -n 's/^run_id=//p' "$SANDBOX/.verify-sandbox")"
  EVIDENCE="$EVIDENCE_ROOT/$RUN_ID"
  mkdir -p "$EVIDENCE"
}

# Claude Code keeps -p transcripts under ~/.claude/projects/<cwd with every
# non-alphanumeric character replaced by '-'>.
transcript_dir() {
  echo "$HOME/.claude/projects/$(printf '%s' "$SANDBOX" | sed 's/[^A-Za-z0-9]/-/g')"
}
