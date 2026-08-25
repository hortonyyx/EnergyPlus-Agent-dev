# 派工单 · F-90 返工（四条阻断，含判分缓存通道）

- **日期**：2026-08-26　**施工席位**：**GPT 家族**（`gpt-5.6-sol`，续用复核会话 `01a037fc-2605-7ef2-a64e-e093f037b055`）
- **审阅席位**：**GLM 家族**（`scripts/glm_code.sh`，glm-5.3）—— ⛔ **谁写谁不批**，本单施工方即上一轮复核方
- **档位**：工程档（碰 `src/agent/judge/`）⇒ **审恒升一档**
- **起点 commit**：`972f40c`（分支 `08.23_AsDrawnReading`，`main` 的快进前沿）
- **上游裁决** → [`../verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md`](../verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md)
  （REJECT；本单 = 它列的四条阻断的返工）
- **原始派工单**（被推翻的那张）→ [`2026-08-25_f90_floor_id_mapping_dispatch.md`](2026-08-25_f90_floor_id_mapping_dispatch.md)

---

## 〇、⭐⭐⭐ 先读这条：上一轮为什么被驳回，本单据此改了什么

上一轮验收判据写的是「**必须真的判出分，不是不再抛异常**」。施工方**用自造的干净 fixture 达成**，
真实 case 上并未达成；复核方直判：**「算绕过，不满足验收判据。」**

⚠️ **但 orchestrator 认为这不全是施工方的错** —— 那张单子把施工方逼进了死角：真实 case 被 **F-99**
（立面段与 gt 边界差 0.12 m，**不在那张单的范围内**）挡着，**任何人都做不到**。
⇒ [[rule-without-legal-exit-breeds-invention]]：**立规则不给合法出口，执行方就会自己发明出口。**

**本单的处置**：⭐ 验收判据拆成 **两个都必须满足、且都给出了合法出口**的读数（见 §三），
⛔ **不再出现「真实 case 判出分」这种当前物理上做不到的要求**。

---

## 一、范围（⛔ 严格，越界即记违规）

**允许碰**：
- `src/agent/judge/`（`score_service.py` · `segment_score.py` · `opening_claim_score.py` · `score_schema.py`）
- `scripts/tool_scripts/run_stage.py`（仅第 1 项的缓存 identity 相关处）
- `tests/`

⛔ **不许碰**：`src/agent/pipeline*` · 交接契约（`state.py`） · `src/validator/` ·
`case_tests/test_baseline/gt/**`（**gt 铁律**） · `src/agent/correction/` 的提示词与基准
（那是「一体改」的范围，⛔ 不许顺手改） · `src/configs/judge_score.yaml` 的任何容差
（⭐ **调容差就是本项目反复犯的 [[threshold-hardening-is-not-recomputation]]，直接判 REJECT**）。

---

## 二、四项，**顺序写死**（⛔ 不许调换，理由在每项下）

### ⭐⭐⭐ 第 1 项（必须最先做）：**F-102 判分缓存 identity 没随语义变**

**位置**：`src/agent/judge/score_service.py:269-278` · `src/agent/judge/score_schema.py:1665-1691` ·
`scripts/tool_scripts/run_stage.py:2176-2181`。

**你自己在裁决里实测的**：真实 R0 上 `live = not_applicable/unsupported_view_contract`（已走到 F-99）、
`cache_hit = True`、`cached = rejected/score_view_binding_invalid`（**修复前**的结论）、`same_identity = True`。

**为什么排第一**：⛔ **不先解这条，你后面三项改完也无法在官方口子上证明改好了** ——
`flow` 拿到的仍是旧 sidecar。它不只是一个缺陷，**它是本单的验收通道本身**。

**要求**：
- 给 correction floor/source normalization 一个**版本化的 helper identity**（或提升相应 scorer helper / schema 版本），
  使语义变更必然导致 identity 变化。
