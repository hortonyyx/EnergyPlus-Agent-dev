"""Small current configuration fixtures; no historical run or credentials."""

from pathlib import Path


def configuration(*, provider="glm-subscription", model="glm-5.3-flash"):
    root = Path(__file__).resolve().parents[1]
    return {
        "schema_version": 1,
        "batch_id": "offline-current",
        "approval_required_before_launch": True,
        "maximum_seconds_per_case": 60,
        "cases": [{
            "case_id": "offline-current", "mode": "single_model",
            "provider": provider, "model": model,
            "credentials_file": "private-fixture.env",
            "input_kind": "images",
            "input": str(root / "tests/fixtures/role_current/sm24/images"),
            "image_kind": "drawings", "floor_plan_images": ["1f_view.png"],
            "output": "runs/offline-current", "scope": "Offline fixture only.",
            "limits": {"model_calls": 10, "tool_calls": 20, "tokens": 500000, "seconds": 60},
            "max_candidates": 24, "output_tokens": 32000,
            "context_tokens": 900000, "compact_at_tokens": 150000,
            "run_root": str(root),
        }],
    }
