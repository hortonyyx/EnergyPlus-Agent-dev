"""Full path evidence must distinguish apertures from unobserved extensions."""
import copy
import numpy as np
from PIL import Image, ImageDraw
import pytest

from src.agent.geometry.plan_wall_support import measure_plan_wall_support


@pytest.mark.parametrize('transpose', [False, True])
def test_whole_path_preserves_true_door_and_reports_separate_blank_extension(transpose):
    image = Image.new('RGB', (80, 80), 'black')
    draw = ImageDraw.Draw(image)
    for a, b in ((5, 19), (30, 44), (60, 70)):
        draw.line((20, a, 20, b), fill=(128, 128, 128))
    plan = dict(partitions=[dict(id='wall', points=[[20, 70], [20, 5]])], openings=[
        dict(id='door', p1=[20, 20], p2=[20, 29]),
        dict(id='nearby_door', p1=[23, 45], p2=[23, 59])])
    if transpose:
        image = image.transpose(Image.Transpose.TRANSPOSE)
        for wall in plan['partitions']:
            wall['points'] = [p[::-1] for p in wall['points']]
        for door in plan['openings']:
            door['p1'], door['p2'] = door['p1'][::-1], door['p2'][::-1]
    before = copy.deepcopy(plan)
    rendered, report = measure_plan_wall_support(image, plan, rgb=[128]*3,
        tolerance=0, radius_pixels=1)
    wall = report['segments'][0]
    assert wall['supported_intervals_pixels'] == [[5, 19], [30, 44], [60, 70]]
    assert wall['declared_opening_sample_count'] == 10
    assert [v['id'] for v in wall['declared_openings']] == ['door']
    assert wall['unsupported_sample_count'] == 15
    assert report['review_intervals'][0]['span_pixels'] == [45, 59]
    assert report['drawing_fidelity'] == 'not_evaluated'
    assert np.array_equal(np.asarray(rendered)[:, :80], np.asarray(image))
    assert plan == before


def test_failed_draft_colour_mismatch_remains_measurement_not_geometry_fix():
    image = Image.new('RGB', (20, 20), 'black')
    plan = dict(partitions=[dict(id='dangling', points=[[5, 5], [5, 12]])], openings=[])
    _, result = measure_plan_wall_support(image, plan, rgb=[128]*3, tolerance=0)
    assert result['review_intervals'][0]['sample_count'] == 8
    assert not result['proposed_space_adjacency_available']
    assert result['drawing_fidelity'] == 'not_evaluated'
    with pytest.raises(ValueError, match='finite'):
        measure_plan_wall_support(image, plan, rgb=[128]*3, tolerance=float('nan'))
