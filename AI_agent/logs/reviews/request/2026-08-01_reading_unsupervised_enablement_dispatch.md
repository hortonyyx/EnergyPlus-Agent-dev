# 派工单 · reading 无监督达标批（W1 / W3 / W4）

> 出单人：主控 Opus 5 · 2026-08-01 · 用户已拍板批次范围与打法
> 施工：**GPT 侧 terra**（`gpt-5.6-terra`，effort=high）—— 用户 08-01 拍板改派 GPT 侧；
> 按 [codex_execution_protocol §5](../../../guides/codex_execution_protocol.md) 「**sol 原则上不当执行器**」
> 取中档执行席 terra，非 sol。
> 对抗审：**GLM-5.2**（跨家族，谁写谁不批）· 主控轻门独立全量。
> 依据：[主控参与生产排查](../../experiments/2026-08-01_controller_in_production_audit/README.md)
> · [无监督识图基线](../../experiments/2026-08-01_unsupervised_reading_baseline/README.md)

---

## 0. 背景（施工方必读，决定你怎么取舍）

本项目的识图（0_reading）阶段由一个冷启动的隔离子代理完成。**产品形态里没有更强的 agent 在旁边
指导它**——判卷只能在整段做完之后整体打回重抽，**不允许按子部分打回、不允许告诉它哪里错了**。

2026-08-01 实测了第一份**无监督**基线（两臂，唯一变量＝有无确定性预扫）：

| 臂 | 五图读完 | 中途停下提问 | 实际跑的探针 | 内墙命中 | 平面窗 |
|---|---|---|---|---|---|
| A（带预扫） | ✅ | 无 | **0 个** | 20.70 / 57.86 m（36 %） | 0 / 11 |
| B（无预扫） | ✅ | 无 | 2 批 | **0.00 / 57.86 m（0 %）** | 0 / 11 |

**根因已定位，本批就是修这两条**：

1. **它不去测量**。A 臂自述 *"No px_per_m scale established yet (CV toolbox deferred);
   coordinates estimated from visual inspection"* —— 手里有整套 CV 工具箱和现成的确定性候选，
   **一次探针都没调**，全靠目测估坐标。
2. **它试过一次，被工具的语法挡回去就放弃了**。A 臂唯一一次标定尝试的守卫回执是
   `probe arguments must be paired --key value; unexpected bare argument: px_m_calibrator`
   （它漏了 `--tool`），此后再没试过。B 臂在探针语法上被拒 6 次，含 `--help` 被拒。

历史对照说明这不是模型看不懂图：2026-07-07 同一个 Haiku 4.5、同样的图，**在被明确要求
「必须先量再画」时调了 19 次探针**，拿到墙 9/9 / 窗 7/7 / 立面窗 15/15。
那次的「必须先量」是**当轮临时指令**（per-run directive）；本批要做的是**把这个强制力
放回随产品发布的 standing 文档**，并把它上次放弃测量的那道坎移掉。

---

## 1. 硬约束（全批适用，违反即 REWORK）

1. **不得改 `case_tests/test_baseline/gt/**`**（评测答案，判卷专用，改动即污染信任根）。
2. **不得改 `case_tests/e2e_tests/*/case_data/**`**（case 素材）。
3. **不得放松 2026-07-31 建成的写保护与路径隔离**（那批净收紧 13 处，不得倒退）。
   W3 改的只是**参数解析的宽容度与错误可操作性**，不是权限边界。
4. **standing 文档里不得出现任何具体 case 的信息**（不得提 sm24 / sm21 / 具体尺寸 / 具体失败形状）
   —— 这些文档随产品发布，写进去就是把答案漏给未来所有 case。
5. **不得为了让新机制"看起来通过"而修改任何历史 run 的产物。**
6. **默认行为不变**：未显式启用新机制时，所有现有 run 与测试的行为必须**逐字不变**。
7. 每个 Slice 做完即停并给可验证证据；删除 / 覆盖 / 推送需单独授权。
8. 「我当时的意思是……」不是可接受的交付说明——边界不清楚就**停下上报**，不要自行降级为假设。

---

## 2. W1 · 把「先量再画」的强制力放回 standing 文档

### 现状（已核，带行号）

