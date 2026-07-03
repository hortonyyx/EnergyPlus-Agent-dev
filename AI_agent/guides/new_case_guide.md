# 主 Agent 操作手册 —— 单一 `flow` 编排 + judge② + 人工校验 跑 case / 建 baseline（2026-07-02 重写）

> **这份文档是给「主控 Agent」看的初始上下文 + 操作手册。** 你（Opus / 任何主控模型）在 dev 期负责：
> **编排** 0–5 管线、**当 judge②** 裁每段 LLM 产物、在**人工校验点**替用户把关、**记录**，最后给用户一份
> 人读总反馈 + 🔍 肉视清单。**换主控模型时，读这一篇就能接手**（不依赖任何单独 memory）。
>
> **范围**：本项目侧 = 识图 → 校正 → 几何（造面+切配）→ 物理 → 装配 → 产 `IntakeOutput` → 下游 9
> subagent → EP。权威接线见 [architecture/pipeline_stage_contracts.md](../architecture/pipeline_stage_contracts.md)。
>
> **一条命令**：正规流程由单一 anchor-aware 编排 verb
> [`run_stage.py flow`](../../scripts/tool_scripts/run_stage.py) 驱动——从当前位置推进到**下一个需要人介入
> 的检查点**（judge / 人工校验 / 几何确认）就停，你处理完**重跑同一条 `flow`** 即自动续（manifest-first）。
> 别再手串 ~15 条 per-stage 命令、别抄近道（run_pipeline 直连 / `run_full_pipeline --intake-from` 会跳过
> judge/attempts/3D/report）。per-stage verbs（run/judge/resample/approve-geometry/status）仍在，`flow`
> 是它们的组合层。

---

## 0. 你的角色与三层叠加门

每段产物依次过**三层门**（叠加、非互斥）：

```
每段产物 ─►─ gate① 确定性(代码)  ─►─ judge② (你, 该段有 judge 且开关 on)  ─►─ 人工校验 (用户, 该点开关 on)
             便宜先跑·违反不变式即失败分类     gt坐标对账(权威)+看图(辅助)              judge 过后停·给用户看 grade 批卷+分表·拍板
```

| 层 | 谁 | 判什么 | 处置 |
|---|---|---|---|
| **gate① 确定性** | 代码 [`validate_case`](../../src/agent/execution/validation_run.py) | 结构/几何不变量(block) + 交叉核对(flag) | block→盲重抽/fail-closed；flag→留痕放行 |
| **judge② gate** | **你**（多模态）| 该段 rubric 逐条 `pass/minor/severe/fatal`（结构化清单**非数字分**）| severe/fatal→3 次盲重抽（按根因路由）；minor→flag |
| **人工校验** | **用户** | judge 之上的外层终审兜底（judge 盖不死的感知项）| judge 过后停·你给用户 grade 批卷+坐标分表·用户拍板（OK→advance / 打回→重抽/重读）|

**开关叠加解析**：judge 开 + 人工开 → judge 先过、用户再审；judge 开 + 人工关 → 只 judge；judge 关 + 人工开
→ 只人工；都关（或该段无 judge）→ 继续。**judge 与人工是叠加不是二选一**。

**judge 判卷口径（硬规约，[[judge-gt-authoritative-images-auxiliary]]）**：
- **数据权威层 = gt 坐标对账**（`score_*_vs_gt`，**放宽容差**、判布局/计数/窗位定性命中，非毫米精确）。judge
  packet 已带机读 evidence：`score_vs_gt`（sidecar 路径）+ `score_criteria`（suggested pass/minor/severe）+
  `grade 批卷`（产物↔gt 叠图 PNG）。**以对账为主判据、看图为辅**（看图只补对账盖不到的感知类，如"这是门不是窗"）。
- **但 `StageVerdict` 仍是你的裁决权威**：`score_criteria` 是 advisory evidence，**代码绝不把它写进
  verdict、绝不用数字分替 checklist**。你读完对账 + grade 批卷 + 原图，**自己**写 `StageVerdict`。

judge 密度（读码实证）：**仅 J0(0_reading)/J1(1_correction) enabled**；J4(4_mep) disabled stub；确定性段
2/3/5 无 per-run judge（靶子=代码单测）。**J23（几何 judge）= P2 规划中、尚未落地**——当前几何一层只有
gate① + 人工确认门（见 §2 S2/S3）。rubric 见 `skills/intake_pipeline/{0_reading,1_correction}/judge_rubric.md`。

