# Reading 质量回退、控制边界与 CV 工具进化调研报告

- **日期**：2026-08-02
- **性质**：只读取证与架构判断；除本报告外不修改生产代码、测试、skill 或历史 run
- **问题**：建筑复杂度升级与 reading 管线改动后，为什么撤走端到端主控介入会使 Haiku 质量崩坏，Sonnet 也无法复刻 07-02 的自建 CV 高质量；历史正确路径能否恢复；reading 内部是否应保留独立控制 agent；CV 工具箱应如何持续进化
- **结论强度标记**：
  - **已证实**：可由原始产物、代码路径、提交历史或单变量 A/B 直接支持
  - **强推断**：多项证据一致，但缺少完整 transcript 或单变量实验
  - **待实测**：合理设计判断，尚未用受控跑测验证

---

## 0. 用户需求、指令与最新治理口径

本节记录本轮调研的用户原始问题及讨论过程中形成的最新约束。后续设计、施工和跑测应以本节为准；若与 08-01 或更早文档中“reading 内部绝对不许更强 agent/具体反馈”的口径冲突，**本节最新裁决覆盖旧口径**。

### 0.1 原始调研需求

用户要求调查近期建筑复杂度升级、reading/建模管线多处改动后出现的异常：

1. 07-07 的 sm21 Haiku CV retest 与 sm24 Haiku CV probe 后来被查出存在端到端主控轻度介入，不是 Haiku 完全独立完成；
2. 撤走主控介入后，Haiku reading 质量完全崩坏；
3. 换 Sonnet 尝试复刻 07-02 自主搭建 CV 工具箱的高质量路径，质量也明显下降；
4. 历史既然出现过稳定全对或接近全对，就说明存在正确做法，不应把当前低水平简单归因于模型随机波动；
5. 调研重点是定位机制是否在复杂度升级和管线改造中被破坏，而不是为低分寻找合理化解释。

### 0.2 质量目标

用户要求以历史高质量路径为目标，不接受“弱模型先掉到 10%–70%，再慢慢优化”作为默认路线。正确顺序应是：

1. 找出已经存在的正确路径；
2. 区分其中由模型、工具、控制、视图证据和评分器各自贡献的部分；
3. 把可复用部分沉淀为工序、代码门和工具；
4. 再向弱模型/开源本地模型降档；
5. 每一档只有接近既有质量上限才算该档可用。

### 0.3 模型降档的根本原因

reading 后续需要转向开源方案并本地部署，因此不能长期让视觉抽取依赖昂贵的高级闭源模型。Haiku 级弱 VLM 在本项目中不是单纯的成本实验，而是本地开源 VLM 档位的代理与过渡基准。

因此最终目标仍是：

> **本地可部署的弱/开源 VLM，在产品化工具和确定性机制支撑下完成高质量 reading。**

强模型可以在开发期帮助发现方法、造工具和建立上限，但不能无记录地变成最终线上每次 reading 的隐性依赖。

### 0.4 对 reading controller 的最新许可与约束

用户明确允许把原端到端主控对 Haiku reading 的控制能力单独剥离，配置为 reading 子环节自己的控制 agent。该 controller 可以操控弱 VLM 完成整体 reading，这种形态在开发期可接受，但必须满足：

1. **与端到端编排主控彻底解耦。** 端到端主控后期要撤除并改成完整启动代码；它不能继续查看图、写反馈或控制 reading 内部轮次。
2. **controller 属于 ReadingService 内部组件。** 从外部看，reading 子系统必须独立完成输入→输出。
3. **模型档位不能特别高。** 理想可接受上限约为 DeepSeek v4Flash 水平或以下；若需要视觉能力，应寻找同档轻量多模态模型或设计局部视觉询问机制。
4. **必须快。** reading 本身已慢，controller 不应增加超长推理；应采用短上下文、结构化输出、有限调用和局部返工。
5. **它是权衡方案，不是默认永久架构。** 最理想仍是 Haiku/本地 VLM 在工具和代码门支撑下自主完成；开发期若“一撤就崩”，可以先保留 controller，后续再代码化、降档或撤除。
6. **成绩必须如实归因。** 配置了 controller 的结果属于 controlled reading，不能记为弱 VLM 独立成绩。

