# 命名确定性化（提案）

Date: 2026-06-23
Branch: `6.15_ValidationArchM0toM4`
Status: 提案，待 Codex 审 → 用户裁决 → 派执行
前置侦察: [`2026-06-21_role_and_naming_recon.md`](2026-06-21_role_and_naming_recon.md)（插入点 / blast-radius 已盘点）
用户决策（2026-06-23，已 ratify）:
1. zone 命名 = `楼层_类型_方位` + **绝对序号（唯一 handle，前置）**；方位 = world 质心相对楼栋 footprint 中心的罗盘象限（居中记 `C`）。
2. **墙不用罗盘、改圈序号**：绕 footprint 一圈 1..N 依次编号（非矩形/切段 >4 也唯一、且向 C2/C3/C4 泛化）。zone 留罗盘象限、墙走圈序——两者口径不同各自最优。
3. 本轮范围 = **代码 + 测试同步，跑回全绿为止**；**golden 重录 + 合并 main 留到 sm21 批次重跑**（不在本轮）。

---

## 0. 问题 & 目标

**问题**：zone/cell id 现由 1_correction 的 LLM（DeepSeek）出，各 run 口径乱（`R_1F_Cor` vs `F1_corridor`）；surface/window 名虽代码派生但 base 串继承 LLM 不确定性 → golden 无法 byte 稳定、跨 run 不可比、"改哪个 zone" 说不清。

**目标**：zone/surface/window 名**全部代码确定性生成**，与 LLM 出的 `Cell.id` 解耦。

**不变量边界（不碰）**：5 条铁律、IntakeOutput 11 字段 schema、几何（verts/obc/配对拓扑/区数/窗数）。本提案**只动命名层**，不动几何。

---

## 1. 命名方案（终态）

```
zone:    Z01_F1_Office_SW     Z02_F1_Corridor_C     Z03_F2_Meeting_NE
         └绝对序号┘└楼层_类型_方位(质心象限,居中=C)┘
墙:      Z01_W1  Z01_W2  Z01_W3  Z01_W4 …   (绕 footprint CCW 一圈依次;切段/非矩形继续 W5…)
窗:      Z01_W1_Win1   Z01_W1_Win2          (父墙序号 + 窗在该墙上的次序)
水平面:  Z01_Floor   Z01_Ceiling   Z01_Roof   (切成多片 → Z01_Floor1 Z01_Floor2)
```

**口径细节**：
- 绝对序号 `Z01`：**两位零填充**（`Z01..Z99`，>99 自动扩位）；前置、是唯一 handle。绝对序号已唯一 → **取消** recon 里 per-bucket 尾号 `_1`（冗余）。
- `类型` = `Cell.role`（phase-1 room_labels 已就位），**Title-case**（`office`→`Office`）。
- `方位` = zone footprint 质心相对楼栋整体 footprint 中心的 8 向罗盘（`N/NE/E/SE/S/SW/W/NW`），落在中心容差带内记 `C`。
- **surface/window 名用短 handle `Z01`**（短、好说）；但 surface 的 **`zone` 引用字段仍是全名 `Z01_F1_Office_SW`**（EP `BuildingSurface:Detailed` 的 Zone Name 必须精确匹配 Zone 对象名）。`Z01` 前缀把面↔区串起来，grep 友好。
- 分隔符 `_`（连字符会被 `_safe()` 吃成 `_`、`4_mep/authoring.md` 也禁；"楼层-类型-方位" 是概念写法，落地下划线）。

**身份 vs 公开名（技术决定，安全形态）**：保留 LLM 的 `Cell.id` 作**内部源身份**（`Window.room` 引用、`cell_by_id`/`zv_by_cell` 查找全不动），**另起确定性 public `zone` 名**。不重写 `Cell.id`，避免 window 引用连锁断裂（recon §8 caution）。

---

## 2. 确定性锚点（实现细节，可调，请 Codex 核）

