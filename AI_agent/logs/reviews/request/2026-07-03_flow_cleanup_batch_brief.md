# 流程清理批次 · 执行简报（2026-07-03）

> **协作**：Claude 出方案 → **Codex 审此简报** → Claude 裁决 → Codex 执行 → Claude 复核。
> 本简报含一处**方案类决策**（判卷容差设计，§1.6）需重点审。
> 视觉规格的**可执行参照** = `AI_agent/logs/review/request/2026-07-03_grade_prototype_reference.py`
> （+ 渲染样张 `overlay_proto/grade_sheet_v2.png` 等，仓库根 `overlay_proto/`）。

## 0. 背景与范围

上轮 `run_2026-07-02_sonnet_flow_e2e` = flow P1 首次真实端到端跑通，暴露 5 点流程缺口。
本批把这 5 点一次收口，**只动流程/产物层，不碰 0–5 契约、不碰 gt 隔离铁律、不重录 golden**。

5 项：① 根目录跑前配置文件 · ② 全流程型号钉死进 baseline · ③ attempts 全产物留痕 ·
④ overlay 重画为 grade 批卷（含新配色/墙窗分层/立面/容差带）· ⑤ F1 修（judge packet 首-pass gt-evidence 空）。

**用户已锁定的设计**见 §1，逐项执行见 §2，铁律见 §3，审阅需求见 §4，测试见 §5。

---

## 1. 已锁定的设计决策（用户 2026-07-03 逐条 ratify）

### 1.1 改名 overlay → grade（批卷）
- 概念/文件/产物统一改：`scripts/tool_scripts/render_overlay.py` → `render_grade.py`；
  产物 `overlay.png` → `grade.png`（段根升级件同名）；术语 "overlay" 退场（代码注释/CLI 打印/report 索引）。
- `_overlay_transform.py` 可保留文件名（纯 transform，无语义）或一并改 `_grade_transform.py`——Codex 定，保持 import 一致即可。

### 1.2 颜色 = 判定，画法 = 元素类别（**两轴正交**）
- **颜色只表判定**：`hit=绿实线` · `miss=红虚线`（窗盒另加淡红填充）· `extra/位置错=红实线`。
- **元素类别只靠画法**（不靠色相）：外边界=最粗(6px)画在footprint边 · 内墙=中粗(4px)画在内部线段 ·
  窗=**外挂车道**(plan，footprint外侧偏移~11px的平行条) / 轮廓盒(elevation) · 楼板线(elevation)=中粗。
- **不再用蓝色**（原型中途试过的边界蓝色作废）。

### 1.3 墙按 zone 邻接**合并线段**画（关键正确性）
- 内墙不是"坍缩坐标画整条通到底"，而是从 zone 矩形抽**共享边线段**、**合并重叠区间后每段只画一次**。
- 效果：走道等开敞段不被竖墙横穿；miss 红虚线单相位干净（修掉逐块重画多相位叠加的 bug）。
- 参照 `2026-07-03_grade_prototype_reference.py:interior_coords()` + `merge()`。

### 1.4 容差内漂移（命中但 |Δ|>0.05m）显示
- 画**淡绿 ±tol 容差带** + **灰发丝 gt 真值中线** + 产物绿线画在 read 位置。
- **只在 |Δ|>0.05m 才画带/发丝**——贴合的墙纯绿保持干净（完美 run 无带、一片平静）。
- 精确偏移量**不画进图**（留机读 `score_vs_gt.json`）；图只表 0/1 命中 + "是否贴容差边"。

### 1.5 元素表示细则
- **miss**：红虚线；窗为盒时加**淡红填充**（"该有没有"的红幽灵）。
- **extra**：红实线/红实框。
- **窗位置画错** = gt 原位画 miss 红幽灵（淡红虚框）+ 产物错位处画 extra 红实框 + 一条 `displaced` 灰虚连线牵着。
  （= scorer 现成 miss+extra 的自然呈现，不需新配对逻辑；连线是可选增强，见 §4-b。）
- gt 参考底 = 淡灰 zone 填充（安静、不抢眼）。

### 1.6 判卷容差 = judge 侧两把独立尺子 · per-run 可配置（**方案类决策，重点审**）
- **现状**：`DEFAULT_WALL_TOL_M=0.30 / DEFAULT_WIN_CENTRE_TOL_M=0.40` 硬编码在
  `src/agent/judge/reading_score.py`，`correction_score.py` **import 同一套** → 目前 reading/correction **共用一把、非 per-run**。
- **要做**：拆成**两把独立尺子**（reading grade / correction grade），提到①根配置的独立 `grade:` 段（见 §2.1），
  **不进 correction.yaml**（那套是确定性核坍缩坐标用的生产尺、另一回事）。
