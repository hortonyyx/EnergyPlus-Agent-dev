"""Per-FILE contract discriminator for the 0_reading vector directory (F-97).

``src/agent/reading/contract.py`` recognizes the reading-product **envelope**
(``{"views": {...}}``).  This module answers a different question, one file at a
time: *given one parsed JSON found in a run's ``0_reading/``, which declared
contract is it, and may 1_correction consume it?*

Why this exists
---------------
``discover_vector_files`` sorts ``0_reading/*.json`` into plans / elevations /
**others**, and the correction prompt pasted every one of them in verbatim.  A
JSON of any shape whatsoever therefore reached the model as untyped text without
passing a single reading gate (F-97).  ⛔ The filename regex is an ORDERING key,
never a contract: ``1f_view_checks.json`` is a check report, not a reading view.

Discipline this module follows
------------------------------
1. ⭐ **The as-drawn schema value is imported from its producer**, never copied.
   ``as_drawn_v2.SCHEMA`` is the one place that string is defined; a literal here
   would be a second definition that silently stops matching the day the
   producer's value changes.  Same lesson as ``judge/as_drawn/denominator.py:14``
   ("⛔ never from a second re-implementation ... a check whose recomputation
   does not mirror the producer's definition measures the difference between two
   opinions").
2. ⭐ **A contract is a (declared schema value × required key set) PAIR**, not a
   schema value alone.  ``as_drawn_plan_v2`` is emitted by two different
   producers with two different shapes (the reading product, and the as-drawn
   check report from ``validator/checks/as_drawn.py``), so keying on the value
   alone would name one of them the other.
3. ⭐ **Every contract is recognized by its producer's own TYPE**, never by a key
   list induced from existing artifacts.  Legacy views use
   ``reading/schema.py:ReadingView`` plus the field correction actually eats,
   ``strokes`` (the prompt cites stroke ids and counts ``pen == "window"``);
   check-report sidecars use ``validator/checks/schema.py:CheckReport``.
   ⚠️ Both models default every field, so they validate ``{}`` — "parses"
   alone would recognize everything, hence the explicit-key conjuncts.
4. ⭐ **Every detector is evaluated; first-match-wins is forbidden.**  Two
   matches is an ambiguity to report, not a race for the detector that ran first.
5. ⭐ **Structural fallback is only for the undeclared.**  Legacy recognition
   exists for artifacts written before ``schema`` did.  A file declaring a value
   this module does not register is unknown by construction, even when it still
   looks like a reading view — otherwise any future contract that kept a
   ``strokes`` list would be silently consumed as a 2026-06 view, which is F-97
   reopened in a new shape.  A file declaring a *registered* value while also
   matching legacy structure still goes to the two-match path (#4).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from src.agent.reading.as_drawn.as_drawn_v2 import SCHEMA as AS_DRAWN_PLAN_SCHEMA
from src.agent.reading.schema import ReadingView

# Historical as-drawn prototype values.  ⚠️ Registered as LITERALS on purpose:
# their only producer is the 2026-08-23 prototype under `AI_agent/logs/
# experiments/`, which is not importable production code.  ⛔ Do not "fix" this
# by importing experiment tooling.  Anything with a live producer imports its
# constant instead — see AS_DRAWN_PLAN_SCHEMA above.
AS_DRAWN_PLAN_V0_SCHEMA = "as_drawn_plan_v0"
AS_DRAWN_ELEVATION_V0_SCHEMA = "as_drawn_elevation_v0"

CONTRACT_READING_VIEW_LEGACY = "reading_view_legacy"
CONTRACT_AS_DRAWN_PLAN = "as_drawn_plan"
CONTRACT_AS_DRAWN_PLAN_V0 = "as_drawn_plan_v0"
CONTRACT_AS_DRAWN_ELEVATION_V0 = "as_drawn_elevation_v0"
CONTRACT_STAGE_CHECK_REPORT = "stage_check_report"
CONTRACT_UNKNOWN = "unknown"


class Disposition(str, Enum):
    """What 1_correction does with a file of this contract."""

    CONSUME = "consume"
    """Pasted into the correction prompt (today: legacy reading views only)."""

    KNOWN_NOT_CONSUMED = "known_not_consumed"
    """Recognized contract that this stage has no wire for ⇒ loud failure.
    ⭐ Deliberately distinct from ``unknown``: when the reading/correction
    unification lands, "not wired yet" and "never heard of it" must stay
    tellable apart."""

    EXCLUDE = "exclude"
    """Declared non-input that lives in the same directory ⇒ dropped from the
    prompt and NAMED in the consumption ledger.  ⛔ Not a silent skip (F-64 is
    "nobody can tell it happened"); the ledger names every excluded file."""


@dataclass(frozen=True)
class ContractSpec:
    contract_id: str
    disposition: Disposition
    detect: Callable[[dict], bool]
    describe: str


def _has_keys(raw: dict, *keys: str) -> bool:
    return all(k in raw for k in keys)


def _is_declared(raw: dict, schema_value: str) -> bool:
    return raw.get("schema") == schema_value


# Every schema value this module registers. A file declaring a value OUTSIDE
# this set is unknown by construction -- ⛔ it must never fall back to structural
# legacy recognition (B-01).
DECLARED_SCHEMA_VALUES: frozenset[str] = frozenset(
    {AS_DRAWN_PLAN_SCHEMA, AS_DRAWN_PLAN_V0_SCHEMA, AS_DRAWN_ELEVATION_V0_SCHEMA}
)


def _declares_unregistered_schema(raw: dict) -> bool:
    return "schema" in raw and raw.get("schema") not in DECLARED_SCHEMA_VALUES


def _detect_legacy_reading_view(raw: dict) -> bool:
    """Legacy views are the ONE contract that predates explicit declaration.

    ⭐ B-01: a file declaring an UNREGISTERED top-level `schema` is never legacy
    by structure. Legacy recognition is the fallback for artifacts written
    before the field existed; letting a declared-but-unregistered contract fall
    back here just because it still carries `strokes` would re-open F-97's
    silent channel in a new shape -- any future contract keeping a `strokes`
    list would be consumed as if it were a 2026-06 reading view.

    ⚠️ Only UNREGISTERED declarations are rejected here. A file declaring a
    registered contract AND matching legacy structure must still reach the
    two-match path so it is reported as AMBIGUOUS -- collapsing it to a single
    verdict here would silently pick a winner, which is what ⛔ first-match-wins
    forbids.
    """
    if _declares_unregistered_schema(raw):
        return False
    # ⚠️ Both remaining conjuncts are load-bearing; see module docstring #3.
    if not isinstance(raw.get("strokes"), list):
        return False
    try:
        ReadingView.model_validate(raw)
    except Exception:
        return False
    return True


def _detect_stage_check_report(raw: dict) -> bool:
    """B-02: the three key names are a proxy; the producer's TYPE is the thing.

    ⭐ Keying on `stage`/`results`/`report_schema_version` merely being present
    let a malformed report (e.g. `results` a string) be silently EXCLUDEd --
    neither loud nor consumed, filed in the ledger as a legitimate exclusion.
    `CheckReport` is the type its producer actually writes, and all 43 real
    sidecars in the tree parse under it, so the stricter path costs no
    compatibility. Explicit presence is still required: `CheckReport` defaults
    every field, so "parses" alone would swallow `{}`.
    """
    if "schema" in raw:
        return False
    if not _has_keys(raw, "stage", "results", "report_schema_version"):
        return False
    from src.validator.checks.schema import CheckReport

    try:
        CheckReport.model_validate(raw)
    except Exception:
        return False
    return True


CONTRACTS: tuple[ContractSpec, ...] = (
    ContractSpec(
        CONTRACT_READING_VIEW_LEGACY,
        Disposition.CONSUME,
        _detect_legacy_reading_view,
        "parses as reading/schema.py:ReadingView and declares a `strokes` list",
    ),
    ContractSpec(
        CONTRACT_AS_DRAWN_PLAN,
        Disposition.KNOWN_NOT_CONSUMED,
        lambda raw: _is_declared(raw, AS_DRAWN_PLAN_SCHEMA)
        and _has_keys(raw, "observations", "declarations", "hypotheses"),
        f"schema=={AS_DRAWN_PLAN_SCHEMA!r} (imported from its producer) "
        "with observations/declarations/hypotheses",
    ),
    ContractSpec(
        CONTRACT_AS_DRAWN_PLAN_V0,
        Disposition.KNOWN_NOT_CONSUMED,
        lambda raw: _is_declared(raw, AS_DRAWN_PLAN_V0_SCHEMA)
        and _has_keys(raw, "wall_bands", "dimension_witnesses"),
        f"schema=={AS_DRAWN_PLAN_V0_SCHEMA!r} with wall_bands/dimension_witnesses",
    ),
    ContractSpec(
        CONTRACT_AS_DRAWN_ELEVATION_V0,
        Disposition.KNOWN_NOT_CONSUMED,
        lambda raw: _is_declared(raw, AS_DRAWN_ELEVATION_V0_SCHEMA)
        and _has_keys(raw, "openings", "structure_lines"),
        f"schema=={AS_DRAWN_ELEVATION_V0_SCHEMA!r} with openings/structure_lines",
    ),
    ContractSpec(
        CONTRACT_STAGE_CHECK_REPORT,
        Disposition.EXCLUDE,
        _detect_stage_check_report,
        "undeclared sidecar: declares stage/results/report_schema_version AND "
        "parses as validator/checks/schema.py:CheckReport",
    ),
)


@dataclass(frozen=True)
class ContractDecision:
    contract_id: str
    disposition: Disposition | None
    reason: str | None
    """Why the file is NOT a single known contract (``None`` when it is one)."""


def classify_vector_json(raw: Any) -> ContractDecision:
    """Name the declared contract of ONE parsed reading-stage JSON.

    Evaluates every detector — ⛔ never first-match-wins — so that a file
    satisfying two contracts is reported as an ambiguity rather than silently
    resolved by declaration order.
    """
    if not isinstance(raw, dict):
        return ContractDecision(
            CONTRACT_UNKNOWN,
            None,
            f"top-level JSON is {type(raw).__name__}, not an object",
        )
    matches = [spec for spec in CONTRACTS if spec.detect(raw)]
    if len(matches) == 1:
        return ContractDecision(matches[0].contract_id, matches[0].disposition, None)
    if len(matches) > 1:
        named = ", ".join(f"{m.contract_id} ({m.describe})" for m in matches)
        return ContractDecision(
            CONTRACT_UNKNOWN,
            None,
            f"AMBIGUOUS: matches {len(matches)} declared contracts at once: {named}",
        )
    keys = sorted(k for k in raw if isinstance(k, str))[:12]
    declared = raw.get("schema")
    declared_txt = (
        f"declares schema={declared!r} but no registered contract has that value "
        "with a matching key set"
        if isinstance(declared, str)
        else "declares no `schema` field and matches no structural contract"
    )
    return ContractDecision(
        CONTRACT_UNKNOWN,
        None,
        f"{declared_txt}; top-level keys={keys}",
    )


@dataclass(frozen=True)
class LedgerRow:
    filename: str
    contract_id: str
    disposition: str
    reason: str | None

    def as_dict(self) -> dict:
        return {
            "file": self.filename,
            "contract": self.contract_id,
            "disposition": self.disposition,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class VectorDirDecision:
    consumed: list[str]
    """Filenames 1_correction may paste, in the caller's original order."""
    rows: list[LedgerRow]

    def as_ledger(self) -> dict:
        counts: dict[str, int] = {}
        for row in self.rows:
            counts[row.disposition] = counts.get(row.disposition, 0) + 1
        return {
            "ledger_version": "reading_vector_contract_ledger_v1",
            "consumed": list(self.consumed),
            "counts": counts,
            "files": [row.as_dict() for row in self.rows],
        }


