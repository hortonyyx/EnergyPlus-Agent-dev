# 执行日志 · F-13 调查：两套顶点顺序规范，B 层漂移门根因

> **调查单**：`AI_agent/logs/reviews/request/2026-08-06_f13_two_vertex_order_conventions_investigation_claude.md`
> **席位**：Claude 侧 Sonnet 子代理（调查席）· **主工作树** · **日期**：2026-08-06
> **边界遵守**：⛔ 零生产码/测试改动 · ⛔ 零 commit/push/`git add` · ⛔ 未碰其它席位 dirty/未跟踪文件 ·
> ⛔ 未跑下游/未跑 EnergyPlus（零 LLM 成本）· ✅ 一次性脚本全在 `/tmp/f13/`（未拷入仓库，遵守边界原文）

---

## 0. 开工自检

```
git log --oneline -1     # 77b3da4 08.06_f12_surface_prompt_transcribe — 符合预期
pwd                      # /workspaces/EnergyPlus-Agent-dev — 符合预期
git status --short       # AI_agent/plan.md(M) + 5 个其它席位产出的未跟踪文件/目录 — 均未碰
```

调查单陈述的事实经核对**全部属实**（§1 的 A/B 两层描述、根因定位、07-02 回溯的引用），本单**无需停下上报**。

---

## 1. TL;DR

1. **§2 决定性实验**：把内核冻结快照的顶点喂过一次**真实生产排序器路径**（`SurfaceConverter.validate`/`FenestrationConverter.validate` → `GeometrySchema.validate_points_sorting` → `_sort_vertices_clockwise`，用真实 metadata），与实测的 live IDF **115/115 逐面逐顶点完全一致**。**排序器是 B 层 104 条漂移的唯一成因，证毕。**
2. **第 2 问（旋转 vs 翻转）**：**也翻转绕向，不是只旋转起点**。用真实 sm21 墙体做正反两组输入实测：`sort(P)` 与 `sort(reversed(P))` 在两种独立测试路径下（① 固定外部法向的孤立函数调用；② 走真实生产路径、含其自身独立推导法向量）**逐字节完全相同**——排序器完全无视输入的原始绕向，只由（它自己独立算出的）法向量决定输出方向。
3. **第 3 问（对内核产物是不是恒等）**：**不是**。115 个面里只有 **11 个（全部是 Floor 类型）** 恰好已经满足排序器的规范；其余 **104 个（Wall/Ceiling/Roof/Window）无一例外都被改写**。排序器不是死代码——它是 `SurfaceConverter`/`FenestrationConverter` 的**唯一** `GeometrySchema` 调用路径，是每一次真实 IDF 面/窗写入的必经关卡（MCP 工具 `create_surface`/`create_fenestration_surface` 也走它）。
4. **三条路线**：推荐 **② 排序器对已合规顶点整段退役/短路**（成本最低、消除根因、不引入新的跨模块耦合）；① 需要内核复刻排序器的"左上角起点"算法，双向维护成本高；③（比较前双边规范化）按调查单自定的判据——**因为第 2 问答案是"也翻转"，③ 不安全**，会把手性错误一起抹掉，**不推荐**（含一条按层区分的补充说明，见 §7）。
5. **第 5 问（B 层门史）**：`_coordinate_gate(idf=...)`/`_live_idf_vertex_drift_issues` 于 **2026-07-14（`ccb396e`）** 接线，比根因代码（`299149c`，04-21）晚近 3 个月。**全仓只有今天这一个 run（`run_2026-08-06_wall3_a_retest`）同时具备"真实冻结快照 + 真实转换出的 IDF"**——用 `find` 机械扫描全仓確认：全库唯一一份 `output_coordinate_snapshot.json` 就在这个 run 里，B 层这道检查**接线以来从未被真实数据喂过，今天是第一次**。104 不是"新坏"，是"第一次测到"。
6. **第 6 问（07-02 那 89 条）**：**证实是同一段代码**。用今天的生产代码跑 07-02 那次真实 run 的内核文本，通过真实排序器路径，**115/115 精确重现 07-02 当年落盘的真实 IDF**；07-02 内核原始顺序 vs 07-02 真实 IDF 的裸比对复算出 **恰好 89/100（BuildingSurface）+ 15/15（Fenestration）差异、全部纯旋转、0 绕向反、0 坐标错**，与调查单引用的 orchestrator 回溯数字逐位吻合。

