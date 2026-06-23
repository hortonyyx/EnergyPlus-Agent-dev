# 外包优先：立面外包尺寸权威 + 确定性吸收（提案）

Date: 2026-06-23
Branch: `6.15_ValidationArchM0toM4`
Status: 提案，待 Codex 审 → 用户裁决 → 派执行（目标：sm21 批次重跑前落地）
用户决策（2026-06-23，已 ratify）:
1. **优先级 立面外包 > 平面外包**（本轮做这层；终极序 `轴线 > 立面 > 平面` 留后续细化）；**窗也优先立面**（同一修法副产品）。
2. 范围 = **先外包**，通用尺寸链 / 轴线优先 / reading role 填全 → 记 backlog。
3. 吸收容差 = **0.3m，进 `correction.yaml` 配置 + 注释说明**。

---

## 0. 诊断（坐实，三次 run + 数据取证）

gt（DXF 直出、人工核过）footprint = **15×8 外包**，zone 精确平铺 0–15 / 0–8、零墙厚。
三次 sm21 run 实际 footprint 全 ~**14.76×7.76**（每边内缩 0.12 = **半墙厚**，即 zone 建在**墙体中线/轴线**），系统性差 ~0.24m，跟 N2「-0.24m 窗 x 漂移」同根。

层层定位：
- **外包信号"在、但没结构化"**：reading 立面维度里有 `D1: text="15000" from=[0,6.6] to=[15,6.6] axis=x note="overall total width of south facade"`——外包 15 captot 了（from→to 跨 0→15）。但它在 **legacy 维度格式**（`text`/`from`/`to`/`note`），不是 P1a（`value_m`/`role`）；**`role=overall` 全 run 没人填**（基建休眠）。
- **1_correction LLM** 没稳定认这条 → 出 14.76 中线。
- **确定性核看不到 reading 维度**（只拿 `CorrectedGeometry`：footprint + cells + windows）→ 无外包权威可优先。
- **facade plane = footprint 派生**（[facade.py](../../../src/agent/correction/facade.py)：South 墙 = `y=footprint_y_min`、窗 along_origin 取 footprint 极值）→ footprint 内缩 0.12，窗世界坐标跟着 +0.12 漂、和 gt 外包基准差 0.12。**修 footprint→外包，窗自动跟正**（= 用户「窗优先立面」）。

**结论**：不是 reading 没采到、不是核算错——是**外包没作为权威喂进确定性核**。

---

## 1. 修法（确定性，立面外包权威 + 误差吸收）

> **从 reading 立面维度确定性抽外包 extent → 喂进核 → 核把 footprint 吸到外包（≤0.3m）→ 窗自动跟。**

四步：

### 1.1 抽外包 extent（pipeline，确定性、不靠 role 已填）
新 helper（pipeline 侧，能访问 reading `vector_dir`）：
- 对每个**立面**视图（North/South → world x；East/West → world y），遍历 `dimensions`，每条算轴向跨度 `span = |to[axis]−from[axis]|`（`value_m` 缺则用 from/to；再缺 fallback 解析 `text` mm→m）。
- `outer_x = max span`（N∪S 视图，axis=x）；`outer_y = max span`（E∪W 视图，axis=y）。
- **只看立面视图，不看平面视图**（落实 facade > plan）。
- 顺带可把命中的那条 `role` 标 `overall`（**激活休眠基建**）——本轮**可选**，role 全量填属 backlog③。

### 1.2 喂进核
`apply_deterministic_core(geom, tol, *, authoritative_envelope=None)` 加可选入参 `authoritative_envelope = {"x": outer_x, "y": outer_y}`（结构化数字，**不破 image-blind**：核不碰图、只多收两个权威跨度）。pipeline 调用点传入；缺省 None 时行为不变（向后兼容）。

