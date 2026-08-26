# 派工单 · F-97：correction 只吃声明过的契约，未声明的形态响亮失败

- **日期**：2026-08-27　**施工席位**：**Claude 家族**（独立 worktree）　**审阅席位**：**GLM 家族**（⛔ 谁写谁不批）
- **档位**：工程档（碰 `src/agent/pipeline.py` = 管线内核 + 交接契约）⇒ **审恒升一档**
- **起点 commit**：`ed0ba09`（分支 `08.23_AsDrawnReading`）

## 〇、你的工作目录（⛔ 写死）

```
/tmp/ep_f97       ← 已建好的 worktree，分支 wt/08.27_f97_contract，起点 ed0ba09
```

- ⛔ **不许在 `/workspaces/EnergyPlus-Agent-dev`（主树）改任何文件、不许在主树跑全量。**
  主树上同时还有两个别的席位（一个改 `src/agent/judge/`、一个在审 `src/validator/`）。
- 跑测：在你的 worktree 里 `python -m pytest -q -n auto`。
  ⛔ **裸跑脚本会静默串到主树代码**（共享 venv 的 editable `.pth` 硬编码主树 = F-94 / 债 D-2）
  ⇒ 一律 `python -m <module>` 或 pytest。
- 开工自检：`git -C /tmp/ep_f97 log --oneline -1` = `ed0ba09`；`grep -c '' AI_agent/CLAUDE.md` = **447**。
  对不上就停下上报。

## 一、这件事在盘面上的位置

用户四步：**① 把判分修好 → ② 按新方案改造 reading+correction 的 harness → ③ 产出新产物 → ④ 验证**。
本单是 **② 的必做前置**：新的 reading 产物（as-drawn）落地后，
**它必须要么被正经消费、要么被响亮拒绝**，⛔ 不能像现在这样被当无名文本塞进提示词。

⭐ 本单是**代码侧**缺陷（换一份产物它还在），⛔ 不依赖任何具体 case 产物。

## 二、缺陷（orchestrator 已核实；⛔ 请你独立复现一遍再动手）

`src/agent/pipeline.py:84` 的 `discover_vector_files(vector_dir)` 把目录下**所有** `*.json` 分三类：

- `plans` = 文件名匹配 `_PLAN_RE` 的
- `elevations` = 文件名以 `_view.json` 结尾的
- **`others` = 其余全部**

返回 `plans + elevations + others`。然后在 `pipeline.py`（约 443 行）：

```python
for fname in vector_files:
    chunks.append(f"\n[reading vector] {fname}:\n```json\n{_read(vector_dir / fname)}\n```\n")
```

⇒ **任何一份 JSON，不管它是什么契约，都会被原样贴进 correction 的提示词，且不经任何识图门。**
⇒ 一份新格式的 as-drawn 产物（例如 `sm25_1f_v2.json`）放进 `0_reading/` 就会走这条**沉默路径**。

**两种产物的契约长相（我实测过）**：

| | 声明方式 | 顶层键 |
|---|---|---|
| **as-drawn**（新） | ⭐ **有显式声明** `"schema": "as_drawn_plan_v0"` | `schema` / `image` / `dialect` / `calibration` / `dimension_witnesses` / `wall_bands` / `unpaired_face_lines` / `ledger` |
| **legacy view**（现行在跑的） | ⛔ **没有任何显式 schema 字段**，只能靠结构认 | `image_label` / `image_kind` / `scale_origin` / `strokes` / `dimensions` / `ocr_texts` / `uncaptured` / `self_check` |

⚠️ 注意那个值是 `as_drawn_plan_v0`（**v0**），而管理文档里一直叫它「as-drawn v2」——
**名字对不上是现实**，⛔ 不要顺手改产物里的值来对齐文档，也不要假设还有别的值。

## 三、要做的三件

### F-a　契约判别器

在合适的位置（你定，但要能被 `discover_vector_files` 的调用侧用上）给出一个判别函数：
输入一份已解析的 JSON，输出它属于哪个**已声明的契约**，或 `unknown` + **为什么不认识**的理由。

- ⭐ 判别**优先看内容里的显式声明**（`schema` 字段），legacy 那种没声明的**才**退回结构识别。
  ⛔ 不要靠文件名正则去猜契约 —— 文件名正则是**排序**用的，不是契约。
- ⛔ 不要新造一套 schema 定义；如果仓库里已有可复用的识别件（例如
  `src/agent/reading/contract.py:identify_reading_contract` 是**信封级**的，不是**单文件级**的，
  ⚠️ 别把两者搞混），复用或说明为什么不能复用。