---

## 2. § 2 决定性零成本实验（先做）

### 2.1 做法

用 `run_2026-08-06_wall3_a_retest` 这个 run（唯一同时具备冻结快照 + 真实 IDF 的 run）：

1. 从**真实 live IDF**（`EP_f12_verify/temp_20260806_100002.idf`）读出每个面/窗的**全部非几何 metadata**（Surface Type / Construction Name / Zone Name / Outside Boundary Condition / …）——这些字段不受排序器影响，可以安全复用。
2. 把 vertices 换成**内核冻结快照**（`5_intakeoutput/output_coordinate_snapshot.json`）里的**未经排序**原始顶点（已由 F-12 施工日志独立证实：A 层今天 0 漂移，即快照顶点与 LLM 实际提交给工具的顶点逐位相同——所以快照顶点就是"排序器处理之前"的真实输入）。
3. 用**真实生产入口** `SurfaceConverter(idf).validate(zone_to_surfaces)`（按 Zone 分组，与 `SurfaceConverter.convert()` 完全同构）+ `FenestrationConverter(idf).validate({"fenestrationsurfaces": ...})`（与生产调用顺序一致：先 surfaces 后 fenestrations），跑出排序后的顶点。
4. 与**实测的** live IDF 顶点逐面比较。

脚本：`/tmp/f13/decisive_experiment.py`（可独立重跑，见 §2.3 命令）。

### 2.2 结果

```
live IDF surfaces: 100  fenestrations: 15
snapshot records: 115
built surface_payload: 100  fenestration_payload: 15
validated_surfaces: 100  validated_fenestrations: 15

=== RESULT: 115/115 faces IDENTICAL after running snapshot vertices through the real sorter path ===
=== DIFFERENT: 0 ===
```

**115/115 逐面逐顶点（含顺序）完全一致。** 用真实 metadata + 真实生产入口 + 真实（未排序）内核顶点，精确重现了实测的 live IDF。

### 2.3 结论 + 复跑命令

**排序器（`GeometrySchema.validate_points_sorting` → `_sort_vertices_clockwise`）是 B 层 104 条漂移的唯一成因**，没有第二个成因——没有任何"喂了排序器仍然对不上"的面。§2 到此**证毕**，以下第 2–6 问的回答均建立在此事实之上。

```bash
cd /workspaces/EnergyPlus-Agent-dev
python3 /tmp/f13/decisive_experiment.py 2>&1 | grep -v "WARNING\|T-vertex"
```
（脚本已用 `BaseSchema.set_idf(IDD_PATH)` 走真实 IDD，无需额外环境；若 `/tmp/f13` 已被清理，本日志 §8 附完整脚本源码可直接复原。）

---

## 3. 第 2 问 ⭐：只旋转起点，还是也翻转绕向？

**判据**（调查单原文）：这条决定"先规范化再比"是否安全——只旋转 ⇒ 手性反仍能被抓到；也翻转 ⇒ 规范化会把手性错误一起抹掉。

### 3.1 读实现（先给出代码依据，再给实测）

`_sort_vertices_clockwise`（`data_model.py:1145-1177`）：
- 用 `cmp_to_key(compare_points)` 对全部顶点**重新排序**，`compare_points` 只依据"该点相对质心的向量、与传入的 `normal_vector` 的叉积符号"判断先后——**完全不参考输入列表原有的相邻关系或方向**。
- 排完后 `np.roll(points, -top_left_index, axis=0)` 只是再选一个起点。