### 三个人工校验点 ↔ 阶段 ↔ judge ↔ 数据权威层 ↔ grade 批卷

| 校验点(开关) | 阶段 | judge | 数据权威层 | 产物↔gt grade 批卷 |
|---|---|---|---|---|
| **reading** | 0_reading | J0 | `score_reading_vs_gt` | reading 描边叠 gt（`grade.png`）|
| **correction** | 1_correction | J1 | `score_correction`(几何对账) | correction cell 叠 gt（`grade.png`）|
| **geometry(3D)** | 2/3 | J23（P2 未落地）| `score_geometry_vs_gt`（P2）| **直接看既有 `manual_review/geometry_viewer.html`**（不新渲 grade 批卷）|

**grade 批卷（`render_grade.py`，2026-07-03）= 对 gt 答案的批卷图**：一张合成图 = 平面各层 + 四立面。**sidecar-driven**——只读该 attempt 的 `score_vs_gt.json` 判定**不重算**（图↔证据同源）。**颜色=判定**（绿实线=命中 / 红虚线+淡红填充=漏 / 红实线=多；窗位置画错=gt 原位红幽灵 + 产物错位红实）；**类别=画法**（外边界·内墙 zone 邻接合并线段·窗外挂车道·立面轮廓+楼层线+窗盒）；容差内漂移画淡绿 ±tol 带 + 灰真值中线；**边界/立面外框/楼层线是中性灰参考（未被判定，绿红只留真被判元素）**。**reading 和 correction 各出一套**（都对同一 gt→两表不一样处=correction 结构操作净效果，看进步/退化）。**per-attempt 留痕**：每个 `attempts/NNN/` 都出自己的 `score_vs_gt.json`+`grade.png`，accepted 的 promote 到 `<stage>/grade.png` + `report/eyeball/{0_reading,1_correction}_grade.png`。

**判卷容差 = judge 侧两把独立尺**（`run_config.yaml` 的 `grade:` 段：`reading`/`correction` 各 `wall_tol_m`/`window_centre_tol_m`，per-run 可调，**默认相等 0.30/0.40**）。**≠ `correction.yaml`**（那套是确定性几何核坍缩坐标的**生产尺**、另一回事）。判卷命中/漏/多由**确定性代码**（`_match_lines`/`_match_windows`）判、非 LLM。**correction 是 gt-盲**（修不了连贯准确度误差、只修内部不一致）→ **reading 判卷尺是准确度真闸门，别设得比 correction 松**（否则错误过 reading→correction 修不动→只能后移无解）。

## 0.1 case = 纯素材；每次 run 自包含进 `run_<注释>/`

**case = 一组确定的测试素材**——`<case>/` 入库时**只含 `case_data/`**（`*_view.png` +
`testdata_prompt.json`）。**改素材才新建 case**。**每次跑 = 一个自包含的 `run_<注释>/`**（单 case 可多轮）：

```
<case>/
  case_data/                       ← THE case（素材；改素材才新 case）
  run_<注释>/                       ← 一次 run（自包含）
    llm.yaml                       本 run 模型配置（reading 模型/effort + 下游 + orchestrator 溯源）
    run_config.yaml                跑前配置（scope/judge/review/models/grade 五段；缺失软降级到旧默认+warn）
    0_reading/                     本 run 识图（复用好识图=拷进新 run）+ 段根 grade.png（accepted 升级件）
    1_correction/ … 5_intakeoutput/  各段产物 + <stage>_checks.json + <stage>/grade.png + attempts/NNN/{output,checks,judge,score_vs_gt,grade.png}
    manual_review/geometry_viewer.html  几何人工校验（3D 离线查看器）
    EP/EP_run/                     EP（flow --with-ep 固定落这里）
    _run/                          机器记账：run_manifest / baseline / orchestration_state / geometry_approval / human_review
    report/REPORT.md               唯一人读报告（GEN 事实区 + AGENT 叙事/建议）
```
`1_correction…5_intakeoutput/ EP/` 由代码**跑中建**，绝不预搭空骨架。`validate_case(<run_dir>)` /
`record_baseline(<case> <run>)` / `flow <case> <run>` 都对**一个 run 目录**操作（case 素材由 `run_dir.parent` 解析）。

## 0.2 参考答案（gt）= judge② 专用，gate① / 执行器绝不看（铁律）

