# 执行日志 · F-13 正式修法：内核产出「左上角起笔、逆时针」的规范顶点顺序

- **派工单**：[`request/2026-08-06_f13_kernel_canonical_vertex_order_dispatch_claude.md`](../request/2026-08-06_f13_kernel_canonical_vertex_order_dispatch_claude.md)
- **席位**：Claude 侧 Sonnet 子代理（施工档）· **主工作树** · 开工 HEAD = `709bc8f`
- **⚠️ 本单不是纯净完成**：§1–§4 全部按单交付；§5 真链路验收撞到一处**派工单前提与事实不符**（见 §5.0），
  已如实改用等价的真实代码路径完成验收，未改动线上产物、未越权改动 `case_tests/`。

---

## 0. 开工自检

```
git log --oneline -1     # 709bc8f — 符合预期
git status --short       # case_tests/ 下 4 个未跟踪目录属已知，未碰
pwd                      # /workspaces/EnergyPlus-Agent-dev
```

前一版 F-13（校验器停止挪起笔点）已确认在主工作树上**原样未改**（`_sort_vertices_clockwise` /
`_get_top_left_corner_from_normal` 逻辑与 07-02 老件跑通版本一致）——无需回滚。

---

## 1. 规范化提取到哪、内核在哪调

### 1.1 提取位置：`src/validator/data_model.py`（新增两个模块级纯函数，紧贴 `class GeometrySchema` 之前）

- `canonicalize_ring_vertices(points: np.ndarray, normal_vector: np.ndarray) -> np.ndarray`
  —— **逐字节**从原 `GeometrySchema._sort_vertices_clockwise` 方法体搬出（cross-product 质心角度排序
  + 调用 `top_left_corner_index` 挪起笔点），**未改一行算法**。
- `top_left_corner_index(points: np.ndarray, normal_vector: np.ndarray) -> int`
  —— 逐字节从原 `GeometrySchema._get_top_left_corner_from_normal` 方法体搬出。

`GeometrySchema._sort_vertices_clockwise` / `._get_top_left_corner_from_normal` 两个实例方法**改为一行委托**
（`return canonicalize_ring_vertices(surface.vertices, normal_vector)` /
`return top_left_corner_index(points, normal_vector)`），**外部调用方式与行为完全不变**
（`validate_points_sorting` 的调用点、参数、返回值语义均未动）。

⇒ 满足派工单「三件事都要复用」：① 保绕向朝外 ② 乱序点排质心角度排环 ③ 挪起笔点到左上角
—— 三件事在 `_sort_vertices_clockwise` 里本就是**同一次排序**完成的（`compare_points` 用传入的
`normal_vector` 做叉积符号判断，天然决定了绕向；排序完再挪起笔点），**不是分三步、无法只挪用一步**，
搬出来是同一个不可分函数，天然满足「三件都复用」。

### 1.2 内核落点：`src/agent/geometry/build.py::build_geometry`（新增 `_canonicalize_bg_vertices(out)`，
`return out` 之前调用一次）

**为什么选这一点，不是逐个 `_wall_verts`/`_ring_verts`/窗口函数处**：
`bg.surfaces[*].verts` 是 `serialize_geometry`（`specs.py`）与 `build_output_coordinate_snapshot`
（`output_coordinates.py:697`）**唯一的公共读取点**——在 `build_geometry` 定稿处规范化一次，
两个下游自动一致，且只有一个改动点（不是散落在 `split_pairing.py` 十几个 `add(...)` 调用点、
`modelling.py` 四个 verts 构造函数里各插一次）。

**内核不需要复刻校验器的「从 Floor Delaunay 推 interior points」**（这正是派工单担心的
「结构上做不到」的那个风险点，**已核实不成立，见下**）：`build_geometry` 跑到 `return out` 之前，
`pair_surfaces`/`attach_windows*` 已经把每个面的顶点**用内核自己一套独立、更直接的几何方法**
定向到朝外（墙用 `owner_poly.covers()` 包含性测试 `_local_outward_normal`；地板/天花/屋顶用固定 `±Z`；
窗用父墙自身法向或显式校验过的 `outward_normal_xy`）——这套逻辑（`_orient`/`_newell`，`modelling.py`）
**F-13 完全没有改动**。既然顶点此刻已经绕向正确，**该顶点集合自己的 Newell 法向（`_newell(verts)`）
就是喂给共享规范化函数的正确 `normal_vector`**——不需要独立重算，也不会翻转已经正确的绕向
（详见 §1.3 的自洽性论证）；退化面（近零面积，`norm(normal) < 1e-9`）原样放过，不猜。

