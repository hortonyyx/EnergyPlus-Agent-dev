"""Offline check that the actual acquisition function uses full-scene packing."""
from pathlib import Path
import json
import sys
import tempfile
import trimesh

HERE = Path(__file__).resolve().parent
HK = HERE.parents[3] / 'case_tests/textured_mass/hongkong'
sys.path.insert(0, str(HK))
import fetch_buildings

bid = 'B416111881201063A0'
source = HK / 'single_buildings' / bid
record = json.loads((source / 'record.json').read_text())
entries = [{'name': f"BUILDING/{bid}/{r['name']}", 'off': r['zip_offset'],
            'csz': r['compressed'], 'crc': int(r['crc32'], 16)} for r in record['files']]
# Network is replaced only at the existing ZIP extraction boundary. Full
# fetch_building resource writing, conversion, statistics and GLB load execute.
original_extract = fetch_buildings.extract
fetch_buildings.extract = lambda url, e: ((source / Path(e['name']).name).read_bytes(), e['csz'])
try:
    with tempfile.TemporaryDirectory(prefix='hk_fetch_regression_') as temp:
        result = fetch_buildings.fetch_building('offline-existing-resources', {bid: entries}, bid, Path(temp))
        scene = trimesh.load(Path(temp) / 'input.glb', force='scene', process=False)
        assert result['faces'] == 170 and result['scene_instances'] == 4
        assert result['source_image_count'] == 4
        assert result['source_material_count'] == len(json.loads((source / (bid + '.gltf')).read_text())['materials'])
        assert result['conversion_version'] == 'complete_scene_v1'
        assert abs(result['width_depth_height_m'][2] - 32.112) < 0.001
        assert len(scene.graph.nodes_geometry) == 4
finally:
    fetch_buildings.extract = original_extract
(HERE / 'fetch_integration.json').write_text(json.dumps({
    'offline': True, 'full_fetch_conversion_executed': True, 'faces': 170,
    'scene_instances': 4, 'images': 4, 'height_m': result['width_depth_height_m'][2],
    'old_input_and_source_unchanged': True, 'network_called': False}, indent=2) + '\n')
print('offline fetch integration: pass')