- [`session_kickoff.md:25`](../../../../skills/intake_pipeline/0_reading/session_kickoff.md#L25)：
  *"CV evidence tools: `cv_toolbox.md` — deterministic pixel probes; **see that file for when the
  toolbox is required or deferred**"* ← **一层间接**：要不要用，推给另一个文件去判断。
- [`cv_toolbox.md:3`](../../../../skills/intake_pipeline/0_reading/cv_toolbox.md#L3)：
  *"Use the CV toolbox before drawing semantic reading JSON for clean vector CAD PNGs…"*
- [`cv_toolbox.md:50`](../../../../skills/intake_pipeline/0_reading/cv_toolbox.md#L50)：
  *"Calibrate first. Before any meter coordinate is written, establish px-to-m scale… Calibration
  anchors must be dimension-chain extension-line intersections or ticks, not wall endpoints or text
  baselines… Target residual is at most 1 px…"*
- `session_kickoff.md` 的 **Non-negotiables 清单里没有「先量」这一条**（现有四条是：误差预算 /
  不过度分割 / 不做拓扑且声明 scale_origin / pen 与 healing / verbatim 与 null）。

### 目标

让一个冷读者在读 kickoff 的**不可协商清单**时，**第一条就知道「必须先标定、先测量，然后才写米制坐标」**，
不需要跳到另一个文件去判断这是不是可选的。

### 硬边界（这几条我写死，不下放）

1. **只做搬运与提级，不新增规则内容。** 措辞可以改写，但**不得引入 `cv_toolbox.md` /
   `guide.md` / `reading_guide.md` / `pen_library.md` 里不存在的新纪律**。
   （理由：新增内容＝主控借 standing 文档投喂，违反不变量 #7。）
2. **保持 kickoff 既有的设计原则**——[`session_kickoff.md:10-11`](../../../../skills/intake_pipeline/0_reading/session_kickoff.md#L10)
   明写「durable 规则不在此重复，重复过的摘要正是当初漂移退化的原因」。
   ⇒ **提级的形式 = 在 Non-negotiables 里加一条「必须先量」的条目 + 指向规则真身**，
   **不是**把 `cv_toolbox.md` 正文抄进 kickoff。
3. **删掉那层间接**：`required or deferred` 的判断不能再推给读者去别处查。
   clean vector CAD 上「必用」这件事要在 kickoff 面上直接成立；
   降质输入（扫描件/手绘）的例外仍指向 `cv_toolbox.md`（该文件已写明该分档尚无 robustness profile）。
4. **四份规则文档正文不动**（`guide.md` / `reading_guide.md` / `pen_library.md` / `cv_toolbox.md`）。
   本项只动 `session_kickoff.md`。若你认为必须动 `cv_toolbox.md` 才能达成目标，**停下上报**。
5. 改动前按 §5#4 备份到 `backup/Skill_history/2026-08-01_<reason>/`。

### 验收

- 冷读者只读 kickoff 的 Non-negotiables 即可知「先标定、先测量」是不可选项。
- `git diff` 显示新增内容全部可在四份规则文档里找到出处（交付时逐条给出处行号）。
- 零具体 case 信息。

---

## 3. W3 · 探针 wrapper 的可用性（让一次语法失败不再导致整个测量环节被放弃）

### 现状（2026-08-01 实测，`access_log.jsonl` 取证）

| 臂 | 守卫回执 | 后果 |
|---|---|---|
| A | `probe arguments must be paired --key value; unexpected bare argument: px_m_calibrator` | **放弃标定，改目测** |
| A | `compound shell token forbidden: \|` ×2 · `command is not allowlisted: mkdir` | |
| B | `unknown probe parameter --help; allowed: --tool --image …` | **想查接口被拒** |
| B | `probe batch must be an object containing only 'requests'` · `probe batch request 1 must contain exactly id, tool, args` | 摸索 batch 格式 |
| B | `command is not allowlisted: find` ×2 · `compound shell token forbidden: \|` | |

### 目标

一次参数写错之后，读者能**从回执本身知道正确写法并立刻改对**，而不是放弃测量。

### 硬边界

1. **`--help` 必须可用**，且输出 = 完整用法 + **至少一个可直接复制粘贴的正确调用示例**
   （三种形式各一：`--tool` 直调 / `--request` / `--batch`）。
2. **参数错误的 reason 必须给出正确形式，不只说错在哪。**
   反例（今天的实际回执）：`unexpected bare argument: px_m_calibrator` —— 没告诉它应该写
   `--tool px_m_calibrator`。正例应形如：*"bare argument 'px_m_calibrator' — tool names go after
   `--tool`; did you mean `--tool px_m_calibrator`?"*
   **要求：凡是能从被拒输入机械推出正确形式的情形，回执必须给出那个形式。**
3. **batch / request 的形状错误同样要给出最小可用模板**（今天 B 臂连撞两次形状错）。
4. **白名单增删逐条给理由**，且每条都要挂上面表格里对应的实测拒绝记录。
   **不得整体放开 Bash**；不得放开链接符 / 重定向 / 管道（那是隔离边界，不是可用性问题）。
   `mkdir` / `find` 是否放行由你判断并给理由——注意读者本来就只能写 `out/` 与 `requests/`，
   若探针 wrapper 自己会建目录，则 `mkdir` 无需放行，请核实后再决定。
5. **必须补测试**：每一条新放行的形状、每一条新的可操作回执，都要有锁；
   并给至少一条 neuter 证明锁真绑（改坏实现后该测试变红）。

### 验收

- 用今天 access_log 里的 6 条真实被拒输入逐条重放，每条的新回执都能让人**一步改对**。
- 隔离边界零放松：给出改造前后守卫**拒绝集合的差分**，证明只放宽了授权的那几处。

---

## 4. W4 · run 级「本轮考试范围」声明

### 背景与已核实的机制事实

- `view_manifest` 由 case 元数据**确定性派生**
  （[`view_manifest.py:54`](../../../../src/agent/execution/view_manifest.py#L54) 的声明族表 + 未分类图硬门），
  当前**全部视图皆 required**。
- 覆盖检查 `reading.view_manifest_coverage` = **INVARIANT / 恒 BLOCK**：required 视图无产物即 miss。
- 隔离工作区按 manifest 拷图（`isolation.py` 的 `_copy_case_data`）。
- **✅ 判卷分母已经是按 bindings 缩放的**——
  [`reading_typed_adapter.py:1376`](../../../../src/agent/judge/reading_typed_adapter.py#L1376)
  `derive_reading_denominator_v1` 只遍历 `bindings.bindings` 里的 plan / elevation 条目，
  **不是**从 GT 全量取。⇒ **少考的视图不会被算成漏答，这一半的机制已经存在**，你只需要在消费侧取子集。

### 目标

新增一个 **run 级**的「本轮考试范围」声明，使一次考试可以只覆盖 case 的一个视图子集，
而**不改 case 素材、不改 GT、不改任何签过名的东西**。

首个用例：sm24_anchor 声明范围 = `[1f_view, South_view]`（一张平面 + 一张立面）。

### 硬边界（全部我写死，不下放）

1. **声明位置 = run 级。** 建议 `run_config.yaml` 新增一段，或 `_run/` 下独立件——由你选并给理由。
   **绝不改 case 元数据（`testdata_prompt.json`）、绝不改 `gt/` 下任何文件。**
2. **三个身份哈希必须逐字不变**：`case_metadata_sha256` · `base_view_manifest_sha256` ·
   `gt_content_sha256`。**交付时给出改造前后这三个值相同的证据。**
3. **缺席必须是"声明过的"，不能是"没做就算了"。** 范围外的视图在 checks 里必须**显式记录**
   为「不在本轮考试范围」并带上声明来源，**不得静默跳过、不得记成 pass**。
   **范围内的视图缺产物仍然 BLOCK**（原有覆盖不变量对范围内视图完全保留）。
4. **判卷 bindings 取子集**：只消费声明范围内 `input_id` 对应的 binding。
   **不得为此修改 GT 侧的 `view_bindings.json` 源文件**——子集在消费侧取。
5. **默认行为不变**：不声明 = 全考。所有现有 run 与测试的行为逐字不变（硬约束 §1.6）。
6. **⚠️「减少题量 ≠ 中途打断」——这是本项的语义要害。**
   一次考试仍须**完整**：声明必须在**开考前**定死，**考试期间不可变更**。
   实现上要有机制保证这一点（例如声明进 run manifest 并绑哈希，考中变更即失效/报错）。
   **不得**做成「读到哪算哪」或「事后决定这轮只算这两张」——那等于事后改卷。
7. **范围声明本身不得携带任何关于答案的信息**（只能是 input_id 列表 + 理由文本；
   不得含期望数量、期望位置、难度提示等）。

### 验收

用 sm24_anchor 声明 `[1f_view, South_view]`：
1. `spawn_isolated_reader build` 出的工作区里**只有这两张图**；
2. 读者只交这两份产物即可通过覆盖检查（其余三张显式记为「不在范围」）；
3. 判卷分母只含 F1 平面 + South 立面（`window_elevation_geometry` 分母从 44 降到 South 那一面的量）；
4. 三个身份哈希与改造前逐字相同；
5. 不声明范围时，跑一遍现有 sm24 run，产物与 checks **逐字节不变**。

---

## 5. 交付要求

- **分 Slice 提交**（建议 W1 → W3 → W4，互不依赖，可独立验收），每 Slice 边界处提交 + 写执行日志。
- 执行日志落 `AI_agent/logs/reviews/execution/2026-08-01_reading_unsupervised_enablement_<seat>.md`：
  每个 Slice 记「改了什么 / 为什么 / 证据命令与输出 / 遇到的欠规格边界与你的处置」。
- **测试**：中间轮跑受影响子集（`scripts/tool_scripts/affected_tests.py` 算），
  **交付前跑一次全仓**（`-n auto`），给出绿数与零回归证据。当前基线 = **2028 绿 + 10 xfail**。
- **欠规格边界一律上报，不得自行降级为假设**（本项目连续三批的失败病根就是这个）。

## 6. 明确不在本批范围

- **「没量过就整轮打回」的确定性门**（原 W2）——**转窄设计轮**。
  理由：现有 schema 判不出「量没量」（实证：唯一那份 9/9 · 0.0 m 的产物 `provenance` 全是 `seen`、
  `dimension_refs` 全空、零像素痕迹；而 8/8 那份全是 `dimension_derived`
  ⇒ **provenance 字段与成绩完全不相关**）。判据需要先给 reading 产物加一等的可复算测量痕迹，
  那是设计工作。**且应在看到「它真的去量了」的正例之后再定判据，避免凭猜写窄。**
- 预扫接进自动编排 / 把测量下沉进代码 —— 属提速提效与工程化，用户 08-01 明确「先保证质量再说」。
- 窗全崩（三份产物 `windows_placed` 全 0/11）—— 与本批无关的真实能力缺口，单独立项。