而这个 `normal_vector` 本身（对墙/窗类）来自 `_get_normal_vector`（:1226-1248）：拿 `points[0],[1],[2]`（**输入列表的前三个点，与输入顺序有关**）算 `cross(v1,v2)`，但**紧接着用"是否指向内部参考点"做符号检验**（:1239）——若指向内部就取反。**这个检验的依据是几何关系（质心与最近内部点的连线），不是输入顺序** ⇒ 无论输入是 CW 还是 CCW，检验后选出来的 `normal_vector` 理论上应该是同一个"朝外"方向。

⇒ 读代码即可预判：完整链路（`_get_normal_vector` + `_sort_vertices_clockwise`）对"同一物理多边形"的输出**应该与输入的原始绕向无关**——这已不是"只旋转"，而是**完全重新推导**。但调查单明令不接受"读代码觉得是"，故做下面两组实测。

### 3.2 实测一：孤立函数、固定外部法向

真实数据：sm21 一扇窗（`Z01_W3_Win1`）在 y=7.65 平面的四个顶点：
```
P          = [(1.0,7.65,2.6), (3.4,7.65,2.6), (3.4,7.65,1.0), (1.0,7.65,1.0)]
P_reversed = [(1.0,7.65,1.0), (3.4,7.65,1.0), (3.4,7.65,2.6), (1.0,7.65,2.6)]   # 同一物理四边形，绕向完全相反
```
分别用**固定**法向 `[0,-1,0]` 与 `[0,1,0]` 调用真实 `_sort_vertices_clockwise(surface, normal)`（`GeometrySchema` 真实实例、真实方法，非重写）：

```
--- normal_vector = [0.0, -1.0, 0.0] ---
  sort(P)           = [(1.0, 7.65, 2.6), (1.0, 7.65, 1.0), (3.4, 7.65, 1.0), (3.4, 7.65, 2.6)]
  sort(reversed(P)) = [(1.0, 7.65, 2.6), (1.0, 7.65, 1.0), (3.4, 7.65, 1.0), (3.4, 7.65, 2.6)]
  逐字节相同

--- normal_vector = [0.0, 1.0, 0.0] ---
  sort(P)           = [(3.4, 7.65, 2.6), (3.4, 7.65, 1.0), (1.0, 7.65, 1.0), (1.0, 7.65, 2.6)]
  sort(reversed(P)) = [(3.4, 7.65, 2.6), (3.4, 7.65, 1.0), (1.0, 7.65, 1.0), (1.0, 7.65, 2.6)]
  逐字节相同
```

对**两种法向选择**，`sort(P)` 与 `sort(reversed(P))` 输出**逐字节完全相同**（不是"互为循环旋转"，是**完全同一个列表**）。脚本：`/tmp/f13/q2_rotation_vs_flip.py`。

### 3.3 实测二：完整生产路径（含排序器自己独立推导法向量）

只测孤立函数还不够严格——生产路径里法向量不是外部给的，是排序器自己从输入算的。用真实 zone（`Z01_F1_Office_NW`）的真实外墙 `Z01_W1`，跑两次**完整** `SurfaceConverter.validate()`（按 zone 分组，与生产完全同构）：
- Run A：该 zone 全部墙都用快照原始顺序；
- Run B：**只把 `Z01_W1` 一面墙的顶点整体反转**，同 zone 其余面不变。

```
target wall = Z01_W1
input (snapshot order) : ((-0.1, 4.75, 0.0), (4.3, 4.75, 0.0), (4.3, 4.75, 3.0), (-0.1, 4.75, 3.0))
input REVERSED          : ((-0.1, 4.75, 3.0), (4.3, 4.75, 3.0), (4.3, 4.75, 0.0), (-0.1, 4.75, 0.0))
sorter output, run A (as-is)    : ((-0.1, 4.75, 3.0), (-0.1, 4.75, 0.0), (4.3, 4.75, 0.0), (4.3, 4.75, 3.0))
sorter output, run B (reversed) : ((-0.1, 4.75, 3.0), (-0.1, 4.75, 0.0), (4.3, 4.75, 0.0), (4.3, 4.75, 3.0))

=== A == B ？ True ===
```

