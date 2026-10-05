"""Offline pytest configuration for the separately proposed Agent registration.

This is an integration rehearsal, never a production bypass. The same verifier
checks all current file bytes and actual MCP catalogs. The only test fixture
redirected is the registry JSON source used by registry-copy tests; their
historical, immutability and tamper assertions remain unchanged. Production
agent_versions.json is byte-guarded and must still be registered by its owner.
"""
import hashlib
from pathlib import Path

from src.agent_runtime import agent_registry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRODUCTION = ROOT / 'src/agent_runtime/agent_versions.json'
PROPOSAL = HERE / 'validation/registration_proposal.json'


def pytest_configure(config):
    config._a5r_registry_bytes = PRODUCTION.read_bytes()
    config._a5r_registry_relative = agent_registry.REGISTRY_RELATIVE_PATH
    agent_registry.agent_version_record(ROOT, registry_path=PROPOSAL, verify=True)
    agent_registry.REGISTRY_RELATIVE_PATH = PROPOSAL


def pytest_collection_modifyitems(items):
    for item in items:
        module = item.module
        if module.__name__.split('.')[-1] == 'test_runtime_agent_registry':
            module.REGISTRY = PROPOSAL


def pytest_report_header():
    return ('A5-R integration rehearsal: explicit proposed registry ' +
            hashlib.sha256(PROPOSAL.read_bytes()).hexdigest() +
            '; default registry untouched; all hash/catalog verifiers enabled')


def pytest_unconfigure(config):
    if hasattr(config, '_a5r_registry_relative'):
        agent_registry.REGISTRY_RELATIVE_PATH = config._a5r_registry_relative
        assert PRODUCTION.read_bytes() == config._a5r_registry_bytes
