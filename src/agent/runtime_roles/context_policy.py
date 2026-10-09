"""Request projections for role mode; single-model defaults remain untouched."""

from src.agent_runtime.context import ContextPolicy


def role_context_policy(role_id: str, *, base: ContextPolicy | None = None, **overrides) -> ContextPolicy:
    """Keep reader artifacts retrievable without repeating their entire ledger.

    Keep exact delivery references/status in the coordinator's mutable tail;
    role_state and read_role_artifact expose the complete records. All roles
    compact to 30%: long reader repairs also need headroom before another prefix
    rewrite. Full history, image bytes and evidence remain retrievable.
    """
    if role_id not in {"coordinator", "plan_reader", "elevation_reader"}:
        raise ValueError(f"unknown context role: {role_id}")
    values = (base or ContextPolicy(compact_at_tokens=150_000 if role_id == "coordinator" else 100_000)).model_dump()
    values["compact_to_ratio"] = 0.3
    if role_id == "coordinator":
        values["state_item_fields"] = {**values.get("state_item_fields", {}), "reader-artifacts": (
            "task_id", "role_id", "target", "status", "artifact", "reason",
        )}
    values.update(overrides)
    return ContextPolicy(**values)