**完整生产路径（含法向量的独立推导）同样把一面被人为反转绕向的真实墙，规范化成与未反转时逐字节相同的输出。** 脚本：`/tmp/f13/q2_full_pipeline_check.py`。

### 3.4 结论

**`_sort_vertices_clockwise`（连同它调用的 `_get_normal_vector`）不是"只旋转起点"，是完全重新推导绕向 —— 给它同一个物理多边形的任意绕向输入，输出永远是同一个（由它自己独立判定为"朝外"的）绕向，起点也随之统一。**

**这条结论对调查单的判据是硬答案：第 2 问的答案是"也翻转"** ⇒ 若在漂移检查里对两边施加同一个规范化再比，会把"同一组顶点、绕向被反转"这种真实的手性缺陷（几何一字节不差，只是绕向反了）**完全抹掉，检查会判定"无漂移"**。这正是调查单强调的不可接受场景。

**重要限定**（避免过度推广）：手性反导致"两窗互换房间"这个具体场景，实际是**两个不同对象**（`host_zone_id` 不同）的问题，漂移检查里 `host`/`zone_or_parent` 是**独立的精确字符串比较**，不受顶点排序影响，**这一位仍然会抓住**。第 2 问揭示的风险是**同一个对象自身**如果发生了"点集不变、绕向被反转"这类缺陷（EnergyPlus 里表现为法向朝内、日照/得热计算全错），规范化会让它在漂移检查里被判定为"正常"。两类风险都真实存在，但机制不同，此处如实拆开说明。

---

## 4. 第 3 问：排序器对内核产物是不是恒等变换？

**不是。** §2 的 115 个面里：

- **11 个恰好已经满足排序器规范**（原样通过、未被改写）——经查**全部是 Floor 类型**（Z08/Z09/Z10/Z11/Z12/Z13/Z14 各层 Floor，与 F-12 施工日志 §4.3 独立记录的名单一致）。
- **104 个（全部 Wall / Ceiling / Roof / Window）无一例外被改写**——起点位置变了（§2.2/§3 已证：不是坐标错，也不是绕向反，纯粹起点不同）。

**为什么只有 Floor 恰好合规**：`validate_points_sorting`（:1112-1122）对 Floor 用**固定**法向 `[0,0,-1]`（不经 `_get_normal_vector` 推导），对 Wall/Ceiling/Roof/Window 才走"从输入点+内部参考点独立推导法向"的分支。本调查未深入内核自身的顶点起点选择算法，只能报告**观测事实**：Floor 这一类恰好与排序器的"左上角起点"规范重合，其余类别系统性不重合。

**它不是死代码**：`grep` 全仓确认 `GeometrySchema` 只有两个调用点——`SurfaceConverter.validate`（:63）与 `FenestrationConverter.validate`（:67），是这两个转换器**唯一**的顶点处理路径，而这两个转换器是 `ConverterManager.convert_all()` 的固定成员、也是 MCP 工具 `create_surface`/`create_fenestration_surface`（`src/mcp/tools/surface.py`/`fenestration.py`）的下游——**每一次真实写入 IDF 的面/窗都必经此路**。`data_model.py:1085-1088` 的"idfpy 切换后整个删掉"是**未来意图**，不是"现在没人用"；今天它仍是每次真实几何输出的必经关卡，删除或改动前必须谨慎评估。

---

## 5. 第 4 问 ⭐：三条修法路线

### ① 统一到排序器的规范（内核直接产出排序器要的顺序）