| 锚点 | 规则 |
|---|---|
| 绝对序号顺序 | 楼层 index 升序 → 质心 N→S（y 降）→ W→E（x 升）。**不依赖 LLM cell 顺序**（命门：correction cell 顺序非确定）。 |
| 方位象限 | 质心相对楼栋 footprint 包围盒中心；8 向 + 中心容差带 `C`（容差 = 包围盒半宽/半高的某比例，待定，建议 ~15%）。 |
| 墙圈序起点/方向 | 从 zone footprint **最西南角顶点**起、**CCW** 绕（顺现有 `_cell_polygon` CCW 法化，不额外翻转）；每面墙按**段中点沿边界环位置**排序得 1..N。 |
| 窗沿墙序 | 同一父墙多窗 → 按窗沿墙起点的距离升序。 |
| 水平面切片序 | Floor/Ceiling/Roof 切成多片 → 按片质心（y 降, x 升）。 |

---

## 3. 插入点 & 实现形态（基于当前码核实）

### 3.1 zone 名 — `build_zone_volumes()`（[modelling.py:274-352](../../../src/agent/geometry/modelling.py)）
现：`ZoneVolume(_safe(c.id), c.id, …)` 第一个字段=zone 名直接取 `_safe(c.id)`（L332）。
改：所有 `ZoneVolume` 建好后，**追加一趟确定性命名**——按 §2 顺序排序 → 派 `Z0n` 绝对序号 + 算质心象限 → 组 `Z0n_F{fi+1}_{Role}_{Dir}` 写回 `zv.zone`；`zv.cell_id` 保持 `c.id` 不变。
- 现有 id/zone-name 唯一性 guard（L289-308）：基于 `c.id`，保留（防 LLM 重复 id）；新公开名由代码生成、天然唯一。

### 3.2 surface 名 — `pair_surfaces()`（[split_pairing.py:38-139](../../../src/agent/geometry/split_pairing.py)）
现：`add()` 即时 `registry.uname(f"{zone}_{stype}")` 命名 + 内联 `sa.obc_obj, sb.obc_obj = sb.name, sa.name`（L42, L71, L109）。
**圈序要求"一个 zone 的墙全建完再命名" → 改两趟**：
1. **建面趟**：`add()` 只建 `Surface`、给**临时内部 id**，互逆配对用**对象引用**记（不再用名字内联设 obc_obj）。
2. **命名趟**：按 zone 分组 → 墙按 §2 CCW 边界位置排序派 `{handle}_W{k}`；Floor/Ceiling/Roof 按类型 + 切片序派 `{handle}_Floor[k]` 等。
3. **回填趟**：用记下的对象配对引用，把 `obc_obj` 解析到最终名。

> ⚠ **核心风险点**：互逆引用（interzone 墙 sa↔sb、跨层 floor↔ceiling fs↔cs）穿过 rename 不能错位。这是本提案 Codex 最该 adversarial 审的地方。几何（verts/obc/topology）一字不动，只把命名挪到确定性后处理。

### 3.3 window 名 — `attach_windows()`（[modelling.py:355-377](../../../src/agent/geometry/modelling.py)）
现：`Window(registry.uname(f"{zone}_Win"), parent.name, verts)`（L376）。
改：base 用**父墙最终名** + 沿墙窗序 → `{parent.name}_Win{k}`（如 `Z01_W1_Win1`）。`w.room → zv_by_cell[w.room].zone` 查找不变（靠 cell_id 身份）。

### 3.4 viewer / building_geometry.json — role 改直接序列化（[specs.py:23-45](../../../src/agent/geometry/specs.py)）
现：`building_geometry_dict` 的 `zones` = `list(dict.fromkeys(bg.zones))`（纯名字串）；viewer（[render_geometry_viewer.py:535-557](../../../scripts/tool_scripts/render_geometry_viewer.py)）靠读 sibling `correction_geometry.json` 按 `cell.id == zone 名` 反查 role —— **public 名 ≠ cell.id 后此反查失效**。
改：**additive** 加一个 `zone_meta` 键（不动 `zones`，降 blast-radius）：
```json
"zone_meta": [{"name": "Z01_F1_Office_SW", "role": "office", "cell_id": "<orig>", "fi": 0}]
```
viewer 改读 `zone_meta` 取 role（不再靠名字猜）。`zones` 串列表保持，validation_run byte-equal 两侧同函数自洽。

