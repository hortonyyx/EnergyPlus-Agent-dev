# 跨家族复核请求 · **接线（模块 7 上半）v2**

- **日期**：2026-09-02 · **请求方**：orchestrator · **复核方**：**GPT 家族**（⛔ 不得 GLM —— 施工方是 GLM）
- **被审 commit**：**`17d998e`**（施工方原件 `687820f`，`cherry-pick -x` 落分支，内容逐字相同）
- **派工单**：[v2 单](2026-09-02a_wiring_module7_dispatch_v2.md) ·
  **前一轮停报裁定**：[题错 #70](../verdict/2026-09-02a_wiring_module7_stop_report_ruling.md)
- **施工方执行档**：[`2026-09-02b_wiring_module7_v2_glm.md`](../execution/2026-09-02b_wiring_module7_v2_glm.md)

**被审 diff（生产代码 + 测试）**：
```
src/agent/pipeline.py                    +437  -3
src/agent/correction/decision_schema.py   +72  -1
src/agent/correction/decision_executor.py +48  -7
src/agent/reading/vector_contract.py      +53 -11
src/configs/llm.yaml                      +18
tests/test_o22m7_evidence_wiring.py      +739（新）
tests/{f97,o22m1,o22m2,o22m3}             +73 -28（翻 pin 锁）
```
⛔ **只看原始需求 + diff + 测试输出**，不必读执行档长篇。

---

## 一、⭐⭐⭐ 这一件的分量：**新链第一次真的跑起来了**

施工方报：真实 `sm25_2f_v2.json` → **`success=True` / 2 轮 / 185.8 秒**，
`response_source=model:correction_decision`（deepseek-v4-pro，round 0 裁决 22 项、round 1 对新 provisional accept）。

**请求方已核的**（⛔ 未复跑模型，只核落盘证据）：
`_run/evidence_chain_route.json` 确写 `"response_source": "model:correction_decision"` 与 `outcome_success: true`；
`decision_loop_outcome.json` 带真实 packet/decision 双哈希与 22 条 item id。
全量尾：**`3654 passed / 13 xfailed / 0 failed`（`-n 6`，8:06，EXIT=0）**。

⇒ ⭐ **请你重点判「这次跑通是不是真的」**，⛔ 别只判代码好不好看：
1. `response_source` 这个字段**能不能被伪造**？它是**代码写的**还是**模型自报的**？
   （⭐ 同族 [[self-report-more-compliant-than-artifact]]：**自述总比产物更合规**）
2. 固定响应（fixture）路径与模型路径，在落盘产物上**分不分得开**？
   若分不开，那「模型真跑了」这个结论就没有载体。
3. `success=True` 是**四部分合取**（模块 6 docstring 自述）—— 请核**每一部分都真的被判了**，
   ⛔ 不是有一部分恒真。

## 二、⭐⭐ 施工方**自我披露**的一处，请你裁（它自己请求裁定）

它在 `as_ledger()` 增了 `"adapted"` 键、`VectorDirDecision` 增了 `adapted` 字段，
判定为「**加不改**」（现有字段含义与顺序未动），因此**不算派工单禁止的「ledger 重排」**。

⇒ **请你判这个边界。** 请求方独立查过：`as_ledger` 在 `vector_contract.py` 之外**零消费者**，
且该模块内**无任何哈希**（`grep sha256` 空）⇒ 请求方**倾向认可**它的判定，
⛔ **但这是施工方自己划的线，理应由你而不是我确认。**

## 三、请你打的三处（⭐ 请求方的疑点，写成**假说**，⛔ 未代判）

| # | 疑点 | 为什么怀疑 |
|---|---|---|
| **H1** | **`ADAPT` 的第五分支会不会造出「既不消费也不报错」的静默第三态？** | 派工单要求它 ⛔ 不进 `consumed`、⛔ 不当 offender ——**这两条同时成立，天然就长得像一个静默通道**。请实测：一份 ADAPT 文件在**新链关闭**时，到底发生什么？施工方说旧腿会「响亮拒绝」，请**独立验证**，⛔ 别采信 |
| **H2** | **翻掉的 8 把 pin 锁，保护的规则是不是真的活下来了？** | 派工单 §一A 硬要求「⛔ 不许删掉了事」。请核 `test_no_new_contract_became_consumable` 的**继任者**是否**同时覆盖 `consuming` 与 `adapting` 两个集合**；⭐ 并造一个「第三个合同偷偷变成 adapting」的变异实测它**能红** |
| **H3** | **「无坐标 guard」的绿是实现挣的，还是夹具挣的？** | 施工方说做了 neuter（摘掉 guard 后字符串走私畅通）。请独立重放 —— [[neuter-proves-wiring-not-discriminating-power]]：**变红≠有分辨力** |

## 四、⚠️ 环境（⛔ 本 worktree 里没有 `.env`，凭据不落盘）

跑全量前在同一个 shell 先执行：
```
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
```
否则 `tests/test_zone_agent.py` **必红一条** = **F-158 已知环境红**，与被审 diff 无关。
⭐ **注意一处不对称**：GLM 席位经 `glm_code.sh` 启动，那个脚本**自己会 source `.env`**
⇒ **它从来没看见过这条红**；而 Claude/GPT 席位会看见。⛔ 别把这条差异读成谁的回归。

## 五、常规项

1. v2 单 §三 的**七条验收**（1 / 2 / 3 / 4 / 4b / 5 / 6）逐条**独立复跑**，⛔ 别采信执行档读数。
2. ⭐ 指南 §五#2：**再找一种能骗过它的真实错误形态**。
3. 环境自证与 pytest 同一条命令：
   `python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest ...`
4. 跑测 **`-n 6`**。
5. 裁决 → `AI_agent/logs/reviews/verdict/2026-09-02d_wiring_module7_v2_crossreview_gpt.md`，
   给 APPROVE / APPROVE-WITH-FINDINGS / REWORK + 阻断数 / 不阻断数。
