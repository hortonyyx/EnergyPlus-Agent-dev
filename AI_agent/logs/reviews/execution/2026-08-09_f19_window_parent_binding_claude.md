# 执行日志 · F-19：`kernel.window_parent_binding` 恒红修复 + 补锁

- **席位**：Claude 侧 Sonnet（执行档）· 通道 = Agent 子代理
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `0efc775`
- **派工单**：[`2026-08-09_f19_window_parent_binding_fix_dispatch_claude.md`](../request/2026-08-09_f19_window_parent_binding_fix_dispatch_claude.md)
- **调查全档（未重做）**：[`2026-08-09_f19_window_parent_binding/README.md`](../../experiments/2026-08-09_f19_window_parent_binding/README.md)

---

## §0. 防假验证自检（开工前作答）

**Q1：验收路径真的会执行到 `kernel.py:362`（改动落地后，同一行比较逻辑现位于 `:402`）那一行吗？**

会。逐层核实：
- `_window_parent_binding` 只在 `bg.geometry_contract == "c2_b5_v1"` **且** `proof is not None` 时才走到顶点比较（`kernel.py:255-261`）。
- `_bundle()`（测试夹具，`tests/test_c2_b5_parent_and_verts.py:151-265`）用 `CorrectedGeometryV3`（`schema_version="3"`）调用真实的
  `build_geometry(result.geom, capability_profile="orthogonal_polygon", window_host_proof=proof)`。
  `build_geometry`（`build.py:200-222`）内部：`is_b5 = str(geom.schema_version) == "3"` → `True`；
  `out = BuildingGeometry(geometry_contract="c2_b5_v1" if is_b5 else "legacy")` → `"c2_b5_v1"`；`proof` 非 `None`。
  两个条件都满足 ⇒ **锁的夹具真的会执行到顶点比较那一行**。
- 生产侧同理已由调查全档实测坐实：`run_2026-08-09_f18_e2e_verify` 在真实 v3 + 真实 proof 的
  `2_modelling` 段撞到 `kernel.window_parent_binding: 15 built window parent-binding defect(s)`，
  offenders reason 全部是 `built_vertices` —— 即生产路径与测试路径命中的是同一行代码。

**Q2：锁的夹具，`built.verts` 是不是真的经过了 `build_geometry` 的 `_canonicalize_bg_vertices`？**

是（前提是使用 `_bundle()` 产出的 `bundle.bg`，**不是**手搓 `BuildingGeometry(...)`）。
`build_geometry` 在 `return out` 前无条件调用 `_canonicalize_bg_vertices(out)`（`build.py:268`），
该函数对 `out.windows` 逐个用 `canonicalize_ring_vertices` 规范化（`build.py:80-85`）。
`_bundle()` 的 `bg=bg` 字段就是这次真实调用的返回值（`test_c2_b5_parent_and_verts.py:253-257,263`）。
⇒ **L-1/L-2/L-4 全部使用 `_bundle()` 产出的 `bundle.bg`，不使用手搓 `BuildingGeometry(...)`**——
本文件里那些手搓 `BuildingGeometry(...)` 的用例（`test_kernel_b5_contract_without_proof_fails_closed` 等）
本来就是在测「契约/proof 缺失」这类与顶点规范化无关的失败模式，未被本次改动触碰。

**Q3：怎么证明「不加修法，这条锁是红的」？**

两条独立证据（均已实测，见 §4 L-2 与 neuter 表）：
1. **机械回放**（`test_f19_l2_gate_would_fail_without_fresh_side_canonicalization`）：
   独立调用未规范化的 `window_verts_on_line(...)`（用 `resolution` 自己存的 p1/p2/parameter_interval/z_interval/normal），
   与 `bundle.bg.windows[0].verts`（已规范化）做逐位比较，断言二者**确实不同**——这就是"OLD 比较法在这份夹具上会挂"的机械证明，
   在补锁 **之前** 用一次性脚本对四个朝面（South/North/East/West）都验证过（见下方"实测记录"）。
2. **neuter 自查**（见 §4 表格）：在 `/tmp` worktree 里把 `kernel.py` 的规范化那 6 行摘掉，
   `test_c2_b5_parent_and_verts.py` 里全部 F-19 相关的锁（L-1×4 + L-2 + L-3 + L-4）**7 个全部转红**，
   其余 52 个无关测试保持绿色。

---

## 1. 改动清单