这一最新许可意味着：早先审计把“环节内部任何更强 agent 反馈”统一判为违规的规则，不再适合作为当前设计前提。现在禁止的是**端到端主控越界、隐性介入和无 provenance 的成绩归因**；正式声明、隔离运行、可替换的 reading controller 是允许评估和采用的产品组件。

### 0.5 对 CV 工具箱的最新要求

用户明确反对把 CV 工具箱做死。当前从一次优秀 Sonnet reading 总结出的 crop、projection、calibration、connected-components 等工具，可能足够覆盖现阶段建筑复杂度，但不代表能覆盖更复杂建筑、图纸风格或未来能力档。

工具箱应当是持续增量进化的系统：

1. 每次跑测都允许暴露现有工具的能力边界；
2. 当 Haiku/目标 VLM 使用冻结工具仍无法做好，或发现更优方法时，开发期允许相对更聪明的 reading/CV agent 现场编写新工具或新 recipe；
3. 新方法若在本次测试中确实有效，应在测试结束后整理、泛化、验证，再加入或整合进正式工具箱；
4. 固定工具路径与现场发明路径必须同时保留，前者负责稳定效率，后者负责能力增长；
5. 权限可以比当前 hard isolation 更大，只要隔离能证明不访问 GT、judge、历史答案和其他 run；
6. 项目目标是把 reading 做好，不应为了形式上的“只能使用固定 wrapper”而禁止有效算法。

因此隔离的设计原则被用户校准为：

> **严格限制可见信息和写出边界，不限制在合法输入上采用何种计算方法。**

### 0.6 本次交付指令

用户要求把本轮完整调研整理为一份 durable report，落入 `AI_agent/logs/reviews/verdict/`，并包含：

- 用户问题与上述指令；
- 历史跑测的监督/看图/返工事实；
- 当前回退的机制根因和证据强弱；
- Haiku 无端到端主控恢复质量的判断；
- 独立 reading controller 的职责、模型档和延迟约束；
- 固定工具箱与现场造工具并存的进化路径；
- 后续验证顺序与不可再沿用的错误结论。

本次只写调研报告，不实施生产修复或新增跑测。

---

## 1. 执行结论

用户关于“主要不是能力波动，而是机制被改坏”的判断基本成立。当前 reading 下滑不是单点故障，而是以下机制叠加：

1. **撤掉了内容级 reviewer，却没有补上内容完成度的机器责任人。** 当前 gate 能确认 JSON 写完，不能确认图读完；CV 证据、自评和 access log 都有信号，但没有可靠消费者。
2. **缩减视图范围直接损害识图。** 同一 Sonnet、同一文档、同一 isolation/scorer 的 A/B 已证明 full scope 显著优于 scoped，不是简单的评分分母变化。
3. **hard isolation 封掉了 07-02 Sonnet 的通用 CV 编程路径。** 当前固定工具仍可取得较好墙体结果，但无法允许模型针对新图纸发明新掩膜、算法或组合。
4. **typed scorer 会把合法的 `mirrored="unknown"` 当成与 trusted `false` 冲突，整张立面的窗全部丢弃。** 最新 Sonnet 的平面窗几何实际为 22/22 PASS，最终存在性却被计为 0/11；表观崩坏被评分器显著放大。
5. **validator/profile、dimensioned metadata、CV evidence 归档和自动 render 存在断线。** 这些问题使严格配置未真实进入检查、尺寸门永久 N/A、视觉证据无法成为验收输入。

历史“稳定全对”并非一个同质基线：

- 07-02 Sonnet 是一次性独立完成，但拥有 full-view、prompt-level 隔离和通用 PIL/NumPy/SciPy 编程能力；case 与评分尺也较旧。
- 07-07 Haiku 的 sm21 和 sm24 高质量产物都经过 reading 内部的针对性 pilot review 与返工，不能记为 Haiku 独立成绩。
- 07-08 GPT-5.4-mini CV cross-test 最接近弱模型自主成功：主控审过 pilot 并放行，但未发现具体纠错回灌，最终只有 attempt 001；它仍不是严格零主控依赖。

因此正确目标不是简单恢复端到端主控，而是：

