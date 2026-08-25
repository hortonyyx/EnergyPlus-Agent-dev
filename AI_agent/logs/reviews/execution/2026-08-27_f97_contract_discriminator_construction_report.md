# 施工报告 · F-97 契约判别器 —— ⛔ 停下上报（未施工）

- **日期**：2026-08-27　**施工席位**：Claude 家族　**worktree**：`/tmp/ep_f97`（分支 `wt/08.27_f97_contract`，起点 `ed0ba09`）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_dispatch.md`
- **结论**：**命中停下上报触发器 §六#1（§二 陈述的事实不成立），未写任何生产代码。**
  本次交付物 = 下面的证据表 + 一张待 orchestrator 拍板的契约表提案。

## 〇、开工自检（通过）

| 项 | 要求 | 实测 |
|---|---|---|
| `git -C /tmp/ep_f97 log --oneline -1` | `ed0ba09` | `ed0ba09 08.26o_WrapUp_...` ✅ |
| `grep -c '' AI_agent/CLAUDE.md` | 447 | 447 ✅ |
| 分支 | `wt/08.27_f97_contract` | 一致 ✅ |
| import 是否串主树 | 必须解析到 worktree | `python -c "import src.agent.pipeline"` → `/tmp/ep_f97/src/agent/pipeline.py` ✅ |

⭐ 最后一行是专门验的：本报告全部读数都用 `python -c`（仅 stdlib + 仓内 `src`），
且实测 `sys.path[0]`=cwd 压过共享 venv 的 editable `.pth`，**读数来自本 worktree，不是主树**。

## 一、§二 的缺陷机制：**成立**（已独立复现）

`src/agent/pipeline.py:84 discover_vector_files` 确实把 `vector_dir/*.json` 三分为
`plans` / `elevations` / **`others`=其余全部**，返回三者拼接；
`pipeline.py:444` 对返回的每个名字无条件 `_read` 并贴进提示词，中间无任何契约门。

实测（B1 目标目录）：

```
discover_vector_files('case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/0_reading')
  -> ['1f_view.json','2f_view.json','East_view.json','North_view.json','South_view.json','West_view.json']
```

这六份全部落 `plans`/`elevations`，`others` 在该目录为空 ⇒ **`others` 是一条潜伏路径**，
与派工单「一份新格式产物放进去就走沉默路径」的判断一致。

生产入口也复核过：`scripts/tool_scripts/run_stage.py:_draw_correction` 用
`rdir = run_dir / "0_reading"` 作 `vector_dir` 调 `run_correction` ⇒ 目录即 run 的 0_reading 本体。

## 二、⛔ §二 不成立的部分（触发器 §六#1）

### 事实 A —— as-drawn 的 `schema` 值**不是** `as_drawn_plan_v0`，而且**不止一个值**

派工单 §二 原文：「注意那个值是 `as_drawn_plan_v0`（**v0**）……⛔ 也不要假设还有别的值。」

全仓扫描（所有 `*.json`，取顶层 `schema` 含 `as_drawn` 者）：

| `schema` 值 | 份数 | 顶层键 | 产出者 |
|---|---|---|---|
| **`as_drawn_plan_v2`** | **77** | 见下（两种形态） | ⭐ **仓内在跑的生产者** |
| `as_drawn_plan_v0` | 4 | `calibration/dialect/dimension_witnesses/image/image_label/ledger/schema/unpaired_face_lines/wall_bands` | 08.23f 原型，**已被取代** |
| `as_drawn_elevation_v0` | 4 | `calibration/dialect/dimension_witnesses/facade_label/image/image_label/ledger/openings/schema/structure_lines` | 立面形态，**派工单完全没提** |

关键证据：

```
src/agent/reading/as_drawn/as_drawn_v2.py:67   SCHEMA = "as_drawn_plan_v2"
src/agent/reading/as_drawn/as_drawn_v2.py:570      "schema": SCHEMA,
```

git 溯源（谁新谁旧，不是印象）：

```
as_drawn_v2.py (生产者)     2026-08-24  283e868 08.25g_ToolboxTransplantedIntoSrc_ByteIdenticalAcrossAllThreeViews
sm25_1f_as_drawn.json (v0)  2026-08-23  c9206b2 08.23f_G1InteriorRuleTightened_...
sm25_east_as_drawn.json     2026-08-23  bf4ce56 08.23c_AsDrawnStepA_PlanFixesAndElevationShape
```

⇒ **`as_drawn_plan_v0` 是 08.23 的原型残留；08.25g 把工具箱搬进 `src/` 后，现行产出的值是 `as_drawn_plan_v2`。**
派工单把 B3 锚在了**已死的值**上：若照单实现，`v0` 进「已知未接线」桶，
而**代码此刻真正会产出的 `v2` 会掉进 `unknown` 桶** —— 正好是 B3 明令禁止的
「⛔ 也不是假装不认识」。B3 会变成一条**测不到真产物的判据**。

⚠️ 我**没有**去改任何产物里的 `schema` 值（派工单 ⛔ 过），只是把值清点出来。

#### A-1　⭐ 病根定位：派工单**点名了对的文件，却描述了旁边那份**

派工单 §二 正文举的例子是「**`sm25_1f_v2.json`**」（第 45 行），
但 §二 表格里给的顶层键 `dialect/calibration/wall_bands/unpaired_face_lines`
是**同目录另一份** `sm25_1f_as_drawn.json` 的键。实测：

```
out/sm25_1f_v2.json        schema=as_drawn_plan_v2  keys=[declarations,hypotheses,image,image_label,ledger,observations,schema]
out/sm25_1f_as_drawn.json  schema=as_drawn_plan_v0  keys=[calibration,dialect,dimension_witnesses,image,image_label,ledger,schema,unpaired_face_lines,wall_bands]
```

⇒ **同一目录下同名前缀的两代产物被读串了**。
（`out/` 里 `*_as_drawn.json` = v0 一代，`*_v2.json` = v2 一代，两代并存未清理。）
这正是 memory 条目「写「新」文档前先 ls 一眼同目录」的形状。

#### A-2　⭐⭐ 这件事两天前的**跨家族设计答复**已点名过，本派工单与之冲突

⚠️ **先说清该文件的地位**（免得我这条被当成比它本身更硬的东西）：
`2026-08-25_reading_correction_unification_gpt_design.md` 开头自述
「**⛔ 不是裁决，⛔ 不构成拍板。定位 = 给 sol 那次架构讨论备料的方案池**」。
⇒ 下面引的是**未拍板的设计答复**，不是既定裁决；但它是**同一问题上更新、且核到字段级**的记录。

`.../verdict/2026-08-25_reading_correction_unification_gpt_design.md:44-46`：

> **契约判别器显式化**：现有判别器只识别 `reading_views_v2`（`src/agent/reading/contract.py:23,33`），
> 新入口必须显式增加 **`as_drawn_plan_v2`**，**未知类型响亮失败**。

且 `AI_agent/logs/reviews/request/2026-08-25_reading_correction_unification_design_ask.md:62-70`
已把 as-drawn 基线件核到字段级：**「产物 schema 名 `as_drawn_plan_v2`」**，
基线件 = `sm25_1f_v2.json` / `sm25_2f_v2.json` / `sm24_1f_v2.json`，
三层 = `observations` / `declarations` / `hypotheses` —— 与我实测的键集**逐字吻合**。

⭐ 而且**F-97 这个缺陷本身就是那份答复发现的**（同文件 §一 #3）：

> 提示词收集器**实际会读目录里所有 JSON**（`pipeline.py:91-106`），而识图门只检查 `*_view.json`
> （`evidence_preflight.py:229`）⇒ 真实形态是「**新产物可能被当原始文本塞给模型，却绕过类型化识别与识图门**」。

⇒ **F-97 的题面与解法都源自 08-25 那份答复，连值都点名了 `as_drawn_plan_v2`。**
本派工单继承了题面，却把锚换成了已退役的 `v0`。
⇒ 请 orchestrator 先与 08-25 那份答复对齐（并决定它是否升格为拍板），再重发单。

⚠️ 该答复的 §一 #2 还指出 `hypotheses` 实物含 `opening_candidates` / `opening_types`
（生产者 `as_drawn_v2.py:617`）—— 说明 as-drawn 的**字段**层面也仍在被逐轮修正中，
这加重了我在 §八#1 里说的「焊死字面量会再次过期」的担心。

### 事实 B —— ⭐ `schema` 字段**单独不足以判别契约**：一个值对应两种产物

`as_drawn_plan_v2` 这 77 份里是**两个完全不同的东西**：

| 形态 | 份数 | 顶层键 | 是什么 |
|---|---|---|---|
| 读图**产物** | 22（+10 带 `crossreview_mutation`） | `declarations/hypotheses/image/image_label/ledger/observations/schema` | as-drawn reading 产物 |
| **checks 报告** | 45 | `checks/image/mutation/role_assignment/schema/source` | 判据报告，见 `src/validator/checks/as_drawn.py:821` |

```
src/validator/checks/as_drawn.py:821
    report = {"source": doc_path, "image": cfg["image"], "schema": "as_drawn_plan_v2", ...}
```

⇒ **F-a 指定的方法「判别优先看内容里的显式声明（`schema` 字段）」在这份仓库里不充分**：
按 `schema` 判，一份 as-drawn **checks 报告**会被判成 as-drawn **读图产物**。
契约必须声明成 **(`schema` 值 × 必需键集合)** 的**配对**，不能只认 `schema` 值。

⚠️ 注意这**恰好是 F-97 缺陷本身的同型复发**：`schema` 值被当成身份，
但它其实只是个标签，两个生产者都往上写 —— 与 memory 里
「把观测量命名成事实性名字，它就以事实身份往下游走」同族。

### 事实 C —— ⭐ 43 份 `*_checks.json` 就住在历史 `0_reading/` 里，**今天正被贴进提示词**

这是派工单完全没有涉及、但**直接决定 B1 能不能过**的一条。

全仓 `0_reading/` 目录下 371 份 `*.json` 中：

| 群体 | 份数 | 顶层键 |
|---|---|---|
| legacy view（含 `image_kind`） | **328** | 14 种变体，见下节 |
| **CheckReport 边车** | **43** | `artifact_hash/attempt_hash/capability_profile/report_schema_version/results/stage`（12 份多一个 `run_profile`） |

例：`case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/0_reading/1f_view_checks.json`
（sm20 baseline、sm21 `run_2026-06-20_gpt54_reading` 等历史 run 均有整套）。

`1f_view_checks.json` 不匹配 `_PLAN_RE`、也不以 `_view.json` 结尾
⇒ **落 `others` ⇒ 今天原样贴进 correction 提示词。**
写入者：`src/agent/execution/validation_run.py:292  _write(rdir / f"{vj.stem}_checks.json", rep)`，
以及 `pipeline.py:1320` 往 `out_dir/0_reading/reading_checks.json`（在 `run_correction` **之前**）。

现代 run（sm25 R0 / sm21 G1 2026-08-20）的 `0_reading/` 根目录已无 checks 边车，
⇒ **现网 live 路径干净**，但**任何历史 run 目录被重放、或先跑过 `validate_case(write_reports=True)` 再重跑 correction，边车就在**。

⇒ 判别器一上线，这 43 份的归属**必须有人签字**，而派工单 §五 B3 的「三种行为」分法**装不下它**：
它既不是要消费的 legacy view，也不是「已知契约但当前不消费」的 as-drawn，
判成 unknown 则历史 run 重放当场响亮红。**这是第 4 个群体，需要 orchestrator 拍板**（⇒ 亦触及触发器 §六#4）。

⛔ 我**没有**自行发明第 4 种处置（例如「已声明的边车，静默排除但记进对账」）——
那既越权、又贴着 F-64「静默跳过」的边，按 §六 顶回来。

## 三、§七「orchestrator 自认最弱一点」的核实结果：**按原文陈述不成立，但可救**

派工单 §七假设 legacy view 靠 `strokes` + `dimensions` + `image_kind` 这组键稳定识别，
自陈只看过 sm25 六份。我把全仓 `0_reading/` 的 **328 份 legacy view** 全查了（不是抽样）：

| 键 | 出现率 |
|---|---|
| `image_kind` | **328 / 328** |
| `image_label` | **328 / 328** |
| `strokes` | **328 / 328** |
| `dimensions` | **322 / 328** ⛔ |
| `self_check` | 322 / 328 |
| `ocr_texts` | 322 / 328 |
| `scale_origin` | **292 / 328** ⛔ |

⇒ **`dimensions` 漏 6 份**（`case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/*.json`，
键集为 `facade_axis_note/image_kind/image_label/scale_origin/strokes/uncaptured_visual_elements[/view_facade]`）
⇒ 照 §七 原文的三键签名实现，**这 6 份历史产物会被判 unknown**，B1 在历史 case 上塌 —— §七 担心的正是这个，担心得对。

⭐ **可救**：改用 `image_kind` + `image_label` + `strokes` 三键，**328/328 全覆盖**，
legacy 变体共 14 种顶层键集（差异集中在 `facade` / `facade_axis_note` / `view_facade` /
`uncaptured` vs `uncaptured_visual_elements` / `calibration_note` / `measurement_basis_note` 这些可选项上）。

⚠️ 但这条**没有独立信任根**：它是我从 328 份现存产物**反推**出来的，
不是任何地方**声明**过的 legacy 契约。按 memory「判据从结果反推出来 ⇒ 它就不是判据」，
这个签名该由 orchestrator 明确**声明**一次，而不是由我从产物里归纳后直接焊进代码。

## 四、§二 中**成立**的其余陈述（已逐条核过）

- ✅ `src/agent/reading/contract.py:identify_reading_contract` 确为**信封级**：只认顶层 `views` 字典
  （`raw["views"]` 缺失即 `unrecognized`），对单份 view 文件恒判 unrecognized ⇒ **不可直接复用于单文件级**。
  调用侧全在 judge typed-adapter / run_stage 信封校验，与本单不冲突。
- ✅ 现行 legacy view **确实没有任何显式 schema 字段**（328 份全无 `schema` 顶层键）。
- ✅ 文件名正则 `_PLAN_RE` 确实只承担**排序**职责，不承担契约。
- ✅ 本单确为**代码侧**缺陷，不依赖具体 case 产物。
- ✅ 现行 live 流程不会把 as-drawn 产物写进 `0_reading/`（`grep as_drawn` 在
  `src/agent/execution/` 与 `pipeline.py` 零命中）⇒ F-97 是**潜伏**缺陷，与派工单定位一致。

## 五、验收判据实测读数

| # | 判据 | 实测 |
|---|---|---|
| B1 | 历史产物全判 legacy + 提示词逐字节不变 | **未测（未施工）**。前置事实已否证：按 §七 三键签名会漏 6/328；另有 43 份 checks 边车归属未定 |
| B2 | 未知契约响亮红并点名 | **未测（未施工）** |
| B3 | as-drawn ⇒「认识但不消费」的响亮失败 | **未测（未施工）**。⛔ 判据本身锚在已死值 `as_drawn_plan_v0` 上，需先改锚 |
| B4 | 全量绿（三数） | **3034 passed / 1 failed / 13 xfailed**（详见下节；1 红=环境缺 `OPENAI_API_KEY`，非回归）。本次零源码改动 ⇒ 此数=`ed0ba09` 基线复核，非修复后读数 |
| B5 | neuter 定向变红 | **未测（未施工）** |

B4 基线实测（`cd /tmp/ep_f97 && python -m pytest -q -n auto`）：

```
1 failed, 3034 passed, 13 xfailed, 211 warnings in 493.55s (0:08:13)
FAILED tests/test_zone_agent.py::test_zone_agent_creates_two_zones - openai.OpenAIError
```

⚠️ **不是绿。据实报**：`3034 passed / 1 failed / 13 xfailed`。

那 1 红**不是回归**，理由三条（不是印象，逐条实测）：

1. **本轮零源码改动**：`git diff --stat HEAD -- src/ tests/` 为空 ⇒ 没有可回归的东西。
2. **报错是环境缺 key，不是断言失败**：
   `openai.OpenAIError: The api_key client option must be set either by passing api_key to the client
   or by setting the OPENAI_API_KEY environment variable`（`openai/_client.py:587`）。
   实测本 shell `OPENAI_API_KEY` **未设置**；`tests/test_zone_agent.py:5` 该用例**无 skip 守卫**，
   直接发真实 OpenAI 调用 ⇒ 无 key 必红。
3. **单独重跑复现同一条**（按 memory「下『某方报的数不对』前先重复跑」）：
   `python -m pytest -q tests/test_zone_agent.py::test_zone_agent_creates_two_zones` → 同样 1 failed，同一异常。
   ⇒ 是**确定性的环境依赖**，不是 flake，也不是席位差异。

**数目对得上**：3034 + 1 = **3035**，`xfailed` **13** 与 orchestrator 主树读数逐字相同
⇒ 差异**全部**由这一条 env-gated 用例解释，worktree 是干净可用的再派工基座。

⭐ 顺带一条给 orchestrator（不在本单范围，仅登记）：
`test_zone_agent_creates_two_zones` 会在**没有 `OPENAI_API_KEY` 的任何环境**里恒红。
主树因为环境里有 key 才是 3035/0，**这条「全量绿」是环境属性、不是树的属性**
（memory：「『全仓绿』是【树+启动器+这段时间】的属性」）。要不要给它加 skip 守卫由你定。

## 六、命中的触发器

- **§六#1（主）**：§二「as-drawn 的值是 `as_drawn_plan_v0`、不要假设还有别的值」不成立
  —— 实测 3 个 `as_drawn*` 值、4 种形态，且**现行生产者产出的是 `as_drawn_plan_v2`**。
- **§六#4（次）**：B3 的「三种行为」分法装不下第 4 个群体
  （43 份住在 `0_reading/` 里的 CheckReport 边车），其归属需 orchestrator 拍板。
- **§七 自陈弱点**：按原文三键签名会在 6 份历史产物上塌；已给出全覆盖替代签名，但该签名需**被声明**而非被反推。
- **⭐ 额外（不在触发器清单里，但影响最大）**：本单与 **08-25 跨家族设计裁决**冲突
  （那份已点名 `as_drawn_plan_v2` + 未知响亮失败）。⇒ 应先对齐既有裁决再重发单，
  否则本单实现完会与一体改本体的设计对不上。

## 七、给 orchestrator 的契约表提案（⚠️ 提案，**未实现**，等拍板）

判别单元建议改为 **(显式 `schema` 值, 必需键集合) 配对**，而非单看 `schema`：

| 契约 id | 识别条件 | 建议处置 | 份数 |
|---|---|---|---|
| `legacy_reading_view` | 无 `schema` 顶层键 且 含 `image_kind`+`image_label`+`strokes` | **消费**（贴进提示词，字节不变） | 328 |
| `as_drawn_plan_v2` | `schema=="as_drawn_plan_v2"` 且 含 `observations`+`declarations`+`hypotheses` | **已知 · 当前不消费 ⇒ 响亮失败** | 32 |
| `as_drawn_plan_v0` | `schema=="as_drawn_plan_v0"` 且 含 `wall_bands`+`dimension_witnesses` | 同上（或明确判定为已退役形态） | 4 |
| `as_drawn_elevation_v0` | `schema=="as_drawn_elevation_v0"` 且 含 `openings`+`structure_lines` | 同上 | 4 |
| `as_drawn_checks_report` | `schema=="as_drawn_plan_v2"` 且 含 `checks`+`source`+`role_assignment` | ⚠️ **待拍板** | 45 |
| `stage_check_report` | 无 `schema`，含 `stage`+`results`+`report_schema_version` | ⚠️ **待拍板**（第 4 群体） | 43 |
| `unknown` | 以上皆不匹配 | **响亮失败 + 点名文件 + 给出理由** | — |

需要 orchestrator 回答的三个问题：

1. **B3 的锚改成 `as_drawn_plan_v2` 吗？** 还是四个 as-drawn 值全部声明？
2. **43 份 `stage_check_report` 边车怎么处置？**（响亮红 / 声明式排除并记入对账 / 别的）
   —— 选「响亮红」等于让所有含边车的历史 run 目录不可重放；选「声明式排除」需要你确认它不算 F-64 静默跳过。
3. **legacy 签名 `image_kind`+`image_label`+`strokes` 你签字吗？** 它现在只是我从 328 份产物反推的归纳。

三条一旦定死，F-a/F-b/F-c 的施工量很小（判别函数 + `discover_vector_files` 调用侧接线 + `_run/` 对账记录），
可一轮做完。

## 八、我最不确定 / 最可能塌的地方

1. **⭐ 最不确定：`as_drawn_plan_v2` 是不是「最终」的值。**
   我证明了 `v0` 已被取代、`v2` 是此刻仓内生产者产出的值，但本批正在做的
   「reading + correction 一体改」很可能**再改一次这个值**。
   若判别表焊死 `v2`，一体改落地那天可能重演今天这一幕（表锚在又一个过期值上）。
   ⇒ 真正的解也许不是列举值，而是让**生产者与判别器共用同一个 `SCHEMA` 常量**
   （`as_drawn_v2.py:67` 已经是单点定义，判别器 import 它即可，别抄字面量）。
   我没有实现这一点，因为它等于替一体改本体做设计决定。
2. **事实 C 的严重度可能被我高估。** 43 份边车全在**历史** run 目录里，
   现网 live 路径实测干净。若 orchestrator 判定「历史 run 目录本就不该被重放」，
   这条就从「拍板项」降为「记一笔」。我按「重放是真实场景」估的，可能过重。
3. **legacy 签名的三键是归纳出来的，可能被下一份产物打脸。**
   328/328 覆盖只覆盖**已经存在**的产物；`image_kind` 是不是 reading-worker-agent
   在任何模型/任何提示词下都必然输出的键，我**没有**从提示词或 schema 侧独立确认，
   只从产物侧统计过。这正是 memory 里「判据从结果反推出来 ⇒ 它就不是判据」的形状。
4. **我没有跑到「提示词逐字节比对」那一步。** B1 最容易做假绿的一条我一次都没实测过，
   因此我对「legacy 侧接上判别器后字节真的不变」只有**结构推理**，没有读数。
