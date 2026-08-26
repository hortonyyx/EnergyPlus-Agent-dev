# 施工报告 · F-97 契约判别器（第二轮：补充裁定后施工完成）

- **日期**：2026-08-27　**施工席位**：Claude 家族　**worktree**：`/tmp/ep_f97`（分支 `wt/08.27_f97_contract`）
- **派工单**：`../request/2026-08-27_f97_contract_discriminator_dispatch.md`（含末尾「⭐⭐⭐ 补充裁定」整节）
- **本轮结论**：**三条裁定全部落地，B1′/B1″/B2′/B3′/B3″/B3‴/B4′/B5 全部实测通过。**

> ⚠️ **本报告累计式自包含**。第一轮（停下上报，第 36 条）的完整证据表在提交 `e08c79b`，
> 其结论已被 orchestrator 复核采纳并写进补充裁定；本文 §七 留索引。

---

## 〇、开工自检

| 项 | 要求 | 实测 |
|---|---|---|
| 本轮起点 commit | `e08c79b`（第一轮 stop-and-report） | 一致 ✅ |
| `AI_agent/CLAUDE.md` 行数 | 447 | 447 ✅ |
| import 是否串主树 | 必须解析到 worktree | `/tmp/ep_f97/src/agent/pipeline.py` ✅ |
| `.env` | orchestrator 已软链 | `.env -> /workspaces/EnergyPlus-Agent-dev/.env` ✅ |

---

## 一、补充裁定的前置事实：**逐条复核，全部成立**（⇒ 无第 37 条）

裁定改了做法，所以裁定所依赖的每条事实我又量了一遍：

| 裁定依赖的事实 | 实测 | 结论 |
|---|---|---|
| `as_drawn_v2.py` 有可 import 的 `SCHEMA` 常量 | `as_drawn_v2.py:67 SCHEMA = "as_drawn_plan_v2"`；import 0.19 s，无副作用 | ✅ |
| `ReadingView` 在 `reading/schema.py:117` | 确在 117 行 | ✅ |
| `ReadingView` 是 `extra="allow"` 且字段全有默认值 ⇒ 对 `{}` 也解析成功 | 实测 `ReadingView.model_validate({})` **成功** ⇒「解析成功」单独**等于没判** | ✅ 裁定 3 的警告完全正确 |
| 「解析成功 + 非缺省 `strokes`」能认全历史 legacy | **328 / 328** | ✅ |
| `dimensions` 会误杀 | 只在 **322/328** 里有，缺的 6 份全在 `sm21_anchor/run_2026-06-20_gpt54_reading/` | ✅ 已按裁定排除出签名 |
| `denominator.py` 有「⛔ 绝不第二次重新定义」的先例 | 在 **`denominator.py:14-15`**，英文原文：「⭐ It derives that from the CONVERTER'S OWN collection pass (`run_p1_plan_view`), ⛔ **never from a second re-implementation of "what a wall line is"**」 | ✅ 引用属实（原文是英文，转译无失真） |
| `.env` 缺失是那条红的真因 | ✅ 见 §五 B4′ | ✅ 我第一轮的归因确实差一层 |

⭐ **额外自查（B3‴ 的前提）**：实测**没有任何**真实产物同时命中两个契约
（328 份 legacy、140 份 as-drawn 家族、43 份边车，交叉命中 **0**）
⇒ 歧义判据在真实数据上**恒绿**，**必须造夹具才有分辨力**——裁定要求「造个夹具证明」正为此，已照做。

---

## 二、改了哪些文件

| 文件 | 性质 | 说明 |
|---|---|---|
| `src/agent/reading/vector_contract.py` | ⭐ **新增**（约 260 行） | 单文件级契约判别器 + 消费对账 |
| `src/agent/pipeline.py` | 改（+44 行） | 三处：import · 提示词组装处接线 · 对账落盘 |
| `tests/test_f97_vector_contract.py` | **新增**（23 用例） | B1′/B2′/B3′/B3″/B3‴ + 两个 neuter 靶子 |
| `scripts/tool_scripts/affected_tests_rules.yaml` | 改（−4 条） | 见 §六「唯一的意外」 |

⛔ **§四/§五「明确不做」全部未碰**：`wall-centerline` 那两句原样（`git diff` 零命中）·
as-drawn 未接线 · 未碰 `src/validator/data_model.py` / `checks/kernel.py` / `tests/test_f95_*` / `tests/test_f13_*` ·
未碰 `src/agent/judge/` · 未改任何 reading 判分/容差 · **未追 F-106**。

### 设计要点（三条裁定的落地形态）

