# B4a Phase C 施工审 verdict r1（升一档·对抗审+活体探针）

- 审阅方：Opus 子代理（Claude 侧独立执行审，次高档）
- 施工方：terra 中档（GPT 家族）
- 日期：2026-07-16
- 合同：`AI_agent/proposals/c2_b4a_detail_spec.md` v2（§13 Phase C / §5.4–5.5 / §10.5–10.8 / §14 / §15.1）
- 改动面（5 文件，未 commit）：`src/agent/judge/gt_extraction.py`(+330)、`gt_schema.py`(+6)、`scripts/tool_scripts/gt_from_dxf.py`(-475 重写)、`tests/test_gt_from_dxf.py`(重写 11→5)、`tests/test_gt_schema.py`(+5)

---

## 总判：APPROVE-WITH-CHANGES

逻辑正确、负测真打失败路径、信任根洞已闭合、硬边界零扰动、回归全绿。但 §10.8 build 末段自检被写成**结构性死分支（恒真式）**，且 §14.1 明令的对应负测缺失（F1，MAJOR）；另有源隔离守卫未实现、若干 §10.7 负测与 writer 篡改测未落地（F2–F5，MINOR）。F1 不产错误产物（当前单一来源使产物恒正确），故非 REWORK，但属本审明确靶点（"自检真断言非 no-op"）且命中连续多批的恒真式家族，须修后方算 §10.8/§14.1 完整落地。

---

## 逐 finding

### F1 — MAJOR · CONFIRMED · `src/agent/judge/gt_extraction.py:708,714`
**§10.8 build 末段"tolerances 逐字段全等"自检是结构性死分支（恒真式），且 §14.1 明令负测缺失。**

- line 708 构造 `GtGeneratorV3(..., tolerances=inputs.tooling.tolerances)`——直接**别名同一对象**，而非 §10.8 要求的"逐字段写入 doc.generator.tolerances"（应产生独立值）。
- line 714 `if doc.generator.tolerances != inputs.tooling.tolerances: _fail("gt_build_profile_tolerances_mismatch")`——两侧是同一对象，比较恒 False。
- 活体探针 PROBE 2：`gen.tolerances is inputs.tooling.tolerances` → **True**；`(gen.tolerances != tol)` → **False**。分支永不触发。
- §14.1 明令："build 测试将当轮 resolved profile 与待写 `doc.generator.tolerances` 制造单字段差异，必须在 writer 前 fail"。核查：`test_gt_extraction.py` 本批**未改**且不测 `extract_gt_v3`；新增 `test_gt_from_dxf.py` 无此负测。该断言与其强制负测**均无效/缺失**。
- 失败场景：未来重构一旦让 generator 元数据的 tolerances 与实际用于 Vg/opening/elevation 计算的 profile 解耦（例如二次解析、硬编码），此 fail-closed 不变量将静默放过——这正是 §10.8 要防的类。
- 位置面正确（只在 build 末，未泄漏进 loader；已核 `test_loader_uses_archived_tolerances` 绿，loader 用存档容差）。
- 建议：把断言的比较右侧改为**独立重建的 tolerances 值**（从 resolved profile 逐字段快照，或在构造 generator 前另存一份 field 快照），使其真能 fail；补 §14.1 单字段差异负测。

### F2 — MINOR · CONFIRMED · `scripts/tool_scripts/gt_from_dxf.py:22-32,35-45`
**`--dxf` 源隔离守卫（§10.1）未实现，且无测试，简报却在 §13 映射声称含 "source-isolation" 覆盖。**

- §10.1："`--dxf` resolve 后必须脱离 `DEFAULT_GT_DIR` 以及 `case_tests/e2e_tests/*/case_data`（允许位于 gt_sources）"。`build_candidate`/`main` 对 `--dxf` 落点**零校验**。
- grep 确认 `test_gt_from_dxf.py` 无 `--dxf`-in-protected-root 负测。写侧（`--out`）保护已实现且已测（`_protected_candidate_path` + `gt_candidate_protected_path`）。
- 风险低（`--dxf` 只读），但守卫是 §10.1 明令项，且简报覆盖声明与实现不符（overclaim）。
- 建议：在 `build_candidate` 加 `--dxf` 受保护根拒绝 + 定向测试；或据实修正简报覆盖声明。

### F3 — MINOR · CONFIRMED · `scripts/tool_scripts/gt_from_dxf.py:37-40,25-26`
**CLI 签名偏离 §10.1：丢失 `--config`/`--vg-config` 两个明列必填参数，改为硬编码 config 路径。**