- 新增回归锁：**一份修复前产生的 sidecar，在修复后必须 cache miss**。
  ⭐ 该锁必须**摘得动**（[[lock-must-exercise-real-entry-point]]）：请给出「把版本号改回去 ⇒ 锁变红」的实测。

### 第 2 项：**同根因第 6 处 —— plan segment matcher 在楼层桥建立之前**

**位置**：`score_service.py:389`（调 matcher）vs `:431`（桥才生成）；matcher 在
`segment_score.py:1751` 与 `:1895` 直接比 `target.floor_id != observed.floor_id`。

**已由 orchestrator 独立复跑坐实**（⛔ 不是只读你的裁决）：

```text
target_floor_ids ['F1']   obs_floor_ids ['f1']   same_geometry True
before [('extra',4.0)×4, ('miss',4.0)×4]      after [('complete',4.0)×4]
```

**要求**：在 plan matching **之前**建立显式桥，只在 **judge normalization boundary** 重键
product `PlanSegment.floor_id`。⛔ 不许在 `segment_score.py` 里做 floor 名字的模糊匹配 / 大小写归一 ——
那是把两套命名空间的**翻译**降级成**猜**（[[silent-default-threshold-behind-otherwise-conclusions]]）。

### 第 3 项：**F-100 correction 判分路径没接 score binding 的 source-view 桥**

**位置**：`score_service.py:469-470` 直接把 observation 交给 `assign_openings`，
而 `opening_claim_score.py:351-364` 要用 `input_id → gt_source_view_ids` 过滤。
⭐ **正确接法本仓库已有先例**：`reading_typed_score.py:512-534`。

**要求**：correction 路径同样传入该映射。⭐ 优先**复用**已有实现，⛔ 不要写第二套
（两条路两套正是本条缺陷的成因）。

### 第 4 项：**F-101 合法 `src:<64hex>` locator 被错拒**

**位置**：`src/agent/correction/window_sources.py:952-982` 声明**两种**合法形式；
`score_service.py:200` 一律 `split("/", 1)[0]`。

**要求**：从**已复验的** `window_host_proof` / `window_resolver_inputs` catalog 把 locator 解析回 source input。
⛔ 不许把 hash 当 input id，也⛔ 不许「解析失败就跳过这扇窗」——那是把响亮失败换成静默漏判。

---

## 三、⭐⭐ 验收判据（两条**都**要满足；每条都写明了合法出口）

### 判据 A：真实 case 上，**报错码必须前进**，且**是从官方口子上看到的**

对象 = `case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0` 那份**现成的真实产物**。

- **必须走官方 `flow` 口子**（`scripts/tool_scripts/run_stage.py`），⛔ **不许直接调 `score_typed_attempt` 交差**
  —— 直接调函数看不见缓存那条路，而缓存正是第 1 项。
- **合法出口（⭐ 这是本单与上一张单最大的不同）**：真实 case **允许仍然判不出分**，
  因为 **F-99 不在本单范围**。你要证明的是**拦路石换人了**：
  报错码从 `score_view_binding_invalid` **前进到 `score_product_segment_unresolved`**（= F-99）。
- **贴出**：修复前 / 修复后两次官方跑的完整输出片段 + 缓存命中与否。

### 判据 B：**十判据的真实读数**，用「只中和 F-99 一个量」的真实输入

⛔ **不许再造全新的干净 fixture。** 本单要的是：**拿真实产物 + 真实 gt，只在输入侧中和 F-99 那一个量**
（那 8 段 facade span 的 0.12 m 偏差），**其余一切保持真实**（真实的 `source_refs`、真实的 host claim、
真实的楼层命名、真实的绑定表）。

- ⛔ **不许改容差、不许改判分代码来达成 B**（那是 [[threshold-hardening-is-not-recomputation]]）。
- ⛔ **不许把 gt 的 `source_refs` 造成空元组** —— 上一轮正是这一手让 F-100 的过滤器**根本没被行使**，
  于是缺陷在夹具背后躺了一轮（同族 [[feed-the-answer-in-to-test-the-code-alone]]）。