> **把 reading 变成边界独立的子系统。端到端层只负责启动和接收结果；reading 内部在开发期可以配置低成本控制 agent 与 CV invention lab，并逐步把重复控制动作沉淀为确定性代码。**

---

## 2. 历史跑测重新定性

### 2.1 汇总表

| run | reader 与环境 | reading 内部监督 | 结果及正确归因 |
|---|---|---|---|
| `run_2026-07-02_sonnet_flow_e2e` | Sonnet 5；full views；prompt-level isolation；可运行临时 PIL/NumPy/SciPy | pilot 仅批准继续，未见针对性打回 | 近乎满分；证明强模型自发经典 CV 路径可行 |
| `run_2026-07-07_haiku_cv_retest` | Haiku 4.5；固定 CV 工具；工具使用被 per-run directive 强制 | pilot r1 被指出错锚、候选未核验、字段为空；r2 后放批量 | 9/9 墙、7/7 平面窗、15/15 立面窗；是“Haiku + 工具 + 控制返工”的成绩 |
| `run_2026-07-07_haiku_cv_probe` | Haiku 4.5；sm24；无 GT；prompt-level isolation | 内容/纪律返工一轮，schema 返工一轮；人工肉检 | 5/5 图收口；明确是 reading controller-assisted |
| `run_2026-07-08_gpt54mini_cv_retest` | GPT-5.4-mini；固化工具箱；clean-room staging | 保留 pilot 门，Opus 主控审后放批量；未见纠错回灌 | 墙 9/9、平面窗 6/7、立面窗 15/15；弱模型自主使用固化工具的最强证据，但仍有 approval 依赖 |
| `run_2026-06-23_gpt54mini_reading` | GPT-5.4-mini；无新 CV 工具箱 | judge 看图/GT 后三次重抽；后两次加入通用 anti-merge/逐隔墙纪律 | attempt 3 恢复；controller-assisted，不是纯自主 |
| 08-01 Haiku unsupervised / W5 | Haiku；硬隔离；零 directive/feedback | 无 | 能写完文件，但墙 9.0%/24.8%、窗 0；证明“环节能结束”不等于“内容完成” |
| 08-02 Sonnet full unsupervised | Sonnet；full views；硬隔离；固定工具 | 无 | 墙 92.1%、外边界 100%、平面窗 22/22；真实能力接近高水平，窗总分被 frame/scorer 契约误杀 |

### 2.2 07-02 Sonnet 做对了什么

forensics 记录显示其 reading 共 112 次工具调用（60 Bash / 45 Read / 7 Write），主要不是肉眼估坐标，而是现场搭建经典 CV：

1. PIL crop/zoom；
2. `R≈G≈B && 60<v<230` 灰度掩膜；
3. NumPy 行列投影定位墙轴；
4. 总尺寸锚做 px/m 标定；
5. SciPy connected components 框立面窗。

第一张图约 30 分钟用于试错和发明配方，后五张复用后显著加速。其核心能力不只是四个算子，而是：

> 观察中间结果 → 修改阈值/裁区/组合 → 再运行 → 形成适合当前图纸的配方。

### 2.3 07-07 Haiku 的控制介入

sm21 pilot r1 已调用 profiler、CC、calibrator 并写 sidecar，但仍出现：

- 用墙端点而非尺寸 tick 标定；
- Y 残差 0.90m，外框 14.52×8.90m；
- 19 道内墙候选未经逐条 crop 核验；
- windows、dimensions、OCR、provenance 为空。

主控按上述失败类别反馈后，r2 才得到 92.6945 px/m、毫米级残差、44 个候选逐条拒收留痕、7 扇窗双通道验证和 32 条尺寸。这里主控没有直接给最终墙坐标，但承担了弱模型的外置执行控制：定位失败类别、迫使追加工作预算、拒绝内容未完成的交卷。

sm24 更明确：r1 被指出标定粗、只描主要墙、窗漏描、换算矛盾；r2 内容达标后又因 `dimensions[].anchor` 自创 schema 被打回；第三轮才收口。sm24 当时没有 GT，provenance 明载 `human eyeball acceptance`，因此内容级判定不可能只来自 schema validator。

### 2.4 主控是否直接看图：证据边界