1. **裁定 1**：`from src.agent.reading.as_drawn.as_drawn_v2 import SCHEMA as AS_DRAWN_PLAN_SCHEMA`
   —— ⛔ 字面量零出现，并**加锁**（`test_b3_as_drawn_schema_value_comes_from_its_producer`
   断言源码里不得出现 `"as_drawn_plan_v2"` 字面量）。
   `as_drawn_plan_v0` / `as_drawn_elevation_v0` 按裁定以**字面量**登记，
   注释写明「历史原型值，无在册生产者，⛔ 不要为它去 import 实验代码」。
2. **裁定 2**：`stage_check_report` = 第 4 类契约，处置 `EXCLUDE`（排除 + 对账逐份点名）。
3. **裁定 3**：legacy 判据 = `ReadingView.model_validate(raw)` 成功 **且** `isinstance(raw.get("strokes"), list)`。
4. ⭐ **契约 = (schema 值 × 必需键集合) 配对**，且**全部检测器都跑**、⛔ 无 first-match-wins：
   0 命中 ⇒ unknown；1 命中 ⇒ 该契约；**≥2 命中 ⇒ 报歧义并响亮失败**。
5. **对账落盘**：`<run>/_run/reading_vector_contract_ledger.json`（跟着现有 `_run/` 纪律，⛔ 没新开目录），
   ⭐ **在提示词组装之前写**，所以**分类失败的 run 也留下点名记录**（`ledger_for` 永不抛）。

---

## 三、⭐ 判别器实际登记的契约表

| 契约 id | 识别条件 | 处置 |
|---|---|---|
| `reading_view_legacy` | 解析成 `ReadingView` **且** 声明 `strokes` 列表 | **CONSUME**（贴进提示词） |
| `as_drawn_plan` | `schema == as_drawn_v2.SCHEMA`（**import**）且含 `observations`+`declarations`+`hypotheses` | **KNOWN_NOT_CONSUMED** ⇒ 响亮失败 |
| `as_drawn_plan_v0` | `schema=="as_drawn_plan_v0"` 且含 `wall_bands`+`dimension_witnesses` | 同上 |
| `as_drawn_elevation_v0` | `schema=="as_drawn_elevation_v0"` 且含 `openings`+`structure_lines` | 同上 |
| `stage_check_report` | **无** `schema` 键，含 `stage`+`results`+`report_schema_version` | **EXCLUDE** ⇒ 排除 + 对账点名 |
| `unknown` | 以上皆不命中，或**同时命中 ≥2 个** | **响亮失败**（点名文件 + 理由） |

⚠️ **我没有登记的一个形态（据实报，见 §八#2）**：as-drawn 的 **checks 报告**
（`schema==as_drawn_plan_v2` 但键是 `checks/source/role_assignment`，45 份，产出者 `validator/checks/as_drawn.py:821`）。
它落 `unknown` ⇒ 真放进 `0_reading/` 会响亮红。
**这是我的判断，不是裁定给的**：登记它等于新增第 5 类处置，属扩范围（§0.1），
且实测这 45 份**全在 `logs/experiments/out/`，从不出现在任何 `0_reading/``**。⇒ 登记为已知缺口，请 orchestrator 定夺。

---

## 四、⛔ 缺陷复现（改动前）

```
discover_vector_files(sm20_anchor/run_2026-06-15_baseline/0_reading)
  -> [..., '1f_view_checks.json', '2f_view_checks.json', ... 共 7 份边车]
```

`1f_view_checks.json` 不匹配 `_PLAN_RE`、不以 `_view.json` 结尾 ⇒ 落 `others` ⇒ **原样贴进提示词**。
生产入口 `run_stage.py:_draw_correction` 用 `rdir = run_dir/"0_reading"` 作 `vector_dir` ⇒ 目录即 run 的 0_reading 本体。

⭐ **机制的根**：**识图门只 glob `*_view.json`**（`evidence_preflight.py:229`），
而**提示词收集器 glob `*.json`**（`pipeline.py:91`）—— 两个 glob 不一致，那条缝就是 F-97。

---

## 五、⭐ 验收判据实测读数（数字全部真实，无估算）

### B1′ —— 提示词**逐字节**比对（⛔ 未用结构推理）

方法：对全仓 **56** 个含 `*.json` 的 `0_reading/` 目录，用改动前的 paste 循环原样重建提示词片段，
与改动后重建的**逐字节 `==`** 比较。

```
dirs measured                 : 56
B1'  bytes IDENTICAL          : 49
B1'' bytes CHANGED            : 7
     loudly RAISED            : 0
