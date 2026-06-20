# 0–5 校验架构施工方案（v2，纳入 Codex 双 review）

> **施工方案（HOW/WHEN），2026-06-15 v2。** 配套设计 [pipeline_stage_contracts.md](pipeline_stage_contracts.md)（WHAT）。**v2 全面纳入 Codex 设计+施工双 review**（CHANGES REQUESTED，逐条处置见会话 + 本文）：新增 **M0 执行/审计地基**、reading schema 迁移、统一 IDF-fragment parser、矩形覆盖洞本轮做、失败分类、check/verdict schema v2、viewer trimesh 先行、用户门=调用策略。依赖序改用 Codex 建议的 M0→M1→M2a→M2b→M2c→M3→M4。
>
> **总纪律**：① 确定性校验**每条配单测**（含真实坏 fixture，不只 sm20 正例）；② **policy 与事实分离**——validator 报事实，block/flag 由 stage+capability profile 映射；③ **append-only attempts**、不覆盖坏 draw；④ 改 skill/src 按 [CLAUDE.md §6#5](../CLAUDE.md) 备份；⑤ **确定性优先**（M2 无 LLM judge），judge 层 M3 后置；⑥ 不动 `IntakeOutput` 11 字段契约、不动下游；⑦ 每个里程碑可独立无网络测试 + 独立回归（小 PR）。

---

## 0. 失败分类 + 重做规则（贯穿全程，Codex 设计 H1 / 施工 H1·H2）

| 失败类 | 谁产生 | 处置 |
|---|---|---|
| `upstream_input_failure` | 输入违反本段前置条件 | 弹**上游产出段**（确有上游根因）|
| `deterministic_code_failure` | 输入合法、确定性代码违反后置条件 | **fail-closed，记 code defect，raise；绝不弹上游/换样本** |
| `stochastic_draw_failure` | LLM 段（0 自动后/1/4）draw 不过 check | **盲重抽**（同输入换采样，judge 评语不进 prompt）|
| `judge_mismatch` | judge 判不过 | 盲重抽 stochastic 段；归因不确定（`root_confidence` 低）→ 不自动路由、交人 |

- **0_reading 当前 = `manual` runner** → 自动路由只返回 `human_redraw_required`（VLM runner 接入后才开放自动 3 次盲重抽）。
- **预算**：每阶段 3 次 + **整条 run 的全局 draw/judge 预算 + 循环检测**。
- **hard sample** 先标 `quarantined_failure`；排除 judge 误判/代码 bug/配置错后才进训练集。

---

## 1. 模块布局（代码落哪）

```
src/agent/execution/                   ← 新：M0 执行/审计地基
  stage_runner.py   StageRunner + registry（stage id / input artifact hashes / capability manual|stochastic|deterministic / outputs）
  manifest.py       run_manifest.json（指向 accepted attempt）+ append-only attempts 布局
  invalidation.py   **完整失效 DAG**（0→1-5 / 1→2-5 / 2→3-5 / 3→4-5 / 4→5）+ resume_from_checkpoint（resume 复用已批准 attempt、不静默重新生成 2/3）
  approval.py       geometry_approval.json（绑定 **accepted geometry checkpoint digest = building_geometry + geometry_specs + kernel check report + stage/check version** / policy / actor / ts；批准后重跑 2/3 须使 approval 失效）
src/validator/checks/                  ← 逐段确定性校验 + 公共 schema（仅 stage adapter，不含领域逻辑）
  schema.py         F1 CheckReport v2（status / layer / check_version / capability_profile / artifact+attempt hash / 机器可读 evidence；policy 与事实分离）
  reading.py  correction.py  kernel.py  mep.py  assembly.py
src/validator/idf_fragments.py         ← 新：统一 MEP fragment parser（一次解析 bundle → 对象索引 + 诊断；checks 共用、禁各自 regex）
src/validator/{interzone,schedules,data_model}.py   保留原位（低层领域 validator，被 checks/* adapter 复用）
src/agent/correction/
  facade.py            立面 image-local 方向 → world 翻译（world_axis/base_world 在此生成，非 reading）
  geometry_validator.py A0§7 coverage/closure/z-stack/非退化
src/agent/judge/                       ← M3 judge 门基建
  verdict.py        verdict schema v2（criterion status + not_applicable/insufficient_evidence + root_stage|null + root_confidence + retriable）
  retry.py          retry_stage_draw(runner, validators, budget, artifact_sink) 单阶段盲抽（跨阶段 route 归 execution/orchestrator）
scripts/tool_scripts/
  render_corrected_geometry.py  扩：填色区图 *_zones.png
  render_elevation_windows.py   新：立面窗位图 *_elev.png
  render_building_3d.py          新：trimesh mesh + GLB/静态投影（viewer 失败不阻塞 checks；headless 不可用 → 显式 skip）
skills/intake_pipeline/<stage>/judge_rubric.md   J0/J1（J4 stub-disabled）
```

> **抽两层、不复用 `_make_correction_validator`**（施工 H2）：`draw_json_once`（一次调用）+ `retry.retry_stage_draw`（单阶段盲抽）；跨阶段 route/invalidation 归 execution orchestrator。明确两入口 `repair_feedback`（现下游 repair，可注入）vs `judge_retry_context=None`（必盲抽），测试断言不串线。

---

## 2. 依赖序 + 里程碑（小 PR，纯 validator 可并行 / 接线按依赖串联）

### M0 — 执行与审计地基
- E0 stage runner / run_manifest / immutable attempts / 失效 DAG / resume；CheckReport v2（status/version/hash/attempt，policy 分离）；CLI policy（judge on/off、`confirmation_policy=required|optional|disabled`、全局预算）。
- **没这层不接 gate**。

### M1 — 输入 schema 与 parser 地基
- **P1a reading dimension/provenance schema**：`dimensions[]` 加 `chain_id / role=overall|segment|baseline / order / value_m / text_verbatim / 像素 bbox·anchor`；明确 plan/elevation endpoint 坐标约定。
- **P1b facade canonical image-local schema**（纳入 re-verify Medium 2，**不混 image/world 语义**）：0_reading 只出 `view_facade`(South/North/East/West，来自可信图名/元数据) / `local_x_positive = image_left_to_right`(纯图内左右、**不写 east/west**) / `mirrored: true|false|unknown` / `orientation_evidence`(结构化来源)；**world axis/sign/base 只由 1_correction 派生**。若需保存 east/west OCR 提示，另作 `world_direction_hint` + provenance、不与 image-local 主字段混用。旧 `facade_axis_note` 仅作迁移 adapter（短期、带 flag）。
- **P2 IDF-fragment parser** `idf_fragments.py`（Codex spike 已验证：sm20 六类片段 eppy `IDF(StringIO)` 解析 138 对象、`validate_schedule_completeness` 0 issue）。
- legacy adapters + migration flags。

### M2a — 0/1 确定性校验 + 二维视觉件
- **S0** `reading.py`：结构 linter（block = 字段存在+合法 pen×kind / 唯一 id / 有限数值 / 非退化 line·rect / dimension 可解析 / axis-端点一致；**`uncaptured` 只要求存在且为 list、不要求非空**）+ 单图尺寸链闭合（flag）+ **内部几何-尺寸一致性**（原 stroke↔dimension，**低置信 flag、非 2f 主验收**）+ 越界（flag）。
- **S1** `correction.py` + `facade.py` + `geometry_validator.py`：A0§7 coverage/closure/z-stack/非退化（block）+ facade image-local→world 确定性翻译并生成 world placement + 跨图对账（flag）+ 窗位落墙（flag）+ 区数 tripwire（flag）+ **correction delta/audit 完整性**（cells 与 reading 墙图矛盾或依赖 testdata 修正 → 必产带来源 correction/conflict，保住"0 曾错"标签）。视觉件：填色区图 + 立面窗位图。
- **fixtures**：真实坏 2f corridor-split reading（与 corrected anchor 分开）+ self-consistent wrong-dimension（证明确定性只 flag 内部一致、原图真值交 J0）+ wrong facade sign/对称窗。
- **半人工 0 失败 → `human_redraw_required`，不自动 redraw**。

### M2b — 2/3 几何门
- **S23** `kernel.py`：zone 封闭/法向/spec 引用（block）+ `kernel_gate_report` 提 block 关口 + **矩形 coverage completeness block**（相邻 cell 共享边 → expected interfaces vs 实际互逆对，集合/面积对账；**本轮做，B5 只泛化非矩形/void**）。
- **负例回归**：人为把一对内墙都改 Outdoors → kernel check 必失败。
- mesh/export **spike**（trimesh 先；pyvista export_html vs 轻量 three.js 短 spike 再定产品依赖）；viewer 不阻塞 validator merge。

### M2c — 4/5 + EP baseline
- **S4** `mep.py`（**拥有全部 MEP 引用图检查**）：用 `idf_fragments` 解析 → `geometry→construction→material` + `people/lights/hvac→zone/schedule` 覆盖（block）+ schedule 完整性（复用 schedules.py）+ **对象语义**（SimpleGlazing standalone / Material:NoMass 正热阻 / schedule type 引用存在 / 必填字段 / 正值，block）。parse 失败 = 4_mep block + 同阶段重抽。合理性区间 = flag/占位。MEP 摘要表。
- **S5** `assembly.py`：只做 `assemble_intake_output` + Pydantic + **接受 S4 report/hash 的 backstop**（重复检查标 defense-in-depth、复用同函数、不另写 parser）。
- `read_ep_end` 断言 + warning policy → test_baseline。

### M3 — judge
- F2 harness：单阶段盲抽 executor + verdict schema v2；J0/J1 接线；**J4 保持 disabled stub**（不让"空 judge"进正式流）；root attribution 仅在 evidence/confidence 足够时；append-only verdict + hard-sample quarantine。

### M4 — 产品策略 + baseline
- hash 绑定 geometry approval + resume（批准后从 geometry hash 续 4/5，**不重抽 1**）；optional 3D viewer 集成；sm20/sm21 正 baseline + **负例语料**；cost/cache/latency 报告；`--intake-from` 标 `validation_scope=downstream_only`。

---

## 2.1 验收测试矩阵（per-milestone，纳入 re-verify Medium 3——不只靠"每条配单测"兜底）

| 里程碑 | acceptance tests（除每条 check 正反单测外） |
|---|---|
| **M0** | append-only：rejected attempts 不覆盖、accepted manifest/hash 正确；完整失效 DAG（0→1-5 … 4→5）+ 全局预算 + route 循环检测；approval 后 resume **不重跑 1/2/3**、批准 digest 失效逻辑；CheckReport v2 policy-事实分离（同 check 矩形 profile=block、非矩形=skip）|
| **M2a** | 真实坏 **bad-2f corridor-split** fixture（与 corrected anchor 分开）；**self-consistent wrong-dimension** fixture（证明确定性只 flag 内部一致、原图真值交 J0）；**wrong facade sign / 对称窗** fixture；半人工 0 失败返 `human_redraw_required` |
| **M2b** | **矩形内部边界 coverage hole** 负例（人为一对内墙都 Outdoors → kernel check 必失败）；封闭/法向/spec 引用正反；viewer headless 不可用 → 显式 skip 非假 PASS；sm20 golden 断言**稳定 check ids + 对象计数 + 关键 hash** |
| **M2c** | **no-mass / SimpleGlazing 多层 / missing schedule day type** 负例 fixture；idf_fragments parse 失败=4 block+重抽；S4 owner / S5 backstop 不重复归因；`read_ep_end` 阈值断言 |
| **M3** | judge **malformed/partial/insufficient_evidence/unknown** verdict、root attribution 不确定不路由、judge unavailable；两入口 `repair_feedback` vs `judge_retry_context` **不串线** 断言；per-stage+global budget；judge 测试全 mock/fake、不把模型措辞放进断言 |
| **M4** | `confirmation_policy=required|optional|disabled`；approval 后 resume 不重抽 1；`--reading-from` / legacy missing facade / `--intake-from`(`validation_scope=downstream_only`) bypass 语义；sm20/sm21 正 baseline + 负例语料 |

## 3. 本轮做 / 占位 / deferred（v2 修订）

| | 内容 |
|---|---|
| **本轮做** | M0 执行地基 / M1 reading schema 迁移 + IDF parser / S0–S5 确定性校验（含**矩形 coverage**、**MEP 对象语义**）+ 单测+真实坏 fixture / 二维视觉件 + trimesh mesh / F2 harness + J0·J1 / 用户门=策略+hash / EP 断言 baseline |
| **占位 stub** | 4_mep 合理性区间（§5.2）；J4 文本 judge **disabled stub** |
| **deferred** | 覆盖完整性**非矩形/void 泛化**（B5）/ reading provenance 富化分步（但 dimension chain 最小字段本轮做，不 defer）/ gt.json 富化（B2）/ corrections.json 评测归因（§5.4）/ pyvista 交互 viewer（spike 后定）|

## 4. 残留风险（已纳入 review，施工时盯）
1. reading schema 迁移要兼容旧 case（legacy facade/dimension adapter + flag）。
2. 失效 DAG/resume/approval-hash 的原子性（不覆盖坏 draw、批准后不重抽）。
3. judge harness 两入口不串线（`repair_feedback` vs `judge_retry_context`）的测试断言。
4. viewer headless skip 不能伪 PASS。
5. 全局预算 + 循环检测，避免 route 死循环。

---

## 5. 施工进度（2026-06-15 开工，全 M0–M4 一轮落地）

| 里程碑 | 状态 | 落地物（代码 + 单测） |
|---|---|---|
| **M0** | ✅ | `src/validator/checks/schema.py`（CheckReport v2：status/layer/check_version/profile/hash + `disposition()` 纯函数 policy≠fact）；`src/agent/execution/`（`manifest.py` append-only attempts + run_manifest + 内容寻址 hash / `stage_runner.py` registry+capability / `invalidation.py` 完整失效 DAG + resume + RunBudget 预算+循环检测 / `approval.py` geometry checkpoint digest / `policy.py` confirmation_policy+validation_scope / `routing.py` 失败分类）。`tests/test_execution_foundation.py` 19 测 |
| **M1** | ✅ | `src/agent/reading/`（P1a dimension chain + P1b facade image-local schema + legacy 迁移 adapter，flag 标注）；`src/validator/idf_fragments.py`（统一 eppy parser，所有 MEP check 共用）。`tests/test_reading_schema.py` 6 + `test_idf_fragments.py` 5 |
| **M2a** | ✅ | `src/validator/checks/reading.py`（结构 linter：唯一 id/合法 pen×kind/非退化/dimension 可解析/axis 一致/uncaptured 列表/链闭合 flag）；`src/agent/correction/geometry_validator.py`（A0§7 coverage/closure/zstack/zone-count/window-on-wall，shapely）；`facade.py`（image-local→world 翻译，sign 由约定+mirror、非 VLM 自声明）；`src/validator/checks/correction.py`（adapter + 跨图 reconcile + delta/audit 完整性）；`render_elevation_windows.py`（`*_elev.png`）。真坏 fixture × 3。`tests/test_checks_reading_correction.py` 19 |
| **M2b** | ✅ | `src/validator/checks/kernel.py`（zone 封闭 by-sums / 法向 / pairing gate 提 block / **矩形 coverage completeness block** / spec 自洽）；`render_building_3d.py`（trimesh GLB + headless 显式 skip 非假 PASS）。负例回归（互逆墙改 Outdoors → coverage 必失败）+ golden 计数。`tests/test_checks_kernel.py` 7 |
| **M2c** | ✅ | `src/validator/checks/mep.py`（引用图 geometry→construction→material + load→zone/schedule + schedule 完整性 + 对象语义 SimpleGlazing standalone/NoMass 正热阻/schedule type；parse 失败 fail-closed；合理性区间占位）；`assembly.py`（S5 backstop 归因 owner=4 + EP end 断言）。`bad_mep_semantics.json` 负例。`tests/test_checks_mep_assembly.py` 11 |
| **M3** | ✅ | `src/agent/judge/`（verdict schema v2：criterion status + not_applicable/insufficient_evidence + root_stage/confidence + retriable；`retry_stage_draw` 单阶段盲抽，两入口 repair_feedback vs judge_retry_context **不串线**；executor J0/J1 接线 + **J4 disabled stub** 非假 PASS + unknown 不路由 quarantine + append-only verdict）；J0/J1 `judge_rubric.md`。judge 测试全 fake。`tests/test_judge_harness.py` 15 |
| **M4** | ✅ | `src/agent/execution/validation_run.py`（`validate_case` 非侵入式跑全段 gate①、不动 `run_pipeline`；confirmation_policy 绑定 geometry digest；`--intake-from`→downstream_only scope）。sm20_anchor 正 baseline 全过 + 负例语料（fixtures）。`tests/test_validation_run_baseline.py` 6 |

**Codex 实现审阅闭环（2026-06-16，CHANGES REQUESTED → 5 findings 全修，[review](../logs/review/review/2026-06-16_pipeline_0-5_validation_implementation_review.md)）**：H1 `validate_case` 全 scope 缺必需产物原静默放行 → 加**必需产物表**逐项发 blocking ERROR + EP 改由 `policy.require_ep` 控（不再凭缺 `.end` 推断 pre-EP）+ digest 只从真产物算（杜绝 `{}` 伪 digest）；H2 `write_reports` 原覆写/伪造 `run_manifest.json` → 改写独立 `validation_manifest.json`（不冒充 M0 审计 manifest）；M1 空/空白 layer Construction 原 vacuous 放行 → 拦；M2 `kernel.spec_self_consistency` 声明集原并入 surface 自身 zone（逮不住未声明 zone）→ 只用 `bg.zones`/`zone_volumes` + closure 拦无 ZoneVolume 的 zone；M3 reading rect 崩轴退化 `and`→`or`。+10 回归测试。

**Codex re-verify（2026-06-16，CHANGES REQUESTED：4/5 PASS、High 1 PARTIAL，[reverify review](../logs/review/review/2026-06-16_pipeline_0-5_validation_reverify_review.md)）→ 全修**：High 残项=`validate_case` 只修了「缺文件」、**坏/陈旧的 2/3 产物仍空过**且 digest 绑到未校验字节 → 把 building_geometry 序列化抽成单一真源 [specs.py `building_geometry_dict`/`geometry_specs_markdown`](../../src/agent/geometry/specs.py)（pipeline.py 改用、输出零变），validate_case 把**磁盘 2/3 产物对账确定性重建**（`kernel.artifact_consistency` 不符即 block）、digest **仅在 2/3 一致且 2_modelling 过后**才算；Medium 残项=`zone_closure` 漏查「声明了但无任何面」的 zone → 遍历 `bg.zones∪zone_volumes∪有面 zone`。+3 回归（坏 specs/坏 building_geometry/无面 zone）。

**Codex re-verify #2（2026-06-16）→ CLOSEABLE**（[reverify2 review](../logs/review/review/2026-06-16_pipeline_0-5_validation_reverify2_review.md)）：无 blocking findings，High-1 残项 + 次要 Medium 均 PASS，上轮 5 条 intact。**三轮实现审阅闭环完成（CHANGES REQUESTED ×2 → CLOSEABLE）。**

**测试 103 → 191 → 201 → 204 全绿。** 纪律全守：每条确定性 check 配正反单测 + 真坏 fixture；policy≠fact（profile 切 not_applicable 不另写 policy）；append-only 不覆盖坏 draw；judge 不注入 prompt；未动 `IntakeOutput` 契约 / 未动 `run_pipeline` / 未动下游。**残留（deferred 不阻塞）**：viewer 交互层（pyvista/three.js spike）；4_mep 合理性区间（占位待 MEP 输入富化）；judge LLM/VLM 真实接线（harness 已就位、judge_fn 可插拔）；resume 接进 `run_pipeline`（地基已就位、validate_case 已用）。

---

_2026-06-15 v3 — 纳入 Codex re-verify Medium：M0 补**完整失效 DAG**（0→1-5 … 4→5）+ approval 绑 **accepted geometry checkpoint digest**（building_geometry+geometry_specs+kernel report+version）+ resume 不重抽；M1 P1b **facade canonical image-local schema**（local_x_positive=image_left_to_right、不混 east/west；world 派生归 correction）；新增 **§2.1 per-milestone 验收测试矩阵**（M0 状态机/DAG/budget、M2a-c 真实坏 fixture、M3 judge unknown/不串线、M4 兼容路径/golden）。_
_2026-06-15 v2 — 纳入 Codex 设计+施工双 review（双 CHANGES REQUESTED）：加 M0 执行/审计地基、失败分类、reading schema 迁移、IDF-fragment parser、矩形 coverage 本轮做、check/verdict schema v2、4/5 归属去重 + MEP 对象语义、facade 仅 image-local（world 落位归 correction）、uncaptured 不 block、viewer trimesh 先行、用户门=调用策略+hash、真实坏 fixture 语料、依赖序改 M0→M1→M2a→M2b→M2c→M3→M4。_
_2026-06-15 v1 — 初版施工方案。_
