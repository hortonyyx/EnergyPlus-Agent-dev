from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from src.agent_runtime.estimation import (
    approximate_text_tokens,
    estimate_chat_request,
    get_model_profile,
    qwen_image_tokens,
)


def _image_url(width: int, height: int) -> str:
    stream = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode()


@pytest.mark.parametrize(
    ("model", "context"),
    [("Qwen3.8-27B", 262_144), ("qwen3.8-flash", 262_144)],
)
def test_registered_profiles_have_sourced_context_limits(model, context):
    profile = get_model_profile(model, strict=True)
    assert profile.context_window_tokens == context
    assert profile.context_source.startswith("https://")
    assert "Paratera" in profile.context_uncertainty
    assert profile.native_context_window_tokens == 262_144
    assert profile.extended_context_window_tokens == 1_000_000
    assert profile.endpoint_context_window_tokens is None
    assert "calibration/summary.json" in profile.safety_margin_source


def test_unknown_model_is_explicitly_unverified_and_strict_lookup_rejects():
    profile = get_model_profile("scripted-model")
    assert profile.context_window_tokens is None
    assert profile.profile_status == "unverified_conservative_approximation"
    with pytest.raises(ValueError, match="no reviewed estimation profile"):
        get_model_profile("scripted-model", strict=True)


def test_qwen_image_estimate_matches_existing_paratera_elevation_usage():
    profile = get_model_profile("Qwen3.8-27B", strict=True)
    # Existing 2026-10-02 Paratera evidence reports 2,380 image tokens for
    # the 2,639 x 931 East elevation and 2,513 for the 2,580 x 993 West one.
    assert qwen_image_tokens(2639, 931, profile) == (2380, 2624, 928)
    assert qwen_image_tokens(2580, 993, profile) == (2513, 2592, 992)


def test_request_estimate_separates_text_image_output_and_context():
    body = {
        "model": "Qwen3.8-Flash",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Inspect this plan 图纸."},
            {"type": "image_url", "image_url": {"url": _image_url(224, 224)}},
        ]}],
        "max_tokens": 64,
    }
    estimate = estimate_chat_request(body, strict=True)
    assert estimate.text_tokens == 23 + approximate_text_tokens(
        "<|im_start|>user\nInspect this plan 图纸.<|im_end|>\n<|im_start|>assistant\n"
    )
    assert estimate.image_tokens == 66
    assert estimate.input_tokens_estimate == estimate.text_tokens + 66
    assert estimate.input_tokens_upper_bound >= estimate.input_tokens_estimate
    assert estimate.reservation_tokens == estimate.input_tokens_upper_bound + 64
    assert estimate.context_window_tokens == 262_144
    assert estimate.fits_context is True
    assert estimate.images[0].request_reference.endswith("/image_url/url")


def test_unknown_model_estimate_does_not_claim_a_context_limit():
    estimate = estimate_chat_request({
        "model": "fake-test-model",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 8,
    })
    assert estimate.context_window_tokens is None
    assert estimate.fits_context is None
    assert "unverified_conservative_approximation" in estimate.source


def test_remote_images_are_rejected_before_a_false_estimate():
    with pytest.raises(ValueError, match="captured image data URLs"):
        estimate_chat_request({
            "model": "Qwen3.8-27B",
            "messages": [{"role": "user", "content": [{
                "type": "image_url", "image_url": {"url": "https://example.test/a.png"},
            }]}],
            "max_tokens": 8,
        })