### 1.3 为什么"自参照法向"是安全的（不是又发明一套近似算法）

`canonicalize_ring_vertices(points, normal_vector)` 内部排序完全由 `normal_vector` 决定绕向
（"叉积·法向"符号判断），与输入点原始顺序无关（该性质已被 F-13 调查单 §3.2/§3.3 用真实 sm21 数据
双路径实测坐实：`sort(P)` 与 `sort(reversed(P))` 逐字节相同）。⇒ **只要喂进去的 `normal_vector`
方向正确，排序结果就正确**，与这个法向是"独立测出来的"还是"从已知正确的顶点自己算出来的"无关。
内核顶点此刻的绕向已经正确（`_orient` 保证），所以 `_newell(顶点)` 与"正确的朝外法向"**同号**——
用它自参照，排序只会把"已经正确定向的环"重排成规范环 + 挪起笔点，**不可能引入新的绕向错误**。

---

## 2. 三条锁各断言什么

新文件 `tests/test_f13_kernel_canonical_vertex_order.py`（8 个测试，见 §4 全绿记录）：

1. **`test_lock1_kernel_output_is_already_canonical_through_real_entry_points`**
   —— 走**真实生产入口** `SurfaceConverter.validate()` / `FenestrationConverter.validate()`
   （与 `SurfaceConverter.convert()`/`FenestrationConverter.convert()` 同构的按 zone 分组、
   surfaces 先于 fenestrations 的调用顺序），断言**每个具体面/窗（按 name 逐个比较）**
   验证前后顶点数组 `np.array_equal`，且 §2.3 改动计数 `== 0`、改动日志 `== []`。
   ⛔ 不是「长度没变」，是逐顶点值断言。
2. **`test_lock2_canonicalization_{vertical_wall,floor,ceiling,window}_top_left_and_outward`**
   （4 个）—— 对已知形状（南墙/地板/天花/窗）喂乱序顶点，断言规范化后
   `canonical[0]` **具体等于**手算的左上角顶点值（如南墙 `(1.0, 0.0, 2.0)`）、
   `top_left_corner_index(canonical, normal) == 0`、`Newell(canonical)·normal > 0.99`（朝外）。
3. **`test_lock3_change_counter_fires_and_repairs_noncanonical_input`** +
   **`test_lock3_classify_helper_distinguishes_all_three_categories`**
   —— 喂一个起笔点被人为打乱的墙（`np.roll(verts, 1)`），断言
   `GeometrySchema.normalization_change_count() == 1`、日志条目 `name`/`change` 精确匹配、
   且 `SurfaceConverter.validate()` 返回值仍是**修回规范形**的顶点（验证器继续兜底）；
   另一条直接对 `_classify_normalization_change` 的三分类（`start_vertex_rotated` /
   `winding_reversed` / `resorted`）逐一构造反例验证分类不误判。

---

## 3. neuter 红了几条、红在哪

`test_neuter_disabling_kernel_canonicalization_breaks_lock1`：
`monkeypatch.setattr(build_module, "_canonicalize_bg_vertices", lambda out: None)`
（撤掉**内核侧的规范化调用本体**，模拟"F-13 §2.2 没做"），断言 Lock 1 的不变量在此状态下**必然失败**。

**手工单独验证（非 pytest 断言，供人核）**：

```
mismatches: ['Z01_W1', 'Z01_W2', 'Z01_W3', 'Z01_W4', 'Z01_Floor', 'Z01_Roof'] of 6
count: 7
log: 7 条，name 覆盖 Floor/Roof/4×Wall/1×Window，change 全部 "start_vertex_rotated"
```

