"""Post-generation partition comparison after a caller-declared translation.

The original proposal/source are never edited. A translated proposal is rebuilt
as a source BIM in a temporary directory, then both raw and translated frames
are compared with the same verified GT. No GT-based fitting is performed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.judge.gt import load_gt_document
from src.agent.judge.partition_evidence import reference_partition


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def translate_proposal(original: dict, shift: tuple[float, float, float]) -> dict:
    """Translate only known proposal geometry fields; reject unhandled frames."""
    dx, dy, dz = shift
    if any(original.get(key) for key in ("enclosure_declaration", "wall_references", "wall_dimensions", "mesh_frame")):
        raise ValueError("proposal has frame-dependent fields outside this evaluation-only translation")
    proposal = copy.deepcopy(original)
    geometry = proposal["geometry"]
    if geometry.get("facade_segments"):
        raise ValueError("facade_segments fingerprints need a separate translation implementation")
    for axis, delta in (("footprint_x", dx), ("footprint_y", dy)):
        geometry[axis] = [value + delta for value in geometry[axis]]
    for floor in geometry["floors"]:
        floor["z_floor"] += dz
        if floor.get("footprint"):
            floor["footprint"]["vertices"] = [
                [point[0] + dx, point[1] + dy] for point in floor["footprint"]["vertices"]]
        for cell in floor["cells"]:
            cell["x"] = [value + dx for value in cell["x"]]
            cell["y"] = [value + dy for value in cell["y"]]
            if cell.get("polygon") is not None:
                cell["polygon"] = [[point[0] + dx, point[1] + dy] for point in cell["polygon"]]
    for window in geometry.get("windows", []):
        along_shift = dx if window["facade"] in {"North", "South"} else dy
        window["span"] = [value + along_shift for value in window["span"]]
        window["z"] = [value + dz for value in window["z"]]
        for point_key in ("p1", "p2"):
            if point_key in window:
                window[point_key] = [window[point_key][0] + dx, window[point_key][1] + dy]
    for opening in geometry.get("openings", []):
        for point_key in ("p1", "p2"):
            opening[point_key] = [opening[point_key][0] + dx, opening[point_key][1] + dy]
        opening["z"] = [value + dz for value in opening["z"]]
    return proposal


def translated_source_consistent(original: dict, shifted: dict, shift: tuple[float, float, float]) -> dict:
    def check_rows(key: str, field: str):
        old = {row["id"]: row for row in original[key]}
        new = {row["id"]: row for row in shifted[key]}
        if old.keys() != new.keys():
            return False
        for identity, row in old.items():
            before = row[field]
            after = new[identity][field]
            if len(before) != len(after):
                return False
            for a, b in zip(before, after):
                if any(abs(b[index] - (a[index] + shift[index])) > 1e-6 for index in range(len(a))):
                    return False
        return True
    return {"spaces_preserved": check_rows("spaces", "polygon"),
            "boundary_vertices_translated": check_rows("boundaries", "vertices"),
            "opening_vertices_translated": check_rows("openings", "vertices"),
            "counts_preserved": all(len(original[key]) == len(shifted[key]) for key in
                                    ("spaces", "boundaries", "openings", "connections"))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--candidate", help="Saved candidate; default delivered candidate")
    parser.add_argument("--translation-m", nargs=3, required=True, type=float, metavar=("X", "Y", "Z"))
    parser.add_argument("--basis", required=True, help="Original-drawing reason for the declared translation")
    parser.add_argument("--out", type=Path, help="New report file; default RUN/frame_aligned_partition.json")
    args = parser.parse_args()
    if not all(math.isfinite(value) for value in args.translation_m) or not args.basis.strip():
        parser.error("finite translation and nonempty original-drawing basis required")
    run = args.run.resolve()
    if not (run / "summary.json").is_file() or not (run / "agent_receipt.json").is_file():
        parser.error("run is still active or incomplete: summary.json and agent_receipt.json are required")
    summary = read(run / "summary.json")
    candidate = args.candidate or (summary.get("delivery") or {}).get("candidate")
    if not candidate or candidate in {".", ".."} or "/" in candidate or "\\" in candidate:
        parser.error("choose a saved candidate with --candidate")
    folder = run / candidate
    original_proposal = read(folder / "proposal.json")
    source_path = folder / "source_model.json"
    original_file_sha256 = digest(source_path)
    original_source = read(source_path)
    translation = tuple(args.translation_m)
    shifted_proposal = translate_proposal(original_proposal, translation)
    gt = load_gt_document("sm24_anchor")
    if gt is None or gt.verification.status != "human_verified":
        raise ValueError("verified sm24 typed-v3 GT required")
    raw = reference_partition(ensure_corrected_geometry(original_proposal["geometry"]),
                              gt, source_spaces=original_source["spaces"])
    with tempfile.TemporaryDirectory(prefix="sm24_frame_evaluation_") as temporary:
        path = Path(temporary) / "translated_candidate"
        built = export_source_proposal(shifted_proposal, path, provenance={
            "mode": "post_generation_explicit_translation_for_evaluation",
            "original_source_model_sha256": original_source["source_model_sha256"],
            "translation_m": list(translation), "basis": args.basis})
        if not built.get("source_geometry_ready"):
            raise RuntimeError(f"translated source failed: {built.get('error', built.get('source_validation'))}")
        shifted_source = read(path / "source_model.json")
        consistency = translated_source_consistent(original_source, shifted_source, translation)
        if not all(consistency.values()):
            raise RuntimeError(f"source translation mismatch: {consistency}")
        aligned = reference_partition(ensure_corrected_geometry(shifted_proposal["geometry"]),
                                      gt, source_spaces=shifted_source["spaces"])
        shifted_hash = shifted_source["source_model_sha256"]
    result = {"mode": "post_generation_explicit_translation_only",
              "candidate": candidate, "original_source_model_sha256": original_source["source_model_sha256"],
              "original_source_file_sha256": original_file_sha256,
              "original_source_bytes_unchanged": digest(source_path) == original_file_sha256,
              "translated_temporary_source_model_sha256": shifted_hash,
              "translation_m": list(translation), "translation_basis": args.basis,
              "source_translation_checks": consistency,
              "unaligned_reference_partition": raw, "frame_aligned_reference_partition": aligned,
              "alignment_policy": "caller-declared translation; no rotation, scale, GT fitting or source candidate edit",
              "limits": ["Frame alignment only removes a declared coordinate-origin difference.",
                         "Partition comparison does not verify doors, windows or original-pixel interpretation."]}
    output = (args.out or run / "frame_aligned_partition.json").resolve()
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"candidate": candidate, "translation_m": list(translation),
                      "unaligned_status": raw["status"], "aligned_status": aligned["status"],
                      "report": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
