# 返工请求书 · F-9 路线②设计稿 v2 → v2.1（sol / GPT 侧）

- **日期**：2026-08-10 · **席位**：**`gpt-5.6-sol`**，effort **max** · **只读，⛔ 不施工**
- **上文**：你在同一天出了这份稿的 v2（全文重写，882 行）。**新会话不继承上下文，请先重读自己的稿。**
- **裁决**：orchestrator 对抗审 = **APPROVE-WITH-CHANGES**（**1 MAJOR / 2 MINOR / 0 BLOCKER**）。
  v1 的 3 BLOCKER + 5 MAJOR + 1 MINOR **你已逐条解掉**，我逐条核实过（含独立数了 4 处约定声明点）。
  **本次只补 MAJOR-1 与 MINOR-1，⛔ 不要重写全稿、⛔ 不要重开已定的路线与分工。**
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `b6a3458`。全仓 2361 passed / 10 xfailed / 0 failed。
- **预算**：一轮。⛔ 不跑全仓测试。探针只在 `/tmp`。

---

## 必读

| 文件 | 是什么 |
|---|---|
| `AI_agent/proposals/f9_route2_evidence_citation_design.md` | **你的 v2 稿**（受审稿，就地改） |
| `AI_agent/logs/reviews/verdict/2026-08-10_f9_route2_design_v2_crossreview_orchestrator.md` | **本次裁决全文**（含实测数据与要求的改法） |

---

## MAJOR-1（必改）：沿墙轴有 typed datum 声明，**z 轴一个都没有**

你的 §7.2 把沿墙（local x）方向处理得很严 —— 显式 `datum_mode="view_global_projected_envelope"`，
未声明就抛 typed `projection_datum_unresolved`、**绝不猜**。
**但 local z → world z 的对应关系全稿没有任何一句规定**：§7.1 的 scope 写了
`z_band_id + world_z_interval`、§5.3 条件 6 要求「floor/z scope 与 window 一致」，
**而「一条立面笔画属于哪个 scope」如何判定，没有定义。**

### 这条今天就是承重的（orchestrator 实测，不是推理）

我用 F-20 的官方入口加载了全项目唯一一份 v3 真实产物、用**生产代码本身**
（`materialize_current_ring_va_elevation_bindings` + `ViewProjectionFrame`）复算了全部 15 扇窗：

```
East_view/S3   local_along [3.40, 4.60]   local_z [4.00, 5.80]   ← 二层那扇
East_view/S4   local_along [3.40, 4.60]   local_z [1.00, 2.80]   ← 一层那扇
```

**两条笔画沿墙区间逐位相同，只有高度不同。**
对 `win_f1_E1`，两条候选到其 plan 区间的端点距离**都是 0.0000 m**
⇒ 你 §5.3 条件 3「最优与次优距离之差大于 ambiguity epsilon」**当场为 0 ⇒ 不满足**
⇒ 一份**完全正确**的产物会被判 `position_evidence_insufficient`。`win_f2_E1` 同理。
**15 扇窗里 2 扇（13%）的判定完全依赖这条未定义的规则。**

**⚠️ 更隐蔽的一层**：本产物的 `local_z` **恰好就是世界 z**（S4 的 `[1.00,2.80]` 与一层窗世界 z 相同）
⇒ 实现者随手写「local_z 即 world z」**今天会碰巧全对**，这条隐含约定于是**永远测不出来**，
直到某份 reading 按层归零 z 为止。

### 要求的改法

1. 给 z 轴一份**与 §7.2 对称**的显式声明（如 `z_datum_mode: world_z | floor_local_z`），
   未声明时 typed 拒绝、⛔ 绝不猜；
2. 写死**「一条立面笔画归属哪个 floor/z scope」的判定规则**（含边界与重叠时的行为）；
3. §12.2「Pair positive」行补一格夹具：**同 view、同 along、仅 z 不同的两条笔画**，
   断言各自只与自己那层的 plan 配上，且**去掉 z scope 后该锁必红**。

---

## MINOR-1（必改）：0.300 m 容差的立论基础在**今天的产物上已经归零** ⇒ 阈值不可观测

你引用的量级**属实**（实测 `envelope_reconcile_tol_m` 与 `facade_frame_cross_check_tol_m` **都恰是 0.300**）。
§12.3 用老夹具 `tests/fixtures/f9_window_host_crash/` 算出 `d = 0.12` **也算对了**
（老 ring `[0.12,14.88]` ⇒ origin 14.88）。

**但今天的产物上，15/15 扇窗的 `d` 全部恰为 `0.0000 m`** —— F-17 修法把 ring 变成 `[0,15]`，
基准差整体消失。⇒ 在现代产物构成的夹具上，**这个常量取 0.001 还是 3.0 没有任何区别**，
一把只用现代夹具的正向锁**对任何 `tol ≥ 0` 都绿** —— 与你 §12.1 第 7 条
（hash/集合相等前断言双方非空）是同一族问题的另一个面。

**要求**：§12.2「Pair positive」**同时**钉两个 regime —— 老夹具（`d=0.12`）与现代产物（`d=0`），
并补一格**跨阈值对照**（如 `0.29` 放行 / `0.31` 拦下），否则阈值本身零分辨力。

---

## MINOR-2（无需改稿）

你上一轮纠正我请求书的两条前提**均成立**，已登记为派工方错误 13/13：
① 工作树并非字面干净；② 兼容面不只 v1/v2，仓库已有 historical v3 producer artifact V1
（第二条有实质影响，会让施工单漏掉一整类边界）。**这条只是告知，不用动稿。**

---

## orchestrator 已用机械测量关掉你 §14.3 的 3 条（**请据此更新 §14.3，别再列为未验证**）

| 你列的未验证项 | 实测 |
|---|---|
| 真实 v3 draw 中「唯一 plan + ≥1 elevation existence」的比例 | **15/15 全满足**；`along`/`host` 也都指向 existence 里那条唯一 plan；**零来源复用** ⇒ §5.1 规则不误伤现产物 |
| 0.300 m 的误拒率 | **零误拒**（15/15 的 d 恰为 0.0000）⇒ 但由此得出 MINOR-1 |
| 跨楼层同 x 的 pairing 行为 | **不是假设，真实产物里已存在** ⇒ MAJOR-1 |

⚠️ **口径必须照抄**：以上测的是**今天盘上这一份语料**（1 个 case / 15 扇窗），
**不是**「代码保证」或「模型永远如此」的不变量证明 ⇒ 施工期 targeted replay 仍须保留。

---

## 合法退出口（**请务必用**）

派工方（orchestrator）历史错误率 **13/13** —— 至今每次「停下上报」事后核查都是派工单的题错了。
**本请求书里任何描述岔口 / 分类 / 「必须先做 X」的句子，都请当作【可能错的前提】读。**
若你认为 MAJOR-1 其实已被稿中某处覆盖、或我的实测解读有误 ⇒ **停下、指出哪一句错、错在哪**，
⛔ 不要迁就它改稿。「题错了」在本项目记正分。

## 硬边界

⛔ 只读；唯一可写 = `AI_agent/proposals/f9_route2_evidence_citation_design.md`。
⛔ 绝不读 `case_tests/test_baseline/gt/`。⛔ 不 commit、不 push。⛔ 不跑全仓测试。
