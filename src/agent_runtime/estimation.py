"""Model-specific, auditable Chat Completions request estimates.

These estimates reserve local budgets. They are never provider billing evidence.
Unknown test models receive an explicitly unverified compatibility profile; production
callers can request strict lookup or inject a reviewed profile.
"""

from __future__ import annotations

import base64
import io
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Mapping

from PIL import Image


@dataclass(frozen=True)
class ModelProfile:
    canonical_name: str
    aliases: tuple[str, ...]
    context_window_tokens: int | None
    native_context_window_tokens: int | None
    extended_context_window_tokens: int | None
    endpoint_context_window_tokens: int | None
    context_limit_kind: str
    context_source: str
    context_uncertainty: str
    text_estimator: str
    text_estimate_offset: int
    text_safety_factor: float
    text_fixed_margin: int
    safety_margin_source: str
    image_estimator: str
    image_patch_size: int
    image_merge_size: int
    image_min_pixels: int
    image_max_pixels: int
    image_special_tokens: int
    image_source: str
    image_uncertainty: str
    profile_status: str


@dataclass(frozen=True)
class ImageTokenEstimate:
    request_reference: str
    width: int
    height: int
    resized_width: int
    resized_height: int
    tokens: int
    source: str


@dataclass(frozen=True)
class RequestTokenEstimate:
    model: str
    profile_name: str
    text_tokens: int
    image_tokens: int
    input_tokens_estimate: int
    input_tokens_upper_bound: int
    output_token_limit: int
    context_window_tokens: int | None
    fits_context: bool | None
    source: str
    uncertainty: str
    images: tuple[ImageTokenEstimate, ...]

    @property
    def reservation_tokens(self) -> int:
        return self.input_tokens_upper_bound + self.output_token_limit


def _profile_from_dict(row: Mapping[str, Any]) -> ModelProfile:
    return ModelProfile(
        canonical_name=row["canonical_name"], aliases=tuple(row.get("aliases", ())),
        context_window_tokens=row.get("context_window_tokens"),
        native_context_window_tokens=row.get("native_context_window_tokens"),
        extended_context_window_tokens=row.get("extended_context_window_tokens"),
        endpoint_context_window_tokens=row.get("endpoint_context_window_tokens"),
        context_limit_kind=row.get("context_limit_kind", "unverified"),
        context_source=row["context_source"],
        context_uncertainty=row["context_uncertainty"],
        text_estimator=row["text_estimator"],
        text_estimate_offset=int(row.get("text_estimate_offset", 0)),
        text_safety_factor=float(row["text_safety_factor"]),
        text_fixed_margin=int(row["text_fixed_margin"]),
        safety_margin_source=row.get("safety_margin_source", "unverified"),
        image_estimator=row["image_estimator"],
        image_patch_size=int(row["image_patch_size"]),
        image_merge_size=int(row["image_merge_size"]),
        image_min_pixels=int(row["image_min_pixels"]),
        image_max_pixels=int(row["image_max_pixels"]),
        image_special_tokens=int(row["image_special_tokens"]),
        image_source=row["image_source"], image_uncertainty=row["image_uncertainty"],
        profile_status=row["profile_status"],
    )


@lru_cache(maxsize=1)
def registered_model_profiles() -> tuple[ModelProfile, ...]:
    raw = json.loads(files("src.agent_runtime").joinpath("model_profiles.json").read_text())
    if raw.get("schema_version") != 1:
        raise ValueError("unsupported model profile schema")
    return tuple(_profile_from_dict(row) for row in raw["profiles"])


def conservative_compatibility_profile(model: str) -> ModelProfile:
    """Return a conspicuously unverified fallback for offline/scripted models."""
    return ModelProfile(
        canonical_name=model, aliases=(), context_window_tokens=None,
        native_context_window_tokens=None, extended_context_window_tokens=None,
        endpoint_context_window_tokens=None, context_limit_kind="unverified",
        context_source="unverified: no registered model profile",
        context_uncertainty="Unknown model; no context limit is asserted or enforced.",
        text_estimator="unicode_chars_v1", text_estimate_offset=0,
        text_safety_factor=1.35,
        text_fixed_margin=32,
        safety_margin_source="unverified compatibility margin, not calibrated for this model",
        image_estimator="decoded_pixels_v0",
        image_patch_size=16, image_merge_size=2, image_min_pixels=65536,
        image_max_pixels=16777216, image_special_tokens=2,
        image_source="legacy decoded-pixel compatibility upper bound",
        image_uncertainty="Unknown image tokenizer; decoded pixels are retained as a deliberately loose compatibility upper bound.",
        profile_status="unverified_conservative_approximation",
    )


def get_model_profile(model: str, *, strict: bool = False) -> ModelProfile:
    folded = model.casefold()
    for profile in registered_model_profiles():
        if folded in {profile.canonical_name.casefold(), *(x.casefold() for x in profile.aliases)}:
            return profile
    if strict:
        raise ValueError(f"no reviewed estimation profile for model {model!r}")
    return conservative_compatibility_profile(model)


_APPROXIMATE_TOKEN = re.compile(
    r"<\|[^|>]+\|>|[A-Za-z_]+|[0-9]+|[^\w\s]|[^\x00-\x7f]"
)


