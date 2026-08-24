"""Finalize a diagnostic draw through the REAL correction production path, then
run the geometry kernel on it.  ⛔ Never a score (the answer is in the input).

Nothing is faked: the B5 window-host proof is issued by the ordinary artifact
verifier, from window citations that point at a real 0_reading.
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, "/workspaces/EnergyPlus-Agent-dev")

from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.parse import correction_target
from src.agent.correction.artifact_serialization import serialize_correction_output
from src.agent.correction.window_host import build_window_hosts_artifact
from src.agent.correction.window_sources import (
    build_verified_window_inputs_from_run,
    serialize_window_resolver_inputs_artifact,
)
from src.agent.geometry.build import _issue_verified_window_host_proof
from src.agent.pipeline import materialize_kernel_geometry
from src.validator.checks.correction import check_correction


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("draw", type=Path)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--profile", default="orthogonal_polygon")
    args = ap.parse_args()

    target = correction_target(args.profile)
    payload = json.loads(args.draw.read_text(encoding="utf-8"))
    rdir = args.run_dir / "0_reading"

    from src.agent.correction.parse import parse_correction_draw
    geom = parse_correction_draw(payload, target)
    print(f"parsed draw: floors={len(geom.floors)} "
          f"cells={sum(len(f.cells) for f in geom.floors)} windows={len(geom.windows)}")

    verified_inputs = build_verified_window_inputs_from_run(
        producer_draw=geom, run_dir=args.run_dir, reading_dir=rdir)
    print("window resolver inputs: verified")

    result = finalize_correction_draw(
        geom, vector_dir=rdir, target=target, verified_window_inputs=verified_inputs)
    print("finalize: ok")

    rep = check_correction(
        result.geom, window_host_proof=result.window_host_claims,
        window_evidence=result.window_evidence_ledger,
        capability_profile=args.profile, run_profile="exploratory",
        verified_window_inputs=verified_inputs)
    blocking = rep.blocking()
    print(f"gate①(correction): {len(rep.results)} checks, {len(blocking)} blocking")
    for r in blocking[:15]:
        print("   BLOCK", r.check_id, "-", r.message[:160])

    # Same three artifacts the real stage writer files, built by the same
    # builders — so the proof below is issued by the ordinary verifier, not
    # hand-forged (a forged trust root would make the whole probe worthless).
    output_bytes = serialize_correction_output(result.geom)
    import hashlib
    output_sha = hashlib.sha256(output_bytes).hexdigest()
    resolver_bytes = serialize_window_resolver_inputs_artifact(verified_inputs)
    hosts_bytes = build_window_hosts_artifact(
        output_sha256=output_sha,
        claims=result.window_host_claims,
        evidence=result.window_evidence_ledger,
    ).model_dump_json(indent=2).encode("utf-8")
    proof = _issue_verified_window_host_proof(
        raw_resolver_inputs_bytes=resolver_bytes,
        raw_window_hosts_bytes=hosts_bytes,
        raw_output_bytes=output_bytes,
    )
    print("B5 window-host proof: issued")
    out_dir = args.out_dir
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "correction_snapped.json").write_bytes(output_bytes)
    bg, issues = materialize_kernel_geometry(
        result.geom, out_dir, capability_profile=args.profile, window_host_proof=proof)
    if bg is None:
        print("KERNEL FAILED:", issues)
        raise SystemExit(1)
    print(f"kernel: zones={len(dict.fromkeys(bg.zones))} surfaces={len(bg.surfaces)} "
          f"windows={len(bg.windows)}  interzone_issues={len(issues)} notes={len(bg.notes)}")
    for i in issues[:20]:
        print("   !", i)
    for n in bg.notes[:20]:
        print("   -", n)

    # 3_split_pairing: the serializer is the next code-only stage, so run it in
    # the same breath — a kernel result that cannot be serialized is not "green".
    from src.agent.geometry.specs import serialize_geometry
    from src.validator.checks.kernel import check_kernel

    krep = check_kernel(bg, window_host_proof=proof, capability_profile=args.profile,
                        interzone_issues=issues, run_profile="exploratory")
    kblock = krep.blocking()
    print(f"gate①(kernel): {len(krep.results)} checks, {len(kblock)} blocking")
    for r in kblock[:15]:
        print("   BLOCK", r.check_id, "-", r.message[:160])
        for row in (r.evidence or {}).get("offenders", [])[:10]:
            print("        ", row)
    frame = "building_axis" if result.geom.schema_version == "3" else "world"
    zone_specs, surface_specs, fen_specs, used = serialize_geometry(bg, frame_label=frame)
    print(f"3_split_pairing: zone_specs={len(zone_specs.splitlines())} lines, "
          f"surface_specs={len(surface_specs.splitlines())} lines, "
          f"fenestration={len(fen_specs.splitlines())} lines")
    if out_dir is not None:
        (out_dir / "geometry_specs.md").write_text(
            "\n\n".join(["## zones", zone_specs, "## surfaces", surface_specs,
                          "## fenestration", fen_specs]), encoding="utf-8")


if __name__ == "__main__":
    main()
