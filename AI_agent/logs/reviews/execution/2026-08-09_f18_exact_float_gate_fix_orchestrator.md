# F-18 施工记录（⚠️ **由 orchestrator 亲自完成，带审阅债**）

- **日期**：2026-08-09
- **派工单**：[`request/2026-08-09_f18_exact_float_gate_fix_dispatch_claude.md`](../request/2026-08-09_f18_exact_float_gate_fix_dispatch_claude.md)
- **基点**：`61a30c7` · 基线 **2326 passed / 10 xfailed / 0 failed**

---

## ⛔⛔ 0. 先说清楚这批的验收是残缺的

**Claude 侧施工席撞月度额度上限中断，orchestrator 接手做完 ⇒ 作者与验证者是同一个，违反本项目「谁写谁不批」。**

- ✅ **可以算数的**：全仓、neuter、真实产物复跑 —— 这些是**机械测量**；
- ⛔ **不能算数的**：「这个修法对不对」的判断。**orchestrator 不得为自己写的代码签字。**

⇒ **已登记审阅债，交 GPT 侧独立交叉审**（用户 2026-08-09 定：审阅统一启 GPT，不阻塞修复进度）。

### ⚠️ 中断形态值得单独记（与 08-08 同型，第二次）

施工席最后一句是 **"Now I have a precise, verified understanding of the bug. Let me apply the fix"** ——
听起来**尚未动手**；实测工作区**已落 20 行**（`_point_close` helper 已加、**三个调用点一行未改**）。

⇒ **纪律：施工席中断后，一律以 `git diff` 为准，⛔ 不许采信它最后一句话的自述。**
（08-08 那次是「中断在 neuter 自查前，『代码在、测试绿』与『已验收』外观完全一致」，本次是
「自述未动手、实际已改半截」—— 两种形态都指向同一条：**中断处的自述不可信**。）

---

## 1. 防假验证自检（派工单 §0，动手前答）

1. **验收路径真的会经过被改的代码吗？** 会。判据在 `window_host_claim_issues`（`window_host.py:585-640`），
   由 `recompute_window_host_claims`（`:1042`）调用，后者由 `stage_runner.record`（`stage_runner.py:299`）
   在**写入侧独立复验**时调用。锁走 `resolve_window_hosts` 官方入口产出 claims，再喂
   `window_host_claim_issues` —— 即被改的那段本身。另用真实产物脚本
   `tools/f18_probe.py` 交叉验证（走 `finalize_correction_draw` 全链）。
2. **锁把修法整个还原会不会转红？** 会（见 §4，2/4 转红、零连带）。
3. **断言的是具体数值行为还是「没抛异常」？** 具体数值：正向断言「无 `line_geometry` issue」，
   反向断言「挪 1e-6 m 后**必须**出现 `world span` / `p1->p2 endpoints` / `vertices`」。

---

## 2. 改了什么

**唯一生产文件**：`src/agent/correction/window_host.py`。

### 2.1 `_point_close` helper（施工席中断前留下的部分，orchestrator 保留未改）

按坐标逐个比较、每个坐标用自己的 eps。其 docstring 明确限定用途：
**只用于「同一个已解析事实的两份 binary64 表示」的回比**，⛔ 不是两个不同候选之间的测量/匹配容差。

### 2.2 三处判据由「逐位相等」改为「B5 自己的容差内」（orchestrator 施工）

| 位置 | 原 | 现 |
|---|---|---|
| `p1->p2 endpoints` | `declared_endpoints != (q0, q1)` | `len(...)!=2 or not all(_point_close(..., eps_xy))` |
| `world span` | `(lo,hi) != (clamped_span.lo, .hi)` | `not _point_close(..., (span_eps,)*2)` |
| `vertices` | `fresh_vertices != declared_vertices` | 长度校验 + 逐点 `_point_close(..., eps_xyz)` |

**容差选择（⛔ 未新造常量、⛔ 未动 `correction.yaml`）**：
宿主线是轴对齐的（上方已有守卫），故一个平面坐标沿立面、另一个是平面偏移 ⇒
`eps_xy` 按 `dy == 0` 分派 `window_host_span_epsilon_m` / `window_host_plane_epsilon_m`（均 1e-9）。
顶点的 z 用 `window_host_plane_epsilon_m` 并**在注释里写明理由**：B5 未定义单独的垂直 epsilon，
在此新造一个未随配置发布的常量比复用更糟。

