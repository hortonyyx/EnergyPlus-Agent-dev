# 跨家族复核请求 · F-133 同层轴合并记账（R1/R2/R3）

- **日期**：2026-08-28 · **请求方**：orchestrator（Claude 家族）· **复核方**：GLM 跨家族
- **被审对象**：**`10115eb`**（施工）+ **`a069476`**（记录补填与主控复核）+ **`2b874f7`**（全量读数）
  ⇒ **审 `49f09dc..2b874f7` 这段**，⛔ 其中 `6b5d9bd` 是纯 `AI_agent/` 文档、不属被审范围
- **分支**：`08.23_AsDrawnReading` · **档位**：工程档

---

## 〇、⛔ 本单的特殊之处：**施工方在 commit 前一刻被 API 中断，由 orchestrator 代提交**

⇒ ⚠️ **「谁写谁不批」在这里更要紧**：orchestrator 既是**派工方**又做了**代提交**，
所以**独立第三方的复核是这一单唯一的外部检查**。

⭐ **请特别对着 orchestrator 自己写的那两段审**（执行记录 §八、§九）——
它们是**派工方给自己打的分**。

---

## 一、原始需求（派工单，⛔ 请只看它 + diff + 测试输出）

→ [`request/2026-08-28_f133_samefloor_step_observability.md`](2026-08-28_f133_samefloor_step_observability.md)

**三件**：
- **R1** 同层轴合并**响亮记账**（两处 kill site 都要覆盖）· ⛔ **几何输出逐位不变**
- **R2** `_MIN_EDGE` 与 `min_edge_length_m` **合一**，⛔ **值不变**
- **R3** 夹具**锁住当前（有缺陷的）行为**，并写明「②-2 落地时必须改成保住」

⛔ **明令不许**：改任何合并/吸附的数值或策略 · 改 `_same_floor_sliver_conflict` ·
碰 `src/agent/judge/` · 为了让全量绿而删锁或放宽既存断言。

---

## 二、diff 范围（`git show --numstat`）

```
10115eb   117  0  src/agent/correction/deterministic.py
           12  0  src/agent/correction/envelope_transform.py
           34  3  src/agent/geometry/modelling.py
          286  0  tests/test_f133_same_floor_step.py
          452  0  AI_agent/logs/reviews/execution/2026-08-28_f133_execution.md
a069476    48  1  AI_agent/logs/reviews/execution/2026-08-28_f133_execution.md
2b874f7    20  0  AI_agent/logs/reviews/execution/2026-08-28_f133_execution.md
```

## 三、已声称的读数（⛔ 请独立复现，别采信）

```
主控权威全量   3208 passed, 13 xfailed, 0 failed   (-n 6, ⛔ 无 -m, 944.12s)  EXIT=0
.pth 哨兵      跑前跑后三行逐字相同
HEAD           跑前跑后同为 a069476
算术           3195(基线) + 13(新夹具) = 3208
新夹具         tests/test_f133_same_floor_step.py  13 passed in 8.68s
```

四档同层台阶的行为（orchestrator 已独立复现一次，**请你再独立跑一次**）：

```
120 mm → y轴 [0.0, 6.0, 6.12, 10.0]   记账 0 条          （没被合并）
 60 mm → y轴 [0.0, 6.03, 10.0]        记账 1 条  step=sliver_merge
 30 mm → y轴 [0.0, 6.02, 10.0]        记账 1 条  step=identity_cluster
 10 mm → y轴 [0.0, 6.0,  10.0]        记账 1 条  step=identity_cluster
```

---

## 四、⭐ 请重点打的六处（我方最怕错在哪）

1. ⭐⭐⭐ **「几何逐位不变」是真的吗？** 这是本单的**承重前提** ——
   R1 声称只加记账不动行为。⇒ 请**自己造几组同层台阶**（⛔ 别只用我给的四档），
   对比 `10115eb` 前后的坐标输出。**任何一处坐标变了 ⇒ 阻断。**
2. ⭐⭐ **记账会不会漏？** 两处 kill site（`identity_cluster` / `sliver_merge`）都覆盖了吗？
   ⇒ 请找**第三条能把同层两条轴并掉的路径**（若存在，就是漏的）。
