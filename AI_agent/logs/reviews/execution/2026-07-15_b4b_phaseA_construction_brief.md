# B4b Phase A 施工简报（terra，2026-07-15）

## 范围与车道

按 `c2_b4b_detail_spec.md` v2 与派单，仅施工 Phase A（合同、identity、score inputs）。B4a Phase B 的未提交 `inspect_dxf.py`、`gt_schema.py`、`gt_extraction.py` 及其测试只读保留；未修改、未 revert。无 commit。

## 改动映射

| 合同章节 | 落地点 |
|---|---|
| §5、§6.1/§6.2、§6.5、§6.7 Phase-A NA/REJECTED skeleton | `src/agent/judge/score_schema.py`、`src/agent/judge/score_config.py`、`src/configs/judge_score.yaml`、`scripts/tool_scripts/run_stage.py` |
| §6.3、§6.3.8 | `src/agent/judge/score_inputs.py`；A0 §4.1.1 登记九键 frame preimage、config/hash/helper 口径 |
| §6.4 | `src/agent/judge/score_inputs.py` 与 `scripts/tool_scripts/build_judge_score_inputs.py`；只产生候选/临时 declaration |
| §7.1、§7.2 | `score_schema.py` typed-only identity/capability skeleton 与独立 `facade_segments_sha256` preimage hash |
| §13 Phase A 测试 | `tests/test_c2_b4b_contract.py`、`tests/test_c2_b4b_score_inputs.py` |

judge-only v8 writer 现仅覆盖 Phase-A 的 NA/REJECTED skeleton，几何 scorer、sidecar full cache/atomic writer、renderer 与 CLI promotion 留在后续 Phase。

## 验收与测试

| 组 | 结果 |
|---|---:|
| B4B-A1 wire strict（extra/missing/type/NaN/Infinity、config/A0、v8 skeleton/schema-7 miss） | 18 passed（与 A2–A4 共用两新测试族） |
| B4B-A2 identity/capability（typed dispatch、identity/sidecar） | 18 passed（包含于上组） |
| B4B-A3 completeness owner（user/dataset body hash、effective manifest、single source/base conflict/idempotence） | 18 passed（包含于上组） |
| B4B-A4 Va preimages（full facade preimage、frame sign/mirror/local-x、缺/多 key） | 18 passed（包含于上组） |
| Va 回归 | 49 passed |
| GT schema/discipline/judge harness 回归 | 72 passed |
| reading/elevation/judge batch 回归 | 44 passed |
| render-grade/run-stage-flow（legacy 标签过渡影响面） | 34 passed（29 条既有 warning） |

本轮定向命令合计为 217 passed（各命令组不重叠；render/flow 组有 29 条既有 warning）。`git diff --check` 通过；受保护 `case_tests` 资产无 diff；未新增 production 对 judge 的 import。

## 出口 gate

- `B4B-A1-wire-strict`: PASS
- `B4B-A2-identity-total`: PASS
- `B4B-A3-completeness-owner`: PASS
- `B4B-A4-va-preimages`: PASS
- `B4B-A5-production-import-zero`: PASS（本批未向 production 模块加入 judge import；既有 judge-run wiring 未改）

## 预期行为、偏离与 review-ask

v3 评分入口的 Phase-A capability/identity 不会调用 raw `load_gt()`；未知 profile 或不支持产品 schema 返回机器可读 NA，合同/identity 错误返回 REJECTED skeleton。frame hash 和 facade-segment hash 均以本批独立 canonical implementation 计算，不 import Va 私有 hash helper。base manifest 始终不写回，overlay 仅生成内存 effective manifest。

## r1 finding 闭合映射（2026-07-15）

| finding | 闭合 |
|---|---|
| BA-C1 | A0 §4.1.1 登记 South 四态的固定 hash 向量；测试以硬编码向量及 A0 文本锚对比，覆盖每一个缺失 preimage key 与多键拒绝，不再由被测 hash 函数生成期望。 |
| BA-C2 | `decide_score_capability(..., view_manifest: ViewManifest)` 改为从 manifest 实例读取 capability-key 的 manifest/completeness 成分；`load_cached_score(..., grade_path, expected_identity)` 重验 PNG bytes hash。 |
| BA-C3 | 移除 `HelperIdentityV8` 五个 Literal 的合同外默认值，并加缺字段拒绝测试。 |
| BA-C4 | 见下列带日期过渡偏离：legacy writer 保持 7，judge v8 skeleton 保持 8。 |
| BA-C5 | 非 UTF-8 judge config 现在转换为 `ScoreContractError`，有回归测试。 |
| BA-C6 | 新增 GT 侧 companion validator（floor/facade/source-ref 交叉验证）及 dataset registry 四元组+body hash 唯一 resolver；其正式 service 接线列入未竟。 |
| BA-C7 | 留痕：strict-wire 跨模型扩展及 facade hash 的独立 A0 byte anchor 仍应在 Phase B adapter 实体测试中补强；本轮已将 frame 的九键缺失检查扩至逐键。 |
| BA-C8 | 留痕并修除：删除不可达 rejected capability 分支及错误码/NA reason 混用。 |
| BA-C9 | 候选 GT 正式入口门与具名 Phase C/D 测试清单如下。 |

## 显式偏离与未竟

**过渡偏离（2026-07-15，主控裁决 BA-C4）**：`scripts/tool_scripts/run_stage.py` 的 legacy sidecar writer 保持 `SCORER_SCHEMA="7"`；judge-only `ScoreSidecarV8` NA/REJECTED skeleton 固定为 `"8"`。这是派单提前 bump 与合同 §13 Phase D 排期不一致的临时双值边界；Phase D full writer/cache validator 落地时统一为 v8，旧 v7 形态严格 cache-miss 后重算。相应 `test_judge_batch_b` 继续如实断言 legacy 标签为 7。

未竟（不得作为已完成宣称）：

- §6.3-3/4 的 GT 侧校验已由 `validate_score_view_bindings_against_gt()` 实现，但冻结的 file loader 无 GT 参数；Phase C typed service/`score_attempt` 必须调用该 validator，不能只调用 loader。
- §6.4-6 的 dataset registry 唯一解析已由 `resolve_dataset_declaration()` 实现；Phase C service 必须把受信只读 registry root 接入 overlay 入口，不能仅调用 builder。
- §7.1 candidate GT 在正式 score/run-stage 入口必须以 `score_gt_identity_invalid` 拒绝；该入口尚属 Phase C/D，当前 candidate file loader 仅供候选检查。
- Phase C 具名测试：正式入口 candidate GT reject、GT companion validator 已接线、true/unknown resolver 端到端、product schema NA、elevation frame/claim totality。
- Phase D 具名测试：schema-7 legacy cache 重算、完整 v8 identity/PNG hash cache hit、原子 sidecar/PNG pair、legacy label 收敛至 v8、renderer/CLI dispatch。

review-ask：请主控抽查 A0 四向量、冻结签名和上述 Phase C/D 未竟登记；确认 BA-C4 的过渡双值在 Phase D 前可接受。

## 本批改动文件

- `AI_agent/logs/reviews/execution/2026-07-15_b4b_phaseA_construction_brief.md`
- `scripts/tool_scripts/build_judge_score_inputs.py`
- `scripts/tool_scripts/run_stage.py`
- `skills/intake_pipeline/1_correction/A0_contract.md`
- `src/agent/judge/score_config.py`
- `src/agent/judge/score_inputs.py`
- `src/agent/judge/score_schema.py`
- `src/configs/judge_score.yaml`
- `tests/test_c2_b4b_contract.py`
- `tests/test_c2_b4b_score_inputs.py`
