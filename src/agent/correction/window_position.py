"""F-9 route② S0 (2026-08-11, design v2.1 §4.4/§5.3/§8/§9/§10 S0): raw
projection context, resolver artifact V2, position-decision/evidence
artifacts, the explicit legacy/new artifact-version loader registry, and the
typed §9 error-code vocabulary.

Everything in this module is new, additive scaffolding — nothing here is
called by any live production path yet (v2.1 §10 S0: "均先不接 live
production"). It is independently schema/serialize/reload/hash-testable now
so S2/S3/S4 do not have to design these types under wiring pressure.

Kept as its own file (not folded into `window_sources.py`, already 1200+
lines) per v2.1 §11's file-responsibility table: "projector、pairing、
hydration artifact → 建议新 correction/window_position.py，避免继续膨胀
window_sources.py".
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agent.correction.footprint import floor_footprint_fingerprint
from src.agent.correction.schema import CorrectionDrawV3CitationV2
from src.agent.correction.window_sources import (
    FiniteFloat,
    Hex64,
    RawReadingArtifactV1,
    SourceIntervalV1,
    SourceLocator,
    StableId,
    WindowResolverInputsArtifactV1,
    canonical_sha256,
)

_CFG = ConfigDict(extra="forbid", frozen=True, strict=True)


def _without_key(model: BaseModel, key: str) -> dict:
    data = model.model_dump(mode="json")
    data.pop(key, None)
    return data


# ---------------------------------------------------------------------------
# §9 typed error vocabulary. A WIDER category type than
# `window_sources.WindowSourceErrorCategory` (which only has
# "model_draw_error"/"input_integrity_error") — v2.1 §9 needs three more
# buckets ("upstream evidence block" / "invariant" / "deterministic
# transform") that the existing type was never meant to cover. Defined as
# its own class (not by widening the existing Literal in place) so this S0
# batch cannot change the runtime behaviour of any existing
# `WindowResolverInputError` call site — none of them are touched.
# ---------------------------------------------------------------------------

PositionEvidenceErrorCategory = Literal[
    "model_draw_error", "upstream_evidence_block", "input_integrity_error",
    "invariant", "deterministic_transform",
]

# v2.1 §9 table, restated as a mechanical code -> category map so a caller
# never has to hand-pick the category string (and risk misclassifying a
# model mistake as an invariant, or vice versa -- exactly the "category is a
# required keyword" discipline `window_sources.WindowResolverInputError`
# already established, extended to the wider vocabulary this design adds).
POSITION_EVIDENCE_ERROR_CATEGORY: dict[str, PositionEvidenceErrorCategory] = {
    "producer_window_span_populated": "model_draw_error",
    "position_evidence_authority_invalid": "model_draw_error",
    "position_evidence_pair_mismatch": "model_draw_error",
    "position_evidence_insufficient": "upstream_evidence_block",
    "projection_datum_unresolved": "upstream_evidence_block",
    "projection_scope_unresolved": "upstream_evidence_block",
    "projection_scope_ambiguous": "upstream_evidence_block",
    "source_identity_invalid": "input_integrity_error",
    "position_hydration_identity_drift": "invariant",
    "position_evidence_post_transform_mismatch": "deterministic_transform",
    "unknown_artifact_version": "input_integrity_error",
}


class WindowPositionEvidenceError(ValueError):
    """Typed, stable route② position-evidence rejection (v2.1 §9).

    Sibling of `window_sources.WindowResolverInputError`, not a replacement
    for it — S0 does not touch any existing `WindowResolverInputError` call
    site. `category` is a required keyword for the same reason that class
    requires it: a raise site that forgets to classify itself fails loudly
    instead of silently defaulting into the wrong retry/archive bucket.
    """

    def __init__(self, code: str, context: Mapping[str, object] | None = None, *, category: PositionEvidenceErrorCategory):
        self.code = code
        self.category = category
        self.context = dict(context or {})
        super().__init__(f"{code}: {self.context}")


def position_evidence_error(code: str, context: Mapping[str, object] | None = None) -> WindowPositionEvidenceError:
    """Construct a `WindowPositionEvidenceError` with its category looked up
    from `POSITION_EVIDENCE_ERROR_CATEGORY` (v2.1 §9 table), instead of
    letting each call site hand-pick a category string.
    """
    category = POSITION_EVIDENCE_ERROR_CATEGORY.get(code)
    if category is None:
        raise KeyError(f"{code!r} is not in the v2.1 §9 error vocabulary; add it to POSITION_EVIDENCE_ERROR_CATEGORY")
    return WindowPositionEvidenceError(code, context, category=category)


# ---------------------------------------------------------------------------
# §4.4 raw projection context: window-independent facade-ring facts a raw
# draw's OWN floor/cell geometry can produce before any window is hydrated.
# ---------------------------------------------------------------------------

class FloorRingFactV1(BaseModel):
    model_config = _CFG
    floor_id: StableId
    footprint_fingerprint: Hex64
    z_floor: FiniteFloat
    ceiling_height: FiniteFloat


class RawProjectionContextV1(BaseModel):
    """v2.1 §4.4 raw projection context.

    REWORKED 2026-08-11 per sol MAJOR-1 (`AI_agent/logs/reviews/verdict/
    2026-08-11_f22_f9s0s1_crossreview_sol.md`): `raw_draw_sha256` used to be
    an opaque caller-supplied string with no cross-check against any actual
    bytes elsewhere in the eventual artifact, so a context could legally
    claim a `raw_draw_sha256` that disagreed with the raw draw bytes it was
    actually paired with in `WindowResolverInputsArtifactV2` (sol's repro:
    `raw_hash_mismatch_accepted == True`). `WindowResolverInputsArtifactV2`
    below now cross-validates this field against its own
    `raw_draw_canonical_bytes`, and a new `view_datum_sha256` field
    similarly cross-validates against `direction_datum_sidecar_bytes` (v2.1
    §5.79-582: "V2 artifact 内嵌 direction/datum sidecar bytes"). The full
    per-scope `datum_geometry_sha256`/`z_datum_mode`/`ElevationProjection
    ScopeV1` machinery (v2.1 §7.1-7.3) is real algorithm work that requires
    live authentication (S2) to produce meaningfully — S0's job is only to
    make the WIRE capable of expressing and hash-binding an identity, which
    `view_datum_sha256` now does; it is not yet populated by any live scope
    resolver.
    """

    model_config = _CFG
    raw_draw_sha256: Hex64
    resolver_hash: Hex64
    view_datum_sha256: Hex64
    floor_rings: tuple[FloorRingFactV1, ...] = Field(min_length=1)
    content_sha256: Hex64

    @model_validator(mode="after")
    def _hash(self):
        ids = [row.floor_id for row in self.floor_rings]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("floor_rings must be sorted by floor_id and unique")
        if self.content_sha256 != canonical_sha256(_without_key(self, "content_sha256")):
            raise ValueError("content_sha256 does not match canonical raw projection context")
        return self


def materialize_raw_projection_context(
    raw: CorrectionDrawV3CitationV2, *, raw_draw_sha256: str, resolver_hash: str, view_datum_sha256: str,
) -> RawProjectionContextV1:
    """Build the window-independent facade-ring context straight from a raw
    draw's own floor/cell geometry (v2.1 §4.4).

    Deliberately takes no window-shaped input and refuses anything but a
    `CorrectionDrawV3CitationV2` instance (v2.1 §4.4 requires this to run
    BEFORE hydration; the type check is a structural guard against a caller
    handing it a full `CorrectedGeometryV3` instead — §12.2 "Raw projection
    context" lock: "给 context builder 传 full model...时，structure/path
    锁红"). Its implementation only reads `raw.floors`, so it cannot depend
    on any window having been hydrated even by accident.

    `raw_draw_sha256` and `view_datum_sha256` are caller-supplied here (this
    function has no bytes of its own to hash) but MUST agree with the
    eventual `WindowResolverInputsArtifactV2.raw_draw_canonical_bytes` /
    `direction_datum_sidecar_bytes` -- that cross-field agreement is
    enforced when the two are assembled together into the artifact, not
    here (see `WindowResolverInputsArtifactV2._canonical_and_hashed`).
    """
    if not isinstance(raw, CorrectionDrawV3CitationV2):
        raise TypeError(
            "materialize_raw_projection_context requires a raw "
            "CorrectionDrawV3CitationV2, not a full/hydrated model"
        )
    rows = tuple(sorted(
        (
            FloorRingFactV1(
                floor_id=floor.id,
                footprint_fingerprint=floor_footprint_fingerprint(raw, floor),
                z_floor=floor.z_floor, ceiling_height=floor.ceiling_height,
            )
            for floor in raw.floors
        ),
        key=lambda row: row.floor_id,
    ))
    payload = {
        "raw_draw_sha256": raw_draw_sha256, "resolver_hash": resolver_hash,
        "view_datum_sha256": view_datum_sha256,
        "floor_rings": [row.model_dump(mode="json") for row in rows],
    }
    return RawProjectionContextV1(
        raw_draw_sha256=raw_draw_sha256, resolver_hash=resolver_hash, view_datum_sha256=view_datum_sha256,
        floor_rings=rows, content_sha256=canonical_sha256(payload),
    )


# ---------------------------------------------------------------------------
# §4.1/§8.5 resolver-input artifact V2 -- the new-run wire, distinct from
# the historical `window_resolver_inputs_v1` producer artifact (still owned
# by `window_sources.WindowResolverInputsArtifactV1`, untouched by S0).
# ---------------------------------------------------------------------------

class WindowResolverInputsArtifactV2(BaseModel):
    """v2.1 §4.1 table row "新 v3 raw draw" / §8.5 attempt-bundle member.

    Distinguished from the historical `window_resolver_inputs_v1` artifact
    by its OWN `artifact_version` field, never by inspecting whether a
    window carries `span` (v2.1 §4.1: "禁止按『有没有 span』猜版本" — see
    `load_window_resolver_artifact` below, which dispatches on this field).

    REWORKED 2026-08-11 per sol MAJOR-1: the ONLY thing the validator used
    to check was this outer envelope's own `content_sha256` — it never
    verified that `raw_projection_context.raw_draw_sha256` actually equals
    `sha256(raw_draw_canonical_bytes)`. Because the outer hash is computed
    OVER both fields together, a hostile/buggy writer could pair a raw draw
    with a context built from DIFFERENT raw bytes, recompute the outer hash
    over that mismatched pair, and the result would still self-validate —
    "外层再自哈希不能替代内层身份绑定" (sol). Now enforced explicitly, plus
    the matching `direction_datum_sidecar_bytes` <-> `view_datum_sha256`
    cross-check (v2.1 §579-582).
    """

    model_config = _CFG
    artifact_version: Literal["window_resolver_inputs_v2"]
    raw_draw_canonical_bytes: bytes
    raw_view_manifest_bytes: bytes
    raw_reading_artifacts: tuple[RawReadingArtifactV1, ...]
    direction_datum_sidecar_bytes: bytes
    raw_projection_context: RawProjectionContextV1
    content_sha256: Hex64

    @model_validator(mode="after")
    def _canonical_and_hashed(self):
        ids = tuple(row.input_id for row in self.raw_reading_artifacts)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("raw_reading_artifacts must have unique canonical input_id order")
        actual_raw_hash = hashlib.sha256(self.raw_draw_canonical_bytes).hexdigest()
        if actual_raw_hash != self.raw_projection_context.raw_draw_sha256:
            raise ValueError(
                "raw_projection_context.raw_draw_sha256 does not match "
                "sha256(raw_draw_canonical_bytes) -- context is bound to different raw bytes"
            )
        actual_datum_hash = hashlib.sha256(self.direction_datum_sidecar_bytes).hexdigest()
        if actual_datum_hash != self.raw_projection_context.view_datum_sha256:
            raise ValueError(
                "raw_projection_context.view_datum_sha256 does not match "
                "sha256(direction_datum_sidecar_bytes) -- context is bound to a different datum sidecar"
            )
        if self.content_sha256 != canonical_sha256(_without_key(self, "content_sha256")):
            raise ValueError("content_sha256 does not match resolver-input artifact v2")
        return self


# ---------------------------------------------------------------------------
# §5.3/§8.1 per-window position decision + the evidence-artifact wrapper.
# ---------------------------------------------------------------------------

def _canonical_window_key(plan_locator: str) -> str:
    """v2.1 §5.3: "必须另存 canonical_window_key = hash(plan_authority_locator)".
    A pure function (not a method) so both `build_window_position_decision`
    and the model's own validator compute it identically.
    """
    return canonical_sha256({"schema": "canonical_window_key_v1", "plan_authority_locator": plan_locator})


class WindowPositionDecisionV1(BaseModel):
    """v2.1 §5.3/§8.1 per-window position decision.

    REWORKED 2026-08-11 per sol MAJOR-2. Two independent gaps closed:

    1. Preimage was missing every identity field that binds a decision to a
       SPECIFIC raw draw / resolver artifact / projection context (v2.1
       §560-575 lists them explicitly). Without them, the exact same
       decision object could be embedded in two `WindowPositionEvidenceArt
       ifactV1` wrappers declaring two different `(raw_draw_sha256,
       resolver_hash)` pairs and self-hash validly in both — sol's repro:
       `evidence_binding a b ... == evidence_binding c d ...` (identical
       `decision_sha256` under two different, both-plausible-looking
       outer bindings). Now `raw_draw_sha256`/`resolver_hash`/
       `raw_projection_context_sha256` are IN the decision's own preimage,
       and the wrapper cross-validates its own binding against them (see
       `WindowPositionEvidenceArtifactV1._hash` below) — a decision can no
       longer be silently re-parented onto a different raw/resolver/context
       triple.
    2. `accepted` had no invariants connecting it to the OTHER fields on the
       same decision — sol's three hostile constructions (`accepted_
       without_elevation`, `accepted_wrong_derived_span`,
       `accepted_distance_over_tolerance`) all passed. Now enforced: an
       accepted decision must have >=1 elevation corroborator, every
       distance <= tolerance_value, and `derived_span == plan_world_interval`
       (v2.1 §5.4: "derived_span = sorted(plan_authority.world_..._interval)").
    """

    model_config = _CFG
    raw_draw_sha256: Hex64
    resolver_hash: Hex64
    raw_projection_context_sha256: Hex64
    canonical_window_key: Hex64
    window_id: StableId
    plan_locator: SourceLocator
    elevation_locators: tuple[SourceLocator, ...]
    plan_world_interval: SourceIntervalV1
    elevation_projected_intervals: tuple[SourceIntervalV1, ...]
    distances: tuple[FiniteFloat, ...]
    tolerance_name: StableId
    tolerance_value: FiniteFloat
    decision: Literal["accepted", "rejected"]
    derived_span: SourceIntervalV1 | None
    decision_sha256: Hex64

    @model_validator(mode="after")
    def _shape(self):
        if not (len(self.elevation_locators) == len(self.elevation_projected_intervals) == len(self.distances)):
            raise ValueError("elevation locators/projected intervals/distances must align 1:1")
        if len(set(self.elevation_locators)) != len(self.elevation_locators):
            raise ValueError("elevation_locators must not repeat within one decision")
        if any(d < 0 for d in self.distances):
            raise ValueError("distances must be non-negative")
        if self.tolerance_value <= 0:
            raise ValueError("tolerance_value must be positive")
        if self.canonical_window_key != _canonical_window_key(self.plan_locator):
            raise ValueError("canonical_window_key does not match hash(plan_locator)")
        if self.decision == "accepted":
            if not self.elevation_locators:
                raise ValueError("accepted decision requires at least one elevation corroborator")
            if any(d > self.tolerance_value for d in self.distances):
                raise ValueError("accepted decision requires every distance within tolerance_value")
            if self.derived_span is None:
                raise ValueError("accepted decision requires derived_span")
            if self.derived_span != self.plan_world_interval:
                raise ValueError(
                    "accepted decision's derived_span must equal plan_world_interval "
                    "(v2.1 §5.4: plan authority is the sole span source)"
                )
        if self.decision == "rejected" and self.derived_span is not None:
            raise ValueError("rejected decision must not carry derived_span")
        if self.decision_sha256 != canonical_sha256(_without_key(self, "decision_sha256")):
            raise ValueError("decision_sha256 does not match canonical position decision")
        return self


class WindowPositionEvidenceArtifactV1(BaseModel):
    """v2.1 §8.1 wrapper. REWORKED 2026-08-11 per sol MAJOR-2: now
    cross-validates that every embedded decision's OWN `raw_draw_sha256`/
    `resolver_hash` agree with this wrapper's — the outer envelope can no
    longer claim a binding a decision does not itself carry.
    """

    model_config = _CFG
    raw_draw_sha256: Hex64
    resolver_hash: Hex64
    decisions: tuple[WindowPositionDecisionV1, ...]
    content_sha256: Hex64

    @model_validator(mode="after")
    def _hash(self):
        ids = [d.window_id for d in self.decisions]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("decisions must be sorted by window_id and unique")
        for decision in self.decisions:
            if decision.raw_draw_sha256 != self.raw_draw_sha256 or decision.resolver_hash != self.resolver_hash:
                raise ValueError(
                    f"decision {decision.window_id!r} raw_draw_sha256/resolver_hash "
                    "does not match this evidence artifact's own binding"
                )
        if self.content_sha256 != canonical_sha256(_without_key(self, "content_sha256")):
            raise ValueError("content_sha256 does not match canonical position evidence artifact")
        return self


def build_window_position_decision(
    *, raw_draw_sha256: str, resolver_hash: str, raw_projection_context_sha256: str,
    window_id: str, plan_locator: str, elevation_locators: tuple[str, ...],
    plan_world_interval: SourceIntervalV1, elevation_projected_intervals: tuple[SourceIntervalV1, ...],
    distances: tuple[float, ...], tolerance_name: str, tolerance_value: float,
    decision: Literal["accepted", "rejected"], derived_span: SourceIntervalV1 | None,
) -> WindowPositionDecisionV1:
    """Convenience constructor that computes `decision_sha256` and
    `canonical_window_key` from the rest of the fields, so a caller (or
    test) never hand-supplies either in a way that could silently drift
    from its preimage.
    """
    canonical_window_key = _canonical_window_key(plan_locator)
    payload = {
        "raw_draw_sha256": raw_draw_sha256, "resolver_hash": resolver_hash,
        "raw_projection_context_sha256": raw_projection_context_sha256,
        "canonical_window_key": canonical_window_key,
        "window_id": window_id, "plan_locator": plan_locator,
        "elevation_locators": list(elevation_locators),
        "plan_world_interval": plan_world_interval.model_dump(mode="json"),
        "elevation_projected_intervals": [i.model_dump(mode="json") for i in elevation_projected_intervals],
        "distances": list(distances), "tolerance_name": tolerance_name, "tolerance_value": tolerance_value,
        "decision": decision,
        "derived_span": None if derived_span is None else derived_span.model_dump(mode="json"),
    }
    return WindowPositionDecisionV1(
        raw_draw_sha256=raw_draw_sha256, resolver_hash=resolver_hash,
        raw_projection_context_sha256=raw_projection_context_sha256, canonical_window_key=canonical_window_key,
        window_id=window_id, plan_locator=plan_locator, elevation_locators=elevation_locators,
        plan_world_interval=plan_world_interval, elevation_projected_intervals=elevation_projected_intervals,
        distances=distances, tolerance_name=tolerance_name, tolerance_value=tolerance_value,
        decision=decision, derived_span=derived_span, decision_sha256=canonical_sha256(payload),
    )


# ---------------------------------------------------------------------------
# §4.1/§10 S0 explicit loader registry: dispatch on the wire's OWN
# `artifact_version` string, never on "has span" (v2.1 §4.1 last line: "禁止
# 按『有没有 span』猜版本"). Unknown version fails closed.
# ---------------------------------------------------------------------------

ArtifactLoader = Callable[[bytes], BaseModel]


def _load_window_resolver_inputs_v1(raw_bytes: bytes) -> WindowResolverInputsArtifactV1:
    # Historical v3 producer artifact V1 -- untouched legacy replay, owned by
    # window_sources.py. This loader does not reinterpret it in any way.
    return WindowResolverInputsArtifactV1.model_validate_json(raw_bytes)


def _load_window_resolver_inputs_v2(raw_bytes: bytes) -> WindowResolverInputsArtifactV2:
    return WindowResolverInputsArtifactV2.model_validate_json(raw_bytes)


WINDOW_RESOLVER_ARTIFACT_LOADER_REGISTRY: dict[str, ArtifactLoader] = {
    "window_resolver_inputs_v1": _load_window_resolver_inputs_v1,
    "window_resolver_inputs_v2": _load_window_resolver_inputs_v2,
}


def load_window_resolver_artifact(raw_bytes: bytes) -> BaseModel:
    """The single dispatch point for either resolver-artifact wire.

    Reads ONLY the `artifact_version` field to pick a loader — this is the
    explicit registry v2.1 §10 S0 requires, and the reason S0's "Legacy
    scope" lock (§12.2) can assert "以『有无 span』猜版本...锁红": this
    function structurally cannot do that, it never inspects `windows` at
    all before dispatching.
    """
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise position_evidence_error("source_identity_invalid", {"artifact": "window_resolver_artifact"}) from exc
    version = payload.get("artifact_version") if isinstance(payload, dict) else None
    loader = WINDOW_RESOLVER_ARTIFACT_LOADER_REGISTRY.get(version) if isinstance(version, str) else None
    if loader is None:
        raise position_evidence_error("unknown_artifact_version", {"artifact_version": version})
    return loader(raw_bytes)


__all__ = [
    "PositionEvidenceErrorCategory", "POSITION_EVIDENCE_ERROR_CATEGORY", "WindowPositionEvidenceError",
    "position_evidence_error",
    "FloorRingFactV1", "RawProjectionContextV1", "materialize_raw_projection_context",
    "WindowResolverInputsArtifactV2",
    "WindowPositionDecisionV1", "WindowPositionEvidenceArtifactV1", "build_window_position_decision",
    "ArtifactLoader", "WINDOW_RESOLVER_ARTIFACT_LOADER_REGISTRY", "load_window_resolver_artifact",
]
