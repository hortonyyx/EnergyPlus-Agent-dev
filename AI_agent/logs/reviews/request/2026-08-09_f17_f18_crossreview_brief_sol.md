# 交叉审请求书 · F-17 + F-18（GPT 侧 sol，验证性审阅）

- **日期**：2026-08-09
- **审阅方**：`gpt-5.6-sol`，effort high
- **仓库**：`/workspaces/EnergyPlus-Agent-dev`，分支 `6.15_ValidationArchM0toM4`，**HEAD = `f91f387`**
- **全仓基线**：`python -m pytest -n 8` ⇒ **2333 passed / 10 xfailed / 0 failed**

---

## 0. ⛔ 为什么找你审（先看这条，它决定了审阅重点）

本轮两个修法的**验收成色不同**：

| | 谁写的 | 谁验的 | 「谁写谁不批」 |
|---|---|---|---|
| **F-17** | Claude 侧 Sonnet 施工席 | orchestrator 轻门（独立全量 + 换方向 neuter ×2） | ✅ 满足 |
| **F-18** | **orchestrator 亲手**（施工席撞额度中断，接手做完） | **orchestrator 自己** | ⛔ **违反** |

⇒ **F-18 是本次审阅的重点，F-17 是顺带复核。**
orchestrator 做的全仓/neuter/真实产物复跑属**机械测量**，可信；
但**「这个修法对不对」的判断没有第二双眼睛看过。**

**⛔ 请特别注意：不要因为「测试全绿」就认可。** 本项目有惨痛先例（F-13）——
一个修法做到「全仓 2243 绿 + 漂移门 104→0 + EnergyPlus 0 severe」三绿齐，
而 **76/79 个垂直面的宽高被 EnergyPlus 判错**。**唯一穿透「三绿」的动作是量产出的物理量本身。**

---

## 1. 请审的两个提交

```
f91f387  08.09_f18_float_tolerance_fix_WITH_REVIEW_DEBT     ← 重点
2c8aca3  08.09_f17_cross_axis_chamfer_fixed_lightgate_passed ← 顺带
```

`git show <sha>` 可看完整 diff 与提交说明（提交说明写得很详细，含机理与验证账）。

---

## 2. F-18：请回答这四个问题（orchestrator 自己答不了的）

### 背景（30 秒）

`src/agent/correction/window_host.py` 的 `window_host_claim_issues` 是一道
**anti-tamper 自洽门**（失败抛 `resolver_output_tampered` +
`invariant_no_geometry_commit`，**裸抛、直接终止整条 flow**）。

它把一个解析结果的世界跨度/平面端点/顶点，**用该结果自己存的参数区间重新算一遍**再比对。
原实现用 `!=` **浮点逐位比较**。真实产物上实测偏差是 **1–4 个 ULP（≤2e-15 m）**
⇒ 15 个窗里 6 个被判「篡改」，整条链路终止。

修法 = 三处比较改用 B5 自己的容差
（`window_host_span_epsilon_m` / `window_host_plane_epsilon_m`，**均 1e-9**，
`src/configs/correction.yaml:98,100`）。

### ⭐ 四个问题

1. **1e-9 m 的容差是否实质削弱了防篡改能力？**
   这是本单**唯一的真实设计风险**。orchestrator 的判断是「1e-9 m = 1 纳米，
   远低于任何有几何意义的篡改」，并配了反向锁（挪 1e-6 m 必须仍被拦下）。
   **请独立判断这个论证是否成立**，特别是：**有没有一种有害的篡改，其幅度小于 1e-9 m 却能造成后果？**
2. **顶点的 z 通道复用 `window_host_plane_epsilon_m` 是否恰当？**
   B5 没有定义单独的垂直 epsilon。orchestrator 选了「复用而非新造常量」
   （理由：新造一个未随配置发布的常量更糟）。**这个取舍对吗？**
3. **新增的模块级 helper `_point_close` 有没有被误用的风险？**
   它的 docstring 限定得很紧（**只用于同一个已解析事实的两份 binary64 表示回比**，
   ⛔ 不是两个不同候选之间的测量/匹配容差），但**没有任何机制阻止别人拿它当匹配容差用**。
   本项目反复吃过「文档说了、机器不管」的亏。**需要加机制吗？**
4. **正向锁只在 4 个参数化用例中的 2 个上具备分辨力**（neuter 时只红 2/4，
   另两个跨度在该夹具几何下恰好逐位往返一致）。orchestrator 的处理是
   **保留 4 个并在 docstring 写死「⛔ 不许精简这个列表」**。
   **这个处理够吗？还是应当构造保证每个用例都有分辨力的夹具？**

### 关键文件

- `src/agent/correction/window_host.py`（`_point_close` + `window_host_claim_issues` 三处比较）
- `tests/test_f18_window_host_float_tolerance.py`（7 passed）
- `AI_agent/logs/reviews/execution/2026-08-09_f18_exact_float_gate_fix_orchestrator.md`（施工记录，含自陈的审阅债）
- `AI_agent/logs/experiments/2026-08-09_f18_window_host_exact_float_gate/README.md`（调查全档，含逐窗实测差值表）

---

## 3. F-17：顺带复核（已有 orchestrator 轻门 PASS）

**根因**：`_apply_components` 顺序就地改写几何，但各 envelope 组件的 `intervals`
锚在**变换前**的坐标系 ⇒ 第二个与第一个**正交**的组件判定公共角点时，
该点坐标已被前一个组件改过 ⇒ 漏移，同时 materialize 又在原位插新点补上
⇒ **一个直角裂成两点、连成 45° 斜边**。

**修法** = 三阶段（相 1 只插点不移动 → 相 2 用**冻结的原始坐标**对全部组件定位、
命中哪个改哪个分量 → 相 3 规范化）。

**已验证**：真实产物跑通（footprint `[0.12,14.88]×[0.12,7.88]` → `[0,15]×[0,8]`）·
orchestrator 换方向 neuter（**只改调用点、函数内部一行未改** ⇒ 锁恰好转红、零连带）。

**请复核**：三阶段实现是否真的做到「组件顺序无关」，有没有遗漏的耦合路径。

**已知缺口（已登记，⛔ 不必重复报告，但欢迎评论严重性）**：
`_materialize_axis_splits` 在**全部现有夹具上调用 101 次、插点恒为 0**
⇒ 整套 T-junction/图闭包机制从未被任何测试执行过；把它整段删掉，全仓零红。
该缺口**继承自旧代码**，非本批引入。

---

## 4. 输出要求

请按本项目惯例给**结构化裁决**：

- **总裁决**：APPROVE / APPROVE-WITH-CHANGES / REWORK / REJECT
- **分级 findings**：BLOCKER / MAJOR / MINOR / NIT，每条给
  **文件:行 + 具体命题 + 为什么 + 建议**
- **对 §2 四个问题逐一明确回答**（这是本次审阅的核心交付）
- 若你认为某条 orchestrator 的论证**不成立**，请直接说，并给出反例或复现路径

⛔ **不要改代码**，只出裁决。⛔ 不要 commit / push。
⛔ 只读仓库；如需跑测请只跑只读命令（全仓已跑过，数字在 §0）。

**⭐ 特别提醒**：本项目 orchestrator 的派工错误率是 **12/12**
（每次施工席「停下上报」，查明都是派工方的题错了）。
**如果你认为这份请求书本身有问题（问错了、前提不成立、范围不对），请直接说。**