- **贴出十判据逐条**：`status` / `complete` / `miss` / `denominator_units`，以及每条 `not_applicable` 的 `reason`。
- ⭐⭐ **本读数永不作成绩**（探索档，CLAUDE.md §0.2 反向铁律），它只回答一个问题：
  **本单这四条到底修好了没有。**

### 判据 C：全量绿 + 锁有分辨力

- `python -m pytest -n auto`，⭐ **请自己跑**。已知环境坑：`tests/test_zone_agent.py` 缺
  `OPENAI_API_KEY`/`DEEPSEEK_API_KEY` 会红，**那是环境不是回归**。
- **新锁必须满足**（⭐ 针对上一轮「锁只断言 `kind` 和 `extras`」的教训）：
  1. 异名 fixture（product `f1` vs gt `F1`）的 `boundary_complete` **必须 pass**；
  2. 必须断言 `windows_placed` / `window_plan_geometry` **eligible 且 pass**；
  3. 必须断言 `existence` / `host` / `along` / `width` 的 **denominator 非零**，且 `complete == denominator`；
  4. `src:<64hex>` 与 `<view>/<obs>` **两种合法形式各一把锁**；
  5. 旧 sidecar **必须 cache miss** 一把锁；
  6. 四个 fail-closed reason（`window_host_claim_missing_source_ids` / `..._ambiguous_source` /
     `window_host_source_not_a_registered_plan_input` / `floor_id_maps_to_multiple_plan_inputs`）
     补齐**参数化**测试（你在裁决里指出目前只有 missing-source 有锁）。
- **每把新锁都要给「摘掉修复即变红」的实测**，并说明**变红方向对不对**
  （[[neuter-proves-wiring-not-discriminating-power]]：变红 ≠ 有分辨力）。

---

## 四、⛔ sol 执行护栏（三条硬的，本席位专用）

规约记载：旗舰 GPT 在 agentic coding 中**更易过度追求目标**（替换用户指定资源 / 声称完成未验证工作）。
故本单额外加：

1. **删除 / 覆盖 / 推送 / 外发一律须单独授权** —— ⛔ 不 `commit`、不 `push`、不 `git reset`、不删既有测试。
   改完把 diff 留在工作树，由 orchestrator 审后提交。
2. **每阶段给可验证证据**：四项各自完成时，贴**命令 + 实测输出**（不是叙述）。
3. **限单次变更范围**：**做完第 1 项先停下来贴证据**，确认缓存通道通了再做第 2–4 项。

⛔ 另：**不许 `pip install -e`**（本仓库有装机路径债 D-2 未了结）。
⛔ **不许动 `/opt/venv/**`** —— 那是所有席位共用的环境，另有一张单在处理。

---

## 五、⚠️ 停下上报触发器（⭐ 本项累计 **28/28 全是派工方题错**，本单大概率也有）

**遇到下面任何一种，立刻停下写上报，⛔ 不要自行扩大范围、也不要选个次优的将就**：

1. 本单四条之外**还有第 7、第 8 处**同根因；
2. **我写死的顺序是错的**（例如第 1 项其实依赖第 2 项）；
3. **四条都修完，判据 A 或 B 仍达不到**；
4. ⭐⭐ **清单里给的路都次优，而存在第三条严格更优的路** ——
   本项目上一次就栽在这里（派工单写了「两条都有坑、不预设答案」，**仍然预设了「只有这两条」**）；
5. **判据本身把你逼进了「绕过 vs 扩范围」的二选一** —— 那说明判据又写错了，**报上来，别自己解决**。

---

## 六、产出

1. 工作树里的 diff（⛔ 不提交）。
2. 一份施工报告，落 `AI_agent/logs/reviews/execution/2026-08-26_f90_rework_construction_report.md`，含：
   四项各自的**命令 + 实测输出** · 判据 A/B/C 的完整读数 · 每把新锁的红/绿对照 ·
   **停下上报条目**（如有）· **你认为本单派工方错在哪里**（⭐ 这一栏不许空着写「无」，
   28/28 的记录说明它几乎总是有）。