### 1.1 `src/validator/checks/kernel.py`（生产码，唯一功能性改动）

- **模块级新增 import**：`from src.validator.data_model import canonicalize_ring_vertices`
  （紧跟既有 `from src.validator.checks.schema import ...`）。
  已核实零循环导入风险：`data_model.py` 的导入图不触及 `src.validator.checks` 或 `src.agent.geometry`；
  `build.py` 已经在模块级这样 import 同一个函数，先例成立。
- **`_window_parent_binding` 内部的 scoped import** 扩了一个名字：
  `from src.agent.geometry.modelling import (SegmentLine2D, _v3_parent_candidates, window_verts_on_line)`
  → 加了 `_newell`。用的是 `modelling.py` 自己的 `_newell`（`build.py` 的 `_canonicalize_bg_vertices`
  用的就是这一个），**没有用** `kernel.py` 模块级自带的另一份 `_newell`（该文件本来就有一份局部 `_newell`，
  两者数学上等价——`canonicalize_ring_vertices` 内部会重新单位化，magnitude 不影响结果——但为了不留"两份实现是否真的等价"
  这种需要读者自己论证的疑点，选用了与 `build.py` 完全同一个函数，做到"同一份规范化"没有歧义）。
- **核心修法**（`_window_parent_binding` 内，原 `kernel.py:362` 一行，现为 `try/except/else` 块的 `else` 分支）：
  在比较之前，把 `fresh_vertices`（`window_verts_on_line` 的原始未规范化输出）也过一遍
  `canonicalize_ring_vertices`，用的是它自己的自洽 Newell 法向（`_newell(fresh_vertices)`），
  与 `_canonicalize_bg_vertices` 对 `built` 一侧的处理方式逐字同构（同一函数、同一"自己的法向"取法、
  同一近零退化保护 `norm < 1e-9` 则跳过）。之后仍是原来的 `if built.verts != fresh_vertices:` 精确比较，
  **未加任何容差、未加任何"等价类"判断**。

  **为什么这么改**：调查已坐实根因 = `built.verts` 走了 F-13 加的规范化、`fresh_vertices` 没走，
  纯顺序（起笔点）差异被逐位比较放大成"顶点被改坏"。派工单明确要求复算侧走**同一份** `canonicalize_ring_vertices`，
  ⛔ 不许另写算法、⛔ 不许改 `build.py`、⛔ 不许加循环旋转豁免。本改动只加了 6 行功能代码（+ 注释），
  三条禁令都遵守：用的是唯一共享函数，`build.py` 一字未动，比较仍是精确 `!=`（不是"忽略起点"或"忽略绕向"）。

  **为什么这样做仍能挡住真正有害的绕向反转**：`canonicalize_ring_vertices` 只按"给定的法向"重排起点+绕向一致性，
  **不会翻转一个本来就错的绕向**（`_canonicalize_bg_vertices` 自己的 docstring 就是这么保证的——它"cannot flip a
  winding that is already correct"）。所以如果 `built.verts` 因为上游 bug 真的绕向反了，规范化后仍然反着，
  而 `fresh_vertices` 是按独立验证过的 `resolution.segment_outward_normal`（真值）定向的，二者规范化后仍不相等
  ⇒ 仍然 fail。L-4 把这条机械验证了一遍（见 §4）。

### 1.2 `tests/test_c2_b5_parent_and_verts.py`（测试文件，四把新/改锁）

替换了原来紧贴 `test_kernel_fresh_recompute_rejects_built_vertex_tamper`（原 788-800 行，即派工单说的"798 那条"）
前后的区域，新增/改动共 6 个测试函数（详见 §4）。**未改动**该文件里其余 52 个既有测试。
**未新增任何 import**（`window_verts_on_line` / `SegmentLine2D` / `check_kernel` / `deepcopy` 等本文件顶部早已导入）。

---

## 2. §2.3 排查结果（谁还在拿未规范化顶点跟 `build_geometry` 输出比）

**判据**：对每处顶点级比较问两件事 —— ①比较的其中一侧是不是 `build_geometry` 返回值里已经跑过
`_canonicalize_bg_vertices` 的 `bg.surfaces[*].verts` / `bg.windows[*].verts`（或从它直接序列化而来）？
②另一侧是不是一次**独立**的、**没有**过同一规范化的"新鲜"重算？③比较用的是不是 `==`/`!=`/逐位比？
三条同时成立才算命中。

