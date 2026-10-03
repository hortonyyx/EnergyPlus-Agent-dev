"""Explicit route parameters and read-only GLM subscription credentials."""

from pathlib import Path


GLM_SUBSCRIPTION = "glm-subscription"
GLM_SUBSCRIPTION_MODEL = "glm-5.3-flash"
GLM_SUBSCRIPTION_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"
MAIN_CREDENTIALS_FILE = Path("/workspaces/EnergyPlus-Agent-dev/.env")
LIVE_PROVIDERS = ("paratera", GLM_SUBSCRIPTION)
# Verified 10-03 on the Coding Plan endpoint: omitted behaves like the top level, low/medium cut
# thinking 2-4x (migration_comparison/subscription_effort_calibration.json). Claude Code sends
# output_config.effort=medium with adaptive thinking (evidence/claude_code_request_capture/).
SUBSCRIPTION_REASONING_EFFORTS = ("low", "medium", "high", "max")


def validate_provider_model(provider: str, model: str) -> None:
    if provider == GLM_SUBSCRIPTION and model != GLM_SUBSCRIPTION_MODEL:
        raise ValueError("glm-subscription requires model glm-5.3-flash")


def subscription_credentials(path: Path | None = None) -> tuple[str, str]:
    """No environment fallback, interpolation, sourcing, or credential logging."""
    if path is not None and path.resolve() != MAIN_CREDENTIALS_FILE:
        raise ValueError("GLM subscription credentials must come from the main-tree .env")
    from dotenv import dotenv_values
    private = dotenv_values(MAIN_CREDENTIALS_FILE, interpolate=False)
    base_url, key = private.get("GLM_BASE_URL"), private.get("GLM_API_KEY")
    if base_url != GLM_SUBSCRIPTION_BASE_URL:
        raise ValueError("GLM_BASE_URL must be the reviewed Coding Plan endpoint")
    if not key:
        raise ValueError("GLM_API_KEY is missing from the main-tree .env")
    return base_url, key


def provider_parameters(provider: str, *, output_tokens: int,
                        temperature: float | None = None,
                        thinking: bool = True, reasoning_effort: str | None = None) -> dict:
    parameters = {"max_tokens": output_tokens}
    if provider == GLM_SUBSCRIPTION:
        if thinking is not True:
            raise ValueError("GLM-5.3-Flash thinking cannot be disabled; omit the thinking switch")
        if reasoning_effort is not None:
            if reasoning_effort not in SUBSCRIPTION_REASONING_EFFORTS:
                raise ValueError("unverified subscription reasoning_effort: " + str(reasoning_effort))
            parameters["reasoning_effort"] = reasoning_effort
        if temperature is not None:
            parameters["temperature"] = temperature
        return parameters
    if reasoning_effort == "medium":
        raise ValueError("Paratera does not offer reasoning_effort=medium")
    parameters["temperature"] = 0.0 if temperature is None else temperature
    if reasoning_effort:
        parameters["reasoning_effort"] = reasoning_effort
    else:
        parameters["enable_thinking"] = thinking
    return parameters
