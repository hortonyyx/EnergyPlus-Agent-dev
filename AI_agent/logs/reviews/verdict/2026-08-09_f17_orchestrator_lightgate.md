# orchestrator 轻门 · F-17 跨轴组件切角修复

- **日期**：2026-08-09
- **裁决**：✅ **PASS（无条件）**
- **被审**：Claude 侧 Sonnet 单席，派工单
  [`request/2026-08-09_f17_cross_axis_chamfer_fix_dispatch_claude.md`](../request/2026-08-09_f17_cross_axis_chamfer_fix_dispatch_claude.md)
- **施工席执行记录**：[`execution/2026-08-09_f17_cross_axis_fix_claude.md`](../execution/2026-08-09_f17_cross_axis_fix_claude.md)
- **基点**：`ee79b6c` · 基线 **2323 passed / 10 xfailed / 0 failed**

---

## 1. 独立全量（唯一权威门）

orchestrator 自己跑，`-n 8`（⛔ 非 `-n auto`），输出直接重定向、退出码单独落文件：

```
========== 2326 passed, 10 xfailed, 209 warnings in 404.50s (0:06:44) ==========
退出码 = 0
跑测时 envelope_transform.py sha256 = 604dc15f…（= 恢复后的树，非 neuter 态）
```

**2323 → 2326，净增 3、零回归、零红。**

## 2. 独立 neuter —— ⭐ **两格都换了方向**（施工席测过的两格不重复）

施工席测的是「复原算法」与「复原分类修法」两格（函数**内部**）。
按本项目纪律（**orchestrator 独立 neuter 必须换方向**），orchestrator 另测两格：

### 格 1 · **接线方向**（08-06 抓出假锁的那个方向）✅ 真锁

**不动 `_apply_components` 本身**，只把**调用点**（`:626`）改回「一次喂一个组件」——
这恰好复原 F-17 缺陷本尊，而函数内部一行未改：

```
2 failed, 29 passed
FAILED test_cross_axis_components_move_every_footprint_corner_without_chamfering
FAILED test_l_shape_footprint_with_cross_axis_components_preserves_notch
```

**恰好 Group A/B 转红 · 零连带**（Group C 与既有 `test_c2_b2b_envelope_transform` 全绿）。

⇒ 锁住的是「**跨轴组件必须一起喂**」这个行为，不只是函数内部实现。
⇒ 兑现 08-06 那条判别问法：**「把调用点改回缺陷形态，锁红不红？」—— 红。**

### 格 2 · **materialize 删除方向**（施工席主动登记的缺口）⛔ 缺口坐实

把 `_materialize_axis_splits` 改成恒等（= 有人「顺手把它删了」）：

```
全仓 2326 passed / 10 xfailed / 0 failed  ← 零测试转红
```

**缺口是全的：没有任何测试守着它。**

### neuter 卫生

改动前后 `sha256` 逐字节比对通过（`604dc15f…` 两次一致），`grep NEUTER` 零残留。
每次 neuter 落下后**先确认改动真的落进文件**再跑测（兑现 08-05 那条「正则命中 0 处的空操作拿到 22 绿」的教训）。

---

## 3. ⭐⭐ 轻门额外量到的（比「缺一把锁」严重）

给 `_materialize_axis_splits` 挂计数器，跑遍全部 envelope 相关测试
（`test_c2_b2b_envelope_transform` / `test_c2_b5_host_resolution` / `test_c2_b2_v3` /
`test_deterministic_core` / `test_f17_cross_axis_envelope`，152 passed）：

```
_materialize_axis_splits 被调用 : 101 次
其中真的插了点的调用            :   0 次
累计插入顶点数                  :   0 个
```

**⇒ 它在全部现有夹具上都是死代码。整套 T-junction / 图闭包机制
（`_floor_axis_edges` 的吸收环 + `_materialize_axis_splits`）从来没有被任何测试真正执行过** ——
101 次调用全部走的是「无事发生」路径。

### 定性（两条，都要说准）

1. **⛔ 这是继承的，不是本批引入的。** 夹具与该函数本批均未被动过，旧代码下同样 0 插入。
   **不记施工席的账**；施工席**主动登记了这个缺口**（执行记录 §8），属加分。
2. **⛔ 但派工单 §4 那条「不许删 `_materialize_axis_splits`」现在是纯文档约束、零机器验证。**
   这正是本项目栽过五次的形状（「规范写了、没有机器验证」/「声称在守其实没守」）。
   **且它正好处在 F-13 那个危险位置上**：全绿、看起来多余、实际在为 L/U 形的 T-junction 服务 ——
   F-13 那次就是 orchestrator 断言一段规范化「多余」并派工砍掉，拿到**三绿齐**而 76/79 面墙被 EnergyPlus 判错。

### 触发它的几何配方（orchestrator 已推出，供补锁时用）

