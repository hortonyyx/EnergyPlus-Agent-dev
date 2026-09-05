"""Capture read-only commands and their unedited output for the design verdict."""
from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
D = 'AI_agent/logs/reviews/execution/2026-09-05a_tick_claim_design_rework1.md'
OLD = 'AI_agent/logs/reviews/verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md'
G = 'AI_agent/guides/reading_correction_split_guide.md'
P = 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype'
commands = [
 ('E01 scope', 'pwd\ngit rev-parse HEAD\ngit diff --numstat ac9a0669..dc886036\ngit diff --numstat dc886036 -- src tests'),
 ('E02 previous findings verbatim', f"rg -n -A 12 '^### [BN]-[1-6]' {OLD}"),
 ('E03 design contract', f"rg -n 'OneTierValueV1|value_source:|node_ref:|operands:|recompute_cert_units:|role: Literal|evidence_ref:|dimension_refs: tuple|provenance:|auto_rule_id:|packet_hash:|decision_hash:|input_id.*同|符号由边角色|检查①|检查②|严格有序|_require_chain_closed|无 provenance|reject_all|whole_building_review|候选.*两路|推荐乙|B2 已定门|闭合 B-4|私有令牌|逐元素受封|从每条 claim|正反例必须' {D}"),
 ('E04 design claims and numeric table', f"rg -n 'South 全|North 全|West|MULTI|ALL_S1|自动一档|自动二档|全量重量命令|python3 -c|66/68 自动|已签字颗粒度|CodeToken.*约束|原料/实测|实测统计|反例/构造|颗粒度收口|直接推出|1940|关于.*二档|无坐标字段|R[1-5] ·|每个.*content_sha256|日期/commit|源码行号' {D}"),
 ('E05 authority delta anchors', fr"rg -n '^### 14\.|^### 15\.|只能取自|两个分辨率|最大差半格|二档不是|第一步.*逐图独立|每笔自带|本图一致性|有新的不一致|登记待确认|推测|输入.*reading|无歧义的自动|没.*落地' {G}"),
 ('E06 actual witness producer', fr"rg -n 'def _nearest|min\(ticks|tick_map\[world\]|here = refs|here.append|t, d = _nearest|dimension_refs.*refs\[pool\]|round\(px, 1\)' {P}/tools/as_drawn_elev.py"),
 ('E07 D1 and carrier source', "rg -n 'def adapt_as_drawn_elevation|z_low_ref=_pointer|z_high_ref=_pointer|elevation_opening_claims=' src/agent/correction/evidence_adapters.py\nrg -n 'class ElevationOpeningClaimV1|deliberately NOT|z_low_m:|z_low_ref:|z_high_m:|z_high_ref:|ELEVATION_Z_VALUE_DRIFTED|def finalize_bundle|_CFG =|class ArtifactPointerV1|class ObservationRefV1|json_pointer:' src/agent/correction/evidence_contract.py\nrg -n 'def _elevation_openings|for field in|def synthesize_openings|for oid, x_lo|world_lo = along_origin' src/agent/correction/opening_synthesis.py\nrg -n 'synthesize_openings\\(' src scripts --glob '*.py'\nrg -l 'elevation_opening_claims' src"),
 ('E08 chain gate full relevant lines', "rg -n -A 43 '^def _require_chain_closed' src/agent/correction/evidence_adapters.py\nrg -n 'DECLARED_GRID_UNITS_PER_M =|_GRID_UNITS_PER_MM =|def grid_units_from_mm|unit / _GRID_UNITS_PER_MM' src/agent/correction/opening_synthesis.py"),
 ('E09 model response and auto action constraints', "rg -n -A 25 '^class AutoActionV1|^class OpenItemV1' src/agent/correction/wall_compiler.py\nrg -n 'CodeToken =|min_length=1, max_length=96|class CorrectionDecisionResponseV1|whole_building_review:|_CFG =|action: Literal|packet_hash:' src/agent/correction/decision_schema.py\nrg -n 'UNKNOWN_RESPONSE_CANDIDATE|item.candidates|whole_building_review|CorrectionDecisionResponseV1' src/agent/correction/decision_executor.py"),
 ('E10 raw data locations', f"rg -n -A 6 '14540|15740|1524.5|1525.0|C_top_fine_s2|C_bot_fine_s4' {P}/out/sm25_west_as_drawn.json {P}/out/sm25_north_as_drawn.json\nrg -n -A 23 '\"C_top_fine\"|\"C_bot_fine\"' {P}/tools/cfg_west.json {P}/tools/cfg_north.json"),
 ('E11 no plan-only boundary in draft (expected exit 1)', f"rg -n '②b|只有平面|平面有立面无|推测|plan_only|unsupported|OUT_OF_SCOPE' {D}"),
 ('E12 current mainline D7', "git log -2 --oneline b4f0b348\ngit diff --numstat dc886036 b4f0b348 -- src/agent/correction\ngit show b4f0b348:AI_agent/plan.md | rg -n 'A-2.*免疫|T4-a.*obligation|B2 返工 3.*交件'\ngit show b4f0b348:src/agent/correction/evidence_contract.py | rg -n 'class EvidenceDebt|obligation:|class ElevationOpeningClaim|deliberately NOT|def _sorted_bundle|def finalize_bundle|def _payload_row_source_ids'\ngit show b4f0b348:src/agent/correction/opening_synthesis.py | rg -n '^def _resolve_backed_obligation|^def redemption_row_for_obligation|^def redeemable_debt_ids|executed.source.binds|^def synthesize_openings|^def _elevation_openings'\ngit show b4f0b348:tests/test_t4a_rework1_resolution_lock.py | rg -n '^def test_|^class Test'"),
 ('E13 in-flight design dependency', "git show b4f0b348:AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md | sed -n '30,70p'\ngit show b4f0b348:AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md | rg -n '闭包|逐元素|最薄弱|声称|依赖'\nrg -n '合法方向|模块私有令牌|逐元素|冻结字节|不能|⛔ 碰' AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md"),
 ('E14 granularity declaration and consumers', "rg -n 'structural_snap_grid_m:|output_precision_m:|window_snap_grid_m:' src/configs/correction.yaml\nrg -n 'tol.structural_snap_grid_m|tol.window_snap_grid_m' src/agent/correction/deterministic.py"),
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
parts = ['# Independent evidence transcript\n\nRead-only commands; snapshots are explicitly identified. Exit 1 from a negative `rg` is retained.\n']
for title, command in commands:
    run = subprocess.run(['bash', '-c', command], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    parts.append(f'\n## {title}\n\n```sh\n{command}\n```\n\n```text\n{run.stdout}[exit {run.returncode}]\n```\n')
(OUT / 'evidence.md').write_text(''.join(parts))
print('CAPTURED', len(commands), 'groups;', len(''.join(parts).splitlines()), 'lines')
