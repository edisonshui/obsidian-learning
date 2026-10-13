#!/bin/bash
# Usage: step.sh <sandbox> <step-name> [--stdin <file>] -- <command> [args...]
# Runs one command inside the sandbox (cwd = sandbox, CLAUDE_PROJECT_DIR = sandbox,
# no Jev key) and records, under $EVIDENCE/<step-name>/:
#   cmd.txt  stdout.txt  stderr.txt  exit.txt  before.json  after.json
#   diff.txt   added/changed/removed files, read from disk
#   files/     a copy of every added or changed file, so proof survives cleanup
# Exits with the command's exit code.
source "$(dirname "$0")/lib.sh"
require_sandbox "${1:-}"; name="${2:?step name}"; shift 2

stdin=/dev/null
if [ "${1:-}" = "--stdin" ]; then stdin="$2"; shift 2; fi
[ "${1:-}" = "--" ] && shift
[ $# -gt 0 ] || die "no command given"

out="$EVIDENCE/$name"
[ -e "$out" ] && die "evidence for step '$name' already exists: $out (pick a new name)"
mkdir -p "$out/files"
printf '%q ' "$@" > "$out/cmd.txt"; echo >> "$out/cmd.txt"

python3 "$SKILL_DIR/scripts/snapshot.py" take "$SANDBOX" "$out/before.json"
set +e
(cd "$SANDBOX" && env -u TYPESAFE_API_KEY CLAUDE_PROJECT_DIR="$SANDBOX" "$@") \
  < "$stdin" > "$out/stdout.txt" 2> "$out/stderr.txt"
code=$?
set -e
echo "$code" > "$out/exit.txt"
python3 "$SKILL_DIR/scripts/snapshot.py" take "$SANDBOX" "$out/after.json"
python3 "$SKILL_DIR/scripts/snapshot.py" diff "$out/before.json" "$out/after.json" > "$out/diff.txt"

while read -r kind path; do
  [ "$kind" = removed ] && continue
  mkdir -p "$out/files/$(dirname "$path")"
  cp "$SANDBOX/$path" "$out/files/$path"
done < <(sed 's/^\([a-z]*\) *\(.*\)$/\1 \2/' "$out/diff.txt")

echo "step $name: exit $code, $(wc -l < "$out/diff.txt" | tr -d ' ') file(s) touched -> $out"
exit "$code"