### 1.3 核吸收（envelope reconcile，新增于 footprint snap 之后）
对每轴：令 `cur_span = footprint[hi]−footprint[lo]`：
- `|cur_span − outer| ≤ envelope_reconcile_tol_m(0.3)` → **吸收**：把 footprint 该轴**按 SW 内角锚定**（CLAUDE.md 不变量#2：原点=整栋 SW 内角）扩到 `outer`，即 `footprint[hi] = footprint[lo] + outer`；audit 记 `deterministic_core.envelope_reconcile`。随后现有 `_close_to_boundary`（gap-close）把贴近新边界的 cell 外边拉到外包（gap_close_threshold 需覆盖半墙厚 ~0.12–0.15，见 §3）。
- `> 0.3` → **不静默强压**，记 `unsupported`（半墙厚该吸、错半栋楼该报，交 judge/人）。
- `authoritative_envelope=None`（无 reading 维度，如纯 codex-CLI run）→ 跳过，行为同今。

### 1.4 窗自动跟
不需单独改：facade plane/along_origin 由 footprint 派生，footprint 一正窗世界坐标即对齐外包基准。

---

## 2. 容差配置（用户定 0.3 + 注释）
[correction.yaml](../../../src/configs/correction.yaml) 加：
```yaml
  envelope_reconcile_tol_m: 0.30
  # 立面外包 vs 平面 footprint 的"墙厚量级"差吸收上限。
  # 背景：立面尺寸到外墙(外包)、平面常到轴线/中线 → 同栋楼两套基准差约一个墙厚。
  # 作用：|平面 footprint 跨度 − 立面外包跨度| ≤ 此值 → 判为墙厚量级误差，
  #       footprint 吸到立面外包(按 SW 内角锚定)、窗随之对齐；超过 → 不静默强压、记 unsupported。
  # 0.30 = 容一个偏厚外墙(~0.24)+余量；调小→偏厚墙吸不动，调大→可能吞真实小尺寸差。
```
同步 `CoreTolerances` dataclass 加字段 + `load_core_tolerances` 读取（[deterministic.py](../../../src/agent/correction/deterministic.py)）。

---

## 3. 插入点（基于当前码核实）
- **抽外包 helper** + 调用：[pipeline.py](../../../src/agent/pipeline.py)（`run_correction` 产 geom 后、`apply_deterministic_core` 前；reading `vector_dir` 在 pipeline 可达，`discover_vector_files` 已读它）。
- **核入参 + 吸收步**：[deterministic.py:505 `apply_deterministic_core`](../../../src/agent/correction/deterministic.py)，footprint snap（L551-553）之后插 envelope reconcile；`gap_close_threshold_m` 现值需核（若 < 0.12 则外边拉不到，需调或在 reconcile 内直接吸外边 cell）。
- **配置**：correction.yaml + `CoreTolerances` + `load_core_tolerances`。
- **不动**：facade.py（窗自动跟）、几何内核、IntakeOutput 契约、gt。

---

## 4. 范围边界
- **本轮**：外包 extent 抽取 + 核 envelope reconcile + 0.3 配置 + 窗自动跟 + 正反单测（吸收/超容差 flag/无 reading 维度跳过/窗对齐）。
- **Backlog（记录、不做）**：① 通用尺寸链 `overall > segment` 内分（Σ段≠overall 时往内分配）；② 终极优先序 `轴线 > 立面 > 平面`（轴线最高，需平面/立面共轴系判定）；③ reading dimension `role` 全量填（legacy→P1a 迁移，让 overall/segment 结构化）。

---

## 5. Review-Asks（请 Codex 重点裁决）
1. **外包识别稳健性（机制命门）**：`max(to−from) over 立面视图` 够不够确定性识别"那条=外包"？退化情形——某立面有跨度更大的杂维度（如标注链总和、跨多构件的参考线）会不会误判？容差门（仅 ≤0.3 才吸）能否兜住误判（杂维度 30m 不会落进 14.76±0.3 → 自然忽略/flag）？需不需要再加"note 含 overall/总宽"关键词或"跨度≈footprint 跨度"双证据？
2. **N/S 两立面给同一 outer_x 但不一致怎么办**：取 max？取与 footprint 更近者？还是不一致即 flag？E/W 给 outer_y 同理。
3. **SW 内角锚定**：吸收时固定 `footprint[lo]`、扩 `footprint[hi]`——若 reading 外包的 0 点与 footprint 的 lo 不在同一角怎么处理？是否该同时校 lo？
4. **gap_close 联动**：footprint 扩到外包后，cell 外边靠 `_close_to_boundary` 拉过去——现 `gap_close_threshold_m` 值够覆盖半墙厚吗？还是 envelope reconcile 步里直接把"原贴 footprint 旧边的 cell 外边"一并平移到新边更稳（避免依赖另一个容差）？
5. **image-blind 边界**：在 pipeline 做确定性 max-span 抽取（非 LLM）+ 传数字给核——是否仍守"核 image-blind"纪律？有无更该放在 1_correction 的理由？
6. **窗自动跟验证**：footprint 改了，attach_windows / facade frame 是否真的全程用最新 footprint（无某处缓存旧值）？