### F-b　未知契约 ⇒ 响亮失败

未知契约的文件**不得**被贴进提示词。行为 = **响亮失败**，报错点名：哪个文件、判成了什么、为什么。
⛔ **不许静默跳过** —— 静默跳过就是 F-64 家族「零产出不报红」，
和「文件根本不存在」在下游看起来一模一样。

### F-c　消费对账记录

把「这一次 run 里，每份 JSON 各以什么契约被消费了」写成一条可读记录（落 `_run/` 或现有 checks 产物里，
跟着现有产物纪律走，⛔ 别新开一个目录）。
⭐ 这条才是拓展性的兑现：**没声明过的形态从「静默漏」变成「点名红」**。

## 四、⛔ 明确不做（超出即停下上报）

- ⛔ **不改 correction 提示词里那两句 `wall-centerline` / `wall CENTERLINE`**
  （`pipeline.py` 约 365–369 行）—— 那是 reading/correction 一体改的本体，另有排期，本单动它会白改。
- ⛔ **不给 as-drawn 接线**（不让 correction 真的消费它）—— 同上，那是一体改本体。
  本单对 as-drawn 的正确行为见 §五 B3。
- ⛔ **不碰 `src/validator/data_model.py` / `checks/kernel.py` / `tests/test_f95_*` / `tests/test_f13_*`**
  —— F-95 正在跨家族审。
- ⛔ **不碰 `src/agent/judge/`** —— 另一个席位在改 gt 原始层。
- ⛔ 不改任何 reading 判分/容差。

## 五、验收判据（每条我都自查过「什么情况下它会不通过」）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| B1 | 现有历史产物（如 `case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/0_reading/*.json` 六份）全部被判成**已知 legacy 契约**，correction 的提示词组装**逐字节不变** | 判别器把在跑的东西判成 unknown ⇒ 直接打断现网路径 |
| B2 | 造一份**未知契约**的 JSON（例如 `{"hello": 1}`）放进 vector_dir ⇒ **响亮红并点名该文件** | 判别器把未知的当已知，或静默跳过 |
| B3 | ⭐ 放一份真的 as-drawn 产物（`"schema": "as_drawn_plan_v0"`）进去 ⇒ 正确行为是**「认识这个契约，但当前 correction 不消费它」的响亮失败**；⛔ 不是当 others 贴进提示词，⛔ 也不是假装不认识 | 三种行为混成一种 ⇒ 一体改落地时分不清「没接线」和「不认识」|
| B4 | 全量绿：`python -m pytest -q -n auto`，**三数报出来** | 有回归 |
| B5 | ⭐ **neuter 实测**：摘掉你的修复，你新加的锁必须**红**，且**只红它**（定向变红）| 锁没接到真实入口 / 恒绿 |

⛔ **B4 不得单独作为通过标志。**
⚠️ **B1 是本单最容易被做假绿的一条**：如果你为了让它过而放宽判别器（例如「认不出就当 legacy」），
那正好把缺陷原样保留下来。⇒ B1 必须用**逐字节比对提示词**证明，不是「跑起来没报错」。

## 六、⛔ 停下上报触发器（任一命中就停，⛔ 不许自行扩路）

1. §二里 orchestrator 陈述的任何一条事实不成立；
2. ⭐ 你发现除本单给的做法外还有**严格更优**的第三条路
   —— **这条明确算触发器**（本项目「停下上报」累计 **35 次全部是我题错**，顶回来是正常产出）；
3. 要动 §四「明确不做」里的任何一项才能完成；
4. 你判断 B3 那个「三种行为」的分法本身是错的 —— 直接说，别自己改分法。

## 七、⚠️ orchestrator 自认的最弱一点（请优先证伪）

**我假设「legacy view JSON 可以靠结构稳定识别」**（`strokes` + `dimensions` + `image_kind` 这组键），
但我只看过 sm25 的六份。
**sm21 / sm24 / sm20 的历史 reading 产物长不长这样，我没核过。**
若它们结构不同，B1 会在历史 case 上塌 ⇒ 请先核实再动手；核不过就停下上报。

## 八、交件形式

1. 施工报告 → 你 worktree 的
   `AI_agent/logs/reviews/execution/2026-08-27_f97_contract_discriminator_construction_report.md`：
   ⛔ 只写**做了什么 + 每条判据的实测读数 + 你自己认为最不确定的地方**。