- **默认值**：两把先设**相等**（0.30 / 0.40），per-run 可分别调。
- **设计原则（写进配置注释 + guide）**：
  - correction 是 **gt-盲 + image-盲**，只修内部不一致（跨层抖动/外包/过度分割），**修不了"连贯读错"的准确度误差**。
  - ∴ **reading grade 是真正的准确度闸门**；**别让 reading 比 correction 松**（否则静默缺口：过 reading→correction 修不动→correction 判卷才报红→已无从补救）。
  - correction grade = 成品质量硬门 + 抓 correction **自己造的**结构错；补救准确度错的唯一杠杆在上游（reading 判卷不过→重读）。
  - 两表对同一 gt，**哪里不一样 = correction 结构操作净效果**（合并/外包=进步、并坏=退化）。

### 1.7 reading + correction 各出一套 grade · 都对同一 gt
- `reading_score`（J0）判 0_reading、`correction_score`（J1）判 1_correction，都对 `gt.json`。
- 一张 grade 整图 = 一段 × 一 attempt 的合成图：**平面各层 + 四立面**（N/S/E/W）拼一张。
- 立面判**横向 x/宽/数**；竖向 sill/head 用 gt 当参考底（当前不判竖向，留 backlog）；立面元素含**边界轮廓 + 楼板线 + 窗**（都上判定色）。

### 1.8 图↔证据同源
- grade 着色**直接读** accepted/该 attempt 的 `score_vs_gt.json`（确定性 scorer 输出），不在渲染里另算几何判定。
- 命中/漏/多是**确定性代码**（`_match_lines`/`_match_windows`）判的，非 LLM judge；judge 拿它当 advisory 证据、StageVerdict 仍裁决权威（不变）。

---

## 2. 逐项执行指引

### ② 型号钉死进 baseline.models（先做，最独立）
- **问题**：`baseline.json.models` 现只记 correction/default，**漏 reading 模型**（上轮 reading 是 `claude-sonnet-5` 经 Agent tool `model=sonnet` 别名解析，没落痕 → 踩 provenance 纪律）。
- **做**：`record_baseline.py` 把**每段** model_id + effort + 主控标识全落 `baseline.models`（reading 段显式含 `claude-sonnet-5`）。
- reading 段模型来源：从①根配置的 `models.reading` 读（见 §2.1），无则 fail-closed 或显式 `unknown` 占位（别静默空）。

### ① 根目录跑前配置文件（类 llm.yaml）
- 新 `<run>/run_config.yaml`（或复用 `llm.yaml` 扩段——Codex 定，倾向独立文件避免和 LLM 工厂配置耦合），字段：
  ```yaml
  scope:   { stages: [0_reading, 1_correction, 2_modelling, ...] }   # 本 run 跑哪些段
  judge:   { mode: stop|off }                                        # judge 开关
  review:  { reading: true, correction: true, geometry: true }       # 3 个人工校验开关
  models:  { reading: claude-sonnet-5, correction: ..., default: ... }  # 各段型号(喂 §2)
  grade:   { reading:   { wall_tol_m: 0.30, window_centre_tol_m: 0.40 },
             correction:{ wall_tol_m: 0.30, window_centre_tol_m: 0.40 } }  # §1.6 两把尺
  ```
- 作用三合一：**跑前确认单**（人过一遍）+ **溯源件**（进 baseline）+ `flow` 直接读（scope/judge/review/models/grade 都从这里取，不再散在 CLI flag）。
- 向后兼容：文件缺失时 `flow` 退回现默认行为 + warn（别硬 raise）。

### ③ attempts 全产物留痕
- **去掉** `run_stage.py:499` 的 accepted-only 门：`_judge_gt_artifacts`（改名 `_grade_artifacts`）对**每个** attempt 都跑 score + 渲 grade，落各自 `attempts/NNN/{score_vs_gt.json,grade.png}`。
- **accepted 的**：copy 一份升到段根目录（`<stage>/grade.png`）+ 进 `report/eyeball/`（现只在 attempts/）。
- 所有 attempt 平等留痕；通过的天然是最后一次。reading + correction 同规格。
- ⚠️ 与 §2-⑤(F1) 有交互：per-attempt 渲染依赖该 attempt 的 manifest 记录已落盘（见 F1）。

### ④ overlay → grade 重画
- 按 §1.2–1.8 全套重写 `render_grade.py`（参照 `2026-07-03_grade_prototype_reference.py` + `grade_proto5.py` 的两表布局）。
- 覆盖 reading 与 correction 两 stage；plan + 四立面合成一张。
- 保留 `render_grade_to_path()` + CLI；`run_stage.py` 调用点改名跟进。
- 图例/标题里的中文/特殊字符（`≈`/`≤`/`✗`）换 ASCII（DejaVu 无字形 → □）。

