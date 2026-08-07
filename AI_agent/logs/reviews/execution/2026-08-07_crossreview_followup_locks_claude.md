# 施工日志 · 交叉审 follow-up：补两处正确性锁

- **日期**：2026-08-07
- **席位**：Claude 侧 Sonnet 子代理（施工席），主工作树
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `950cdbf`（施工单要求 `950cdbf` 或更新，命中）
- **施工单**：[`request/2026-08-07_crossreview_followup_locks_dispatch_claude.md`](../request/2026-08-07_crossreview_followup_locks_dispatch_claude.md)
- **来源**：GLM-5.2 交叉审 [`verdict/2026-08-07_f12_f9_f13_crossreview_glm.md`](../verdict/2026-08-07_f12_f9_f13_crossreview_glm.md)
- **状态**：✅ 完成（任务一 + 任务二 + 两次 neuter 全部按纪律做完，全仓零回归）

> 证据纪律：每条结论附可独立重跑的命令 / 文件:行号 / 数字。neuter 副本落 `/tmp` 一次性 worktree，逐字节复原。

---

## 0. 开工自检

```
$ git log --oneline -1
950cdbf 08.07_WrapUp_EndToEnd_TrustworthyNumbers_F13r1_Passed   ✓ 命中施工单要求

$ git status --short
 M AI_agent/logs/reviews/verdict/2026-08-06_f13_r1_orchestrator_lightgate.md   (已知，非本单)
?? AI_agent/logs/reviews/request/2026-08-07_crossreview_followup_locks_dispatch_claude.md  (本单)
?? AI_agent/logs/reviews/verdict/2026-08-07_f12_f9_f13_crossreview_glm.md      (本单来源)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_e1_haiku_e2e/0_reading/cv_evidence/  (已知未跟踪，不碰)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_smoke_downstream/                    (已知未跟踪，不碰)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-05_smoke_downstream_r2/1_correction/    (已知未跟踪，不碰)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/                      (已知未跟踪，不碰)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-07_f13_e2e_verify/                      (已知未跟踪，不碰)
```

自检通过，与施工单 §0 一致。全程只改 `tests/`，未碰任何 `case_tests/` 未跟踪目录，未 `git add -A`。

---

## 1. 任务一 —— `tests/test_f13_kernel_canonical_vertex_order.py` lock2 补三条手算断言

### 1.1 手算值与推导依据

三条断言都从 `top_left_corner_index`（`src/validator/data_model.py:1086-1116`）的定义**独立推导**，
**没有跑一遍实现再抄输出**（推导先做、跑实现核对在后，见 §1.2）。推导过程整段作为注释写进
`tests/test_f13_kernel_canonical_vertex_order.py`（楼板 `:189-224`、天花 `:236-262`、窗 `:288-296`）。

| 面型 | 法向 | `world_up` 分支 | `right` | `up` | 手算 `canonical[0]` |
|---|---|---|---|---|---|
| 楼板 | `(0,0,-1)`（朝下） | `\|dot\|>0.99` 且 `dot<0` ⇒ 换成 `(0,-1,0)` | `(1,0,0)` | `(0,-1,0)` | **`[0.0, 0.0, 0.0]`** |
| 天花/屋顶 | `(0,0,1)`（朝上） | `\|dot\|>0.99` 且 `dot>0` ⇒ 换成 `(0,1,0)` | `(1,0,0)` | `(0,1,0)` | **`[0.0, 3.0, 3.0]`** |
| 窗（南向竖直面） | `(0,-1,0)` | 不触发换轴分支，`world_up` 仍 `(0,0,1)` | `(1,0,0)` | `(0,0,1)` | **`[1.0, 0.0, 1.5]`** |

**楼板一句话**：法向朝下 ⇒「从外面看」= 从下往上看 ⇒ `up` 取世界 `-Y` 而非 `+Y`（与俯视直觉相反，
这正是施工单点名 orchestrator 本轮实际错过的一步）；`right` 仍是世界 `+X`；「上」（`up` 投影最大）
挑世界 Y 最小的一组，同组内再挑「左」（`right` 投影最小）= X 最小 ⇒ `(0,0,0)`。