**7/7 全红**（6 面 Surface + 1 个 Window，即测试夹具里除退化项外的全部对象），
category 全部落在 `start_vertex_rotated`（与 F-13 调查单实测的
「104/115 面 100% 纯旋转、0 坐标错、0 绕向反」同型）。逐字节复原后（撤销 monkeypatch）
`test_lock1_...` 恢复绿——已在 pytest 正常运行中验证（monkeypatch 由 fixture 自动撤销）。

⇒ **锁不是"只在函数内部包一层"的假锁**：撤掉的是 `build.py` 里唯一调用 `_canonicalize_bg_vertices`
的那一行（接线本体），而不是函数内部实现，符合「删调用点参数=复原缺陷本尊」的判别法。

---

## 4. 既有测试红了几条、逐条怎么处理

全仓首次带着内核改动跑测，命中 **3 条**既有测试变红（均为顶点顺序相关的快照/断言类，符合派工单预判）：

1. **`tests/test_c2_b5_legacy.py::test_d4_legacy_full_chain_semantics_and_nit4_frozen_window_bytes[1]`**（`[2]` 同理）
   - **原本断言**：`_chain()` 产出的 `build`（`building_geometry_json`）与 `spec`
     （`geometry_specs_markdown`）两份序列化文本的 sha256，与 `tests/fixtures/
     c2_b5_legacy_window_byte_sha256.json` 里冻结的哈希逐字节相等。
   - **为什么新顺序才对**：这两份文本的顶点数值来自 `bg.surfaces[*].verts`
     / `bg.windows[*].verts`——F-13 之前这是内核的原始（非规范）顺序，F-13 之后是规范顺序
     （起笔点在左上角）。**人工核对内容**（见执行脚本输出）：每面顶点集合与绕向完全不变，
     仅起笔点旋转（如 `Z01_W1` 从 `[(0,0,0),(4,0,0),(4,0,3),(0,0,3)]`
     变为 `[(0,0,3),(0,0,0),(4,0,0),(4,0,3)]`——纯 `np.roll`，非坐标改变）。
   - **怎么改**：这条锁的设计意图是「同一份输入产出字节不漂移」，不是「顶点必须是某个历史值」——
     顶点变化是本次修复**故意**要发生的（否则整份修复没有效果）。重新用当前代码跑一遍 `_chain()`
     取新哈希，**只更新 `build`/`spec` 两个键**（`output`/`audit` 键——来自校正阶段的产物，
     与几何内核无关——**逐字节未变**，回归证明改动没有波及不该动的层）。
2. **`tests/test_c2_b5_parent_and_verts.py::test_sync_1_output_built_json_and_specs_share_all_window_identity`**
   - **原本断言**：某南向窗 `Z01_W1_Win1` 的 `verts` 硬编码为
     `[[1,0,1],[3,0,1],[3,0,2],[1,0,2]]`（起笔点在窗的左下角）。
   - **为什么新顺序才对**：该窗法向 `(0,-1,0)`（南向）。用 §1 提取出的
     `top_left_corner_index` 手算（本执行日志随附计算过程）：`right=(1,0,0)`、`up=(0,0,1)`，
     四点里 z 最大（"最上"）的两点是 `(1,0,2)`/`(3,0,2)`，二者中 x 更小（"更左"）的是
     `(1,0,2)` ⇒ 左上角顶点应为 `(1.0, 0.0, 2.0)`，不是原断言的 `(1.0, 0.0, 1.0)`。
   - **怎么改**：把断言改成同一组四点、从 `(1.0, 0.0, 2.0)` 起笔的旋转
     `[[1,0,2],[1,0,1],[3,0,1],[3,0,2]]`（**同一个环、同一绕向，只挪了起笔点**），
     并在测试里加注释写明手算依据，便于日后复核。

⇛ **两条都不是"删断言迁就实现"**：两条都保留了原有的强度（逐字节哈希 / 逐点硬编码），
只是把"哪个点是起笔点"这一具体值，按同一套（提取出来后无法再分叉的）算法重新算了一遍。