### ⑤ F1 修（judge packet 首-pass gt-evidence 空）
- **根因**：`_judge_gt_artifacts`（run_stage.py:496）从磁盘 reload manifest，但当前段 accept 在 `run_one_stage` 返回后才 `manifest.save`（:994）→ 首 pass `rec is None` → score_vs_gt/overlay/score_criteria 全空；二 pass 自愈。
- **修向**：`run_one_stage` 内 accept 后**即持久化** manifest（或把 in-memory manifest 传进 `_grade_artifacts`），使 packet 构建时 `rec` 已在。
- **测试**：补端到端**首-pass** packet 内容测试（现单测未覆盖此时序）。

---

## 3. 铁律 / 不变量（不得破）
1. **gt 隔离**：grade/score/render/policy 全 judge-side；`validator/`、`pipeline`、`execution`、`correction` **绝不 import gt**；`test_gt_discipline` 必须仍绿。
2. **契约不动**：IntakeOutput 11 字段、CorrectedGeometry schema、reading schema 全不改。
3. **不重录 golden**：本批纯流程/产物层；sm20/sm21 golden baseline 不动，现有 9 strict xfail 不受影响。
4. **run_pipeline 生产路径不碰**（§ 桶③已关闭，勿回折）。
5. **向后兼容**：①根配置缺失、旧 run 无新字段 → 软降级 + warn，不 fail-closed。

---

## 4. 审阅需求（Claude 自报，请 Codex 重点看）
- **a｜§1.6 容差设计**（方案类决策）：两把独立尺 + 默认相等 + "别让 reading 更松" 的原则，是否成立？配置放独立文件还是 llm.yaml 扩段？是否该把 reading/correction 默认设成**不等**（如 correction 更紧）？
- **b｜§1.5 displaced 连线**：miss+extra 的配对连线是"可选增强"——scorer 不做配对，连线要不要做进正式版？若做，配对规则（最近 miss↔extra 且 ≤某距离）定在哪层（judge scorer 出配对 or 渲染端就近连）？倾向**先不做配对连线**、正式版只画 miss 幽灵 + extra，连线留 backlog。
- **c｜①配置文件形态**：独立 `run_config.yaml` vs 复用 `llm.yaml`——哪个副作用小？grade 容差喂进 `score_floor(wall_tol=,win_tol=)` 的线程化路径怎么走最干净（judge executor → scorer）？
- **d｜③×⑤ 交互**：per-attempt 渲染是否必须等 F1 修好（manifest 时序）才不出空图？执行顺序建议 ⑤→③。
- **e｜④立面数据**：correction 侧立面窗判定，`correction_score` 是否已产四立面 windows（reading 侧确认已有）？若 correction 缺某立面数据，grade 该画"无数据"占位而非漏画。

---

## 5. 测试要求
- 新增/改：`render_grade` 单测（hit/miss/extra/drift-band/wrong-position 各一 fixture，断言不抛 + 关键像素/元素计数）；per-attempt 产物落盘测试（每 attempt 有 grade.png，accepted 升段根）；①配置读取 + 默认/缺失降级测试；②baseline.models 含 reading 型号断言；⑤首-pass packet gt-evidence 非空测试。
- 全量 `pytest` 保持绿（现 410 + 9 xfail）；`test_gt_discipline` 必绿。
- 执行分批：**Batch 1** = ⑤(F1) + ②(型号) + ①(配置)；**Batch 2** = ④(grade 重画) + ③(per-attempt 留痕)。每批 Codex 执行后 Claude 大节点全面审（自跑 pytest + 逐行 diff）。

---

## 6. 交付物清单
- `render_grade.py`（新，替 render_overlay.py）+ `_grade_transform.py`（或保留原名）
- `run_stage.py`：调用点改名 + 去 accepted-only 门 + per-attempt 渲染 + accepted 升级 + F1 时序修
- `record_baseline.py`：models 全段落痕
- `<run>/run_config.yaml` 读取接线（`flow` + record_baseline + scorer 容差线程化）
- `src/agent/judge/{reading_score,correction_score}.py`：容差从配置注入（保留常量默认）
- 测试若干（§5）
- guide/contracts 文档同步（术语 overlay→grade、容差两把尺、per-attempt 留痕、①配置）——**这部分 Claude 亲手改**（AI_agent/ + skills 文档）

---

## 7. 裁决 + 增补（据 Codex 审 `review/2026-07-03_flow_cleanup_batch_review.md`）——**本节权威，执行以此为准**