---

## 4. Blast radius & 同步清单（本轮全做）

1. **测试 ~30 文件 + 4 fixture** 写死精确名（recon §"Test And Fixture" 全表）：`test_geometry_kernel` / `test_kernel_guards` / `test_deterministic_core` / `test_intakeoutput_assembly` / `test_geometry_viewer` / `test_zone_agent` / `test_gt_from_dxf` / `test_gt_render` / `test_checks_*` / `test_interzone` / `test_pipeline_kernel_wiring` / `test_correction_stability` …——改成断言**新确定性名**或改成结构断言（计数/关系而非字面名，凡可）。
2. **下游节点 prompt prose**（[zone.py](../../../src/agent/nodes/zone.py) / surface / fenestration / people / lights）写的旧命名约定（`{floor}_{usage}_{direction}` / `{zone}_People` 等）→ 更新到新格式描述。**注**：节点是 verbatim 转写 zone_specs/surface_specs，不自己造名，所以是**文档对齐**非逻辑改。
3. **viewer**（§3.4）。
4. **golden byte-equal 测试**：`test_validation_run_baseline` / `test_orchestrate_baseline` 大多是**计数断言**（recon 标 :214-216/:94 count-only）——若不碰存档名应可过；若 fixture 内嵌精确名则同步。**真实 sm20/sm21 golden 存档不在本轮重录**（留 sm21 批次）。

**不需要改**：correction schema（`Cell.id/role` 仍 LLM 出）、IntakeOutput schema、几何内核算法、5 条铁律、gt（gt 用自己的 id 体系，judge 只判定性）。

---

## 5. 范围边界（本轮 vs 下轮）

- **本轮**：§3 代码 + §4 测试/prompt/viewer 同步 → **pytest 跑回全绿（当前 328）**。不重录真实 golden。
- **下轮（sm21 批次）**：用新命名跑 sm21_anchor（连同 reading-honest + judge 两轴 + auto re-read），重录 sm20/sm21 golden（byte-equal），结果 OK → 合并 main。

---

## 6. Review-Asks（请 Codex 重点裁决）

1. **§3.2 两趟 rename 的互逆完整性**：interzone 墙 / 跨层 floor-ceiling 的 `obc_obj` 解析有无错位风险？两趟切分（对象引用记配对 → 命名 → 回填）是否最稳形态，还是有更简的单趟方案？
2. **墙圈序确定性锚点**（§2）：最西南角起 + CCW + 段中点环位置排序——对**非矩形/切段**是否真唯一且稳定？退化情形（共线段、孤立 sliver 墙）会不会序号抖动？
3. **绝对序号顺序键**（楼层→N→S→W→E）：质心相同/近似的退化情形如何 tie-break 才确定？（建议加 cell_id 字典序兜底？）
4. **方位象限中心容差**：`C`（居中）的容差带比例定多少合理？会不会大量 zone 落进 `C` 导致方位段失去区分度？
5. **building_geometry.json `zone_meta` additive**：除 viewer 外还有谁读 `zones`？additive 加键会不会破坏任何现存 consumer 或 byte-equal 断言？
6. **blast-radius 有没有漏**：recon 表外，是否还有脚本/fixture/契约硬编码了旧名？
7. **窗名 `{parent.name}_Win{k}`**：父墙名内含 `Z01_W1`，窗名 `Z01_W1_Win1`——长度/可读性 OK？还是窗也该挂绝对序号？

---

## 7. v2 修订（依 Codex 审 `2026-06-23_deterministic_naming_review.md` 裁决，2026-06-23）

