# 派工单 · F-18：窗宿主自洽门用浮点精确相等，误判真实产物为「被篡改」

- **日期**：2026-08-09
- **席位**：Claude 侧 Sonnet（单席）
- **性质**：判据修正（**不是几何修法**）+ 锁。**不碰任何 prompt、不碰下游节点、不改几何。**
- **基点**：`61a30c7`（分支 `6.15_ValidationArchM0toM4`）· 基线 **2326 passed / 10 xfailed / 0 failed**
- **调查全档（必读）**：[`logs/experiments/2026-08-09_f18_window_host_exact_float_gate/README.md`](../../experiments/2026-08-09_f18_window_host_exact_float_gate/README.md)

---

## 0. ⛔ 第一步：防假验证自检（动手前先做）

1. 我要改的判据在 `src/agent/correction/window_host.py:576-613`（`window_host_claim_issues`）。
   **我的验收路径真的会执行到它吗？** 提示：它由 `recompute_window_host_claims`（`:1017`）调用，
   而后者由 `stage_runner.record`（`stage_runner.py:299`）在**写入侧独立复验**时调用。
   夹具若直接调 `resolve_window_hosts` 而不过 `window_host_claim_issues`，就没经过被改的代码。
2. 我的锁如果**把修法整个还原**，会不会转红？
3. 我断言的是**具体数值行为**，还是「没抛异常」？

---

## 1. 根因（已实测坐实，⛔ 不是推断）

`window_host.py:596-600`：

```python
projected = (q0[0], q1[0]) if dy == 0 else (q0[1], q1[1])
lo = projected[0] if projected[0] < projected[1] else projected[1]
hi = projected[1] if projected[0] < projected[1] else projected[0]
if (lo, hi) != (resolution.clamped_span.lo, resolution.clamped_span.hi):
    raise ValueError("world span")
```

`q0/q1 = line.point_at(t)`（即 `p1 + t*(p2-p1)`），而 `clamped_span` 由解析器**另一条路**算出并存下。
**两条不同计算路径 + 浮点精确相等比较。**

实测（真实产物 `run_2026-08-09_f17_e2e_verify`，15 个窗）：

```
W_F1_SE  重算 11.359999999999998  vs 声明 11.36   差 -1.8e-15
W_F1_NW  重算  1.2400000000000002 vs 声明  1.24   差 +2.2e-16
W_F2_NW  重算  1.9499999999999993 vs 声明  1.95   差 -6.7e-16
… 共 6 个窗失败，9 个逐位相同
```

⇒ **1–4 个 ULP 的末位噪声，不是几何错。** 后果：抛
`invariant_no_geometry_commit` 裸异常 ⇒ **不归档、直接终止整条 flow**。

**⭐ 最关键的事实**：项目**早就有**为这个量准备的容差
`window_host_span_epsilon_m = 1.0e-9`（`src/configs/correction.yaml:98`），
**在同一个文件里被用了 11 次**，其中一处就在失败那道检查**上面 14 行**（`:562`）。
实测噪声比它低**六个数量级**。⇒ **不是缺容差，是这道门没用。**

---

## 2. 要做的事

### 2.1 主修法

把这道自洽门的「相等」从**逐位**改为**项目容差内**（`tolerances.window_host_span_epsilon_m`）。

### 2.2 ⛔ 同一个 try 块里另外两处**同族**的精确相等比较，必须一并处理

- `if declared_endpoints != (q0, q1)`（`:594`）
- `if fresh_vertices != declared_vertices`（`:609`）

它们目前没报，但**是同一枚地雷**：同样是「两条算路 + 精确相等」。
⛔ **只修一处 ⇒ 下一份真实产物就在另外两处炸**（本项目在 F-15② 上刚吃过这个亏：
「只统一了顶层清单、嵌套那层原样留着同一个病」）。

顶点比较涉及 z 与法向，选容差时注意量纲：**平面用 `window_host_span_epsilon_m`，
若需要另一个量纲请用 `window_host_plane_epsilon_m`（同为 1e-9）**，
⛔ 不许自己新造常量、不许硬编码字面量。