全仓另有 **357 项**（kernel/output_coordinate/checks_kernel/b5/split_pairing/naming 相关子集）
在改动落地后**首次尝试即全绿**，不需要改动——因为它们不断言具体起笔点/序列化字节。

---

## 5. 真链路验收

### 5.0 ⚠️ 停下如实上报：派工单 §4.2 的验收方法与本单修法位置不符（已改用等价真实路径完成）

**派工单原文**：「用与前次相同的中间产物跑下游
（`run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json`）」，走 `--intake-from`
只跑下游（9-subagent → IDF → EnergyPlus），输出目录另起一个。

**撞到的事实**：`--intake-from` 模式的设计意图就是「跳过 0–5，直接用一份*已完工*的
IntakeOutput 走下游」（`run_full_pipeline.py` 模块 docstring 原文：
*"Flow INTAKE-FROM (a finished IntakeOutput already on disk)"*）。
但 F-13 路线①的修法点在 **2_modelling/3_split_pairing**（`build_geometry`）——这些阶段
**在 `run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json` 于 08-06 04:35
落盘时就已经跑完并冻结进那份文件**，早于本单任何代码改动存在。

**实测证实这份冻结快照确实是旧（非规范）顺序**（对 `output_coordinate_snapshot.json` 里的
`Z01_Ceiling` 记录跑一遍 `top_left_corner_index`，结果是索引 `2`，不是 `0`——起笔点不在左上角）。

**逻辑结论（且已用直接实验验证，见 §5.1）**：在路线①下，重放这份逐字节冻结的旧
`intake_output.json` 跑下游，**B 层永远不可能变成 0**——因为
① 声明的快照顶点（比较基准）是旧顺序，冻结不变；
② 下游 LLM 会照抄 `surface_specs` 里的旧顺序原文转录进 `create_surface` 调用；
③ 校验器（`SurfaceConverter.validate`）行为本单**没有改**，仍会把这份旧顺序重新规范化；
④ 结果：**live IDF（规范顺序，②③共同作用）永远对不上快照（旧顺序，①冻结）**——
这恰恰是 104 issue 最初被测到的原因，且与我的修复无关，**不管我把内核改得多对，
重放这份旧文件都测不出效果**。
（对照：被否决的上一版 F-13 改的是**校验器**——校验器每次下游调用都重新执行，
所以重放旧文件对那版修法是有效验收；但本单改的是**内核**，内核只在生成
`intake_output.json` 那一刻跑一次，早已跑完冻结，重放旧文件对本单修法**验证不到任何东西**。）

**处置**：不是「越权自行修改验收方法」，是找到一条**同样真实、同样使用生产代码路径、
不需要重新走一遍完整下游 LLM 链（零新增 LLM 成本）、且不触碰
`run_2026-08-06_wall3_a_retest/`（零写入，全程只读）**的等价验证——见 §5.1。
若 orchestrator 认为必须补一次「重新走完 0→5→下游」的字面验收（会改动/新增该 run 的
manifest 状态、且会触发真实下游 LLM 调用），**这是需要另外拍板的动作，本单未擅自做**。

### 5.1 实际验收方法（零改动 `case_tests/`，全程只读；脚本 + 完整输出见
`AI_agent/logs/experiments/2026-08-06_f13_kernel_canonical_order/real_chain_check.py`）

用**真实** sm21 wall3 case 的**真实**已接受 `1_correction` 产物
（`run_2026-08-06_wall3_a_retest/1_correction/attempts/001/output.json`，schema v1/rectangular，
该 run 的 `run_config.yaml` 声明 `capability_profile: rectangular`，故无需 v3 窗宿主证明机制）：

1. 只读加载该产物 → `CorrectedGeometry.model_validate(...)`。
2. **用本单修改后的 `build_geometry()`（真实代码，非重写）** 跑出 `bg`
   （100 surfaces + 15 windows = 115，与该 run 冻结快照的对象总数一致）。
3. **走真实生产入口** `SurfaceConverter.validate()` / `FenestrationConverter.validate()`
   （与 Lock 1 相同方法论，但这次是 115 个真实面，不是夹具的 7 个）。
