"""Both runners admit the same inputs; evaluation reads either historical layout."""
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import pytest

from scripts.tool_scripts import run_bim_agent as runner
from src.agent import runtime_entry
from src.agent.bim_inputs import prepare_bim_inputs


@pytest.mark.parametrize('names', [('1f_view.png', '2f_view.png', 'South.png'),
                                  ('1f_view.png', 'East.png'), ('1f_view.png', '2f_view.png', 'West.png')])
def test_entrypoints_share_exact_input_payload(tmp_path, monkeypatch, names):
    images = tmp_path / 'originals'
    images.mkdir()
    for name in names:
        Image.new('RGB', (12, 8)).save(images / name)
    (images / 'private.json').write_text('not admitted')
    monkeypatch.setattr(runner, 'time', SimpleNamespace(time=lambda: 1000.0))
    seen = []
    def boundary(run, prompt, **kwargs):
        seen.append(run)
        return {'elapsed_seconds': 0, 'result': {'is_error': False}}
    monkeypatch.setattr(runner, 'subscription', boundary)
    old = tmp_path / 'claude'
    runner.run_experiment(SimpleNamespace(images=images, out=old, scope='same input scope',
        timeout=60, max_candidates=4, provider='claude', effort='medium'))
    new, _, _ = runtime_entry.prepare_inputs(tmp_path / 'runtime', images=images, mesh=None,
        building_input=None, scope='same input scope', image_kind='drawings', max_candidates=4,
        started_epoch=1000.0, seconds=60)
    left, right = (json.loads((path/'inputs.json').read_bytes()) for path in (old, new))
    assert left.pop('provider') == 'claude'
    assert right.pop('provider') == 'runtime'
    # Execution route is the only differing field under identical inputs/clock.
    assert json.dumps(left, ensure_ascii=False).encode() == json.dumps(right, ensure_ascii=False).encode()
    assert len(seen) == 1
    for name in names:
        assert (old/'images'/name).read_bytes() == (new/'images'/name).read_bytes()
    assert not (new/'private.json').exists()
    assert left['input_contents']['ground_truth_or_evaluation'] == {'included': False}
    assert left['lite_bim_grid_step_m'] == .1
    assert 'src/agent/bim_inputs.py' in left['implementation_sha256']


def test_identical_shared_function_options_write_identical_manifest_bytes(tmp_path):
    images = tmp_path / 'images'
    images.mkdir()
    Image.new('RGB', (2, 2)).save(images/'1f.png')
    options = dict(images_path=images, mesh_path=None, building_input_path=None,
        scope='shared', image_kind='drawings', max_candidates=2, started_epoch=1000., seconds=30.)
    for name in ('a', 'b'):
        prepare_bim_inputs(tmp_path/name, **options)
    assert (tmp_path/'a/inputs.json').read_bytes() == (tmp_path/'b/inputs.json').read_bytes()


def test_unlimited_runtime_inputs_preserve_clock_without_a_deadline(tmp_path):
    images = tmp_path / 'images'
    images.mkdir()
    image = images / '1f.png'
    Image.new('RGB', (2, 2)).save(image)
    original = image.read_bytes()
    run, _, _ = runtime_entry.prepare_inputs(tmp_path / 'runtime', images=images, mesh=None,
        building_input=None, scope='unlimited offline input', image_kind='drawings', max_candidates=2,
        started_epoch=1000.0, seconds=None)
    manifest = json.loads((run / 'inputs.json').read_bytes())
    assert manifest['started_epoch'] == 1000.0
    assert manifest['time_budget_seconds'] is None and manifest['deadline_epoch'] is None
    assert (run / 'images/1f.png').read_bytes() == image.read_bytes() == original


@pytest.mark.parametrize('image_kind', ['drawings', 'photos', 'unknown'])
def test_only_new_drawing_manifests_select_lite_grid_independently_of_scope(tmp_path, image_kind):
    images = tmp_path / 'images'
    images.mkdir()
    Image.new('RGB', (2, 2)).save(images/'plan.png')
    manifest = prepare_bim_inputs(tmp_path/'run', images_path=images, mesh_path=None,
        building_input_path=None, scope='model text requests a different 0.2 m grid',
        image_kind=image_kind, max_candidates=2)
    assert manifest.get('lite_bim_grid_step_m') == (.1 if image_kind == 'drawings' else None)


@pytest.mark.parametrize('image_kind,head,accepted', [
    ('drawings', 2.1, True), ('drawings', 2.14, False), ('photos', 2.14, True),
])
def test_new_lite_run_cannot_admit_an_off_grid_recovery_seed(tmp_path, image_kind, head, accepted):
    from tests.test_bim_agent_tools import _two_room_proposal
    images = tmp_path / 'images'
    images.mkdir()
    Image.new('RGB', (12, 8)).save(images/'plan.png')
    seed = tmp_path/'seed'
    seed.mkdir()
    proposal = json.loads(_two_room_proposal())
    proposal['geometry']['openings'][0]['z'][1] = head
    raw = json.dumps(proposal).encode()
    (seed/'proposal.json').write_bytes(raw)
    options = dict(images_path=images, mesh_path=None, building_input_path=None,
                   scope='review previous candidate', image_kind=image_kind,
                   max_candidates=2, seed_path=seed)
    if accepted:
        manifest = prepare_bim_inputs(tmp_path/'run', **options)
        if image_kind == 'drawings':
            assert manifest['seed']['lite_grid']['status'] == 'pass'
    else:
        with pytest.raises(ValueError, match='admission rejected'):
            prepare_bim_inputs(tmp_path/'run', **options)
        grid = json.loads((tmp_path/'run/seed/lite_grid.json').read_bytes())
        assert grid['status'] == 'rejected' and grid['violations']
        assert not (tmp_path/'run/inputs.json').exists()
    assert (seed/'proposal.json').read_bytes() == raw