def approximate_text_tokens(text: str) -> int:
    """Small dependency-free approximation for Qwen-family BPE tokenization.

    CJK and other wide-script codepoints are counted individually. Common ASCII
    words often occupy one token; an eight-character ceiling approximates longer
    BPE pieces. Numbers use three characters per token and punctuation one each.
    Qwen chat-template markers count as their registered special token.
    """
    count = 0
    for piece in _APPROXIMATE_TOKEN.findall(text):
        if piece.startswith("<|"):
            count += 1
        elif piece.isascii() and (piece[0].isalpha() or piece[0] == "_"):
            count += math.ceil(len(piece) / 8)
        elif piece.isascii() and piece.isdigit():
            count += math.ceil(len(piece) / 3)
        elif len(piece) == 1 and unicodedata.category(piece).startswith("M"):
            continue
        else:
            count += 1
    return count


def qwen_image_tokens(width: int, height: int, profile: ModelProfile) -> tuple[int, int, int]:
    """Apply Qwen's smart-resize patch grid and two vision boundary tokens."""
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    factor = profile.image_patch_size * profile.image_merge_size
    resized_h = max(factor, round(height / factor) * factor)
    resized_w = max(factor, round(width / factor) * factor)
    pixels = resized_h * resized_w
    if pixels > profile.image_max_pixels:
        beta = math.sqrt((height * width) / profile.image_max_pixels)
        resized_h = max(factor, math.floor(height / beta / factor) * factor)
        resized_w = max(factor, math.floor(width / beta / factor) * factor)
    elif pixels < profile.image_min_pixels:
        beta = math.sqrt(profile.image_min_pixels / (height * width))
        resized_h = math.ceil(height * beta / factor) * factor
        resized_w = math.ceil(width * beta / factor) * factor
    patch_tokens = (resized_h // factor) * (resized_w // factor)
    return patch_tokens + profile.image_special_tokens, resized_w, resized_h


def _data_image_size(url: str) -> tuple[int, int]:
    if not url.startswith("data:image/") or ";base64," not in url:
        raise ValueError("request estimation needs captured image data URLs")
    encoded = url.split(",", 1)[1]
    raw = base64.b64decode(encoded, validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        return image.size


def _text_payload(body: Mapping[str, Any]) -> tuple[str, list[tuple[str, str]]]:
    """Build the tokenizer input approximation without counting base64 bytes."""
    fragments: list[str] = []
    image_urls: list[tuple[str, str]] = []
    messages = body.get("messages", [])
    for i, message in enumerate(messages):
        fragments.append(f"<|im_start|>{message.get('role', '')}\n")
        content = message.get("content")
        if isinstance(content, str):
            fragments.append(content)
        elif isinstance(content, list):
            for j, block in enumerate(content):
                if block.get("type") == "text":
                    fragments.append(str(block.get("text", "")))
                elif block.get("type") == "image_url":
                    image_urls.append((f"/messages/{i}/content/{j}/image_url/url", block["image_url"]["url"]))
                else:
                    fragments.append(json.dumps(block, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        elif content is not None:
            fragments.append(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        for key in ("name", "tool_call_id", "tool_calls", "reasoning_content"):
            if key in message:
                fragments.append(json.dumps(message[key], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        fragments.append("<|im_end|>\n")
    fragments.append("<|im_start|>assistant\n")
    if body.get("tools"):
        fragments.append(json.dumps(body["tools"], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if "tool_choice" in body:
        fragments.append(json.dumps(body["tool_choice"], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return "".join(fragments), image_urls


def estimate_chat_request(body: Mapping[str, Any], *, profile: ModelProfile | None = None,
                          strict: bool = False) -> RequestTokenEstimate:
    model = body.get("model")
    if not isinstance(model, str) or not model:
        raise ValueError("request body needs a model")
    selected = profile or get_model_profile(model, strict=strict)
    output_limit = body.get("max_tokens", body.get("max_completion_tokens"))
    if type(output_limit) is not int or output_limit <= 0:
        raise ValueError("explicit positive output token cap required")
    text, image_urls = _text_payload(body)
    text_tokens = approximate_text_tokens(text) + selected.text_estimate_offset
    images: list[ImageTokenEstimate] = []
    for reference, url in image_urls:
        width, height = _data_image_size(url)
        if selected.image_estimator == "qwen_vl_patch32_v1":
            tokens, resized_w, resized_h = qwen_image_tokens(width, height, selected)
        elif selected.image_estimator == "decoded_pixels_v0":
            tokens, resized_w, resized_h = width * height, width, height
        else:
            raise ValueError(f"unsupported image estimator {selected.image_estimator!r}")
        images.append(ImageTokenEstimate(reference, width, height, resized_w, resized_h,
                                         tokens, selected.image_source))
    image_tokens = sum(row.tokens for row in images)
    estimate = text_tokens + image_tokens
    upper = math.ceil(text_tokens * selected.text_safety_factor) + selected.text_fixed_margin + image_tokens
    total_upper = upper + output_limit
    fits = None if selected.context_window_tokens is None else total_upper <= selected.context_window_tokens
    source = (f"profile={selected.canonical_name}; text={selected.text_estimator}; "
              f"image={selected.image_estimator}; context={selected.context_source}; "
              f"context_limit_kind={selected.context_limit_kind}; "
              f"safety_margin={selected.safety_margin_source}; status={selected.profile_status}")
    uncertainty = f"{selected.context_uncertainty} {selected.image_uncertainty}"
    return RequestTokenEstimate(model, selected.canonical_name, text_tokens, image_tokens,
        estimate, upper, output_limit, selected.context_window_tokens, fits, source,
        uncertainty, tuple(images))
