"""Stateless ChatGPT subscription Responses protocol, with no credential discovery.

The local output allowance reserves budget; the subscription preview does not
accept a wire output cap. Full opaque output items are journalled and replayed.
Protocol source: https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import replace
from time import perf_counter

import httpx

from src.harness_contracts import (AdapterRequestPayload, ImageTransmission,
    InjectedContent, ModelResponsePayload, ParameterAudit, ParametersNotReported,
    ParametersUnverified, ResponseToolCall, ThinkingSummary, ThinkingTokenCount,
    ThinkingUnavailable, UsageMissing, UsageReported)
from .adapter import ParsedResponse, PreparedRequest, decode_image_url
from .estimation import (RequestTokenEstimate, approximate_text_tokens,
    estimate_chat_request, get_model_profile)
from .failures import ModelServiceError, _sanitize, http_failure
from .store import json_bytes


ENDPOINT = "https://api.openai.com/v1/responses"
TOOL_NAMESPACE = "runtime"
# Preview-unsupported fields may be audited locally, but never reach the wire.
_OMITTED = frozenset({"max_tokens", "max_completion_tokens", "max_output_tokens",
    "temperature", "top_p", "top_logprobs", "background", "conversation",
    "max_tool_calls", "metadata", "moderation", "multi_agent", "prompt",
    "prompt_cache_retention", "safety_identifier", "truncation", "user",
    "previous_response_id"})
_ALLOWED = frozenset({"reasoning_effort", "reasoning", "text", "tool_choice",
    "parallel_tool_calls", "prompt_cache_key", "service_tier"})


def _allowance(parameters):
    value = parameters.get("max_tokens", parameters.get("max_completion_tokens",
        parameters.get("max_output_tokens")))
    if type(value) is not int or value <= 0:
        raise ValueError("explicit positive local output allowance required")
    return value


def _content(content, *, assistant=False):
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": "output_text" if assistant else "input_text", "text": content}]
    if not isinstance(content, list):
        raise ValueError("message content must be text or blocks")
    blocks = []
    for block in content:
        kind = block.get("type")
        if kind in {"text", "input_text", "output_text"}:
            text = block.get("text")
            if not isinstance(text, str):
                raise ValueError("invalid text block")
            blocks.append({"type": "output_text" if assistant else "input_text", "text": text})
        elif kind in {"image_url", "input_image"} and not assistant:
            image = block["image_url"]
            url = image["url"] if isinstance(image, dict) else image
            decode_image_url(url)
            detail = image.get("detail", block.get("detail", "high")) if isinstance(image, dict) else block.get("detail", "high")
            if detail not in {"auto", "low", "high", "original"}:
                raise ValueError("invalid image detail")
            blocks.append({"type": "input_image", "image_url": url, "detail": detail})
        else:
            raise ValueError("unsupported logical Responses content block")
    return blocks


def _convert_messages(messages):
    native, origins = [], []
    for index, message in enumerate(messages):
        role = message["role"]
        if role == "assistant" and "responses_output" in message:
            items = message["responses_output"]
            if not isinstance(items, list) or not all(isinstance(item, dict) and isinstance(item.get("type"), str) for item in items):
                raise ValueError("invalid recorded Responses output")
            native.extend(copy.deepcopy(items))
            origins.extend([index] * len(items))
            continue
        if role == "tool":
            item = {"type": "function_call_output", "call_id": message["tool_call_id"],
                    "output": _content(message.get("content"))}
            native.append(item)
            origins.append(index)
            continue
        if role not in {"system", "developer", "user", "assistant"}:
            raise ValueError("unsupported message role")
        blocks = _content(message.get("content"), assistant=role == "assistant")
        if blocks:
            native.append({"role": "developer" if role == "system" else role, "content": blocks})
            origins.append(index)
        if role == "assistant":
            for call in message.get("tool_calls", []):
                arguments = call["function"]["arguments"]
                if not isinstance(json.loads(arguments), dict):
                    raise ValueError("tool arguments must be an object")
                native.append({"type": "function_call", "call_id": call["id"],
                    "name": call["function"]["name"], "namespace": call.get("namespace", TOOL_NAMESPACE),
                    "arguments": arguments})
                origins.append(index)
    return native, origins


def build_responses_body(*, model, messages, tools, parameters):
    """Build the exact subscription body without a store or credentials."""
    _allowance(parameters)
    unknown = set(parameters) - _OMITTED - _ALLOWED
    if unknown:
        raise ValueError("unreviewed Responses parameters: " + ", ".join(sorted(unknown)))
    native, _ = _convert_messages(messages)
    body = {"model": model, "input": native, "store": False, "stream": True,
            "include": ["reasoning.encrypted_content"]}
    body.update({key: copy.deepcopy(value) for key, value in parameters.items() if key in _ALLOWED and key != "reasoning_effort"})
    if "reasoning_effort" in parameters:
        if "reasoning" in parameters:
            raise ValueError("reasoning and reasoning_effort cannot both be specified")
        body["reasoning"] = {"effort": parameters["reasoning_effort"]}
    if tools:
        functions, seen = [], set()
        for tool in tools:
            if tool.get("type") != "function":
                raise ValueError("only locally executed function tools are supported")
            function = tool["function"]
            name = function["name"]
            if not isinstance(name, str) or not name or name in seen:
                raise ValueError("invalid or duplicate local function name")
            seen.add(name)
            functions.append({"type": "function", "name": name,
                "description": function.get("description", ""),
                "parameters": copy.deepcopy(function["parameters"]), "strict": False})
        body["tools"] = [{"type": "namespace", "name": TOOL_NAMESPACE,
                          "description": "Locally executed runtime tools", "tools": functions}]
    return body


def _walk_images(value, pointer=""):
    if isinstance(value, dict):
        if value.get("type") == "input_image":
            yield pointer + "/image_url", value
        for key, child in value.items():
            yield from _walk_images(child, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_images(child, pointer + f"/{index}")


def estimate_responses_request(body, *, output_token_limit, profile=None, strict=False):
    """Estimate actual Responses history/schema; output allowance is local only."""
    if type(output_token_limit) is not int or output_token_limit <= 0:
        raise ValueError("explicit positive local output allowance required")
    model = body.get("model")
    if not isinstance(model, str) or not model:
        raise ValueError("request body needs a model")
    selected = profile or get_model_profile(model, strict=strict)
    text_body = copy.deepcopy(body)
    images = []
    from src.harness_contracts.events import _resolve_json_pointer
    for reference, block in _walk_images(body):
        # Delegate all model-specific image formulas to the shared estimator.
        single = estimate_chat_request({"model": model, "max_tokens": output_token_limit,
            "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {
                "url": block["image_url"], "detail": block.get("detail", "high")}}]}]}, profile=selected)
        images.append(replace(single.images[0], request_reference=reference))
        _resolve_json_pointer(text_body, reference.rsplit("/", 1)[0])["image_url"] = "[captured image]"
    text_tokens = approximate_text_tokens(json_bytes(text_body).decode("utf-8")) + selected.text_estimate_offset
    image_tokens = sum(image.tokens for image in images)
    upper = math.ceil(text_tokens * selected.text_safety_factor) + selected.text_fixed_margin + image_tokens
    allowance = selected.reasoning_token_allowance
    fits = None if selected.context_window_tokens is None else upper + output_token_limit + allowance <= selected.context_window_tokens
    return RequestTokenEstimate(model, selected.canonical_name, text_tokens, image_tokens,
        text_tokens + image_tokens, upper, output_token_limit, allowance,
        selected.context_window_tokens, fits,
        f"responses_json_v1; profile={selected.canonical_name}; text={selected.text_estimator}; image={selected.image_estimator}; safety_margin={selected.safety_margin_source}",
        f"{selected.context_uncertainty} {selected.image_uncertainty} Local output allowance is not a provider cap. {selected.reasoning_allowance_source}", tuple(images))


def estimate_responses_messages(*, model, messages, tools, parameters, strict=False, profile=None):
    return estimate_responses_request(build_responses_body(model=model, messages=messages,
        tools=tools, parameters=parameters), output_token_limit=_allowance(parameters), profile=profile, strict=strict)


def prepare_responses_request(*, store, model, messages, message_sources, tools,
        tool_source, parameters, versions, image_originals=None, model_profile=None,
        strict_model_profile=False, reasoning_history="all"):
    if len(messages) != len(message_sources):
        raise ValueError("every request message needs a recorded source")
    if reasoning_history not in {"all", "current_tool_chain"}:
        raise ValueError("unsupported reasoning_history")
    body = build_responses_body(model=model, messages=messages, tools=tools, parameters=parameters)
    _, origins = _convert_messages(messages)
    injections = [InjectedContent(request_location=f"/input/{i}",
        content=store.capture(item), source=message_sources[origin])
        for i, (item, origin) in enumerate(zip(body["input"], origins, strict=True))]
    if tools:
        injections.append(InjectedContent(request_location="/tools", content=store.capture(body["tools"]), source=tool_source))
    images = []
    for reference, block in _walk_images(body):
        data, mime = decode_image_url(block["image_url"])
        sent = store.put_bytes(data, mime)
        original = (image_originals or {}).get(sent.sha256, sent)
        store.get_bytes(original)
        images.append(ImageTransmission(original=original, sent=sent, request_reference=reference))
    wire = json_bytes(body)
    captured = store.capture(body, force_blob=True)
    if store.capture_bytes(captured) != wire:
        raise ValueError("stored Responses request differs from wire")
    payload = AdapterRequestPayload(adapter="openai-responses-http-v1", final_request_body=captured,
        wire_sha256=hashlib.sha256(wire).hexdigest(), injected_content=tuple(injections), images=tuple(images),
        parameters=ParameterAudit(requested=copy.deepcopy(parameters),
            provider_report=ParametersNotReported(reason="service does not attest applied parameters"),
            effect=ParametersUnverified(reason="subscription preview omits unsupported wire fields; output allowance is local only")), versions=versions)
    estimate = estimate_responses_request(body, output_token_limit=_allowance(parameters), profile=model_profile, strict=strict_model_profile)
    return PreparedRequest(body, wire, estimate, payload)


def _usage(raw):
    value = raw.get("usage") if isinstance(raw, dict) else None
    # Usage is numeric accounting data, never arbitrary provider error text.
    def numeric(value):
        if isinstance(value, dict):
            return {key: clean for key, child in value.items() if (clean := numeric(child)) is not None}
        return value if type(value) is int and value >= 0 else None
    clean = numeric(value)
    return UsageReported(raw_usage=clean) if clean else UsageMissing(reason="service omitted per-request usage")


def parse_responses_response(raw, request_event_id, store):
    usage = _usage(raw)
    visible, thinking, calls, runtime_calls = [], [], [], []
    assistant, error = {}, None
    finish = "length" if raw.get("status") == "incomplete" and (raw.get("incomplete_details") or {}).get("reason") == "max_output_tokens" else "stop"
    try:
        if raw.get("object") != "response" or not isinstance(raw.get("output"), list):
            raise ValueError("invalid Responses object")
        seen = set()
        for item in raw["output"]:
            kind = item["type"]
            if kind == "message":
                if item.get("role") != "assistant" or not isinstance(item.get("content"), list):
                    raise ValueError("invalid output message")
                for block in item["content"]:
                    if block.get("type") == "output_text":
                        if not isinstance(block.get("text"), str):
                            raise ValueError("invalid output text")
                        if block["text"].strip():
                            visible.append(block["text"])
                    elif block.get("type") == "refusal" and isinstance(block.get("refusal"), str) and block["refusal"].strip():
                        visible.append(block["refusal"])
            elif kind == "reasoning":
                for summary in item.get("summary", []):
                    if summary.get("type") == "summary_text" and isinstance(summary.get("text"), str) and summary["text"].strip():
                        thinking.append(ThinkingSummary(summary=summary["text"]))
            elif kind == "function_call" and raw.get("status") == "completed":
                if item.get("status", "completed") != "completed":
                    raise ValueError("unfinished function call")
                namespace = item.get("namespace")
                if namespace not in {None, TOOL_NAMESPACE}:
                    raise ValueError("foreign function namespace")
                call = ResponseToolCall(call_id=item["call_id"], tool_name=item["name"], full_arguments=json.loads(item["arguments"]))
                if call.call_id in seen:
                    raise ValueError("duplicate function call identity")
                seen.add(call.call_id)
                calls.append(call)
                runtime_call = {"type": "function", "id": call.call_id,
                    "function": {"name": call.tool_name, "arguments": item["arguments"]}}
                if namespace is not None:
                    runtime_call["namespace"] = namespace
                runtime_calls.append(runtime_call)
            # Unknown output items remain opaque, complete and replayable.
        count = ((raw.get("usage") or {}).get("output_tokens_details") or {}).get("reasoning_tokens")
        if type(count) is int and count >= 0:
            thinking.append(ThinkingTokenCount(tokens=count))
        assistant = {"role": "assistant", "content": "\n\n".join(visible) or None,
                     "responses_output": copy.deepcopy(raw["output"])}
        if calls:
            assistant["tool_calls"] = runtime_calls
            finish = "tool_calls"
        if raw.get("status") != "completed":
            error = "incomplete_response"
        elif not visible and not calls:
            error = "empty_response"
    except (ValueError, TypeError, KeyError, AttributeError):
        error = "malformed_response"
        calls, assistant = [], {}
    if not thinking:
        thinking = [ThinkingUnavailable(reason="no public reasoning summary or count; opaque output items retained for replay")]
    payload = ModelResponsePayload(request_event_id=request_event_id, visible_text=tuple(visible), tool_calls=tuple(calls),
        thinking=tuple(thinking), usage=usage, raw_response=store.capture(raw, force_blob=True))
    return ParsedResponse(payload, assistant, finish, error)


class HttpResponsesAdapter:
    """One OAuth request per send. Token renewal belongs to the injected provider.

