# 审阅请求（RE-VERIFY）：0–5 校验架构设计+施工方案 修订复核

- **日期**：2026-06-15
- **发起**：主开发 Agent（Opus）
- **审阅方**：Codex（跨模型）
- **类型**：**re-verify**——复核两份 CHANGES REQUESTED review 的 findings 是否已正确落实，判两份是否 closeable

## 0. 背景

两份 review（双 CHANGES REQUESTED）已收到、**全盘接受**并据此修订：
- 设计 review：[review/2026-06-15_pipeline_0-5_validation_architecture_design_review.md](../review/2026-06-15_pipeline_0-5_validation_architecture_design_review.md)（4H/4M/2L）
- 施工 review：[review/2026-06-15_pipeline_0-5_validation_build_plan_review.md](../review/2026-06-15_pipeline_0-5_validation_build_plan_review.md)（4H/6M/2L）

修订落到：
- **设计** [architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md) → **v7**（§0.3 改写 + 新增 §0.4 十条 + §1 2/3·5 + §3.2 + §4 不变量 6）
- **施工** [architecture/pipeline_validation_build_plan.md](../../architecture/pipeline_validation_build_plan.md) → **v2**（新增 M0 + 依赖序 M0→M1→M2a→M2b→M2c→M3→M4 + 全部施工 findings）

## 1. 逐 finding 处置对照（请逐条核对落点是否正确、充分）

### 设计 review

| Finding | 处置 | 落点 |
|---|---|---|
| **设计 H1** 确定性判坏必弹上游 / 0 无法自动重抽 | 改失败分类 4 类；确定性后置 fail-closed 记 code defect、**不弹上游**；0=`manual`→`human_redraw_required`；全局预算+循环检测；hard sample→`quarantined` | contracts §0.3「失败分类+重做规则」表 + §4 不变量 6；build M0 + §0 失败分类表 |
| **设计 H2** facade_axis.base_world 越界 | 0_reading 只产 image-local（view_facade/local_x_direction/mirror+证据）；world_axis/base_world **归 1_correction** 生成；sign 需独立证据 | contracts §0.4#2；build M1 P1b |
| **设计 H3** 2f 确定性线不保证 + correction 擦归因 | stroke↔dim 改「内部几何-尺寸一致性」**低置信 flag、非 2f 主验收**；加 correction delta/audit（矛盾/依赖 testdata→带来源 conflict 记录）；固化真实坏 fixture | contracts §0.4#3·#4；build M2a（S1 delta-audit + bad-2f fixture）|
| **设计 H4** 覆盖洞 deferred + 2/3 无 judge | **矩形 coverage 本轮 block**（共享边→expected interfaces vs 实际互逆对）；B5 只泛化非矩形；加负例回归 | contracts §0.4#5 + §1 2/3 ④ + §3.2#3；build M2b |
| **设计 M1** uncaptured 非空不应 block | block 改「字段存在且为 list」；加真不变量（唯一 id/有限数值/非退化/合法 pen×kind/可解析/axis-端点一致） | contracts §0.4#6；build M2a S0 |
| **设计 M2** 4/5 归属重复 + 引用图错 | Construction 不引用 Schedule；4 拥有全部 MEP 引用图；5 仅装配+Pydantic+S4 backstop | contracts §0.4#7 + §1 5 校验/归属表 + §3.2#5；build M2c |
| **设计 M3** MEP 漏对象语义 | 加确定性对象语义（SimpleGlazing standalone/NoMass 正热阻/schedule type/必填/正值）；区间仍 flag | contracts §0.4#7；build M2c S4 |
| **设计 M4** 用户门应是调用策略 | viewer 始终可产；`confirmation_policy` 由调用方定；批准绑 building_geometry hash、批准后不重抽 1 | contracts §0.4#9 + §1 2/3；build M0/M4 |
| **设计 L1** judge 密度自相矛盾 | 统一：自动 judge 只 0/1/4；2/3 仅用户门/dev 手动；5 无 | contracts §0.3「judge 密度」段 |
| **设计 L2** verdict 需 unknown/归因不确定 | 加 not_applicable/insufficient_evidence/root_stage\|null/root_confidence/retriable；unknown 不自动路由 | contracts §0.3 门②；build judge verdict v2 |