每个 case 的评测标准答案放 [`case_tests/test_baseline/gt/<case>.json`](../../case_tests/test_baseline/gt)
（真实区划 / 每立面窗数 / 尺寸真值，人读原图独立得出）。**只有你（gate② judge）+ judge-side 工具经
[`src/agent/judge/gt.py:load_gt`](../../src/agent/judge/gt.py) 读它**（`score_*_vs_gt`、grade 批卷 渲染都在
judge/tooling 侧）；**gate① 与执行器绝不 import**（gate① 随上线、prod 无答案，必须 dev/prod 一致；执行器看了
=照抄、误差预算崩）。机械守：[`tests/test_gt_discipline.py`](../../tests/test_gt_discipline.py)。详见
[gt/README.md](../../case_tests/test_baseline/gt/README.md)。无 gt 的 case = 简单测试、判卷降级为纯看图、不上主线。

## 1. 不污染原则（最重要，机械保证，别破）

> 你既编排又当 judge，最大风险是把 judge 信息 / 下游信息 / gt 泄漏进某段输入，污染误差预算与训练数据。

1. **各阶段执行器隔离**：每段用**独立 API 调用**或**冷启子 Agent**，只喂该段**合同输入**（规则 + 上游产物 +
   testdata），看不到你的 judge 评语、看不到下游信息、看不到 gt。子 Agent 冷启 = 天然隔离。
2. **重做 = 盲重抽**：judge 说"不行"只触发"**同样输入换采样重跑**"，你的评语**只进带外记录**
   （`attempts/NNN/judge.json`），**绝不回灌 prompt**（`judge/retry.py` 已强制永不注入）。`flow` 的自动重抽
   也是盲抽。
3. **失败先分类再处置**（[contracts §0.3](../architecture/pipeline_stage_contracts.md)）：
   - `deterministic_code_failure`（确定性段后置失败）→ **fail-closed、记 code defect、不弹上游/不换样本**。
   - `stochastic_draw_failure`（0自动后/1/4 的 draw）→ **盲重抽**（≤3，超则 quarantine 交人）。
   - `upstream_input_failure`（输入违反前置）→ 弹**上游产出段**。
   - `judge_mismatch` → 盲重抽；归因不确定（root_confidence 低）→ **不自动路由、交人**（`judge_block_human`）。
   - **0_reading 默认 = manual** → `human_redraw_required`；`reading_runner_available=True` 时可
     `awaiting_reread`，由你冷启隔离子 Agent 盲重读（≤每段预算）。

## 2. 完整跑测 SOP（6 步，主控 ↔ 用户）

> 记号：`<case>` 在 `case_tests/e2e_tests/<case>/`；`BD=case_tests/e2e_tests`。

**Step 1 · 查 gt 状态 → 报用户**。有 gt = 正式跑（判卷 gt 权威）；无 gt = 简单测试、不上主线、判卷降级。

**Step 2 · 定模型配置 + 建新 run 目录 →（跟用户确认一次）**。落 `<run>/llm.yaml`（reading 模型/effort +
下游模型 + orchestrator），run 溯源记录（[[run-provenance-recording-requirement]]）。reading 由冷启子 Agent
产（见 §2.1 + 附录 A），写进 `<run>/0_reading/*_view.json`。

**Step 3 · 定起止范围 + judge 开关 + 3 个人工校验开关 →（用户拍）**。映射到 `flow` 参数（见 §2.2 矩阵）。

**Step 4 · judge-in-the-loop 跑**：`run_stage.py flow`。它推进到下一个检查点就停（退出码 10）：
- **judge 停点**（`--judge stop` 且该段 J0/J1）：看 packet 的 `score_vs_gt` + `grade 批卷` + 原图 → 写
  `StageVerdict` → `judge ... --verdict v.json` 提交 → **重跑 flow 续**。verdict 非阻塞→advance；severe/fatal
  可路由→`flow` 自动盲重抽根因段；不可归因→交人。
- **几何确认停点**（`--geometry required`）：看 `manual_review/geometry_viewer.html` → `approve-geometry` →
  重跑 flow。（`--geometry auto` 则 flow 自动过、记 `actor=flow:auto/policy=auto` 审计字段，用户"跳我审直接过"即此档。）

**Step 5 · 开了的人工校验点**：judge 过后 flow 停在 `awaiting_human_review`（退 10）→ 你给用户看
`attempts/NNN/grade.png` + `score_vs_gt.json` 坐标分表 → **用户拍板** → `approve-review <case> <run> <stage>
--actor <user>` → 重跑 flow 续。（人工校验绑 accepted `output_hash`，任何重抽即失效重审。）

