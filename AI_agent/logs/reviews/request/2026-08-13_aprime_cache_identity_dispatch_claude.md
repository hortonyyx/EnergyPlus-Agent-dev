# 派工单 · 摊 A′ —— 判卷侧三个收口：F-24 缓存身份 · MINOR-A1 拒判仍显 PASS · NIT-F25 同名常量

- **日期**：2026-08-13
- **席位**：Claude 侧执行档（Sonnet 5）
- **审阅去向**：GPT 侧 sol（与摊 A / 摊 C 合并进第四轮复审）
- **依据**：[round3 裁决书](../verdict/2026-08-12_round3_full_body_crossreview_sol.md) §6（F-24 / F-25）+ §3.1 末（MINOR-A1）
- **前置**：摊 A（BLOCKER-1）已完工并过 orchestrator 轻门；摊 C 已完工。
  **当前工作树基线 = `2568 passed / 10 xfailed / 0 failed`**（orchestrator 独立实测，rc=0、汇总行在）。

---

## 0. ⭐ 停止规矩（分层）

1. **承重前提错**（错了则任务方向作废）⇒ **立即停下上报**。
2. **外围论据错**（不改变方向）⇒ **报告里写明「派工方这句错了 + 你的实测」，继续做完主体**。

派工方历史错误率 **16/16**（今天早上刚新增一条：给摊 C 写的「只动这些文件」与「全仓必须绿」互相冲突，
因为仓里有一把既有锁硬断言了要被推翻的旧语义）。⇒ **§2 每条前提都请主动证伪。**

## 1. ⛔ 为什么 F-24 必须在**这一摊**做完（时间窗，orchestrator 实测）

**F-24 不是「以后再说」的债，它的截止点就在今天这一轮里**：

- 用户已拍板：摊 A 修完要**真跑一次完整链路**（现有正确产物没有印章⇒也被拒判，需重跑一次拿回分数）。
- 那次重跑会**写出本仓第一份新版判卷侧车缓存**。盘上现有侧车最高 `scorer_schema = 9`（29 份具名版本：
  9×20 / 8×4 / 7×4 / 6×1，另 1 份无版本 legacy），**摊 A 已把 `SCORER_SCHEMA` 从 `"10"` 提到 `"11"`**
  ⇒ 今天不会命中陈旧缓存（**这条「当前零影响」前提 sol 与 orchestrator 都已核实成立**）。
- **但那道 fail-open 门是从「第一份新缓存落盘」那一刻起才真的敞开的。**
  ⇒ **F-24 必须排在那次重跑之前。** 这是本摊存在的理由。

## 2. 三个要修的东西

### 2.1 `MAJOR-F24` —— 缓存没有绑定「判卷此刻期望的信任身份」

**⛔ 先纠正一个容易写错的表述**（sol 已纠，orchestrator 也曾写宽）：
缺口**不是**「内嵌印章状态完全不在 cache key 里」—— 同一份产物的印章字段从缺失变成存在，
`output_hash` 会跟着变，现有 key 已经会 miss。

**真正缺的是「scorer 当前接受的 core stamp version / convention trust policy 身份」**：
同一份 output bytes，在 `DETERMINISTIC_CORE_STAMP_VERSION` 从 `1` 升到下一版之后，
**应当从 trusted 变 untrusted**，但 `_load_valid_score_sidecar`（`scripts/tool_scripts/run_stage.py`，
判据 = `output_hash` + `stage` + `attempt` + `scorer_schema` + `tolerances`）**仍会直接复用旧缓存**。

**修法（sol 给的口径）**：在**侧车与 cache predicate 两处**显式加入至少
`expected_deterministic_core_stamp_version` · output-convention / trust-policy version ·
scorer implementation identity；**或**定义一个由这些量 canonical hash 得到的 `scoring_semantics_sha256`。
> ⛔ **sol 明确：只靠「工程师记得手动 bump `SCORER_SCHEMA`」不足以绑定跨模块版本。**
> ⇒ 你加的身份量**必须由那些常量/策略实际派生**，不许是又一个手写常量
> （**「不与行为绑定的声明 = 带变量名的注释」这个形状昨天一天现形三次、今天早上又一次**）。