```

⇒ **49/56 逐字节不变，0 个历史目录被打断。**
其中派工单点名的 `sm25-L_anchor/run_2026-08-25_c2_rescore_R0/0_reading` 六份
**全部判 `reading_view_legacy`、字节不变**。

### B1″ —— ⭐ 变化面（⛔ 未藏）

**7 个历史 run 目录**的提示词会变，**全部**只因排除 `*_checks.json` 边车，**共移除 170,455 字节**：

| 减少字节 | 边车份数 | 目录 |
|---:|---:|---|
| 60,892 | 6 | `sm21_anchor/run_2026-07-01_sonnet_e2e_r2/0_reading` |
| 42,013 | 6 | `sm21_anchor/run_2026-07-01_sonnet_e2e_r1/0_reading` |
| 15,230 | 7 | `sm20_anchor/run_2026-06-15_baseline/0_reading` |
| 13,080 | 6 | `sm21_anchor/run_2026-06-21_sonnet_reading_retry/0_reading` |
| 13,080 | 6 | `sm21_anchor/run_2026-06-20_sonnet_reading/0_reading` |
| 13,080 | 6 | `sm21_anchor/run_2026-06-20_gpt54_reading/0_reading` |
| 13,080 | 6 | `sm21_anchor/run_2026-06-16_opus_e2e/0_reading` |
| **170,455** | **43** | **合计**（43 = 裁定 2 说的那 43 份） |

⚠️ **方向说明**：这 7 个目录的提示词**只减不增**，减掉的**全是 gate① 的检查报告**（即 F-106 的载体）。
⛔ 没有任何一份**读图产物**被移除（每个目录的 `*_view.json` 全部保留且字节不变）。

### B2′ / B3′ / B3″ / B3‴

| # | 判据 | 实测 |
|---|---|---|
| **B2′** | `{"hello":1}` ⇒ 响亮红并点名 | ✅ `UnconsumableVectorFile`，报文含 `mystery.json` + `unknown contract` + 实际看到的键 |
| **B3′** | `as_drawn_plan_v2`（**取自生产者常量**）⇒「认识但不消费」 | ✅ 报文含 `no wire for it` + `NOT unknown`，且**不含** `unknown contract` ⇒ 与 B2′ 可区分 |
| **B3′** | `as_drawn_plan_v0` / `as_drawn_elevation_v0` | ✅ 同为 `KNOWN_NOT_CONSUMED` |
| **B3″** | 边车 ⇒ 排除 + 对账点名 | ✅ 不抛异常；提示词里搜不到 `1f_view_checks.json` 与 `report_schema_version`；对账 `counts == {"consume":1,"exclude":1}` 且该行 `reason` 非空 |
| **B3‴** | 两契约同时命中 ⇒ 报歧义 | ✅ 夹具（`schema=as_drawn_plan_v2` + 合法 `strokes`）⇒ `AMBIGUOUS`，理由**同时点名两个契约**；⛔ 未按顺序择一 |

### B4′ —— 全量

```
3058 passed, 13 xfailed, 211 warnings in 333.93s (0:05:33)
```

⭐ **对账**：orchestrator 基线 **3035** + 本轮新增 **23** 条 = **3058**，`xfailed` **13** 一致，`failed` **0**。
⇒ 数目逐项对得上，**没有顺手改动别的用例**。
✅ 第一轮那条 `test_zone_agent.py` 红**已消失**（`.env` 软链生效），orchestrator 的归因得到验证。

### B5 —— neuter 定向变红（**两个方向都测了**）

**neuter ①（摘掉接线）**：把 `pipeline.py:427` 改回 `vector_files = discover_vector_files(vector_dir)`，**跑全量**：

```
4 failed, 3054 passed, 13 xfailed in 308.41s
FAILED tests/test_f97_vector_contract.py::test_b2_unknown_contract_raises_and_names_the_file
FAILED tests/test_f97_vector_contract.py::test_b3_as_drawn_raises_and_says_known_not_unknown
FAILED tests/test_f97_vector_contract.py::test_b3_check_report_sidecar_is_excluded_not_raised
FAILED tests/test_f97_vector_contract.py::test_b3_ambiguous_file_fails_loudly
```

⇒ **恰好 4 红，全部在我新加的文件里，零附带**（3054+4 = 3058，与全绿总数一致）
⇒ **定向变红成立**，且 4 条全部走**真实入口** `_build_correction_messages`（⛔ 不是直接调判别器）。

**neuter ②（把 import 换成抄来的字面量）**：
`AS_DRAWN_PLAN_SCHEMA = "as_drawn_plan_v2"` 替换 import ⇒
`test_b3_as_drawn_schema_value_comes_from_its_producer` **红**
⇒ 裁定 1「⛔ 不许抄字面量」这条**有分辨力，不是恒绿装饰**。

---

## 六、唯一的意外：`affected_tests_rules.yaml` 少了 4 条

首轮全量出现 1 红：`test_affected_tests_map.py::test_every_production_module_is_mapped_or_honestly_allowlisted`。

**不是我漏映射，方向相反**：该判据要求「未被任何测试到达的生产模块」集合与 allowlist **完全相等**。
我的新测试 import 了 `as_drawn_v2.SCHEMA`，**给 as-drawn 读图工具箱建立了第一条测试可达边**，
于是这 4 个模块不再 uncovered，而 allowlist 里它们的条目
（写着「no project-side test imports src/ directly yet」）**陈述过时**：

```
src/agent/reading/as_drawn/{__init__,_plan_ink,as_drawn_v2,pens}.py
```

⇒ 已删除这 4 条（其余 30 条未动；`src/validator/checks/as_drawn.py` 与
`src/agent/judge/as_drawn/*` 仍 uncovered，条目保留）。

⭐ **顺带一条正面证据**：`tests/test_gt_discipline.py::test_pipeline_import_closure_excludes_gt_and_as_drawn_judge`
**全程绿** ⇒ 我把 `pipeline` 接到的是 **reading 侧** as-drawn，
**没有**把 judge 侧 gt 代码拉进管线导入闭包（不变量 §1.5#4 未破）。

⚠️ **但这条「覆盖」是 import 边，不是行为覆盖**，见 §八#1。

---

## 七、第一轮（停下上报，第 36 条）证据存档

完整文本见提交 `e08c79b`。三条否证已被 orchestrator 复核采纳并写进补充裁定：
**A** as-drawn 值不是 `v0`（3 值 4 形态，生产者产 `v2`；病根 = 派工单点名 `sm25_1f_v2.json` 却描述了 `sm25_1f_as_drawn.json`）·
**B** `schema` 单独不足以判契约（`as_drawn_plan_v2` 被两个生产者共用）·
**C** 43 份 CheckReport 边车住在历史 `0_reading/` 里且正被贴进提示词（⇒ 已登记为 F-106）。
另：§七 三键签名会漏 6/328（`dimensions` 322/328）。

---

## 八、⭐ 我自己认为最不确定 / 最可能塌的地方（必答）

1. **⭐ 最不确定：我删了 `affected_tests_map` 的 4 条 allowlist，但那 4 个模块的「覆盖」是 import 边撑起来的，不是行为覆盖。**
   我的测试只 import 了一个字符串常量 `SCHEMA`，**一行 `_plan_ink.py` / `pens.py` 的逻辑都没跑过**。
   对「改了 X 该跑哪些测试」这个用途，import 边是对的信号（`as_drawn_v2.py` 一改我的锁确实该跑）；
   但对 `_plan_ink.py` / `pens.py` 是**传递性的、很弱的**边——它们现在**看起来被覆盖了，实际没有**。
   ⇒ 这正是 [[proxy-mistaken-for-the-thing]] 的形状：**我把「可达」当成了「被测」**。
   建议 orchestrator 复核这 4 条删除是否该改成「保留条目 + 改写理由」。**这是本轮我最可能被推翻的一处。**

2. **as-drawn 的 checks 报告（45 份）我没登记，它落 unknown ⇒ 真放进 `0_reading/` 会响亮红。**
   我按「不扩范围」决定不登记，理由是它们从不出现在 `0_reading/`（实测）。
   但这条推理**锚在「现在的产物分布」上**，而不是锚在「代码能不能产出它到那里」——
   正是 [[is-this-conclusion-product-side-or-code-side]] 警告的形状。**换一份产物这条结论可能不在。**

3. **`stage_check_report` 的签名仍是我从 43 份边车归纳的**，不是从 `CheckReport` 的类型定义推的。
   裁定 3 把 legacy 从「归纳」搬到了「生产者类型」，**但裁定 2 的这个签名没做同样的搬迁**，
   我也没主动搬（会动到 `validator/checks/schema.py`，属 §四 F-95 在审的邻域）。
   ⇒ 同一份代码里两个契约用了两种成色的判据，**弱的那个是这一个**。

4. **B1″ 的 170,455 字节只覆盖「仓库里现存的 56 个目录」。**
   ⛔ 它不是「所有历史 run」的变化面——未入库的、别处的 run 目录我量不到。
   我报的是**可测全集**，不是**真全集**。

5. **施工过程中我两次用行号做文本替换、两次都替错了位置**
   （把一个 `_write(...)` 覆盖成 docstring、把一段 `sorted(...)` 塞进了字典字面量里），
   第二次直接产生 `SyntaxError` 才被发现。已全部修好且全量绿，
   但这说明**我这一轮的编辑手法不稳**；若审阅席位要抽查，建议优先 diff `tests/test_f97_vector_contract.py` 的完整性。

6. **我在一次 neuter 全量跑着的时候改了树**（两处换行整形），当场作废了那次跑并重跑。
   最终 B5 读数取自**改完之后**干净的一跑，但这是我自己踩了
   [[green-suite-is-a-property-of-tree-and-launcher]] 的「⛔ 全量在跑时不许动树」。
