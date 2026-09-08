"""isolation.py 中被删除的 prescan 相关片段（取自 0cfa289）。

这不是可运行模块，是把散在 isolation.py 里的三处 prescan 逻辑集中留档，
以免恢复时需要在 1600 行文件里翻找。恢复方式见同目录 RESTORE.md。
"""

# —— 1) build 时把 orchestrator 预生成的候选拷进 staging ——
def _copy_prescan(run_dir: Path | None, staging_root: Path, manifest: WorkspaceManifest) -> None:
    if run_dir is None:
        return
    src = run_dir / "0_reading" / "cv_evidence"
    if not src.exists():
        return
    # Layout parity with staging-direct generation (--out-dir <staging>/prescan):
    # prescan/cv_evidence/<stem>/prescan/... either way.
    dest_root = staging_root / "prescan" / "cv_evidence"
    for path in sorted(src.glob("*/prescan/**/*")):
        if path.is_file():
            _assert_source_allowed(path)
            _copy_file(path, dest_root / path.relative_to(src), "prescan", manifest)


# —— 2) 拷贝白名单里唯一放行 run_*/ 子树的例外 ——
def _is_run_prescan_path(rel: Path) -> bool:
    """Only run-dir subtree readable by the builder: orchestrator-produced
    prescan candidates at run_*/0_reading/cv_evidence/<stem>/prescan/**."""
    parts = rel.parts
    for i, part in enumerate(parts[:-1]):
        if part.startswith("run_"):
            tail = parts[i + 1 :]
            return (
                len(tail) >= 5
                and tail[0] == "0_reading"
                and tail[1] == "cv_evidence"
                and tail[3] == "prescan"
            )
    return False


# —— 3) kickoff 里介绍预扫产物的段落（原在 _write_kickoff 内）——
    if (staging_root / "prescan").exists():
        text += (
            "Deterministic prescan candidates are provided under "
            "prescan/cv_evidence/<image_stem>/prescan/: `candidates.json` (all "
            "candidates); kind views `structural_candidates.json`, "
            "`cc_box_candidates.json`, and `tick_candidates.json`; overlays "
            "`combined_overlay.png` (structural-only), `cc_box_overlay.png`, "
            "`tick_overlay.png`, and `all_candidates_overlay.png` (all "
            "candidates). Nothing is dropped: every candidate remains reachable "
            "through `candidates.json` and the kind views; consume them per the "
            "cv_toolbox discipline.\n"
        )