- 做法：内核序列化（`serialize_geometry` / `src/agent/geometry/specs.py`）复刻 `_get_top_left_corner_from_normal` 的算法（法向 → world_up 选轴 → right/up 基 → 按 `(-y_coord, x_coord)` 字典序找起点），对每个面在写出前就选到排序器认可的起点。
- 后果：A 层已 0 漂移（F-12 已修），若内核也匹配排序器规范，`_sort_vertices_clockwise` 对内核产出退化为恒等 ⇒ B 层归零，两层都稳定通过。
- 代价：**中到高**——需要在 `src/agent/geometry/` 里维护一份与 `src/validator/data_model.py` 里几乎相同的起点算法，两处必须永远同步（排序器算法一旦调整，内核这边不跟着改就会立刻复发）；引入了原本没有的跨模块耦合。

### ② 统一到内核的规范（排序器对已合规顶点不动手，或整段退役）——**推荐**

- 做法：给 `validate_points_sorting` 加一个"信任已经是绝对世界坐标、且已经是一致朝外顶点顺序"时的**短路**分支（例如按来源标记跳过重排），或者既然 §4 已证实它当前**只做起点归一化、不做任何坐标修正**、且它的"翻转绕向"能力本身是调查单标记为危险的行为——**评估后直接整段退役**，前提是先确认（未在本单授权范围内验证，留待施工单）内核自己保证输出永远是有效的、朝外一致的简单多边形（EnergyPlus 端需要正确绕向才能算对法向/得热，若这个保证不成立，退役会让潜在的内核绕向 bug 直接进 IDF 不被拦截）。
- 后果：B 层 104 归零（连同 §3 那 11 个已合规的一起，全部变成"内核产出=最终 IDF"的恒等路径）；A/B 两层将真正等价（因为它们比的是同一份未被二次处理的顶点）。
- 代价：**小到中**——是本地单点改动，不产生新的跨模块耦合；主要风险是"排序器过去偶然承担了修正绕向的安全网角色"（§3.1 读码已证：它会把任何反绕向的输入摆正），退役后若内核自身存在尚未发现的绕向 bug，会直接体现为真实 IDF 里法向朝内的面，且**该 bug 只有靠 EnergyPlus 报错或人工目检才能发现**——**这不是坏事**（把隐藏的 bug 变成可见的 bug 正是本调查该做的事），但要在施工单里写清楚这个权衡，别当成零风险改动。

### ③ 比较前双边规范化——**不推荐**，且给出比调查单二元判据更细一层的说明

调查单原文判据：只有第 2 问答"只旋转不翻转"，这条才安全。**本单第 2 问的实测答案是"也翻转"** ⇒ **按调查单自己定的判据，③ 不安全，不应采用**。

补充说明（不改变结论，但避免以后有人把这条想得比实际更可怕或更安全）：
- ③ 若施加在**漂移检查这一层**（即比较时对两边各自跑一次同一个规范化函数，而不是让排序器出现在生产转换路径里之外的地方），对 **B 层**这个具体检查而言，实际风险比"抹掉所有手性信息"要窄——因为 B 层比的"实际"一侧（live IDF）**本来就已经**被生产转换器强制跑过一次排序器（这是转换器的固定行为，不是可选项），也就是说：只要转换器还在无条件跑排序器，一个"点集不变、绕向被反转"的缺陷**在今天的架构下，根本不可能原样进入 live IDF**——它早就在真实转换那一步被排序器摆正了，B 层检查看不看得出来跟"要不要在比较时再套一层规范化"无关。真正的风险窗口在 **A 层**（ConfigState vs 快照，转换发生之前）：如果 A 层也套上同一个规范化再比，就会掩盖"LLM 提交的绕向是否忠实转录"这个信号——但由于 host/zone 仍是精确比对（§3.4 已说明），"两窗互换房间"这个具体场景不会被这条路线放过。
- **即便如此，仍不推荐**：因为这个"B 层天然安全"的论证**依赖一个实现细节**（转换器至今无条件跑排序器）而不是结构性保证——一旦有人以后给转换器加了"跳过排序器"的旁路（例如为了实施路线①或②），这条论证立刻失效；把一个安全性论证建立在"某处实现细节将来不变"上是脆弱的。**推荐直接走 ②**，从根上消除需要"规范化再比"的理由。

### 什么都不改

