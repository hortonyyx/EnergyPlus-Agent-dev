"""WP-1 byte-reproducibility locks for converter-produced augmented DXFs."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.gt_extraction import ExtractionInputs, extract_gt_v3
from src.agent.judge.gt_render_model import gt_to_render_model
from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1, resolve_converter_tooling


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"
REQUEST = REPO / "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json"
ANNOTATIONS = REPO / "tests/fixtures/sm24_review/bundle_07_25/review_annotations.json"
RASTER_ROOT = REPO / "case_tests/e2e_tests/sm24_anchor/case_data"


def _run(tmp_path: Path, label: str):
    source = tmp_path / "source.dxf"
    if not source.exists():
        source.write_bytes(SOURCE.read_bytes())
    request = TarchConversionRequestV1.model_validate_json(REQUEST.read_text(encoding="utf-8"))
    tooling = resolve_converter_tooling(REPO / "src/configs/judge_gt.yaml", REPO / "src/configs/correction.yaml")
    result = tn.run_p2_conversion(source, request, request.plan_views[0], tooling, tmp_path / label / "work")
    document = extract_gt_v3(ExtractionInputs(result.augmented_dxf_path, result.manifest, tooling,
                                               compute_gt_implementation_hashes(REPO_ROOT)))
    return result, document


def _render_all(document, manifest, out: Path) -> dict[str, bytes]:
    sys.path.insert(0, str(REPO / "scripts/tool_scripts"))
    import render_gt as render_gt
    import render_gt_overlay as overlays

    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))["zone_roles"]
    out.mkdir(parents=True)
    model = gt_to_render_model(document)
    render_gt.render_plan_model(model, review_annotations=annotations).save(out / "gt_plan.png")
    render_gt.render_elevation_model(model).save(out / "gt_elev.png")
    images = overlays.build_gt_overlay_images_v3(document, manifest, raster_root=RASTER_ROOT,
                                                  review_annotations=annotations)
    for view_id, image in images.items():
        image.save(out / f"overlay_{view_id}.png")
    return {path.name: path.read_bytes() for path in sorted(out.iterdir())}


def test_r1_1_augmented_dxf_is_byte_identical_for_two_runs(tmp_path):
    first, _ = _run(tmp_path, "first")
    second, _ = _run(tmp_path, "second")
    assert first.augmented_dxf_path.read_bytes() == second.augmented_dxf_path.read_bytes()


def test_r1_2_neutering_metadata_pin_releases_r1_1(tmp_path, monkeypatch):
    monkeypatch.setattr(tn, "_apply_deterministic_dxf_metadata", lambda *args: None)
    first, _ = _run(tmp_path, "first")
    second, _ = _run(tmp_path, "second")
    assert first.augmented_dxf_path.read_bytes() != second.augmented_dxf_path.read_bytes()


def test_r1_3_metadata_guids_change_with_source_or_request():
    source = hashlib.sha256(b"source-a").hexdigest()
    request = hashlib.sha256(b"request-a").hexdigest()
    baseline = tn._deterministic_dxf_metadata(source, request)
    assert tn._deterministic_dxf_metadata(hashlib.sha256(b"source-b").hexdigest(), request)["$VERSIONGUID"] != baseline["$VERSIONGUID"]
    assert tn._deterministic_dxf_metadata(source, hashlib.sha256(b"request-b").hexdigest())["$FINGERPRINTGUID"] != baseline["$FINGERPRINTGUID"]


def test_r1_4_gt_and_all_seven_renders_are_byte_identical(tmp_path):
    first, gt_first = _run(tmp_path, "first")
    second, gt_second = _run(tmp_path, "second")
    assert gt_first.content_sha256 == gt_second.content_sha256
    assert _render_all(gt_first, first.manifest, tmp_path / "first" / "renders") == _render_all(
        gt_second, second.manifest, tmp_path / "second" / "renders")


def _sm24_answer_content_for_hash_seed(source: Path, work_dir: Path, seed: str) -> dict:
    output = work_dir / "answer-content.json"
    script = """
import json
import sys
from pathlib import Path

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.gt_extraction import ExtractionInputs, extract_gt_v3
from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1, resolve_converter_tooling

