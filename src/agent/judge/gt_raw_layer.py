"""GT **raw layer** reader + mechanical reproduction gate — judge② / human side ONLY.

The user's 2026-08-26 ruling splits gt into three layers: a RAW layer (a faithful
transcription of the drawing, deviations included), an irregularity list, and a
DERIVED answer layer.  This module exposes the first one.

The raw layer is already on disk and has been since the converter was written:
``case_tests/test_baseline/gt/<case>/review/conversion_report.json`` carries, for
every zone edge, ``p1/p2/basis/thickness_m/offset_m/source_handles`` plus the
thickness proof handles.  R-6 ("measured it, used it, threw it away when saving")
is therefore **inaccurate** and is corrected here: it is *saved*, but until now
(a) no scoring path read it and (b) it sits **outside the human signature**.

⛔ Same lock as :mod:`src.agent.judge.gt` (gt iron law, CLAUDE.md §1.5#4): only
the gate② judge and humans may import this.  gate① checks and the stage
executors must stay blind.  ``tests/test_gt_discipline.py`` enforces it.

## Why a reproduction gate at all (G1-b)

``tarch_review_bundle._RUNTIME_BUNDLE_FILES`` lists ``conversion_report.json``
among the *non-indexed* runtime files, so ``review_index.json`` never hashes it
and the human ``review_ack.json`` does not cover it.  Its trustworthiness can
therefore not come from the signature.  It can only come from *reproducing* it
mechanically out of inputs that ARE signed:

    review_ack.json  --signs-->  source.dxf sha256   (byte hash)
                     --signs-->  request_sha256      (RECOMPUTED from content,
                                                      never the declared field)

Re-running the converter on those two and comparing the result field-by-field is
what :func:`verify_raw_layer_reproduction` does.

⛔ Content fields, never bytes.  The converter's normalized-DXF bytes (and hence
``normalized_dxf_sha256``) depend on Python hash randomisation; comparing bytes
would be a guaranteed false red.  Measured on 2026-08-27: the content fields are
identical across PYTHONHASHSEED 1 / 7 / 12345.

## The two reds are kept apart (G1-b, ⭐)

``implementation_drift``  the converter/config/extractor fingerprints recorded in
                          the signed artefacts no longer match this tree.  The
                          on-disk report may still be exactly what the reviewer
                          approved; it is *this tree* that moved.
``content_mismatch``      the fingerprints all match, so the same implementation
                          was re-run — and it did not produce what is on disk.
                          That points at the artefact.

The fingerprint check runs FIRST and returns early, so a drifted tree can never
be reported as a suspect artefact.

### Which fingerprints are fatal, and why exactly those

The **fatal** set is the three the report *itself* binds: ``converter_sha256``
(= ``tarch_normalize.py``), ``judge_config_sha256`` and ``vg_config_sha256``.
That mirrors the producer's own declaration of "what implementation made me",
which is the standing rule for a recomputing gate: a check whose definition does
not mirror the producer's measures the difference between two opinions.

The signed ``gt.json`` generator block carries three more —
``extractor_sha256`` / ``validator_sha256`` / ``vg_implementation_sha256`` — but
those are the fingerprints of a *different* artefact.  They are reported as an
**advisory**, never as a fatal drift, for a measured reason: ``extractor_sha256``
is a group hash over ``gt_extraction.py`` + ``gt_manifest.py`` +
``scripts/tool_scripts/gt_from_dxf.py``, and the last of those is a CLI entry
point that the conversion import closure was MEASURED (2026-08-27) not to load
at all.  Treating that group as fatal makes a CLI-only edit — precisely what
commit ``91ae82d`` did on 2026-08-25, adding five lines of ``sys.path``
bootstrap — masquerade as converter drift.  A fingerprint that is wider than the
question is the same false-red species as comparing bytes.

⚠️ **Declared blind spot.**  ``gt_extraction.py``, ``gt_manifest.py`` and
``tarch_converter_schema.py`` ARE inside the conversion import closure but have
no exactly-scoped signed fingerprint.  Drift confined to them is therefore
reported as ``content_mismatch``, not ``implementation_drift`` — the difference
is still caught loudly, but its *attribution* is wrong.  This is a genuine
residual hole, written down rather than papered over.

## Nothing degrades silently (G1-c)

:class:`RawLayerTrust` always says what the trust root actually is.  A raw layer
whose reproduction was never attempted reports ``reproduction=None`` and
``status="not_attempted"`` — it never reads as "verified".  The same holds when
the signed inputs cannot be found (``inputs_unavailable``).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from .gt import DEFAULT_GT_DIR, case_gt_dir
from .gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from .tarch_converter_schema import (GT_SOURCES_ROOT, ConversionReportV1,
                                     HumanReviewAckV1, TarchConversionRequestV1,
                                     ZoneEdgeReportV1, compute_request_sha256,
                                     resolve_converter_tooling)

__all__ = [
    "RawEdge", "GtRawLayer", "RawLayerTrust", "ReproductionVerdict",
    "load_gt_raw_layer", "verify_raw_layer_reproduction",
    "SIGNATURE_DEPENDENT_POINTERS", "HUMAN_REVIEW_GATE_IDS",
]


# --------------------------------------------------------------------------- #
# What is allowed to differ between the on-disk report and a fresh re-run
# --------------------------------------------------------------------------- #
# ⭐ Derived from the PRODUCER's own declaration, NOT from an observed diff.
# ``tarch_review_bundle.sign_review_bundle`` requires every gate to be green
# *except* ``{6, 10}`` at signing time -- i.e. the producer itself names G6 and
# G10 as the gates whose verdict is a function of the human signature rather
# than of the drawing.  A fresh re-run happens in a work dir with no
# review_ack.json / review_index.json, so exactly those two are red there.
HUMAN_REVIEW_GATE_IDS = frozenset({"G6", "G10"})

# ``ConversionReportV1._status_geom_contract`` makes both of these a mechanical
# CONSEQUENCE of a red gate: status is BLOCKED, and a non-PASS report is not
# allowed to carry ``normalized_dxf_sha256``.
SIGNATURE_DEPENDENT_POINTERS = frozenset({"/status", "/normalized_dxf_sha256"})


def _pointer_is_signature_dependent(pointer: str) -> bool:
    """True only for differences that the human signature itself explains.

    Everything else -- every wall, opening, cavity, zone edge, diagnostic, the
    provenance hashes, and even G6's *geometric* evidence -- must match.
    """
    if pointer in SIGNATURE_DEPENDENT_POINTERS:
        return True
    parts = pointer.split("/")
    if len(parts) < 3 or parts[1] != "gates" or parts[2] not in HUMAN_REVIEW_GATE_IDS:
        return False
    tail = parts[3:]
    if parts[2] == "G10":
        # G10 *is* the signature check; its whole evidence body is about the ack.
        return tail[:1] in ([], ["passed"], ["evidence"])
    # G6 is a real geometric gate that merely needs a human to confirm the
    # near-threshold faces.  Only its verdict and the confirmation stamp may
    # move; cavity counts, areas and centroids must still reproduce.
    if tail == ["passed"]:
        return True
    return (len(tail) >= 3 and tail[:2] == ["evidence", "views"]
            and (tail[3:] == ["passed"] or tail[3:] == ["evidence", "human_confirmation"]))


# --------------------------------------------------------------------------- #
# Typed raw-layer view
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RawEdge:
    """One zone-boundary edge exactly as the converter transcribed it."""
    zone_id: str
    floor_id: str
    edge_index: int
    edge: ZoneEdgeReportV1

    @property
    def p1(self) -> tuple[float, float]:
        return tuple(self.edge.p1)  # type: ignore[return-value]

    @property
    def p2(self) -> tuple[float, float]:
        return tuple(self.edge.p2)  # type: ignore[return-value]

    @property
    def basis(self) -> str:
        return self.edge.basis

    @property
    def thickness_m(self) -> float:
        return self.edge.thickness_m

    @property
    def offset_m(self) -> float:
        return self.edge.offset_m

    @property
    def source_handles(self) -> list[str]:
        return list(self.edge.source_handles)


@dataclass(frozen=True)
class ReproductionVerdict:
    """Outcome of re-deriving the raw layer from the signed inputs."""
    status: Literal["reproduced", "implementation_drift", "content_mismatch",
                    "inputs_unavailable"]
    detail: str
    #: JSON pointers whose values differ, for ``content_mismatch``.
    differing_pointers: tuple[str, ...] = ()
    #: Fingerprint names that moved, for ``implementation_drift``.
    drifted_fingerprints: tuple[str, ...] = ()
    #: Fingerprints of NEIGHBOURING artefacts that moved.  Never fatal here (see
    #: the module docstring), but never swallowed either.
    advisory_drifted_fingerprints: tuple[str, ...] = ()

    @property
    def reproduced(self) -> bool:
        return self.status == "reproduced"


@dataclass(frozen=True)
class RawLayerTrust:
    """⭐ G1-c: what this layer's trust actually rests on — stated, not assumed.

    ``human_signed`` is always False today and is *derived* (by reading the
    signed file inventory), not asserted: if a future re-sign adds
    conversion_report.json to review_index.json, this flips on its own.
    """
    human_signed: bool
    human_signed_reason: str
    signed_source_dxf_sha256: str | None
    signed_request_sha256: str | None
    reproduction: ReproductionVerdict | None

    @property
    def reproduction_status(self) -> str:
        """⛔ Never silently "ok": an un-run gate says so in as many words."""
        return "not_attempted" if self.reproduction is None else self.reproduction.status

    @property
    def trustworthy(self) -> bool:
        return self.human_signed or (self.reproduction is not None
                                     and self.reproduction.reproduced)


@dataclass(frozen=True)
class GtRawLayer:
    """The raw layer of one case's gt, plus an explicit statement of its trust root."""
    case: str
    report: ConversionReportV1
    trust: RawLayerTrust

    def edges(self) -> Iterator[RawEdge]:
        for zone in self.report.zones:
            for index, edge in enumerate(zone.edges):
                yield RawEdge(zone_id=zone.zone_id, floor_id=zone.floor_id,
                              edge_index=index, edge=edge)

    def edge_count(self) -> int:
        return sum(len(zone.edges) for zone in self.report.zones)

    def basis_histogram(self) -> dict[str, int]:
        histogram: dict[str, int] = {}
        for raw in self.edges():
            histogram[raw.basis] = histogram.get(raw.basis, 0) + 1
        return histogram

    def thickness_histogram(self) -> dict[float, int]:
        histogram: dict[float, int] = {}
        for raw in self.edges():
            histogram[raw.thickness_m] = histogram.get(raw.thickness_m, 0) + 1
        return histogram


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #
def _review_dir(case: str, gt_dir: Path | str) -> Path:
    return case_gt_dir(case, gt_dir=gt_dir) / "review"


