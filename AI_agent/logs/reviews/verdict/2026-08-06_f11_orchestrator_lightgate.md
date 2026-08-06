# orchestrator 轻门 · F-11：下游死循环 + foundations 阶段跑终态校验

- **日期**：2026-08-06 · **裁决**：**PASS（经一轮返工 r1）** · **施工席**：GLM-5.2（调查 + 施工 + 返工同席）
- **落库**：`4b87e9f`（修法）→ `966d667`（r1 补接线锁）

---

## 1. 缺陷（orchestrator 已独立复核）

| # | 事实 |
|---|---|
| 1 | 节点序列 `intake→material→zone→schedule→cross_ref_foundations→validate→intake→…` 每 ~16s 一圈**永不终止**；`surface`/`fenestration`/`hvac`/`people`/`lights` **一次没跑** |
| 2 | `cross_ref_foundations` 返回 **115 条** `VERTEX_FRAME_DRIFT: <面> in the snapshot is missing from ConfigState` |
| 3 | 根因 = **终态语义挂在非终态阶段**：`_vertex_drift_issues`（`src/validator/output_coordinates.py:794`）拿**终态 snapshot** 比对 foundations 阶段**还空**的 `config.surfaces` |
| 4 | ⭐ `cross_ref_foundations_node` 的 **docstring 自己写着** *"no constructions, surfaces, HVAC yet"* —— 作者知道这阶段没有面，后加的 E4 校验没顾上 |
| 5 | 放大器：`graph.py:52` 有错即短路到 validate ⇒ 永远到不了 `construction` |
| 6 | 循环三出口全封死：`MAX_RETRIES=0` 让重试成死代码 · `auto_approval` 有错必拒 · 错误消失需要 surfaces 而 surfaces 永远造不出来 |
| 7 | **触发条件 = 契约来源类型**：`accepted_correction` 强制带 snapshot（今晚 5_intakeoutput 首次产出）⇒ 触发；`legacy standalone` 无 snapshot（probe B，`snapshot_sha256: null`）⇒ 不触发 |

**⇒ 这个缺陷是被「变好」触发的**：5_intakeoutput 现在能产出正确绑定的契约（更强的行为），正是它把潜伏的时序缺陷照出来。**与 F-10 同族：被前面的墙遮蔽，谁也没走到过。**

## 2. 修法（两件成对）

- **A**：`validate_output_coordinate_contract` / `_output_coordinate_errors` 加 `include_vertex_drift`（**默认 True**），只门控第 6 步 `_vertex_drift_issues`；`cross_ref_foundations` 传 `False`，`cross_ref_complete`/`validate` 保持默认。
  **⭐ snapshot 字节哈希完整性子检查留在 flag 之外、永远跑** ⇒ 防篡改不受影响。步骤 1–5 不动。
- **B**：`auto_approval` 拒绝时 WARNING 打印全部错误（原先**全程零输出**）+ `InterruptLoopBreakerError` 确定性熔断（按**连续相同错误集**计数、签名排序顺序无关、干净 interrupt 不计数且重置、默认阈值 3）。
  **⛔ 刻意不给 `auto_approval` 加 `errors` 键** —— 那只会把死循环换成 intake 处硬崩（= 调查选项 A），与其自身调查结论一致。

## 3. ⛔ 轻门抓到的 MAJOR（返工 r1 已修）

**`test_foundations_path_skips_terminal_vertex_drift` 是一把假锁。**
它**自己传 `include_vertex_drift=False`** 去直调 validator，**从不经过 `cross_ref_foundations_node`**
⇒ 锁的是**机制**（参数管不管用），**不是接线**（foundations 到底传没传）。

**orchestrator 实测坐实**：把调用点的 `include_vertex_drift=False` 删掉（= **原样复原 F-11 本尊**）
⇒ 该文件 **8/8 依然全绿**。全仓唯一驱动该节点的 `test_output_coordinate_dispatch_guard.py:164`
喂的 state 无 snapshot/surfaces ⇒ 两种情况都不产 drift、也照不出来。

**⭐ 为什么施工席自己的四向 neuter 没抓到**：它 neuter 的是**机制**（函数内部），
orchestrator neuter 的是**接线**（调用点）。**方向不同才照得出来** ——
这是「独立 neuter 必须换个方向做」这条纪律第一次真正兑现价值。

**r1 修法**：新增 `test_foundations_node_binds_drift_skip_at_callsite` —— **真实驱动 `cross_ref_foundations_node`**、
喂真漂移 state、断言无 `VERTEX_FRAME_DRIFT`、**不手传 flag**（让节点自己决定传什么，那才是被保护的行为）。

## 4. orchestrator 独立验证

| 项 | 结果 |
|---|---|
| **独立全量** | **2234 passed / 10 xfailed / 0 红**（362.18s）；基线 2225 ⇒ **净增 9 锁零回归**。与施工方数字逐字一致 |
| **⭐ 决定性 neuter（orchestrator 自做）** | 删调用点 `include_vertex_drift=False` ⇒ **新接线锁精确变红**，报 `VERTEX_FRAME_DRIFT ... 'W1' ... missing from ConfigState`；**其余 8 把仍绿** ⇒ 锁定位准、不过宽。还原后 9/9 绿 |
| **亲核 diff** | 生产码 3 文件 +129/−4；`include_vertex_drift` 默认 True（新增调用点自动拿全量门，fail-safe 方向）；哈希完整性在 flag 外 |
| **真链路（施工席实测，orchestrator 复核日志）** | 图**单调前进** `intake→material→zone→schedule→cross_ref_foundations→construction→surface`，**整段只出现一次 `cross_ref_foundations`**（修复前每 16s 一次），零拒绝零熔断；**`surface` 跑完全部 14 区 ≈ 100 个面** —— 修复前**结构上永不可达** |

## 5. ⛔ 派工方（orchestrator）第 8 次出错

**验收 1 同时写了「`timeout ≤300s`」与「五个 subagent 都执行到」——对本负载客观不可同时满足**
（surface 用 pro 档跑 14 区 ≈ 4m10s，290s 超时恰在 surface 收尾时杀进程）。
**施工席处理完全正确**：如实报「1/5 节点执行到 + 死循环确证打破」，**未投机降档、未伪造**，
并指出其余四节点是 surface 的直系下游（`graph.py:103-108` 严格前向链、中间无门）⇒ **可达性已证、仅被时间预算截断**。

**⇒「停下/如实上报」计数更新为 8 次，8 次全是派工方的题错了。**
**新自检条目**：写验收条件时须检查**各条之间是否互相冲突**（此前只检查「单条是否可达」）。

## 6. 结转

- **⚠️ `MAX_RETRIES = 0` 未动**（`src/agent/_share.py:7`）：validate 的自动重试分支目前是**死代码**。
  本批靠熔断保证终止，**但"为什么把自动重试关成 0"未查** —— 登记待查。
- **五节点一次跑穿**：orchestrator 以放宽预算（`timeout 1500`）另跑一次真链路作为端到端主线证据，结果另记。
- **⭐ 治理教训（新）**：**neuter 必须同时覆盖「机制」与「接线」两个层面。**
  只 neuter 函数内部会漏掉「调用点没传对参数」这一整类 —— 而那恰恰是缺陷复发最常见的形态。
  **判别问法：把调用点改回缺陷形态，锁红不红？**
