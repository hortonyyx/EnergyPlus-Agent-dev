"""Strict model routing for the drawing-only role-division runtime."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from src.agent_runtime.estimation import get_model_profile
from src.agent_runtime.output_limits import validate_output_limit
from src.agent_runtime.providers import (
    LIVE_PROVIDERS,
    provider_parameters,
    validate_provider_model,
)


ROLE_NAMES = ("coordinator", "plan_reader", "elevation_reader")


class RoleConfiguration(BaseModel):
    """One explicit, reviewed chat route used by a runtime role."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    reasoning_effort: str = Field(min_length=1)
    output_tokens: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_reviewed_route(self, info: ValidationInfo) -> "RoleConfiguration":
        allow_scripted = bool((info.context or {}).get("allow_scripted", False))
        if self.provider == "scripted" or self.model == "scripted-model":
            if allow_scripted and self.provider == "scripted" and self.model == "scripted-model":
                return self
            raise ValueError("scripted role routes are admitted only by an explicit offline runtime")
        if self.provider not in LIVE_PROVIDERS:
            raise ValueError(f"role provider {self.provider!r} is not a reviewed live provider")
        if "deepseek" in self.model.casefold():
            raise ValueError("DeepSeek is outside the approved role-division batch")
        validate_provider_model(self.provider, self.model)
        get_model_profile(self.model, strict=True)
        provider_parameters(
            self.provider,
            output_tokens=self.output_tokens,
            reasoning_effort=self.reasoning_effort,
        )
        validate_output_limit(self.model, self.output_tokens)
        return self


def load_roles(value: object, *, allow_scripted: bool = False) -> dict[str, RoleConfiguration]:
    """Validate the complete fixed role set without defaults or inheritance."""

    if not isinstance(value, Mapping):
        raise ValueError("role_division requires an explicit roles object")
    supplied = set(value)
    required = set(ROLE_NAMES)
    missing = sorted(required - supplied)
    unexpected = sorted(supplied - required)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing roles: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected roles: " + ", ".join(unexpected))
        raise ValueError("role_division identities are fixed; " + "; ".join(details))
    return {name: RoleConfiguration.model_validate(
        value[name], context={"allow_scripted": allow_scripted}) for name in ROLE_NAMES}