**天花一句话**：法向朝上 ⇒「从外面看」= 从上往下看的常规鸟瞰视角（北 `+Y` 为上，与平面图习惯一致）；
`up` 取世界 `+Y`、`right` 取世界 `+X`；测试环里北 `y=3` 那组是「上」，同组内选 X 最小 ⇒ `(0,3,3)`（西北角）。

**窗一句话**：与已有范例「竖直墙」（`:200-201`）法向相同（`(0,-1,0)`），不触发近水平换轴分支，
`right=(1,0,0)`、`up=(0,0,1)`，挑 `z` 最大（`1.5`）组里 `x` 最小的 ⇒ `(1.0, 0.0, 1.5)`。

### 1.2 推导 vs 实现核对结果

推导完成后跑了一次确认，**三个手算值与实现逐字节一致**（脚本见下，非断言来源，仅核对）：

```
$ python3 -c "
import numpy as np
from src.validator.data_model import canonicalize_ring_vertices
floor = np.array([[4,3,0],[4,0,0],[0,0,0],[0,3,0]], dtype=float)
print(canonicalize_ring_vertices(floor, np.array([0.,0.,-1.]))[0])   # -> [0. 0. 0.]
ceiling = np.array([[0,0,3],[4,0,3],[4,3,3],[0,3,3]], dtype=float)
print(canonicalize_ring_vertices(ceiling, np.array([0.,0.,1.]))[0])  # -> [0. 3. 3.]
window = np.array([[1,0,1],[2,0,1],[2,0,1.5],[1,0,1.5]], dtype=float)
print(canonicalize_ring_vertices(window, np.array([0.,-1.,0.]))[0])  # -> [1.  0.  1.5]
"
floor canonical[0] = [0. 0. 0.]
ceiling canonical[0] = [0. 3. 3.]
window canonical[0] = [1.  0.  1.5]
```

**一致 ⇒ 不停下上报**（若不一致按施工单要求应立刻停，不自行改任何一边）。楼板值与施工单 §1 引用的
「GLM 手算楼板首顶点 = `[0,0,0]`」逐字吻合，交叉核实一致。

### 1.3 断言落点

三条新断言（`np.array_equal(canonical[0], np.array([...]))`）分别插在
`test_lock2_canonicalization_floor_top_left_and_outward` / `..._ceiling_..` / `..._window_..`
里，紧跟推导注释、在既有自指断言 `top_left_corner_index(canonical, normal) == 0` **之前**，
与垂直墙那条（`:202-203`）同形。

### 1.4 顺带登记（不在本单范围内）

端到端宽高对账仍**只覆盖垂直面**（79/115，36 个水平面被判据排除，因为 `~Width`/`~Height`
对水平面语义不同，需另设计判据）——**本单未补**，按施工单 §1 明确不要求。

---

## 2. 任务二 —— `VERTEX_FRAME_DRIFT` 行为门单元锁

新文件 `tests/test_f12_vertex_frame_drift_gate.py`（7 个测试，全部新增，未改任何既有文件）。

### 2.1 两条路径的覆盖情况

**两条路径都覆盖**：
- **ConfigState 侧**（`_vertex_drift_issues`，`src/validator/output_coordinates.py:816`）：
  `test_configstate_side_negative_no_drift_when_vertices_match_snapshot`（阴性对照）+
  `test_configstate_side_reports_drift_when_start_vertex_is_rotated`（阳性，起笔点旋转）。