- §10.1 明列 5 必填参数含 `--config <src/configs/judge_gt.yaml> --vg-config <src/configs/correction.yaml>`；实现仅 `--dxf/--manifest/--out`，config 路径硬编码。
- 方向安全（R2 禁止 CLI override profile，硬编码与之一致），但仍是 documented interface 偏离，且阻断了经文档接口指向 reviewed 备选 profile 的能力。
- 建议：恢复两参数以符 §10.1，或在简报显式登记为与 R2 一致的有意简化（当前简报只写"替换为 build-only candidate CLI"，未点名删参）。

### F4 — MINOR · CONFIRMED · `src/agent/judge/gt_extraction.py:579-580,691-694`
**§10.7 elevation 两条核心负测缺失：多最优解 tie（`elevation_opening_assignment_ambiguous`）与多 view 竖向不一致（`elevation_opening_vertical_disagreement`）。**

- 逻辑读来正确：`_assign_elevation` 为整 view 全枚举最小代价 bipartite（非贪心），top-2 落 tie epsilon → fail；多 view 同 opening 的 z `!=` 即 fail、且存原值不平均。
- 但 `test_gt_from_dxf.py` 无用例触发 elevation-tie 或 z-disagreement（plan-opening tie 已由 PROBE 5 / `test_opening_no_candidate_and_tie_fail_closed` 覆盖，elevation 侧未覆盖）。§14.2 明列"elevation global assignment"为必测。
- 建议：补一个 U-case elevation 双候选 tie 测 + 一个双 view z 冲突测。

### F5 — MINOR · CONFIRMED · `src/agent/judge/gt_schema.py:652-657,699-723`
**writer 信任根行为正确但无回归锁：无测试篡改 `content_sha256` 验证 writer 重算而非照写。**

- PROBE 3：把 `content_sha256` 篡改为 `dddd…` → 落盘 hash = `9aca…`（正确重算值），writer 用 `canonical_gt_v3_bytes` 恒写重算 digest，**不信任调用方 hash**。信任根洞 CLOSED（与 B-M CR-01/Vg CR1/B2 F1/B-O CR4-5 同族洞在此**未复现**）。
- 但无测试锁此行为；未来 writer 若改为信任 `doc.content_sha256`，测试抓不到。
- 建议：加 tamper 测断言落盘 hash == 重算值（≠ 篡改值）。

### F6 — NIT · CONFIRMED（代码质量，聚合）
- `gt_extraction.py:475-477` `_bbox_points` 末两分支同为 `return points`，死重复分支。
- `gt_extraction.py:326` inspector 异常兜底把 DXF 读两遍（`ezdxf.readfile` 调用两次），冗余。
- `gt_from_dxf.py:29-32` `build_candidate` 先 `inspect_extraction_inputs`，`extract_gt_v3` 内部 `extract_plan_geometry` 又重跑一次 inspect，双重检查冗余（不影响正确性）。

---

## 靶点逐条结论

| 靶点 | 结论 | 证据 |
|---|---|---|
| 1 覆盖回归（净少6测） | **无安全锁丢失**。11 个旧测全针对已删 v2 提取器（`build("sm21_anchor")`/`_self_check`/`_floor_of_sill`），属重写废弃。旧文件本无"拒绝写受保护路径"锁测（旧脚本 `--write` 本就允许覆写）→ 受保护路径拒绝是 v3 新特性，已在新套件锁（`gt_candidate_protected_path`+`not blocked.exists()`）。B2-F1 高危模式**未复现**。 | 新旧 test 逐函数比对；`test_gt_schema.py:240-259,368-380` |
| 2 大删-475 | 删除的是真迁移/废弃行为（v2 W/D·rect·固定 facade·`--write` 覆写能力），非悄丢校验。v3 拒绝/校验行为在 `gt_extraction.py`+`gt_schema.py` 等价重建或强化。 | `gt_from_dxf.py` 全文；§10.1 |
| 3 负测真打失败路径 | **CONFIRMED 真打**。no-candidate→`opening_segment_assignment_no_candidate`；tie→`opening_segment_assignment_ambiguous`。排序虽含 `segment.id` 但 tie 检查（line 667）**在 id 消歧之前**触发，无 ID 兜底。tie 输入构造出两段等距（0.3/0.3），移除检查会改由 id 选中→测试转红（非恒真/自指）。 | PROBE 5；`gt_extraction.py:664-668` |
| 4 candidate writer 信任根 | **SAFE**。writer 恒写重算 digest，不信调用方 hash；受保护路径（DEFAULT_GT_DIR/gt_sources/e2e case_data）+ out.exists + 无 overwrite=True 实现均拒绝并已测。 | PROBE 3；`gt_schema.py:652-657,699-726` |
| 5 build 末段自检 | **F1（死分支+缺测）**。断言存在且只在 build 末、未泄漏 loader，但恒真无法 fail，§14.1 负测缺失。 | PROBE 2；`gt_extraction.py:708,714` |
| 6 elevation bipartite | 逻辑正确：整 view 全枚举最小代价（非贪心）、多最优 tie→fail、多 view z 精确一致不平均、plan-only z=null。负测覆盖不足（F4）。 | `gt_extraction.py:548-581,679-695` |
| 7 segments | 调 Vg 公开 `vg_for_direction` + GT 自有 `stable_boundary_segment_id`；全仓 grep 无 `_segment_geometry_sha256` 私有导入；全 hidden 段保留（`test_plan_only_z_and_u_hidden_depth_are_preserved` 锁 `not visible_intervals and depth>0`）；surface key `sorted(set(...))` 去重。 | grep；`gt_extraction.py:596-644` |
| 8 review-ask 复核 | terra 处置**与 §5.4 一致，建议采纳**（见下）。 | PROBE 4；§5.4 |
| 9 fail-open/shapely/except | 无 fail-open。shapely 解包绑定**正确**（dangle 落 ret[2]，代码 ret[2]→`dangles`；且 gate 对 cuts/dangles 对称，即便互换也不产生假通过）。`except Exception` 各处均 fail-closed（block/raise）。 | PROBE 1；`gt_extraction.py:243,356,495,510-511` |

