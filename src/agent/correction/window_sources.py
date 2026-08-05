"""B5 Phase-A source trust and current-ring direction bindings.

This module is deliberately the sole production owner of the source locator
catalogue and the ephemeral, ring-dependent Va elevation bindings.  It imports
no judge code: score bindings are an oracle for tests only.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Mapping, Union

from pydantic import AllowInfNan, BaseModel, ConfigDict, Field, Strict, StringConstraints, model_validator

from src.agent.correction.claims import CLAIMS_VOCAB_VERSION, WINDOW_CLAIMS
from src.agent.correction.facade_applicability import ElevationViewBindingV1 as VaElevationViewBindingV1
from src.agent.correction.facade_visibility import FacadeVisibilityInvariantError, VisibilityTolerances, validate_materialized_facade_segments
from src.agent.correction.footprint import floor_footprint_fingerprint
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.execution.view_manifest import RequiredViewEntry, ViewManifest
from src.agent.reading import parse_reading_view

WINDOW_RESOLVER_INPUT_SCHEMA_VERSION = "1"
SOURCE_LOCATOR_PREFIX = "src:"
CURRENT_RING_BINDING_HELPER_VERSION = "window_direction_frame_v1"

FiniteFloat = Annotated[float, Strict(), AllowInfNan(False)]
StableId = Annotated[str, Strict(), StringConstraints(min_length=1)]
Hex64 = Annotated[str, Strict(), StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SourceLocator = Annotated[str, Strict(), StringConstraints(pattern=r"^src:[0-9a-f]{64}$")]
ClaimName = Literal["existence", "host", "along", "width", "sill", "head", "appearance"]
CardinalFamily = Literal["North", "South", "East", "West"]
_CFG = ConfigDict(extra="forbid", frozen=True, strict=True)
_AXIS = {"North": "x", "South": "x", "East": "y", "West": "y"}
_BASE_SIGN = {"North": -1, "South": 1, "East": 1, "West": -1}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _without_hash(model: BaseModel) -> dict:
    data = model.model_dump(mode="json")
    data.pop("content_sha256", None)
    return data


# F-7 (2026-08-05): every window-source rejection is either the correction
# LLM's fault (it cited an observation reference it invented, mis-scoped, or
# was not entitled to use) or an upstream input-integrity fault (the reading
# artifact / view manifest / accepted-attempt bytes do not line up with each
# other — no resample of the correction draw can fix that). The caller that
# turns a rejection into either an archived failed attempt + blind resample
# (model's fault) or a hard, non-retried crash (input's fault) must be able
# to tell the two apart WITHOUT parsing the message text or the `code`
# string — `code` values are reused across both categories at different call
# sites, so only the throw site itself knows which one applies. `category`
# is therefore a required keyword: a raise site that forgets to classify
# itself fails loudly (TypeError) instead of silently defaulting into either
# bucket.
WindowSourceErrorCategory = Literal["model_draw_error", "input_integrity_error"]


class WindowResolverInputError(ValueError):
    """Typed, stable B5 draw/source-input rejection.

    ``category`` distinguishes a correction-draw mistake (archive as a
    failed attempt, blind-resample) from an input-integrity fault (hard
    crash, resampling cannot help) — see the module-level note above.
    """

    def __init__(
        self,
        code: str,
        context: Mapping[str, object] | None = None,
        *,
        category: WindowSourceErrorCategory,
    ):
        self.code = code
        self.category = category
        self.context = dict(context or {})
        super().__init__(f"{code}: {self.context}")


class SourceIntervalV1(BaseModel):
    model_config = _CFG
    lo: FiniteFloat
    hi: FiniteFloat

    @model_validator(mode="after")
    def _ordered(self):
        if self.lo >= self.hi:
            raise ValueError("source interval requires lo < hi")
        return self


class PlanSourceWindowV1(BaseModel):
    model_config = _CFG
    channel: Literal["plan"]
    source_locator: SourceLocator
    source_input_id: StableId
    source_output_sha256: Hex64
    observation_id: StableId
    floor_ref: Annotated[int, Strict(), Field(gt=0)]
    world_x_interval: SourceIntervalV1
    world_y_interval: SourceIntervalV1
    positive_claims: tuple[ClaimName, ...]


class ElevationSourceWindowV1(BaseModel):
    model_config = _CFG
    channel: Literal["elevation"]
    source_locator: SourceLocator
    source_input_id: StableId
    source_output_sha256: Hex64
    observation_id: StableId
    local_along_interval: SourceIntervalV1
    local_z_interval: SourceIntervalV1 | None
    positive_claims: tuple[ClaimName, ...]


SourceWindowV1 = Annotated[Union[PlanSourceWindowV1, ElevationSourceWindowV1], Field(discriminator="channel")]


class WindowClaimSourceLinkV1(BaseModel):
    model_config = _CFG
    window_id: StableId
    claim: ClaimName
    source_locator: SourceLocator


class ReadingArtifactIdentityV1(BaseModel):
    model_config = _CFG
    input_id: StableId
    expected_output_id: StableId
    output_sha256: Hex64


class ElevationDirectionFactV1(BaseModel):
    model_config = _CFG
    input_id: StableId
    resolved_building_direction: CardinalFamily
    resolution_source: Literal["manifest_building_axis", "resolved_direction_sidecar"]
    mirrored: Annotated[bool, Strict()]
    local_x_positive: Literal["image_left_to_right", "image_right_to_left"]
    orientation_output_hash: Hex64 | None
    adapter_version: StableId | None
    view_manifest_sha256: Hex64


class WindowResolverInputsV1(BaseModel):
    model_config = _CFG
    schema_version: Literal["1"]
    claims_vocab_version: Literal["1"]
    producer_draw_sha256: Hex64
    view_manifest: ViewManifest
    reading_artifacts: tuple[ReadingArtifactIdentityV1, ...]
    elevation_direction_facts: tuple[ElevationDirectionFactV1, ...]
    source_windows: tuple[SourceWindowV1, ...]
    claim_links: tuple[WindowClaimSourceLinkV1, ...]
    content_sha256: Hex64

    @model_validator(mode="after")
    def _hash(self):
        if tuple(item.input_id for item in self.reading_artifacts) != tuple(sorted(item.input_id for item in self.reading_artifacts)):
            raise ValueError("reading_artifacts must be sorted by input_id")
        if tuple(item.input_id for item in self.elevation_direction_facts) != tuple(sorted(item.input_id for item in self.elevation_direction_facts)):
            raise ValueError("elevation_direction_facts must be sorted by input_id")
        if tuple((item.channel, item.source_input_id, item.observation_id) for item in self.source_windows) != tuple(sorted((item.channel, item.source_input_id, item.observation_id) for item in self.source_windows)):
            raise ValueError("source_windows must be canonical sorted")
        rank = {claim: index for index, claim in enumerate(("existence", "host", "along", "width", "sill", "head", "appearance"))}
        if tuple((item.window_id, rank[item.claim], item.source_locator) for item in self.claim_links) != tuple(sorted((item.window_id, rank[item.claim], item.source_locator) for item in self.claim_links)):
            raise ValueError("claim_links must be canonical sorted")
        if self.content_sha256 != canonical_sha256(_without_hash(self)):
            raise ValueError("content_sha256 does not match canonical resolver inputs")
        return self


class RawReadingArtifactV1(BaseModel):
    """Exact raw reading bytes embedded in the persisted resolver artifact."""

    model_config = _CFG
    input_id: StableId
    raw_bytes: bytes


class WindowResolverInputsArtifactV1(BaseModel):
    """Self-contained attempt artifact used by accepted and integrated loaders.

    ``WindowResolverInputsV1`` remains the stable resolver-content wire and
    hash root.  This outer artifact carries the immutable raw sources needed
    to re-authenticate that wire without adding parameters to the integrated
    verifier's frozen signature.
    """

    model_config = _CFG
    artifact_version: Literal["window_resolver_inputs_v1"]
    inputs: WindowResolverInputsV1
    producer_draw_canonical_bytes: bytes
    raw_view_manifest_bytes: bytes
    raw_reading_artifacts: tuple[RawReadingArtifactV1, ...]
    content_sha256: Hex64

    @model_validator(mode="after")
    def _canonical_and_hashed(self):
        ids = tuple(row.input_id for row in self.raw_reading_artifacts)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("raw_reading_artifacts must have unique canonical input_id order")
        if self.content_sha256 != canonical_sha256(_without_hash(self)):
            raise ValueError("content_sha256 does not match resolver-input artifact")
        return self


class WindowSourceOfferV1(BaseModel):
    model_config = _CFG
    schema_version: Literal["1"]
    view_manifest_sha256: Hex64
    source_windows: tuple[SourceWindowV1, ...]
    allowed_claims_by_locator: tuple[tuple[SourceLocator, tuple[ClaimName, ...]], ...]
    content_sha256: Hex64

    @model_validator(mode="after")
    def _hash(self):
        if tuple((item.channel, item.source_input_id, item.observation_id) for item in self.source_windows) != tuple(sorted((item.channel, item.source_input_id, item.observation_id) for item in self.source_windows)):
            raise ValueError("source_windows must be canonical sorted")
        if self.content_sha256 != canonical_sha256(_without_hash(self)):
            raise ValueError("content_sha256 does not match canonical source offer")
        return self


@dataclass(frozen=True)
class VerifiedWindowResolverInputs:
    """Opaque-in-practice marker; only builders in this module create it."""

    inputs: WindowResolverInputsV1
    raw_inputs_bytes: bytes
    producer_draw_canonical_bytes: bytes
    raw_view_manifest_bytes: bytes
    raw_reading_artifacts: tuple[tuple[str, bytes], ...]


def build_window_resolver_inputs_artifact(
    verified: VerifiedWindowResolverInputs,
) -> WindowResolverInputsArtifactV1:
    """Bind the resolver wire to the exact producer/manifest/reading bytes."""
    readings = tuple(
        RawReadingArtifactV1(input_id=input_id, raw_bytes=raw)
        for input_id, raw in sorted(verified.raw_reading_artifacts)
    )
    payload = {
        "artifact_version": "window_resolver_inputs_v1",
        "inputs": verified.inputs.model_dump(mode="json"),
        "producer_draw_canonical_bytes": verified.producer_draw_canonical_bytes.decode("utf-8"),
        "raw_view_manifest_bytes": verified.raw_view_manifest_bytes.decode("utf-8"),
        "raw_reading_artifacts": [row.model_dump(mode="json") for row in readings],
    }
    return WindowResolverInputsArtifactV1(
        artifact_version="window_resolver_inputs_v1",
        inputs=verified.inputs,
        producer_draw_canonical_bytes=verified.producer_draw_canonical_bytes,
        raw_view_manifest_bytes=verified.raw_view_manifest_bytes,
        raw_reading_artifacts=readings,
        content_sha256=canonical_sha256(payload),
    )


def serialize_window_resolver_inputs_artifact(
    verified: VerifiedWindowResolverInputs,
) -> bytes:
    return canonical_json_bytes(
        build_window_resolver_inputs_artifact(verified).model_dump(mode="json")
    )


def source_locator(*, input_id: str, observation_id: str, output_sha256: str) -> str:
    return SOURCE_LOCATOR_PREFIX + canonical_sha256({
        "input_id": input_id, "observation_id": observation_id,
        "output_sha256": output_sha256, "schema": "window_source_locator_v1",
    })


def _parse_manifest(raw: bytes) -> ViewManifest:
    try:
        return ViewManifest.model_validate_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise WindowResolverInputError("source_identity_invalid", {"artifact": "view_manifest"}, category="input_integrity_error") from exc


def _interval(raw: object, *, observation_id: str, field: str) -> SourceIntervalV1:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise WindowResolverInputError("source_identity_invalid", {"observation_id": observation_id, "field": field}, category="input_integrity_error")
    try:
        return SourceIntervalV1(lo=raw[0], hi=raw[1])
    except ValueError as exc:
        raise WindowResolverInputError("source_identity_invalid", {"observation_id": observation_id, "field": field}, category="input_integrity_error") from exc


def _window_strokes(raw: bytes, entry: RequiredViewEntry):
    try:
        payload = json.loads(raw.decode("utf-8"))
        view = parse_reading_view(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise WindowResolverInputError("source_identity_invalid", {"input_id": entry.input_id, "artifact": "reading"}, category="input_integrity_error") from exc
    output_sha = hashlib.sha256(raw).hexdigest()
    for stroke in view.strokes:
        if stroke.pen != "window":
            continue
        geometry = stroke.geometry
        locator = source_locator(input_id=entry.input_id, observation_id=stroke.id, output_sha256=output_sha)
        if entry.view_type == "plan":
            yield PlanSourceWindowV1(channel="plan", source_locator=locator, source_input_id=entry.input_id,
                source_output_sha256=output_sha, observation_id=stroke.id, floor_ref=entry.floor_ref,
                world_x_interval=_interval(geometry.get("x_range_m"), observation_id=stroke.id, field="x_range_m"),
                world_y_interval=_interval(geometry.get("y_range_m"), observation_id=stroke.id, field="y_range_m"),
                positive_claims=("existence", "host", "along", "width"))
        elif entry.view_type == "elevation":
            # Elevation vertical span (sill→head) lives in the rect's y_range_m
            # (image-local vertical = height); there is no z_range contract field.
            z = geometry.get("y_range_m")
            yield ElevationSourceWindowV1(channel="elevation", source_locator=locator, source_input_id=entry.input_id,
                source_output_sha256=output_sha, observation_id=stroke.id,
                local_along_interval=_interval(geometry.get("x_range_m"), observation_id=stroke.id, field="x_range_m"),
                local_z_interval=None if z is None else _interval(z, observation_id=stroke.id, field="y_range_m"),
                positive_claims=("existence", "along", "width", "sill", "head", "appearance"))


def _catalog(*, manifest: ViewManifest, raw_reading_artifacts: Mapping[str, bytes]) -> tuple[SourceWindowV1, ...]:
    required = {entry.input_id: entry for entry in manifest.required_entries()}
    if set(raw_reading_artifacts) != set(required):
        raise WindowResolverInputError("source_identity_invalid", {"reading_inputs": sorted(raw_reading_artifacts), "required_inputs": sorted(required)}, category="input_integrity_error")
    rows: list[SourceWindowV1] = []
    for input_id in sorted(required):
        entry = required[input_id]
        if entry.view_type in ("plan", "elevation"):
            rows.extend(_window_strokes(raw_reading_artifacts[input_id], entry))
    _validate_catalog(rows, raw_parser=True)
    return tuple(sorted(rows, key=lambda item: (item.channel, item.source_input_id, item.observation_id)))


def _validate_catalog(rows: tuple[SourceWindowV1, ...] | list[SourceWindowV1], *, raw_parser: bool = False) -> None:
    locators = [item.source_locator for item in rows]
    observations = [(item.source_input_id, item.observation_id) for item in rows]
    if raw_parser and len(observations) != len(set(observations)):
        raise WindowResolverInputError("duplicate_source_observation", category="input_integrity_error")
    if len(locators) != len(set(locators)):
        raise WindowResolverInputError("duplicate_source_locator", category="input_integrity_error")
    if not raw_parser and len(observations) != len(set(observations)):
        raise WindowResolverInputError("duplicate_source_observation", category="input_integrity_error")


def verify_window_resolver_inputs(inputs: WindowResolverInputsV1) -> None:
    """Narrow verifier for already-parsed untrusted input wire (test/loader seam).

    It deliberately returns no verified marker: only the raw-artifact builder
    below can issue one.  Keeping this seam public lets loaders reject a
    syntactically valid but duplicate catalog before any marker exists.
    """
    if inputs.content_sha256 != canonical_sha256(_without_hash(inputs)):
        raise WindowResolverInputError("source_identity_invalid", {"artifact": "resolver_inputs"}, category="input_integrity_error")
    _validate_catalog(inputs.source_windows)
    by_locator = {row.source_locator: row for row in inputs.source_windows}
    for link in inputs.claim_links:
        row = by_locator.get(link.source_locator)
        if row is None:
            raise WindowResolverInputError("source_identity_invalid", {"source_locator": link.source_locator}, category="input_integrity_error")
        entry = inputs.view_manifest.entry_by_input_id(row.source_input_id)
        if not isinstance(entry, RequiredViewEntry):
            raise WindowResolverInputError("source_identity_invalid", {"input_id": row.source_input_id}, category="input_integrity_error")
        # Permission is intentionally checked before declaration/manifest
        # observability: it is a channel hard boundary, not a missing claim.
        permitted = ((row.channel == "plan" and link.claim in {"existence", "host", "along", "width"}) or
                     (row.channel == "elevation" and link.claim in {"existence", "along", "width", "sill", "head", "appearance"}))
        if not permitted:
            raise WindowResolverInputError("claim_permission_invalid", {"window_id": link.window_id, "claim": link.claim}, category="input_integrity_error")
        if link.claim not in row.positive_claims:
            raise WindowResolverInputError("source_claim_undeclared", {"window_id": link.window_id, "claim": link.claim}, category="input_integrity_error")
        if link.claim not in entry.opening_evidence.potentially_observable_claims:
            raise WindowResolverInputError("manifest_claim_not_observable", {"window_id": link.window_id, "claim": link.claim}, category="input_integrity_error")


def verify_window_resolver_inputs_against_raw_artifacts(
    inputs: WindowResolverInputsV1,
    *,
    raw_view_manifest_bytes: bytes,
    raw_reading_artifacts: Mapping[str, bytes],
) -> None:
    """Re-authenticate persisted resolver inputs against accepted raw sources."""
    verify_window_resolver_inputs(inputs)
    manifest = _parse_manifest(raw_view_manifest_bytes)
    if manifest != inputs.view_manifest:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "view_manifest"}, category="input_integrity_error"
        )
    rows = _catalog(manifest=manifest, raw_reading_artifacts=raw_reading_artifacts)
    if rows != inputs.source_windows:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "source_catalog"}, category="input_integrity_error"
        )
    facts = _check_direction_facts(
        manifest,
        inputs.elevation_direction_facts,
        raw_reading_artifacts,
    )
    if facts != inputs.elevation_direction_facts:
        raise WindowResolverInputError(
            "direction_fact_invalid", {"artifact": "direction_facts"}, category="input_integrity_error"
        )
    identities = tuple(
        ReadingArtifactIdentityV1(
            input_id=entry.input_id,
            expected_output_id=entry.expected_output_id,
            output_sha256=hashlib.sha256(raw_reading_artifacts[entry.input_id]).hexdigest(),
        )
        for entry in sorted(manifest.required_entries(), key=lambda item: item.input_id)
    )
    if identities != inputs.reading_artifacts:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "reading_artifacts"}, category="input_integrity_error"
        )


def build_window_source_offer(*, raw_view_manifest_bytes: bytes,
                              raw_reading_artifacts: Mapping[str, bytes]) -> WindowSourceOfferV1:
    manifest = _parse_manifest(raw_view_manifest_bytes)
    rows = _catalog(manifest=manifest, raw_reading_artifacts=raw_reading_artifacts)
    allowed = tuple((row.source_locator, row.positive_claims) for row in rows)
    payload = {"schema_version": "1", "view_manifest_sha256": manifest.content_sha256,
               "source_windows": [row.model_dump(mode="json") for row in rows],
               "allowed_claims_by_locator": [[loc, list(claims)] for loc, claims in allowed]}
    return WindowSourceOfferV1(schema_version="1", view_manifest_sha256=manifest.content_sha256,
        source_windows=rows, allowed_claims_by_locator=allowed, content_sha256=canonical_sha256(payload))


@dataclass(frozen=True)
class ObservationReferenceCatalogEntry:
    """One legal ``<expected_output_id>/<observation_id>`` a correction draw
    may cite in ``source_ids`` — the model-facing counterpart of a
    :class:`SourceWindowV1` row, with the internal locator hash stripped out
    (the model must never see or copy a ``src:`` hash)."""

    reference: str
    allowed_claims: tuple[str, ...]


def derive_observation_reference_catalog(
    *, raw_view_manifest_bytes: bytes, raw_reading_artifacts: Mapping[str, bytes],
) -> tuple[ObservationReferenceCatalogEntry, ...]:
    """The single, mechanically-derived catalogue of legal observation
    references for this run's reading artifacts.

    Built from the exact same :func:`_catalog` (and therefore the same
    ``source_locator`` computation) that :func:`_translate_observation_reference`
    validates against — the prompt-facing listing and the enforced catalogue
    can never diverge because both are read off this one function's output.
    """
    manifest = _parse_manifest(raw_view_manifest_bytes)
    rows = _catalog(manifest=manifest, raw_reading_artifacts=raw_reading_artifacts)
    expected_output_id_by_input = {entry.input_id: entry.expected_output_id for entry in manifest.required_entries()}
    return tuple(
        ObservationReferenceCatalogEntry(
            reference=f"{expected_output_id_by_input[row.source_input_id]}/{row.observation_id}",
            allowed_claims=row.positive_claims,
        )
        for row in rows
    )


def format_observation_reference_catalog(entries: tuple[ObservationReferenceCatalogEntry, ...]) -> str:
    """Human-readable prompt text for :func:`derive_observation_reference_catalog`.

    Never emits a ``src:`` locator or a 64-hex hash: only the reference form
    the model can actually produce (and its allowed claims) is shown.
    """
    if not entries:
        return "(no window observations found in this run's reading artifacts)"
    return "\n".join(
        f"- {entry.reference}: allowed claims = [{', '.join(entry.allowed_claims)}]"
        for entry in entries
    )


def build_observation_reference_catalog_from_run(*, run_dir: Path, reading_dir: Path) -> str | None:
    """Prompt-facing catalog listing for a run's correction-draw guidance.

    Returns ``None`` when the view manifest (or one of its required reading
    artifacts) is not yet on disk — this is advisory prompt content only;
    the enforcement path (`build_verified_window_inputs_from_run` ->
    `build_verified_window_resolver_inputs` -> `_claim_links`) independently
    re-derives and re-validates everything after the draw regardless of
    whether this listing was shown, so a missing catalog here weakens
    guidance, never the contract.
    """
    from src.agent.execution.run_meta import run_meta_path
    from src.agent.execution.view_manifest import VIEW_MANIFEST_NAME

    manifest_path = run_meta_path(Path(run_dir), VIEW_MANIFEST_NAME)
    if not manifest_path.is_file():
        return None
    raw_manifest = manifest_path.read_bytes()
    try:
        manifest = _parse_manifest(raw_manifest)
    except WindowResolverInputError:
        return None
    raw_readings: dict[str, bytes] = {}
    for entry in manifest.required_entries():
        path = Path(reading_dir) / f"{entry.expected_output_id}.json"
        if not path.is_file():
            return None
        raw_readings[entry.input_id] = path.read_bytes()
    try:
        entries = derive_observation_reference_catalog(
            raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=raw_readings,
        )
    except WindowResolverInputError:
        return None
    return format_observation_reference_catalog(entries)


def derive_manifest_direction_facts(
    *,
    raw_view_manifest_bytes: bytes,
    raw_reading_artifacts: Mapping[str, bytes],
) -> tuple[ElevationDirectionFactV1, ...]:
    """Derive ring-free facts for manifest-declared building-axis elevations.

    True-azimuth/unknown entries require the separately verified orientation
    sidecar and therefore fail closed here instead of inventing a direction.
    """
    manifest = _parse_manifest(raw_view_manifest_bytes)
    facts: list[ElevationDirectionFactV1] = []
    for entry in manifest.required_entries():
        if entry.view_type != "elevation":
            continue
        if entry.direction_semantics != "building_axis" or entry.building_view_direction is None:
            raise WindowResolverInputError(
                "direction_fact_invalid",
                {"input_id": entry.input_id, "reason": "verified_orientation_sidecar_required"},
                category="input_integrity_error",
            )
        try:
            reading = parse_reading_view(
                json.loads(raw_reading_artifacts[entry.input_id].decode("utf-8"))
            )
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise WindowResolverInputError(
                "direction_fact_invalid", {"input_id": entry.input_id, "artifact": "reading"}, category="input_integrity_error"
            ) from exc
        mirrored = False
        local_x_positive = "image_left_to_right"
        if reading.facade is not None:
            if isinstance(reading.facade.mirrored, bool):
                mirrored = reading.facade.mirrored
            if reading.facade.local_x_positive in {
                "image_left_to_right", "image_right_to_left",
            }:
                local_x_positive = reading.facade.local_x_positive
        facts.append(ElevationDirectionFactV1(
            input_id=entry.input_id,
            resolved_building_direction=entry.building_view_direction,
            resolution_source="manifest_building_axis",
            mirrored=mirrored,
            local_x_positive=local_x_positive,
            orientation_output_hash=None,
            adapter_version=None,
            view_manifest_sha256=manifest.content_sha256,
        ))
    return tuple(sorted(facts, key=lambda fact: fact.input_id))


def build_verified_window_inputs_from_run(
    *,
    producer_draw: CorrectedGeometryV3,
    run_dir: Path,
    reading_dir: Path,
) -> VerifiedWindowResolverInputs:
    """Production run-directory adapter for the unique raw-input builder."""
    from src.agent.execution.run_meta import run_meta_path
    from src.agent.execution.view_manifest import VIEW_MANIFEST_NAME

    verify_reading_stage_root_against_accepted_attempt(run_dir, reading_dir)
    manifest_path = run_meta_path(Path(run_dir), VIEW_MANIFEST_NAME)
    if not manifest_path.is_file():
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "view_manifest", "path": str(manifest_path)}, category="input_integrity_error"
        )
    raw_manifest = manifest_path.read_bytes()
    manifest = _parse_manifest(raw_manifest)
    raw_readings: dict[str, bytes] = {}
    for entry in manifest.required_entries():
        path = Path(reading_dir) / f"{entry.expected_output_id}.json"
        if not path.is_file():
            raise WindowResolverInputError(
                "source_identity_invalid", {"input_id": entry.input_id, "path": str(path)}, category="input_integrity_error"
            )
        raw_readings[entry.input_id] = path.read_bytes()
    facts = derive_manifest_direction_facts(
        raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=raw_readings,
    )
    return build_verified_window_resolver_inputs(
        producer_draw=producer_draw,
        raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=raw_readings,
        elevation_direction_facts=facts,
    )


def verify_reading_stage_root_against_accepted_attempt(
    run_dir: Path,
    reading_dir: Path,
) -> None:
    """Bind flat reading inputs to 0_reading's accepted attempt when present.

    ``StageRunner`` archives a reading draw as one JSON object keyed by each
    ``*_view.json`` stem.  Flat files remain convenience mirrors of the latest
    draw, so reconstruct that exact writer payload and compare its byte hash to
    the accepted record.  Runs without an accepted reading attempt retain the
    standalone/exploratory behavior.
    """
    from src.agent.execution.manifest import hash_bytes, hash_text, load_run_manifest

    manifest = load_run_manifest(Path(run_dir))
    if manifest is None:
        return
    accepted = manifest.accepted("0_reading")
    if accepted is None:
        return
    attempt_path = (
        Path(run_dir)
        / "0_reading"
        / "attempts"
        / f"{accepted.accepted_attempt:03d}"
        / "output.json"
    )
    if not attempt_path.is_file():
        raise WindowResolverInputError(
            "source_identity_invalid",
            {"artifact": "accepted_reading", "path": str(attempt_path)},
            category="input_integrity_error",
        )
    try:
        accepted_bytes = attempt_path.read_bytes()
        if hash_bytes(accepted_bytes) != accepted.output_hash:
            raise WindowResolverInputError(
                "source_identity_invalid",
                {"artifact": "accepted_reading", "reason": "output_hash_mismatch"},
                category="input_integrity_error",
            )
        current = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(Path(reading_dir).glob("*_view.json"))
        }
        current_text = json.dumps(current, indent=2, ensure_ascii=False)
    except WindowResolverInputError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "reading_stage_root"}, category="input_integrity_error"
        ) from exc
    if hash_text(current_text) != accepted.output_hash:
        raise WindowResolverInputError(
            "source_identity_invalid",
            {"artifact": "reading_stage_root", "reason": "accepted_attempt_mismatch"},
            category="input_integrity_error",
        )


def _check_direction_facts(manifest: ViewManifest, facts: tuple[ElevationDirectionFactV1, ...],
                           raw_reading_artifacts: Mapping[str, bytes]) -> tuple[ElevationDirectionFactV1, ...]:
    expected = {entry.input_id: entry for entry in manifest.required_entries() if entry.view_type == "elevation"}
    got = {fact.input_id: fact for fact in facts}
    if len(got) != len(facts) or set(got) != set(expected):
        raise WindowResolverInputError("direction_fact_invalid", {"declared": sorted(got), "required": sorted(expected)}, category="input_integrity_error")
    out = []
    for input_id, entry in expected.items():
        fact = got[input_id]
        if fact.view_manifest_sha256 != manifest.content_sha256:
            raise WindowResolverInputError("direction_fact_invalid", {"input_id": input_id, "field": "view_manifest_sha256"}, category="input_integrity_error")
        try:
            reading = parse_reading_view(json.loads(raw_reading_artifacts[input_id].decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise WindowResolverInputError("direction_fact_invalid", {"input_id": input_id, "artifact": "reading"}, category="input_integrity_error") from exc
        if reading.facade is not None:
            mirrored = reading.facade.mirrored
            if isinstance(mirrored, bool) and (fact.mirrored != mirrored or fact.local_x_positive != reading.facade.local_x_positive):
                raise WindowResolverInputError("direction_fact_invalid", {"input_id": input_id, "field": "reading_facade"}, category="input_integrity_error")
        if fact.resolution_source == "manifest_building_axis":
            if (entry.direction_semantics != "building_axis" or
                    fact.resolved_building_direction != entry.building_view_direction or
                    fact.orientation_output_hash is not None or fact.adapter_version is not None):
                raise WindowResolverInputError("direction_fact_invalid", {"input_id": input_id}, category="input_integrity_error")
        elif (entry.direction_semantics not in ("true_azimuth", "unknown") or
              fact.orientation_output_hash is None or fact.adapter_version is None):
            raise WindowResolverInputError("direction_fact_invalid", {"input_id": input_id}, category="input_integrity_error")
        out.append(fact)
    return tuple(sorted(out, key=lambda item: item.input_id))


def _producer_preflight(producer: CorrectedGeometryV3) -> None:
    # These two are model_draw_error (not input_integrity_error): a
    # correction draw pre-filling deterministic-core-only fields is the LLM
    # writing outside its scope, not a broken upstream artifact — retrying
    # the draw can fix it.
    if producer.facade_segments or any(window.facade_segment_id is not None for window in producer.windows):
        raise WindowResolverInputError("producer_segment_ref_prefilled", category="model_draw_error")
    if any(isinstance(row, dict) and row.get("kind") == "window_host_resolution"
           for rows in (producer.corrections, producer.conflicts, producer.unsupported) for row in rows):
        raise WindowResolverInputError("producer_resolver_audit_prefilled", category="model_draw_error")


_SOURCE_LOCATOR_PATTERN = re.compile(r"^src:[0-9a-f]{64}$")


def _translate_observation_reference(
    reference: str,
    *,
    rows: tuple[SourceWindowV1, ...],
    manifest: ViewManifest,
    window_id: str,
    claim: str,
) -> str:
    """Translate a correction draw's cited source into its internal locator.

    F-7 (2026-08-05): a correction draw cannot see or compute the 64-hex
    locator hash (it embeds the reading-artifact byte hash, which the LLM has
    no access to) — so it must cite what it CAN see: the reading vector
    file's own name and the observation ``id`` printed in that file's
    ``strokes`` array, as ``<expected_output_id>/<observation_id>`` (e.g.
    ``1f_view/S11``). This is the sole translation point; the resulting
    locator is then validated exactly as before by every existing
    ``_claim_links`` check below — nothing downstream is relaxed.

    Two forms are accepted:
      1. An already-valid ``src:<64hex>`` locator — passed through unchanged
         (backward compatibility for callers/fixtures that already carry a
         real locator, e.g. computed directly via :func:`source_locator`).
      2. ``<expected_output_id>/<observation_id>`` — the only form a live
         draw can produce.
    Anything else (no ``/``, an unknown view name, or an unknown observation
    id within a known view) is a named, distinct model-draw error — never a
    silent guess at which view/observation was meant.
    """
    if _SOURCE_LOCATOR_PATTERN.match(reference):
        return reference
    parts = reference.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise WindowResolverInputError(
            "observation_reference_ambiguous",
            {"window_id": window_id, "claim": claim, "source_ids": reference},
            category="model_draw_error",
        )
    view_name, observation_id = parts
    input_id = manifest.expected_output_ids().get(view_name)
    if input_id is None:
        raise WindowResolverInputError(
            "observation_reference_view_unknown",
            {"window_id": window_id, "claim": claim, "expected_output_id": view_name},
            category="model_draw_error",
        )
    for row in rows:
        if row.source_input_id == input_id and row.observation_id == observation_id:
            return row.source_locator
    raise WindowResolverInputError(
        "observation_reference_observation_unknown",
        {"window_id": window_id, "claim": claim, "expected_output_id": view_name, "observation_id": observation_id},
        category="model_draw_error",
    )


def _claim_links(producer: CorrectedGeometryV3, rows: tuple[SourceWindowV1, ...], manifest: ViewManifest) -> tuple[WindowClaimSourceLinkV1, ...]:
    by_locator = {row.source_locator: row for row in rows}
    used_existence: set[str] = set()
    links: list[WindowClaimSourceLinkV1] = []
    for window in producer.windows:
        provenance = window.provenance or {}
        existence = provenance.get("existence")
        if existence is None or not existence.source_ids or existence.provenance == "assumed":
            raise WindowResolverInputError("source_identity_invalid", {"window_id": window.id, "claim": "existence"}, category="model_draw_error")
        for claim, detail in provenance.items():
            for reference in detail.source_ids:
                locator = _translate_observation_reference(
                    reference, rows=rows, manifest=manifest, window_id=window.id, claim=claim,
                )
                source = by_locator.get(locator)
                if source is None:
                    raise WindowResolverInputError("source_identity_invalid", {"window_id": window.id, "source_locator": locator}, category="model_draw_error")
                if claim not in source.positive_claims:
                    raise WindowResolverInputError("source_claim_undeclared", {"window_id": window.id, "claim": claim}, category="model_draw_error")
                entry = manifest.entry_by_input_id(source.source_input_id)
                if not isinstance(entry, RequiredViewEntry):
                    raise WindowResolverInputError("source_identity_invalid", {
                        "window_id": window.id, "input_id": source.source_input_id,
                    }, category="input_integrity_error")
                if claim not in entry.opening_evidence.potentially_observable_claims:
                    raise WindowResolverInputError("manifest_claim_not_observable", {"window_id": window.id, "claim": claim}, category="model_draw_error")
                permitted = ((source.channel == "plan" and claim in {"existence", "host", "along", "width"}) or
                             (source.channel == "elevation" and claim in {"existence", "along", "width", "sill", "head", "appearance"}))
                if not permitted:
                    raise WindowResolverInputError("claim_permission_invalid", {"window_id": window.id, "claim": claim}, category="model_draw_error")
                if claim == "existence":
                    if locator in used_existence:
                        raise WindowResolverInputError("source_identity_invalid", {"source_locator": locator, "reason": "multiple_windows"}, category="model_draw_error")
                    used_existence.add(locator)
                links.append(WindowClaimSourceLinkV1(window_id=window.id, claim=claim, source_locator=locator))
    order = {claim: index for index, claim in enumerate(("existence", "host", "along", "width", "sill", "head", "appearance"))}
    return tuple(sorted(links, key=lambda link: (link.window_id, order[link.claim], link.source_locator)))


def _check_floor_order(manifest: ViewManifest, producer: CorrectedGeometryV3,
                       rows: tuple[SourceWindowV1, ...], links: tuple[WindowClaimSourceLinkV1, ...]) -> None:
    refs = sorted({entry.floor_ref for entry in manifest.required_entries() if entry.view_type == "plan"})
    if refs != list(range(1, len(refs) + 1)) or len(refs) != len(producer.floors):
        raise WindowResolverInputError("manifest_floor_ref_non_contiguous", category="input_integrity_error")
    floor_by_id = {floor.id: floor for floor in producer.floors}
    rank = {floor.id: index for index, floor in enumerate(sorted(producer.floors, key=lambda floor: floor.z_floor), start=1)}
    windows = {window.id: window for window in producer.windows}
    for row in rows:
        if isinstance(row, PlanSourceWindowV1):
            for link in (link for link in links if link.source_locator == row.source_locator):
                if rank[windows[link.window_id].floor_id] != row.floor_ref:
                    raise WindowResolverInputError("floor_ref_window_mismatch", {"window_id": link.window_id}, category="model_draw_error")
        elif isinstance(row, ElevationSourceWindowV1) and row.local_z_interval is not None:
            candidates = [floor for floor in producer.floors
                          if row.local_z_interval.lo >= floor.z_floor and row.local_z_interval.hi <= floor.z_floor + floor.ceiling_height]
            for link in (link for link in links if link.source_locator == row.source_locator):
                if len(candidates) != 1 or windows[link.window_id].floor_id != candidates[0].id:
                    raise WindowResolverInputError("elevation_floor_mismatch", {"window_id": link.window_id,
                        "candidate_floors": [floor.id for floor in candidates]}, category="model_draw_error")
    if set(floor_by_id) != set(rank):  # defensive, makes the mapping invariant explicit
        raise WindowResolverInputError("floor_ref_window_mismatch", category="input_integrity_error")


def build_verified_window_resolver_inputs(*, producer_draw: CorrectedGeometryV3,
                                          raw_view_manifest_bytes: bytes,
                                          raw_reading_artifacts: Mapping[str, bytes],
                                          elevation_direction_facts: tuple[ElevationDirectionFactV1, ...]) -> VerifiedWindowResolverInputs:
    producer = CorrectedGeometryV3.model_validate(producer_draw.model_dump(mode="json"))
    _producer_preflight(producer)
    manifest = _parse_manifest(raw_view_manifest_bytes)
    rows = _catalog(manifest=manifest, raw_reading_artifacts=raw_reading_artifacts)
    facts = _check_direction_facts(manifest, elevation_direction_facts, raw_reading_artifacts)
    links = _claim_links(producer, rows, manifest)
    _check_floor_order(manifest, producer, rows, links)
    producer_bytes = canonical_json_bytes(producer.model_dump(mode="json"))
    artifacts = tuple(ReadingArtifactIdentityV1(input_id=entry.input_id, expected_output_id=entry.expected_output_id,
        output_sha256=hashlib.sha256(raw_reading_artifacts[entry.input_id]).hexdigest())
        for entry in sorted(manifest.required_entries(), key=lambda item: item.input_id))
    payload = {"schema_version": "1", "claims_vocab_version": CLAIMS_VOCAB_VERSION,
               "producer_draw_sha256": hashlib.sha256(producer_bytes).hexdigest(),
               "view_manifest": manifest.model_dump(mode="json"),
               "reading_artifacts": [item.model_dump(mode="json") for item in artifacts],
               "elevation_direction_facts": [item.model_dump(mode="json") for item in facts],
               "source_windows": [item.model_dump(mode="json") for item in rows],
               "claim_links": [item.model_dump(mode="json") for item in links]}
    inputs = WindowResolverInputsV1(schema_version="1", claims_vocab_version=CLAIMS_VOCAB_VERSION,
        producer_draw_sha256=payload["producer_draw_sha256"], view_manifest=manifest,
        reading_artifacts=artifacts, elevation_direction_facts=facts, source_windows=rows,
        claim_links=links, content_sha256=canonical_sha256(payload))
    raw_inputs = canonical_json_bytes(inputs.model_dump(mode="json"))
    return VerifiedWindowResolverInputs(inputs=inputs, raw_inputs_bytes=raw_inputs,
        producer_draw_canonical_bytes=producer_bytes, raw_view_manifest_bytes=raw_view_manifest_bytes,
        raw_reading_artifacts=tuple((key, raw_reading_artifacts[key]) for key in sorted(raw_reading_artifacts)))


def verify_window_resolver_inputs_artifact(
    raw_artifact_bytes: bytes,
) -> VerifiedWindowResolverInputs:
    """Rebuild a verified marker solely from a self-contained attempt artifact.

    Direction facts for the currently supported production building-axis path
    are independently re-derived from the raw manifest/readings.  A future
    true-azimuth adapter must embed and verify its own raw orientation sidecar;
    it may not fall back to trusting the persisted fact tuple.
    """
    artifact = WindowResolverInputsArtifactV1.model_validate_json(raw_artifact_bytes)
    canonical = canonical_json_bytes(artifact.model_dump(mode="json"))
    if raw_artifact_bytes != canonical:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "window_resolver_inputs_canonical_bytes"}, category="input_integrity_error",
        )
    raw_readings = {
        row.input_id: bytes(row.raw_bytes) for row in artifact.raw_reading_artifacts
    }
    fresh_facts = derive_manifest_direction_facts(
        raw_view_manifest_bytes=bytes(artifact.raw_view_manifest_bytes),
        raw_reading_artifacts=raw_readings,
    )
    producer = CorrectedGeometryV3.model_validate_json(
        bytes(artifact.producer_draw_canonical_bytes)
    )
    rebuilt = build_verified_window_resolver_inputs(
        producer_draw=producer,
        raw_view_manifest_bytes=bytes(artifact.raw_view_manifest_bytes),
        raw_reading_artifacts=raw_readings,
        elevation_direction_facts=fresh_facts,
    )
    if rebuilt.inputs != artifact.inputs:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "resolver_inputs_replay"}, category="input_integrity_error",
        )
    return rebuilt


DirectionBindingErrorCode = Literal["direction_binding_ring_invalid", "direction_binding_ring_incompatible"]


class WindowDirectionBindingError(ValueError):
    def __init__(self, code: DirectionBindingErrorCode, context: Mapping[str, object]):
        self.code = code
        self.context = dict(context)
        super().__init__(f"{code}: {self.context}")


def _frame_hash(*, input_id: str, family: str, fingerprint: str, axis: str, sign: int,
                origin: float, mirrored: bool, local: str) -> str:
    return canonical_sha256({"schema": "view_projection_binding_v1", "input_id": input_id,
        "resolved_building_direction": family, "source_footprint_fingerprint": fingerprint,
        "world_axis": axis, "sign": sign, "along_origin": origin, "mirrored": mirrored,
        "local_x_positive": local})


def materialize_current_ring_va_elevation_bindings(*, geom: CorrectedGeometryV3, manifest: ViewManifest,
                                                    direction_facts: tuple[ElevationDirectionFactV1, ...],
                                                    visibility_tolerances: VisibilityTolerances) -> tuple[VaElevationViewBindingV1, ...]:
    """Fresh, non-cached 13-field Va bindings for exactly ``geom``'s ring."""
    try:
        validate_materialized_facade_segments(geom, tolerances=visibility_tolerances)
    except FacadeVisibilityInvariantError as exc:
        raise WindowDirectionBindingError("direction_binding_ring_invalid", {"upstream_error": exc.code, **exc.context}) from exc
    # Facts are authenticated by ``build_verified_window_resolver_inputs``.
    # This helper deliberately rechecks only totality/manifest identity and
    # derives every ring-dependent field afresh from ``geom``.
    facts = tuple(sorted(direction_facts, key=lambda item: item.input_id))
    expected = {entry.input_id: entry for entry in manifest.required_entries() if entry.view_type == "elevation"}
    if {fact.input_id for fact in facts} != set(expected) or len({fact.input_id for fact in facts}) != len(facts):
        raise WindowDirectionBindingError("direction_binding_ring_invalid", {"reason": "direction_fact_totality"})
    for fact in facts:
        entry = expected[fact.input_id]
        if fact.view_manifest_sha256 != manifest.content_sha256:
            raise WindowDirectionBindingError("direction_binding_ring_invalid", {"input_id": fact.input_id, "reason": "manifest_identity"})
        if fact.resolution_source == "manifest_building_axis":
            valid = (entry.direction_semantics == "building_axis" and
                     fact.resolved_building_direction == entry.building_view_direction and
                     fact.orientation_output_hash is None and fact.adapter_version is None)
        else:
            valid = (entry.direction_semantics in ("true_azimuth", "unknown") and
                     fact.orientation_output_hash is not None and fact.adapter_version is not None)
        if not valid:
            raise WindowDirectionBindingError("direction_binding_ring_invalid", {"input_id": fact.input_id, "reason": "direction_fact_invalid"})
    floors = {floor.id: floor for floor in geom.floors}
    output = []
    for fact in facts:
        family = fact.resolved_building_direction
        per_floor = []
        for floor_id, floor in sorted(floors.items()):
            fingerprint = floor_footprint_fingerprint(geom, floor)
            segments = [segment for segment in geom.facade_segments if segment.floor_id == floor_id and segment.facade_family == family]
            if not segments:
                raise WindowDirectionBindingError("direction_binding_ring_invalid", {"floor_id": floor_id, "input_id": fact.input_id})
            if any(segment.source_footprint_fingerprint != fingerprint for segment in segments):
                raise WindowDirectionBindingError("direction_binding_ring_invalid", {"floor_id": floor_id, "input_id": fact.input_id,
                    "declared_fingerprint": [segment.source_footprint_fingerprint for segment in segments], "recomputed_fingerprint": fingerprint})
            per_floor.append((floor_id, fingerprint, (min(s.world_along_interval.lo for s in segments), max(s.world_along_interval.hi for s in segments))))
        fingerprints = {item[1] for item in per_floor}; extents = {item[2] for item in per_floor}
        if len(fingerprints) != 1 or len(extents) != 1:
            raise WindowDirectionBindingError("direction_binding_ring_incompatible", {"input_id": fact.input_id,
                "floor_ids": [item[0] for item in per_floor], "fingerprints": [item[1] for item in per_floor], "family_extents": [item[2] for item in per_floor]})
        fingerprint = per_floor[0][1]; lo, hi = per_floor[0][2]
        axis = _AXIS[family]
        flip = fact.mirrored ^ (fact.local_x_positive == "image_right_to_left")
        sign = -_BASE_SIGN[family] if flip else _BASE_SIGN[family]
        origin = lo if sign == 1 else hi
        output.append(VaElevationViewBindingV1(input_id=fact.input_id, resolved_building_direction=family,
            resolution_source=fact.resolution_source, view_manifest_sha256=manifest.content_sha256,
            orientation_output_hash=fact.orientation_output_hash, adapter_version=fact.adapter_version,
            source_footprint_fingerprint=fingerprint, world_axis=axis, sign=sign, along_origin=origin,
            mirrored=fact.mirrored, local_x_positive=fact.local_x_positive,
            frame_transform_sha256=_frame_hash(input_id=fact.input_id, family=family, fingerprint=fingerprint,
                axis=axis, sign=sign, origin=origin, mirrored=fact.mirrored, local=fact.local_x_positive)))
    return tuple(sorted(output, key=lambda item: item.input_id))


__all__ = [
    "CURRENT_RING_BINDING_HELPER_VERSION", "ElevationDirectionFactV1", "ElevationSourceWindowV1",
    "ObservationReferenceCatalogEntry",
    "PlanSourceWindowV1", "RawReadingArtifactV1", "ReadingArtifactIdentityV1", "SourceIntervalV1", "VerifiedWindowResolverInputs",
    "WindowClaimSourceLinkV1", "WindowDirectionBindingError", "WindowResolverInputError", "WindowResolverInputsV1",
    "WindowResolverInputsArtifactV1", "WindowSourceErrorCategory", "WindowSourceOfferV1",
    "build_observation_reference_catalog_from_run",
    "build_verified_window_inputs_from_run",
    "build_verified_window_resolver_inputs", "build_window_source_offer",
    "build_window_resolver_inputs_artifact",
    "derive_manifest_direction_facts",
    "derive_observation_reference_catalog", "format_observation_reference_catalog",
    "materialize_current_ring_va_elevation_bindings", "source_locator", "verify_window_resolver_inputs",
    "serialize_window_resolver_inputs_artifact", "verify_window_resolver_inputs_against_raw_artifacts",
    "verify_window_resolver_inputs_artifact",
]