def _read_ack(review: Path) -> HumanReviewAckV1 | None:
    path = review / "review_ack.json"
    if not path.is_file():
        return None
    return HumanReviewAckV1.model_validate_json(path.read_bytes())


def _human_signed(review: Path) -> tuple[bool, str]:
    """Ask the signed inventory whether it covers conversion_report.json."""
    index_path = review / "review_index.json"
    if not index_path.is_file():
        return False, "review_index_missing"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    listed = {item.get("path") for item in index.get("files", [])}
    if "conversion_report.json" in listed:
        return True, "listed_in_review_index"
    return False, "not_in_review_index_file_set"


def load_gt_raw_layer(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR,
                      reproduction: ReproductionVerdict | None = None) -> GtRawLayer | None:
    """Load the raw layer for ``case``, or None when the case has no review bundle.

    ``reproduction`` is threaded through rather than run here: re-running the
    converter costs seconds and needs a writable staging dir, so the caller
    decides.  Passing nothing yields ``reproduction_status == "not_attempted"``.
    """
    review = _review_dir(case, gt_dir)
    report_path = review / "conversion_report.json"
    if not report_path.is_file():
        return None
    report = ConversionReportV1.model_validate_json(report_path.read_bytes())
    ack = _read_ack(review)
    signed, reason = _human_signed(review)
    trust = RawLayerTrust(
        human_signed=signed, human_signed_reason=reason,
        signed_source_dxf_sha256=ack.source_dxf_sha256 if ack else None,
        signed_request_sha256=ack.request_sha256 if ack else None,
        reproduction=reproduction)
    return GtRawLayer(case=case, report=report, trust=trust)


