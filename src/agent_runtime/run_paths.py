"""Explicit run storage roots without granting writes to another checkout."""
from pathlib import Path
import subprocess


def resolve_run_output(output: Path, *, repository_root: Path, run_root: Path | None = None) -> Path:
    repository_root = repository_root.resolve()
    if run_root is not None and not Path(run_root).is_absolute():
        raise ValueError("run_root must be an absolute path")
    root = repository_root if run_root is None else Path(run_root).resolve()
    # Preserve the original CLI's cwd-relative behavior unless storage was
    # explicitly relocated. Configuration callers supply repository paths.
    target = Path(output).resolve() if run_root is None else (root / output).resolve()
    if not target.is_relative_to(root):
        raise ValueError("run output escapes its configured root (default: own worktree)")
    # Resolve symlinks before checking both registered worktrees and independent
    # checkouts. A broad root such as /root never authorizes a sibling worktree.
    listed = subprocess.check_output(["git", "worktree", "list", "--porcelain"],
                                     cwd=repository_root, text=True)
    other_trees = [Path(line[9:]).resolve() for line in listed.splitlines()
                   if line.startswith("worktree ") and Path(line[9:]).resolve() != repository_root]
    if any(target.is_relative_to(tree) for tree in other_trees):
        raise ValueError("run output must not be inside another worktree")
    for parent in (target, *target.parents):
        if (parent / ".git").exists() and parent != repository_root:
            raise ValueError("run output must not be inside another worktree or repository")
    return target