### 2.2 `MINOR-A1` —— 拒判时 `boundary_complete` 仍单项显示 PASS

`src/agent/judge/score_policy.py:249-303` 把 `boundary=None` 计成 `0/0`，
再由 `missed_boundary == 0` 得出 `boundary_complete = pass`
（实测形态：`boundary_hits=0/0; missed=0; no_data_floors=2` ⇒ `pass`）。
整体没有伪装成全对（`walls_complete=severe` + `score_evidence_completeness=severe` 已在守），
**但这一项自己在说反话。**

**修法**：`no_data_boundary_floors > 0` 时让 `boundary_complete` 明确 **severe / unavailable**。
⛔ **不许靠另一条 criterion 替它纠正含义**（sol 原话）。

### 2.3 `NIT-F25` —— 两个同名常量不表达同一合同

`scripts/tool_scripts/run_stage.py:103` 的 `SCORER_SCHEMA`（现为 `"11"`）= **legacy attempt cache label**；
`src/agent/judge/score_schema.py:40` 的 `SCORER_SCHEMA = "8"` = **typed contract label**。
**没有运行时错配**（既有锁 `test_legacy_scorer_schema_is_independent_of_typed_v8_contract_label` 已钉住独立性），
纯审计认知负担。**修法 = 把前者改名 `LEGACY_SCORE_CACHE_SCHEMA`**，后者沿用既有 `SCORE_SIDECAR_SCHEMA`。
⛔ **不许借机改任何行为**；若改名会牵动超过纯符号替换的东西，**停下上报**。

## 3. 验收条件

1. **F-24 必须同时有正反两把锁**（⛔ 这条最重要）：
   - **反向**：构造一份合法的新版缓存，**只改 live expected stamp version**（其它一切不变）
     ⇒ 缓存**必须失效**、必须重算。
   - **正向**：身份一致时缓存**必须命中**（否则你只是把缓存关掉了）。
   > ⛔ 缺正向锁 = 本项目 F-19 那个「只有负向断言的门，恒红结构上不可观测」的老坑；
   > 摊 A 正是靠一把正向 happy-path 锁才发现了自己算错哈希源的真 bug。
2. **A1 的锁**：`no_data` 情形下断言该项**不是 pass**；并**自证前提**（先断言旧口径在该夹具上确实给出 pass）。
3. **neuter 实测**：每把新锁中和其守护的实现后必须转红 + 核对红点位置 + 回答
   **「不加这处改动，这道门本来红不红」**。⚠️ 打印式探针用 `-n0`（`-n auto` 吞 worker stdout）；
   **探针零输出 ≠ 目标不存在**，先自证探针看得见目标。
4. **全仓**：`python -m pytest tests -q -n auto`，与基线 `2568 passed / 10 xfailed / 0 failed` 对账、零回归；
   **判跑完看 `N passed` 汇总行**；退出码文件**用新文件名**（⛔ 不许跨两次跑复用）。
5. **⛔ 防假验证自检**：写明你的验收路径**真的经过**了 `_load_valid_score_sidecar` 那个判据本身。
6. **如实分账**：实测 / 推理 / 未验各自列清。⛔ 不许把未验证项写成已验证。

## 4. 运维

- 本摊**必须能在一个 5 小时额度窗内收尾**；判断做不完就停下上报，
  ⛔ 不要停在「改了行为、锁一把没写」的中间态。
- **现在工作树上没有别的施工席位**（摊 A / 摊 C 均已完工、改动未提交）。
  ⛔ 仍然绝不 `git add -A` / `stash` / `checkout`；⛔ 不要 commit —— orchestrator 统一提交。
- 中断时**不要总结自己做了什么**（本项目已三次实证席位自述不可信，一律以 `git diff` 为准）。
