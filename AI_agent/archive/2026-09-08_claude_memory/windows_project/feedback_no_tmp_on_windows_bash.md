---
name: No /tmp on this Windows bash
description: The user's bash shell on Windows has no /tmp directory; scratch files must go under the workspace.
type: feedback
originSessionId: dabf94b5-507c-47f4-86a1-aa4a8568d6f3
---
Do not write scratch/intermediate files to `/tmp/...` from Bash. The path does not exist in the user's Windows bash environment and `cat /tmp/...` returns "No such file or directory".

**Why:** Observed 2026-04-27 while building scratch JSON for `update_surfaces_batch` — `python ... > /tmp/upd.json` silently produced an empty file and the next `cat` failed.

**How to apply:** For any throwaway file the LLM generates (helper JSON, intermediate dumps, scratch scripts), put it under the case's `output/` directory or another workspace path. Never assume POSIX scratch directories exist.