Codex 审 = REWORK（3 BLOCKER / 6 DISAGREE / 4 NIT）。逐条裁决：**全采纳**（B3 校准 scope）。下为对 §1–§6 的覆盖增量，执行以此为准。

### V2-A 规范顺序并进数据流（B1 — 最重要补强）
仅排序「命名」不够：`bg.zones` / `building_geometry.json["surfaces"]` / `geometry_specs.md` 仍保留 `zvs`/list 插入序（= LLM cell 序）→ 同名但不同字节序。改：
- `build_zone_volumes()` **返回按规范键排序的 `zvs`**：`(floor_rank_by_z, round(-cy), round(cx), bounds, area, canonical_ring_hash, _safe(cell_id) 末位)`。绝对序号 `Z0n` 在此序上派。
- `pair_surfaces()` 按规范 zone 序迭代；zone 内墙按环序、水平面按切片序。
- 序列化（`building_geometry_dict` / `serialize_geometry` / `geometry_specs_markdown`，[specs.py:152-161](../../../src/agent/geometry/specs.py)）：zones 按规范 `zvs` 序，surfaces 按 `(zone 规范 index, surface 确定性键)`，windows 按 `(parent, k)`。**只改产物顺序，verts/obc/topology/计数不动。**

### V2-B 删 obsolete 公开名撞名 guard（B2）
[modelling.py:302-308](../../../src/agent/geometry/modelling.py) 的 `_safe(c.id)` 撞名 raise 在公开名改代码生成后已 obsolete（再耦合 LLM 拼写）。**删它**；**保留** raw `c.id` 全局唯一性 guard（`Window.room`/`zv_by_cell`/`cell_by_id` 需源身份）。加回归：两个 raw id 不同但 `_safe` 后相同、window.room 合法 → 应正常 build。

### V2-C B3 = xfail（本轮 scope，用户 2026-06-23 定）
sm20/sm21 正基线测试走 `validate_case` 精确重建（[validation_run.py:155-180](../../../src/agent/execution/validation_run.py)），且 golden 的 `4_mep`/`5_intakeoutput` 也写死旧名（4_mep 是 LLM 阶段）→「纯机械重录几何」不够。**本轮**：golden run 目录**原封不动**，对那几个走精确重建的 baseline 测试打 `@pytest.mark.xfail(reason="deterministic-naming golden re-record pending sm21 batch")`；只更新 inline-fixture 单测到新名。**全量 golden 重录（几何 + MEP 走真管线）留 sm21 批次**，届时撤 xfail。净 pytest = 全绿 + N 个 tracked xfail（非假绿）。

### V2-D 配对实现约束（D1）
`Surface` 是可变 dataclass（不可 hash 当 dict key）。`add()` 建面时 `pair_refs.append((sa, sb))`（对象引用）；命名在**原对象原地**改；最后 `for a,b in pair_refs: a.obc_obj=b.name; b.obc_obj=a.name`。**禁**按最终名/几何相等/质心/list 下标 rematch。加测试：多个等面积跨层切片 + 同 zone 多段切墙，证互逆穿过排序不错。

### V2-E 墙环序规范键（D2）
新 `_canonical_ring(poly)`：确保 CCW + 旋转到圆整 `min(y,x)` 顶点。每墙段键 = `(段中点沿环位置, round 端点 a, round 端点 b, 长度, obc_rank, 配对 handle/空)`；圆整后仍真 tie → **报错**（不让 Shapely 迭代序决定 `W{k}`）。

### V2-F 绝对序号几何指纹兜底（D3）
tie-break 用量化几何指纹（bounds/area/规范环 hash）**先于** cell_id；cell_id 仅「不可能 tie」末位兜底；同层两 zone 同指纹 → raise（多半重叠/重复几何）。

### V2-G `C` 容差收窄（D4）
归一近原点小带：`abs(dx)/half_w ≤ 0.05 且 abs(dy)/half_h ≤ 0.05` + 小绝对容差（吸 snap 噪声）+ 米级上限。加测试：居中走廊 / 略偏心房 / 大 footprint 核心房。

