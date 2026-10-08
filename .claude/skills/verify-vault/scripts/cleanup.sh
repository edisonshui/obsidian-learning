#!/bin/bash
# Usage: cleanup.sh <sandbox>
# Deletes the sandbox and the ~/.claude/projects transcript folder its -p turns
# created. Never touches $EVIDENCE: it checks the evidence is still there after.
source "$(dirname "$0")/lib.sh"
require_sandbox "${1:-}"

tdir="$(transcript_dir)"
rm -rf "$SANDBOX"
[ -d "$tdir" ] && rm -rf "$tdir" && echo "removed transcripts $tdir"
echo "removed sandbox $SANDBOX"

if [ -d "$EVIDENCE" ] && [ -n "$(ls -A "$EVIDENCE")" ]; then
  echo "evidence kept: $EVIDENCE"
  ls "$EVIDENCE"
else
  echo "evidence dir $EVIDENCE is empty or missing (nothing was driven?)"
fi
