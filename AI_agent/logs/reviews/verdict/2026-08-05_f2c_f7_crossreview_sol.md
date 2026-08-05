# sol 跨家族对抗审 · F-2c + F-7 —— **REWORK（1 BLOCKER / 4 MAJOR / 0 MINOR / 0 NIT）**

- **日期**：2026-08-05
- **审阅席**：GPT 侧 **sol**（`gpt-5.6-sol`，effort=xhigh），经 codex CLI
- **审阅请求书**：[`../request/2026-08-05_f2c_f7_crossreview_brief_sol.md`](../request/2026-08-05_f2c_f7_crossreview_brief_sol.md)
- **被审**：`git diff 3310ed3..86ab24b`（F-2c `a8c367a` GLM 施工 · F-7 `a174fe8` Sonnet 施工）
- **总判**：**REWORK**

> **⚠️ 本文由 orchestrator 代为落盘**：sol 侧容器所有写操作（含 `apply_patch` 与 `/tmp` 写入）均失败于
> `bwrap: No permissions to create a new namespace` ⇒ 它无法写 verdict 文件，结论只存在于 CLI 输出。
> 下方 §1 为其结论**原文转录**，§2 为 orchestrator 的独立核实。**仓库未被 sol 改动过一个字节。**
> ⚠️ 同一故障导致 **sol 的定向 pytest 未能启动** ⇒ 其结论建立在**读码**而非跑测之上，判读时须计入这一点。

---

## 1. sol 结论（原文转录）

- **BLOCKER**：请求书规定的真实 sm21 `1_correction` accepted attempt 并未产生；轻门也在 `:82` 明确认账"未达成"。
- **MAJOR**：v3 catalog 仍允许 `None` 静默回退；旧调用会先耗费 LLM 请求，再在执法侧失败。
- **MAJOR**：`window_sources.py:841` 把模型输出楼层数错误误归为 input integrity，导致硬崩而非归档重抽
  ——**证伪分类双向分辨力的泛化结论**。
- **MAJOR**：`parse.py:82-91` 的两个 `model_draw_error` 会被 `_call_json_llm` 包装成 `RuntimeError`，
  根本到不了 `_draw_correction` 的分类分流。
- **MAJOR**：F-2c mirror 写入未处理 stage root 的陈旧 `*_view.json`，且 accepted pointer 先于 mirrors 落盘；
  干净 tmp fixture 掩盖了真实前态下的"先接受、下一段再崩"。

**未证伪的三项**（orchestrator 请求书 §5 自查项）：合并漏填扫描 · 翻译层 neuter · 单一探测器双向锁。
`git diff --check` 通过。

---

## 2. orchestrator 独立核实

| sol finding | 核实结果 |
|---|---|
| **MAJOR ②**（`window_sources.py:841` 误归类）| ✅ **属实**。`_check_floor_order` 首行：`if refs != list(range(1, len(refs)+1)) or len(refs) != len(producer.floors)` ⇒ **`producer.floors` 是模型的输出**。模型少写/多写一层 ⇒ 抛 `manifest_floor_ref_non_contiguous` 且 `category="input_integrity_error"` ⇒ **硬崩，不归档不重抽**。而这是典型的「模型抽签写错」。 |
| **MAJOR ③**（`parse.py` 分类到不了消费侧）| ✅ **属实**。`parse_correction_draw` 只在 `_schema_only_correction_validator`（`pipeline.py:587`）与 `_make_correction_validator`（`:611`）里被调用，二者都是喂给 `_call_json_llm` 的 validator ⇒ 异常被内层重试循环吞掉，最终包成 `RuntimeError(f"{prefix}: failed after N attempt(s)")` ⇒ **永远到不了 `_draw_correction:411/422` 的 `except WindowResolverInputError`**。那两处 `category="model_draw_error"` 是**死标注**。 |
| **MAJOR ①**（catalog 静默回退）| ✅ 属实，且**正是 orchestrator 在请求书 §6 主动请它打的那条** ⇒ 判定成立，修法方向随之明确（v3 目标下应升为前置条件）。|
| **MAJOR ④**（F-2c mirror 陈旧文件 / 落盘次序）| ⚠️ **未独立核实**（sol 自身跑测未能启动，此条纯读码）。**排在返工首位待验**：需实测「stage root 已有陈旧 `*_view.json` + 隔离 merge」这一真实前态。|
| **BLOCKER**（真实产物未出 accepted attempt）| ✅ 事实属实，orchestrator 轻门 §5 已自认。**但归因需分开**：其直接原因是**下一道墙 F-9**（`resolve_window_hosts` 拒收），不是这两批的缺陷。⇒ orchestrator 判定：**作为「本批验收条件未达成」成立**，作为「本批实现有错」不成立。返工批应把它作为**出口条件**继续持有，⛔ 不得改口径绕过。|

---

## 3. ⭐⭐ orchestrator 自我更正（本次审阅最贵的一条）

轻门 §3 我做了三格 neuter（禁用翻译 / 一律判模型错 / 一律判输入错），每格恰好红它自己那条锁，
据此我在请求书 §5 写下自查项「**分类判据双向分辨力**」。

**sol 的 MAJOR ② 证伪了这条结论的泛化范围，而且它是对的。**

> **我验证的是「分类机制有分辨力」，不是「每个抛出点的归类是对的」。**
> 前者是**机制**，后者是**逐点判断**——两者之间还隔着约 40 个抛出点，我一个都没审。

这正是本项目 08-04 那条教训**又长了一层**：

- 08-04 版：**neuter 变红只证明「实现被调用了」，不证明「判据有分辨力」。**
- **08-05 新增：分辨力实测只证明「机制能分辨」，不证明「每个抛出点分得对」。**
  **⇒ 凡「由抛出点自行归类」的设计，必须逐点审计归类正确性；机制级 neuter 不能替代。**

⚠️ 且我在请求书 §5 把这条列成「已自查、能证伪比新增 finding 更有价值」——
**这个写法本身是对的**（它确实促成了本次最有价值的一条 finding），但**结论的措辞下得过宽**，属我的错。

---

## 4. 返工排序建议（待用户拍板）

| 序 | 事项 | 依据 |
|---|---|---|
| 1 | **逐点审计全部 `category` 归类**（约 40 处），至少修 `_check_floor_order` 那处 | MAJOR ② + §3 的新纪律 |
| 2 | **`parse.py` 两处死标注**：要么让分类可达（异常穿透 validator），要么删掉标注并明说走内层重试通道 | MAJOR ③ |
| 3 | **catalog 静默回退升为前置条件**（v3 目标下缺清单即明确失败）| MAJOR ① + 请求书 §6 |
| 4 | **实测核 MAJOR ④**（真实前态：stage root 有陈旧 `*_view.json`），再决定改法 | MAJOR ④ 未核 |
| 5 | **BLOCKER 继续持有为出口条件**，随 F-9 一并解 | 见 §2 |