07-07 的完整开工 prompt、pilot r1 原产物和逐轮 transcript 未保存在 run 内，无法逐动作证明“Fable 看了哪一张原图、用户看了哪一张 render”。但可以区分：

- 标定残差、外框与 testdata 不符、字段为空、anchor schema 错误，可由 JSON/sidecar 发现；
- 19 个候选中哪些是假墙、是否只描了主要墙、哪些窗/门漏掉、L 形走廊和无标注 H6 墙是否正确，需要查看源图、crop 或 overlay，或通过另一个 VLM 做视觉核验。

结合审计中“gate 分辨力为 0，主控必须亲自看图”的记录，**主控进行了视觉核验是强推断；具体视觉动作分工属于 unknown。**

07-08 GPT-5.4-mini 则不同：provenance 明载 pilot 由 orchestrator 审核，但最终只有 attempt 001，`judge.json` 明载 out-of-band commentary 未注入 prompt，盘上也无 feedback/reread ladder。因此可判：

- 有视觉/产物 review 与“继续”控制位；
- 没有证据表明通过针对性纠错把失败结果救回；
- 最终高质量主要支持“固化工具箱能被另一弱模型自主采用”，但还不能记为严格零控制基线。

---

## 3. 当前质量回退的机制根因

### 3.1 P0 · 撤控制未补内容闭环（已证实）

08-01 删除了 `Stop and wait for review`，使 Haiku 能从输入走到输出；但 stage completion 仍由文件/schema 完成驱动，而非内容完成驱动。

关键证据：

- d1 明确写 `all_visible_strokes_captured=false`、`all_dimensions_transcribed=false`，仍以 0 block accepted；
- d2 四个 self-check 全填 `true`，实际墙仅 24.8%，说明不能把自报 bool 直接升级为真值；
- 8/8 与 1/8 历史产物跑最严格 gate 均为 0 blocker；
- `cv_evidence`、candidate id、prescan coverage 没有进入 validator 的质量判定；
- `access_log.jsonl` 记录工作量但没有消费者；
- hard-isolation merge 不把完整 `out/**/cv_evidence` 归档为 attempt 的一等证据。

这不是 Haiku “不听话”：它甚至诚实报告未做完。问题是系统没有内容完成的 owner。

### 3.2 P0 · typed scoring frame 契约误杀窗（已证实）

08-02 full Sonnet 的原始评分显示：

- `window_plan_geometry`：22/22 PASS；
- 最终 `windows_placed`：0/11；
- 所有 elevation component 以 `elevation_local_x_sense_disagreement` 变为 N/A 且保留为 miss。

产品输出四个 facade 均为：

```json
{"local_x_positive":"image_left_to_right","mirrored":"unknown"}
```

trusted bindings 为相同 local-x 方向、`mirrored:false`。reading guide 明确允许 `mirrored: true | false | unknown`，typed adapter 却把 `unknown` 与 `false` 当成不相等，整张立面组件直接拒绝，数值窗几何没有被比较。

因此 08-02 报告中“plan 与 elevation 互相矛盾”的描述不够精确：至少在当前执行路径里，elevation 数值并未得到机会证明矛盾。该契约会奖励自信猜 `false`，惩罚诚实的 `unknown`。

### 3.3 P0 · scope reduction 有害（单变量 A/B 已证实）

同一 Sonnet、同一 skill、同一零监督/硬隔离/scorer，仅改变可见视图：

| 输入 | 墙长命中 | 外边界 | 多余墙长 |
|---|---:|---:|---:|
| scoped | 70.9% | 48.8% | 46.01m |
| full | 92.1% | 100% | 6.77m |

复杂建筑中，其他楼层和立面提供比例、轴线、窗墙关系和全局消歧。减卷移除的是弱模型需要的冗余证据，不只是减少 token。

### 3.4 P1 · hard isolation 封掉历史成功路径（机制差异已证实，因果份额待 A/B）

07-08 后的 hard isolation 允许固定 CV wrapper，拒绝 `python -c`、临时脚本、管道和通用搜索。08-02 full Sonnet access log 有 7 次 denied，包括检查 JSON 的 Python 和 grep/find 组合。

所以当前要求 Sonnet “复刻 07-02 手搓 CV”在执行能力上自相矛盾：07-02 的通用 PIL/NumPy/SciPy 路径已被环境禁止。