class UnconsumableVectorFile(RuntimeError):
    """A 0_reading JSON that 1_correction must not paste into its prompt."""


def _classify_rows(
    vector_dir: Path, names: list[str]
) -> tuple[list[str], list[LedgerRow], list[str]]:
    """Shared core: (consumed, ledger rows, offender descriptions). Never raises."""
    vector_dir = Path(vector_dir)
    rows: list[LedgerRow] = []
    consumed: list[str] = []
    offenders: list[str] = []
    for name in names:
        path = vector_dir / name
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rows.append(
                LedgerRow(name, CONTRACT_UNKNOWN, "error", f"invalid JSON: {exc}")
            )
            offenders.append(f"{name}: invalid JSON ({exc})")
            continue
        decision = classify_vector_json(raw)
        if decision.disposition is Disposition.CONSUME:
            consumed.append(name)
            rows.append(
                LedgerRow(
                    name, decision.contract_id, decision.disposition.value, None
                )
            )
        elif decision.disposition is Disposition.EXCLUDE:
            rows.append(
                LedgerRow(
                    name,
                    decision.contract_id,
                    decision.disposition.value,
                    "recognized; 1_correction does not consume this contract",
                )
            )
        elif decision.disposition is Disposition.KNOWN_NOT_CONSUMED:
            rows.append(
                LedgerRow(
                    name, decision.contract_id, decision.disposition.value, None
                )
            )
            offenders.append(
                f"{name}: recognized as contract {decision.contract_id!r}, but "
                "1_correction has no wire for it (known contract, NOT unknown)"
            )
        else:
            rows.append(LedgerRow(name, CONTRACT_UNKNOWN, "error", decision.reason))
            offenders.append(f"{name}: unknown contract — {decision.reason}")
    return consumed, rows, offenders


def ledger_for(vector_dir: Path, names: list[str]) -> dict:
    """The consumption ledger for ``names`` — ⭐ never raises.

    Written before the prompt is assembled so that a run which fails
    classification still leaves a readable record naming every offending file.
    """
    consumed, rows, _ = _classify_rows(vector_dir, names)
    return VectorDirDecision(consumed=consumed, rows=rows).as_ledger()


def classify_vector_dir(vector_dir: Path, names: list[str]) -> VectorDirDecision:
    """Classify ``names`` under ``vector_dir``; raise unless every file is consumable.

    ⭐ This is the point where "an undeclared shape" stops being a silent paste
    and becomes a named failure.  ``EXCLUDE`` files are dropped but recorded.
    """
    consumed, rows, offenders = _classify_rows(vector_dir, names)
    if offenders:
        raise UnconsumableVectorFile(
            "1_correction refuses to assemble a prompt from "
            f"{Path(vector_dir)}: {len(offenders)} file(s) carry no consumable "
            "contract (F-97: an undeclared shape must fail loudly, never be "
            "pasted as untyped text). Offending files:\n  - "
            + "\n  - ".join(offenders)
        )
    return VectorDirDecision(consumed=consumed, rows=rows)
