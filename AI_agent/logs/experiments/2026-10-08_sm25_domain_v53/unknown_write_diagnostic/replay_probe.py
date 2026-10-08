"""Read-only reproduction of the plan_f1 third-trial preprocessing failure.

This deliberately stops before PlanTrial calls build_plan_bim.  Run with
Python's ``-B`` flag so the frozen worktree remains byte-for-byte untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback


FROZEN_WORKTREE = Path(r"D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008")
HERE = Path(__file__).resolve().parent
IMAGE_SHA256 = "6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644"

sys.path.insert(0, str(FROZEN_WORKTREE))

from src.agent.geometry.plan_feedback import resolve_plan_lengths  # noqa: E402
from src.agent.geometry.plan_ink_alignment import _segments  # noqa: E402
from src.agent.geometry.plan_input import normalize_plan_fields  # noqa: E402
from src.agent.geometry.profile_observation_binding import resolve_plan_pixels  # noqa: E402
from src.agent.runtime_roles.trial import _reading_align  # noqa: E402


def reject_profile_lookup(profile_id: str):
    raise RuntimeError(f"unexpected profile lookup: {profile_id}")


def trace_failure(frame, event, argument):
    if (
        event == "exception"
        and frame.f_code.co_filename.endswith("plan_dimension_alignment.py")
        and frame.f_lineno == 210
        and argument[0] is StopIteration
    ):
        local = frame.f_locals
        footprint = local["plan"]["footprint_pixels"]
        print("failure_chain=" + str(local.get("chain", {}).get("id")))
        print("failure_edge_index=" + str(local.get("edge_index")))
        print("loop_ring_length=" + str(len(local.get("ring", []))))
        print("current_ring_length=" + str(len(footprint)))
        print("current_segment_indices=" + json.dumps([row[0] for row in _segments(footprint, closed=True)]))
        print("current_footprint=" + json.dumps(footprint, separators=(",", ":")))
        print("target_pixels=" + json.dumps(local.get("target_pixels"), separators=(",", ":")))
    return trace_failure


def main() -> int:
    plan = json.loads((HERE / "trial_003_plan.json").read_bytes())
    normalized, aliases = normalize_plan_fields(dict(plan))
    print(f"normalize_plan_fields=ok aliases={len(aliases)}")
    numeric, length_bindings = resolve_plan_lengths(normalized)
    print(f"resolve_plan_lengths=ok bindings={len(length_bindings)}")
    numeric, measurement_bindings = resolve_plan_pixels(
        numeric,
        image="1f_view.png",
        image_sha256=IMAGE_SHA256,
        load_profile=reject_profile_lookup,
    )
    print(f"resolve_plan_pixels=ok bindings={len(measurement_bindings)}")
    sys.settrace(trace_failure)
    try:
        _reading_align(numeric, image_path=HERE / "1f_view.png", image_name="1f_view.png")
    except BaseException as error:
        sys.settrace(None)
        print(f"exception={type(error).__module__}.{type(error).__qualname__}: {error}")
        traceback.print_exc(file=sys.stdout)
        return 1
    finally:
        sys.settrace(None)
    print("unexpected_result=_reading_align completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