3. ⭐⭐ **记账会不会误报？** **跨层**合并被刻意排除在外（那是 `cross_floor_align_tol_m` 的立意）。
   ⇒ 请构造**跨层抖动**的输入，确认它**不产生**记账行；再构造**同层+跨层混合**，看归类对不对。
4. ⭐ **R2 的「值不变」是真的吗？** `_MIN_EDGE` 从字面量改成了
   `load_core_tolerances().min_edge_length_m` 的惰性读取。
   ⇒ 请确认**默认配置下逐位等于 0.100**，且 `$EP_AGENT_CORRECTION_CONFIG` 覆盖时**两条路径读到同一个值**。
   ⭐ 施工方给了一处反空转实测（覆盖配置设 `0.200` ⇒ 0.15 m 的 cell 边在 correction 路径被拒、
   在 modelling 路径被收）—— **请复现它**。
5. ⭐ **R3 夹具有没有分辨力？** 它锁的是**当前有缺陷的行为**。
   ⇒ 请做 neuter：**去掉 R1 的记账** ⇒ 夹具必须红；**改回字面量 `_MIN_EDGE`** ⇒ 相关用例必须红。
   ⛔ 若某条用例两种 neuter 都不红 ⇒ 它是空转的。
6. ⚠️ **`envelope_transform.py` 只加了 12 行**，按派工单那里**只该加注释**（`min_edge_length_m`
   被挪用作窗宽/窗高下限的语义警示）。⇒ **请确认那 12 行确实没有行为**。

---

## 五、⚠️ 派工方本单已知的题错（第 42、43 条，施工方抓出）

| | 内容 | 处置 |
|---|---|---|
| **#42** | **`_MIN_EDGE` 有第三处独立声明**：`src/validator/interzone.py:64`（超本单授权范围，施工方记一行未动）⇒ **R2 只合了三分之二** | 留下轮。⭐ **请确认全仓没有第四处** |
| **#43** | 派工单未交代记账要不要过 `output_precision_m` 滤网。施工方指出：若过，**10 mm 那档会被滤掉**（每侧只挪 5 mm），而那正是验收点名要的档 | 施工方显式不过滤 + 夹具写死理由。⭐ **请判这个处置对不对** |

**施工方的一条异议，orchestrator 已采纳**：不同意派工单说的
「`_same_floor_sliver_conflict` **方向反了**」，认为是「**量错了尺子**」
（注释立意指向 `axis_jitter_tol_m` 50 mm，实现却拿 `min_edge_length_m` 100 mm 去量，
且对「直接相邻的两条同层轴」这个主场景近乎恒假）。
⇒ ⭐ **请判这两种读法哪个对**，或都不对。**本单没有改它**。

---

## 六、⛔ 明确不在本单范围（⛔ 别按这些判阻断）

- **不改合并策略** —— 同层「真实台阶」与「模型抖动」在 correction 层**结构上分不开**
  （实测模型抖动 5–10 mm、200/180 墙真台阶 10 mm，**同一个数**）。
  分得开的前提 = **R-6 厚度活到这一层**，归 ②-2。
  ⭐ **但如果你能找到一条【今天就成立】的结构判据把两者分开 ⇒ 请写下来**，那比本单值钱得多
  （施工方认领失败并列了它否掉的三条路，见执行记录 §七.3）。
- `src/validator/interzone.py` 的第三处声明 · 出模形式 · 事实层 · `src/agent/judge/`。

---

## 七、⚠️ 一条我方实犯，请核我有没有说全

施工方第 1 次全量红了一条 `test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent`，
它定位为「跑测途中第三方改了共享工作树」。**那个第三方是 orchestrator** ——
我在它跑全量期间提交了 `6b5d9bd`（纯文档）。复跑即绿。

⇒ 请核：**这条红确实与本单 diff 无关吗？** 我的判断依据只有「它是 baseline-marker 用例、
且复跑绿、且第 2 次跑时脏路径变化没落在它的窗口内」。⛔ **若你认为它可能是真回归，请说。**

---

## 八、交件

写一份 `logs/reviews/verdict/2026-08-28_f133_crossreview_glm_verdict.md`：
**裁决**（APPROVE / APPROVE-WITH-FINDINGS / REWORK / REJECT）· **阻断与不阻断分开列** ·
**你独立跑出来的读数原文**（全量汇总行 + `.pth` 哨兵 + 四档行为）·
**你做的 neuter 与结果** · **你认为我方还没说到的地方**。