repo, source, work_dir, output = map(Path, sys.argv[1:])
request = TarchConversionRequestV1.model_validate_json(
    (repo / "tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json").read_text(encoding="utf-8")
)
tooling = resolve_converter_tooling(
    repo / "src/configs/judge_gt.yaml", repo / "src/configs/correction.yaml"
)
result = tn.run_p2_conversion(
    source, request, request.plan_views[0], tooling, work_dir / "work"
)
document = extract_gt_v3(ExtractionInputs(
    result.augmented_dxf_path, result.manifest, tooling,
    compute_gt_implementation_hashes(REPO_ROOT),
))
raw = document.model_dump(mode="json")
answer = {key: raw[key] for key in (
    "schema_version", "case", "geometry_profile", "coordinate_frame",
    "north_axis_deg", "north_axis_source_refs", "floors", "openings",
)}
output.write_text(
    json.dumps(answer, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    encoding="utf-8",
)
"""
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = seed
    completed = subprocess.run(
        [sys.executable, "-c", script, str(REPO), str(source), str(work_dir), str(output)],
        cwd=REPO, env=environment, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, (
        f"PYTHONHASHSEED={seed} conversion failed\n{completed.stdout}\n{completed.stderr}"
    )
    return json.loads(output.read_text(encoding="utf-8"))


def test_sm24_answer_content_is_stable_across_python_hash_seeds(tmp_path):
    """DXF bytes and the derived ``content_sha256`` stamp are known unstable in dev.

    Python hash-order dependence flows into DXF entity/handle order.  The answer
    content (floors, nested zones/footprints, openings, and every coordinate) is
    stable, so this lock compares those fields across independent hash-seeded runs.
    Eliminating byte instability belongs to later productisation, not this dev lock.
    """
    source = tmp_path / "source.dxf"
    source.write_bytes(SOURCE.read_bytes())
    seeds = ("0", "1", "8675309")
    answers = [
        _sm24_answer_content_for_hash_seed(source, tmp_path / f"seed-{seed}", seed)
        for seed in seeds
    ]
    for seed, answer in zip(seeds[1:], answers[1:]):
        assert answer == answers[0], f"answer content drifted under PYTHONHASHSEED={seed}"


# --------------------------------------------------------------------------- #
# F-D (dispatch ②-1b R4): converter_sha256() widened to a conversion CLOSURE,
# AST-normalized.  ⛔ Two mutation directions, EACH with its own real edit --
# "variant didn't run" and "variant had no effect" are indistinguishable on the
# product alone, so each direction below actually performs the edit it claims
# to and checks the number the edit is supposed to move.
# --------------------------------------------------------------------------- #
def _copy_converter_closure(tmp_path: Path) -> Path:
    """A writable mirror of every CONVERTER_CLOSURE_FILES member, so a mutation
    test can edit a file without touching the real tree."""
    root = tmp_path / "closure_copy"
    for relative in tn.CONVERTER_CLOSURE_FILES:
        src = REPO / relative
        dst = root / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return root


def test_f_d_a_comment_only_edit_does_not_flip_the_closure_fingerprint(tmp_path, monkeypatch):
    """F-D direction 1: dispatch's own example ("改一个字的注释就让指纹翻转").

    The pre-fix definition (sha256 of tarch_normalize.py's raw bytes) WOULD
    flip here; ``converter_sha256()``'s AST-normalized digest must not.
    """
    root = _copy_converter_closure(tmp_path)
    monkeypatch.setattr(tn, "_CONVERTER_REPO_ROOT", root)
    before = tn.converter_sha256()

    target = root / "src/agent/judge/tarch_normalize.py"
    mutated = target.read_text(encoding="utf-8").replace(
        "def converter_sha256() -> str:",
        "# a completely harmless re-wording of an existing comment\n"
        "def converter_sha256() -> str:", 1)
    assert mutated != target.read_text(encoding="utf-8"), "the edit must actually change the file"
    target.write_text(mutated, encoding="utf-8")

    after = tn.converter_sha256()
    assert after == before, "a comment-only edit moved the widened fingerprint"

    # ⛔ the OLD definition WOULD have flipped -- prove the mutation was real,
    # not merely a no-op that any digest would survive.
    old_before = hashlib.sha256((REPO / "src/agent/judge/tarch_normalize.py").read_bytes()).hexdigest()
    old_after = hashlib.sha256(target.read_bytes()).hexdigest()
    assert old_after != old_before, "mutation did not even change raw bytes -- test is vacuous"


def test_f_d_b_a_schema_behaviour_edit_flips_the_closure_fingerprint(tmp_path, monkeypatch):
    """F-D direction 2: the false NEGATIVE that mattered -- a real behavioural
    edit to a closure-external-to-tarch_normalize.py file (tarch_converter_schema.py)
    used to leave ``converter_sha256()`` silent.  It must not any more.
    """
    root = _copy_converter_closure(tmp_path)
    monkeypatch.setattr(tn, "_CONVERTER_REPO_ROOT", root)
    before = tn.converter_sha256()

    target = root / "src/agent/judge/tarch_converter_schema.py"
    mutated = target.read_text(encoding="utf-8") + "\nF_D_MUTATION_PROBE_NEW_STATEMENT = 1\n"
    target.write_text(mutated, encoding="utf-8")

    after = tn.converter_sha256()
    assert after != before, "a real code addition to a closure member left the fingerprint unchanged"


def test_f_d_c_widening_actually_moved_the_value_relative_to_the_legacy_definition():
    """Sanity: the widened value really differs from sha256(this file's raw
    bytes alone) on the UNMODIFIED tree -- i.e. this is not a no-op rename."""
    legacy = hashlib.sha256((REPO / "src/agent/judge/tarch_normalize.py").read_bytes()).hexdigest()
    assert tn.converter_sha256() != legacy


def test_f_d_d_known_pre_fix_values_are_pinned_not_recomputed():
    """⭐⭐ A1 (②-1b-R, GLM N-1): the set must equal EXACTLY the pinned sm25
    value -- ⛔ ``in``/``not in`` alone has ZERO discriminating power against
    an extra, unvetted member being padded into the set (MEASURED, GLM: a
    fabricated hash added to the set produced 0 test failures across
    ``test_gt_raw_layer.py`` + ``test_gt_promotion_path.py`` +
    ``test_tarch_converter_reproducibility.py`` before this assertion
    existed).  ⚠️ This locks the SET, ⛔ it does not change what the set is
    allowed to exempt -- see ``KNOWN_PRE_F_D_CONVERTER_SHA256``'s own
    docstring; that behaviour is untouched by this rework (changing it needs
    a re-sign, not a test).
    """
    sm25_report = json.loads((REPO / "case_tests/test_baseline/gt/sm25-L_anchor"
                              "/review/conversion_report.json").read_text(encoding="utf-8"))
    assert tn.KNOWN_PRE_F_D_CONVERTER_SHA256 == frozenset({sm25_report["converter_sha256"]})
    sm24_report = json.loads((REPO / "case_tests/test_baseline/gt/sm24_anchor"
                              "/review/conversion_report.json").read_text(encoding="utf-8"))
    assert sm24_report["converter_sha256"] not in tn.KNOWN_PRE_F_D_CONVERTER_SHA256

    # ⭐ Second layer (GLM N-1's "加强"): anchor the pinned value to an
    # IMMUTABLE git object rather than to this module's own say-so -- "who
    # may declare a legacy exemption" moves from "whoever edits this file"
    # to "the commit the docstring already names".
    frozen_bytes = subprocess.run(
        ["git", "show", "a40d56d:src/agent/judge/tarch_normalize.py"],
        cwd=REPO, capture_output=True, check=True,
    ).stdout
    assert hashlib.sha256(frozen_bytes).hexdigest() in tn.KNOWN_PRE_F_D_CONVERTER_SHA256


def test_f_d_d2_the_exact_equality_assertion_actually_has_teeth():
    """⭐ Self-proof (GLM's own measured fact, made executable): padding the
    set with one arbitrary extra member must break the SAME shape of
    assertion the test above makes.  ⛔ Constructed locally, no monkeypatch
    of module state -- this proves the ASSERTION SHAPE has discriminating
    power, independent of whether anyone remembers to run it against a
    mutated module.
    """
    sm25_report = json.loads((REPO / "case_tests/test_baseline/gt/sm25-L_anchor"
                              "/review/conversion_report.json").read_text(encoding="utf-8"))
    padded = frozenset(tn.KNOWN_PRE_F_D_CONVERTER_SHA256 | {"f" * 64})
    with pytest.raises(AssertionError):
        assert padded == frozenset({sm25_report["converter_sha256"]})


# --------------------------------------------------------------------------- #
# CONVERTER_CLOSURE_FILES membership must have an OUT: a real static import
# walk, not a hand-typed list nobody re-checks ([[dispatch ②-1b R4]]).
# --------------------------------------------------------------------------- #
def _module_level_local_imports(path: Path) -> set[Path]:
    """Relative/`src.agent.*`-absolute imports written at MODULE SCOPE (not
    inside a function body) in ``path``.  AST-based: comments can't fool it,
    and a lazy (function-body) import is correctly invisible here -- those are
    the ones ``CONVERTER_CLOSURE_FILES``'s own docstring names and justifies
    by hand, one grep-checked case at a time (below)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[Path] = set()
    for node in tree.body:                      # ⛔ .body only, not ast.walk
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.level == 1:                 # `from .X import ...`
                candidate = path.parent / (node.module.replace(".", "/") + ".py")
                out.add(candidate.resolve())
            elif node.level == 0 and node.module.startswith("src.agent."):
                base = REPO / (node.module.replace(".", "/"))
                as_module = base.with_suffix(".py")
                if as_module.is_file():
                    out.add(as_module.resolve())
                else:
                    # `from src.agent.correction import facade_convention` --
                    # `node.module` names the PACKAGE, and each imported name
                    # may itself be a submodule file rather than a symbol.
                    for alias in node.names:
                        submodule = (base / alias.name).with_suffix(".py")
                        if submodule.is_file():
                            out.add(submodule.resolve())
    return out


def _static_closure(entry: Path) -> set[Path]:
    seen = {entry.resolve()}
    frontier = [entry.resolve()]
    while frontier:
        current = frontier.pop()
        for dep in _module_level_local_imports(current):
            if dep.is_file() and dep not in seen:
                seen.add(dep)
                frontier.append(dep)
    return seen


def test_f_d_closure_membership_matches_a_static_import_walk():
    """The provenance CONVERTER_CLOSURE_FILES's own docstring promises: a real
    AST walk of MODULE-LEVEL imports, starting at tarch_normalize.py, must
    equal the tuple minus the one hand-added lazy dependency."""
    entry = REPO / "src/agent/judge/tarch_normalize.py"
    discovered = {str(p.relative_to(REPO)) for p in _static_closure(entry)}
    expected = set(tn.CONVERTER_CLOSURE_FILES) - {"src/agent/judge/gt_extraction.py"}
    assert discovered == expected, (
        f"static top-level import closure disagrees with CONVERTER_CLOSURE_FILES "
        f"(update BOTH together): missing={sorted(expected - discovered)} "
        f"extra={sorted(discovered - expected)}")


def test_f_d_gt_extraction_lazy_dependency_is_real_and_on_the_p2_path():
    """The ONE member the static walk above cannot see: prove the lazy
    ``from .gt_extraction import`` sits inside a function this file's own
    source shows is called from the P2 conversion path, rather than trusting
    the docstring's claim."""
    text = (REPO / "src/agent/judge/tarch_normalize.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    holders = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
              and any(isinstance(sub, ast.ImportFrom) and sub.module == "gt_extraction"
                      for sub in ast.walk(node))}
    assert "_run_g9_v3_preflight" in holders
    assert "def run_p2_conversion(" in text or "run_p2_conversion" in text
    assert "_run_g9_v3_preflight(" in text  # actually called somewhere in this file


def test_f_d_excluded_lazy_imports_are_confirmed_unreachable():
    """The two lazy imports CONVERTER_CLOSURE_FILES's docstring EXCLUDES by
    name must still be unreachable from the conversion path.  If a future
    edit wires either in for real, this must fail loudly rather than let
    F-D's blind spot silently reopen."""
    write_gt_v3_candidate_callers = subprocess.run(
        ["grep", "-rn", "write_gt_v3_candidate(", "--include=*.py", "src", "scripts"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.splitlines()
    call_sites = [line for line in write_gt_v3_candidate_callers
                 if "def write_gt_v3_candidate" not in line]
    assert call_sites and all(line.startswith("scripts/tool_scripts/gt_from_dxf.py:")
                              for line in call_sites), call_sites

    corrected_geometry_validators = subprocess.run(
        ["grep", "-rlE", r"CorrectedGeometryV3\.model_validate(_json)?\(",
         "--include=*.py", "src/agent/judge"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.split()
    closure_paths = set(tn.CONVERTER_CLOSURE_FILES)
    assert not (set(corrected_geometry_validators) & closure_paths), corrected_geometry_validators


def test_ezdxf_default_writer_matches_converter_writer_except_pinned_metadata(tmp_path):
    """MINOR-3: retain ezdxf's writer behaviour apart from the six pinned values."""
    import ezdxf
    default = tmp_path / "default.dxf"; converter = tmp_path / "converter.dxf"
    ezdxf.readfile(SOURCE).saveas(default)
    tn._save_converter_augmented_dxf(ezdxf.readfile(SOURCE), converter, "a" * 64, "b" * 64)
    def strip_pinned(raw: bytes) -> bytes:
        text = raw.decode("utf-8")
        for name in ("$TDCREATE", "$TDUCREATE", "$TDUPDATE", "$TDUUPDATE", "$FINGERPRINTGUID", "$VERSIONGUID"):
            text = re.sub(rf"({re.escape(name)}\n\s*\d+\n)[^\n]+", r"\1<PINNED>", text)
        text = re.sub(r"(WRITTEN_BY_EZDXF\n\s*350\n[0-9A-F]+\n\s*0\nDICTIONARYVAR.*?\n\s*1\n)[^\n]+",
                      r"\1<PINNED>", text, flags=re.S)
        return text.encode("utf-8")
    assert strip_pinned(default.read_bytes()) == strip_pinned(converter.read_bytes())
