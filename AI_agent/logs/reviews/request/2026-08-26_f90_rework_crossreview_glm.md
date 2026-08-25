# 跨家族复核请求 · F-90 返工五项（含验收通道 F-102/F-103）

- **日期**：2026-08-26　**对方**：**GLM 家族**（`scripts/glm_code.sh`，glm-5.3）
- **档位**：工程档（碰 `src/agent/judge/` + `scripts/tool_scripts/run_stage.py`）⇒ **审恒升一档**
- ⛔ **谁写谁不批**：**施工方 = GPT 家族**（`gpt-5.6-sol`），它同时也是**上一轮把这批问题挑出来的复核方**
  ⇒ **它不能审自己的修复**，所以派你。
- **被审 commit**：**`b735db4`（第 1/1b/2 项）+ `8ea9aca`（第 3/4 项）**，起点 `10f1469`
  ⇒ 一次看全量 diff：`git diff 10f1469..8ea9aca`
- **派工单** → [`2026-08-26_f90_rework_four_blockers_dispatch.md`](2026-08-26_f90_rework_four_blockers_dispatch.md)
- **施工报告**（⚠️ **只作线索不作证据**）→
  [`../execution/2026-08-26_f90_rework_construction_report.md`](../execution/2026-08-26_f90_rework_construction_report.md)
- **上游裁决**（本单的由来）→
  [`../verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md`](../verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md)

---

## 一、⭐ 请重点攻的六条

### 1. ⭐⭐⭐ 新信任根换了，换对了吗？

F-90 原实现从**窗户的 host 溯源**反推楼层桥；施工方走了派工单**没给**的第三条路：
改用**已复验的 resolver-input catalog**（产物楼层按 `z_floor` 排名 → manifest `floor_ref` → plan input），
窗户溯源降为**一致性佐证**、不一致即响亮失败。

orchestrator 已核过该契约确实存在（`window_sources.py:1030-1070` 的 `_check_floor_order`
+ `view_manifest.py:503-510`）。⭐ **请你独立判断更难的那一问**：
**这个换根是让信任链变强了还是变弱了？** 具体请攻：
- `_check_floor_order` 是否**在所有到达判分的路径上都必然跑过**？还是存在某条路能拿到 proof 却没过这个检查？
- `_resolver_inputs_from_verified_proof` → `_reverify_window_host_proof` 这条重验，**验的是什么、不验什么**？
- ⭐ **零窗户楼层**真的能判分了吗？请**构造一个零窗户楼层的用例实测**，⛔ 不要只读代码下结论。

### 2. ⭐⭐ 判据 A「通过」这个结论，你复现得出来吗？

施工称真实 R0 走官方 `run_stage._grade_typed_attempt_artifacts` 后，
`score_payload_detail` 从 `score_view_binding_invalid` 前进到 `score_identity_support_ambiguous`。
⭐ **请自己跑一遍**，⛔ 不要采信它贴的输出。并判断：
**「报错码换了一个」到底证明了什么、没证明什么？**（orchestrator 认为它只证明「本单四条不再是第一块拦路石」，
⛔ **不证明它们各自都修对了** —— 你同意吗？）

### 3. ⭐⭐⭐ 那七把 fail-closed 锁，有分辨力还是只会变红？

施工给了「摘掉两个 bridge helper ⇒ 七条全红」的实测。
⚠️ 本项目有过明确教训：**变红 ≠ 有分辨力**。请攻：
**有没有哪一条，是无论修没修都会红 / 或者随便动点别的也会红**？
⭐ 特别请攻这两条**命名与实情不符**的（施工自己在报告 §12 也列了）：
- locator **不在 catalog 里**时，抛的是 `window_host_claim_ambiguous_source` 且 `candidate_inputs: []`
  —— 「查无此源」被报成「有歧义」；
- 窗户在 catalog 里**一条 host claim link 都没有**时，也落进同一个 reason。
⇒ **这两处该不该各给专属 reason？** 请给结论。

### 4. ⭐⭐ 缓存 identity 这条防线，是防漂移的门还是一次性标签？

`CORRECTION_OPENING_MATCHER_HELPER_VERSION` 从 v2 一路手工提到 **v5**（每项语义改动提一档）。
⭐ 请判断：**下一次有人改了 correction 侧的规范化语义但忘了提版本，什么东西会拦住他？**
如果答案是「没有」，请明说这是**执行机制不是根治机制**（本项目上一轮 D-1 也是被这句话点掉的）。
⚠️ **本轮明令不许实施派生摘要**（另开单），所以这一条只要你的**判定**，不要你改。

### 5. ⭐ `tests/test_f102_score_cache_identity.py` 的前提能活多久？

该锁断言归档 R0 的 sidecar `opening_matcher == "reading_opening_global_assignment_v1"`。
⇒ **一旦有人把那份 sidecar 重跑并提交，这把锁的前提就没了。**
请判断：它会**响亮红**还是**静默变成恒真**？（本项目有条老账：回归用例必须自证前提。）

### 6. ⭐ F-103 只加信息没改分类，这个说法查得实吗？

施工称改前 `grep` 全仓**零个** `payload.detail` 消费者，且粗分类 `reason` 的四个取值一个没动。
⭐ 请自己 grep 一遍并**扩大搜索面**（含 `detail` 的间接读取、`model_dump` 后按键取值、下游 report/renderer）。
若有它漏掉的消费者，请点名。

---

## 二、验收判据

1. **全量绿**：`python -m pytest -n auto`，⭐ **请自己跑**。施工报的是 `3029 passed, 13 xfailed`。
   ⚠️ 已知环境坑：`tests/test_zone_agent.py` 需要 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY`，无凭据环境会红 —— **那是环境不是回归**。
2. **范围**：diff 应只含 `src/agent/judge/{score_service,score_schema,score_inputs,reading_typed_score}.py` ·
   `scripts/tool_scripts/run_stage.py` · `tests/**` · `AI_agent/logs/reviews/execution/` 那一份报告。
   ⛔ 碰 pipeline 内核 / `state.py` / `src/validator/` / gt / `src/agent/correction/` / 任何容差 ⇒ 记为越权，**请自己核**。
3. ⛔ **容差零改动**必须由你独立确认（`git diff 10f1469..8ea9aca -- src/configs/`）。

---

## 三、⚠️ 必答

1. **判据 B 未达成，施工方停下上报了**（说 0.12 m 被冻结在五处契约里，不是可独立替换的输入量，
   三次尝试各被不同的真实 validator 拒绝）。⭐ **这个「做不到」你认不认？**
   请**自己试一次**中和 F-99 的路 —— 如果你找到了一条既不绕过 proof、又不扩范围的路，那施工方就是偷懒了，请点名。
2. **「停下上报」累计 33/33 全是派工方（orchestrator）题错**，本单一家就贡献了 5 条（29–33）。
   ⇒ **这 5 条你都认同吗？还有第 6 条吗？**
3. ⭐ **本单最该被质疑的地方（orchestrator 自评）**：
   **真实 case 上的十判据读数至今不存在**（挡在 F-99 后面）。
   ⇒ **在这个前提下，说「F-90 修好了」的证据强度够不够？** 请直说。

---

## 四、产出

先给 **APPROVE / REJECT / APPROVE-WITH-FINDINGS** 一句话结论，再逐条列证据（**指到文件行或命令输出**）。
⛔ 只审：不改文件、不提交、不 push。需要做对照实验请 `git worktree add` 到 `/tmp` 下改副本，用完 `git worktree remove --force`。
⛔ 不要 `pip install -e`；⛔ 不要动 `/opt/venv/**`。