---

## review-ask 独立复核（§5.4 canonical bytes vs raw source SHA）

**推荐：采纳 terra 处置（保留 raw source hash + 锁"提取器实体遍历序不敏感"），无需改。**

- terra 的顾虑（重新序列化 raw DXF 会改 raw bytes → 破坏 manifest `source_dxf_sha256` 精确匹配）成立；因此把"顺序不敏感"锁定在 extractor 层。
- §5.4 已明文限定："所谓'输入顺序不敏感'只指 DXF entity、manifest selector 和原始 ring 起点**经 extractor 后**得到同一 canonical wire"。terra 的锁测正是此语义，**一致**，该 review-ask 实为已被 §5.4 裁决的非问题。
- 活体验证 `test_reordered_dxf_entity_iteration_has_identical_canonical_candidate` **非假绿**：PROBE 4 证实 `entity_space.entities.reverse()` 真改迭代序（`[2F,30,31]`→`[31,30,2F]`），测试断言 `canonical_gt_v3_bytes` 逐字节 + `content_sha256` 相同。有效。
- 唯一附带建议（非阻塞）：该测试反转的是 in-memory `entity_space`；可选加一条注释说明"不重序列化 raw bytes 以保 source hash"，让意图对后续读者自解释（terra 简报已述，代码内可留一行）。

---

## 硬边界核验表

| 边界 | 结论 | 证据 |
|---|---|---|
| 零资产扰动（gt.json/DXF/PNG/golden） | PASS | `git status --short` 仅 5 代码 + 2 review 文档；无 `gt.json`/`.dxf`/`.png`/golden 变动 |
| `gt_sources/` 未动 | PASS | git status 无 `gt_sources` 条目 |
| 无 v3 GT 写入仓库可见路径 | PASS | 无新增 `gt/**` 文件；测试候选只进 tmp_path |
| 未碰 Phase D（render_gt*.py） | PASS | diff 无 `render_gt.py`/`render_gt_overlay.py` |
| 未碰 correction/Vg/Va 生产码 | PASS | 改动仅 `src/agent/judge/` + `gt_from_dxf.py` |
| 未碰 B4b 车道（score_*/judge_score.yaml） | PASS | diff 无相关文件 |
| gt 铁律：生产路径零 judge import | PASS | `test_gt_discipline.py` 绿（回归组内） |
| sm21 v2 raw 字节/SHA 不变 | PASS | `test_dual_read_v2_raw_equality...` 绿（SHA a9be379b… 断言） |

---

## 测试执行记录（独立复跑）

- `test_gt_schema.py + test_gt_from_dxf.py + test_gt_extraction.py + test_inspect_dxf.py`：**66 passed**（6 Pydantic serializer warnings，既有）。
- `test_gt_render.py + test_gt_overlay.py + test_gt_discipline.py + test_reading_score.py + test_elevation_score.py + test_judge_batch_b.py + test_judge_harness.py`：**76 passed**。
- 全量 pytest 归主控轻门（简报报 1141 passed + 9 xfailed）。
- 活体探针脚本：`scratchpad/probe.py`（PROBE 1–5 全命中，见上）。