- **IDF 侧**（`_live_idf_vertex_drift_issues`，`:781`）：
  `test_idf_side_negative_no_drift_when_vertices_match_snapshot`（阴性对照）+
  `test_idf_side_reports_drift_when_start_vertex_is_rotated`（阳性）。
  用 `idf.newidfobject("BUILDINGSURFACE:DETAILED", ...)` 直接在一个新鲜 eppy IDF 上造顶点字段
  （`Vertex_i_Xcoordinate/Ycoordinate/Zcoordinate`），不经过完整 `ConverterManager` 流水线
  （与 `tests/test_output_coordinate_registry.py` 里 `_fresh_idf()` 的手法同源）。
- **另加 3 条经公开入口 `validate_output_coordinate_contract` 的接线锁**（证明两条私有函数确实被真
  实调用方接住，且互不遮蔽 —— 复现 `_live_idf_vertex_drift_issues` 自身 docstring 里
  BO-CR5 的理由「ConfigState 干净不代表 live IDF 没被转换器/原始片段注入改过」）：
  - `test_full_gate_negative_when_both_sides_match_snapshot`：两侧都对 ⇒ 门不报。
  - `test_full_gate_reports_live_idf_drift_even_when_configstate_matches`：ConfigState 侧干净、
    只有 live IDF 漂移 ⇒ 门仍报（证明 ConfigState 侧的"干净"不会把 IDF 侧的问题盖住）。
  - `test_full_gate_reports_configstate_drift_even_when_live_idf_matches`：反过来，只有 ConfigState
    侧漂移 ⇒ 门仍报（两条路径彼此独立生效）。

### 2.2 断言落点

全部落具体 check-id + 具体面名，不用「数量变了 / 不是 None」：
```python
drift = [i for i in issues if i.code == "VERTEX_FRAME_DRIFT"]
assert drift, ...
assert any("W1" in i.message and "vertices differ from the pre-E4 snapshot" in i.message
           for i in drift), drift
```

### 2.3 阳性用例的"最小漂移"设计

阳性测试用的漂移是**起笔点旋转**（`np.roll(_CANON, 1, axis=0)`）——同一个环、同一批点、同一绕向，
只是起点下标不同，是施工单 §2 明确要求覆盖的最小可能漂移形态（对应 F-13 `start_vertex_rotated` 同型）。

### 2.4 覆盖前状态核实

补锁前 `grep -rn "vertices differ from the pre-E4 snapshot" tests/*.py` 零命中，
与施工单「该门目前只有端到端实证、没有单元锁」的判断吻合（既有 `tests/test_f11_foundations_scope_and_loop_breaker.py`
只覆盖了「记录缺失」`missing from ConfigState` 这一支路径，未覆盖「顶点值漂移」这一支）。

---

## 3. neuter 自验

在 `/tmp/neuter_f13_wt`（一次性 detached worktree，`git worktree add --detach /tmp/neuter_f13_wt HEAD`）
里做，两次都**逐字节复原**（`git diff --stat` 改动前非空、`git checkout --` 后为空）。

### 3.1 任务一 neuter —— 实现挑错角

改动：`src/validator/data_model.py:1114`
```diff
- top_left_index = np.lexsort((sort_keys[:, 1], sort_keys[:, 0]))[0]
+ top_left_index = np.lexsort((sort_keys[:, 1], sort_keys[:, 0]))[-1]  # NEUTER: 挑右下角而非左上角
```

结果（`pytest tests/test_f13_kernel_canonical_vertex_order.py -v`）：
```
FAILED test_lock2_canonicalization_ceiling_top_left_and_outward
FAILED test_lock2_canonicalization_floor_top_left_and_outward
FAILED test_lock2_canonicalization_window_top_left_and_outward
FAILED test_lock2_canonicalization_vertical_wall_top_left_and_outward
4 failed, 4 passed in 9.04s
```
**4 条 lock2 全红，红在新补的手算断言那一行**（逐条核实，例如楼板：
`AssertionError: assert False` where `np.array_equal(array([4., 3., 0.]), array([0., 0., 0.]))`——
挑到的是错误角 `(4,3,0)` 而非手算值 `(0,0,0)`；天花、竖直墙、窗同理，均在
`assert np.array_equal(canonical[0], np.array([...]))` 这一行红，不是在自指断言那行）。
**手算断言确实变红**，不是"抄实现值"的假锁。其余 4 条（lock1/lock3/neuter 自身）不受影响，仍绿
——符合预期，因为它们不依赖 `top_left_corner_index` 挑哪个角（lock1/lock3 走的是内核自己产的
canonical 顺序 + gate①，两边用同一把被 neuter 的尺子，一起偏但形状仍自洽；neuter 测试本身检验的
是另一件事）。

