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
