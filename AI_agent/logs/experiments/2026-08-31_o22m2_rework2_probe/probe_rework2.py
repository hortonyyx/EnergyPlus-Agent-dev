"""Independent reproduction probe for the 2026-08-31 rework-2 dispatch.

Three shapes, straight from the GPT cross-review verdict (B-1 x2 + B-2).
Expected on the PRE-CHANGE tree: all three VALIDATE (that is the hole).
"""
import json
import runpy
import sys

from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
ns = runpy.run_path(str(REPO / "tests/test_o22m2_evidence_contract.py"))
EvidenceDebtV1 = ns["EvidenceDebtV1"]
finalize = ns["finalize_bundle"]


def _set_sources(art, channel, input_ids):
    art.bundle.channel_status = [
        (
            s.model_copy(update={"source_input_ids": tuple(input_ids)})
            if s.channel == channel
            else s
        )
        for s in art.bundle.channel_status
    ]
    return art


def _refinalize(art):
    art.bundle = finalize(art.bundle)
    return art


def _try_validate(label, art):
    try:
        ns["validate_evidence_bundle"](art)
    except Exception as exc:  # noqa: BLE001 - probe reports both directions
        print(f"{label}: REJECTS {exc}")
        return
    print(f"{label}: VALIDATES")


tiny = ns["_tiny_artifact"]()
empty = ns["_empty_artifact"]()

# ── B-1 (walls): freeze BOTH products; declare walls' source as the empty one,
#    payload still entirely from tiny. ─────────────────────────────────────────
art = tiny.model_copy(deep=True)
src = empty.frozen_sources[0]
art.frozen_sources.append(src)
art.bundle.source_artifacts.append(src.artifact)
_set_sources(art, "walls", ("empty_plan",))
_try_validate("B1[walls]", _refinalize(art))

# ── B-1 (plan_openings): same shape on the openings channel ──────────────────
art = tiny.model_copy(deep=True)
art.frozen_sources.append(src)
art.bundle.source_artifacts.append(src.artifact)
_set_sources(art, "plan_openings", ("empty_plan",))
_try_validate("B1[plan_openings]", _refinalize(art))

# ── B-2: dimensions=present + zero_payload_channel(dimensions) ────────────────
art = tiny.model_copy(deep=True)
art.bundle.channel_status = [
    (
        s.model_copy(update={
            "state": "present", "source_input_ids": ("tiny",),
            "covered_by_debt_ids": (),
        })
        if s.channel == "dimensions"
        else s
    )
    for s in art.bundle.channel_status
]
art.bundle.evidence_debts.append(EvidenceDebtV1(
    debt_id="debt_zero_dimensions", kind="zero_payload_channel",
    channel="dimensions",
    description="dimensions present, produced nothing this run",
))
_try_validate("B2[dimensions]", _refinalize(art))

# ── dispatch acceptance 2's shape (for later): declared source with no payload
#    while the channel DOES carry payload from another declared source ────────
art = tiny.model_copy(deep=True)
art.frozen_sources.append(src)
art.bundle.source_artifacts.append(src.artifact)
_set_sources(art, "walls", ("empty_plan", "tiny"))
_try_validate("B1-reverse[unscoped]", _refinalize(art))
art2 = art.model_copy(deep=True)
art2.bundle.evidence_debts.append(EvidenceDebtV1(
    debt_id="debt_zero_walls", kind="zero_payload_channel", channel="walls",
    description="walls wired, produced nothing",
))
_try_validate("B1-reverse[global-debt]", _refinalize(art2))
