# 施工报告 · G1：gt「原始层」变成可读、可复现的一层

- **日期**：2026-08-27　**施工席位**：Claude 家族　**worktree**：`/tmp/ep_g1`　**分支**：`wt/08.27_gt_raw_layer`
- **起点**：`ed0ba09`　**开工自检**：`log -1` = `ed0ba09` ✅ / `grep -c '' AI_agent/CLAUDE.md` = **447** ✅ / 指南存在 ✅
- **未停下上报**（§六触发器逐条核过，见 §5）

---

## 1. ⭐ §七：orchestrator 自认最弱的那条假设 —— 实测结论

> 假设原文：「从已签字的 source.dxf + 冻结的 request/manifest 能确定性重跑出同一份 conversion_report 的内容字段」

### 结论：**假设成立**。内容字段 **100% 复现，逐字段零差异**。

实测：把已签字 DXF 拷进临时目录 → 载入冻结 request → `run_tarch_conversion` → 与盘上
`conversion_report.json` 做**逐 JSON 指针**比对（不是哈希、不是抽样）：

| 项 | 读数 |
|---|---|
| 全报告差异指针总数 | **15** |
| 其中落在 `walls`(84) / `openings`(61) / `cavities`(29) / `zones`(29,136 边) / `diagnostics`(28) / `elevation_audit_rows`(34) / 各 sha256 provenance 字段 | **0** |
| 落在 `gates/G6`（人审门） | 5 |
| 落在 `gates/G10`（人审门） | 8 |
| `/status`（BLOCKED vs PASS） | 1 |
| `/normalized_dxf_sha256`（None vs str） | 1 |

**那 15 条差异全部、且只由「临时目录里没有 `review_ack.json` / `review_index.json`」造成**，与图纸内容无关：

- 生产者自己就把 G6/G10 定义成人审门 —— `tarch_review_bundle.sign_review_bundle` 第 200 行
  `any(not gates[f"G{i}"].passed for i in range(1, 11) **if i not in {6, 10}**)`；
- `/status` 与 `/normalized_dxf_sha256` 是红门的**机械后果**，由
  `ConversionReportV1._status_geom_contract` 强制（非 PASS 不许带 normalized 哈希）；
- ⭐ **G6 的几何证据（cavity_count 14/14、near_threshold_faces 的面积与质心）两侧逐位相同**，
  只有 `passed` 与 `human_confirmation` 变了。

### 确定性（对付「哈希随机化」那条已登记事实）
`PYTHONHASHSEED` = **1 / 7 / 12345** 三次重跑，内容字段规范化摘要恒为
`0f57e5ee0b45d192c60157002b72ebf341cce3ada34e0450c24a5a26bbd67504`，边数恒 136。
⇒ 派工单「⛔ 比内容字段，不比字节」的判断是对的，且**内容侧确实稳定**。

### ⚠️ 但派工单 §三 关于**输入在哪**的陈述是错的（三处）
`gt_promotion.promote_gt_v3` 只往 `review/` 拷 **5 个文件**，`source.dxf` / `request.json` /
`manifest.json` / `normalized.dxf` / `overlay_plan.svg` **都不在里面**：

| 派工单说 | 实际 |
|---|---|
| `review/source.dxf` | ❌ 不存在。签字的 DXF 在 `case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf`，字节 sha = `1251f651…` **与 ack 完全一致** ✅ |
| 冻结的 `request.json` | ❌ 不在 gt 树。仅存于 `AI_agent/logs/experiments/**/request.json`（3 份，字节相同） |
| 冻结的 `manifest.json` | ❌ 且**根本不需要** —— manifest 是转换器的**产物**不是输入 |

⭐ **这不构成阻塞**，因为信任根不依赖位置：`request_sha256` 是**可从内容重算**的规范哈希
（`compute_request_sha256`，实测重算 = `d738d0ac…` = ack 签的值）。
⇒ 复现门**不信任声明字段、不信任路径**，而是「谁重算出签字的那个值，谁就是那份 request」。
同理 source DXF 按**字节哈希**认。位置因此没有权威性，放在 experiments 里也不削弱信任。

---

## 2. 每条验收判据的实测读数

| # | 判据 | 实测读数 | 结果 |
|---|---|---|---|
| **A1** | 136 条带 basis 的边；basis 直方图 `wall_axis 90 / outer_skin 46`；厚度 `0.12×78 / 0.24×58` | zones=**29**，edge_count=**136**，basis=**{'wall_axis': 90, 'outer_skin': 46}**，thickness=**{0.12: 78, 0.24: 58}** | ✅ 逐位吻合 |
| **A2** | 复现门在未改动的树上跑绿 | `status = **reproduced**`，`differing_pointers = **()**`，耗时 ~13 s | ✅ |
| **A3** | 单条边 `thickness_m` 0.12→0.13，门必须红且**指名那条边** | `status = **content_mismatch**`，`differing_pointers = **('/zones/0/edges/0/thickness_m',)**` | ✅ 精确到该边该字段 |
| **A4** | 实现哈希漂移一位 ⇒ 报「实现漂移」而非「内容不一致」 | `converter_sha256` `539615ab…`→`139615ab…`；`status = **implementation_drift**`，`drifted_fingerprints = **('converter_sha256',)**`，`differing_pointers = **()**` | ✅ 两种红分开 |
| **A5** | 全量绿 | **3042 passed / 13 xfailed / 0 failed**（550.39 s） = 基线 3035 + 本单新增 7 条 | ✅ 零回归 |
| **A6** | neuter：摘门 ⇒ 锁必须红且**只红它** | N1 摘内容比对（`_diff_pointers`→`[]`）⇒ **仅 a3 红**（1 failed / 6 passed）；N2 摘漂移检查（`_fatal_fingerprints`→`[]`）⇒ **仅 a4 红**（1 failed / 6 passed） | ✅ 双向定向变红 |

