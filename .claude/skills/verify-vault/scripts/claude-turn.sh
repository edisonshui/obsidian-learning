#!/bin/bash
# Usage: claude-turn.sh <sandbox> <step-name> "<prompt>" [<session-id-to-resume>]
# One headless turn of Claude Code in the sandbox, through step.sh, so the
# file diff and copies land beside the stream. Uses the vault's own permission
# rules (--permission-mode default): an `ask` rule is a denial under -p, which
# is the case /learn-end must report honestly.
# Env: MODEL (optional --model), BUDGET (default 5, --max-budget-usd).
# Adds to the step's evidence: session-id.txt, result.md, denials.json,
# hooks.jsonl (hook events), transcript.jsonl (the persisted conversation).
# Prints the session id last, for the next turn's resume argument.
source "$(dirname "$0")/lib.sh"
require_sandbox "${1:-}"; name="${2:?step name}"; prompt="${3:?prompt}"; resume="${4:-}"

if [ -n "$resume" ]; then sid="$resume"; session=(--resume "$sid")
else sid="$(uuidgen | tr 'A-Z' 'a-z')"; session=(--session-id "$sid"); fi

args=(claude -p "$prompt" "${session[@]}" --output-format stream-json --verbose
      --include-hook-events --permission-mode default --max-budget-usd "${BUDGET:-5}")
[ -n "${MODEL:-}" ] && args+=(--model "$MODEL")
# A fresh /tmp folder is an untrusted workspace, and Claude Code ignores a
# project's permissions.allow there (stderr says so). Pass the same list as
# --allowedTools so the sandbox gets the vault's real allow rules. The `ask`
# rules still apply on their own. This avoids writing trust into ~/.claude.json.
while IFS= read -r rule; do args+=(--allowedTools "$rule"); done \
  < <(jq -r '.permissions.allow[]?' "$SANDBOX/.claude/settings.json")

set +e
"$SKILL_DIR/scripts/step.sh" "$SANDBOX" "$name" -- "${args[@]}"
code=$?
set -e

out="$EVIDENCE/$name"
echo "$sid" > "$out/session-id.txt"
stream="$out/stdout.txt"
jq -r 'select(.type=="result") | .result // empty' "$stream" > "$out/result.md" 2>/dev/null || true
jq -c 'select(.type=="result") | .permission_denials // []' "$stream" > "$out/denials.json" 2>/dev/null || true
jq -c 'select(.type=="system" and (.subtype|tostring|test("hook")))' "$stream" > "$out/hooks.jsonl" 2>/dev/null || true
transcript="$(transcript_dir)/$sid.jsonl"
[ -f "$transcript" ] && cp "$transcript" "$out/transcript.jsonl" || echo "no transcript at $transcript" >&2

echo "result: $(head -c 300 "$out/result.md")"
echo "denials: $(cat "$out/denials.json")"
echo "$sid"
exit "$code"