**Step 6 · 跑完 → report → 汇报**：`flow --with-ep --record` 收尾产 `_run/baseline.json` +
`report/REPORT.md`，你补 AGENT 区叙事 + 四桶建议（§4）→ 向用户汇报。

### 2.1 reading（0_reading）来源
`flow` **默认复用现有 `<run>/0_reading/`**（本项目 reading = 冷启子 Agent 产，非 flow 自动化）。`--from
1_correction` 起（显式声明复用已判 reading）。若 reading 缺/未过，flow 停并打印子代理 reading/reread 协议
（不在 flow 内起子代理）。启动 prompt 见 [附录 A](#附录-a--识图0_reading-子-agent-启动-prompt)。

### 2.2 `flow` 命令矩阵（一条命令覆盖两种典型跑法）

```bash
BD=case_tests/e2e_tests
# dev judge-in-the-loop（正规重跑，判在环 + 人工校验点 + 全产物 + 3D + EP + report）
python scripts/tool_scripts/run_stage.py --base-dir $BD --date <ISO> flow <case> <run> \
    --judge stop --review reading,correction --geometry auto \
    --with-ep --record --orchestrator <你的模型id>
#   停 judge → 提交 verdict → 重跑；停 human_review → approve-review → 重跑；auto 几何自动过

# regression 一把过（回归/CI，judge off = 仅 gate①，无人可停）
python scripts/tool_scripts/run_stage.py --base-dir $BD --date <ISO> --run-profile regression flow <case> <run> \
    --judge off --geometry auto --with-ep --record --orchestrator <你的模型id>
```

**flow 参数**：`--from auto|<stage>`（默认 auto=manifest-first 从最早未 advance 段起，不静默跳 0_reading/J0）·
`--to <stage>`（默认 5_intakeoutput）·`--judge stop|off`·`--review reading,correction`（人工校验开关，默认无）·
`--geometry required|auto`（默认 required）·`--with-ep`·`--record --orchestrator <m>`·`--record-partial`（有
pending 段仍强记）·`--llm-config`·`--epw`。

**退出码**（scriptable）：`0` 完成 / `10` 停在人或动作检查点（judge/几何/人工校验/reread/未能自动处理的
JUDGE_BLOCK）/ `20` 终止编排停（quarantine/deterministic_defect/human_redraw/judge_block_human）/ `30`
EP·record 失败（含有 pending 段 `--record` 未加 `--record-partial`）。

**辅助 verbs**：
```bash
python scripts/tool_scripts/run_stage.py --base-dir $BD status <case> <run>                 # 编排账本 + stop_reason
python scripts/tool_scripts/run_stage.py --base-dir $BD judge <case> <run> <stage> --verdict v.json
python scripts/tool_scripts/run_stage.py --base-dir $BD approve-geometry <case> <run> --actor <you>
python scripts/tool_scripts/run_stage.py --base-dir $BD approve-review   <case> <run> <stage> --actor <you>
```

### 2.3 逐段执行器 + gate① + judge（`flow` 内部按此推进）

- **S0 0_reading**（识图，冷启子 Agent；后 VLM）：gate① `check_reading_view` 结构 linter；**gate② J0**（你看
  原图 + `*_render.png` + `grade.png` + `score_vs_gt.json`，rubric=`0_reading/judge_rubric.md`）；致命/严重→
  human_redraw / awaiting_reread（handoff 见 §2.1 + 附录 A）。
- **S1 1_correction**（DeepSeek 独立调用）：执行器 `run_correction`（只喂 reading+testdata+规则、看不到 judge/gt）
  → 确定性核吸附 `apply_deterministic_core`；gate① `check_correction`（coverage/closure/zstack + 区数 tripwire
  + 窗位落墙 + evidence 覆盖）；**gate② J1**（你看原图 + `zones.png`/`elev.png` + `grade.png` +
  `score_vs_gt.json`，rubric=`1_correction/judge_rubric.md`）severe/fatal→盲重抽。
- **S2+S3 几何内核**（代码，确定性，无 per-run judge）：`materialize_kernel_geometry` 造面+切配；gate①
  `check_kernel`（封闭/法向/pairing-gate/矩形 coverage/spec 自洽），block=**代码缺陷 fail-closed**；过 gate① 后
  生成 **`manual_review/geometry_viewer.html`**（three.js 离线交互：orbit/半透明/截面/爆炸/量距/着色）→ 几何
  **人工确认门**（`--geometry required` 停 `awaiting_geometry_approval`；用户看完 `approve-geometry` 绑 digest、
  几何漂移自动失效）。**J23 几何 judge = P2 规划**（判过度分区/欠合并 + `score_geometry_vs_gt`），当前未落地。
- **S4 4_mep**（DeepSeek 独立调用）：`run_mep`；gate① `check_mep`（引用图 + load→schedule + schedule 完整性 +
  对象语义 + placeholder 禁令）；**gate② J4 暂 disabled**（记 disabled，非假 PASS）。
- **S5 装配 + EP**：`assemble_intake_output` + `validate_contract` → `intake_output.json`；`check_assembly`。
  `flow --with-ep` 跑下游 9 subagent + InterZone 门 + EP → `<run>/EP/EP_run/`（共享 `run_downstream_ep`，EP 无论
  入口都落这里）。EP end 断言 `check_ep_baseline`。

## 3. 记录（attempts 全上 + 成绩单）

- **每次抽都落 append-only attempt**：`<stage>/attempts/NNN/{output,checks,judge}.json`（+ judge 段的
  `score_vs_gt.json`/`grade.png`），accepted 指针进 `_run/run_manifest.json`（`file_stage_attempt`；坏草稿不覆盖）。
- **你的 judge verdict** = `StageVerdict`（schema v2：criterion status + root_stage/confidence + recoverability，
  见 `src/agent/judge/verdict.py`，`extra="forbid"`——别往里塞 score 数字分）。
- **人工校验记录** = `_run/human_review.json`（绑 accepted `output_hash`，resample 即失效 fail-closed）。
- **成绩单**：`flow --record`（或单独 `record_baseline.py <case> <run> --date <ISO> --orchestrator <m>`）跑
  `validate_case` + 汇总 + 读 llm.yaml/EP end + 收集 attempts/verdicts → `_run/baseline.json` + `report/REPORT.md`。

## 4. 给用户的总反馈 + 🔍 肉视清单

`record_baseline.py` 生成单一 `report/REPORT.md`：GEN 区代码刷、AGENT 区你撰写。**你必须填 AGENT 槽**，尤其
错因链 + 四桶建议（机制 / 能力 / 脚手架 / 修法）；建议区结构化 bullet：`action` / `evidence: [E:...]` / `owner`，
每条 evidence id 必须存在于 `_run/baseline.json.evidence_index`（citation linter 纯词法卡）。无证据支持则留哨兵
`本 run 无可证据支持的建议`。**你在对话里也复述这份反馈**：
- 结论（clean / blocked）+ golden 计数 + EP 结果。
- **🔍 必看**（人工校验，确定性+judge 盖不死的）：① `report/eyeball/` 填色区图/grade 批卷 vs 原平面（走廊有没被切断）
  ② 立面窗位图/grade 批卷 vs 原立面（窗在不在对的立面）③ `manual_review/geometry_viewer.html` 体量/分区/窗位像不像
  ④ 每条 flag 对应的那张图那一点。**精确到"看哪张图哪一点"，别让用户瞎看。**

## 5. 「干净」收口 + baseline 入库

- 收口标准：gate① **0 block** + EP **0 severe**；flag 允许但必须在 `_run/baseline.json.flags[]` 留痕。不该有的
  flag（区数 tripwire / 跨图对账不齐）→ 回 S0 修识图到干净，不带病入库。
- 入库：[`case_tests/test_baseline/index.md`](../../case_tests/test_baseline/index.md) 登记一行 + 加/更新该 anchor
  golden 测试（`tests/test_validation_run_baseline.py` 断言 `blocked=False` + 计数 + EP 干净）。
- anchor 管线产物**提交入库**（冻结金标准；EP `eplusout.*` 与 `EP/temp_*` 仍 gitignored）。

## 6. 模型配置（per-run）

`<run>/llm.yaml`（从全局 `src/configs/llm.yaml` 拷模板，经 `EP_AGENT_LLM_CONFIG` 覆盖；`flow --with-ep` 解析序
= `--llm-config` > `<run>/llm.yaml` > `<case>/llm.yaml` > 全局）。段→阶段：

| 段 | 阶段 | thinking |
|---|---|---|
| `intake_correction` | 1_correction（+几何兜底）| **enabled**（单次推理）|
| `intake_mep`（缺则回退 correction）| 4_mep | enabled |
| `default` | 下游 surface/construction/fenestration | disabled（多轮 ReAct，开则 400）|
| `zone`(*flash) | 下游 zone/material/schedule/hvac/people/lights | disabled |

换模型 = 改 run 里的 `llm.yaml`，不动全局/代码。

## 7. 常见坑

| 坑 | 处理 |
|---|---|
| 抄近道（run_pipeline 直连 / `run_full_pipeline --intake-from`）| **别**——跳过 judge/attempts/3D/report。走 `flow` |
| 识图把杂物当结构 / 漏真墙 | gate② J0 抓（看 `grade.png` + `score_vs_gt`）；manual → human_redraw |
| 走廊被切成多段（区数 ↑）| gate① 区数 tripwire flag + J1 布局裁决；回 S0 修 |
| judge 拍脑袋 | 以 `score_vs_gt` 对账为主判据、看图为辅；坐标一对账就见真章 |
| 1_correction 0 窗 / 非法 JSON | draw 级校验已拦 → 盲重抽（DeepSeek 偶发）|
| EP 段错（不完整 schedule）| `mep.schedule_completeness` 前移已拦 |
| `flow` 停在 human_review 反复停 | 记得 `approve-review`（绑 output_hash）后再重跑 flow |
| EP `eplusout.end` 缺 | fatal/段错，**非 PASS**（`check_ep_baseline` fail-closed）|

---

## 附录 A · 识图（0_reading）子 Agent 启动 prompt

> S0 用。冷启一个多模态子 Agent / 独立会话。**启动 prompt 已版本化为单文件**
> [`skills/intake_pipeline/0_reading/session_kickoff.md`](../../skills/intake_pipeline/0_reading/session_kickoff.md)
> ——durable 纪律不贴这里（根因=非版本化启动 prompt 会悄悄退化），规则真身在
> `skills/intake_pipeline/0_reading/` 三件套，运行时读取。

把下面**单行**作首条消息（按 case 改占位）：

```
Read skills/intake_pipeline/0_reading/session_kickoff.md and follow it for case <CASE>.
The drawings are at <CASE>/case_data/ (or the path I give you); fill the image table in the kickoff
before tracing. Do the pilot first, then stop and wait for my review.
```

`session_kickoff.md` 自身指引读三件套 + 填图名表 + pilot→review→batch 流程 + 边界。改纪律请改 `guide.md`
（版本化），不要改回启动 prompt。**污染硬隔离**：给子 Agent 只喂 `case_data/*.png` + testdata + skill，禁 prior
strokes/attempts/judge 评语/gt。

---

_2026-07-03 — 流程清理批次（`7.03_FlowCleanupBatch1/2`）：① 新增 `<run>/run_config.yaml`（scope/judge/review/models/grade 五段·缺失软降级）；② overlay → **`render_grade.py` gt 批卷**（sidecar-driven 只读判定不重算·颜色=判定/类别=画法·墙窗分层·容差带·边界中性灰·reading与correction各一套对gt）；③ **per-attempt 全渲染**（每 attempt 各出 grade·accepted promote 段根+eyeball）；④ **判卷容差=judge 侧两把独立尺**（run_config `grade:` 段·per-run·非 correction.yaml·默认相等·别让 reading 更松）；⑤ F1 修（judge packet 传 in-memory manifest·首-pass gt-evidence 不再空）。产物 `overlay.png`→`grade.png`。_

_2026-07-02 — 重写为「单一 `flow` 编排 + 三层叠加门（gate①→judge②→人工校验）+ gt 权威判卷 + grade 批卷」：
正规流程从 ~15 条 per-stage 命令收敛为单一 `run_stage.py flow`（manifest-first 可续 + 3 开关叠加 + JUDGE_BLOCK
自动重抽 + geometry-auto 审计 + durable 人工校验 + 退出码）。judge 判卷以 `score_*_vs_gt` 对账为权威主判据、
看图为辅（`StageVerdict` 仍裁决权威、score_criteria 仅 advisory）。J23 几何 judge + `score_geometry_vs_gt` = P2。
配套 P1 落地：`flow`/`approve-review` verb（run_stage.py）·`review.py`·共享 `run_downstream_ep`·judge-side
`score_policy`/`correction_score`/`render_overlay`（2026-07-03 改名 `render_grade`）。旧「逐段 ~15 命令」版备份 git 历史（2026-06-16 重写版）。_
