"""Conservative transient-error classification and credential-free diagnostics."""

from __future__ import annotations

import asyncio
import json
import re

import httpx

from src.harness_contracts import UsageMissing, UsageReported
from src.harness_contracts.events import ModelFailureDetails


def _sanitize(value, secret=""):
    text = str(value)
    if secret:
        text = text.replace(secret, "[redacted]")
    text = re.sub(r"(?i)(bearer\s+)[^\s\"',;]+", r"\1[redacted]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[redacted]", text)
    text = re.sub(
        r'(?i)([\"\']?(?:api[_-]?key|authorization|access[_-]?token|password|secret|credential)[\"\']?\s*[:=]\s*)'
        r'([\"\'][^\"\']*[\"\']|[^\s,;}]+)', r'\1"[redacted]"', text)
    return text


class ModelServiceError(Exception):
    def __init__(self, details: dict, usage):
        # Never include the original HTTP exception, URL or response in str().
        super().__init__(details["category"])
        self.details = details
        self.usage = usage


def http_failure(response: httpx.Response, *, secret: str, provider: str | None = None) -> ModelServiceError:
    try:
        body = response.json()
    except ValueError:
        body = None
    error = body.get("error", body) if isinstance(body, dict) else {"message": response.text}
    error = error if isinstance(error, dict) else {"message": str(error)}
    error_type = error.get("type", error.get("code"))
    diagnostic = " ".join(str(error.get(k, "")) for k in ("type", "code", "message")).casefold()
    status = response.status_code
    # Provider-specific codes are meaningful only on the identified route.
    # Source: https://docs.bigmodel.cn/cn/api/api-code (checked 2026-10-04).
    glm_code = str(error.get("code", "")) if provider == "glm" else ""
    glm_quota = glm_code in {"1113", "1308", "1309", "1310", "1314",
                            "1316", "1317", "1318", "1319", "1320", "1321"}
    glm_permission = glm_code in {"1000", "1001", "1003", "1005", "1220", "1311", "1315"}
    # Ambiguous 429 is a stop. Only an explicitly temporary rate/concurrency
    # limit is retryable; account, balance and subscription exhaustion win.
    quota = glm_quota or any(word in diagnostic for word in (
        "quota", "balance", "credit", "billing", "daily limit", "usage limit",
        "monthly limit", "subscription limit", "额度", "配额", "余额", "欠费", "套餐", "用尽", "用完",
        "使用上限", "消费上限", "限额", "每周", "每月"))
    permission = glm_permission or any(word in diagnostic for word in (
        "permission", "unauthorized", "forbidden", "权限", "无权", "身份验证"))
    transient_rate = any(word in diagnostic for word in (
        "rate_limit", "rate limit", "too many requests", "concurrency", "frequency",
        "temporar", "限流", "频率", "并发"))
    if status in {401, 403} or permission:
        category, retryable = "permission_denied", False
    elif quota:
        category, retryable = "quota_exhausted", False
    elif status == 429:
        if glm_code in {"1302", "1305"}:
            category, retryable = "temporary_rate_limit", True
        elif glm_code or "公平使用" in diagnostic or "fair use" in diagnostic:
            # 1313 requires an account-side policy action, despite mentioning
            # request frequency. Unknown business codes are not guessed.
            category, retryable = "unclassified_rate_limit", False
        else:
            category, retryable = ("temporary_rate_limit", True) if transient_rate else ("unclassified_rate_limit", False)
    elif status == 408:
        category, retryable = "timeout", True
    elif 500 <= status <= 599:
        category, retryable = "service_unavailable", True
    else:
        category, retryable = "invalid_request", False
    usage_raw = body.get("usage") if isinstance(body, dict) else None
    # Preserve reported usage separately, without copying arbitrary service
    # payload fields (which can echo authorization) into the ledger.
    usage_raw = {key: value for key, value in (usage_raw or {}).items()
                 if key in {"prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"}
                 and type(value) is int and value >= 0} if isinstance(usage_raw, dict) else {}
    usage = UsageReported(raw_usage=usage_raw) if usage_raw else UsageMissing(reason="HTTP error omitted token usage")
    request_id = response.headers.get("x-request-id", response.headers.get("request-id"))
    if request_id is None and isinstance(body, dict):
        request_id = body.get("request_id", body.get("id"))
    return ModelServiceError({
        "category": category, "retryable": retryable, "http_status": status,
        "service_error_type": _sanitize(error_type, secret)[:256] if error_type is not None else None,
        "body_excerpt": _sanitize(response.text, secret).encode("utf-8")[:2048].decode("utf-8", errors="ignore"),
        "request_id": _sanitize(request_id, secret)[:256] if request_id is not None else None,
        "usage_received": bool(usage_raw),
    }, usage)


def classify_failure(exc: BaseException, request_event_id: str) -> ModelFailureDetails:
    if isinstance(exc, ModelServiceError):
        return ModelFailureDetails(request_event_id=request_event_id, **exc.details)
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        category, retryable = "timeout", True
    elif isinstance(exc, (ConnectionError, httpx.TransportError)):
        category, retryable = "transport_error", True
    elif isinstance(exc, asyncio.CancelledError):
        category, retryable = "cancelled", False
    else:
        category, retryable = "unknown_error", False
    return ModelFailureDetails(request_event_id=request_event_id, category=category,
        retryable=retryable, service_error_type=type(exc).__name__, usage_received=False)
