"""Offline image/probe round trip and failure evidence; never authorizes live IO."""

import asyncio
import io
import json

from PIL import Image
import pytest

from scripts.dev import smoke_chatgpt_vision as smoke
from src.harness_contracts import RemoteModelIdentity
from test_agent_runtime import versions


@pytest.fixture
def offline_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke, "CACHE_ROOT", tmp_path)

    def manifest(*args, **kwargs):
        return versions().model_copy(update={"remote_model": RemoteModelIdentity(
            route_id=smoke.CHATGPT_SUBSCRIPTION, remote_alias=kwargs["route"]["model"],
            alias_status="unverified")})

    # Sealing is tested separately; development edits must not block this
    # offline protocol test. The actual CLI retains make_versions unchanged.
    monkeypatch.setattr(smoke, "make_versions", manifest)

    def forbidden(*args, **kwargs):
        raise AssertionError("offline smoke must not inspect subscription credentials")

    monkeypatch.setattr(smoke, "resolve_connection", forbidden)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-paid-key-must-never-be-used")
    return tmp_path


def args_for(directory, model="gpt-6-astra"):
    return smoke.parser().parse_args(["--out", str(directory / "run"), "--model", model])


def test_synthetic_image_encodes_only_the_private_color_key():
    data, colors = smoke.make_challenge()
    picture = Image.open(io.BytesIO(data))
    assert picture.size == (480, 180) and sorted(colors) == sorted(smoke.PALETTE)
    assert picture.getpixel((0, 0)) == (255, 255, 255)
    assert [picture.getpixel((80 + index * 160, 90)) for index in range(3)] == [
        smoke.PALETTE[color] for color in colors]
    assert not picture.info


@pytest.mark.parametrize("model", ["gpt-6-astra", "gpt-6-sol", "gpt-6-luna"])
def test_offline_two_request_image_nonce_and_raw_evidence(offline_environment, model):
    args = args_for(offline_environment, model)
    result = asyncio.run(smoke.execute(args))
    assert result["passed"] and result["vision_observation_passed"] and result["nonce_round_trip_passed"]
    assert result["live_model_requests"] == result["paid_api_requests"] == 0
    assert result["fixture_requests"] == 2 and result["tool_calls"] == 1
    assert result["requested_reasoning_effort"] == "high" and result["fallback"] is False
    assert result["evidence"]["requests_with_exact_image"] == 2
    assert result["evidence"]["provider_reported_models"] == [model, model]
    assert [value["total_tokens"] for value in result["evidence"]["raw_usage"]] == [180, 180]
    events = (args.out / "events.jsonl").read_text(encoding="utf-8")
    assert '"model_response"' in events and '"adapter_request"' in events
    for path in args.out.rglob("*"):
        if path.is_file():
            assert b"fake-paid-key-must-never-be-used" not in path.read_bytes()
            assert b"offline-placeholder-not-a-credential" not in path.read_bytes()


def test_wrong_image_read_fails_without_revealing_answer(offline_environment, monkeypatch):
    factory = smoke.make_offline_adapter
    monkeypatch.setattr(smoke, "make_offline_adapter", lambda model, colors: factory(model, colors[::-1]))
    args = args_for(offline_environment)
    result = asyncio.run(smoke.execute(args))
    assert not result["passed"] and not result["vision_observation_passed"]
    assert not result["nonce_round_trip_passed"] and result["fixture_requests"] == 2
    assert result["status"] == "completed" and result["evidence"]["recorded_responses"] == 2
    probe = smoke.VisionProbe(["red", "green", "blue"])
    reply = asyncio.run(probe.call_tool("vision_probe", {"colors": ["blue", "green", "red"]}))
    rejected = json.loads(reply["content"][0]["text"])
    assert rejected == {"accepted": False, "error": "invalid_color_observation"}
    assert "nonce" not in rejected and not any(color in json.dumps(reply) for color in smoke.PALETTE)


def test_wrong_nonce_fails_after_correct_image_read(offline_environment, monkeypatch):
    original = smoke.VisionProbe.call_tool

    async def corrupt_nonce(self, name, arguments):
        reply = await original(self, name, arguments)
        data = json.loads(reply["content"][0]["text"])
        if data.get("accepted"):
            data["nonce"] = "corrupted-fixture-nonce"
        reply["content"][0]["text"] = json.dumps(data)
        return reply

    monkeypatch.setattr(smoke.VisionProbe, "call_tool", corrupt_nonce)
    result = asyncio.run(smoke.execute(args_for(offline_environment)))
    assert result["vision_observation_passed"]
    assert not result["nonce_round_trip_passed"] and not result["passed"]
    assert result["status"] == "completed" and result["evidence"]["recorded_responses"] == 2


def test_no_output_overwrite_or_outside_cache(offline_environment):
    args = args_for(offline_environment)
    args.out.mkdir()
    with pytest.raises(ValueError, match="never overwritten"):
        asyncio.run(smoke.execute(args))
    args.out = offline_environment.parent / "outside-cache"
    with pytest.raises(ValueError, match="subdirectory"):
        asyncio.run(smoke.execute(args))

