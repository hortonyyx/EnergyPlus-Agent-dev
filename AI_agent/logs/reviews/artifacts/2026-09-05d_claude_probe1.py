import copy
import pickle
import types
from pathlib import Path

from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
from src.agent.correction.evidence_contract import (
    CorrectionEvidenceBundleArtifactV1,
    EvidenceContractError,
    finalize_bundle,
)
from src.agent.correction import multifloor as m
from src.agent.correction.multifloor import (
    MultiFloorAssemblyError,
    ValidatedFloorLadder,
    assemble_multifloor_geometry,
    derive_floor_ladder,
)
from src.agent.correction.schema import CorrectedGeometryV3

raw = Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_east_as_drawn.json').read_bytes()
art = adapt_as_drawn_elevation(raw, input_id='claude_probe_east', facade_ref='east')
fixture = Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json')
source = CorrectedGeometryV3.model_validate_json(fixture.read_text(encoding='utf-8'))
one_floor = source.model_copy(update={'floors': [source.floors[0]], 'windows': [], 'facade_segments': []})

ordered = sorted(art.bundle.floor_level_claims, key=lambda c: c.z_m)
drift = {ordered[0].structure_line_id: 12.34, ordered[1].structure_line_id: 17.91}
drifted_claims = [
    c.model_copy(update={'z_m': drift[c.structure_line_id]})
    if c.structure_line_id in drift else c
    for c in art.bundle.floor_level_claims
]
drifted_art = CorrectionEvidenceBundleArtifactV1(
    bundle=finalize_bundle(art.bundle.model_copy(update={'floor_level_claims': drifted_claims})),
    frozen_sources=art.frozen_sources,
)


def outcome(label, thunk):
    try:
        thunk()
    except Exception as exc:
        print(label, '= REJECTED', type(exc).__name__, getattr(exc, 'code', ''), str(exc)[:140])
    else:
        print(label, '= !!!ACCEPTED!!!')


honest_ladder = derive_floor_ladder(art)
print('HONEST_BASELINE=', [(round(x.z_floor_m, 6), round(x.ceiling_height_m, 6)) for x in honest_ladder][:2])

# ── CLAUDE PROBE 1: copy.deepcopy() of a HONEST ladder, then mutate the copy's
# __dict__ DIRECTLY (bypassing __setattr__/FrozenInstanceError entirely -- no
# object.__setattr__ call anywhere in this probe) to swap in a drifted artifact.
copied = copy.deepcopy(honest_ladder)
print('DEEPCOPY_TYPE_MATCHES=', type(copied) is ValidatedFloorLadder, 'DEEPCOPY_ISINSTANCE=', isinstance(copied, ValidatedFloorLadder))
copied.__dict__['_artifact'] = drifted_art
outcome('PROBE1_DEEPCOPY_THEN_DICT_MUTATE', lambda: assemble_multifloor_geometry(copied, [one_floor]))

# ── CLAUDE PROBE 2: pickle round-trip of the honest ladder (does __reduce_ex__
# even work for a class minted inside a closure? if it does, does the round
# trip preserve or lose the seal?) ──
try:
    blob = pickle.dumps(honest_ladder)
    restored = pickle.loads(blob)
    print('PROBE2_PICKLE_ROUNDTRIP= SUCCEEDED', type(restored).__name__)
    restored.__dict__['_artifact'] = drifted_art
    outcome('PROBE2_PICKLE_ROUNDTRIP_THEN_MUTATE', lambda: assemble_multifloor_geometry(restored, [one_floor]))
except Exception as exc:
    print('PROBE2_PICKLE_ROUNDTRIP= FAILED', type(exc).__name__, str(exc)[:160])

# ── CLAUDE PROBE 3: call the "module-private" minter `_mint_sealed_ladder`
# DIRECTLY (bypassing derive_floor_ladder's own pre-gate `_levels_of(...)`
# call entirely) with a DRIFTED (never-gated-at-mint-time) artifact. Tests
# whether skipping the mint-side pre-check matters, given the exit-side
# re-derivation. Access is via ordinary module attribute (no __closure__ /
# introspection of cells) -- `_mint_sealed_ladder` sits in `__all__`'s
# complement but is still a plain importable module attribute.
print('PROBE3_MINTER_ACCESSIBLE_WITHOUT_INTROSPECTION=', hasattr(m, '_mint_sealed_ladder'))
forged_via_private_minter = m._mint_sealed_ladder(drifted_art)
print('PROBE3_MINT_SUCCEEDED_BYPASSING_DERIVE_GATE=', type(forged_via_private_minter).__name__)
outcome('PROBE3_PRIVATE_MINTER_UNGATED_ARTIFACT', lambda: assemble_multifloor_geometry(forged_via_private_minter, [one_floor]))

# ── CLAUDE PROBE 4: __class__ reassignment -- build an ordinary, totally
# unrelated object (plain instance with a __dict__, NOT ValidatedFloorLadder,
# no dataclass machinery, no __init__/__init_subclass__ ever invoked for the
# target class), set `_artifact` via a completely NORMAL attribute assignment,
# then coerce its __class__ to ValidatedFloorLadder. Tests whether isinstance
# can be won without ever touching __new__/__init__/__setattr__ of the sealed
# class at all.
class _Blank:
    pass


blank = _Blank()
blank._artifact = drifted_art
try:
    blank.__class__ = ValidatedFloorLadder
    print('PROBE4_CLASS_REASSIGN= SUCCEEDED, isinstance=', isinstance(blank, ValidatedFloorLadder))
    outcome('PROBE4_CLASS_REASSIGNMENT_FORGERY', lambda: assemble_multifloor_geometry(blank, [one_floor]))
except Exception as exc:
    print('PROBE4_CLASS_REASSIGN= FAILED', type(exc).__name__, str(exc)[:160])

# ── CLAUDE PROBE 5 (confirmation, not a new class): the evidence-contract
# pydantic models here use `ConfigDict(extra="forbid", strict=True)` with NO
# `frozen=True` -- so ordinary attribute assignment (not object.__setattr__)
# on a REAL, already-derive-passing artifact should mutate it in place. Does
# in-place `.bundle = <drifted>` on the SAME real artifact object (no swap of
# _artifact at all, no new artifact constructed) survive re-derivation?
mutable_check_art = adapt_as_drawn_elevation(raw, input_id='claude_probe_east_2', facade_ref='east')
ladder2 = derive_floor_ladder(mutable_check_art)
print('PYDANTIC_ORDINARY_ASSIGN_ALLOWED=', end=' ')
try:
    mutable_check_art.bundle = drifted_art.bundle  # plain assignment, no object.__setattr__
    print(True)
except Exception as exc:
    print(False, type(exc).__name__)
outcome('PROBE5_INPLACE_BUNDLE_MUTATE_SAME_ARTIFACT_OBJECT', lambda: assemble_multifloor_geometry(ladder2, [one_floor]))
