# 派工单（GLM 席位）· F-9 候选 —— `resolve_window_hosts` 拒收，**只读调查**

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **席位**：GLM-5.2
- **性质**：**纯只读调查。⛔ 不改任何生产代码、⛔ 不改任何测试、⛔ 不提交代码。**
  产出 = 一份调查报告 + 修法方向建议（**方向由 orchestrator 与用户拍板，不由施工席自裁**）。

> **⚠️ 派工方自述**：本轮我已经出错七次（含两次 F-7 相关的错误预设、两次 worktree 环境题、一次基线数字口径题）。
> **本单里凡是与代码实情不符的地方，一律停下上报，不要硬做。**「停下上报」在本项目记功不记过 ——
> 本轮六次停下上报，六次都是我的题错了。**⛔ 也不要为了迎合我下面的猜测去找证据**：
> 我的猜测如果错了，请直接推翻它，那是本单最有价值的产出。

---

## 0. 背景：这是「端到端缺陷批」推进到的第 9 道墙

本轮打法 = 拿 **07-07 那份已知满分的 sm21 识图产物**跑真链路，把识图变量摘掉，
只问「除识图外这条链今天还通不通」。已逐条撞出并修掉 F-1…F-7（F-8 是新登记的独立缺陷，本单不涉）。

**每修好一条，链路就往前推进一段，下一道墙才露出来。** 现在推进到了几何内核。

## 1. 现象（orchestrator 已实测，不必重跑复现）

**跑测**：`case_tests/e2e_tests/sm21_anchor/run_2026-08-05_f7_verify_sonnet/`
（07-07 sm21 识图产物 · `exploratory` 档 · 标准 `flow` SOP · `--to 1_correction`）

**两次抽签，形态不同：**

**attempt 001** —— 被**正确归档**为失败 attempt（F-7 新分类生效，不是硬崩）：
```
correction.window_source_reference  fail
window source reference rejected (source_claim_undeclared):
  {'window_id': 'win_1F_N_1', 'claim': 'appearance'}
```
（模型把 `appearance` 挂到了**平面**来源上；平面只允许 `existence/host/along/width`。）

**重抽那次** —— **完全通过 `_claim_links`**，一路走到几何内核深处才崩：
```
run_stage.py:744  <lambda> -> _draw_correction
run_stage.py:416  finalize_correction_draw
finalize.py:120   apply_deterministic_core
deterministic.py:1061  _apply_envelope_reconcile
deterministic.py:778   apply_v3_envelope_transaction
envelope_transform.py:536  _dry_resolve_current_ring
envelope_transform.py:478  resolve_window_hosts
window_host.py:877  raise WindowHostResolutionError(tuple(conflicts))
src.agent.correction.window_host.WindowHostResolutionError: window host resolution rejected
```

**⚠️ 整个 traceback 一个诊断细节都没有** —— `conflicts` 元组的内容**从未被打印或落盘**，
只有一句 `window host resolution rejected`。**与本批 F-3 那条「两段之后炸、报一句看不懂的话」同型。**

## 2. 请回答四个问题（按重要性排序）

### Q1 ⭐⭐ `conflicts` 里到底是什么？

把内容取出来，说清**哪几扇窗、冲突的具体形状**（哪个房间/哪面墙/坐标差多少）。

- 可以在 `/tmp` 下写一次性脚本复现（加载那份 accepted 的 reading + 重跑到 `resolve_window_hosts`）；
- **⛔ 不要为了打印它而改仓库里的代码**；
- 那次崩掉的抽签**没有落盘**（硬崩不归档），所以你可能需要重新跑一次 correction 抽签。
  **⚠️ 这会真调 LLM 并消耗额度** —— 如果你判断代价过高或抽签不可复现（模型有随机性），
  **停下上报**，我们改用 `run_2026-08-05_smoke_downstream_r2` 里已落盘的产物做离线分析。**先评估再动手。**

### Q2 ⭐⭐ 这是「模型真的画错了」还是「又一个接口错位」？

**判据（本批 F-5/F-7 都是后者，所以这条要认真答）**：
- 模型是否**拿得到**做对这件事所需的信息？
- 规范/prompt 里是否**告诉过它**这个约束？
- 消费侧要求的形态，生产侧**产得出来**吗？

如果是模型真画错了（比如窗户确实落在了两个房间的边界外），请说清**它凭现有输入能不能画对**。

### Q3 ⭐ 它该硬崩还是该归档重抽？

按 F-7 这次落地的分类口径评估（用户 08-05 拍板：模型抽签写错 ⇒ 归档重抽；输入完整性坏 ⇒ 硬崩）。
注意 `WindowHostResolutionError` 是**另一个异常类**，**不在** F-7 新加的分类覆盖面里。

**⛔ 只给判断和证据，不要动手扩覆盖面。**

### Q4 ⭐ 「抛异常不带诊断」这条本身要不要单独治？

`window_host.py:877` 把 `conflicts` 塞进异常却从不呈现。评估：
- 这条是不是普遍现象（`src/agent/correction/` 与 `src/agent/geometry/` 下还有几处同形）？
- 若要治，最小改法是什么（**只给方案，不动手**）？

## 3. 交回

报告落 `AI_agent/logs/reviews/execution/2026-08-05_f9_window_host_investigation_glm.md`，含：

- 四个问题的逐条回答 + **证据（文件:行 / 实测输出原文）**；
- 修法方向建议（可以有倾向，但**明确标注这是建议、待拍板**）；
- 如果推翻了我在 §1/§2 里的任何预设，**请直接写「orchestrator 的预设 X 不成立，证据是……」** —— 这是本单最有价值的产出。

**⛔ 提交纪律**：只提交你这份报告文档（`git add` 单个文件），**⛔ 不许 `git add -A`**
（工作树里有 orchestrator 的未提交文档 + 若干未跟踪的跑测产物目录）。**⛔ 不要 push。**
**做完一件存一件**（容器 OOM 会带走会话，本项目实犯过两次）。
