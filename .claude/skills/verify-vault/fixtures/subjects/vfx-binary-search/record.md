---
subject: "vfx-binary-search"
title: "VFX Fixture: Binary search"
status: active
started: "2026-10-01"
last_session: "2026-10-01"
sessions: 1
next: /learn-resume vfx-binary-search, decay-check n1, then teach n2.
deadline:
goal_met:
---

# VFX Fixture: Binary search — learner record

SYNTHETIC FIXTURE for verify-vault. Not a real learner's record.

## Goal

"Trace binary search on a sorted array and say why it needs the array sorted."

## Success criteria

1. Trace lo/hi/mid on an 8-element sorted array to a found index.
2. Explain why an unsorted array breaks the halving step.
3. Name the worst-case comparison count for n = 8.

## Strands

| Strand | Floor (demonstrated) | Ceiling (not yet) | Last probed |
| --- | --- | --- | --- |
| Array indexing | 0-based index lookup | none found | 2026-10-01 |
| Halving | split a range in half | integer mid with odd length | 2026-10-01 |

## Nodes

| Node | Status | Last checked | Evidence (latest) |
| --- | --- | --- | --- |
| n1 | checked | 2026-10-01 | 2026-10-01 s01: traced mid for [0,7] → 3 → correct |
| n2 | planned |  |  |

## Misconceptions

## Evidence log

- 2026-10-01 s01: mid of lo=0, hi=7? → 3 → correct → n1 checked

## What works for this learner in this subject

## Sessions

- [[learn/subjects/vfx-binary-search/sessions/2026-10-01-s01|s01 2026-10-01]] — n1