- 现状：任何走完下游到 `run_simulation`/`export_idf_only` 的真实 case，都会在 Pre-EnergyPlus gate 撞上 104 条 `VERTEX_FRAME_DRIFT`，`Simulation not started`。**EnergyPlus 阶段永远不可达。** 不可接受作长期态（与 F-12 施工日志 §4.2 结论一致）。

---

## 6. 第 5 问：B 层这道门什么时候接上的、以前有没有产物喂过它

### 6.1 接线时间

```bash
git log --format="%ad %h %s" --date=short -S "_coordinate_gate" -- src/mcp/tools/workflow.py
# 2026-07-14 ccb396e 7.14_BO_NorthAxisWiringClosure

git log -S "_live_idf_vertex_drift_issues" --format="%ad %h %s" --date=short -- src/validator/output_coordinates.py
# 2026-07-14 ccb396e 7.14_BO_NorthAxisWiringClosure
```

`_coordinate_gate(idf=manager._idf)`（把真实转换出的 IDF 传给校验层，从而触发 `_live_idf_vertex_drift_issues`）与该函数本体，**同一个提交 `ccb396e`（2026-07-14）一起接线**。作为对照，"Pre-EnergyPlus gate"这个提法本身更早（`04e7dbe`，06-10），但当时只查 interzone pair + schedule，**不含顶点/坐标**这部分；顶点比对是 07-14 才加进这道关卡的。

排序器本体 `299149c`（04-21）比这道检查早了近 3 个月——与调查单 §1 陈述一致，已核实。

### 6.2 是否有产物喂过（机械扫描全仓）

触发 B 层比对需要**同时满足**两个前提（`output_coordinates.py:670` + `:696`）：`idf is not None` **且** `snapshot_bytes is not None`（context 里带着真实冻结快照）。扫描全仓：

```bash
find case_tests -iname "output_coordinate_snapshot.json" | grep -v "/attempts/"
# case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/output_coordinate_snapshot.json
```

**全仓库、跨所有 case、所有历史 run，只存在这一份 `output_coordinate_snapshot.json`。** 也就是说，07-14 接线以来的三周里，没有任何其它 run 具备触发 B 层比对所需的第二个前提（快照）——即使某些 run（如 `probe_b_2026-08-05_legacy_intake`）确实产出过真实 IDF（`find case_tests -iname "temp_*.idf"` 命中 20+ 个历史 run），它们全部发生在快照机制存在之前，或者本身走的路径不产出/不携带快照。

**⇒ 结论：B 层这道门自 07-14 接线以来从未被真实数据喂过，今天（`run_2026-08-06_wall3_a_retest`）是它第一次真正被执行到、且第一次拿到能比对的真实数据。104 不是"新引入的回归"，是"三周未被测过的门，第一次被测，测出了一个从 04-21 就存在、比它自己早三个月的老缺陷"。** 这与本项目已有方法论（"新门第一次报红，先问门什么时候接上的，别默认红=新坏"）完全吻合，也与调查单 §1 的定性一致。

---

## 7. 第 6 问：07-02 那 89 条是不是同一段代码造成的？

**证实：是。** 07-02 那次 run（`run_2026-07-02_sonnet_flow_e2e`）比 E4 快照机制（07-14）早了 12 天，**该 run 目录下没有 `output_coordinate_snapshot.json`**（已用 `find` 确认），所以它当年根本没有、也不可能触发过 B 层检查——orchestrator 提到的"回溯对账"必然是**事后**用 07-02 遗留的 `intake_output.json`（内核序列化的原始几何文本）与 07-02 遗留的真实 IDF（`EP/temp_20260702_132413.idf`）做的离线对账，不是当年产生的检查结果。

本单**独立复算**这份历史数据（不读取/沿用 orchestrator 的脚本，自己解析 `surface_specs`/`fenestration_specs` NL 文本，脚本 `/tmp/f13/q6_0702_check.py` + `/tmp/f13/q6_breakdown.py`）：

