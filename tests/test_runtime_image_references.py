"""Exact wire reconstruction, original pixels and independent reader checks."""

import asyncio
import base64
import hashlib
import json

import pytest

from src.agent.runtime_behaviour import _captured
from src.agent_runtime.store import json_bytes
from test_agent_runtime import MESSAGES, response, runtime


def test_new_wire_requests_and_injections_reconstruct_without_embedded_images(tmp_path):
    engine = runtime(tmp_path, [response(("v", "view", {})), response(text="Done")])
    with engine.store as store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "completed"
        requests = [e.payload for e in store.events if e.payload.event_type == "adapter_request"]
        for payload, sent in zip(requests, engine.adapter.requests, strict=True):
            assert store.capture_bytes(payload.final_request_body) == sent
            assert hashlib.sha256(sent).hexdigest() == payload.wire_sha256
            assert _captured(payload.final_request_body, store.directory) == json.loads(sent)
        captured = requests[-1].final_request_body
        assert captured.kind == "image_references"
        assert b"base64," not in store.get_bytes(captured.blob)
        assert len(captured.images) == 1
        image = requests[-1].images[0]
        assert store.get_bytes(image.original) == store.get_bytes(image.sent)
        assert captured.images[0].image == image.sent
        assert any(i.content.kind == "image_references" for i in requests[-1].injected_content)
        store.validate()


@pytest.mark.parametrize("shape", ["openai", "anthropic", "mcp"])
def test_protocol_images_reconstruct_exact_text_including_unusual_base64(tmp_path, shape):
    # Zh== is accepted base64 with nonzero unused bits, decoding to b'f'.
    encoded = "Zh=="
    block = {
        "openai": {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}},
        "anthropic": {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": encoded}},
        "mcp": {"type": "image", "mimeType": "image/png", "data": encoded},
    }[shape]
    original = {"a/b~c": [block, block], "text": "保留原文 \\ / \""}
    engine = runtime(tmp_path, [])
    with engine.store as store:
        captured = store.capture(original)
        assert store.capture_bytes(captured) == json_bytes(original)
        assert len(captured.images) == 2
        assert captured.images[0].image == captured.images[1].image
        assert captured.images[0].base64_text is not None
        assert store.get_bytes(captured.images[0].image) == base64.b64decode(encoded)
        assert store.resolve(captured) == original


@pytest.mark.parametrize("damage", ["image", "template", "wire_hash", "spelling", "duplicate"])
def test_corrupt_or_inconsistent_references_are_rejected(tmp_path, damage):
    engine = runtime(tmp_path, [])
    with engine.store as store:
        captured = store.capture({"type": "image_url", "image_url": {"url": "data:image/png;base64,Zh=="}})
        if damage in {"image", "template", "spelling"}:
            ref = {"image": captured.images[0].image, "template": captured.blob,
                   "spelling": captured.images[0].base64_text}[damage]
            (store.directory / ref.uri).write_bytes(b"corrupt")
        elif damage == "duplicate":
            captured = captured.model_copy(update={"images": captured.images * 2})
        else:
            captured = captured.model_copy(update={"wire_sha256": "0" * 64})
        with pytest.raises(ValueError):
            store.capture_bytes(captured)