### A5 的两个诚实备注
1. 第一次全量：`3041 passed / 1 failed`，红的是 `tests/test_zone_agent.py`（worktree 里当时无 `.env`
   ⇒ OpenAI 凭据缺失）。orchestrator 软链 `.env` 后该测单跑 **1 passed**，全量重跑归零。
2. 中途一次 `-n auto` **整场崩**（worker `OSError: cannot send`，无 summary 行）。当时
   `load average = 17.44 / 16 核` —— 别的席位在同机跑全量。**这是同机竞争的假红，不是本单的红**；
   降到 `-n 6` 后 EXIT=0。⇒ 复现同族教训「全量绿是【树+启动器+这段时间】的属性」。

---

## 3. 做了什么（三件）

### G1-a　原始层读取 API
新增 `src/agent/judge/gt_raw_layer.py`：`load_gt_raw_layer(case, gt_dir=…)` →
`GtRawLayer`。⛔ **没有新造平行 schema** —— 直接复用 `ConversionReportV1` / `ZoneEdgeReportV1`。
`edges()` 逐 zone 逐边吐 `RawEdge(zone_id, floor_id, edge_index, edge)`，
暴露 `p1/p2/basis/thickness_m/offset_m/source_handles`。
**同一把锁**：`tests/test_gt_discipline.py` 的**行为级**闭包探针已加入本模块
（`m in ('src.agent.judge.gt', 'src.agent.judge.gt_raw_layer')`）。
词法扫描无需改 —— `_FORBIDDEN` 里的 `"judge.gt"` 已是 `"judge.gt_raw_layer"` 的子串。
⭐ 该探针的**分辨力实测**：在探针里主动 import 本模块，它确实报出
`["src.agent.judge.gt", "src.agent.judge.gt_raw_layer"]`（⛔ 未碰 `pipeline.py`，§四禁区）。

### G1-b　机械复现门
`verify_raw_layer_reproduction(case, gt_dir=…)` → `ReproductionVerdict`，四态：
`reproduced` / `implementation_drift` / `content_mismatch` / `inputs_unavailable`。

**两种红怎么分开**：指纹检查**先跑并 early-return**，所以一棵漂移的树永远不会被报成「产物可疑」。

⭐ **致命指纹集 = 报告自己绑定的那三个**（`converter_sha256` / `judge_config_sha256` / `vg_config_sha256`）
—— 复刻生产者自己的「什么实现造了我」声明。

⚠️ **这里我改过一次口径，必须交代清楚**：第一版我把已签字 `gt.json` generator 块的
`extractor_sha256` 也算作致命，结果**未改动的树上 A2 直接红**。查下来是**真漂移**：
08-25 的 `91ae82d` 给 `scripts/tool_scripts/gt_from_dxf.py` 加了 5 行 `sys.path` 自举（F-94 A 案）。
但**实测转换的 import 闭包只有** `gt_extraction` / `gt_manifest` / `tarch_converter_schema`，
**`gt_from_dxf` 根本没被 import** ⇒ 那个 group 哈希对本问题**太宽**，会把纯 CLI 改动伪装成转换器漂移
（与「比字节必然假红」是同一物种）。
⇒ 改判为**非致命 advisory**，仍逐次报出，⛔ 不吞。
**⛔ 我没有为了变绿调任何参数或容差**：判据窄化的依据是「闭包实测 + 复刻生产者定义」，
且窄化后 A3/A4 证明它**仍然会红**。

### G1-c　把「未被签字覆盖」变成显式声明
`RawLayerTrust` 随读取口一并返回：
- `human_signed=False` + `human_signed_reason='not_in_review_index_file_set'`
  —— ⭐ 这是**读 `review_index.json` 的 files 清单推出来的**，不是写死的常量；
  将来若用户重签把 `conversion_report.json` 纳入清单，它会**自己翻成 True**。
- `signed_source_dxf_sha256` / `signed_request_sha256` = 真正被签的那两个锚。
- `reproduction=None` ⇒ `reproduction_status` 读出 **`'not_attempted'`**，`trustworthy=False`。
  ⛔ 没跑过的门**绝不读成通过**（同族：`grep … || echo 通过` 把「文件不存在」读成「检查通过」）。
- 找不到签字输入 ⇒ `inputs_unavailable`，显式降级。

---

## 4. 改了哪些文件