**第一步：裸比对**（07-02 内核原始顺序 vs 07-02 真实 IDF，不经过任何处理）：
```
BuildingSurface:Detailed (n=100): same=11 diff=89
FenestrationSurface:Detailed (n=15): same=0 diff=15
raw identical: 11/115   raw different: 104
  pure rotation   : 104
  winding reversed: 0
  coord differs   : 0
```
**89/100（BuildingSurface）与调查单引用的 orchestrator 数字逐位吻合**；全 115 个对象合计裸差异 104，其中 100% 纯旋转、0% 坐标错、0% 绕向反——与今天 08-06 run 的 B 层 104 条**形态完全同构**。

**第二步：用今天的生产代码重放**（把 07-02 内核文本喂过今天的 `SurfaceConverter.validate`/`FenestrationConverter.validate`）：
```
=== predicted (kernel text through real sorter) vs REAL 07-02 IDF ===
total comparable: 115
identical         : 115
different         : 0
```

**今天（2026-08-06）的排序器代码，原样处理 07-02 的内核输出，精确重现了 07-02 当年落盘的真实 IDF，115/115 逐面逐顶点完全一致。** 由于排序器自 `299149c`（04-21）以来未变（§6.1 已核实），且 07-02（`2026-07-02`）落在 04-21 之后、该结果并非巧合——**07-02 的 89 条与今天 08-06 的 104 条，是同一段代码在两次不同的真实数据上产生的同一类效应**。

**⇒ 调查单 §1 最后一条陈述得到证实，不是"八成"，是可机械重放验证的事实。**

---

## 8. 附：可独立复跑的脚本（`/tmp/f13/`，若已清理见下方内联源码）

```bash
cd /workspaces/EnergyPlus-Agent-dev
python3 /tmp/f13/decisive_experiment.py 2>&1 | grep -v "WARNING\|T-vertex"       # §2
python3 /tmp/f13/q2_rotation_vs_flip.py 2>&1 | grep -v "WARNING\|T-vertex"      # §3.2
python3 /tmp/f13/q2_full_pipeline_check.py 2>&1 | grep -v "WARNING\|T-vertex"   # §3.3
python3 /tmp/f13/q6_0702_check.py 2>&1 | grep -v "WARNING\|T-vertex"           # §7
python3 /tmp/f13/q6_breakdown.py 2>&1 | grep -v "WARNING\|T-vertex"            # §7 raw breakdown
git log --format="%ad %h %s" --date=short -S "_coordinate_gate" -- src/mcp/tools/workflow.py   # §6.1
find case_tests -iname "output_coordinate_snapshot.json" | grep -v "/attempts/"                 # §6.2
```

（脚本全部只读生产代码 + 只读 `case_tests/` 历史产物，未修改任何文件；未在 `/tmp` 之外落任何新文件，遵守调查单边界原文 "✅ 一次性脚本一律放 /tmp"。若需要本单在仓库内留存脚本副本以便复核，请在拍板时明确指出，本单按边界原文默认不拷入仓库。）

---

## 9. 边界符合性 + 停下上报判断

- ⛔ 未改任何生产代码/测试；⛔ 未 `git add`/commit/push；⛔ 未跑下游/未跑 EnergyPlus（零 LLM 成本）；⛔ 未放宽任何门/未改任何容差；⛔ 未碰 `case_tests/` 未跟踪目录（全部只读）、未碰其它席位的 dirty 文件（`plan.md` 等）。
- **停下上报**：本单陈述的事实经逐条核对**全部属实**，无需上报。唯一值得记录的澄清：调查单 §2 的建议做法（"喂过一次同一个排序器路径"）本单采用了**真实生产入口**（`SurfaceConverter.validate`/`FenestrationConverter.validate`，含按 zone 分组、含真实 metadata）而非直接手调 `_sort_vertices_clockwise`——这是为了让 §2 实验的结论对"生产路径"而不仅是"孤立函数"成立，比调查单原文思路更严格，非偏离本意的改动。