但不能把当前墙体剩余 7.9% 缺失全部归因于 guard：最新 Sonnet 使用固定工具仍取得 92.1% 墙长和完整外边界。hard isolation 是明确的能力封口和摩擦放大器，其独立因果份额仍需同模型 A/B。

### 3.5 P1 · 固定工具箱覆盖算子，不覆盖自适应能力（已证实）

当前工具与 07-02 算法映射基本完整：

| 07-02 临时实现 | 当前工具 |
|---|---|
| crop / zoom | `crop_zoom` |
| 灰度掩膜 + 行列投影 | `wall_line_profiler` / `prescan-*` |
| px↔m 标定 | `px_m_calibrator` |
| connected components | `window_cc_detector` |
| 层线投影 | `storey_line_profiler` |
| 决策留痕 | `overlay_logger` |

因此“基础算法没有固化”不是主因。缺口在更高层：

- 当前只有 `clean_vector_v1` 固定 recipe；
- 无通用数组运算、动态掩膜、任意 morphology、Hough/LSD 或新算法组合；
- 工具输出是机械候选，最终语义筛选和全图查漏仍由弱 VLM 承担；
- 没有 candidate coverage → final strokes → rerender residual 的闭环；
- 工具失败一次后，弱模型常直接放弃路径。

当前工具箱更准确的定义是：**固化的 sm21 成功配方，而不是替代通用 CV 编程能力的完整工作台。**

### 3.6 P1 · gate/profile/metadata/可视化断线（已证实，单项质量影响不同）

1. hard-isolation merge 调 `check_reading_stage` 时未传入配置中的 `capability_profile` / `run_profile`，近期 hard-isolated runs 的 `checks.json` 实际记录为默认 `rectangular + exploratory`。
2. sm24 `_run/view_manifest.json` 把实际带完整尺寸链的视图全部标为 `dimensioned:false`，十项尺寸相关检查直接 N/A。
3. 自动 render 仍从根目录 glob `0_reading/*_view.json`，hard merge 的聚合产物却在 `attempts/001/output.json`；08-02 后见到的 PNG 更像诊断性补产物，标准自动路径仍断。
4. CV evidence sidecars 当前不是 attempts/report 的稳定一等证据。

profile 断线本身不能解释墙窗低分：当前 `capability_profile` 多数只影响报告和有限分支，历史严格 recheck 也表现为零分辨力。它的重要性是证明“配置宣称 regression/orthogonal_polygon”与真实 gate 执行不一致，削弱审计可信度。

### 3.7 评分与 case 不可直接纵向等同（已证实）

- sm21 与 sm24 的建筑复杂度不同；
- 历史 sm21 使用旧 count-based/legacy scorer，当前 sm24 使用 length-based typed fusion；
- 当前 GT/schema 版本不同；
- 07-07 Haiku 有返工，08-01/02 无返工；
- prompt-level isolation、hard isolation、视图 scope、工具入口均发生变化。

所以不能写成简单的“100% → 9%”模型退化曲线。能下的结论是：在当前机制下无监督 Haiku 客观低分；历史受控路径证明它在外置执行控制下能做出高质量产物。

---

## 4. 因果链

```text
建筑复杂度升级
    + full-view 被缩减
    + 通用 CV 编程被 hard isolation 封掉
                         ↓
              reader 获得的证据与适配能力变弱
                         ↓
        pilot reviewer / 针对性返工被一次性撤走
                         ↓
     结构 gate 接受“JSON 写完、图没读完”的产物
                         ↓
   typed scorer 再丢弃 mirrored=unknown 的正确窗观测
                         ↓
          最终分数低于真实视觉/测量能力
```

这条链中：scope A/B、scorer frame 拒绝、gate 零分辨力、hard-isolation 能力差异均有直接证据；各因素对 Haiku/墙体得分的精确占比尚未隔离。

---

## 5. 能否撤掉端到端主控并恢复 Haiku

### 5.1 判断

可以撤掉端到端主控的 reading 生产介入，但不应把“无端到端主控”误写成“reading 内部只能单 agent 一次生成”。

分两种目标：

