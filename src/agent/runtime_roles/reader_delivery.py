"""Local drawing review bound to the exact saved reader result and its views."""

import hashlib
from pathlib import Path


LOCAL_REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"summary": {"type": "string", "minLength": 1}},
    "required": ["summary"],
}


def local_review(review, *, artifact_sha256, views, image_sha256=None):
    import jsonschema
    jsonschema.validate(review, LOCAL_REVIEW_SCHEMA)
    if not review["summary"].strip():
        raise ValueError("local_review.summary must describe the drawing/overlay check")
    if not views:
        raise ValueError("local review requires saved result views; prepare or trial the reading first")
    return {"status": "reviewed_by_reader", "summary": review["summary"],
            "artifact_sha256": artifact_sha256, "image_sha256": image_sha256,
            "views": views, "independently_verified": False}


def verify_views(root, views):
    root = Path(root).resolve()
    for row in views:
        path = (root / row["file"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("reader view is missing or outside its task")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("reader view hash mismatch")


def require_observed_trial(store, tool_name, identity_key, identity, view_hashes):
    """A review must follow a model request that actually contained these views.

    Pure validators have no model journal. RoleSession always supplies its child
    store, so real/scripted readers cannot trial and pre-approve in one response.
    Earlier observations of unchanged views remain usable after context eviction.
    """
    if store is None:
        return
    events = list(store.events)
    prepared = None
    for event in reversed(events):
        payload = event.payload
        if (payload.event_type == "tool_execution" and payload.tool_name == tool_name
                and payload.outcome == "succeeded"):
            raw = store.resolve(payload.raw_result)
            if (raw.get("structuredContent") or {}).get(identity_key) == identity:
                prepared = event
                break
    expected = set(view_hashes)
    if prepared is not None and expected:
        for event in events:
            if event.sequence > prepared.sequence and event.payload.event_type == "adapter_request":
                if expected <= {image.sent.sha256 for image in event.payload.images}:
                    return
    raise ValueError("The exact trial views have not reached a model request yet. Inspect the returned views before submitting; do not trial and approve in the same response.")


def completed_reader_handoff(engine):
    """Stop after the accepted, reviewed submission, without an extra model reply."""
    name = "submit_plan_reading" if engine.role.role_id == "plan_reader" else "submit_elevation_reading"
    event = next((e for e in reversed(engine.store.events)
                  if e.payload.event_type == "tool_execution"
                  and e.payload.repeatability != "read_only"), None)
    if event is None or event.payload.tool_name != name or event.payload.outcome != "succeeded":
        return None
    raw = engine.store.resolve(event.payload.raw_result)
    if raw.get("isError"):
        return None
    saved = engine.tools.submission.read()
    if saved is None or not saved["validation"].get("local_review"):
        return None
    reply = raw.get("structuredContent") or {}
    if reply.get("artifact_sha256") != saved["artifact_sha256"]:
        return None
    return {"origin": "domain_tool", "tool_name": name, "event_id": event.event_id,
            **engine.tools.submission.snapshot()}
