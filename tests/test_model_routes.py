"""Role replacement, capability mismatch and credential isolation, offline."""

from copy import deepcopy

import pytest
import yaml

from src.agent.llm import LLM_CONFIG_ENV, create_llm, load_llm_section
from src.agent.model_routes import ModelRoutes


@pytest.fixture
def routes():
    return dict(schema_version=1, default_role="modeling",
        services={
            "own_server": dict(provider="openai", base_url="http://localhost:1234/v1",
                               api_key_env="EP_TEST_LOCAL_KEY"),
            "remote": dict(provider="openai", base_url="https://example.invalid/v1",
                           api_key_env="EP_TEST_REMOTE_KEY"),
        },
        models={
            "small": dict(service="own_server", model_name="deployment-a", temperature=0.7,
                          max_tokens=1000, capabilities={"image_input": True, "tool_calls": True}),
            "fast": dict(service="remote", model_name="deployment-b", temperature=0.2,
                         max_tokens=500, capabilities={"image_input": True, "tool_calls": True}),
        },
        roles={
            "modeling": dict(model="small", requires=["image_input", "tool_calls"]),
            "visual_review": dict(model="fast", requires=["image_input"]),
        })


def test_same_roles_allow_different_deployments_and_shared_models(routes, monkeypatch):
    monkeypatch.setenv("EP_TEST_LOCAL_KEY", "dummy-local")
    monkeypatch.setenv("EP_TEST_REMOTE_KEY", "dummy-remote")
    first = ModelRoutes.model_validate(routes)
    assert first.chat_config("modeling")["base_url"] == "http://localhost:1234/v1"
    swapped = deepcopy(routes)
    swapped["roles"]["modeling"]["model"] = "fast"
    second = ModelRoutes.model_validate(swapped)
    assert second.chat_config("modeling") == second.chat_config("visual_review")
    assert second.chat_config("modeling")["model_name"] == "deployment-b"
    assert first.chat_config("modeling")["model_name"] == "deployment-a"


def test_unknown_role_never_inherits_default(routes, monkeypatch):
    monkeypatch.setenv("EP_TEST_LOCAL_KEY", "dummy-local")
    config = ModelRoutes.model_validate(routes)
    assert config.chat_config(None) == config.chat_config("modeling")
    with pytest.raises(ValueError, match="not configured"):
        config.chat_config("ocr")
    routes.pop("default_role")
    with pytest.raises(ValueError, match="not configured"):
        ModelRoutes.model_validate(routes).chat_config(None)


@pytest.mark.parametrize("capabilities", [{}, {"image_input": None}, {"image_input": False}])
def test_unknown_or_missing_capability_refuses_binding(routes, capabilities):
    routes["models"]["fast"]["capabilities"] = capabilities
    with pytest.raises(ValueError, match="unconfirmed capabilities"):
        ModelRoutes.model_validate(routes)


def test_only_selected_service_requires_credentials(routes, monkeypatch):
    monkeypatch.setenv("EP_TEST_LOCAL_KEY", "dummy-local")
    monkeypatch.delenv("EP_TEST_REMOTE_KEY", raising=False)
    config = ModelRoutes.model_validate(routes)
    assert config.chat_config("modeling")["api_key"] == "dummy-local"
    with pytest.raises(ValueError, match="EP_TEST_REMOTE_KEY"):
        config.chat_config("visual_review")
    assert "dummy-local" not in config.model_dump_json()


@pytest.mark.parametrize("broken", ["service", "model", "default", "capability_type"])
def test_bad_configuration_is_rejected(routes, broken):
    if broken == "service":
        routes["models"]["small"]["service"] = "missing"
    elif broken == "model":
        routes["roles"]["modeling"]["model"] = "missing"
    elif broken == "default":
        routes["default_role"] = "missing"
    else:
        routes["models"]["small"]["capabilities"]["image_input"] = "yes"
    with pytest.raises(ValueError):
        ModelRoutes.model_validate(routes)


def test_existing_client_entry_consumes_routes(routes, monkeypatch, tmp_path):
    path = tmp_path / "roles.yaml"
    path.write_text(yaml.safe_dump(routes))
    monkeypatch.setenv(LLM_CONFIG_ENV, str(path))
    monkeypatch.setenv("EP_TEST_LOCAL_KEY", "dummy-local")
    seen = []
    monkeypatch.setattr("src.agent.llm.init_chat_model", lambda *a, **k: seen.append((a, k)))
    create_llm(node_name="modeling")
    assert seen[0][0] == ("openai:deployment-a",)
    assert seen[0][1]["base_url"] == "http://localhost:1234/v1"
    assert seen[0][1]["api_key"] == "dummy-local"
    with pytest.raises(ValueError, match="not configured"):
        load_llm_section("ocr")