- **Haiku + 当前弱 gate + 单次生成 + 无任何内部控制**：现有实测表明不可稳定达到历史水平。
- **Haiku + 确定性检查 + reading 内部低成本 controller + 有界局部返工**：对 sm21 clean-vector 类恢复历史水平具有较高可行性；对更复杂建筑仍需跑测验证。

主控提示作用大，不是因为它提供了答案，而是它相当于 Haiku 的外置执行功能：

1. 把“哪里可能失败”从全图搜索压缩为局部任务；
2. 强迫模型追加一轮时间/工具预算；
3. 不接受内容不完整但 schema 完整的交卷；
4. 在必要时查看 source/crop/overlay 做视觉仲裁。

这些职责可以从端到端主控中单独剥离，成为正式 reading subsystem 的内部实现。

### 5.2 推荐边界

```text
Deterministic E2E Launcher
  │
  └── ReadingService.run(case_bundle, reading_profile)
        ├── deterministic prescan / tool runner / evidence gates
        ├── Reading Controller（Flash 级，快速、短上下文）
        │     ├── 指挥目标弱 VLM（Haiku / 本地开源 VLM）
        │     ├── 查看结构化失败包与少量 flagged crops
        │     └── 最多一轮局部返工
        ├── CV Lab（开发期按需造工具）
        └── reading output + evidence + provenance
```

端到端层只能：

- 创建 reading job；
- 传入冻结的 case bundle / profile；
- 等待完成；
- 接收 `status + output + evidence manifest`。

端到端层不能：

- 写自由文本 directive/feedback；
- 查看图后指导 worker；
- 选择 CV 参数或返工区域；
- 操作 reading 内部会话；
- 接触 GT 后把结论送回同一 reading run。

这样端到端主控后期可以完整替换为启动代码，而 reading 内部是否仍配置 controller 不影响外部管线契约。

### 5.3 Reading Controller 的档位与延迟设计

controller 应是执行控制器，不是第二个完整 reader。推荐正常路径最多两次短调用：

1. 读取 manifest + prescan 摘要，输出结构化任务计划；
2. worker 完成后，仅当确定性 audit 失败时，读取失败摘要和少量 flagged crops，输出一次局部修复计划。

约束建议：

- DeepSeek v4Flash 水平或更低；
- thinking disabled；
- 结构化 JSON 输出；
- 短 token cap，不重复加载完整 1200 行 skill；
- 最多一次计划 + 一次修复；
- 不重新抽取整栋建筑；
- 不直接编写最终坐标，最终 stroke 仍须来自 worker + 工具证据。

如果控制模型无视觉能力，它可以检查数字、证据链和完成度，但不能独立判断候选是否为真实墙。可选路径：

1. 使用同档轻量多模态 controller，仅看 flagged regions；
2. controller 向 Haiku 发局部二选一/对比式视觉询问，再检查回答与证据；
3. 优先把高频视觉判定继续下沉为确定性算法。

第一种独立性最好，第二种成本低但存在同模型相关错误。具体档位应由 A/B 决定，而不是预设必须使用高级模型。

---

## 6. CV 工具箱应成为可进化系统

### 6.1 正确隔离边界：限制数据，不限制解题方法

当前 hard isolation 主要按命令形态限制能力；对 reading/CV 研发更合适的是信息流隔离。

**允许：**

- 读取当前 run 的 `case_data`、testdata、公开 skill/工具代码；
- 在受限环境内编写并运行任意 PIL/NumPy/SciPy/OpenCV 程序；
- crop、掩膜、投影、morphology、connected components、Hough/LSD、参数搜索；
- 写入当前 run 的 scratch、experimental tool、overlay 和 `cv_evidence`；
- 留存所有临时代码、命令、输入输出 hash。

**禁止：**

- GT、baseline、judge score、review verdict；
- 其他 run、历史 attempts 和答案派生产物；
- 修改生产源码或隔离区外文件；
- 任意网络访问（模型推理端点除外，且不允许数据外传到其他服务）；
- 超过 CPU/RAM/墙钟/输出大小预算。

目标是：**方法尽量开放，信息严格封闭。** 项目要防的是漏题和污染，不是模型使用某种算法。

### 6.2 两类 agent 不应混为一个

#### Reading Controller

