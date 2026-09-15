"""Apply explicit case decisions after new roof aperture surface hits."""
from pathlib import Path
import json
HERE = Path(__file__).resolve().parent
path = HERE / 'case_plan.json'
old = HERE / 'case_plan_initial.json'
assert not old.exists(), 'Revision must not overwrite its original record'
old.write_bytes(path.read_bytes())
plan = json.loads(path.read_text())
plan['shell']['attic_court_long'] = -.1
for opening in plan['additional_openings']:
    if opening['id'].startswith('roof_court_'):
        opening['plane_key'] = 'attic_court_long'
plan['inferred_core_rectangles']['CORE_S'] = [-4.2,-26.3,-1.4,-23.7]
plan['inferred_service_rectangles']['services_s'] = [-6,-27.4,.8,-23.7]
plan['revision'] = {
    'reason':'Seven roof-window centres hit original mesh X=-0.075..-0.200m, so the attic inner facade is recessed from main X=0.8m. Preserve measured window coordinates and adjust the inferred interior scenario.',
    'changes':['Set attic inner wall to X=-0.1m.', 'Move hypothetical southern vertical core fully inside both main and attic footprints.',
               'Express the southern service/lobby as one connected U-shaped space around the core, clipped to each storey footprint; no fabricated open-office partition or exterior core projection.',
               'Retain the original missing-scan region as unknown enclosure on the service-space outside wall.'],
    'evidence':'additional_views/aperture_queries.json', 'prior':'case_plan_initial.json',
    'not_measured':'Core and service/lobby layout remain internal hypotheses, not observed reality.'}
plan['assumptions'].append('新屋顶窗命中显示长翼内院的退台墙约X=-0.1m，按此回退轮廓；南交通核心及其服务/候梯空间随之调整到各层共同范围内，未挪动观察到的窗。服务/候梯区可环绕核心保持一个连续空间，仍为内部方案假设。')
path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