# --------------------------------------------------------------------------- #
# G1-b: the mechanical reproduction gate
# --------------------------------------------------------------------------- #
REQUEST_SEARCH_ROOT = REPO_ROOT / "AI_agent/logs/experiments"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_signed_source_dxf(case: str, expected_sha256: str) -> Path | None:
    """A DXF is *the* signed source iff its bytes hash to the signed value."""
    case_root = GT_SOURCES_ROOT / case
    if not case_root.is_dir():
        return None
    for candidate in sorted(case_root.glob("*.dxf")):
        if _sha256_file(candidate) == expected_sha256:
            return candidate
    return None


def find_signed_request(expected_sha256: str) -> TarchConversionRequestV1 | None:
    """A request is *the* signed request iff its content RE-HASHES to the signed value.

    ⭐ The declared ``request_sha256`` field is never trusted: it is recomputed
    from the request body, so a tampered copy cannot pass by rewriting its own
    stamp.  Location therefore carries no authority -- which matters, because
    promotion does not copy request.json into the answer tree and the only
    copies live under the experiments staging root.
    """
    if not REQUEST_SEARCH_ROOT.is_dir():
        return None
    for candidate in sorted(REQUEST_SEARCH_ROOT.rglob("request.json")):
        try:
            request = TarchConversionRequestV1.model_validate_json(candidate.read_bytes())
        except Exception:
            continue
        if compute_request_sha256(request) == expected_sha256:
            return request
    return None


