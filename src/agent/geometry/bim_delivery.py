"""Truthful, source-bound delivery summaries for viewable source BIMs.

The summary deliberately reports what has and has not been reviewed.  It does
not inspect drawings, infer missing geometry, or turn a self-consistent source
model into a drawing-fidelity verdict.
"""
from __future__ import annotations

import copy
from typing import Any

from .opening_review import opening_inventory


_KINDS = ("door", "passage", "window")
_CONSISTENT = "consistent_with_supplied_observations"
_FOLLOW_UP = "observations_require_follow_up"


def _as_list(value: Any, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"source {field} must be a list when present")
    return copy.deepcopy(value)


def _review_ref(review: dict, index: int, *, state: str, reason: str | None = None) -> dict:
    """Keep the useful, stable identity of a review without copying its body."""
    scope = review.get("review_scope")
    image = review.get("image")
    findings = review.get("findings", [])
    reference = review.get("review_file")
    if not isinstance(reference, str) or not reference:
        reference = f"reviews[{index}]"
    result = {
        "review_ref": reference,
        "review_index": index,
        "state": state,
        "source_model_sha256": review.get("source_model_sha256"),
        "floor_id": scope.get("floor_id") if isinstance(scope, dict) else None,
        "kind": scope.get("kind") if isinstance(scope, dict) else None,
        "coverage": scope.get("coverage") if isinstance(scope, dict) else None,
        "image": copy.deepcopy(image) if isinstance(image, dict) else None,
        "conclusion": review.get("conclusion"),
        "finding_codes": sorted(
            row["code"] for row in findings
            if isinstance(row, dict) and isinstance(row.get("code"), str)
        ),
    }
    if reason is not None:
        result["stale_reason"] = reason
    return result


def _image_identity(ref: dict) -> tuple[str, str] | None:
    image = ref.get("image")
    if not isinstance(image, dict):
        return None
    sha256 = image.get("sha256")
    if isinstance(sha256, str) and sha256:
        return ("sha256", sha256)
    name = image.get("name")
    if isinstance(name, str) and name:
        return ("name", name)
    return None


def _scope_status(effective_complete: list[dict], partial: list[dict]) -> str:
    """Return only statuses with an explicit meaning to delivery consumers."""
    # A partial result is useful but cannot establish coverage by itself.
    if not effective_complete:
        return "partial" if partial else "not_reviewed"
    # A current partial from another image cannot erase a complete coverage
    # claim.  Its findings are nevertheless retained in scope findings below.
    if any(ref.get("conclusion") != _CONSISTENT or ref["finding_codes"]
           for ref in effective_complete):
        return _FOLLOW_UP
    # ``partial_review_not_complete`` records a deliberately limited scope;
    # it does not contradict a complete, consistent review already available
    # for this source scope.  Any other partial finding remains a risk.
    if any(set(ref["finding_codes"]) - {"partial_review_not_complete"}
           for ref in partial):
        return _FOLLOW_UP
    return _CONSISTENT