**覆盖范围**：`src/validator/`、`src/agent/geometry/`、`src/agent/`（含 `output_coordinates.py` 全部漂移门 + `judge/`）、`tests/`。
搜索方式：`grep` 全部 `.verts`/`vertices` 的 `==`/`!=` 比较 + 全部 `window_verts_on_line(` 调用点交叉核对
+ 全部 `canonicalize_ring_vertices(`/`top_left_corner_index(` 调用点（确认目前只有 `build.py:78/84` 两处在用，
加上 `data_model.py` 自己的 `GeometrySchema` 委托）。

| 位置 | 比什么 | 判定 | 理由 |
|---|---|---|---|
| **`src/validator/checks/kernel.py:395`（原 362）** | `built.verts`（规范化）vs `fresh_vertices`（原始） | ✅ **命中 = F-19 本体** | 本次已修 |
| `src/agent/geometry/modelling.py:831`（`attach_windows_v3` 内） | `verts`（`window_verts_on_line` 现算）vs `record_verts`（来自 `resolution.clamped_vertices`） | ⛔ 未命中 | `attach_windows_v3` 在 `build_geometry` 里**先于** `_canonicalize_bg_vertices` 执行（`build.py:240-247` 早于 `:268`），此刻**两侧都是未规范化空间**。`record_verts` 追到源头（`window_host.py:955-965`）也是同一个未规范化 `window_verts_on_line` 用**逐字保存**的输入参数算出来的——两次调用同一纯函数、同一组存量参数值，理论上位对位相等，这是纯正的"篡改自检"（tamper check），不是"规范化 vs 未规范化"错配。既不涉及 `build_geometry` 的规范化输出，也不是本类 bug。 |
| `src/agent/correction/window_host.py:610-660`（`window_host_claim_issues`，F-18 那道自检） | `fresh_vertices`（现算）vs `declared_vertices`（`resolution.clamped_vertices`） | ⛔ 未命中 | 同样发生在 correction 阶段、`build_geometry` 还没跑，两侧都在未规范化空间；且已经是 F-18 修过的**容差**比较（`_same_resolution_representation_close`），不是精确 `!=`，与本类 bug（规范化缺口）不同族。 |
| `src/validator/output_coordinates.py:816` `_vertex_drift_issues`（E4 层 A：ConfigState vs 冻结快照） | 两侧都读 `bg.surfaces`/`bg.windows`，均在 `_canonicalize_bg_vertices` **之后**捕获（`build.py` F-13 注释明确点名 `serialize_geometry`/`build_output_coordinate_snapshot` 是"两个下游消费者"，都读同一份已规范化输出） | ⛔ 未命中 | 规范化 vs 规范化，且额外 `round(...,2)` 吸收浮点噪声。 |
| `src/validator/output_coordinates.py:781` `_live_idf_vertex_drift_issues`（E4 层 B：写盘 IDF vs 同一份冻结快照） | 快照侧同上（规范化）；IDF 侧的顺序来自 `GeometrySchema.validate_points_sorting`，F-13 后**委托给同一个** `canonicalize_ring_vertices`/`top_left_corner_index`（`data_model.py:1338/1363`），对已规范化输入是恒等变换 | ⛔ 未命中（标准路径下） | **登记一条未证实的理论缺口，非命中**：若存在绕过 `GeometrySchema` 写盘的"原始片段注入"路径（`validate_output_coordinate_contract` 的 docstring 提到过这个可能性），该路径写入的顶点可能不经过规范化。本次未找到任何生产代码走这条路径写 `BuildingSurface:Detailed`/`FenestrationSurface:Detailed`，**只登记，不当命中**，需要独立调查才能坐实或排除。 |
| `src/agent/geometry/specs.py:354` `check_geometry_specs_consistency` | 两份"重新序列化"都直接从同一个 `bg` 对象现算（`building_geometry_dict(bg,...)` / `serialize_geometry(bg,...)`），不是独立的几何重算 | ⛔ 未命中 | 比的是"同一个已规范化对象的两种序列化是否互相一致"，不存在规范化/未规范化的落差。 |
| `src/agent/judge/`（含 `opening_claim_score.py`） | — | ⛔ 未命中 | `grep` 全目录零个 `.verts`/`window_verts_on_line`/`canonicalize_ring_vertices` 命中。 |
| `tests/` 里其余用到 `window_verts_on_line`/`canonicalize_ring_vertices` 的文件 | `test_f13_kernel_canonical_vertex_order.py`、`test_f18_window_host_float_tolerance.py` | ⛔ 未命中 | 前者是 F-13 规范化机制本身的单元测试（测的是函数，不是消费方比较）；后者是 F-18 已修过的容差比较（同上，另一个阶段、另一个已知类别）。 |

