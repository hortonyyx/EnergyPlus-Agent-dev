"""Explicit route parameters and read-only GLM subscription credentials."""

from pathlib import Path


GLM_SUBSCRIPTION = "glm-subscription"
GLM_SUBSCRIPTION_MODEL = "glm-5.3-flash"
GLM_SUBSCRIPTION_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"
MAIN_CREDENTIALS_FILE = Path("/workspaces/EnergyPlus-Agent-dev/.env")
LIVE_PROVIDERS = ("paratera", GLM_SUBSCRIPTION)


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
        if reasoning_effort is not None or thinking is not True:
            raise ValueError("subscription thinking controls are unverified; omit them to use the service default")
        if temperature is not None:
            parameters["temperature"] = temperature
        return parameters
    parameters["temperature"] = 0.0 if temperature is None else temperature
    if reasoning_effort:
        parameters["reasoning_effort"] = reasoning_effort
    else:
        parameters["enable_thinking"] = thinking
    return parameters
