# 返工派工单 · G1：把「豁免清单」整个去掉，并补上两条没跑完的读数

- **日期**：2026-08-27　**施工席位**：**GPT 家族 sol**（⚠️ 它**没有**审过 G1，谁写谁不批成立）
- **审阅席位**：**GLM 家族** 或 **Claude 家族**（⛔ 不能是 GPT）
- **被返工 commit**：`06dd513`（worktree `/tmp/ep_g1`，分支 `wt/08.27_gt_raw_layer`）
- **上一轮裁决**：[`../verdict/2026-08-27_g1_gt_raw_layer_glm_verdict.md`](../verdict/2026-08-27_g1_gt_raw_layer_glm_verdict.md)
  （GLM，**APPROVE-WITH-FINDINGS / 0 阻断**，⛔ 但 A1/A6 未填）
- **原派工单**：[`2026-08-27_g1_gt_raw_layer_dispatch.md`](2026-08-27_g1_gt_raw_layer_dispatch.md)

## 〇、工作目录（⛔ 写死）

```
/tmp/ep_g1      ← 分支 wt/08.27_gt_raw_layer，HEAD = 06dd513
```
⛔ 不许碰 `/workspaces/EnergyPlus-Agent-dev`（主树）。跑测 **`python -m pytest -q -n 6`**
（同机另有 Claude 家族的施工在跑；⛔ 不用 `-n auto`，实测高负载下整场崩＝假红）。
⛔ 裸跑脚本会因共享 venv 的 editable `.pth` 静默串到主树 ⇒ 一律 `python -m` / pytest。
✅ `.env` 已软链；基线全量 **3035**，本 commit 应为 **3042**。
开工自检：`git -C /tmp/ep_g1 log --oneline -1` = `06dd513`。

## 一、这单是什么（一段话）

`src/agent/judge/gt_raw_layer.py` 给判分侧提供两件东西：**读 gt 的转换审计件**，
以及一道**机械复现门** —— 从**已签字的源 DXF + 冻结 request** 重跑转换器，与盘上的
`review/conversion_report.json` **逐 JSON 指针**比对；「实现漂移」与「内容不一致」两种红要分开。

它**已经能用**（六条判据当时全过：复现零差异、改一条边的厚度会指名到 `/zones/0/edges/0/thickness_m`、
哈希漂移报 `implementation_drift`、neuter 双向定向）。**本单不是推翻它，是拆掉它里面最脏的一块。**

## 二、⭐⭐⭐ 要做的第一件（本单主体）：**让整张豁免清单消失**

### 现状为什么脏

复现跑在临时目录里**没有 `review_ack.json`**，于是 G6/G10 两个**人审门**的结果必然与盘上不同
⇒ 施工方写了一个 `_pointer_is_signature_dependent` **豁免清单**把这些指针排除掉。
**而他自述：「我是看过实测 diff 之后才写下它的」** —— 判据从结果反推。

复核方做了**反向验证**，坐实了这一点：把豁免收窄到它声称的最小集，**门就变红**
（L1 剩 11 条未解释、L2 剩 7 条**全是 G10 evidence**）⇒ **门今天的绿，完全系于「G10 evidence 整树豁免」一项**。
而那一项的非循环理由只能支撑「**今天这些键**」，支撑不了「**任何键**」
⇒ 将来生产者往 G10 evidence 塞进真内容，对它的篡改会**静默失去比对**。

### ⭐ 复核方实测出的更优解（本单照它做）

> **把被签的 `review_ack.json` + `review_index.json` 一并喂进复现跑 ⇒ diff = 0 指针
> ⇒ 整张豁免清单可以直接消失。**

**要求**：
1. **删掉 `_pointer_is_signature_dependent` 及其豁免清单**（⛔ 不是「改成白名单」——那只是把病灶缩小）。
2. 复现跑的输入集里**加上那两个签字件**，并且**它们必须先按签字链验过**才允许进
   （`review_index` 的 `inventory_sha256` == `review_ack.review_index_sha256`；
   ⚠️ 注意它签的是 **files 清单的规范化摘要**，不是 `review_index.json` 文件自身的 sha256）。
3. **两种红仍要分开**（`content_mismatch` vs `implementation_drift`），⛔ 不许在这次重构里退化。

### ⚠️ orchestrator 自认最弱的一点（**请优先证伪**）

**我认为「把签字件喂进去」不削弱这道门** —— 理由是：ack/index 属于**信任根的一部分**（被人签过），
不是**被验对象**（被验的是 `conversion_report.json` 的内容）；喂进去只是让复现环境完整，
使人审门在两侧**同样地**求值。
⛔ **但这是我的推理，不是实测。** 若你发现喂进去之后**门对某类篡改失去了分辨力**
（例如篡改 `conversion_report` 里 G6/G10 的**几何证据**不再变红），**立刻停下上报** ——
那意味着这条「更优解」是拿分辨力换干净。

