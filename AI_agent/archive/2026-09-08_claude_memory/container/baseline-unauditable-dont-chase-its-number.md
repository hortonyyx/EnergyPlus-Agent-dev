---
name: baseline-unauditable-dont-chase-its-number
description: 2026-08-15 查实 07-07 那个 9/9 基准既不能证明干净也不能证明泄漏——它不可审计；基准不可审计时别把它的分数当靶子，改成「好用 + 产生过程可审计」
metadata: 
  node_type: memory
  type: project
  originSessionId: 9ed0fafd-2cdb-49a8-a106-a2b9331dc492
  modified: 2026-08-15T17:29:55.346Z
---

**2026-08-15**：追了一整天「怎么恢复 07-07 的 9/9」，收工前才发现**那个基准本身不可审计**。

## 三条查实（均可复算）

1. **gt 当时物理够得着**：`723b0f9:case_tests/test_baseline/gt/sm21_anchor/gt.json` 存在；
   读图器是**经 Agent tool 起的子代理**、跑在仓内、有完整读文件能力、**无 guard**。
   `llm.yaml` 写的 "Isolated: fed only …, no gt" 是 **prompt 级**，不是物理隔离。
2. **无任何访问记录**：access log 是硬隔离壳（`isolation.py`+`guard.py`+`run_cv_probe.py`，
   共 2199 行）带来的，**07-07 时这三个文件一行都不存在** ⇒ 不可回溯。
3. **⭐ 产物自身没有推导链**：strokes 标 `dimension_derived`、引 `D1/D11/D12`，
   但那些 dimension 条目 **`text=None`、`anchor=None`**、`notes` **全空**
   ⇒ 拿不出「这个数从哪个像素/哪段文字来」。
   而「产物必须自证推导链」这条纪律**恰恰是 07-07 之后才写进 `cv_toolbox.md` 的**。

⇒ **结论是第三种：不可审计。** 既不是「干净」也不是「泄漏」，是**没有证据能判**。

## ⭐ 但「泄漏」这个解释被用户当场排掉（orchestrator 没想到）

**sm24 也出过好 reading，而那时 sm24 根本没有 gt。**
核实：sm24 的 gt **2026-07-26/27** 才进仓，而 `sm24_anchor/run_2026-07-07_haiku_cv_probe`
早三周，其过程指标 = **38 次 CV 调用（crop_zoom 14 · px_m_calibrator 5 · overlay_logger 5）**
⇒ **要恢复的那个「量」的工作模式，出现在一个 gt 尚不存在的 case 上。**
⚠️ 该 run 的**分数**未能重判（scorer floor 映射未解析）⇒ 只坐实工作模式，未坐实满分。

## ⇒ 可迁移的判据

**基准不可审计时，别把它的分数当靶子。**
- ⛔ 「恢复到 X 的 9/9」这种目标，前提是 X 的出身能核验；不能核验就是在追一个可能虚高的数。
- ✅ 改成双条件：**好用（下游真能消费）+ 产生过程可审计（有访问记录 + 产物自证推导链）**。
- ⚠️ 连带口径：**今天分数低，可能有一部分是「老基准分数虚高」的镜像** —— 无法量化，但不得省略。
- 反面提醒：**今天的跑虽然分低，但可审计**（D1 有 63 条 access log、5 条 deny 全留痕）。
  ⇒ 硬隔离壳里「gt 物理不可达 + 留痕」是**净收益**，⛔ 别因为要撤「能力封口」就整体回退。

同族 [[version-number-is-not-behavior-attestation]]（声明不等于行为）·
[[hash-of-whole-report-is-not-an-equality-test-for-its-parts]] ·
[[reading-quality-lever-is-crop-budget-not-review-ring]]（当日杠杆清单）