Only response.completed is a successful terminal object. response.incomplete
returns failure evidence for the parser/truncation journal, never executable calls.
"""

    def __init__(self, *, token_provider, transport=None):
        self._token_provider = token_provider
        self.client = httpx.AsyncClient(transport=transport, follow_redirects=False)
        self.last_send_timing = {}

    async def close(self):
        await self.client.aclose()

    async def send(self, request: PreparedRequest, *, timeout: float):
        token, latest = "", {}
        self.last_send_timing = {}
        started = perf_counter()
        def failure(category, description, raw=None, retryable=False, error_type=None):
            usage = _usage(raw)
            if usage.kind == "missing":
                usage = _usage(latest)
            return ModelServiceError({"category": category, "retryable": retryable,
                "service_error_type": _sanitize(error_type, token)[:256] if error_type else None,
                "body_excerpt": _sanitize(description, token)[:2048],
                "usage_received": usage.kind == "reported"}, usage)
        try:
            try:
                token = await self._token_provider()
            except Exception:
                raise failure("permission_denied", "OAuth token provider failed") from None
            if not isinstance(token, str) or not token or token.startswith("sk-") or any(character.isspace() for character in token):
                token = ""  # Error sanitization must never call str.replace(None).
                raise failure("permission_denied", "OAuth bearer token unavailable or invalid")
            async with self.client.stream("POST", ENDPOINT, content=request.wire_bytes,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "text/event-stream"}, timeout=timeout) as response:
                if not response.is_success:
                    await response.aread()
                    error = http_failure(response, secret=token)
                    try:
                        error.usage = _usage(response.json())
                    except ValueError:
                        error.usage = _usage({})
                    error.details["usage_received"] = error.usage.kind == "reported"
                    raise error
                done_items, data = {}, []
                async def event():
                    nonlocal latest
                    if not data:
                        return None
                    event_raw = json.loads("\n".join(data))
                    if not isinstance(event_raw, dict):
                        raise ValueError("invalid SSE object")
                    kind = event_raw.get("type")
                    value = event_raw.get("response")
                    if value is None and event_raw.get("usage") is not None:
                        latest = {"usage": event_raw["usage"]}
                    if isinstance(value, dict):
                        if _usage(value).kind == "reported" or _usage(latest).kind != "reported":
                            latest = value
                    if kind == "response.output_item.done":
                        index, item = event_raw["output_index"], event_raw["item"]
                        if type(index) is not int or index < 0 or not isinstance(item, dict):
                            raise ValueError("invalid output item")
                        if index in done_items and done_items[index] != item:
                            raise ValueError("conflicting output item")
                        done_items[index] = copy.deepcopy(item)
                    if kind in {"response.failed", "error"}:
                        reason = (value or event_raw).get("error") or (value or {}).get("incomplete_details") or {}
                        raise failure("service_error",
                            json.dumps(reason), value, error_type=reason.get("type", reason.get("code")) if isinstance(reason, dict) else None)
                    if kind in {"response.completed", "response.incomplete"}:
                        expected = "completed" if kind == "response.completed" else "incomplete"
                        if not isinstance(value, dict) or value.get("object") != "response" or value.get("status") != expected or not isinstance(value.get("output"), list):
                            raise ValueError("invalid terminal response")
                        result = copy.deepcopy(value)
                        def diagnostic(value):
                            if isinstance(value, str):
                                return _sanitize(value, token)
                            if isinstance(value, dict):
                                return {key: diagnostic(child) for key, child in value.items()}
                            if isinstance(value, list):
                                return [diagnostic(child) for child in value]
                            return value
                        for key in ("error", "incomplete_details"):
                            if key in result:
                                result[key] = diagnostic(result[key])
                        # output_item.done is the complete opaque replay evidence.
                        for index, item in sorted(done_items.items()):
                            if index < len(result["output"]):
                                final = result["output"][index]
                                if any(key in final and final[key] != child for key, child in item.items()):
                                    raise ValueError("conflicting completed output")
                                result["output"][index] = {**item, **final}
                            elif index == len(result["output"]):
                                result["output"].append(item)
                            else:
                                raise ValueError("missing output item")
                        return result
                    return None
                async for line in response.aiter_lines():
                    if not line:
                        result = await event()
                        data = []
                        if result is not None:
                            return result
                    elif line.startswith("data:"):
                        data.append(line[5:].lstrip(" "))
                if data:
                    result = await event()
                    if result is not None:
                        return result
                raise failure("transport_error", "Responses stream ended without response.completed", retryable=True)
        except ModelServiceError:
            raise
        except httpx.TimeoutException:
            raise failure("timeout", "Responses stream timed out", retryable=True) from None
        except httpx.TransportError:
            raise failure("transport_error", "Responses stream transport interrupted", retryable=True) from None
        except (ValueError, TypeError, KeyError, AttributeError):
            raise failure("invalid_response", "Invalid Responses stream protocol") from None
        finally:
            self.last_send_timing["http_round_trip_seconds"] = perf_counter() - started


def present_tools(store, body, request, response, context_event_id):
    """Record logical tool results alongside actual native Responses input."""
    from src.harness_contracts import ToolPresentationPayload
    delivered = {event.payload.tool_execution_event_id for event in store.events if event.payload.event_type == "tool_presentation"}
    results = {item["call_id"]: item for item in body["input"] if item.get("type") == "function_call_output"}
    blocks = [block for item in body["input"] for block in (item.get("content") or item.get("output") or []) if isinstance(block, dict)]
    for event in store.events:
        payload = event.payload
        if payload.event_type != "tool_execution" or event.event_id in delivered or payload.call_id not in results or payload.shown_result.kind == "missing":
            continue
        original = store.resolve(payload.shown_result)
        result = results[payload.call_id]
        output = result["output"]
        logical_message = {"role": "tool", "tool_call_id": payload.call_id,
            "content": output if isinstance(output, str) else "".join(block["text"] for block in output if block.get("type") == "input_text")}
        kept, native_images = [], []
        for logical in original.get("image_blocks", []):
            native = _content([logical])[0]
            if native in blocks:
                kept.append(logical)
                native_images.append(native)
        if (logical_message != original["tool_message"] or kept != original.get("image_blocks", [])) and context_event_id is None:
            raise ValueError("changed logical tool presentation requires context evidence")
        actual = {**original, "tool_message": logical_message, "image_blocks": kept,
            "wire_tool_result": result, "wire_image_blocks": native_images,
            "conversion": "logical tool result and images converted to Responses input; image bytes unchanged"}
        store.append(ToolPresentationPayload(tool_execution_event_id=event.event_id,
            request_event_id=request.event_id, response_event_id=response.event_id,
            shown_result=store.capture(actual, force_blob=True), context_event_id=context_event_id,
            protocol_conversion="responses_v1"))