`_materialize_axis_splits` 只在**区间端点严格落在某条 owner 边内部**时才插点。
现有夹具的组件区间恒**覆盖整条 footprint 边** ⇒ 无内部割点。
要触发，需要**同一轴线上两段不相连的 footprint 边**（如 U 形的两个凸出）
+ **一个跨越缺口的 cell**（其该轴边同时压住两段）⇒ `_floor_component_intervals` 产出
**两个不合并的区间** ⇒ 该 cell 边上出现内部割点 ⇒ materialize 真的插点。

---

## 4. 逐条核对派工单验收条件

| 条件 | 结果 |
|---|---|
| `tools/f17_repro.py` 不再抛 ValueError（真实产物 + 官方入口） | ✅ 施工席复跑 `[run] 没崩`；orchestrator 侧亦确认修复前抛、修复后不抛 |
| `tools/f17_matrix.py` 15 格全部 0 斜边 | ✅ |
| 全仓 ≥2323 / 0 failed、`-n 8`、以汇总行+退出码为准 | ✅ 2326 / 0 failed（orchestrator 独立复跑） |
| neuter 自验做过且如实记录 | ✅ 施工席两格 + orchestrator 另两格 |
| 执行记录落盘 | ✅ 221 行，含防假验证自检三问 |
| 根因修法 + 分类修法**一起交** | ✅ 两条都在同一份 diff 里 |
| 锁的夹具 footprint lo 侧 ≠ 0 | ✅ Group A `[0.12,14.88]×[0.12,7.88]`（逐字节照抄真实产物）· Group B `[0.12,10.0]×[0.12,7.88]` |
| 断言等于手算值 | ✅ 零处停留在「没抛异常 / 数量变了」 |
| 文件白名单 | ✅ 生产码仅 `envelope_transform.py`；未碰 prompt / nodes / `_BASE_SIGN` / 正交判据 / CLAUDE.md / plan.md |
| 未 commit / 未 push | ✅ |

## 5. 修法质量复核（orchestrator 读 diff，非采信报告）

- **相 2 的关键设计正确**：`original = list(point)` **冻结只读** vs `resolved = list(original)` **累加写入**，
  每个组件都测 `original` 从不测 `resolved` ⇒ 组件顺序无关，恰好恢复 legacy 由 bbox 表示免费得到的跨轴独立性。
- **`moved` 审计语义合理**：一个角点被 x/y 各命中一次 ⇒ 该 ref 出现两次；
  Group A 直接把 `moved["floor_vertex_refs"].count("f1:0") == 2` **当断言**用来证明「两个分量各命中一次」——
  这是把内部审计变成可观测行为断言的好用法。
- **分类修法落点正确**：`EnvelopeTransformRejected("correction.envelope_cell_ring_valid", …)`
  被 `apply_v3_envelope_transaction` 既有的 `except` 接住 ⇒ 归档重抽路径；
  并同步把新 gate id 挂进 `_conflict_shape` 的 `unsupported_geometry / topology_identity` 桶（与同族 gate 一致）。
- **docstring 写明机理并指向调查报告** —— 不是「声称在守」的空注释，是可核对的。

---

## 6. ⭐ 施工席自陈的一次假验证事故（登记为通用教训）

第一次跑测用了 `python -m pytest -n 8 2>&1 | tee logfile | head -20`：
`head -20` 读满 20 行后关闭 stdin ⇒ `tee` 写第 21 行时收到 SIGPIPE 提前终止 ⇒ **连带 pytest 被打断**；
日志永久停在 33%，而后台通知里的「退出码 0」**其实是 `head` 的退出码，不是 pytest 的**。

施工席自己发现（日志不完整 + `ps` 确认进程已死）并改用
`pytest … > logfile 2>&1; echo $? > exitcode_file` 重跑。

⇒ **这是「以退出码为准」这条纪律的一个新变种：管道里的退出码来自错误的那个命令。**
⇒ **新纪律：跑权威门时输出直接重定向到文件、退出码单独落一个只属于该命令的文件，
⛔ 中间不许接任何下游管道（`tee`/`head`/`grep` 都可能截断或改写退出码）。**
（与 08-08 记的「`-n auto` 静默 OOM，外观与还在跑难分」并列：**权威门的观测通道本身必须是可信的**。）

---

## 7. 结转（⛔ 不阻塞本批落库）

| 事项 | 状态 |
|---|---|
| **T-junction 锁（materialize 零覆盖）** | ⏸ **待用户拍板是否本轮补**。缺口继承自旧代码、不影响 F-17 本身正确性（两把锁两个方向都验过），但那条 ⛔ 约束目前零机器验证。配方见 §3 |
| **多层 / 更复杂形态的跨轴** | ⏸ Group A 夹具是单层（照抄真实产物 F1）；真实产物两层现象一致但未单独锁 |
| **落盘产物官方重放姿势** | ⏸ 另开小单（用户 08-09 定：不与 F-17 绑定） |
| **F-17 真链路验收** | ⏸ 未做（要烧 LLM 钱）。派工单明确不要求施工席跑；**是否跑由用户定** |