Codex 结论 = **APPROVE-WITH-CHANGES**；Claude 裁决 = **8 findings + §4 答复 + 3 风险全采纳**。折进执行规格如下：

**7.1 容差 sidecar 身份（MAJOR-1，进 Batch 1）**
- `score_vs_gt.json` sidecar 增 `tolerances: {wall_tol_m, window_centre_tol_m}`；`_load_valid_score_sidecar()`（run_stage.py:473）把 tolerances **纳入严格匹配**（stage/attempt/output_hash/source **+ tolerances** 全等才复用，否则重算）。
- `score_policy.py`（:93/:104）evidence criteria 文本现**硬写默认容差** → 改成传入的真容差。
- resume/重画用 `output_hash + tolerances` 跳过（避免每次重绘，风险1）。

**7.2 render_grade 只读 sidecar（MAJOR-2）**
- 签名 `render_grade_to_path(stage, score_sidecar, gt, out_path, ...)`：hit/miss/extra/漂移 **只读 sidecar 的 `scores`**（`read`/`delta`/`extra_*`），**渲染端绝不再 `_match_lines/_match_windows`**。
- gt 仅作**参考几何**（zone 填充/墙段 extent/立面 sill-head 底）——judge-side 读 gt 合法。参照原型（proto 已是 sidecar-driven）。

**7.3 F1 先落 + 真首-pass 测试（MAJOR-3，⑤→③）**
- Batch 1 先修 F1：packet 构建前持久化 accepted manifest，或把 in-memory manifest/accepted record 传入 `_grade_artifacts`（不 reload 磁盘旧态）。
- 新测试走 `cmd_flow()`/`run_one_stage()` 首次 accepted 后**立即**断言 packet 的 `score_vs_gt/grade/score_criteria` 非空（现 `test_judge_batch_b.py` 直调 `_judge_packet` 且 manifest 已在盘、覆盖不到此时序）。

**7.4 eyeball 收集 + accepted 升级（MAJOR-4，Batch 2）**
- accepted `<stage>/grade.png` promote 到段根 + `collect_eyeball_assets()`（report_assembly.py:100–155）显式收 `report/eyeball/{0_reading_grade,1_correction_grade}.png`。
- `_print_review_checkpoint()`（run_stage.py:703）从 `overlay.png` 改 `grade.png`。

**7.5 gt 隔离测试扩面（MAJOR-5，Batch 1 顺手）**
- `test_gt_discipline`（tests/test_gt_discipline.py:50/:57）扫描**递归扩到整个** `src/agent/execution/` + `src/agent/correction/`，保留 judge/tool-scripts 白名单。per-attempt score/render **只留** run_stage.py 的 judge path 或 `src/agent/judge/`，不下沉进 `StageRunner`/`step_orchestrator`/correction executor。

**7.6 baseline.models 结构化（MINOR-1，Batch 1）**
- `baseline.models` 改结构化 `{stage/role: {model_id, effort, source}}`（reading/correction/mep/default/orchestrator）；缺 `run_config.yaml` → `unknown`+warn（不 hard fail，§3 兼容）。

**7.7 立面无数据区分（MINOR-3，Batch 2）**
- 空 facade（如 `"W": []` 合法无窗）→ 画空立面；**仅** score floor 缺失/facade key 缺失/unmapped evidence → 画 `no data` 占位。

**7.8 §1.6 容差方向加锐（据 §4a）**
- 两把尺默认**相等**（0.30/0.40）；**若不等，方向只能 `reading_tol ≤ correction_tol`**（reading 更紧或相等，**绝不 reading 更松**——因 correction gt-盲、reading 放过的准确度错补救点后移无解）。**不要**默认 correction 更紧。

**7.9 displaced 连线（MINOR-2）**= 正式版不做，留 backlog（需 scorer 先出 `displaced_pairs` 再画，否则渲染端最近邻配对=第二套证据、破 §1.8）。

**7.10 配置形态（§4c 线程化路径）**
- 独立 `<run>/run_config.yaml`（非 llm.yaml 扩段）。容差线程：
  `run_config.yaml → RunConfig.grade_for(stage) → _judge_packet() → _grade_artifacts() → _score_attempt_output(wall_tol,win_tol) → score_floor()/score_correction_geometry() → reading_score_criteria(wall_tol,win_tol) → sidecar tolerances → render_grade_to_path(sidecar,gt)`。

**7.11 Batch 边界（据风险3）**
- **Batch 1** = ⑤(F1) + ②(结构化 models) + ①(run_config.yaml) + **7.1 sidecar 容差身份最小骨架** + 7.5 隔离测试扩面。
- **Batch 2** = ④(render_grade 全套视觉) + ③(per-attempt 全渲染 + accepted promote) + 7.4 eyeball + 7.7 立面占位。
