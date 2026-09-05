from pathlib import Path
from types import SimpleNamespace
from src.agent.correction.multifloor import (
    ValidatedFloorLadder,
    assemble_multifloor_geometry,
)
from src.agent.correction.schema import CorrectedGeometryV3

fixture = Path('tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json')
source = CorrectedGeometryV3.model_validate_json(fixture.read_text(encoding='utf-8'))
one_floor = source.model_copy(update={'floors': [source.floors[0]], 'windows': [], 'facade_segments': []})
hand_level = SimpleNamespace(
    floor_index=0,
    z_floor_m=12.34,
    ceiling_height_m=5.57,
)
ladder = ValidatedFloorLadder((hand_level,))
print('ALT_PATH=PUBLIC_VALIDATED_CARRIER_DIRECT_CONSTRUCTOR')
print('ALT_CARRIER_EXPORTED=', ValidatedFloorLadder.__name__)
print('ALT_LEVEL_RUNTIME_TYPE=', type(tuple(ladder)[0]).__name__)
print('ALT_INPUT_Z=', hand_level.z_floor_m, hand_level.ceiling_height_m)
try:
    assembled = assemble_multifloor_geometry(ladder, [one_floor])
except Exception as exc:
    print('ALT_RESULT=REJECTED')
    print('ALT_ERROR=', type(exc).__name__, str(exc))
else:
    print('ALT_RESULT=ASSEMBLED')
    print('ALT_OUTPUT_Z=', [(floor.z_floor, floor.ceiling_height) for floor in assembled.floors])
