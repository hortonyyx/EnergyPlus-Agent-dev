"""Budget reservations, usage evidence, and settlement validation."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, JsonValue, model_validator

from .base import ContractModel, NonEmptyStr


class BudgetAmounts(ContractModel):
    tokens: int | None = Field(default=None, ge=0)
    money_usd: Decimal | None = Field(default=None, ge=0)
    seconds: Decimal | None = Field(default=None, ge=0)
    calls: int | None = Field(default=None, ge=0)

    def add(self, other: BudgetAmounts) -> BudgetAmounts:
        def add_optional(left: int | Decimal | None, right: int | Decimal | None):
            if left is None and right is None:
                return None
            return (left or 0) + (right or 0)

        return BudgetAmounts(
            tokens=add_optional(self.tokens, other.tokens),
            money_usd=add_optional(self.money_usd, other.money_usd),
            seconds=add_optional(self.seconds, other.seconds),
            calls=add_optional(self.calls, other.calls),
        )

    def subtract(self, other: BudgetAmounts) -> BudgetAmounts:
        """Subtract known dimensions without turning an unbounded one into zero."""

        def subtract_optional(
            left: int | Decimal | None, right: int | Decimal | None
        ) -> int | Decimal | None:
            if left is None:
                return None
            return left - (right or 0)

        return BudgetAmounts(
            tokens=subtract_optional(self.tokens, other.tokens),
            money_usd=subtract_optional(self.money_usd, other.money_usd),
            seconds=subtract_optional(self.seconds, other.seconds),
            calls=subtract_optional(self.calls, other.calls),
        )


class UsageReported(ContractModel):
    kind: Literal["reported"] = "reported"
    raw_usage: dict[str, JsonValue]

    @model_validator(mode="after")
    def raw_usage_cannot_be_empty(self) -> UsageReported:
        if not self.raw_usage:
            raise ValueError("reported usage must preserve the non-empty raw object")
        return self


class UsageMissing(ContractModel):
    kind: Literal["missing"] = "missing"
    reason: NonEmptyStr


UsageEvidence = Annotated[UsageReported | UsageMissing, Field(discriminator="kind")]


class ReportedCost(ContractModel):
    kind: Literal["reported"] = "reported"
    usd: Decimal = Field(ge=0)


class EstimatedCostUpperBound(ContractModel):
    kind: Literal["estimated_upper_bound"] = "estimated_upper_bound"
    usd: Decimal = Field(ge=0)
    reason: NonEmptyStr


class CostUnavailable(ContractModel):
    """No price or bill was reported; unknown is not a zero-dollar estimate."""

    kind: Literal["unavailable"] = "unavailable"
    reason: NonEmptyStr


CostEvidence = Annotated[
    ReportedCost | EstimatedCostUpperBound | CostUnavailable,
    Field(discriminator="kind"),
]


class BudgetReservation(ContractModel):
    reservation_id: NonEmptyStr
    purpose: Literal["primary_task", "child_task", "context_summary", "retry"]
    amounts: BudgetAmounts
    task_id: NonEmptyStr

    @model_validator(mode="after")
    def require_nonempty_reservation(self) -> BudgetReservation:
        if not _has_positive_dimension(self.amounts):
            raise ValueError("a reservation needs at least one positive budget dimension")
        return self


class BudgetSettlement(ContractModel):
    reservation_id: NonEmptyStr
    actual: BudgetAmounts
    usage: UsageEvidence
    cost: CostEvidence

    @model_validator(mode="after")
    def missing_usage_requires_estimated_cost(self) -> BudgetSettlement:
        if self.usage.kind == "missing":
            if self.actual.tokens is not None:
                raise ValueError("missing token usage must remain None, not zero or an estimate")
            if self.cost.kind == "reported":
                raise ValueError(
                    "when raw usage is missing, cost must be an explicit estimated upper bound"
                )
        if self.cost.kind == "reported":
            if self.actual.money_usd != self.cost.usd:
                raise ValueError("reported cost must equal actual.money_usd")
        elif self.actual.money_usd is not None:
            raise ValueError(
                "an estimated cost upper bound must not be stored as actual.money_usd"
            )
        return self


class BudgetLedger(ContractModel):
    total_limit: BudgetAmounts
    reservations: tuple[BudgetReservation, ...]
    settlements: tuple[BudgetSettlement, ...] = ()

    @model_validator(mode="after")
    def validate_ledger(self) -> BudgetLedger:
        if not _has_positive_dimension(self.total_limit):
            raise ValueError("total budget needs at least one positive dimension")
        reservation_by_id: dict[str, BudgetReservation] = {}
        for item in self.reservations:
            if item.reservation_id in reservation_by_id:
                raise ValueError(f"duplicate reservation_id: {item.reservation_id}")
            reservation_by_id[item.reservation_id] = item

        settled: set[str] = set()
        for item in self.settlements:
            if item.reservation_id in settled:
                raise ValueError(f"reservation settled twice: {item.reservation_id}")
            settled.add(item.reservation_id)
            reservation = reservation_by_id.get(item.reservation_id)
            if reservation is None:
                raise ValueError(f"settlement has no reservation: {item.reservation_id}")
            _ensure_within_reservation(
                item.actual,
                reservation.amounts,
                f"settlement exceeds reservation: {item.reservation_id}",
            )
            if item.cost.kind == "unavailable":
                if reservation.amounts.money_usd is not None:
                    raise ValueError("unknown cost cannot settle a money-limited reservation")
                continue
            if reservation.amounts.money_usd is None:
                raise ValueError(
                    f"settlement cost has no money reservation: {item.reservation_id}"
                )
            if item.cost.usd > reservation.amounts.money_usd:
                raise ValueError(
                    f"settlement cost exceeds reservation: {item.reservation_id}"
                )
        _ensure_within_limit(
            self.committed,
            self.total_limit,
            "effective charges and outstanding reservations exceed total budget",
        )
        return self

    @property
    def outstanding(self) -> BudgetAmounts:
        """Full conservative holds for reservations without a settlement."""

        settled = {item.reservation_id for item in self.settlements}
        total = BudgetAmounts()
        for reservation in self.reservations:
            if reservation.reservation_id not in settled:
                total = total.add(reservation.amounts)
        return total

    @property
    def charged(self) -> BudgetAmounts:
        """Effective settled charge, retaining holds where evidence is unknown."""

        reservation_by_id = {
            item.reservation_id: item for item in self.reservations
        }
        total = BudgetAmounts()
        for settlement in self.settlements:
            reservation = reservation_by_id.get(settlement.reservation_id)
            if reservation is not None:
                total = total.add(_effective_charge(reservation, settlement))
        return total

    @property
    def committed(self) -> BudgetAmounts:
        """Settled effective charge plus every still-outstanding reservation."""

        return self.charged.add(self.outstanding)

    @property
    def available(self) -> BudgetAmounts:
        """Remaining configured capacity; None continues to mean unbounded."""

        return self.total_limit.subtract(self.committed)


def _effective_charge(
    reservation: BudgetReservation, settlement: BudgetSettlement
) -> BudgetAmounts:
    """Return what remains committed after a settlement, dimension by dimension."""

    def actual_or_hold(name: str):
        actual = getattr(settlement.actual, name)
        return actual if actual is not None else getattr(reservation.amounts, name)

    if settlement.cost.kind == "reported":
        money = settlement.cost.usd
    elif settlement.cost.kind == "estimated_upper_bound":
        money = settlement.cost.usd
    else:
        money = reservation.amounts.money_usd
    return BudgetAmounts(
        tokens=actual_or_hold("tokens"),
        money_usd=money,
        seconds=actual_or_hold("seconds"),
        calls=actual_or_hold("calls"),
    )


def _ensure_within_reservation(
    actual: BudgetAmounts, limit: BudgetAmounts, message: str
) -> None:
    for name in ("tokens", "money_usd", "seconds", "calls"):
        value = getattr(actual, name)
        ceiling = getattr(limit, name)
        if value is not None and (ceiling is None or value > ceiling):
            raise ValueError(f"{message} ({name})")


def _ensure_within_limit(
    actual: BudgetAmounts, limit: BudgetAmounts, message: str
) -> None:
    for name in ("tokens", "money_usd", "seconds", "calls"):
        value = getattr(actual, name)
        ceiling = getattr(limit, name)
        if ceiling is not None and value is not None and value > ceiling:
            raise ValueError(f"{message} ({name})")


def _has_positive_dimension(amounts: BudgetAmounts) -> bool:
    return any(
        value is not None and value > 0
        for value in (
            amounts.tokens,
            amounts.money_usd,
            amounts.seconds,
            amounts.calls,
        )
    )
