# 调查单 · F-9 重新定性：`resolve_window_hosts` 崩溃

> **⚠️ 这是「调查单」不是「施工单」。本单不写病因假设、不写修法、不写验收条件。**
> **⛔ 本单只调查、不改生产代码。**

- **日期**：2026-08-06
- **派工方**：orchestrator（Opus 5）
- **席位**：GLM-5.2，**主工作树**（串行，在墙 3 调查单之后）
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD 应为 `b379cd8`

---

## 0. 开工自检（三行，不对就停）

```bash
git log --oneline -1     # 期望 b379cd8
git status --short       # 3 个 case_tests 未跟踪目录属已知、不要动
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```

## 1. ⛔ 先读这条：**上一份 F-9 调查的结论已作废，⛔ 不要继承它**

08-05 有过一份 F-9 调查（`execution/2026-08-05_f9_window_host_investigation_sonnet.md`），
它的结论 **「这批图纸平面与四立面共用一套轴网、不镜像，所以 `_BASE_SIGN` 写错了」** —— **已被证伪并作废**。

**⛔ 硬约束（用户 2026-08-05 当面定案，不得推翻、不得重新讨论）**：

> **这批图纸的立面就是标准画法：人站在楼外面看这堵墙。**
> ⇒ `window_sources.py:42` 的 `_BASE_SIGN = {"North": -1, "South": 1, "East": 1, "West": -1}` **是正确的**。
> ⇒ **⛔ 不许改 `_BASE_SIGN`，⛔ 不许改 `A1_coordinate_normalization.md` §2.2 的方向约定。**

orchestrator 已按右手系（`右 = 视线方向 × 上`）独立验算四个方向，与 `_BASE_SIGN` 逐一吻合。
上一份调查的两条证据均被查明**零分辨力**：北立面尺寸链 `1240|2400|2660|2400|2660|2400|1240` 是**回文**、
两层窗集合镜像后逐字节相同；南立面 `+1` 在外视惯例下本来就是 `+1`。
**详见 [`plan.md` 「F-9 定性作废」条](../../plan.md)。**

**⇒ 方向/惯例这个问题已经关闭。本单要查的是：既然约定是对的，那它到底崩在哪。**

## 2. 现象

`run_2026-08-05_f7_verify_sonnet` 这个 run（**F-7 修好之后**的产物）：
`_claim_links` **完全通过**，然后**死在更深的 `resolve_window_hosts`**，抛 `WindowHostResolutionError`。

崩溃前的草稿已落盘（`run_correction()` 在崩溃前就写了 `correction_geometry.json`）。

## 3. 复现路径（**零 LLM 成本**，产物已在盘上）

⚠️ **产物在另一棵工作树里**（不是主树）：

```
.claude/worktrees/f7-manual/case_tests/e2e_tests/sm21_anchor/run_2026-08-05_f7_verify_sonnet/
  ├── 0_reading/            # 六份 *_view.json
  └── 1_correction/
        ├── correction_geometry.json      # 崩溃前的草稿
        └── attempts/001/output.json
```

**已核实的一条事实**（orchestrator 亲查，你可自行复核）：该产物的 `source_ids` 是**带图名的**，
例如 `W-F1-N-1.provenance.existence.source_ids == ['1f_view/S11', 'North_view/S5']`
—— 即 **F-7 的翻译机制生效了**，与 08-05 那份调查用的**裸编号**产物（`smoke_downstream_r2`）**不是同一形态**。

**上一份调查的离线复现方法可以照用**（纯读盘 + 确定性代码，零 LLM）：
加载 `correction_geometry.json` → `build_verified_window_inputs_from_run(...)` → `finalize_correction_draw(...)`。
⚠️ **但请用本单指的这份产物**（`f7_verify_sonnet`），不是 `smoke_downstream_r2`。

## 4. 已登记但**未经证实**的观察（供参考，⛔ 不是结论、不要当前提）

orchestrator 08-05 顺手记下、**都没查实**，你可采纳可推翻：

- 代码算出的 `along_origin = 14.88`，而北立面尺寸链总宽是 **15000**（`14.88 = 15.0 − 0.12`）。
- `apply_v3_envelope_transaction` 两次调 `_dry_resolve_current_ring`：
  变换**后**那次（`envelope_transform.py:576-591`）catch 住并优雅回滚 + 写 `geom.conflicts`；
  变换**前**那次（`:536`）**没有 try/except**、裸穿出去崩全流程。两处是同一个 07-18 提交加的。

**⇒ 这两条我没验证过，可能都不相干。⛔ 不要因为它们写在这儿就去凑。**

## 5. 边界

- ⛔ **不改任何生产代码 / 测试**（本单是调查）
- ⛔ **不改 `_BASE_SIGN`、不改方向约定**（见 §1，用户已定案）
- ⛔ **不重跑 correction 抽签**（零 LLM 成本要求；产物已够用）
- ⛔ **不碰 `case_tests/` 未跟踪目录**；⛔ **不在 f7-manual worktree 里写任何东西**
- ✅ 一次性脚本放 `/tmp`

## 6. 请你回答的（交付物）

1. **崩溃点的 `conflicts` 里到底是什么？** 逐条列：window_id · reason_code · 各来源换算出的世界区间 · 与平面声明区间的关系。
2. **⭐ 定性**：在「方向约定是对的」这个前提下，它为什么还是对不上？给判据，不给印象。
3. **⭐ 2–3 个修法选项 + 各自后果与代价**（含"什么都不改会怎样"）。**⛔ 不要动手修。**
4. **该硬崩还是该归档重抽？** 与 `correction_draw_issues` 的既有口径对齐着说。

## 7. 证据纪律（本轮新立，硬要求）

> **⛔ 不接受「我看了 / 我读了」作为结论依据** —— 每条结论给出可独立重跑的命令 / 路径+行号 / 数字。
> **⛔ 凡涉及「方向 / 左右 / 对称」的判断，必须先证明载荷本身不对称**（对称载荷镜像后逐字节相同 ⇒ 零分辨力）。
> 上一份 F-9 调查正是栽在这条上。

## 8. 交付

日志落 `AI_agent/logs/reviews/execution/2026-08-06_f9_rediagnosis_investigation_glm.md`；先落骨架再补。
**⛔ 不 commit、不 push。**

## 9. 停下上报（**记功不记过**）

本轮至今 **7 次「停下上报」，7 次都是派工方（我）的题错了**。
本单陈述的事实与你看到的不符 / 你认为提法本身有问题 / 真相与本单框架不兼容 ⇒ **立刻停下上报**。
**⛔ 唯一不接受的「上报」是要求推翻 §1 那条用户定案。**