- Flash 级常规组件；
- 每次 run 可用；
- 调度现有工具、检查完成度、组织局部返工；
- 目标是快、便宜、以后可代码化或本地化。

#### CV Inventor

- 开发期按需升级组件；
- 仅在冻结工具箱反复失败或 capability profile 不支持时触发；
- 可以使用更聪明的模型和通用 CV sandbox；
- 负责现场发明、验证和留档新算法；
- 不应成为最终线上每次 reading 的强模型依赖。

这使开发期可以保留 07-02 式创新能力，同时避免所有生产 reading 都承担强模型长推理成本。

### 6.3 三层工具注册表

| 层 | 内容 | 生命周期 |
|---|---|---|
| Core | 已验证的 crop/projection/calibration/CC 等稳定工具 | 随产品发布 |
| Recipes | 不同图纸风格、能力档和参数组合 | 版本化持续迭代 |
| Experimental | 当前 run 现场编写的新工具/recipe | 仅隔离区内，待晋升 |

实验工具晋升条件：

1. 当前 run 的 reading 质量或证据质量确有改善；
2. 接口不硬编码当前 case 的坐标/名字；
3. 不读禁区，资源与写边界可验证；
4. 在未参与发明的 holdout case 上复验；
5. 有确定性测试、适用范围和失败模式声明；
6. 代码审查后进入 Core 或 Recipes。

否则只能作为 run-local experiment 保存，不能把针对单图的脚本误当通用能力。

---

## 7. 成绩与 provenance 治理

后续每次 run 至少记录：

```yaml
reading_mode:
  worker_model: haiku | local_vlm | sonnet
  controller_model: deepseek-v4-flash | none
  controller_visual_access: flagged_crops | none
  repair_rounds: 0
  cv_inventor_model: sonnet | none
  toolbox_version: ...
  experimental_tools: []
  isolation_profile: ...
```

成绩必须分账：

- **autonomous**：目标 VLM + 冻结工具箱，无 controller；
- **controlled**：目标 VLM + reading controller；
- **tool-invention**：允许开发期 CV inventor 现场造工具。

controlled/tool-invention 的产物完全可以作为真实工程成功，但不能再归因成“Haiku 独立满分”。同时保留 autonomous lane，才能知道离最终本地部署目标还有多远。

---

## 8. 推荐验证顺序

### V0 · 先修正测量口径，不重跑模型

对现有 08-02 Sonnet full 产物做离线 scorer 对照：

1. 保持原规则；
2. `mirrored=unknown` 不作显式冲突，或使用 trusted binding 做投影但记录 unresolved；
3. 比较 elevation/window 总分变化。

目的：先量出“评分器误杀”份额，避免拿错误分数评价 reader。

### V1 · 隔离 controller 的真实贡献

同一 sm24、full-view、同一冻结工具箱，至少两抽，建议四臂：

| 臂 | 配置 | 回答的问题 |
|---|---|---|
| A | Haiku autonomous | 当前真实地板 |
| B | Haiku + deterministic audit only | 代码门能承接多少控制职责 |
| C | Haiku + Flash controller | 低成本控制是否足够 |
| D | Haiku + 强 controller（dev upper bound） | controller 架构的可达上限 |

报告：墙长/窗、额外墙长、boundary、证据覆盖、repair 次数、总墙钟、controller 增量墙钟、token、工具失败恢复率。若 C 接近 D 且延迟可接受，说明 Flash 档成立；若 D 也差，问题主要在工具/任务分解，不应继续加 controller 推理。

可在 C 内进一步区分 text-only 与 flagged-crop visual controller，但不应一次引入过多变量。

### V2 · 隔离通用 CV 能力的贡献

同一 Sonnet、sm24 full-view、同一 prompt/预算，至少两抽：

- 固定 wrapper hard isolation；
- 信息流隔离的通用 CV sandbox。

目的：量出“07-02 自适应配方能力被封”对墙体/窗/工具失败恢复的独立影响。

### V3 · 工具晋升实验

当 CV Inventor 产生新工具时：

1. 当前 case 内验证改善；
2. 冻结工具与参数；
3. 在 holdout case 上盲测；
4. 再决定是否晋升。

不得用同一 case 的 GT 分数反复调参后直接宣称泛化。

