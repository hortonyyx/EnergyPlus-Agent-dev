# 跨家族复核请求 · F-97 契约判别器（correction 只吃声明过的契约）

- **日期**：2026-08-27　**复核席位**：**GPT 家族 sol**（只读；⛔ 谁写谁不批）
- **施工席位**：**Claude 家族**（worktree `/tmp/ep_f97`，分支 `wt/08.27_f97_contract`）
- **被审 commit**：`8fda4c1`（前一提交 `e08c79b` 是它的「停下上报」，一行源码未改）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_dispatch.md`
  —— ⚠️ **必读它末尾的「⭐⭐⭐ 补充裁定（2026-08-27）」整节**：施工方第一轮**停下上报顶回了我三条错**，
  三条裁定是在那之后才定的，**验收判据被整表重写**（B1′/B1″/B2′/B3′/B3″/B3‴/B4′/B5）。
- **施工方自述**：`AI_agent/logs/reviews/execution/2026-08-27_f97_contract_discriminator_construction_report.md`
  （⚠️ **只作线索，不作证据**）

## 〇、工作目录与纪律

```
/tmp/ep_f97      ← 被审 worktree 本体，HEAD = 8fda4c1
```

- ⛔ 不许碰 `/workspaces/EnergyPlus-Agent-dev`（主树）；⛔ 不许替它改代码（探针做完必须还原）。
- ⚠️⚠️ **跑全量用 `python -m pytest -q -n 4`** —— 同机另有一个跨家族复核在跑全量，
  实测 `-n auto` 在高负载下**整场崩**（worker `OSError: cannot send`、**无 summary 行**）= 假红，重跑即可。
- ⛔ 裸跑脚本会因共享 venv 的 editable `.pth` 静默串到主树；一律 `python -m` 或 pytest。
- ✅ `.env` 已软链；基线 = `3035 passed / 13 xfailed / 0 failed`；本 commit 施工方报 `3058 passed`。

## 一、缺陷与做法（一段话）

`pipeline.py:discover_vector_files` 把 `0_reading/` 下**所有** `*.json` 分成 plans / elevations / **others**，
然后逐份**原样贴进 correction 的提示词**、不经任何门 ⇒ 新格式 as-drawn 产物会走这条**沉默路径**。
本单加**契约判别器**：已知契约 → 正常消费或「认识但本阶段不消费」的**响亮失败**；
未知契约 → **响亮红并点名**；并产一份**消费对账**。

三条裁定（补充裁定节）：
**① 锚 `as_drawn_plan_v2` 且必须 import 生产者常量**（`as_drawn_v2.py` 的 `SCHEMA`），⛔ 不抄字面量；
**② `stage_check_report`（`*_checks.json` 边车）= 第 4 类契约 ⇒ 声明式排除 + 对账点名**，⛔ 不红、⛔ 不静默；
**③ legacy 判据 = 能按 `src/agent/reading/schema.py:ReadingView` 解析成功 且 带非缺省 `strokes`**，
⛔ `dimensions` 不进签名（会误杀 6 份真历史产物）。

diff：`src/agent/reading/vector_contract.py`(+310, 新增) · `src/agent/pipeline.py`(+44) ·
`tests/test_f97_vector_contract.py`(+347, 23 例) · `scripts/tool_scripts/affected_tests_rules.yaml`(−18)。

## 二、⭐⭐⭐ 请你重点打的四处（按价值排序）

### 2.1 ⭐⭐⭐ 施工方自己点名的最弱处：**它删了 4 条 `affected_tests` allowlist，而新覆盖是「import 边」不是行为**

原话：「我只 import 了一个常量，`_plan_ink.py` / `pens.py` **一行逻辑都没跑**。它们现在**看起来被覆盖了、实际没有**。」
⇒ 这是 [[proxy-mistaken-for-the-thing]] 的形状，而且它动的是**「改了哪些文件要跑哪些测试」的映射表** ——
**判错会让将来某次改动的相关测试根本不被选中**（一条静默失效通道）。
**请你判：这 4 条该不该删；若不该，是不是阻断项。**

### 2.2 ⭐⭐ B1″ 那 170,455 字节的行为变化，**方向对不对、范围够不够**

它报告：56 个 `0_reading/` 目录里 **7 个**的提示词改变，**只减不增**，减掉的**全是 `*_checks.json` 边车**
（43 份），⛔ 无任何 `*_view.json` 被移除。**请独立复核这三件事**：

- 真的**只减不增**吗（有没有哪份原本没进提示词的东西现在进去了）；
- 减掉的**真的全是 gate① 报告**吗（有没有误伤真 reading 产物）；
- 它自陈「56 个目录是**可测全集**、不是真全集」—— **这个口径的漏网面有多大**。

### 2.3 ⭐⭐ 三种「已知但不消费」的行为**真的可区分**吗

判据要求三种报文互不混淆：**未知契约**（红，含 `unknown contract`）· **as-drawn**（红，含 `no wire for it`、
⛔ 不含 `unknown contract`）· **`stage_check_report`**（⛔ 不红，排除 + 对账点名）· 外加**双命中 ⇒ `AMBIGUOUS`**。
施工方称四条都过。⭐ **请你自己造夹具复验**，特别是：
**有没有哪种真实输入会掉进「都不匹配又不该红」的缝里**（= 新的静默通道）。

### 2.4 ⭐ 施工方自陈的另外三条不确定，请逐条定性（阻断 / 不阻断）

1. **as-drawn 的 checks 报告（45 份）没登记** ⇒ 真放进 `0_reading/` 会**响亮红**。
   它按不扩范围决定不登记，但理由锚在「**现在的产物分布**」而非「**代码能不能产出它到那里**」
   —— [[is-this-conclusion-product-side-or-code-side]] 警告的形状。
2. **`stage_check_report` 的签名仍是归纳的**（没像 legacy 那样搬到生产者类型上）
   ⇒ 同一份代码里两个契约成色不同。
3. B1″ 的全集口径（见 2.2）。

## 三、⚠️ 施工方主动报的两个过程失误（请以 diff 复核其后果）

- 两次用**行号做文本替换**、两次都替错位置（覆盖了一个 `_write(...)`；把 `sorted(...)` 塞进字典），
  第二次靠 `SyntaxError` 才发现。⇒ **请优先逐行核测试文件的完整性**（有没有哪条断言被替没了）。
- **它在一次 neuter 全量跑着时改了树**（换行整形），当场作废并重跑；最终读数取自干净的一跑。
  ⇒ 请核实最终读数确实来自干净树。

## 四、验收判据（每条我都自查过「什么情况下它会不通过」）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| A1 | 你独立跑全量（`-n 4`），三数报出来 | 有回归；⚠️ 无 summary 行的崩溃是同机竞争假红，重跑 |
| A2 | §2.1 那 4 条 allowlist 删除的定性 | 覆盖是 import 边而非行为 ⇒ 该判阻断而没判 |
| A3 | §2.2 三件独立复核给出读数 | 有增无减 / 误伤真产物 / 漏网面被低估 |
| A4 | §2.3 你自造夹具复验四种行为可区分，并**主动找那条缝** | 存在「都不匹配又不该红」的静默通道 |
| A5 | neuter 复验：摘接线后应**只红它自己的 4 条**、零附带；摘 import 换字面量应让反字面量锁变红 | 锁没接真实入口 / 连带外溢 |
| A6 | §三 两个过程失误的后果核实（测试断言完整性） | 有断言被替没了 |

⛔ **「全量绿」不得单独作为通过标志。**

## 五、⛔ 停下上报触发器

1. §一 / §二 里 orchestrator 陈述的任何一条事实不成立；
2. ⭐ 你发现严格更优的第三条路（**明确算触发器**；本项目累计 **36 次「停下上报」全部是派工方题错**，
   今晚已有两次分别由施工席位与跨家族复核方替我触发）；
3. 要动被审范围以外的文件才能完成；
4. 你判断应 REWORK 但把握不足 ⇒ 摆证据交 orchestrator。

## 六、交件形式

裁决写到 `/tmp/ep_f97/AI_agent/logs/reviews/verdict/2026-08-27_f97_contract_discriminator_gpt_verdict.md`，
并把**全文贴回**（worktree 会被回收）。必含：总判 · §四六条判据逐条读数 · §二四处实测结论 ·
findings 分「阻断 / 不阻断」· 你自己跑的全量三数 · ⭐ **以及「你认为 orchestrator 题面写错的地方」**。