| 文件 | 性质 |
|---|---|
| `src/agent/judge/gt_raw_layer.py` | **新增**（G1-a/b/c 全部） |
| `tests/test_gt_raw_layer.py` | **新增**，7 条（A1×3 / A2 / A3 / A4 / 降级显式） |
| `tests/test_gt_discipline.py` | 改 2 处：行为级闭包探针纳入新模块 + docstring 同步 |

⛔ **未碰**：`gt.json`、`review_index.json` 的签字文件集合（未重签）、`src/validator/**`、
`tests/test_f95_*`、`tests/test_f13_*`、`src/agent/pipeline.py`、任何判分口径/容差/评分规则。
⛔ 未跑任何 case、未产 reading/correction 产物。⛔ 未 push、未合并。

---

## 5. §六 触发器逐条核对（结论：均未命中，故未停下上报）

| # | 触发器 | 核对结果 |
|---|---|---|
| 1 | §二事实不成立 | **五条全部独立复核通过**：①136 边 / 90:46 / 78:58 逐位吻合，且 136 条**全部**带 basis；②`_RUNTIME_BUNDLE_FILES` 确实排除 `conversion_report.json`，`_review_files()` 不含它；③`inventory_sha256` 我重算 = `49065597…` = ack 签的值；④`gt.py:load_gt` 是唯一 gt 读取口；⑤`denominator.py` 确实从 `run_p1_plan_view` 取墙线且每次现算 |
| 2 | 有严格更优的第三条路 | 想过「直接把 `conversion_report.json` 纳入签字集合重签」—— 但 §四 明令禁止且重签是用户动作；且它**替代不了**复现门（签名抓不住实现漂移）。⇒ 未命中 |
| 3 | 必须动 §四禁区 | 未命中（A6 的分辨力验证特意绕开了 `pipeline.py`） |
| 4 | 复现门跑不通且指向转换器不确定 | 未命中 —— 转换器**确定性成立**（三种子恒等） |

---

## 6. ⭐ 我自己认为最不确定 / 最可能塌的地方（按可能性排序）

1. **⭐⭐⭐ 最可能塌：`_pointer_is_signature_dependent` 的豁免清单是我写的，而它正好把 A2 变绿了。**
   我给的非循环理由是「豁免集复刻生产者自己的 `{6, 10}` 声明」，这条我认为站得住；
   **但我是在看过实测 diff 之后才写下它的** —— 同族登记教训
   [[acceptance-bar-must-not-be-written-from-the-result]] 说的正是这种形状。
   ⭐ **请审阅方专攻这里**：`_pointer_is_signature_dependent` 对 G10 豁免了**整个 evidence 子树**，
   如果转换器某天把真正的几何信息塞进 G10 的 evidence，**那部分会静默失去比对**。
   （G6 我只豁免了 `passed` + `human_confirmation`，几何证据仍在比 —— G10 我放宽了，这是我最心虚的一处。）

2. **⭐⭐ 已声明但确实存在的盲区：`gt_extraction.py` / `gt_manifest.py` / `tarch_converter_schema.py`
   在转换闭包里，却没有精确对应的签字指纹。** 只发生在这三者的漂移会被**归类成 `content_mismatch`**
   —— 差异仍抓得住、但**归因是错的**，恰好是 A4 想防的那件事在这三个模块上失效。
   我选择写进 docstring 显式声明而不是假装覆盖，但这是真洞。

3. **⭐⭐ A1 的第二个失败模式在 sm25 上不可达。** 派工单说 A1 会红当「把 `basis=None` 的厚度变化
   step 边也算进来」—— 但 `ZoneEdgeReportV1.basis: EdgeBasis` 是 `Literal["outer_skin","wall_axis"]`
   **无 `| None`**，schema 层就不允许 null；且 sm25 实测 136/136 全有 basis。
   ⇒ **A1 对该失败模式零分辨力**（它只对「读错文件」有分辨力）。换一个真有 step 边的 case 才谈得上。

4. **⭐ 复现门依赖 `AI_agent/logs/experiments/**/request.json` 存在。** 信任**不**依赖位置（按重算哈希认），
   但**可得性**依赖：那是过程痕迹目录，谁清理一次门就退化成 `inputs_unavailable`。
   降级是显式的（不会假绿），但会从「绿」变「测不了」。⭐ 建议下一单把 request.json 归档进
   `gt_sources/<case>/`（⛔ 本单不做，属 §四 之外的范围扩张）。

5. **⭐ 单 case 单点。** 全部实测只在 sm25-L_anchor 上做过。sm21/sm24 的 gt 目录我**没有**验证过
   是否有 `review/conversion_report.json`，也没跑过它们的复现门。

---

## 7. 一条需要更正的登记事实（R-6）

派工单 §二#1 的更正**成立**，且可以再精确一点：
R-6「量了、用掉了、存盘时扔了」→ 实际是 **「量了、用掉了、**存盘了**，但
(a) 没有任何判分路径读它，(b) 它不在人工签字覆盖范围内」**。
本单把 (a) 补上了（读取 API），并给 (b) 配了一个**替代信任根**（机械复现门）而非假装它被签过。
