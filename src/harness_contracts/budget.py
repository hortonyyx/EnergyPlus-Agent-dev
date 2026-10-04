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
    image_tokens_estimate: int = Field(default=0, ge=0)
    reported_usage_includes_image_tokens: bool = False
    # None preserves historical ledger semantics; new receipts supply the
    # separately charged amount independently of what raw usage includes.
    additional_image_tokens: int | None = Field(default=None, ge=0)
    token_overrun: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def missing_usage_requires_estimated_cost(self) -> BudgetSettlement:
        if self.image_tokens_estimate == 0 and self.reported_usage_includes_image_tokens:
            raise ValueError(
                "reported usage cannot include image tokens when the request had none"
            )
        if self.usage.kind == "missing":
            if self.actual.tokens is not None:
                raise ValueError("missing token usage must remain None, not zero or an estimate")
            if self.cost.kind == "reported":
                raise ValueError(
                    "when raw usage is missing, cost must be an explicit estimated upper bound"
                )
            if self.reported_usage_includes_image_tokens:
                raise ValueError(
                    "missing usage cannot attest that reported usage includes image tokens"
                )
        if self.cost.kind == "reported":
            if self.actual.money_usd != self.cost.usd:
                raise ValueError("reported cost must equal actual.money_usd")
        elif self.actual.money_usd is not None:
            raise ValueError(
                "an estimated cost upper bound must not be stored as actual.money_usd"
            )
        if self.usage.kind == "reported" and (
            self.image_tokens_estimate or self.reported_usage_includes_image_tokens or self.additional_image_tokens
        ):
            reported_tokens = _reported_total_tokens(self.usage.raw_usage)
            if reported_tokens is not None and self.actual.tokens != reported_tokens:
                raise ValueError(
                    "image accounting must preserve provider-reported token usage"
                )
        if self.token_overrun:
            if self.usage.kind != "reported":
                raise ValueError("a token overrun requires reported usage")
            reported_tokens = _reported_total_tokens(self.usage.raw_usage)
            if reported_tokens is None:
                raise ValueError(
                    "a token overrun requires raw total token usage or input/output usage"
                )
            if self.actual.tokens != reported_tokens:
                raise ValueError(
                    "reported raw token usage must equal actual.tokens for an overrun"
                )
        return self

    @property
    def effective_tokens(self) -> int | None:
        """Budget charge while keeping provider-reported usage unmodified."""

        if self.actual.tokens is None:
            return None
        if self.additional_image_tokens is not None:
            return self.actual.tokens + self.additional_image_tokens
        if self.reported_usage_includes_image_tokens:
            return self.actual.tokens
        return self.actual.tokens + self.image_tokens_estimate


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
            reserved_tokens = reservation.amounts.tokens
            actual_tokens = item.effective_tokens
            expected_overrun = (
                max(actual_tokens - reserved_tokens, 0)
                if actual_tokens is not None and reserved_tokens is not None
                else 0
            )
            if item.token_overrun != expected_overrun:
                raise ValueError(
                    f"settlement token_overrun differs from actual minus reservation: "
                    f"{item.reservation_id}"
                )
            effective_actual = item.actual.model_copy(
                update={"tokens": item.effective_tokens}
            )
            _ensure_within_reservation(
                effective_actual,
                reservation.amounts,
                f"settlement exceeds reservation: {item.reservation_id}",
                allow_token_overrun=bool(item.token_overrun),
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
        committed_for_limit = self.committed.model_copy(
            update={
                "tokens": (
                    None
                    if self.committed.tokens is None
                    else self.committed.tokens
                    - sum(item.token_overrun for item in self.settlements)
                )
            }
        )
        _ensure_within_limit(
            committed_for_limit,
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

        committed = self.committed
        if (
            self.total_limit.tokens is not None
            and committed.tokens is not None
            and committed.tokens > self.total_limit.tokens
        ):
            committed = committed.model_copy(
                update={"tokens": self.total_limit.tokens}
            )
        return self.total_limit.subtract(committed)


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
        tokens=(
            reservation.amounts.tokens
            if settlement.actual.tokens is None
            else settlement.effective_tokens
        ),
        money_usd=money,
        seconds=actual_or_hold("seconds"),
        calls=actual_or_hold("calls"),
    )


def _ensure_within_reservation(
    actual: BudgetAmounts,
    limit: BudgetAmounts,
    message: str,
    *,
    allow_token_overrun: bool = False,
) -> None:
    for name in ("tokens", "money_usd", "seconds", "calls"):
        value = getattr(actual, name)
        ceiling = getattr(limit, name)
        if name == "tokens" and allow_token_overrun and ceiling is not None:
            continue
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


def _reported_total_tokens(raw_usage: dict[str, JsonValue]) -> int | None:
    from .usage import reported_total_tokens
    return reported_total_tokens(raw_usage)