### 施工 review

| Finding | 处置 | 落点 |
|---|---|---|
| **施工 H1** 缺执行/checkpoint 层 | **新增 M0**：StageRunner/registry + run_manifest + append-only attempts + 失效 DAG + resume + hash 绑定 approval；没这层不接 gate | build §1 模块 `src/agent/execution/` + M0 |
| **施工 H2** 不能复用 `_make_correction_validator` | 抽 `draw_json_once` + 单阶段 `retry_stage_draw`；跨阶段 route 归 execution；两入口 `repair_feedback` vs `judge_retry_context=None` 不串线；verdict 加 retry_stage/retriable/root_confidence | build §1「抽两层」+ M3；contracts §0.3 |
| **施工 H3** S0 算法现 schema 不可实现 | **P1 扩成 reading schema 迁移**：dimensions 加 chain_id/role/order/value_m/text_verbatim/anchor；S0 先做 chain closure+内部一致；原图真值交 J0/OCR | build M1 P1a + M2a S0；contracts §0.4#3 |
| **施工 H4** 矩形 coverage 不应随 B5 | 同设计 H4：矩形本轮 block + 负例回归 | build M2b；contracts §0.4#5 |
| **施工 M1** 缺统一 IDF-fragment parser | 加 `src/validator/idf_fragments.py`（一次解析 bundle→对象索引，checks 共用、禁各自 regex；解析失败=4 block+重抽） | build §1 模块 + M1 P2 + M2c |
| **施工 M2** S4/S5 重复解析 | S4 拥有全部引用图；S5 只 assemble+Pydantic+backstop；interzone/schedules 保留原位作 adapter | build M2c + contracts §0.4#7 |
| **施工 M3** Check schema 太薄 | CheckReport v2：status/check_version/capability profile/artifact·attempt hash/机器可读 evidence；**policy 与事实分离** | build §1 schema.py + M0；contracts §0.4#8 |
| **施工 M4** uncaptured 非空 | 同设计 M1 | build M2a S0；contracts §0.4#6 |
| **施工 M5** viewer 先 spike | trimesh（已是依赖）出 mesh+静态投影先；pyvista/three.js spike 后定；viewer 失败不阻塞 check、headless skip 非假 PASS | build §1 render_building_3d + M2b §0.4#10 |
| **施工 M6** 测试缺坏样本/状态机/兼容 | 列入真实坏 fixture（bad-2f/self-consistent wrong dim/coverage hole/wrong facade sign/no-mass·SimpleGlazing·missing daytype）+ 状态机/预算/失效/兼容路径 + sm20 golden 断言稳定 ids | build M2a–M4 fixtures + §0 总纪律① |
| **施工 L1** “全段并行”过强 | 改“纯 validator 可并行 / 接线按依赖串联” | build §2 标题 + §0 纪律⑦ |
| **施工 L2** `--intake-from` 语义 | 标 `validation_scope=downstream_only`、不跑 stage check/不等批准 | build M4；contracts §0.4#9 |

## 2. 请复核 + 验收

- 逐条判 **PASS（已正确充分落实）/ PARTIAL / FAIL**，PARTIAL/FAIL 给具体缺口。
- 特别确认三处**原设计实质漏洞**是否真补上：① 确定性 fail-closed（设计 H1）② M0 执行地基（施工 H1）③ facade 越界 + reading schema 迁移（设计 H2 / 施工 H3）。
- 有无**修订引入的新矛盾**（如 §0.4 与 §1 残留旧表述打架）？我已修 §1 2/3·5 几处直接矛盾，但 §1 各段正文仍有未逐字改的旧描述、靠 §0.4 覆盖——这样可接受吗，还是要求把 §1 正文也逐段改齐？
- 结论：两份 review 是否 **closeable**；若否，列 must-fix。
- 命名：`review/2026-06-15_pipeline_0-5_validation_reverify_review.md`

> 闭环后即按 build plan v2 **M0** 开工（用户定"全部确定完、Codex 审过再施工"）。