**结论：本次机械排查 0 个新命中**（除 F-19 本体外）。命中项按纪律**只登记、不顺手改**——本次实际排查结果是
"排查完的清单里只有 F-19 自己算命中"，故无其余项需要登记为"未改的命中"。唯一保留的开放问题是
`_live_idf_vertex_drift_issues` 的原始片段注入理论缺口，已如实标注为"未证实、需要独立调查"，不计入命中数、
不在本次范围内处理（超出 F-19）。

**`src/agent/geometry/` 逐文件核对完整性**（该目录派工单点名必查）：`adjacency.py`、`build.py`、`capability.py`、
`modelling.py`、`specs.py`、`split_pairing.py`、`to_idf.py`、`__init__.py` 共 8 个源文件全部 `grep` 过
（`.verts`/`vertices` 的 `==`/`!=`、`window_verts_on_line`、`canonicalize_ring_vertices`），
除 `build.py`（规范化的定义处）与 `modelling.py`（表 2 中已判定"未命中"的那处）外，其余 6 个文件零匹配。

---

## 3. L-1…L-4 锁清单

全部新增/改动的测试都在 `tests/test_c2_b5_parent_and_verts.py`，紧接在原
`test_correction_validator_rejects_evidence_different_from_proof_artifact` 之后：

- **L-1** `test_f19_l1_gate_passes_on_real_build_geometry_output`（`@pytest.mark.parametrize("facade", [South, North, East, West])`，4 个用例）：
  用 `_bundle()`（真实 `build_geometry` 输出）在四个朝面上分别断言 `kernel.window_parent_binding` 的
  `status.value == "pass"`。这是此前 7 条断言里**唯一**方向的正向锁——此前完全不存在。
- **L-2** `test_f19_l2_gate_would_fail_without_fresh_side_canonicalization`：
  先独立重放"未规范化"版本的比较（`window_verts_on_line` 原始输出 vs `bundle.bg.windows[0].verts`），
  断言二者**确实不相等**（自证前提——若这份夹具凑巧不能分辨，这一步会大声报错，不会静默退化成空锁）；
  再断言真实（已修复）门 `pass`。
- **L-3** `test_kernel_fresh_recompute_rejects_built_vertex_tamper`（原"798"，就地改写）：
  补上"先断言干净 bundle `pass`"的前提检查，再做原有的"改坏顶点 ⇒ `fail` 且 reason 含 `built_vertices`"。
  这把此前的假锁改成了真的锁到"顶点被改坏"这件事本身。
- **L-4** `test_f19_l4_reversed_winding_still_caught`：
  把 `bundle.bg.windows[0].verts` 整体倒序（模拟真正有害的绕向反转），断言门仍然 `fail` 且 reason 含 `built_vertices`。

### neuter 自查表（全部在 `/tmp` 的 git worktree 副本里做，工作树全程未改动）

隔离方式：`git worktree add --detach <scratchpad>/f19_neuter_worktree HEAD`（`HEAD=0efc775`，与工作树完全独立的
detached checkout，共享 `.git` 对象库、不占用额外磁盘），把本次 diff `git apply` 进去后再逐条 neuter。
每次 neuter 前后都用 `grep` 确认改动真的落地（非空操作），全部记录见下：

| # | neuter 内容 | 预期 | 实测结果 | 连带 |
|---|---|---|---|---|
| 1 | 摘掉 `kernel.py` 里新加的规范化 6 行，还原成裸 `if built.verts != fresh_vertices:` | 派工单点名 L-1/L-2 应转红 | **7 个全部转红**：L-1×4（South/North/East/West）+ L-2 + L-3 + L-4 | **零连带**——该文件其余 52 个既有测试全部保持绿色 |
| 2 | 把 L-3（"798"）的 mutation 行 `broken.windows[0].verts[0] = (9.0, 9.0, 9.0)` 注释掉（"恢复 798 原样"） | 派工单点名 L-3 应转红 | **恰好 1 个转红**：`test_kernel_fresh_recompute_rejects_built_vertex_tamper` | **零连带**——其余 58 个（含 L-1×4/L-2/L-4）保持绿色 |
| 3a | 给门加"循环旋转等价"豁免的**危险实现**（`frozenset(built.verts) != frozenset(fresh_vertices)`，即完全无视顺序，不只是无视起点） | 派工单点名 L-4 应转红 | **恰好 1 个转红**：`test_f19_l4_reversed_winding_still_caught` | **零连带**——其余 58 个保持绿色 |
| 3b | 给门加"循环旋转等价"的**保方向实现**（只认"同绕向的任意起点旋转"，用双倍列表滑窗判定，不吞并绕向反转） | （补充实测，派工单未点名） | **0 个转红**，59 全绿 | 见下方说明 |