---

## 3. ⛔ 三条硬约束

1. **⛔ 不许删掉这道门、也不许降级为 advisory。** 它是 anti-tamper（`resolver_output_tampered`），
   防的是解析器输出被伪造。**要保留防篡改语义，只把「相等」的定义从「逐位」换成「容差内」。**
2. **⛔ 不许改这道门失败时的出口语义。** `invariant_no_geometry_commit` 裸抛是
   **F-9 的有意设计**（不变量违反必须硬崩、不得静默归档重抽）。
   **该改的是判据，不是崩的方式。**
3. **⛔ 不许动任何几何计算。** 几何是对的（精度 1e-15 m）。这单只改「怎么比」。

---

## 4. 必须交付的锁（形态写死）

1. **真实形态锁（核心）**：夹具的窗跨度**必须用二进制不可精确表示的十进制值**
   （`11.36` / `1.24` / `2.19` / `3.64` 这类）。
   ⛔ **不许用 `0/4/10/5` 这类整齐数字** —— **全仓 2326 绿之所以漏掉这个 bug，
   正是因为现有夹具的跨度全是整齐数字（二进制可精确表示）**，这是本单的命门。
   断言：这样的产物**能通过** `window_host_claim_issues` / `recompute_window_host_claims`。
2. **⭐ 反向锁（防放水，必须有）**：人为把 `clamped_span` 挪 **1e-6 m**
   （远大于 1e-9 容差、远小于任何几何意义）⇒ **必须仍被拦下**。
   ⇒ 证明防篡改能力没被放宽。
   **⛔ 只证明「现在能过」不算数** —— 呼应本项目纪律「恒等锁 ≠ 正确性锁」：
   必须同时证明**该拦的还拦得住**。
3. **另两处同族比较各配一把**（端点 / 顶点），形态同上（真实形态过 + 挪动量被拦）。
4. **neuter 自验**：把判据改回 `!=`，上述「真实形态锁」必须转红；恢复后全绿。

---

## 5. 验收条件

- [ ] 用真实产物离线复跑 `AI_agent/logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/tools/f18_probe.py`
      ⇒ **写入侧 `recompute_window_host_claims` 通过**（当前是 `WindowHostResolutionError`）。
- [ ] `tools/f18_detail.py` 仍能跑（它只做观测，不应受影响）。
- [ ] 全仓 **≥ 2326 passed / 0 failed**，零回归。
      **⛔ `-n 8`，不要 `-n auto`**；**输出直接重定向到文件、退出码单独落一个只属于该命令的文件，
      ⛔ 中间不接任何下游管道**（`| tee | head` 会因 SIGPIPE 打断 pytest，且退出码来自 `head` —— 上一单实际踩过）。
- [ ] neuter 自验做过且如实记录。
- [ ] 执行记录落 `AI_agent/logs/reviews/execution/2026-08-09_f18_exact_float_gate_fix_claude.md`。

⛔ **不要 commit、不要 push**，工作区留着走 orchestrator 独立轻门。

---

## 6. 文件白名单

**允许改**：`src/agent/correction/window_host.py` · 新建
`tests/test_f18_window_host_float_tolerance.py`（或并入既有 host 测试文件）· 你的执行记录。

**⛔ 不许改**：`src/configs/correction.yaml`（容差值不许动）· 任何 prompt ·
`src/agent/nodes/**` · 几何计算（`modelling.py` 的 `point_at` / `window_verts_on_line` 等）·
`AI_agent/CLAUDE.md` / `plan.md`。

---

## 7. ⭐ 合法退出口

**派工方（orchestrator）历史错误率 12/12** —— 每次施工席「停下上报」都是我的题错了。
若发现：验收条件不可达 · 我给的根因与你实测不符（**以你的实测为准**）· 某把锁硬补必得假锁 ·
容差选择在某个量纲上不成立 · 或**改成容差后防篡改能力被实质削弱**（这条尤其重要，
若你判断 1e-9 挡不住有意义的篡改，**请停下来说**）—— **立刻上报，不要硬凑**。
