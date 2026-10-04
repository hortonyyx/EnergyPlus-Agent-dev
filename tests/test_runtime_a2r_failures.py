"""A2-R: official GLM error codes and terminal counterexamples, offline."""

import asyncio

import httpx
import pytest

from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.failures import http_failure
from src.agent_runtime.loop import RunLimits
from test_agent_runtime import MESSAGES, response, runtime


@pytest.mark.parametrize("code,message,category,retryable", [
    ("1302", "请求过多，请稍后重试", "temporary_rate_limit", True),
    (1305, "该模型当前访问量过大，请您稍后再试", "temporary_rate_limit", True),
    ("1113", "请充值后重试", "quota_exhausted", False),
    ("1308", "已达到 5 小时使用上限", "quota_exhausted", False),
    ("1309", "GLM Coding Plan 到期", "quota_exhausted", False),
    ("1310", "已达到每周使用上限", "quota_exhausted", False),
    ("1311", "当前订阅套餐未开放权限", "permission_denied", False),
    ("1313", "请求频率已受到限制，请申请解除限制", "unclassified_rate_limit", False),
    ("1314", "企业套餐失效", "quota_exhausted", False),
    ("1315", "Key 仅限企业编程套餐", "permission_denied", False),
    ("1316", "5小时上限余额不足", "quota_exhausted", False),
    ("1317", "7天上限余额不足", "quota_exhausted", False),
    ("1318", "子账号月消费上限", "quota_exhausted", False),
    ("1319", "7天和子账号月消费上限", "quota_exhausted", False),
    ("1320", "企业级月消费上限", "quota_exhausted", False),
    ("1321", "7天和企业级月消费上限", "quota_exhausted", False),
    ("1302", "rate limit; quota exhausted", "quota_exhausted", False),
    ("1305", "rate limit; 权限不足", "permission_denied", False),
    ("9999", "请稍后重试 rate limit", "unclassified_rate_limit", False),
    (None, "请求过多，请稍后重试", "unclassified_rate_limit", False),
    (None, "异常", "unclassified_rate_limit", False),
])
def test_glm_codes_and_terminal_counterexamples(code, message, category, retryable):
    body = {"error": {"message": message}}
    if code is not None:
        body["error"]["code"] = code
    error = http_failure(httpx.Response(429, json=body), secret="", provider="glm")
    assert error.details["category"] == category
    assert error.details["retryable"] is retryable


def test_other_providers_do_not_inherit_glm_numeric_codes():
    error = http_failure(httpx.Response(429, json={"error": {"code": "1305", "message": "busy"}}), secret="")
    assert not error.details["retryable"]


@pytest.mark.parametrize("code,expected_calls,status", [
    ("1302", 2, "completed"), ("1305", 2, "completed"),
    ("1308", 1, "quota_exhausted"), ("1313", 1, "unclassified_rate_limit"),
])
def test_glm_classification_uses_existing_bounded_retry_and_stops_quota(tmp_path, code, expected_calls, status):
    sent = []

    def handler(request):
        sent.append(request.content)
        if len(sent) > 1:
            return httpx.Response(200, json=response(text="OK"))
        return httpx.Response(429, json={"error": {"code": code, "message": "请求过多，请稍后重试"}})

    engine = runtime(tmp_path, [], limits=RunLimits(model_calls=3, tool_calls=0, tokens=100000,
        seconds=300, retry_backoff_seconds=0))
    engine.adapter = HttpChatAdapter(base_url="https://open.bigmodel.cn/api/coding/paas/v4",
        api_key="test-key", transport=httpx.MockTransport(handler))

    async def run():
        try:
            return await engine.run(MESSAGES)
        finally:
            await engine.adapter.close()

    with engine.store:
        result = asyncio.run(run())
        assert result["status"] == status
        assert result["model_calls"] == len(sent) == expected_calls
        assert all(raw == sent[0] for raw in sent)
        engine.store.validate()
