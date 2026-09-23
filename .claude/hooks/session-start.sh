#!/bin/bash
# Both hosts share the compact start context and retain the open-note warning.
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HOOK_DIR/session_context.py" --vault "$ROOT"
