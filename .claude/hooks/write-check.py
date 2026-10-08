#!/usr/bin/env python3
"""Prove which learning files a skill wrote, from disk, not from git.

  write-check.py snapshot <id>    hash every file under learn/ into learn/.write-check/<id>.json
  write-check.py compare <id>     re-hash and print each file that was added, changed, or removed

`/learn-end` and `/learn-review` snapshot before their first write and compare
in their verify step. git cannot do this job: learn/subjects/, learn/me/,
learn/reviews/, Home.md and Dashboard.md are all gitignored, so `git status`
never lists a single file those skills write.

Skipped: each subject's log.md and codex-log.md (hooks rewrite them while a
reply streams, so they always differ) and every dot-directory under learn/
(.mc-runtime/, .codex-runtime/, and this script's own .write-check/).
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SKIP_NAMES = {"log.md", "codex-log.md", ".DS_Store"}


def hashes(vault):
    learn = vault / "learn"
    found = {}
    for path in sorted(learn.rglob("*")):
        relative = path.relative_to(learn)
        if not path.is_file() or path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in relative.parts[:-1]):
            continue
        found[str(path.relative_to(vault))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def snapshot_path(vault, snapshot_id):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", snapshot_id):
        raise ValueError("snapshot id may use only letters, digits, '.', '_' and '-'")
    return vault / "learn/.write-check" / (snapshot_id + ".json")


def snapshot(vault, snapshot_id):
    path = snapshot_path(vault, snapshot_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    files = hashes(vault)
    path.write_text(json.dumps(files, indent=1, sort_keys=True) + "\n")
    return "snapshot %s: %d files under learn/" % (snapshot_id, len(files))


def compare(vault, snapshot_id):
    path = snapshot_path(vault, snapshot_id)
    if not path.is_file():
        raise FileNotFoundError("no snapshot %s: nothing to compare against, so no write can be proven" % snapshot_id)
    old, new = json.loads(path.read_text()), hashes(vault)
    lines = []
    for name in sorted(set(old) | set(new)):
        if name not in old:
            lines.append("added    " + name)
        elif name not in new:
            lines.append("removed  " + name)
        elif old[name] != new[name]:
            lines.append("changed  " + name)
    lines.append("no other files under learn/ changed" if lines else "no file under learn/ changed")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("snapshot", "compare"))
    parser.add_argument("id", help="e.g. oop-s05 for /learn-end, review-r03 for /learn-review")
    parser.add_argument("--vault", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        print((snapshot if args.command == "snapshot" else compare)(args.vault, args.id))
    except (ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