def _fatal_fingerprints(report: ConversionReportV1) -> list[tuple[str, str, str]]:
    """(name, recorded, current) for the hashes the REPORT ITSELF binds.

    Mirroring the producer's own declaration is the whole point: these three are
    what ``build_p1_report`` / the P2 report builder stamp into the artefact as
    "the implementation that made me".
    """
    tooling = resolve_converter_tooling(REPO_ROOT / "src/configs/judge_gt.yaml",
                                        REPO_ROOT / "src/configs/correction.yaml")
    return [
        ("converter_sha256", report.converter_sha256, _converter_sha256_now()),
        ("judge_config_sha256", report.judge_config_sha256, tooling.judge_config_sha256),
        ("vg_config_sha256", report.vg_config_sha256, tooling.vg_config_sha256),
    ]


def _advisory_fingerprints(case: str, gt_dir: Path | str) -> list[tuple[str, str, str]]:
    """Signed fingerprints of the NEIGHBOURING artefact (gt.json's generator block).

    Reported, never fatal — ``extractor_sha256`` bundles a CLI script that the
    conversion closure does not import.  See the module docstring.
    """
    gt_path = case_gt_dir(case, gt_dir=gt_dir) / "gt.json"
    if not gt_path.is_file():
        return []
    generator = json.loads(gt_path.read_text(encoding="utf-8")).get("generator", {})
    current = compute_gt_implementation_hashes(REPO_ROOT).model_dump()
    return [(key, generator[key], current[key])
            for key in ("extractor_sha256", "validator_sha256", "vg_implementation_sha256")
            if key in generator]


def _converter_sha256_now() -> str:
    from .tarch_normalize import converter_sha256
    return converter_sha256()


def _normalise_for_diff(report: ConversionReportV1) -> dict:
    """Report as JSON, with gates re-keyed by id so pointers survive reordering."""
    payload = report.model_dump(mode="json")
    payload["gates"] = {gate["id"]: gate for gate in payload.get("gates", [])}
    return payload


def _diff_pointers(left: object, right: object, pointer: str = "") -> list[str]:
    if type(left) is not type(right):
        return [pointer or "/"]
    if isinstance(left, dict):
        out: list[str] = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                out.append(f"{pointer}/{key}")
            else:
                out.extend(_diff_pointers(left[key], right[key], f"{pointer}/{key}"))
        return out
    if isinstance(left, list):
        if len(left) != len(right):
            return [pointer or "/"]
        out = []
        for index, (a, b) in enumerate(zip(left, right)):
            out.extend(_diff_pointers(a, b, f"{pointer}/{index}"))
        return out
    return [] if left == right else [pointer or "/"]


