#!/usr/bin/env python3
"""Hash every file a drive could touch, or diff two such snapshots.

  snapshot.py take <sandbox> <out.json>
  snapshot.py diff <before.json> <after.json>

Covers learn/, "Claude outputs/" and .claude/obsidian-live/ in the sandbox.
The diff is the ground truth a skill's own "changed/unchanged" claims are
checked against, so it reads the disk, never git (learn/subjects is gitignored).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOTS = ("learn", "Claude outputs", ".claude/obsidian-live")


def take(sandbox, out):
    sandbox = Path(sandbox)
    files = {}
    for root in ROOTS:
        base = sandbox / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                files[str(path.relative_to(sandbox))] = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(out).write_text(json.dumps(files, indent=1, sort_keys=True))


def diff(before, after):
    old, new = json.loads(Path(before).read_text()), json.loads(Path(after).read_text())
    for path in sorted(set(old) | set(new)):
        if path not in old:
            print("added    " + path)
        elif path not in new:
            print("removed  " + path)
        elif old[path] != new[path]:
            print("changed  " + path)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "take":
        take(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