---

## 9. 不应再使用的结论

1. **“07-07 Haiku 完全独立满分”**：错误；两案均有针对性返工。
2. **“当前 Sonnet 窗识别是 0/11 水平”**：错误；平面窗几何 22/22，当前 0/11 主要来自 frame adapter 拒绝。
3. **“工具箱已经固化，所以 Sonnet 与 07-02 计算能力等价”**：错误；算子覆盖不等于自适应编程能力。
4. **“缩小视图能帮助弱模型”**：已被同模型 A/B 反证，至少对当前 sm24 reading 不成立。
5. **“gate 通过代表 reading 内容合格”**：错误；当前 gate 对历史 8/8 与 1/8 阻断分辨力为 0。
6. **“只要把 self-check false 变成 blocker 就能解决”**：错误；d2 全 true 仍低分。
7. **“撤端到端主控就必须撤掉 reading 内所有 controller”**：架构上不成立；reading controller 可以成为正式、独立、可替换的子系统组件。

---

## 10. 最终建议

短期应同时推进三条相互独立的线：

1. **先校正 scorer/frame、scope 和 gate/evidence 断线**，恢复可信测量；
2. **把 reading 控制职责从端到端主控剥离成独立 ReadingService**，用 Flash 级短调用验证是否能恢复 Haiku；
3. **把 hard isolation 改造成信息流隔离的 CV Lab**，保留固定工具与现场发明两条路径。

长期目标仍可保持：本地开源 VLM + 确定性工具箱，controller 降档或撤除。开发期保留 controller/CV inventor 不是放弃该目标，而是把高质量路径显式化、记录化，再将反复出现的控制动作和新算法逐步编译进产品。

---

## 11. 主要证据索引

### 历史成功路径与控制介入

- [07-07 Haiku CV 实验记录](../../experiments/2026-07-07_haiku_cv_retest/README.md)
- [07-08 GPT-5.4-mini 交叉测试交接单](../../experiments/2026-07-07_haiku_cv_retest/HANDOFF_gpt54mini_crosstest.md)
- [07-02 Sonnet reading summary](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/reading_summary.md)
- [07-08 GPT-5.4-mini run config](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/run_config.yaml)
- [07-08 GPT-5.4-mini judge](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/0_reading/attempts/001/judge.json)
- [07-07 sm24 Haiku provenance](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/llm.yaml)
- [06-23 GPT-5.4-mini reread ladder](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading/0_reading/reread_ladder.md)

### 无监督回退、scope A/B 与主控审计

- [主控生产接缝审计](../../experiments/2026-08-01_controller_in_production_audit/README.md)
- [无监督 reading baseline](../../experiments/2026-08-01_unsupervised_reading_baseline/README.md)
- [W5 scoped 双抽](../../experiments/2026-08-01_w5_scoped_unsupervised_reading/README.md)
- [scope harms reading A/B](../../experiments/2026-08-02_scope_harms_reading/README.md)
- [compliance gap 独立调查](2026-08-01_compliance_gap_investigation_sol.md)
- [reading completeness 设计稿](2026-08-01_reading_completeness_design_fable.md)

### 代码与契约

- [CV 工具箱说明](../../../../skills/intake_pipeline/0_reading/cv_toolbox.md)
- [reading guide frame 契约](../../../../skills/intake_pipeline/0_reading/guide.md)
- [CV tools 实现](../../../../src/agent/reading/cv_toolbox/tools.py)
- [prescan recipes](../../../../src/agent/reading/cv_toolbox/recipes.py)
- [typed reading adapter](../../../../src/agent/judge/reading_typed_adapter.py)
- [hard isolation merge](../../../../src/agent/execution/isolation.py)
- [reading validator](../../../../src/validator/checks/reading.py)
- [sm24 full Sonnet output](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-08-02_sonnet_full_unsup/0_reading/attempts/001/output.json)
- [sm24 full Sonnet score](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-08-02_sonnet_full_unsup/0_reading/attempts/001/score_vs_gt.json)
- [sm24 view manifest](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-08-02_sonnet_full_unsup/_run/view_manifest.json)

---

_本报告只完成调研整理，没有实施修复、重算评分或新增跑测。_
