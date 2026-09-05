"""A-6a: one-image dimension decisions, frozen batches and explicit reconsideration.

The public decision API accepts candidate IDs, never model coordinates. Reading
witnesses nominate candidates, not facts. A session owns the current batch;
consumers must supply its independently retained expected batch ID. Persistence
is immutable JSON bytes, not a mutable tree of pointers. This is ordinary API
encapsulation, not a defence against Python reflection or modified source code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from src.agent.correction.config import load_core_tolerances


class TickClaimError(ValueError):
    def __init__(self, code: str, detail: object = None):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")


def freeze(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def units(mm: object) -> int:
    if isinstance(mm, bool) or not isinstance(mm, (int, float, str, Decimal)):
        raise TickClaimError("VALUE_OFF_DECLARED_GRID", mm)
    number = Decimal(str(mm)) * 10
    if not number.is_finite() or number != number.to_integral_value():
        raise TickClaimError("VALUE_OFF_DECLARED_GRID", mm)
    return int(number)


def require_chain(chain: dict) -> tuple[int, ...]:
    """Positive segment lengths, zero-relative prefix nodes; origin is separate."""
    try:
        values = tuple(units(v) for v in chain["values_mm"])
        nodes = tuple(units(v) for v in chain["cum_mm"])
        overall = units(chain["overall_mm"])
    except (KeyError, TypeError) as exc:
        raise TickClaimError("CHAIN_RECORD_INVALID") from exc
    if not values or len(nodes) != len(values) + 1 or nodes[0] != 0:
        raise TickClaimError("CHAIN_DOMAIN_INVALID")
    if any(v <= 0 for v in values):
        raise TickClaimError("CHAIN_SEGMENT_NOT_POSITIVE")
    if sum(values) != overall or nodes[-1] != overall:
        raise TickClaimError("CHAIN_TOTAL_NOT_CLOSED")
    if any(nodes[i + 1] != nodes[i] + v for i, v in enumerate(values)):
        raise TickClaimError("CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM")
    return nodes


@dataclass(frozen=True)
class OperandRef:
    """Indices address either nodes or segments; they are never interchangeable."""
    source_sha: str
    chain_id: str
    domain: Literal["node", "segment", "declaration"]
    index: int


@dataclass(frozen=True)
class Expression:
    operation: Literal["node", "anchored_sum", "anchored_diff", "axis_half_wall"]
    anchor: OperandRef
    operands: tuple[OperandRef, ...] = ()
    direction: Literal["positive", "negative"] = "positive"
    thickness_kind: Literal["full", "half"] | None = None


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    expression: Expression
    value_u: int


@dataclass(frozen=True)
class Edge:
    edge_id: str
    axis: str
    raw_u: int
    pointer: str
    witness: bytes
    candidates: tuple[Candidate, ...]
    missing_chains: tuple[str, ...]


class TickChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    edge_id: str
    action: Literal["select", "pixel", "pixel_pending_evidence", "reperceive"]
    candidate_id: str | None = None
    reason: str

    @model_validator(mode="after")
    def choice_shape(self):
        if (self.action == "select") != (self.candidate_id is not None):
            raise ValueError("CHOICE_CANDIDATE_SHAPE")
        if not self.reason.strip():
            raise ValueError("CHOICE_REASON_REQUIRED")
        return self


class TickResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    packet_id: str
    choices: tuple[TickChoice, ...]


@dataclass(frozen=True)
class TickPacket:
    packet_id: str
    image_id: str
    source_sha: str
    generation: int
    edges: tuple[Edge, ...]
    source_bytes: bytes
    supplement_bytes: bytes | None
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class TickBatch:
    batch_id: str
    record: bytes


@dataclass(frozen=True)
class TickFact:
    edge_id: str
    axis: str
    value_u: int
    tier: str
    candidate_id: str | None
    source_sha: str
    batch_id: str
    debt_id: str | None


def _chain_records(raw: bytes, supplement: bytes | None) -> dict[str, dict]:
    doc = json.loads(raw)
    # Check every calibration chain even when a supplemental declaration is used.
    for ch in doc.get("calibration", {}).values():
        if isinstance(ch, dict) and "values_mm" in ch:
            require_chain(ch)
    if supplement is None:
        return {}
    cfg = json.loads(supplement)
    # The reading supplement is explicitly bound to these source bytes and image.
    if (cfg.get("source_sha") != digest(raw) or cfg.get("image") != doc.get("image")
            or cfg.get("schema") != "tick_reading_supplement_v1"):
        raise TickClaimError("SUPPLEMENT_SOURCE_MISMATCH")
    records = cfg["chains"]
    for cid, ch in records.items():
        require_chain(ch)
        if ch.get("axis") not in ("x", "y", "z") or ch.get("direction") not in (-1, 1):
            raise TickClaimError("CHAIN_FRAME_INVALID", cid)
        units(ch["origin_mm"])
        if ch.get("qualification") != "drawing_dimension":
            raise TickClaimError("OPERAND_NOT_DECLARED", cid)
    for axis, cid in cfg.get("primary", {}).items():
        if cid not in records or axis not in doc["calibration"]:
            raise TickClaimError("PRIMARY_CHAIN_IDENTITY_MISSING", cid)
        original = doc["calibration"][axis]
        if (records[cid]["axis"] != axis or
                require_chain(records[cid]) != require_chain(original)):
            raise TickClaimError("PRIMARY_CHAIN_SOURCE_MISMATCH", cid)
    return records


def freeze_prototype_supplement(raw: bytes, config_bytes: bytes) -> bytes:
    """Reading handoff for the existing prototype's explicit dimension config.

    Does not edit either original. Image/facade and primary arrays must agree.
    The config is an additional declared input, not reconstructed from the lossy
    pixel map. Persist its original bytes in the supplement for review.
    """
    doc, cfg = json.loads(raw), json.loads(config_bytes)
    if cfg.get("image") != doc.get("image") or (
        doc.get("facade_label") is not None and cfg.get("view_facade") != doc["facade_label"]
    ):
        raise TickClaimError("SUPPLEMENT_IMAGE_MISMATCH")
    chains = {}
    vertical = "z" if doc["schema"] == "as_drawn_elevation_v0" else "y"
    for cid, ch in cfg["chains"].items():
        vals = ch["values_mm"]
        cumulative = [0]
        for v in vals:
            cumulative.append(cumulative[-1] + units(v))
        chains[cid] = dict(axis="x" if ch["axis"] == "row" else vertical,
                           values_mm=vals, cum_mm=[v / 10 for v in cumulative],
                           overall_mm=cumulative[-1] / 10,
                           origin_mm=ch["world_start_mm"], direction=ch["direction"],
                           qualification="drawing_dimension")
    result = freeze(dict(schema="tick_reading_supplement_v1", source_sha=digest(raw),
                         image=doc["image"], config=json.loads(config_bytes),
                         chains=chains, declarations=[],
                         primary={a: cfg[f"primary_{a}_chain"] for a in ("x", vertical)}))
    _chain_records(raw, result)
    return result


def evaluate(expression: Expression, *, raw: bytes, supplement: bytes, axis: str) -> int:
    """All results are positions in the source image's declared local axis frame.

    Sum/diff first produce displacement, then explicitly add/subtract at anchor.
    The sign never comes from an opening edge's low/high role.
    """
    chains = _chain_records(raw, supplement)
    cfg = json.loads(supplement)
    if type(expression) is not Expression or expression.direction not in ("positive", "negative"):
        raise TickClaimError("OPERATION_SIGNATURE_INVALID")

    def resolve(ref: OperandRef, domain: str) -> tuple[int, dict]:
        if type(ref) is not OperandRef or ref.source_sha != digest(raw):
            raise TickClaimError("OPERAND_CROSS_IMAGE")
        if ref.domain != domain or type(ref.index) is not int or ref.index < 0:
            raise TickClaimError("OPERAND_REF_DOMAIN", domain)
        if domain == "declaration":
            if ref.chain_id != "declarations":
                raise TickClaimError("OPERAND_REF_DOMAIN")
            try:
                decl = cfg["declarations"][ref.index]
            except (IndexError, KeyError) as exc:
                raise TickClaimError("OPERAND_REF_MISSING") from exc
            if (decl.get("qualification") != "drawing_dimension" or decl.get("axis") != axis
                    or not decl.get("callout_id")):
                raise TickClaimError("OPERAND_NOT_DECLARED")
            return units(decl["value_mm"]), decl
        try:
            chain = chains[ref.chain_id]
            if chain["axis"] != axis:
                raise TickClaimError("OPERAND_FRAME_MISMATCH")
            values = require_chain(chain) if domain == "node" else tuple(units(v) for v in chain["values_mm"])
            value = values[ref.index]
        except (KeyError, IndexError) as exc:
            raise TickClaimError("OPERAND_REF_MISSING") from exc
        if domain == "node":
            value = units(chain["origin_mm"]) + chain["direction"] * value
        return value, chain

    anchor, _ = resolve(expression.anchor, "node")
    op, operands = expression.operation, expression.operands
    sign = 1 if expression.direction == "positive" else -1
    if op == "node":
        if operands or expression.thickness_kind is not None or sign != 1:
            raise TickClaimError("OPERATION_SIGNATURE_INVALID")
        return anchor
    if op == "axis_half_wall":
        if len(operands) != 1 or expression.thickness_kind not in ("full", "half"):
            raise TickClaimError("OPERATION_SIGNATURE_INVALID")
        value, decl = resolve(operands[0], "declaration")
        if decl.get("kind") != expression.thickness_kind or value <= 0:
            raise TickClaimError("THICKNESS_DECLARATION_MISMATCH")
        if expression.thickness_kind == "full":
            if value % 2:
                raise TickClaimError("WALL_THICKNESS_HALF_UNGRID")
            value //= 2
        return anchor + sign * value
    if expression.thickness_kind is not None:
        raise TickClaimError("OPERATION_SIGNATURE_INVALID")
    if op == "anchored_sum":
        if not operands:
            raise TickClaimError("OPERATION_SIGNATURE_INVALID")
        if (len({r.chain_id for r in operands}) != 1 or
                [r.index for r in operands] != list(range(operands[0].index, operands[0].index + len(operands)))):
            raise TickClaimError("SEGMENTS_NOT_CONTIGUOUS")
        displacement = sum(resolve(r, "segment")[0] for r in operands)
    elif op == "anchored_diff":
        if len(operands) != 2 or operands[0].chain_id != operands[1].chain_id:
            raise TickClaimError("OPERATION_SIGNATURE_INVALID")
        lo, _ = resolve(operands[0], "node")
        hi, _ = resolve(operands[1], "node")
        displacement = hi - lo
    else:
        raise TickClaimError("OPERATION_SIGNATURE_INVALID")
    return anchor + sign * displacement


def _raw_edges(doc: dict):
    """The frozen source, not a caller-supplied list, defines the entire scope."""
    if doc.get("schema") == "as_drawn_elevation_v0":
        seen = set()
        for i, opening in enumerate(doc["openings"]):
            oid = opening["id"]
            if oid in seen:
                raise TickClaimError("OPENING_ID_DUPLICATE", oid)
            seen.add(oid)
            for axis, names in (("x", ("x0", "x1")), ("z", ("z_low", "z_high"))):
                for j, name in enumerate(names):
                    yield f"{oid}:{name}", axis, opening[f"{axis}_range_m"][j], f"/openings/{i}/{axis}_range_m/{j}", opening.get("edge_witnesses", {}).get(name, {})
    elif doc.get("schema") == "as_drawn_plan_v0":
        seen = set()
        for i, band in enumerate(doc["wall_bands"]):
            if band["id"] in seen:
                raise TickClaimError("OPENING_ID_DUPLICATE", band["id"])
            seen.add(band["id"])
            axis = "y" if band["constant_world_axis"] == "x" else "x"
            for k, opening in enumerate(band["opening_runs"]):
                for j, role in enumerate(("lo", "hi")):
                    yield f"{band['id']}:run{k}:{role}", axis, opening["run_m"][j], f"/wall_bands/{i}/opening_runs/{k}/run_m/{j}", opening.get("edge_witnesses", {}).get(role, {})
    else:
        raise TickClaimError("TICK_SOURCE_CONTRACT_UNSUPPORTED")


def build_packet(raw: bytes, *, image_id: str, generation: int,
                 supplement: bytes | None = None,
                 expressions: tuple[tuple[str, Expression], ...] = ()) -> TickPacket:
    chains = _chain_records(raw, supplement)
    source_sha = digest(raw)
    edges = []
    extra = {}
    for eid, expr in expressions:
        extra.setdefault(eid, []).append(expr)
    for eid, axis, measured_m, pointer, witness in _raw_edges(json.loads(raw)):
        candidates = []
        refs = witness.get("dimension_refs", [])
        named = {}
        for ref in refs:
            match = re.fullmatch(r"(.+)_s([1-9][0-9]*)", ref)
            if match:
                named.setdefault(match[1], set()).add(int(match[2]))
        missing = tuple(sorted(cid for cid in named if cid not in chains))
        # Preserve chain identity. No use of dimension_witnesses' lossy value map.
        proposed = []
        for cid, segments in sorted(named.items()):
            if cid not in chains:
                continue
            chain = chains[cid]
            if chain["axis"] != axis:
                raise TickClaimError("WITNESS_CHAIN_FRAME_MISMATCH", eid)
            n = len(chain["values_mm"])
            if any(s > n for s in segments):
                raise TickClaimError("WITNESS_SEGMENT_MISSING", eid)
            indices = {s for s in segments if s + 1 in segments}
            if segments == {1}:
                indices.add(0)  # candidate only; NOT an automatic origin claim
            if segments == {n}:
                indices.add(n)
            for index in sorted(indices):
                proposed.append(Expression("node", OperandRef(source_sha, cid, "node", index)))
        # Source without witnesses still offers its declared nodes for model review.
        if not named:
            for cid, chain in sorted(chains.items()):
                if chain["axis"] == axis:
                    proposed.extend(Expression("node", OperandRef(source_sha, cid, "node", i))
                                    for i in range(len(chain["cum_mm"])))
        proposed.extend(extra.pop(eid, []))
        unique = {}
        for expr in proposed:
            value = evaluate(expr, raw=raw, supplement=supplement, axis=axis)
            cid = digest(freeze({"edge": eid, "expression": asdict(expr)}))
            unique[cid] = Candidate(cid, expr, value)
        candidates = tuple(unique[k] for k in sorted(unique))
        edges.append(Edge(eid, axis, units(Decimal(str(measured_m)) * 1000), pointer,
                          freeze(witness), candidates, missing))
    if extra:
        raise TickClaimError("EXPRESSION_EDGE_UNKNOWN", sorted(extra))
    if len({e.edge_id for e in edges}) != len(edges):
        raise TickClaimError("EDGE_ID_DUPLICATE")
    # Include source, config, full edge universe and all proposed expressions.
    identity = dict(image_id=image_id, generation=generation, source_sha=source_sha,
                    supplement_sha=digest(supplement) if supplement else None,
                    edges=[dict(edge=e.edge_id, candidates=[c.candidate_id for c in e.candidates]) for e in edges])
    return TickPacket(digest(freeze(identity)), image_id, source_sha, generation,
                      tuple(edges), raw, supplement, ("SAME_IMAGE_MODEL_REQUIRED",) if edges else ())


class TickSession:
    """Owner of the current per-image generation; all cross-image reads pass here."""
    def __init__(self, raw: bytes, *, image_id: str, supplement: bytes | None = None,
                 expressions: tuple[tuple[str, Expression], ...] = (), max_rounds: int = 3):
        if max_rounds < 1:
            raise TickClaimError("ROUND_BUDGET_INVALID")
        self._generation = 0
        self._max_rounds = max_rounds
        self._packet = build_packet(raw, image_id=image_id, generation=0,
                                    supplement=supplement, expressions=expressions)
        self._current: TickBatch | None = None
        self._history: list[bytes] = []
        self._previous_debts: dict[str, str] = {}
        self._precision_u = units(Decimal(str(load_core_tolerances().output_precision_m)) * 1000)
        if self._precision_u <= 0:
            raise TickClaimError("OUTPUT_PRECISION_INVALID")

    @property
    def packet(self) -> TickPacket:
        return self._packet

    @property
    def history(self) -> tuple[bytes, ...]:
        return tuple(self._history)

    def submit(self, response: TickResponse) -> TickBatch:
        if type(response) is not TickResponse or response.packet_id != self._packet.packet_id:
            raise TickClaimError("STALE_TICK_RESPONSE")
        if self._current is not None:
            raise TickClaimError("BATCH_ALREADY_DECIDED_USE_RECONSIDER")
        choices = {c.edge_id: c for c in response.choices}
        if (len(choices) != len(response.choices) or
                set(choices) != {e.edge_id for e in self._packet.edges}):
            raise TickClaimError("TICK_DECISION_COVERAGE_MISMATCH")
        if any(c.action == "reperceive" for c in choices.values()):
            raise TickClaimError("RETURN_TO_READING")
        rows = []
        for edge in self._packet.edges:
            choice = choices[edge.edge_id]
            candidates = {c.candidate_id: c for c in edge.candidates}
            candidate = candidates.get(choice.candidate_id)
            debt = None
            if choice.action == "select":
                if candidate is None:
                    raise TickClaimError("UNKNOWN_TICK_CANDIDATE", edge.edge_id)
                value = evaluate(candidate.expression, raw=self._packet.source_bytes,
                                 supplement=self._packet.supplement_bytes, axis=edge.axis)
                tier = "chain_backed"
            else:
                if choice.action == "pixel_pending_evidence":
                    if not edge.missing_chains:
                        raise TickClaimError("EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE")
                    debt = digest(freeze(dict(image=self._packet.image_id, edge=edge.edge_id,
                                             missing=edge.missing_chains)))
                value = int((Decimal(edge.raw_u) / self._precision_u).quantize(Decimal(1), rounding=ROUND_HALF_UP)) * self._precision_u
                tier = "pixel_only"
            rows.append(dict(edge_id=edge.edge_id, axis=edge.axis, value_u=value, tier=tier,
                             pointer=edge.pointer, witness=json.loads(edge.witness),
                             candidate=asdict(candidate) if candidate else None,
                             choice=choice.model_dump(), debt_id=debt,
                             retired_debt_id=self._previous_debts.get(edge.edge_id)
                             if tier == "chain_backed" and not edge.missing_chains else None))
        # Every interval is checked after the choices, including pixel rounding.
        by_id = {r["edge_id"]: r for r in rows}
        for eid, row in by_id.items():
            high = None
            if eid.endswith(":x0"):
                high = eid[:-2] + "x1"
            elif eid.endswith(":z_low"):
                high = eid[:-5] + "z_high"
            elif eid.endswith(":lo"):
                high = eid[:-2] + "hi"
            if high and row["value_u"] >= by_id[high]["value_u"]:
                self.reconsider("INTERVAL_NOT_ORDERED")
                raise TickClaimError("RETURN_TO_STEP_ONE_INTERVAL", eid)
        record = freeze(dict(schema="tick_batch_v1", packet_id=response.packet_id,
                             source_sha=self._packet.source_sha, image_id=self._packet.image_id,
                             generation=self._generation, response=response.model_dump(),
                             output_precision=dict(config_field="output_precision_m", units=self._precision_u),
                             rows=rows))
        self._current = TickBatch(digest(record), record)
        self._history.append(record)
        return self._current

    def consume(self, expected_batch_id: str, batch: TickBatch | None = None) -> tuple[TickFact, ...]:
        current = self._current
        if current is None or current.batch_id != expected_batch_id:
            raise TickClaimError("TICK_BATCH_INVALIDATED")
        supplied = current if batch is None else batch
        if type(supplied) is not TickBatch or supplied.batch_id != expected_batch_id or supplied.record != current.record or digest(supplied.record) != expected_batch_id:
            raise TickClaimError("TICK_BATCH_NOT_CURRENT_DECISION")
        record = json.loads(supplied.record)
        if record["packet_id"] != self._packet.packet_id or record["source_sha"] != digest(self._packet.source_bytes):
            raise TickClaimError("TICK_BATCH_SOURCE_MISMATCH")
        return tuple(TickFact(r["edge_id"], r["axis"], r["value_u"], r["tier"],
                              r["choice"]["candidate_id"], record["source_sha"], expected_batch_id,
                              r["debt_id"]) for r in record["rows"])

    def reconsider(self, reason: str, *, raw: bytes | None = None,
                   supplement: bytes | None = None,
                   expressions: tuple[tuple[str, Expression], ...] = ()) -> TickPacket:
        """Named return to step one, owned by correction; old consumers go stale.

        Reading supplies evidence; correction calls this and asks its same-image
        model again. Debts retire only after the new matching edge is chain-backed.
        """
        if not reason.strip():
            raise TickClaimError("RECONSIDERATION_REASON_REQUIRED")
        if self._current:
            self._previous_debts.update({r["edge_id"]: r["debt_id"] for r in json.loads(self._current.record)["rows"] if r["debt_id"]})
        self._history.append(freeze(dict(event="RETURN_TO_STEP_ONE", reason=reason,
                                        invalidated=self._current.batch_id if self._current else None)))
        self._current = None  # invalidate BEFORE any possible retry failure
        self._generation += 1
        if self._generation >= self._max_rounds:
            raise TickClaimError("REGISTER_PENDING_ROUND_LIMIT")
        old = self._packet
        new_raw = old.source_bytes if raw is None else raw
        if json.loads(new_raw).get("image") != json.loads(old.source_bytes).get("image"):
            raise TickClaimError("SUPPLEMENT_IMAGE_MISMATCH")
        new_supplement = old.supplement_bytes if supplement is None else supplement
        self._packet = build_packet(new_raw, image_id=old.image_id, generation=self._generation,
                                    supplement=new_supplement, expressions=expressions)
        return self._packet