---

## 6. v2 修订（依 Codex 审 `2026-06-23_envelope_facade_priority_review.md` 裁决，2026-06-23）

Codex 审 = REWORK（4 BLOCKER / 4 DISAGREE / 3 NIT），**全采纳**（同方向工程加固，方向/范围/0.3 容差不变）。执行以下为准，覆盖 §1–§5。

### V2-A 抽取改「评分候选 + 权威 bounds + 单位安全」（B1+B2+B3+D1）
不再用裸 `max span`。新结构 `EnvelopeCandidate(axis, bounds, span, source_kind, view, source_id, role, note, confidence)`：
- **来源（两类，互为佐证/兜底）**：① 立面**维度** from/to（**世界坐标 bounds**，如 sonnet South `D1 from=[0,6.6] to=[15,6.6]`→x bounds `[0,15]`）；② 立面**描边** outline/wall_fill 的轴向 extent（如 gpt54 South outline `[0,15]`、East/West `[0,8]`——**覆盖无 dimensions[] 的 run**）。
- **单位安全**：优先 from/to bounds/span（世界米）；`value_m` 仅当与 from/to 一致才采（legacy.py 解析 `text="15000"` 不转 mm→m，会得 15000，**禁 value_m-first**）；text fallback 必推单位（`15000`→15.0）。
- **authority 评分排序**：`note 含 overall|total|总` 或 `role=overall` > outline/wall_fill 包络 extent > 裸 max-span > text-only fallback。
- **要求第二证据**才 reconcile：显式 overall/total note、或描边包络一致、或同轴对面立面（N↔S / E↔W）一致。
- **分歧处理**：同轴高 authority 候选（N vs S）差 > 小容差 → `conflict`/skip 该轴，**不静默取 max**。
- 解析成 `AuthoritativeEnvelope`（每轴：接受的 bounds + 候选 + skip 原因）。

### V2-B 传权威 bounds（非 span），核设 lo+hi（B1）
`apply_deterministic_core(geom, tol, *, authoritative_envelope: AuthoritativeEnvelope | None = None)`。
- 有 bounds（如 `[0,15]`）→ **lo、hi 都设**（落实 SW 内角=整栋 origin 不变量，sm21 `[0.12,14.88]` 应→`[0,15]` 而非 fixed-lo 的 `[0.12,15.12]`）。
- 仅 span 无独立 origin → **不静默锚**，记 origin-ambiguity `unsupported`。
- `None`（无 reading 信号）→ 跳过、行为同今（向后兼容）。

### V2-C 直接挪 cell 外边 + 窗，不靠 gap_close（B4+D2，**内核从 cell 造区**）
内核 `build_zone_volumes` 从 **cells** 造区、不从 footprint（review §topology）→ 只改 footprint 不够。reconcile 步：
- 记旧 footprint bounds；把**落在旧外边界上/附近的 cell 外边**直接移到新权威边界（origin 移则该轴全体一致平移 + 外边扩到 hi）；**窗 along/坐标随父外墙一致移**（窗跟=因父 cell 外墙移了，非 facade.py）。
- 独立 audit 规则 `deterministic_core.envelope_reconcile`（非 gap_close）。
- **不依赖** `gap_close_threshold_m`（现 0.3 凑巧够、调低会静默穿洞）。
- reconcile 后跑 `validate_corrected_geometry()` 证无洞/无重叠（coverage 硬不变量）。