def verify_raw_layer_reproduction(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR,
                                  work_dir: Path | None = None) -> ReproductionVerdict:
    """Re-derive the raw layer from the signed inputs and compare it field-by-field.

    Loud on failure, and specific: a ``content_mismatch`` names the exact JSON
    pointers, so a single tampered ``thickness_m`` is reported as the edge it
    belongs to rather than as a bulk hash difference.
    """
    review = _review_dir(case, gt_dir)
    report_path = review / "conversion_report.json"
    if not report_path.is_file():
        return ReproductionVerdict("inputs_unavailable", f"no conversion_report.json under {review}")
    on_disk = ConversionReportV1.model_validate_json(report_path.read_bytes())

    ack = _read_ack(review)
    if ack is None:
        return ReproductionVerdict("inputs_unavailable", f"no review_ack.json under {review}")

    source = find_signed_source_dxf(case, ack.source_dxf_sha256)
    if source is None:
        return ReproductionVerdict(
            "inputs_unavailable",
            f"no DXF under {GT_SOURCES_ROOT / case} hashes to the signed "
            f"source_dxf_sha256={ack.source_dxf_sha256}")
    request = find_signed_request(ack.request_sha256)
    if request is None:
        return ReproductionVerdict(
            "inputs_unavailable",
            f"no request.json under {REQUEST_SEARCH_ROOT} recomputes to the signed "
            f"request_sha256={ack.request_sha256}")

    advisory = tuple(name for name, recorded, current
                     in _advisory_fingerprints(case, gt_dir) if recorded != current)

    # ⭐ Fingerprints FIRST: a moved tree must never be reported as a bad artefact.
    drifted = [name for name, recorded, current in _fatal_fingerprints(on_disk)
               if recorded != current]
    if drifted:
        return ReproductionVerdict(
            "implementation_drift",
            "this tree no longer matches the implementation that produced the report; "
            f"moved fingerprints: {', '.join(drifted)}. The on-disk report may still be "
            "exactly what was signed -- re-check after aligning the tree.",
            drifted_fingerprints=tuple(drifted), advisory_drifted_fingerprints=advisory)

    owned_work = work_dir is None
    root = Path(tempfile.mkdtemp(prefix=f"gt-raw-repro-{case}-")) if owned_work else Path(work_dir)
    try:
        # assert_staging_input forbids converting a DXF in place under gt_sources/,
        # so the signed source is copied out first (as build_review_bundle does).
        staged = root / "source.dxf"
        shutil.copyfile(source, staged)
        from .tarch_normalize import run_tarch_conversion
        tooling = resolve_converter_tooling(REPO_ROOT / "src/configs/judge_gt.yaml",
                                            REPO_ROOT / "src/configs/correction.yaml")
        fresh = run_tarch_conversion(staged, request, tooling, root).conversion_report
    finally:
        if owned_work:
            shutil.rmtree(root, ignore_errors=True)

    pointers = _diff_pointers(_normalise_for_diff(fresh), _normalise_for_diff(on_disk))
    unexplained = tuple(p for p in pointers if not _pointer_is_signature_dependent(p))
    if unexplained:
        return ReproductionVerdict(
            "content_mismatch",
            f"{len(unexplained)} field(s) of {report_path} could not be reproduced from the "
            f"signed source DXF + request under an IDENTICAL implementation: "
            f"{', '.join(unexplained[:20])}"
            + (f" (+{len(unexplained) - 20} more)" if len(unexplained) > 20 else ""),
            differing_pointers=unexplained, advisory_drifted_fingerprints=advisory)
    return ReproductionVerdict(
        "reproduced",
        f"every content field of {report_path} re-derived from the signed source DXF "
        f"({source.name}) and the signed request; only signature-dependent fields differ."
        + (f" ADVISORY: neighbouring-artefact fingerprints moved ({', '.join(advisory)}); "
           "outside the measured conversion import closure, see module docstring."
           if advisory else ""),
        advisory_drifted_fingerprints=advisory)
