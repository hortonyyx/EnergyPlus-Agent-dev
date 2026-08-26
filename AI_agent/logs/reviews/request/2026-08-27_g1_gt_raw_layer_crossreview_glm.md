# 跨家族复核请求 · G1：gt 派生审计件的可读 API + 机械复现门

- **日期**：2026-08-27　**复核席位**：**GLM 家族**（`scripts/glm_code.sh`，`glm-5.3`）
- **施工席位**：**Claude 家族**（独立 worktree `/tmp/ep_g1`）⇒ ⛔ 谁写谁不批
- **被审 commit**：`06dd513`（分支 `wt/08.27_gt_raw_layer`，起点 `ed0ba09`）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-27_g1_gt_raw_layer_dispatch.md`（含末尾无补充裁定）
- **施工方自述**：`AI_agent/logs/reviews/execution/2026-08-27_g1_gt_raw_layer_construction_report.md`
  （⚠️ **只作线索，不作证据** —— §5#8：施工席自述一律以 `git diff` 为准）

## 〇、你的工作目录（⛔ 写死）

```
/tmp/ep_g1        ← 被审 worktree 本体，HEAD = 06dd513，工作树干净
```

- ⛔ **不许在 `/workspaces/EnergyPlus-Agent-dev`（主树）改任何文件、不许在主树跑全量。**
- ⛔ **你是复核方，不许替它改代码**。可做探针/变异实验，**做完必须还原**
  （交件时 `git -C /tmp/ep_g1 status --porcelain` 应只剩你自己的裁决文件）。
- ⚠️⚠️ **跑全量请用 `python -m pytest -q -n 6`，⛔ 不要 `-n auto`** ——
  同机另有施工席位在跑，施工方实测 `-n auto` 在 `load average 17.44 / 16 核` 时
  **整场崩**（worker `OSError: cannot send`、无 summary 行）= **同机竞争的假红**。
- ⛔ 裸跑脚本会因共享 venv 的 editable `.pth` 静默串到主树；一律 `python -m` 或 pytest。
- ✅ `.env` 已软链进该 worktree ⇒ **全量基线 = `3035 passed / 13 xfailed / 0 failed`**（本 commit 应为 3035+7）。
- 开工自检：`git -C /tmp/ep_g1 log --oneline -1` = `06dd513`。对不上停下上报。

## 一、这件事在盘面上的位置（⚠️ 定位在施工期间被改过，以本节为准）

用户四步：**① 把判分修好 → ② 一体改 → ③ 产新产物 → ④ 验证**。当前在 **①** 的 gt 侧。

⚠️⚠️ **命名更正（2026-08-27 晚，跨家族设计复核 sol 指出，orchestrator 采纳）**：
派工单里把 `conversion_report.json` 叫作 **「gt 原始层」**，**这个叫法是错的** ——
它是 **0.1 mm 量化 + 墙厚判定 + cavity 扩张之后的派生审计件**；真正原始的是**签字 DXF + 签字 request**。
⇒ 本单的正确定位 = **「派生审计件的可复现性门 + 可读 API」**，⛔ 不是「原始层」。
**这不改变本单要做的事，只改变它的名字与它能承诺什么。**（裁决全文：
`AI_agent/logs/reviews/verdict/2026-08-27_night_findings_design_crossreview_sol.md`）

## 二、改了什么（据 `git show --stat`，请你自己看 diff 核）

```
src/agent/judge/gt_raw_layer.py                    | 493 +++++  (新增)
tests/test_gt_raw_layer.py                         | 147 +++++  (新增, 7 条)
tests/test_gt_discipline.py                        |   9 +-
AI_agent/logs/reviews/execution/…construction_report.md | 182 +++  (新增)
AI_agent/logs/reviews/request/…dispatch.md              | 136 +++  (新增)
```

三件功能：**(a)** 派生审计件的 typed 读取 API（复用 `ConversionReportV1` / `ZoneEdgeReportV1`，
与 `load_gt` 同一把 gt 铁律锁）· **(b)** **机械复现门**：从签字 DXF + 冻结 request 重跑转换器、
与盘上报告**逐 JSON 指针**比对，**比内容字段⛔不比字节**，且「**实现漂移**」与「**内容不一致**」两种红必须分开 ·
**(c)** 信任根显式化（这一层不在人工签字覆盖内，读取口须带出它凭什么可信）。

## 三、⭐⭐⭐ 请你重点打的四处（按价值排序）

### 3.1 ⭐⭐⭐ **施工方自己点名的最心虚处：豁免清单是看过实测 diff 之后才写的**

`_pointer_is_signature_dependent` 的豁免清单**决定了复现门 A2 能不能变绿**，而施工方自述：
「**我是看过实测 diff 之后才写下它的**」—— 这正是本项目已登记的病
[[acceptance-bar-must-not-be-written-from-the-result]]：**判据若从结果反推，它就不是判据。**

它给的非循环理由是「复刻生产者自己的 `{6, 10}` 声明」（`sign_review_bundle` 里的 `if i not in {6, 10}`）。
**请你判定这个理由成不成立**，并特别攻：

- ⭐ 它对 **G10 豁免了整个 `evidence` 子树**（G6 只豁免 `passed` + `human_confirmation`，几何仍在比）。
  **⇒ 若 G10 的 evidence 里将来塞进真几何信息，那部分会静默失去比对。**
  这是「豁免范围超出了它给的理由」的典型形状 —— 请核实豁免范围与 `{6,10}` 声明是否**逐条对齐**，
  超出的部分有没有独立依据。
- ⭐ **反向验证**：把豁免清单**收窄到它声称的最小集**，A2 还绿不绿？若不绿，说明清单里有靠结果撑着的项。

### 3.2 ⭐⭐ 复现门的分辨力是不是**只在被测过的那一格**成立

施工方给了 A3（改一条边的 `thickness_m` ⇒ `content_mismatch` 并指名 `/zones/0/edges/0/thickness_m`）
与 A4（`converter_sha256` 漂移一位 ⇒ `implementation_drift`）。**请你自己另造变异**，至少覆盖：

- 改 `source_handles`（溯源被篡改而几何不变）· 删掉一整条边 · 增加一条边 · 改 `basis`（`wall_axis`↔`outer_skin`）·
  改 `openings` / `walls` / `cavities` 里的值（不是 `zones`）· 改 `diagnostics`。
- ⭐ **重点**：有没有**整类字段**其实根本没进比对（= 静默不设防）。
  判法建议：拿实测 diff 的**指针全集**与报告的**全部叶子指针**对账，报出「**从不被比对的指针集合**」。

### 3.3 ⭐⭐ 施工方自述的三个「已声明的洞」，请判它们是不是**该阻断**

1. `gt_extraction` / `gt_manifest` / `tarch_converter_schema` **在转换闭包内却没有精确签字指纹**
   ⇒ 只有它们漂移时会被归类成 `content_mismatch`（**抓得住但归因错**）—— 而 A4 的全部意义就是分开这两种红。
2. **A1 对「混入 step 边」零分辨力**：`ZoneEdgeReportV1.basis` 是 `Literal["outer_skin","wall_axis"]` 无 `|None`，
   schema 层就不允许 null ⇒ A1 只对「读错文件」有分辨力。
3. **可得性依赖 `AI_agent/logs/experiments/` 目录**（过程痕迹目录被清理 ⇒ 退化成 `inputs_unavailable`）。
   施工方自述这是「显式不假绿」。**请核实这条降级路径是否真的响亮**，⛔ 而不是变成一条新的静默通道。

### 3.4 ⭐ 一处口径改动（施工方主动交代，请核）

它第一版把 `extractor_sha256` 也算致命，未改动树上 A2 **直接红**；查下来是**真漂移**
（08-25 `91ae82d` 给 `gt_from_dxf.py` 加了 5 行 `sys.path` 自举）。它把该项**降为 advisory**（仍逐次报出不吞），
依据是「实测转换 import 闭包不含 `gt_from_dxf`」。
⇒ **请独立核实那个闭包**：`gt_from_dxf` 真的不在转换路径的 import 闭包里吗？
⛔ 若在，这就是「为了让门变绿而放宽判据」。

## 四、验收判据（每条我都自查过「什么情况下它会不通过」）

| # | 判据 | 什么情况下会红 |
|---|---|---|
| A1 | 你独立跑全量（`-n 6`），三数报出来 | 有回归 / 同机竞争假红（那就重跑，⛔ 别记成回归）|
| A2 | §3.1 的反向验证：豁免清单收窄到其声称的最小集后 A2 仍绿 | 清单里有靠结果撑着的项 ⇒ 阻断 |
| A3 | §3.2 你自造的变异矩阵，报出「**从不被比对的指针集合**」 | 存在整类字段静默不设防 |
| A4 | §3.3 三个洞逐条定性（阻断 / 不阻断 + 理由） | —— |
| A5 | §3.4 import 闭包独立核实 | `gt_from_dxf` 其实在闭包内 ⇒ 放宽判据 ⇒ 阻断 |
| A6 | neuter 复验：摘掉 `_diff_pointers` 应只红 a3；摘掉 `_fatal_fingerprints` 应只红 a4 | 锁没接到真实入口 / 连带外溢 |

⛔ **「全量绿」不得单独作为通过标志。**

## 五、⛔ 停下上报触发器

1. §一 / §二 / §三 里 orchestrator 陈述的任何一条事实不成立；
2. ⭐ 你发现严格更优的第三条路（**明确算触发器**；本项目「停下上报」累计 **36 次全部是派工方题错**，
   而且今晚已有一次是跨家族复核方替我触发的）；
3. 要动被审范围以外的文件才能完成；
4. 你判断本单应 REWORK 但把握不足 ⇒ 把证据摆出来交 orchestrator，⛔ 不替我们下结论。

## 六、⚠️ 派工单里已知的三处错（施工方查出，orchestrator 已认，**⛔ 不必再查，但可以复核**）

派工单 §三 关于「输入在哪」的三处陈述都是错的：`review/source.dxf` **不存在**
（真身在 `case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf`，sha `1251f651…` 与 ack 一致）·
`request.json` **不在 gt 树**（只在 `AI_agent/logs/experiments/`）· `manifest.json` **根本不是输入**（它是产物）。
施工方判定不阻塞，理由是 `request_sha256` 可从内容重算（实测重算 = 签字值 `d738d0ac…`），
**门按「谁重算出签字值谁就是它」认，位置无权威性**。⇒ **请你判这个理由成不成立**。

## 七、交件形式

裁决写到 `/tmp/ep_g1/AI_agent/logs/reviews/verdict/2026-08-27_g1_gt_raw_layer_glm_verdict.md`，
并把**全文贴回**给 orchestrator。必含：总判 · §四六条判据逐条读数 · §三四处实测结论 ·
findings 分「阻断 / 不阻断」· 你自己跑的全量三数 · ⭐ **以及「你认为 orchestrator 在这份请求单里题面写错的地方」**。
