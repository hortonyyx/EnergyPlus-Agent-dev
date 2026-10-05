"""Finish saved BIMs with T1's shared selection and delivery implementation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.tool_scripts.bim_agent_budget import fallback_selection
from scripts.tool_scripts.run_bim_agent import Toolkit


def finalize_building(run: Path, *, reason: str, elapsed_seconds: float) -> dict:
    """Mirror the subscription runner's timeout/selection precedence.

    Time or CNY budget stops prefer the latest complete building, even if a
    later partial candidate was selected. Other stops preserve a selection.
    Completeness, geometry checks and HTML all come from the shared T1 code.
    """
    timed_out = reason.endswith("time_budget_exhausted")
    money_stopped = reason.endswith("money_budget_exhausted") or reason == "money_cny_usage_unavailable"
    generation = {"state": "completed" if reason == "completed" else "interrupted",
        "agent_response_completed": reason == "completed", "timed_out": timed_out,
        "elapsed_seconds": elapsed_seconds, "runtime_stop_reason": reason}
    try:
        toolkit = Toolkit(run)
        selection = run / "delivery_selection.json"
        if selection.is_file() and not (timed_out or money_stopped):
            chosen = json.loads(selection.read_bytes())["candidate"]
            origin = "agent_selected"
        else:
            chosen, origin = fallback_selection(toolkit)
        if chosen is None:
            return {"status": "no_saved_candidate", "delivery": None}
        delivery = toolkit.delivery(chosen, selection_origin=origin, generation_status=generation)
        return {"status": "delivered", "delivery": {
            "candidate": chosen, "selection_origin": origin,
            "complete_building": delivery["floor_completeness"]["complete_building"],
            "report": "bim/delivery.json", "viewer": "bim/delivery.html"}}
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Keep the stop reason and saved sources inspectable if handoff fails.
        return {"status": "delivery_failed", "delivery": None,
                "error_type": type(error).__name__, "error": str(error)}


def finalize_runtime_building(engine, reason: str) -> dict:
    if engine.role.read_only:
        return {"status": "readonly_no_building_delivery", "delivery": None}
    return finalize_building(engine.tools.run_directory, reason=reason,
        elapsed_seconds=engine.limits.seconds - engine._remaining())
