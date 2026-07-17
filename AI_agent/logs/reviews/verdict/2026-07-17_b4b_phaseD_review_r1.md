# B4b Phase D 升一档执行审 r1（Opus 子代理 · 独立上下文 · 活体探针）

日期：2026-07-17　审向：terra 施工（GPT 中档，含续作 r1 全链接通）→ Opus 跨厂商升一档审
基座 HEAD `239dc00`；分支 `6.15_ValidationArchM0toM4`；改动未 commit。
范围：B4b 全系列**最后封口批**（run-stage/cache/renderer/CLI + `SCORER_SCHEMA "7"→"8"` + full identity cache + sidecar/PNG atomic pair + typed polygon renderer/gray hatch + CLI service dispatch + legacy v2 封口 + VA-C7 六项）。

---

## 总裁决：APPROVE-WITH-CHANGES

**无 MAJOR。** 封口批的四条信任根（全链真接通 / cache identity 全量 / 原子 pair / legacy 字节锁）全部经**活体探针实证为真**，非假绿、非又交半成品。剩 2 MINOR（均落在**当前休眠的 v3 基础设施**上、不腐蚀权威 sidecar、且其一已被派工单预先承认可延后）+ 2 NIT。可封口，MINOR/NIT 登记为随手跟进债，不构成返工阻断。

findings 计数：**MAJOR 0 · MINOR 2 · NIT 2**。

---

## 探针记录（真 fixture + 真 service，零 mock 信任根）

| 探针 | 内容 | 结果 |
|---|---|---|
| **A 全链真实性** | 复现 e2e run-stage → dump 真实 sidecar | **CONFIRMED 真**：`schema=8`/`c2_scored`；segment_rows 真（status=complete，误差 0.0）；claim_rows 真（含真实 `ledger_content_sha256`）；score_criteria 真评分（`boundary_complete` 分母 16/passing 16、`window_plan_geometry` 2/2、`window_elevation_geometry` 2/2）；reference ledger digest ≠ `canonical_sha256([])`（非空壳）；grade.png 真 16KB PNG。**非 stub/pseudo。** |
| **B cache identity 完备** | 改 D1 测试**未覆盖**的 9 个 identity 字段 | **CONFIRMED 全量**：`product_applicability_sha256`/`absence_applicability_sha256`/`helpers.segment_scorer`/`helpers.grade_renderer`/`capability.path`/`gt.content_sha256`/`manifest.case_metadata_sha256`/`product.stage`/`product.attempt` **每一个都触发 cache miss**。`load_cached_score` 用整体 `ScoreIdentityV8 !=` 结构相等，**无组件漏进 identity**。 |
| **schema 7→8 收敛** | 源码残留扫描 | **CONFIRMED**：`run_stage.SCORER_SCHEMA=="8"` 且 `score_schema.SCORER_SCHEMA=="8"`；`test_d1_schema_zero_to_seven` 断言 schema 0–7 全 miss；源码无 `SCORER_SCHEMA="7"` 残留。 |
| **D 原子 pair** | 跨目录 / grade digest 不符 / **首次(PNG)** replace 故障 / 持久半 pair | **CONFIRMED 锁死**：跨目录→`score_atomic_write_failed`；digest 不符→`score_sidecar_invalid`；**首次 replace 失败**（D2 单测只测了第二次）→旧 pair 完整回滚、cache 仍服务旧值；持久「新 PNG+旧 sidecar」(SIGKILL between replaces)→读侧 digest 复验返 `None`，**半 pair 永不服务**。 |
| **3 byte parity** | `test_d1_d2_d3_...byte_for_byte` 核验 | **CONFIRMED 真比对**：line 205-206 逐字节 `read_bytes()==read_bytes()` 比 run-stage 与 CLI subprocess 产出的 `score_vs_gt.json` + `grade.png`，非恒真式。二者经同一 `score_attempt_service`/`score_typed_attempt`。 |
| **9 correction v3 分支** | 类型自洽核 + caller 扫描 | correction 分支用 `product_segment.world_along_interval.lo/.hi`/`.floor_id`/`.facade_family` — 经查 `FacadeSegment`(correction schema) 确有这些属性（同 GT `WorldInterval` 类型），**无 AttributeError 陷阱**；但 `score_typed_attempt(stage="correction")` **零集成测试**（见 MINOR-1）。 |
| **10 动态导入** | `gt_openings_to_va_claims` 可否正常导入 | **CONFIRMED 无循环**：可直接 `from ... import`，score_service 正常加载 → line 197 `__import__` 是纯冗余气味（同函数 line 109 已 `from` 导入该模块），非掩盖 cycle（见 NIT-1）。 |
| **D5 VA-C7 真断言** | `invoke` helper 溯源 | **CONFIRMED 真**：`va_tests.invoke` 调真实 `derive_opening_claim_applicability` 引擎；六项（第八 claim/重复 opening/悬空 segment/悬空 source/凹形多段 len>4/删声明双调用 digest 变化/hidden-untrusted negative）逐条真 `pytest.raises` 匹配真实错误码，非占位/恒真。 |
| **回归/legacy 锁** | 定向套件 | **151 passed**（contract/render_grade/judge_batch/run_stage_flow/phase_b/phase_c/va_applicability）+ phase_d **10 passed**；legacy pixel hash `c44204…` + 采样点 `(300,300)=(238,238,234)`/`(50,900)=(150,150,145)` 锁死。（29 warnings 为既有 Pillow/run-config 噪声，无害。）|