### V2-D 抽取 helper 共享 + 不改 reading role（D3）
- 抽取放 reading/correction **共享 util**，`pipeline.py`（mutation）与 `validator/checks/correction.py`（已有 `elevation_widths` 入参）同调一份，不双实现。
- 核只收结构化 `AuthoritativeEnvelope`/None，**raw reading JSON 解析不进 deterministic.py**（守 image-blind）。
- **本轮不就地改 `0_reading` 的 `dimensions[].role`**（role 推断写进 correction audit/candidate metadata；全量 role 填属 backlog③）。

### V2-E 结构化 audit / unsupported（D4）
- 每**接受**轴：`corrections[]` 记 source view、dim/stroke id、原 footprint bounds/span、resolved bounds/span、tolerance name/value、candidate class（A0 §authority 变更须带 provenance）。
- 每**拒绝**轴：`unsupported`/`conflict` 带所有近候选 + 原因（超容差 / 跨立面分歧 / 缺 origin / 单位歧义）。

### V2-F 配置 + A0 词表 + 测试（N1+N2+N3）
- `envelope_reconcile_tol_m: 0.30` 进 correction.yaml（注释见 §2）+ `CoreTolerances`（[config.py](../../../src/agent/correction/config.py)）+ loader + config 校验；A0 加命名 `ENVELOPE_RECONCILE_TOL`。
- 测试（不靠现 golden xfail）：**抽取**（sm21 South/North/East/West JSON 精确 fixture，含 gpt54 无 dimensions[] 走描边、含 D1 单位回归 15.0≠15000）；**核**（接受 `[0.12,14.88]`→`[0,15]` / 超容差拒 / 无信号 no-op / origin 歧义 / 直接挪 cell 边 / **reconcile 后窗挂到新外墙**）；reconcile 后 `validate_corrected_geometry` 无洞。

### V2 净范围（不变）
本轮=抽取 util + 核 envelope reconcile（bounds/直接挪 cell+窗/audit）+ 0.3 配置 + A0 词表 + 上述测试。**Backlog 不动**：通用尺寸链 overall>segment 内分 / 轴线>立面>平面 / reading role 全量填。

---

## 7. v2.1 修订（二审 REWORK 2 BLOCKER，采纳；覆盖 V2-C）

二审指出 V2-C 的坐标运动规则仍危险。修正：

### V2.1-A 改 attachment-based 挪边，**禁全轴平移、窗 along 默认不动**（二审 B1）
- 反例：`[0.12,14.88]→[0,15]` 若「全轴平移 -0.12」，内隔墙 `5.0/10.0` 会变 `4.88/9.88`——**反造漂移**。
- 正解：**只挪「在 `boundary_attach_tol` 内贴旧 lo/hi 外边界」的 cell 边**到新权威 bounds（lo 贴边→新 lo，hi 贴边→新 hi）；**内部隔墙轴一律不动**（除非有独立证据整帧平移，单列、需 audit）。
- 例：`[0.12,14.88]→[0,15]`：贴 0.12 的 cell 外边→0、贴 14.88 的→15，外圈 cell 各加宽半墙；`5.0/10.0` 内隔墙原样。
- **窗 along-facade span 默认不平移**——窗"跟"是因父外墙 cell 边移了、墙面重建（[modelling.py attach_windows 用父墙面](../../../src/agent/geometry/modelling.py)）；仅当整帧平移被显式接受+audit 才动窗 span。

### V2.1-B pre-move 碰撞/坍缩门（二审 B2）
- 挪边**前**算每个受影响 perimeter cell 的新跨度。
- 若新边界会：越过最近内部轴 / 翻转 cell / 使任一受影响 cell 跨度 < `tol.min_edge_length_m`（**用核的 0.10、非 validator 的 _MIN_EXTENT=0.05**）→ **skip 该轴** + `unsupported`/`conflict`（带候选 + offending cell id）。
- `validate_corrected_geometry()` 留作 reconcile 后**兜底断言**，不是主碰撞策略。

### V2.1-C 单立面轴的第二证据规则（写死，二审 D1）
- 某轴只有一个立面（如只见 South、无 North）：dimension 候选**仅当**有 `role=overall` / note 含 `overall|total|总` 的权威信号 **且** 过 footprint 容差门 → 可 reconcile；
- 否则需**同视图 outline/wall_fill 一致**佐证；再否则 skip（insufficient evidence、不 reconcile）。