**3b 的诚实说明（不回避这个结果）**：一个"只认旋转、不认绕向反转"的宽松比较，**不会**让 L-4 转红——
这在数学上是预期的：对一个非对称的矩形环，把它整体倒序后得到的序列，通用地**不是**它自己任何一个同向旋转
（因为倒序同时改变了"从哪个点起"和"往哪个方向走"两件事，而单纯旋转只改变起点）。本次已用真实产物的坐标手算验证过这一点
（四个朝面全部验证：倒序结果都不在四个旋转候选之中）。**这不代表 L-4 没用**——它准确地挡住了派工单点名、
且历史上真实出现过的危险实现（3a 那种"干脆不比较顺序"的偷懒写法，正是这次 F-19 bug 本身"起点漂移"教训之后
最容易被人重新引入的"过度修正"），只是不能宣称它能分辨"所有形式的循环旋转豁免"——它分辨的是**结果**
（绕向反转必须仍然 fail），不是某个特定的"坏实现写法"。这个边界已经写进 L-4 的 docstring。

**清理**：所有 neuter 都已在 worktree 副本内逐条撤销，最终状态与本次真实 diff 逐字节一致
（`diff <(git show HEAD:src/validator/checks/kernel.py) <worktree>/src/validator/checks/kernel.py`
只显示本次预期新增的行，无其它差异）；worktree 已在收尾时 `git worktree remove` 清理。

---

## 4. 跑测记录

### 4.1 单文件（`tests/test_c2_b5_parent_and_verts.py`）

- 改动前（仅确认基线）：`53 passed in 9.36s`
- 改动后：`59 passed in 9.27s`（53 − 1 原地改写的 L-3 + 4 个 L-1 参数化用例 + L-2 + L-4 = 59，对得上）

### 4.2 受影响子集（`affected_tests.py`）

跑测声明（`affected_tests.py --changed src/validator/checks/kernel.py tests/test_c2_b5_parent_and_verts.py`）：
`SCOPE: SUBSET`，122 个测试文件（因 `kernel.py` 是被广泛依赖的枢纽模块——`check_kernel`/`_window_parent_binding`
被 judge/output_coordinates/gt/tarch_converter 等大量测试直接或间接 import——子集本身已接近全仓规模）。

命令：
```
python -m pytest -p no:cacheprovider -q tests/test_a1_fenestration_multiplier_not_exposed.py ... (122 files) ... -n 8
```

**结果：`2281 passed, 10 xfailed, 191 warnings in 520.48s (0:08:40)`，退出码 0。**
（输出直接重定向到文件、退出码单独落文件，中间未接任何管道，遵守跑测纪律。）

### 4.3 全仓（交付前，权威）

命令：`python -m pytest -p no:cacheprovider -q -n 8 > run.log 2>&1; echo $? > run.exitcode`（未用 `-n auto`，
输出与退出码分别落两个独立文件，中间未接任何管道）。

**原始汇总行**：
```
2345 passed, 10 xfailed, 209 warnings in 459.74s (0:07:39)
```
**退出码：`0`**

**对账基线**：派工单给的全仓基线 = `2339 passed / 10 xfailed / 0 failed`。
本次改动净增 6 个测试（该文件 53 → 59：+4 个 L-1 参数化用例 + L-2 + L-4，L-3 原地改写不增减数量）。
`2339 + 6 = 2345`，与实测汇总行**逐字吻合**。**xfailed 数量 10 → 10 不变，0 failed 保持。⇒ 零回归。**

---

## 5. 审阅需求（review-ask）

以下是本次施工中做过判断取舍、或自认没有 100% 把握的地方，如实列出：

