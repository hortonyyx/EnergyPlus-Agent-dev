"""Capture this review's commands; never overwrite the previous evidence."""
from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
D = 'AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md'
OLD = 'AI_agent/logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md'
G = 'AI_agent/guides/reading_correction_split_guide.md'
P = 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype'
LEGACY = 'AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt'
HERE = str(OUT.relative_to(ROOT))
groups = [
    ('E01 scope', 'pwd\ngit rev-parse HEAD\ngit status --short\ngit diff --numstat b4f0b348..75f7732a\ngit diff --numstat 75f7732a -- src tests\ngit diff --exit-code 75f7732a -- ' + D),
    ('E02 original five findings and four nonblocking items', f"rg -n -A 18 '^### F-|^### N-' {OLD}\nrg -n '病根一句|建议方向' {OLD}"),
    ('E03 F1 completeness and competing branches', f"rg -n -A 12 '^AutoProvenanceV1:|^WholeBuildingOpeningReviewInputV1:|^候选生成|^不满足值域锚点' {D}\nrg -n '强制进入|不进.*OpenItem|已裁定|ALL_S1|本轮新增的.*confidence|信息论' {D}"),
    ('E04 F2 membership, address debt, and named owner search', f"rg -n 'CHAIN_NODE_VALUE_AUTHORITY|∃ k|不管.*dimension_refs|obligation=None|debt_id=|affected_refs=|description=|升档条件|人工排期|主链数组|同一个锚点|另一种' {D}\nrg -n '兑债|兑现|redeem|owner|升级|升档|重跑|回第一步|本次裁决|batch|manifest' {D}"),
    ('E05 F3 exact gate promises', f"rg -n '逐节点前缀和|CALIBRATION_CHAIN_|原始像素测量|不在本层验证|两道任一|∀ i|区间级' {D}\nrg -n -A 43 '^def _require_chain_closed' src/agent/correction/evidence_adapters.py"),
    ('E06 F4 complete declared signatures', f"rg -n -A 13 '^ChainDerivedValueV1:|^DerivedOperandV1:|^硬不变量（ChainDerived|^segment_span_diff 的合法性|^segment_span_sum 的合法性' {D}\nrg -n 'operand.evidence_tier|evidence_tier|value_source:|direction:|role:|derivation:|source_ref.input_id|声明常量|结果 =|前置：每个 operand|WALL_THICKNESS_HALF_UNGRID' {D}"),
    ('E07 F5 complete printed factory and bindings', f"rg -n -A 31 '^def _mint_sealed_tick_claims' {D}\nrg -n '本次具体动作|auto_action_id:|auto_rule_id:|packet_hash:|decision_hash:|AutoActionV1.kind|裁决账绑定|tuple.sealed_claims|正反例覆盖' {D}\nrg -n -A 47 '^class CorrectionEvidenceBundleV1' src/agent/correction/evidence_contract.py\nrg -n -A 13 '^class CorrectionEvidenceBundleArtifactV1|^def validate_evidence_bundle' src/agent/correction/evidence_contract.py"),
    ('E08 B2 actual paradigm and its stated limits', "rg -n '闭包|只存一个字段|每次读取|门在前|急切过门|塞类型正确|不同.*冻结字节|reading 信任根|载体唯一|only sanctioned|没有声称' AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md\nrg -n -A 8 '唯一途径是提供' AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md"),
    ('E09 real debt dispatch and review API', "rg -n -A 37 '^class EvidenceDebtV1' src/agent/correction/evidence_contract.py\nrg -n -A 75 '^def assert_obligations_backed' src/agent/correction/opening_synthesis.py\nrg -n -A 31 '^class WholeBuildingReviewV1' src/agent/correction/decision_schema.py\nrg -n -A 16 '^class AutoActionV1' src/agent/correction/wall_compiler.py"),
    ('E10 authority and configuration', fr"rg -n '把多通道证据变成|刻度认领.*第一步|只能取自|一档.*链|二档.*只有|逐图独立|无歧义的自动|本图一致性|有新的不一致|几档|推测|两个分辨率|半格|没有落地|pipeline 出口.*10 mm|0.1 mm 整数' {G}\nrg -n 'A-2.*免疫' AI_agent/plan.md\nrg -n 'structural_snap_grid_m:|output_precision_m:|window_snap_grid_m:' src/configs/correction.yaml".replace('\\n', '\n')),
    ('E11 nonblocking closure and author evidence claims', f"rg -n '数字自查|170|948|本稿定稿后|South/East|代价是所有|三处|拟议|单一声明点|②b|③ 场景|纯平面实体|不再声称|撤回|0mm|R[1-5] ·|碰撞点数值|capture_evidence|my_counterexamples.py' {D}\nrg -n '^def _sorted_bundle|^def finalize_bundle|^def _payload_row_source_ids|^def validate_evidence_bundle' src/agent/correction/evidence_contract.py\nrg -n '^def adapt_as_drawn_elevation|^def _require_chain_closed' src/agent/correction/evidence_adapters.py\nrg -n '^def redemption_row_for_obligation|^def _resolve_backed_obligation|^def assert_obligations_backed|^def redeemable_debt_ids|^def _elevation_openings|^def synthesize_openings' src/agent/correction/opening_synthesis.py"),
    ('E12 producer, data and probe source anchors', fr"rg -n 'def _nearest|min\(ticks|tick_map\[world\]|here = refs|here.append|t, d = _nearest|dimension_refs.*refs\[pool\]' {P}/tools/as_drawn_elev.py\nrg -n 'world_start_mm|direction|primary_x_chain' {P}/tools/cfg_south.json\nrg -n 'SPEC_|ACTUAL_|EXACT_D6|carrier._artifact|def draft_branch|def check|prefix =|def arity_bridge' {HERE}/probe.py".replace('\\n', '\n')),
    ('E13 independent NEW inputs', f'python3 {HERE}/probe.py all'),
    ('E14 unchanged prior statistics', f'python3 {LEGACY}/probe.py statistics'),
    ('E15 unchanged prior counterexamples', f'python3 {LEGACY}/probe.py counterexamples'),
    ('E16 unchanged prior arithmetic', f'python3 {LEGACY}/probe.py arithmetic'),
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
parts = ['# 本轮独立命令与原文输出\n\n被审对象固定为 `75f7732a`。SPEC 是明示的设计公式/字段形状推演；ACTUAL 才是现有仓库代码。\n']
for name, cmd in groups:
    run = subprocess.run(['bash', '-c', cmd], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    parts.append(f'\n## {name}\n\n```sh\n{cmd}\n```\n\n```text\n{run.stdout}[exit {run.returncode}]\n```\n')
    print(name, 'exit=', run.returncode)
(OUT / 'evidence.md').write_text(''.join(parts))
for label, cmd in [('legacy_numbers', f'python3 {LEGACY}/probe.py numbers'), ('numbers', f'python3 {HERE}/probe.py numbers')]:
    run = subprocess.run(['bash', '-c', cmd], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / f'{label}.md').write_text(f'# {label}\n\n```sh\n{cmd}\n```\n\n```text\n{run.stdout}[exit {run.returncode}]\n```\n')
    print(label, 'exit=', run.returncode, 'summary=', '\n'.join(run.stdout.splitlines()[-3:]))

# Replay the old capture's EXACT command list, relocating only its output.
# This avoids mutating the old evidence.md (part of the reviewed inputs).
old_capture = ROOT / LEGACY / 'capture_evidence.py'
code = old_capture.read_text().replace("(OUT / 'evidence.md')", "(OUT / 'legacy_capture.md')")
exec(compile(code, str(old_capture), 'exec'), {'__file__': str(OUT / 'capture_evidence.py'), '__name__': '__legacy_capture__'})
print('Legacy capture replay: same command list, output relocated to', OUT / 'legacy_capture.md')
