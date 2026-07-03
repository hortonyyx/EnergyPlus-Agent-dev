# 边界判定入 scorer + 批卷上判定色 · 方案（2026-07-03）

> 承接流程清理批次。当前 grade 批卷里外边界/立面外框是**中性灰未判参考**，因 scorer 只判内墙+窗、不判边界。
> 用户定：**把边界判定也做了**，让批卷图全部元素都判定色支撑（准确反映）。
> 走协作规约：Claude 出此方案 → Codex 审+执行 → Claude 复核。

## 1. 现状（已核）
- `reading_score.py`：`derive_gt_walls`/`extract_reading_walls` 用 `_BOUNDARY_EPS_M < x < W-eps` **故意排除 footprint 边界**，只判内墙 + 窗（四立面）。
- `correction_score.py`：同构，只判内墙 + 窗。
- `score_vs_gt.json` 因此**无边界 hit/miss 字段** → `render_grade.py` 拿不到边界判定 → 画中性灰。
- footprint W/D **另有校验**（envelope.py + gate①），但结论不在批卷 sidecar 里。

## 2. 要做什么
给 reading + correction 两个 scorer 各加**边界（footprint 四边）判定**，写进 `score_vs_gt.json`，`render_grade.py` 据此给边界/立面外框上绿/红。

### 2.1 语义（per-floor，与内墙对称）
- gt 四边固定坐标：**S: y=0 · N: y=D · W: x=0 · E: x=W**（footprint 建筑级共享，但**逐 floor 判**——每层识图各自描了没描对该层外框）。
- 产物边界线提取（**新增，不动现有内墙提取**）：
  - reading：从 wall 描边里取**贴边**那些（竖 x 距 0 或 W ≤ `_BOUNDARY_EPS_M` → W/E 候选；横 y 距 0 或 D ≤ eps → S/N 候选），每边取最贴近的一条。
  - correction：从 `footprint_x`/`footprint_y`（correction 输出已有该字段）或 cells 外包 bbox 取四边。
- 每边判定：产物该边坐标在 gt 边 ±`wall_tol` 内 = **hit**（记 delta=read−truth）；无 = **miss**；（多余边界线罕见，可选记 extra）。
- 复用现成 `_match_lines` 思路（单坐标匹配），别新造匹配算法。

### 2.2 输出（`FloorScore` + sidecar）
- `FloorScore` 加 `boundary: dict[str, LineMatch]`（键 N/S/E/W）。
- `_floor_score_dict`（run_stage.py）把 boundary 序列化进 `score_vs_gt.json.scores[floor].boundary`。
- **容差**：用同一把判卷尺（reading/correction 各自的 `grade.wall_tol_m`）；边界属"墙类"、走 wall_tol。

### 2.3 render_grade 上色
- plan 四边 + 立面 envelope 外框：**有 boundary 判定就上绿(hit)/红虚(miss)**；**sidecar 无 boundary 字段（老 run/no-data）→ 退回中性灰参考**（保持向后兼容 + §7.7 no-data 语义）。
- 立面**楼板线**（floor slab）：gt/scorer 无楼板线判定字段 → **仍中性灰参考**（不在本次范围；backlog）。
- 图例：边界既可能绿/红（判定）也可能灰（无判定数据）——文案说明"边界：有判定则上色，无判定数据时灰"。

### 2.4 sidecar schema 版本位（顺带健壮性，关键）
- **问题**：加 `boundary` 后，老 `score_vs_gt.json`（无此字段）会因 stage/attempt/hash/source/tolerances 全等被 `_load_valid_score_sidecar` **复用** → 边界字段永远填不上、重渲也不变色。
- **修**：sidecar 加 `scorer_schema`（如 `"2"`）字段，`_load_valid_score_sidecar` 严格匹配纳入它；本次 bump → 老 sidecar 不匹配即**自动重算**、补上 boundary。（延续 §7.1 sidecar 身份原则。）

## 3. 铁律
- gt 隔离：改动全在 `src/agent/judge/`（scorer）+ `scripts/tool_scripts/{run_stage,render_grade}.py`（judge path）；不下沉 execution/correction/pipeline；`test_gt_discipline` 必绿。
- 契约不动（reading/correction/IntakeOutput schema 均不改，只加 scorer 内部/ sidecar 字段）；不重录 golden；向后兼容（老 sidecar 无 boundary → 灰 + 自动重算补上）。
- render 仍 **sidecar-driven**：边界颜色只读 sidecar 的 boundary 判定，renderer 不自己算边界对错。

## 4. 测试
- reading/correction scorer 边界判定单测（hit/miss/delta，含贴边提取）。
- sidecar 含 boundary + `scorer_schema` 断言；老 schema 触发重算断言。
- render_grade：boundary=hit→绿、miss→红虚、无字段→灰 各一 fixture。
- 全量 pytest 保持绿（现 427 + 新增）；`test_gt_discipline` 绿。

## 5. 审阅需求（Codex 掂量）
- a｜reading 边界提取：贴边 wall 描边法够稳吗？有没有 reading 不描外框只给窗/footprint 的情况→那时该 miss 还是 no-data？倾向：有内墙/窗但四边无贴边描边=**miss**（真漏了外墙）；整层空=no-data 灰。
- b｜correction 边界源：`footprint_x/footprint_y` vs cells 外包 bbox，哪个权威？（倾向 footprint_x/y 显式字段优先，缺则 bbox 兜底。）
- c｜`scorer_schema` 版本位放 sidecar 顶层字段 ok？bump 策略（常量 `SCORER_SCHEMA="2"`）。
- d｜边界要不要进 score_criteria（judge advisory 文本）？倾向：加一条 boundary 命中数、与 wall 分开，advisory-only。
- e｜楼板线暂不判（保持灰）是否认同？（gt 无独立楼板线元素、竖向判是更大 backlog。）