---

## 六出口 gate 逐一核验

| Gate | 结论 | 依据 |
|---|---|---|
| **D1 cache-identity** | **PASS** | 探针 B：整体结构相等，9 个未覆盖字段全 miss；schema 0–7 全 miss；输出 hash/grade digest 独立复验。 |
| **D2 atomic-artifacts** | **PASS** | 探针 D：首/次 replace 故障均回滚旧 pair；持久半 pair 读侧 digest 复验拒；spec §10.4 顺序（PNG→sidecar commit marker）咬合，「新 sidecar 指向旧 PNG」被排序结构性排除。 |
| **D3 gray-hatch/totality** | **PASS（带 MINOR-2）** | `validate_typed_render_totality` 真 raise `scoring.render_totality`（未知 target 探针+单测实证；少 target/claim 防御性覆盖）；NA hatch 常量按 §11.3 冻结。**divergence**：§11.3 partial-interval hatch + §11.4「区间 clip 不守恒」在 box-rail 简化渲染模型下未实现（MINOR-2）。 |
| **D4 legacy-v2-regression** | **PASS** | legacy `render_grade`/`render_grade_to_path`/`_grade_transform` 一行未动（diff 纯 additive，新函数在 line 1015 后追加）；pixel hash + 采样点锁；151 定向绿。`render_grade_to_path` == `render_grade().save()`，run-stage 新 buffer 保存字节等价。 |
| **D5 va-c7-closed** | **PASS** | 探针 D5：六项经 public Va/B4b seam 逐条真断言；`facade_applicability.py` 未动（diff 确认）；no-op source scan 真。 |
| **D6 protected-assets-clean** | **PASS** | 生产路径（execution/correction/reading/pipeline.py）零 import 8 个新 judge 模块；execution 不 import run_stage（judge 留脚本侧）；diff 仅 5 tracked+2 new，无 golden/gt/production-schema/case_tests；`git diff -- case_tests` 空。 |

---

## Findings 逐条

### MINOR-1 — correction v3 装配分支 shipped-untested（已披露·休眠基础设施）
- **文件**：`src/agent/judge/score_service.py:149-153,159-171,175-188`（`score_typed_attempt` 的 `stage=="correction"` 分支）
- **场景**：`score_typed_attempt` 仅经 `test_d1_d2_d3_...byte_for_byte` 以 **stage="reading"** 跑通 e2e；correction 装配路径（`CorrectedGeometryV3.model_validate` → `extract_correction_plan_segments` → facade containment 绑定 → window→OpeningObservation 转换）**零集成测试**。子助手（extract/bind/resolve host）phase B/C 各有单测，但**装配胶水层**从未端到端跑过。
- **CONFIRMED/PLAUSIBLE**：CONFIRMED 无测试 + CONFIRMED 类型自洽（属性核实无 AttributeError）；未发现真 bug。
- **定性**：**非隐瞒**——terra 简报 r1 明确披露「本批 e2e fixture 覆盖 reading v3，主控可在全量/抽样时补测 correction v3」；派工单亦预承认此为 capability 边界。当前**无任何 v3 GT 的活 case**，整条 v3 路径休眠，correction 分支不会在生产被触达。
- **修法方向**：在依赖 correction v3 前补一条 e2e（GT+匹配 CorrectedGeometryV3+bindings→`score_typed_attempt(stage="correction")`→断言 sidecar/segment binding/host）。**非返工阻断**，登记为债。注意：装配层使用 `bind_correction_window_segment` 但未调 `resolve_correction_window_host`（room 直接取 `window.room`）——补测时一并核实 host 解析是否应参与。

