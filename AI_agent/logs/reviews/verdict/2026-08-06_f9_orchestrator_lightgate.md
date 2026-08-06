# orchestrator 轻门 · F-9 窗宿主解析接线与分类

- **日期**：2026-08-06 · **裁决人**：orchestrator（Opus 5，独立执行，未参与施工）
- **被审对象**：分支 `f9-fix-2026-08-06` @ `f316cfe`（worktree `.claude/worktrees/f9-fix`，基点 `dfbd62a`）
- **施工席**：Claude 侧 Sonnet 子代理 · **派工单**：[`request/2026-08-06_f9_fix_and_c_design_dispatch_claude.md`](../request/2026-08-06_f9_fix_and_c_design_dispatch_claude.md)

## 裁决：**PASS**（附三条如实登记，均不阻断）

---

## 1. 独立全量（orchestrator 亲跑，非采信施工席数字）

| 树 | 结果 | 收集总数 |
|---|---|---|
| **干净基线** `dfbd62a`（`/tmp/f9base`，独立 worktree） | **2222 passed · 4 failed · 8 skipped · 10 xfailed** | **2244** |
| **F-9 分支** `f316cfe` | **2231 passed · 3 failed · 8 skipped · 10 xfailed** | **2252** |

- **收集数 2244 → 2252 = 正好 +8**，等于新增锁数 ⇒ **新锁确实被收集、确实跑了**（非静默跳过）。
- **passed 2222 → 2231 = +9**：+8 新锁，另 +1 见 §3.1。
- **failed 4 → 3**：少的那条见 §3.1，**与本次施工无关**。
- ⇒ **零回归确认。**

### ⛔ 更正施工席的一处论证（结论对、理由错）
施工席报「2231 + 3 = 2234，与派工单的 2234 基线对得上」——**这是数字巧合**。
2234 是**主工作树**的绿数；**干净树基线是 2222 passed**。
正确对账是 **2222 + 8（新锁）+ 1（§3.1）= 2231**。**结论（零回归）不变，论证作废。**

> **顺带记我自己一笔（第 10 次派工方出错）**：F-9 派工单同时写了「基线 2234 绿 / **0 红**」
> 和「可能有 3 条已知 F-8 红」——**两条验收条件自相矛盾**。施工席没硬凑、如实登记，做得对。

---

## 2. ⭐ 独立 neuter（**换方向**：施工席三次都是「删代码」，本轮改为「代码全在、故意分错类」）

在 `/tmp/f9neuter`（一次性 worktree，验完逐字节复原并销毁）：

| 方向 | 改动 | 结果 |
|---|---|---|
| **N1** | `.category` 一律返回 `model_draw_error`（该硬崩的被降级成归档重抽） | **2 红**：`test_category_all_invariant_conflicts_is_input_integrity_error` · `test_category_any_invariant_conflict_is_input_integrity_error` |
| **N2** | `.category` 一律返回 `input_integrity_error`（该归档重抽的被升级成硬崩） | **3 红**，含 **真实入口锁** `test_real_crash_run_no_longer_hard_crashes` —— 真的抛出 `WindowHostResolutionError`、崩在 `window_host.py:903` |

⇒ **真锁，不是假锁。** 两次复原均 `git diff --quiet` 通过（逐字节一致）。

### ⚠️ 如实登记（不阻断）：锁的覆盖不对称
**N1 方向没能让真实入口锁变红** —— 即「不变量级冲突必须硬崩」这一侧**目前只有单元测试在守**，
端到端锁只覆盖了「模型错要归档重抽」那一侧。
**不是假锁**（单测断言落在具体 category 值上、真的绑住了），但覆盖不对称，**登记为跟进债**。

---

## 3. 三条如实登记

### 3.1 ⭐ 新发现（F-14 候选）：全仓里有一条测试**真的在调付费 API**
基线的第 4 条红 = `tests/test_zone_agent.py::test_zone_agent_creates_two_zones`
（`openai.AsyncOpenAI` 在 `validate_environment` 构造失败），F-9 分支那次它通过了。
**与本次施工无关**，但坐实一件事：

- 该测试**没有任何 mock/patch/stub**（`tests/` 下**根本没有 `conftest.py`**），主树单跑耗时 **13.5s**
  ⇒ **它构造真实 LLM 客户端并发出真实请求**。
- ⇒ **「全仓绿」还额外依赖 API 可用性与凭据** —— 与 **F-8 同族、但机制是新的**
  （F-8 是被 `.gitignore` 挡住的活输入；这条是**实时网络 + 付费调用**）。
- ⇒ **每跑一次全仓都在烧钱**，且这是一个天然的 flaky 源。
- **范围已界定**：机械扫描 `tests/*.py`，**同类只有这一条**（`test_reading_mode.py` 也 import 了节点但有 mock）。
- **⛔ 本轮不修**，登记待排期。

### 3.2 设计稿结论（第二段，⛔ 未施工）
`build_observation_reference_catalog_from_run`（`window_sources.py:493-495`）只接 `run_dir`/`reading_dir`，
**签名里没有几何**；它在 `run_stage.py:329-333` 被调用，**早于 `run_correction()`（:334）画出 footprint**。
而世界区间所需的 `along_origin` 依赖 footprint/`geom` 的 ring ⇒ **建目录的时刻结构上拿不到。**
⇒ **路线①（代码算好世界区间喂给模型）在当前接线下不可行**，除非两遍画或引入会漂移的代理值。
⇒ 施工席推荐**路线②（配对整个交给代码）**，并**明确未单方面拍板** ——
`source_ids` 的自证粒度会从「笔画级」降到「视图级」，**待 B5 口径持有者/用户签字**。

### 3.3 `envelope_transform.py` 那处修法的锁较弱
施工席自己如实报告：单独 neuter 掉 `envelope_transform.py:536` 的对称捕获，**只红 1 条**
（其本身的对称性单测）；端到端锁**仍然绿**，因为 `run_stage.py` 那侧的接线已足以接住。
⇒ 该修法**不是端到端必需**，是「两个调用点语义对称」的正确性修复。**如实记录，不阻断。**

---

## 4. 结论

- **代码审**：`fallback_action` 是只有两个取值的 `Literal`（`window_host.py:320`），构造器硬拦空 conflicts（:387）
  ⇒ 分类**全域覆盖、无兜底默认、无空集漏洞**，符合 F-7 立的「分类落在错误类型/抛出点、不匹配消息文字」口径。✅
- **`_BASE_SIGN` 与方向约定一字未改** ✅（用户定案未被触碰）。
- **⇒ PASS。** 可并入主分支。跟进债三条：§2 覆盖不对称 · §3.1 F-14 候选 · §3.2 路线②待签字。