def summarize_delivery(source: dict, reviews: list[dict]) -> dict:
    """Summarize a source BIM and only reviews bound to that exact source.

    ``reviews`` is ordered: a later list item is a later submitted review.  A
    later *complete* review of the same source, floor/kind scope, and image
    explicitly supersedes earlier records for that same image.  Complete
    reviews from other images remain independently effective; partial reviews
    never supersede a complete review and never establish full coverage.

    This is intentionally a delivery description, not a global pass/fail gate:
    a geometrically valid source with no image review remains viewable and is
    reported as ``not_reviewed``.
    """
    if not isinstance(reviews, list) or any(not isinstance(review, dict) for review in reviews):
        raise ValueError("reviews must be a list of review objects")

    inventory = opening_inventory(source)
    source_hash = inventory["source_model_sha256"]
    current_reviews: list[dict] = []
    stale_reviews: list[dict] = []
    for index, review in enumerate(reviews):
        if review.get("source_model_sha256") != source_hash:
            reason = ("source_model_sha256_missing" if "source_model_sha256" not in review
                      else "source_model_sha256_mismatch")
            stale_reviews.append(_review_ref(review, index, state="stale", reason=reason))
        else:
            current_reviews.append(_review_ref(review, index, state="current"))

    # Only a valid scope can influence the status of source opening scopes.
    scope_refs: dict[tuple[str, str], list[dict]] = {}
    for ref in current_reviews:
        key = (ref["floor_id"], ref["kind"])
        if key[0] is not None and key[1] in _KINDS:
            scope_refs.setdefault(key, []).append(ref)

    opening_review_scopes = []
    for floor in inventory["floors"]:
        floor_id = floor["floor_id"]
        counts = floor["counts"]
        for kind in _KINDS:
            refs = scope_refs.get((floor_id, kind), [])
            complete = [ref for ref in refs if ref["coverage"] == "complete"]
            partial = [ref for ref in refs if ref["coverage"] == "partial"]

            # Same source + image + scope: the later complete review replaces
            # all earlier records for that image.  Missing image identity is
            # intentionally not merged with another record.
            latest_complete_by_image: dict[tuple[str, str] | tuple[str, int], dict] = {}
            for ref in complete:
                image_key = _image_identity(ref) or ("review_index", ref["review_index"])
                latest_complete_by_image[image_key] = ref
            effective_complete = sorted(latest_complete_by_image.values(), key=lambda row: row["review_index"])
            effective_by_image = {
                _image_identity(ref) or ("review_index", ref["review_index"]): ref
                for ref in effective_complete
            }
            superseded = []
            for ref in refs:
                image_key = _image_identity(ref) or ("review_index", ref["review_index"])
                replacement = effective_by_image.get(image_key)
                if replacement is None or ref is replacement:
                    continue
                # A complete report replaces an earlier report of the same
                # image, including an earlier partial.  A later partial is
                # retained as additional, non-complete evidence.
                if ref["coverage"] == "complete" or ref["review_index"] < replacement["review_index"]:
                    superseded.append(ref)
            # A same-image complete review also supersedes earlier partial
            # evidence for that scope; a partial from another image, or a
            # later partial, remains explicit.
            effective_partial = [
                ref for ref in partial
                if ref not in superseded
            ]

            finding_codes = sorted({
                code for ref in [*effective_complete, *effective_partial]
                for code in ref["finding_codes"]
            })
            opening_review_scopes.append({
                "floor_id": floor_id,
                "kind": kind,
                "built_count": counts[kind],
                "built_opening_ids": [
                    opening_id for opening_id in floor["opening_ids"]
                    if next(row["kind"] for row in floor["openings"] if row["id"] == opening_id) == kind
                ],
                "review_status": _scope_status(effective_complete, effective_partial),
                "current_review_refs": [ref["review_ref"] for ref in refs],
                "effective_complete_review_refs": [ref["review_ref"] for ref in effective_complete],
                "partial_review_refs": [ref["review_ref"] for ref in effective_partial],
                "superseded_review_refs": [ref["review_ref"] for ref in superseded],
                "finding_codes": finding_codes,
            })

    generation = source.get("generation", {})
    if generation is None:
        generation = {}
    if not isinstance(generation, dict):
        raise ValueError("source generation must be an object when present")
    counts = {
        name: len(_as_list(source.get(name), name))
        for name in ("spaces", "boundaries", "openings", "connections", "unbuilt_openings", "unsupported")
    }
    return {
        "schema_version": "bim_delivery_v1",
        "source_model_sha256": source_hash,
        "source_validation": copy.deepcopy(source.get("validation")),
        "counts": counts,
        "unbuilt_openings": _as_list(source.get("unbuilt_openings"), "unbuilt_openings"),
        "assumptions": _as_list(source.get("assumptions"), "assumptions"),
        "generation": {"unresolved": _as_list(generation.get("unresolved"), "generation.unresolved")},
        "opening_inventory": inventory,
        "opening_review_scopes": opening_review_scopes,
        "current_reviews": current_reviews,
        "stale_reviews": stale_reviews,
        "drawing_fidelity": "not_evaluated",
    }
