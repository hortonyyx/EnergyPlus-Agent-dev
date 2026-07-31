# 问题书 · 识图阶段的类型化判卷通路（F-6）

> 主控 Opus 5 · 2026-07-31 · 收件人 = sol（GPT 侧顶档，出细稿 + 施工）
> 审阅方 = GLM-5.2（验证性对抗审）· 主控轻门（细稿边界 + 施工尾）
>
> **本文只给事实与约束，不给解法方向。** 解法由你出细稿定死。

---

## 1. 触发事件

2026-07-30 sm24 端到端跑测第一次尝试，识图 attempt 003 已 accepted、gate① 阻断层干净，
`flow` 一进 J0 判卷即崩：

```
ScoreContractError: score_product_identity_invalid at scoring.input_identity
  reason=elevation_observations_not_list
  (normalize_typed_elevation_observations)
```

未被任何调用方捕获，**整条 flow 挂掉**，下游 1_correction / 几何 / MEP / 装配 / EP 全部未跑。
sm24 是本项目史上第一个 v3 签字答案的 case，所以这条路径此前从未被真实触发过。

---

## 2. 已核实的事实（主控逐条读码复核，2026-07-31）

编号供细稿引用。**这些是事实，不是要求。**

**F1 · 能力判定对 reading 零守卫。**
[`src/agent/judge/score_schema.py:584-609`](../../../../src/agent/judge/score_schema.py#L584-L609)
`decide_score_capability` 有两道产物侧守卫，条件都写死 `stage == "correction"`：
`product_schema ∈ {"3","v3"}`（:598）与 `product_artifact_contract ∈ {correction_b5_v1, correction_b5_orientation_v1}`（:600-608）。
`stage == "reading"` 一道都不过，直接落到 `:609` 的 `path="c2_v3"`。

**F2 · 判卷主流程对 reading 走的是「顶层扁平 payload」形状。**
[`src/agent/judge/score_service.py:223-258`](../../../../src/agent/judge/score_service.py#L223-L258)
`if stage == "correction"` 分支走真生产提取器 `extract_correction_plan_segments(geometry)`；
`else` 分支（:257-258）是 `coerce_plan_observations(product_payload.get("segments", ()))`。
开口侧同理：`:293` 的 `_opening_observations` 读 `payload["openings"]`，
`:50-62` 的 `normalize_typed_elevation_observations` 读 `payload["elevation_observations"]`。

**F3 · 识图产物形态与之不符，且全仓无生产代码产出该扁平形态。**
识图 `output.json` 顶层 = `{"views": {<input_id>: <ReadingView>}}`；
`ReadingView`（[`src/agent/reading/schema.py:119-140`](../../../../src/agent/reading/schema.py#L119-L140)）
的内容是 `strokes` / `dimensions` / `ocr_texts` / `uncaptured` / `self_check` / `facade` / `scale_origin`。
`grep elevation_observations` 全仓只命中测试与 `scripts/tool_scripts/judge_arbitration_sm24_audit.py`
——即**该形状的输入历来全靠测试手搓 payload**，没有任何生产路径产出它。
实测 sm24 attempt 003：`views` = `1f_view` / `North_view` / `South_view` / `East_view` / `West_view`；
`1f_view` 有 15 条 stroke、13 条 dimension。

**F4 · 「回落 legacy 尺子」这条路不存在。**
主控实跑 `load_gt("sm24_anchor")` →
`GtValidationError: gt_v3_requires_typed_consumer at /schema_version`
（[`src/agent/judge/gt.py:66`](../../../../src/agent/judge/gt.py#L66)）。
v3 答案对 legacy 消费者是**硬拒**的，`scripts/tool_scripts/score_reading_vs_gt.py` 的 legacy 路线
（经 `reading_score.score_floor`）在 v3 case 上不可用。
typed 路线经 `load_gt_document`（`gt.py:84`）可读 v3。

**F5 · 立面通道的世界投影已经在生产里，缺的只是形状。**
`gt/<case>/score_inputs/view_bindings.json` 的每个 elevation binding 都带
`along_origin` / `sign` / `world_axis` / `facade_family` / `local_x_positive` / `mirrored`
（sm24 实测四条立面绑定齐全，主控已用生产加载器核过身份全吻合）。
`normalize_typed_elevation_observations`（`score_service.py:50-100`）消费
`{observation_id, source_input_id, floor_id, kind, facade_family, local_x_interval, z_interval}`
并经 bindings 做 local_x → world 投影。
⇒ 立面侧需要的是 **ReadingView → 该条目形状的转换**，不是几何标定。

**F6 · 平面通道相反：约定存在于散文里，代码里零消费者。**
`ReadingView.scale_origin`（`schema.py:125`）**全仓零消费者**——`grep scale_origin` 只命中 schema 定义本身。
sm24 实测该字段值 = `{"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": null, "note": "<自由散文>"}`，
note 自述「原点在 SW 角、x 东 y 北、px_per_m=36.6」。
而 legacy `reading_score.extract_reading_wall_segments`
（[`src/agent/judge/reading_score.py:271-285`](../../../../src/agent/judge/reading_score.py#L271-L285)）
**直接把 reading 平面坐标当世界坐标用**（拿 `W`/`D` 卡边界，无任何变换）。
⇒ 平面侧的「投影」实为一个**从未被代码执行过的恒等约定**，且原点声明字段无人读。

**F7 · 架构原意是识图要走类型化判卷。**
[`scripts/tool_scripts/run_stage.py:1345-1350`](../../../../scripts/tool_scripts/run_stage.py#L1345-L1350)
的生产注释原文：*"Official typed correction scoring is defined only for the manifest-accepted B5
six-artifact bundle … **reading attempts do not have this restriction and must continue through the
scorer**"*，并据此对 correction 早退、对 reading 放行。

**F8 · 识图产物被静默声称为 v3。**
`run_stage.py:1360` 取 `output_schema=str(output.get("schema_version", "3"))`；
识图 `output.json` 顶层**没有 `schema_version` 键**（只有 `views`）⇒ 静默默认为 `"3"`。
即便 F1 的守卫补上 `product_schema` 检查，这个默认值也会让检查恒真通过。

**F9 · 附带的错误文案缺陷（同处）。**
`score_service.py:57` 用 `payload.get("elevation_observations", ())` —— 默认值是**元组**，
`:58` 的校验要求 **list** ⇒「键根本不存在」被报成 `elevation_observations_not_list`，
错误文案指向错误方向（主控初查时被误导过一次）。

**F10 · 同族前科。**
2026-07-20 的 M2 = 判卷循环撞 `ScoreContractError`、全链无捕获 → flow 崩，是同一失败形状；
当时的修法是对**非 accepted 的 correction attempt** 静默早退（`run_stage.py:1349`）。
本次不同：崩在 **accepted attempt 上、且无条件**。

---

## 3. 硬约束（不可协商）

**C1 · R-4 判卷器口径。**「合不合法」的权威在生产、「量不量得了」的权威在判卷，
且判卷器**只许说 unsupported，不许说 broken，更不许崩**。
判卷器拿自己的能力上限宣判上游几何非法 = 本项目连续三轮假红的结构性根源。

**C2 · 空观测 ≠ 不适用。** 若某通道最终判为不做，必须是**显式的 not_applicable 收口并给出理由**，
不得让该通道以「零观测」进入计分从而算成全 miss —— 那是假红，且会被误读成识图模型的锅。

**C3 · 不变量 #4（gt 铁律）。** gt 只 gate② judge / 人可读，gate①/执行器绝不 import。
新写的投影层若被生产侧消费，不得因此让 gt 泄进执行路径。

**C4 · 不变量 #6（复杂度可扩展性）。** 不得把「共底面盒子 / 单层 / 正交 / 平面即世界系」
这类当前简化假设烤死到无法松动。F6 那个恒等约定若要固化，必须固化成**可替换的显式变换**，
不是散落的隐含假设。

**C5 · 用户硬规约（识图质量度量）。** 识图好坏的唯一权威 = **坐标级 reading↔gt 逐元素对账**
（命中 / 偏移），看图仅辅助。2026-07-30 那轮 8/8→1/8 的退化正是靠这把尺子才发现的，
而当时是主控**手工**量的（违「禁手搓判卷」）。这把尺子必须回到生产里。

**C6 · 判卷结论必须由可复算的证书支撑**（2026-07-28 本批核心原则），
不能由执行顺序、错误文案、浮点偶合或未保留的语义前提支撑。

**C7 · 已签字的 sm24 答案字节不动**，签名有效、不重签不迁移。
`case_tests/test_baseline/gt/sm24_anchor/` 受保护树 14 项 hash 必须 byte-identical。

**C8 · 禁改测试迁就实现。** 现有断言不得为了让新码通过而改写；
确需改动必须单列并说明为何原断言是错的。

---

## 4. 用户已下的方向裁定（2026-07-31）

用户拍板原话：**「不急着跑到验收，先把流程修好，通路打通」**。

主控据此裁定：**走真投影（出口 B），范围以「把通路真打通」为准，不为赶验收砍范围。**
主控此前给出的「只做平面通道、立面判 NA」的缩范围方案，其唯一理由是当日能跑到验收；
该理由已被用户取消，故不得再作为缩范围依据。

**但**：若你在细稿阶段实测发现某条通道**在现有输入下确实不可机械投影**，
这属于 C1/C2 覆盖的情形 —— 应当**停下上报**（见 §5），由主控裁定该通道显式 NA，
**不得自行降级为假设，也不得为凑通路而编造标定**。

---

## 5. 交付要求

### 5.1 细稿（第一交付物，先交、待主控轻门后再施工）

- **累计式自包含**：同路径迭代禁「vN 不变」引用已覆写正文，每版全文累计。
  自检 = 一个新执行者只读当前稿能否施工。
- **边界必须由你定死，不得留给施工方猜。** 这是本项目 2026-07-27 那批连续三轮 REWORK 的共同病根
  （r0 守恒边界没定 / r2 并存优先级没定 / r3 哪些算真破裂没定），2026-07-28 那批靠「设计者即施工者 +
  欠规格边界逐条上报」才闭环。你这轮**既是设计者又是施工者**，边界理解误差本应最小 —— 用好这一点。
- **欠规格边界必须列成清单上报，不得自行降级为假设。** 上一批施工方上报 10 处、无一自行降级，
  主控逐条裁定后写进派工单、与设计稿同等约束力 —— 那是本项目至今最有效的一次治理动作。
- **探针数字随稿落盘**：稿里出现的任何实测数字，必须附可复现脚本或命令，主控会独立复跑对账。
  （2026-07-22 教训：未落盘的探针数字被审阅方直接判「无法判定」。）
- 稿子落 `AI_agent/proposals/reading_typed_scoring_plan_sol.md`。

### 5.2 施工（主控细稿轻门通过后）

- 按细稿 §Slice 拆分，**「先落会红的锁」优先**：每个 Slice 先写在现码上必红的测试，
  再写实现让它转绿；红的理由必须**逐条对靶**（写清这条红证明了哪个缺陷真实存在）。
- **neuter 自查表**：每把新锁指定一处 neuter（生产码上的定点破坏），报告该 neuter 下**哪些测试变红**。
  「全仓绿」不等于「锁是真的」—— 本项目在这一点上栽过至少三次。
  **诚实披露优于伪造**：查出自己的锁其实是假锁并修到夹具层，是本项目认可的正面样板。
- 每个 Slice 边界 commit + 写执行日志到
  `AI_agent/logs/reviews/execution/2026-07-31_reading_typed_scoring_sol.md`
  （运维教训：codex MCP 连撞过四次 30 分钟静默超时，主控靠**读工作树 + 执行日志**看进度，
   不能只看 stdout。你每个 Slice 落盘一次，主控就零工作丢失。）
- 跑测节奏：中间轮只跑受影响子集（用 `scripts/tool_scripts/affected_tests.py` 算，禁自由裁量），
  交付前跑一次全仓。**主控轻门的独立全量是唯一权威门**，你的自跑不替代它。
  当前基线 = **1786 passed / 10 xfailed / 0 failed**。

### 5.3 sol 执行护栏（规约 §5 硬条款）

1. **删除 / 覆盖 / 推送 / 外发必须单独授权** —— 尤其 §3 C7 的受保护答案树。
2. **每阶段给可验证证据**（测试输出 / diff / 实际状态），不给自述。
3. **一个 Slice 做完即停**，重新审视计划再继续。
4. 简报只回 inline terse report，**不要贴 diff / 文件内容**；主控自己跑 `git diff`。
5. 简报必含 **review-ask 段**：哪些处没把握 / 做了判断取舍 / 动了风险点或不变量。
   无则写 `none — routine spec'd execution`。
   **「我当时的意思是……」不是可接受的交付说明。**

---

## 6. 验收口径（主控会这样验）

1. 独立全量 pytest，逐数字对账，零回归。
2. 亲核 diff；重点看 F1 守卫是否**恒真**（F8 那个默认 `"3"` 会让 schema 检查变成永真断言）。
3. 抽查 neuter：主控会在 `/tmp` 副本上自己拆锁，看红的是不是你说的那几条。
4. **活体跑通 sm24 的 J0**：识图 attempt 走真 `flow`，要么出分、要么响亮 NA，**不许崩**。
5. GLM 会做验证性对抗审（它的强项），并被要求实跑你指定的 neuter 对账。

---

## 7. 起手建议（非解法，只是省你时间）

- 现场：`case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json`
  是真实的 accepted 识图产物（质量不合格 1/8，但形状是真的），可直接当输入夹具。
- 答案：`case_tests/test_baseline/gt/sm24_anchor/gt.json`（v3，`human_verified`，**只读**）。
- 侧车：`case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json`。
- 崩溃复现：走 `flow` 或直接调 `score_typed_attempt(stage="reading", ...)`。