### MINOR-2 — grade renderer 未实现 §11.3 partial-interval hatch / §11.4 clip-conservation gate
- **文件**：`scripts/tool_scripts/render_grade.py:145-157`（claim box 渲染）+ `validate_typed_render_totality:51-81`
- **场景**：typed renderer 采用**简化的 claim-box 网格**（每 claim 一个 48×14 小方块：complete/within/miss 实色，或整块 NA hatch），而非 spec §11.3 描述的**几何 interval rail + unobserved_intervals 局部斜线**。因此：①partial claim（部分 applicable + 部分 unobserved）被画成整块实色，丢失 partial-NA 视觉；②§11.4「区间 clip 不守恒 → render_totality reject」在无 interval clip 的模型下**结构性 N/A、未实现该 gate 分支**。`validate_typed_render_totality` 只守 未知/少 target + claim 未渲染。
- **CONFIRMED/PLAUSIBLE**：CONFIRMED（读代码 + §11.3/§11.4 对照）。
- **影响**：**仅 grade 可视化**（人工复检辅助图）。权威评分在 sidecar，`applicable_intervals`/`unobserved_intervals` 完整保留、不受影响；render totality 主齿（未知/缺失 target/claim）有效。当前无活 v3 case 触达 partial。
- **修法方向**：二选一——(a) 实现 §11.3 partial-interval hatch + §11.4 clip-conservation 断言；(b) 若 box-rail 简化是有意决策，回稿 §11.3/§11.4 明确 C2 grade 采用 claim-box 模型、clip-conservation 归 sidecar 层。**非阻断**，建议登记待 B5b 消费 grade 时定夺。

### NIT-1 — 冗余动态导入
- **文件**：`src/agent/judge/score_service.py:197` `__import__("src.agent.judge.opening_claim_score", fromlist=["gt_openings_to_va_claims"])`
- **实证**：该模块同函数 line 109 已 `from ... import (...)`；`gt_openings_to_va_claims` 可正常直接导入、无循环。纯风格不一致，建议并入 line 109 的 from-import。无功能影响。

### NIT-2 — 不可达防御分支
- **文件**：`scripts/tool_scripts/run_stage.py:1171-1174` `elif render_needed:`
- **实证**：前置 `if render_needed or not grade_path.exists()` 为 False 时，`render_needed` 必为 False，故 `elif render_needed` 恒 False、永不执行。注释自称「defensive clarity」，实为死代码。建议删或改成有意义的后置断言。无功能影响。

---

## 覆盖 / 安全锁 / 禁区合规
- **legacy sidecar 写无回归**：核 git 旧版——OLD `score_path.write_text` 本就在 `if sidecar is None:` 内（8 空格缩进），NEW 经 `_commit_legacy_grade_pair` 在同条件下写，行为等价且升级为原子 pair。**非之前担心的「无条件写被移除」**。
- **cache 语义**：`load_cached_score` 三重复验（整体 identity != / output_sha256 / grade_png_sha256），schema 0–7 全 miss，无「兼容默认值」提升旧 sidecar。合 spec §10.2/§10.4。
- **CLI/run-stage 共用 service**：二者均入 `score_attempt_service`（typed→`score_typed_attempt`；legacy→注入 evaluator），**policy 未复制**；byte-for-byte 实证等价。合 spec §10.5。
- **禁区**：production output schema / view_manifest emitter / RunManifest artifact union / case_tests·gt·golden / B5·B5b·B6 **全未动**（diff+扫描确认）。

## review-ask 核实
- 简报 r1「**无新增 review-ask**」——**属实**。原 2 条已被主控裁决关闭（①退回续作=已接通全链；②同目录 committer + 读侧 PNG digest 复验=充分，不上目录级发布）；探针 D 独立验证该裁决成立（半 pair 读侧确被拒）。剩余披露项（correction v3 e2e、floor-line/oversplit/negative inert criteria）为 capability 边界/Phase C 已裁决接受的 explicit-NA，非阻断问题——探针 A 确认 inert criteria `eligible=False` 是真 NA、**无伪造 0 分或伪 pass**。本审将 correction v3 e2e 转记为 MINOR-1 跟进债。

---

**结论**：封口批全链真接通、cache/原子性/legacy 三锁经活体探针实证咬合，无 MAJOR。APPROVE-WITH-CHANGES——批准封口，MINOR-1（correction v3 e2e 债，已披露·休眠）+ MINOR-2（grade partial-clip 渲染 divergence，休眠·不腐蚀 sidecar）+ 2 NIT 登记为随手跟进，均不阻断合并。