**⭐ 选这两个常量的依据（不是随手挑的）**：`config.py` 对它们的注释写着
「B5 must never silently borrow a Vg or legacy window tolerance」，且**故意不给 dataclass 默认值**
—— 它们正是为这个解析器准备的。

---

## 3. 三条硬约束的遵守情况

| 约束 | 遵守 |
|---|---|
| ⛔ 不许删门 / 降级 advisory | ✅ 门仍在，仍抛 `resolver_output_tampered` |
| ⛔ 不许改 `invariant_no_geometry_commit` 裸抛的出口语义 | ✅ 一字未动（F-9 的有意设计） |
| ⛔ 不许动几何计算 | ✅ `point_at` / `window_verts_on_line` 一字未动 |

---

## 4. 锁与 neuter

**新文件** `tests/test_f18_window_host_float_tolerance.py`，**7 passed**。

| 类 | 内容 |
|---|---|
| **正向 ×4** | footprint 从 `0.12` 起（真实形态）+ 跨度用**二进制不可精确表示的十进制**：`11.36-13.76`（真实失败窗 `W_F1_SE` 的原值）/ `1.24-3.64` / `2.19-5.55` / `6.3-8.7` ⇒ **必须无 `line_geometry` issue** |
| **反向 ×3** | 分别把 `clamped_span.lo` / `endpoint.x` / `vertex.z` 挪 **1e-6 m**（容差的 1000 倍、仍远低于几何意义）⇒ **必须仍被拦下**，且 `detail` 精确等于对应字符串 |

**⭐ 反向锁是刻意加的**：只证明「现在能过」= 恒等锁，不证明**该拦的还拦得住**。

### neuter（三处判据全改回 `!=`）

```
tests/test_f18_window_host_float_tolerance.py + tests/test_c2_b5_host_resolution.py
⇒ 2 failed, 67 passed
FAILED test_binary64_round_trip_noise_is_not_tampering[1.24-3.64]
FAILED test_binary64_round_trip_noise_is_not_tampering[2.19-5.55]
```

**⛔ 只红 2/4，如实记**：`11.36-13.76` 与 `6.3-8.7` 在这个夹具几何下恰好逐位往返一致。
**这本身印证了「ULP 噪声出不出现取决于具体算式」的定性** ⇒ 分辨力在**那一组**而非单个用例。
已把该实测结论 + **⛔「不许把这个列表精简成『真正有用的那几个』」** 写进测试 docstring，
否则将来一删、锁就静默失效。

**零连带**：其余 67 条（含整个 `test_c2_b5_host_resolution`）全绿。
**恢复后 sha256 逐字节一致（`fc7c84a2…`）、`grep NEUTER` 零残留。**

---

## 5. 验收

| 条件 | 结果 |
|---|---|
| 真实产物 `tools/f18_probe.py` | ✅ 写入侧 `recompute_window_host_claims` **由抛异常变为通过** |
| 全仓（`-n 8`，输出直接重定向 + 退出码单独落文件，⛔ 无下游管道） | ✅ **2333 passed / 10 xfailed / 0 failed**，退出码 0（2326 → 2333，零回归） |
| neuter | ✅ 见 §4 |
| 文件恢复校验 | ✅ sha256 一致、零残留 |

---

## 6. ⛔ 交给交叉审的具体问题（orchestrator 自己答不了的）

1. **1e-9 容差是否实质削弱了防篡改能力？** —— 这是本单唯一的真实设计风险。
   orchestrator 的判断是「1e-9 m = 1 纳米，远低于任何有意义的几何篡改」，但**作者不能给自己判**。
2. **顶点 z 复用 `window_host_plane_epsilon_m` 是否恰当？** B5 没有垂直 epsilon，
   这是「复用 vs 新造」的取舍，需要第二双眼睛。
3. **`_point_close` 的适用边界是否被后续使用者误解的风险？** 它的 docstring 限定得很紧
   （只用于同一事实的两份表示回比），但它现在是模块级函数，**没有机制阻止别人拿它当匹配容差用**。
4. **正向锁只红 2/4 是否可接受**，还是应当构造保证每个用例都有分辨力的夹具。