## 三、要做的第二件：**补上两条没跑完的读数**

上一轮 GLM 的裁决里 **A1（独立全量）与 A6（neuter 复验）留着 `{{PASSED}}` 之类的模板占位符**
（它的会话在全量跑完前结束了）⇒ **这两条至今没有复核方读数**。
⇒ **本单请你在返工后把两条都实测出来并写进施工报告**（它们会连同你的改动一起被下一位复核方独立复核）。

## 四、要做的第三件：**三条不阻断 findings 里，顺手能做的两条**

- **F-2**：往 `gates` 数组塞**重复 id 的 gate**（内容任意）⇒ **复现门照绿**
  （`_normalise_for_diff` re-key 成 dict 时静默覆盖）。⇒ re-key 时断言 `len(list) == len(dict_keys)`，
  重复即 `content_mismatch`。**这是唯一被找到的「形态级」不设防，顺手做掉。**
- **F-3**：`vg_implementation_sha256`（correction 四件）**纯闭包内、无闭包外噪声**，
  却随 `extractor_sha256` 组一并降成 advisory —— 降级理由（「邻接 artefact 的指纹」）对它**不成立**。
  ⇒ **要么把 vg 组升回 fatal，要么把 docstring 的「洞清单」按实测闭包重写**（现清单只列 3 个文件，
  复核方实测闭包还含 `gt_schema` + correction 四件）。**两条路你选一条并说明理由。**
- ⛔ **F-1 不用做**（它就是豁免清单本身，§二 直接把它整个删掉）。
- ⛔ **F-4 不做**（接线提醒，等真有消费者时再说）。

## 五、⛔ 明确不做

⛔ 不改 `gt.json` / 不改 `review_index` 的签字文件集合 / **不重签**（重签是用户动作）·
⛔ 不碰 `src/validator/data_model.py`、`checks/kernel.py`、`tests/test_f95_*`、`tests/test_f13_*` ·
⛔ 不碰 `src/agent/pipeline.py` 与 `src/agent/reading/`（**Claude 家族正在那里做 F-97 返工，会撞车**）·
⛔ 不改任何判分口径 / 容差 · ⛔ 不跑 case、不产 reading/correction 产物。

## 六、验收判据（每条我自查过「什么情况下会红」）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| **R1** | 豁免清单**已从代码里消失**（`grep` 零命中），且复现门在未改动树上 `status=reproduced`、`differing_pointers=()` | 喂签字件后仍有残差 ⇒ 那条「更优解」不成立，停下上报 |
| **R2** | ⭐ **分辨力没退化**：改一条边的 `thickness_m` 仍 `content_mismatch` 并**指名到该字段**；⭐ **另加**：篡改 **G6 的几何证据**（`gates/G6/evidence/views/0/evidence/near_threshold_faces/0/area_m2`）**必须仍然红** | 喂签字件把人审门整段变成"两侧一样"从而失去比对 |
| **R3** | 实现哈希漂移仍报 `implementation_drift` 且与 `content_mismatch` 可分 | 重构中两种红被压成一种 |
| **R4** | **F-2**：`gates` 塞重复 id ⇒ **红** | re-key 仍静默覆盖 |
| **R5** | **F-3**：给出你选的那条路 + 理由；若升 fatal，则 correction 四件任一漂移 ⇒ 报 `implementation_drift` 而非 `content_mismatch` | 洞清单仍与实测闭包不符 |
| **R6** | 全量 `python -m pytest -q -n 6` 三数（基线 3035，本 commit 3042） | 有回归 |
| **R7** | **neuter 逐条定向**：摘掉本单每处修复，对应锁必须红且**只红它** | 锁没接真实入口 / 连带外溢 |
| **R8** | **补上原 A1 / A6 的读数**（见 §三） | —— |

⛔ **「全量绿」不得单独作为通过标志**（这道门就是在全量绿的情况下被查出问题的）。

## 七、⛔ 停下上报触发器

1. §二「我自认最弱的一点」被证伪（喂签字件削弱了分辨力）—— **最重要的一条**；
2. §一 / §二 / §四 里 orchestrator 陈述的任何事实不成立；
3. ⭐ 你发现严格更优的第四条路（**明确算触发器**：本项目累计 **36 次停下上报全是派工方题错**，
   而且**这条「更优解」本身就是复核方替我触发出来的**）；
4. 要动 §五 里的任何一项才能完成。

## 八、交件

施工报告 → `/tmp/ep_g1/AI_agent/logs/reviews/execution/2026-08-27_g1_rework_construction_report.md`；
在 `wt/08.27_gt_raw_layer` 上 commit（⛔ 不 push、不合并）；把报告全文 + `git show --stat` 贴回。
必含 **R1–R8 逐条实测读数** + **你自己认为最可能塌的地方**。