复原：`git checkout -- src/validator/data_model.py`（diff 归零），复跑 8/8 全绿。

### 3.2 任务二 neuter —— 门恒不报

改动：`src/validator/output_coordinates.py` 两处比较改成 `if False:`
```diff
-        if actual != expected:
+        if False:  # NEUTER: 门恒不报
```
（`:807` IDF 侧 `_live_idf_vertex_drift_issues`）
```diff
-        if actual_vertices != rec.vertices:
+        if False:  # NEUTER: 门恒不报
```
（`:835` ConfigState 侧 `_vertex_drift_issues`）

结果（`pytest tests/test_f12_vertex_frame_drift_gate.py -v`）：
```
PASSED test_configstate_side_negative_no_drift_when_vertices_match_snapshot
FAILED test_configstate_side_reports_drift_when_start_vertex_is_rotated
PASSED test_idf_side_negative_no_drift_when_vertices_match_snapshot
FAILED test_idf_side_reports_drift_when_start_vertex_is_rotated
PASSED test_full_gate_negative_when_both_sides_match_snapshot
FAILED test_full_gate_reports_live_idf_drift_even_when_configstate_matches
FAILED test_full_gate_reports_configstate_drift_even_when_live_idf_matches
4 failed, 3 passed in 9.24s
```
**4 条阳性锁全红**（ConfigState 侧 1 条 + IDF 侧 1 条 + 两条接线锁），**3 条阴性对照仍绿**
（符合预期——阴性对照本就断言"不报"，门被 neuter 成恒不报后阴性对照观察不到差异，这是阴性对照
的正常行为，不是锁失效）。红的 4 条逐条落在新补的 `assert drift, ...` 这一行（`drift` 列表为空）。

复原：`git checkout -- src/validator/output_coordinates.py`（diff 归零），复跑 7/7 + 8/8 = 15/15 全绿。

清理：`git worktree remove /tmp/neuter_f13_wt --force`。

---

## 4. 全仓验收

```
$ python -m pytest -q
2262 passed, 10 xfailed, 209 warnings in 381.03s (0:06:21)
```
基线 **2255 passed / 10 xfailed / 0 failed**；本单净增 7 个测试函数（新文件
`tests/test_f12_vertex_frame_drift_gate.py`；`test_f13_kernel_canonical_vertex_order.py` 只在既有
3 个测试函数体内各加一条断言，未新增测试函数）⇒ **2255 + 7 = 2262 完全吻合，0 failed，零回归**。
（209 条 warnings 均为既有 `record_baseline.py` 的 `RuntimeWarning`，与本单无关，本单改动前后一致。）

---

## 5. 改动清单

- `tests/test_f13_kernel_canonical_vertex_order.py`：lock2 三条测试各加一条手算 `canonical[0]`
  断言 + 推导注释；不改任何既有断言、不改生产码。
- `tests/test_f12_vertex_frame_drift_gate.py`：新文件，7 个测试。
- 生产码（`src/`）：**零改动**（neuter 全部发生在 `/tmp` 一次性 worktree，已复原）。

---

## 6. 停下上报

本单未撞见事实与描述不符之处：施工单给出的楼板参照值 `[0,0,0]` 与独立推导结果一致；
三个面型的手算值与实现全部吻合；`VERTEX_FRAME_DRIFT` 门的两条私有函数结构上都可从单元层直接驱动
（无需改生产码签名）。**无需停下上报。**