2. 在你的分支上 `git commit`（message 仿 `08.27_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响）。
   ⛔ 不 push、不合并。
3. 把施工报告全文 + `git show --stat` 贴回给 orchestrator。

---

# ⭐⭐⭐ 补充裁定（2026-08-27 · orchestrator）—— 施工席位「停下上报」**第 36 条，仍是我题错**

⛔ **本节是派工单的正式演进，⛔ 不是复核单里的悄悄改动**（08-26 GLM 点过这个病：范围演进必须回写派工单）。
施工席位**一行源码没改就顶了回来**，三条否证 orchestrator 已逐条独立复核，**全部属实**。

## 一、我错在哪（三条，逐条认）

1. ⛔ **我把契约值写错了，而且错法是「读串了两份文件」**：§二 点名 `sm25_1f_v2.json`，
   描述的却是同目录 `sm25_1f_as_drawn.json` 的键。**实测全仓**：
   `as_drawn_plan_v2` **132** 份 · `as_drawn_plan_v0` 4 份 · `as_drawn_elevation_v0` 4 份
   （⚠️ 第三个值我**完全没提**）。**仓内在跑的生产者常量 = `src/agent/reading/as_drawn/as_drawn_v2.py:67 SCHEMA = "as_drawn_plan_v2"`**。
   ⇒ 照我原单实现，会把**代码此刻真会产出的形态**判进 unknown —— 正是 B3 明令禁止的「假装不认识」。
   同族 [[grep-zero-hits-conflates-unused-with-nonexistent]] / [[proxy-mistaken-for-the-thing]]。
2. ⛔ **「优先看 `schema` 字段」不充分**：`as_drawn_plan_v2` 被**两个生产者共用**
   —— 读图产物（`observations`/`declarations`/`hypotheses`）与 checks 报告（`checks/source/role_assignment`）。
   ⇒ 契约必须是 **(schema 值 × 必需键集合)** 的配对。⭐ **这正是 F-97 缺陷本身的同型复发。**
3. ⛔ **§七 我自陈的弱点，方向对但值错**：`dimensions` 只在 **322/328** 份历史产物里有
   （缺的 6 份全在 `sm21_anchor/run_2026-06-20_gpt54_reading/`）⇒ 拿它进签名会**把真的历史 reading 判成未知**。

## 二、三个问题的裁定（施工席位要的三条签字）

### 裁定 1 —— B3 的锚：改 `as_drawn_plan_v2`，且 ⭐ **判别器必须 import 生产者的常量，⛔ 不许抄字面量**

- 锚 = `src/agent/reading/as_drawn/as_drawn_v2.py` 的 `SCHEMA` 常量本身。
- 理由：仓内已有同样的先例并写在注释里 —— `judge/as_drawn/denominator.py` 明写
  「**从转换器自己的收集通道取，⛔ 绝不第二次重新定义**」。抄字面量 = 埋下第二个定义，
  一体改改了值就静默失配。
- ⛔ 这**不算**替一体改做设计决定：它是「镜像生产者、不重新实现」的既有纪律，不是新口径。
- `as_drawn_elevation_v0` / `as_drawn_plan_v0`：一并登记为**已知契约**（历史形态），处置同 as-drawn（见裁定 2 的第 3 类）。
  ⚠️ 若它们也有生产者常量可 import 就 import；只在原型档（`logs/experiments/`）里的，⛔ 不要为它去 import 实验代码，
  ⇒ 那两个值**允许**以字面量登记，但要在代码注释里写明「历史原型值，无在册生产者」。

### 裁定 2 —— 43 份（我复核到的更宽口径下 **108** 份）`*_checks.json` 边车：**声明式排除 + 记进对账**，⛔ 不响亮红

新增**第 4 类契约** `stage_check_report`（无 `schema` 键，含 `stage` + `results` + `report_schema_version`）。处置：

- ✅ **从提示词里排除** + **在消费对账里逐份点名**（「已识别 / 本阶段不消费」）。
- ⛔ **不是响亮红** —— 它是我们自己的门写进那个目录的合法产物，让所有含边车的历史 run 目录不可重放，
  代价大于收益（§0.1：不做它下一次跑测能不能跑起来？能 ⇒ 不做）。
- ⛔ **也不是 F-64 静默跳过** —— F-64 的形状是「零产出不报红」，即**没有人知道发生了什么**；
  这里是**逐份点名后排除**，⇒ 可观测，不是静默。
- ⚠️ **由此 B1 必须重写**（见 §三）：排除边车**会改变**含边车的历史目录的提示词字节。
  ⇒ **必须把「有多少历史 run 的提示词会变、各变多少字节」测出来报上，⛔ 不许藏。**

⭐ **顺带登记一条新缺陷（F-106）**：`stage_check_report` 是 **gate① 的检查结果**，
而它今天正被原样贴进 **correction 的提示词** ⇒ **判分/门的输出反向流进了被判的那一段**。
⛔ 本单不追这条的影响面（不扩范围），只登记。

### 裁定 3 —— legacy 签名：⛔ **不签那个三键归纳**，改锚在**已有的生产者契约 + 真实消费者**上

施工席位自己点破了病根，我采纳：「从 328 份产物反推出来的签名」= [[acceptance-bar-must-not-be-written-from-the-result]]。改判据：

- **契约侧**：仓里**已经有** legacy 的类型定义 —— `src/agent/reading/schema.py:117 `**`ReadingView`**（Pydantic）。
- **消费侧**：correction 提示词真正吃的是 **`strokes`**（它逐字要求引用笔画 id、并数 `pen=="window"`）。
- ⇒ **判据 = 能按 `ReadingView` 解析成功 **且** 带一个非缺省的 `strokes` 列表。**
  ⛔ `dimensions` **不许**进签名（会误杀那 6 份）。
- ⚠️ `ReadingView` 是 `extra="allow"` 且**全部字段有默认值** ⇒ 它对 `{}` 也会解析成功
  ⇒ **必须**配 `strokes` 那一条，⛔ 只靠「解析成功」等于没判。
- ⭐ **若两个契约同时命中**（例如某份 as-drawn 也能解析成 `ReadingView`），⇒ **报歧义并响亮失败**，
  ⛔ 不许按顺序「先匹配到谁算谁」。

## 三、验收判据重写（⛔ 覆盖原 §五）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| **B1′** | 对**契约判为 `reading_view_legacy`** 的文件，correction 提示词组装**逐字节不变** —— 必须**真的做字节比对**（原 B1 你自己点出「我一次都没实测过」）| 判别器把在跑的东西判错 |
| **B1″** | ⭐ **变化面测出来并报上**：有多少历史 run 目录因排除 `stage_check_report` 而提示词改变、各改多少字节 | 藏起来不报 |
| **B2′** | 未知契约（如 `{"hello":1}`）⇒ **响亮红并点名该文件** | 把未知当已知 / 静默跳过 |
| **B3′** | `as_drawn_plan_v2`（**取自生产者常量**）⇒ 「认识但本阶段不消费」的响亮失败；`as_drawn_elevation_v0` / `as_drawn_plan_v0` 同类 | 三种行为混成一种 |
| **B3″** | `stage_check_report` ⇒ **排除 + 对账点名**（⛔ 不红、⛔ 不静默） | 当 unknown 报红，或悄悄跳过不记 |
| **B3‴** | ⭐ **两个契约同时命中 ⇒ 报歧义**（造个夹具证明）| 按顺序先到先得 |
| **B4′** | 全量：`python -m pytest -q -n auto`。⭐ **基线已更正见 §四** | 有回归 |
| **B5** | 不变：neuter 实测（摘修复必红、且定向）| 锁没接到真实入口 |

## 四、⚠️ 环境更正：worktree 里那条红是 **`.env` 缺失**，不是「shell 没设 key」

施工席位报 `3034 passed / 1 failed`（`test_zone_agent.py`：`openai.OpenAIError: api_key must be set`）。
**orchestrator 复核后更正它的归因**：我的 shell 里 `OPENAI_API_KEY` **也没有**（`env | grep -c` = 0），
而主树同一 commit 是 **3035 passed / 0 failed**。真因 = **`.env` 被 gitignore ⇒ 任何 worktree 里都没有它**，
而 `src/agent/llm.py:12` 调 `load_dotenv()`。
⇒ ✅ **orchestrator 已把主树 `.env` 软链进三个 worktree**。**重跑一次全量，基线 = `3035 passed / 13 xfailed / 0 failed`。**

⭐ 这是 [[green-suite-is-a-property-of-tree-and-launcher]] 的一次活体现形：**同一棵树、同一条命令，
换个启动环境读数就不同**。⛔ 以后任何席位报「已知环境红」，先查 `.env` 在不在。

## 五、⛔ 仍然不做（原 §四不变）+ 新增一条

原 §四全部条款不变（⛔ 不改 `wall-centerline` 那两句 · ⛔ 不给 as-drawn 真接线 · ⛔ 不碰 F-95 在审的文件 · ⛔ 不碰 `src/agent/judge/`）。
**新增**：⛔ **不追 F-106**（gate① 检查报告流进 correction 提示词的影响面），本单只登记。

## 六、停下上报触发器不变

⭐ 你这一次是对的，**继续这么干**。若本补充裁定里又有事实不成立，照样停下上报（那会是第 37 条）。