### V2-H discover_roles 先读 zone_meta（D5）
所有 viewer 调用点都显式传 `roles=discover_roles(...)`（[render_geometry_viewer.py:593-600](../../../scripts/tool_scripts/render_geometry_viewer.py)、run_stage、report_assembly）→ 仅「roles is None 才读 zone_meta」无效。改：`discover_roles(bg)` **先读 `building_geometry.json` 的 `zone_meta`** 返回 `{name: role}`，无则回退旧法。更新 `test_geometry_viewer` 覆盖 `cell_id != name`。

### V2-I role-token 归一器（D6）
现存 role 有多词（`entrance lobby`/`meeting room`）。`.title()` 会留空格→非法。helper：strip → 词首大写 → `_safe` → 折叠重复 `_` → 去首尾 `_` → 空则回退 `Office`/`Unknown`（如 `meeting room`→`Meeting_Room`）。加测试（多词/标点/空/非 ASCII）。

### V2-J 其余（N1-N4）
- **N1**：窗按父墙分组，按 `(沿墙起点, end, z_min, z_max, w.id 末位)` 排序派 `Win{k}`，序列化按 `(parent,k)`。
- **N2**：`zone_meta` 放 `building_geometry_dict` 的 `zones` 之后、由规范 `zone_volumes` 序生成；加 byte/render 测试。
- **N3**：blast 清单加 `report_assembly`（viewer 重生成）/ viewer CLI help / `zone_tools` docstring 示例。**MCP `src/mcp/api/core.py` 的 `{zone}_Wall_{i}` 等保持不变**（独立通用 CRUD API，CLAUDE.md §3 out-of-scope + §11 idfpy 搁置）——仅注记，不在本轮对齐。
- **N4**：`ZoneVolume` 加 `handle: str = ""` 字段（确定性命名趟回填），surface/window 名取 handle，不靠从 `zv.zone` 拆 `Z01`。

### V2 净范围
代码（modelling/split_pairing/specs/build + viewer discover_roles）+ inline-fixture 单测改新名 + 新增回归（D1/B2/D4/D6/N2/D5）+ 节点 prose/docstring 对齐 + 那几个 golden 重建测试 xfail。**pytest 目标 = 全绿 + tracked xfail**。golden 物理重录、MEP/intake、合并 main **不在本轮**。

### V2.1 二审 residual（Codex 二审 APPROVE-WITH-CHANGES / 0 BLOCKER，采纳）
1. **单一量化精度常量**：序号几何指纹（V2-F）、环起点选择 + 墙段键（V2-E）、质心量化（V2-A）全部复用**同一个** `_NAME_QUANT`（建议绑现有 kernel 坐标容差，定义一处）；**量化后**再对墙段端点对做规范排序（`(a,b)` 与 `(b,a)` 归一），避免方向歧义。
2. **strict xfail**：那几个 golden 重建测试用 `@pytest.mark.xfail(strict=True, reason="deterministic-naming golden re-record pending sm21 batch")`——sm21 批次重录后若意外 XPASS 会报错，强制提醒撤 xfail。

**精确 xfail 清单（Codex grep 实测，执行器照此打、不要误打 inline-fixture 测试）**：
- `tests/test_validation_run_baseline.py::test_sm20_anchor_positive_baseline`
- `tests/test_validation_run_baseline.py::test_sm20_anchor_reports_writable`
- `tests/test_validation_run_baseline.py::test_geometry_digest_computed`
- `tests/test_validation_run_baseline.py::test_confirmation_required_blocks_until_approved`
- `tests/test_validation_run_baseline.py::test_optional_policy_never_blocks_on_approval`
- `tests/test_validation_run_baseline.py::test_require_ep_passes_on_clean_run`
- `tests/test_validation_run_baseline.py::test_run_with_clean_ep_validates`
- `tests/test_validation_run_baseline.py::test_sm21_anchor_positive_baseline`
- `tests/test_orchestrate_baseline.py::test_record_baseline_on_anchor`
