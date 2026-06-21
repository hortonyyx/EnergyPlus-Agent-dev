from src.agent.roles import ALIASES, CANONICAL_ROLES, normalize


def test_normalize_aliases_and_canonical_roles():
    assert "unknown" in CANONICAL_ROLES
    assert ALIASES["meeting room"] == "meeting"
    assert ALIASES["entrance lobby"] == "lobby"
    assert normalize(" Meeting Room ") == "meeting"
    assert normalize("entrance-lobby") == "lobby"
    assert normalize("Office") == "office"
    assert normalize("not a real role") == "not a real role"