1. **`_newell` 选用哪一份**：`kernel.py` 模块级本来就有自己的一份 `_newell`（未规范化、给该文件其余检查用，
   如 `_normals`），而我在 `_window_parent_binding` 内部改用 scoped import 引入 `modelling.py` 的那一份
   （`build.py` 的 `_canonicalize_bg_vertices` 用的正是这一份），刻意让它在函数内**局部遮蔽**同名的模块级名字。
   两份 `_newell` 数学上等价（`canonicalize_ring_vertices` 内部会重新单位化，量级不影响排序结果），
   但我判断"用同一个函数对象、不靠等价性论证"更稳妥，故选了后者，并加了行内注释解释这处遮蔽。
   如果评审认为局部遮蔽同名模块级标识符本身是代码异味、宁可接受"两份数学等价实现"的说法，这是一个可以反过来改的点。
2. **§2.3 排查的方法论边界**：排查手段是 `grep` 文本匹配（`.verts`/`vertices` 的 `==`/`!=`
   + 交叉核对全部 `window_verts_on_line`/`canonicalize_ring_vertices` 调用点），双向交叉验证降低了漏判概率，
   但**不是**形式化的穷尽证明——如果哪处比较是通过自定义 `__eq__`、或先转成 JSON 字符串再比、或包一层不带
   "verts"/"vertices" 字样的 helper 函数名做的，这次 grep 扫不到。目前没有证据这种情况存在，但没法排除到 100%。
3. **`_live_idf_vertex_drift_issues` 的原始片段注入理论缺口**（表格已登记为"未证实、非命中"）：
   `validate_output_coordinate_contract` 的 docstring 提到过"raw-fragment injection"这个可能性
   （不完全信任 ConfigState、要拿写盘的真实 IDF 核对），如果这类注入路径确实存在且真的绕过了
   `GeometrySchema.validate_points_sorting`，该处比较理论上可能重演一次"规范化 vs 未规范化"型的假阳性。
   本次未找到任何生产代码走这条路径写窗/墙顶点，按纪律**只登记不深挖**（深挖会超出 F-19 范围）。
4. **L-2 只在 South 朝面上锁，没有像 L-1 一样四朝面参数化**：写锁前我用一次性脚本独立验证过四个朝面
   "未规范化比较确实会挂"这条前提对全部朝面都成立，但落进代码的锁只挑了 South 一个。判断依据是
   L-1 已经四朝面覆盖了"pass"方向、L-2 的职责是把"自证前提"这个模式立住，一个朝面足以证明模式本身有效，
   四个朝面会是纯重复。如果评审认为这里也该参数化以防未来只有非 South 朝面才复现的边角情形，可以补。
5. **`modelling.py:831`（`attach_windows_v3` 内 `verts != record_verts`）判定为"未命中"这一条，
   是本次排查里论证链条最长的一条**（§2.3 表格）：结论依赖"两次调用同一个纯函数、且输入值逐字段来自
   `resolution` 存量字段，即便中间经过一次 JSON 序列化/反序列化（`WindowHostsArtifactV1.model_dump_json`
   → 校验环节的 `_reverify_window_host_proof`/`_proof_parts`），Python 的 float↔JSON 往返本身无损"这条推理。
   我用真实产物做过侧面印证（`_bundle()` 全链路跑完后 built vs 规范化 fresh **逐位精确相等，不需要任何容差**，
   如果这条 JSON 往返真的丢过精度，这个精确相等会不成立）——但这不是针对
   `attach_windows_v3` 那处比较本身的直接测量，是间接推论。如果评审想要更硬的证据，可以在
   `attach_windows_v3` 内加一条临时探针直接打印两侧数值对比，本次未做（超出 F-19 范围，且现有证据链已经足够支持
   "非命中"这个判断）。

⚠️ 以上五条均为"做了判断、认为站得住，但愿意接受反驳"的性质，不是已知缺陷。除此之外没有其它不确定点。

---

## 6. 环境说明（非本次改动，如实记录）

收尾核对 `git status` 时发现 `AI_agent/plan.md` 与 `AI_agent/proposals/f9_route2_evidence_citation_design.md`
显示为已修改（+92/+39 行）。**本次会话全程未对这两个文件调用过任何写工具**（逐一核对本会话的工具调用记录确认）；
两文件的磁盘修改时间也早于本次对 `kernel.py`/测试文件的修改时间。按硬约束「不动 `AI_agent/` 下的管理文档」，
本次交付**不包含**这两个文件的任何改动——如实登记，供 orchestrator 核对是否为并发的另一侧工作。