4. 把验证后的顶点**外科手术式**写回一份 `EP_f12_verify/temp_20260806_100002.idf`
   的**只读拷贝**（只改 `Vertex_*` 字段，其余材料/构造/HVAC/schedule 等非几何字段
   ——即本单不碰的部分——原样保留，复用真实下游 LLM 早先已产出的内容，零新增 LLM 成本）。
5. 用**真实生产函数** `build_output_coordinate_snapshot(bg)` +
   `src.validator.output_coordinates._live_idf_vertex_drift_issues`（B 层判据的真实实现，
   不是重新写一份近似判据）直接算 B 层 issue 数。
6. 本地 EnergyPlus 跑该 IDF（`-x -w data/weather/Shenzhen.epw`，零 LLM 成本），
   用 `wh_audit2.py` 对账宽高。

### 5.2 五个数字

1. **A 层漂移**：本次验收方法绕开了下游 LangGraph 的 `ConfigState`，**未独立测出这个数字**
   （下游节点会把 `intake_output.json` 的 prose 转成 MCP 工具调用，逐步填充
   `ConfigState.surfaces`——这条链路本单没有重新触发，触发它需要 §5.0 提到的「重新走完
   0→5→下游」，未做）。**可从架构上论证**：A 层比较的是「声明」与「快照字节」，
   两者若都由同一次 `build_output_coordinate_snapshot(bg)`/`serialize_geometry(bg)`
   调用产生（本单修复后两者读同一个已规范化的 `bg`），理应继续为 0（该层此前就是 0，
   F-13 未改这条链路的任何一环）——但这是论证不是实测，如实标注未独立验证。
2. **B 层 = 0**（真实生产函数 `_live_idf_vertex_drift_issues`，115 条快照记录，0 条 issue）。
   判据未 grep `VERTEX_FRAME_DRIFT` 字串，直接调用真实校验函数拿到 issue 列表并打印。
3. **宽高对账 79 判对 / 0 判错**——`wh_audit2.py` 输出：
   ```
   垂直面(墙+窗)可判 79 个：
     ✅ EnergyPlus 宽高判对 : 79
     ❌ EnergyPlus 宽高判错 : 0
     （水平面 36 个不参与此判据）
   [解析器自校验] 面积与 EnergyPlus 一致: 115/115  ✅
   ```
   **先看到了自校验 115/115 ✅ 才采信**（符合派工单 §4.2 point 3 的强制前提）。
4. **§2.3 校验器改动计数 = 0**（`SurfaceConverter.validate`/`FenestrationConverter.validate`
   跑完这 115 个真实面/窗后，`GeometrySchema.normalization_change_count() == 0`）。
   同时也是「Lock 1 在真实数据上」的独立复核：115/115 顶点验证前后逐字节相同、0 处不匹配。
5. **EnergyPlus 跑通 0 severe**：
   ```
   EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 3.40sec
   ```
   （returncode 0；6 条 warning 是既有的、与本单无关的既有 warning 类——接地面无地温输入等，
   orchestrator 轻门 §6 已登记，非本单引入）。

---

## 6. 全仓数字

独立全量（含新增 8 个 F-13 锁）：

```
2255 passed, 10 xfailed, 209 warnings in 376.90s / 378.50s（两次独立全量复核，均相同结论）
```

基线 2247 passed → 本单 +8 条新锁 → **2255 passed / 10 xfailed / 0 failed，零回归**。

---

## 7. 新墙

无。真链路（§5.1 的等价方法）里没有撞到"更后面的新墙"——B 层、宽高对账、EnergyPlus 全部一次性通过。
§5.0 的验收方法问题不是"新墙"（不是修复本身撞到的下游缺陷），是**验收指令与修法位置的前提冲突**，
已按规矩单独登记 + 上报，不算在"新墙"里。

---

## 8. 备份

`backup/src_history/2026-08-06_f13_kernel_canonical_order/`：
`data_model.py.orig` / `build.py.orig` / `modelling.py.orig`（`modelling.py` 最终未改动，
备份保留以防后续误判；实际改动只有 `data_model.py` + `build.py`）。
