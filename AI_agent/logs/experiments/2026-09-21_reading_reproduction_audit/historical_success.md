# 历史 100 分 reading 与 09-16 复现失败的只读审计

本报告只比较仓库原件，没有运行模型/API，没有读取凭据，也没有改动旧产物或生产代码。结论先说：**09-16 已恢复了相当一部分“配方文件和口头要求”，但没有恢复历史成功时真正发生的高密度量测、逐候选裁图判别和完整转录动作。** 当前最可证、也最容易复核的失败环节是同名工具被提供后，模型实际只执行了很小一部分工序；此外，历史原 prompt、Agent-tool 宿主和模型服务端状态缺失，使 09-16 不能算逐条件精确复现。**这是定位到执行差异，尚未解释为何模型不执行，也没有通过受控试验证明增加动作就足以恢复满分。** 下文“原因排序”是下一轮验证的优先次序，不是已隔离的因果结论。

## 一、先分清三个“成功”

1. **07-02 sm21 Sonnet 是有机器分数原件的 100 分 reading。** 原 scorer 记录墙 `9/9`、平面窗 `7/7`、立面窗 `15/15`，墙最大偏移 `0.0m`；采用容差为墙 `0.30m`、平面窗中心 `0.40m`、立面沿墙/宽 `0.40m`、窗台/窗顶 `0.30m`。证据：`case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/attempts/001/score_vs_gt.json:2707-2768,2943-2945`。这只是当时 reading 判卷范围的满分，不等于今天的完整源 BIM、门洞连接或稳定无人介入能力。
2. **07-07 sm21 Haiku 也是同一旧判卷下的 100 分 reading。** 原 scorer 同样是 `9/9 + 7/7 + 15/15`，见 `run_2026-07-07_haiku_cv_retest/.../score_vs_gt.json:2781,2840,3017`；它是“固化 CV 工具箱 + 明确要求先量后画 + pilot 返工”形式最有把握的量化成功实例。
3. **07-07 sm24 Haiku 是有效的历史成功，但没有 GT，不能叫机器 100 分。** 当时是用户人工检查认可；run 配置明确 `judge: off` 且写明 `sm24 has no gt`，见 `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/run_config.yaml:3-11,23-26`。它仍然很有价值：五图完整、量测链和候选台账可审计、L 形走廊等非矩形图意被正确保留；只是评价口径必须写成“人工认可的好 reading”。

## 二、最适合作为严格重跑基线的一次：07-07 sm21 Haiku

选择它而不是 07-02 Sonnet，原因是它既有独立 GT 分数，又是后来固化方法的直接实例；07-02 是方法来源，完整原 transcript 目前不在 run 中。准确条件如下。

| 条件 | 历史原件能确认的内容 |
|---|---|
| 输入 | `sm21_anchor/case_data` 的 **6 张原图**：1F、2F、东南西北四立面，加原 `testdata_prompt.json`。reader 只拿 case 图片、声明、0_reading skill 和格式示例，禁 GT、旧 attempts、judge 产物和其他 run。证据：`2026-07-07_haiku_cv_retest/README.md:13-15`、`llm.yaml:18-24`。 |
| reader / 会话 | `claude-haiku-4-5-20251001`，由当时 Agent tool 以 `model="haiku"` 冷启动子代理；pilot 被打回后在原会话继续，期间订阅额度中断一次，恢复段只补报告。证据：`llm.yaml:18-25`、实验 README `:24-26`。 |
| 主控 | Claude Fable 5；负责看盘上 pilot、给流程性返工、再放批量。GT scorer 是权威分数，Fable 的 judge 只做定性/路由。证据：`llm.yaml:29-32`、实验 README `:16`。 |
| 代码版本 | 完整树 `723b0f98ed37285b66cb3d1d30caa8e42eb01a74`，提交时间 2026-07-06 11:39 UTC。run provenance 记录 skill/hash 和 reading 源码 hash，见 `llm.yaml:33-37`；提交为 `7.06_MgmtDocsSyncFacadeFrameWired`。 |
| 工具 | `crop_zoom`、`wall_line_profiler`、`px_m_calibrator`、`window_cc_detector`、`storey_line_profiler`、`overlay_logger`，入口 `scripts/tool_scripts/cv_probe.py`。工具定义见该提交的 `skills/intake_pipeline/0_reading/cv_toolbox.md:5-12`。 |
| prompt 可恢复部分 | 完整原始 spawn prompt **未保存**。可精确恢复的是 `session_kickoff.md` 和四份规则/示例，以及 provenance 保存的逐 run 指令：`cv_toolbox.md is REQUIRED`，墙线、窗框、层线必须先用 `cv_probe.py` 量再画。证据：`llm.yaml:21-28`；旧 kickoff 的 pilot/停等流程在 `723b0f9:skills/.../session_kickoff.md:60-67`。因此任何“逐字复原 prompt”的说法都不成立。 |
| 逐图组织 | 先只做 1F pilot；主控复核后才做 2F 和四立面。每张图独立标定，立面用层线 profiler 和局部窗 CC。原记录：README `:24-26`。 |
| 实际动作 | 1F r2：从尺寸链 tick 标定到 `92.6945 px/m`，筛 48 个墙候选、拒收 44 个，治愈 8 个有门符号的洞口，7 个窗用墙带 CC 与尺寸链双证据，完整转录 32 条尺寸。原 summary `0_reading/reading_summary.md:7-35`。全六图留下 **92 份 JSON CV sidecar**；其中 1F 为 17 crop、5 标定、2 墙 profiler、5 窗检测、4 个 overlay 台账（按原目录文件计数）。 |
| 主控返工 | r1 虽调用工具，但把墙端/文字行当标定 tick、外框量成 14.52×8.90m，未经 crop 判别就画 19 道内墙，且窗/尺寸/来源为空。主控只给流程合规反馈，不给 GT 坐标；r2 改用尺寸 tick、逐候选处置并补齐窗/尺寸后放批量。证据：实验 README `:24-26,46-48`。 |
| 输出要求 | 每张原图一个历史 schema 的 `*_view.json`，附 CV sidecar、render 和最终 `reading_summary.md`；reading 只画语义笔画和尺寸，不做空间拓扑/world placement。旧 kickoff `:3-6,42-67`。 |
| 评价 | GT 在 reader 隔离区外，由确定性 scorer 按上述容差比较；五项 `walls_complete/windows_placed/boundary_complete/no_oversplit/elevation_windows_placed` 全 pass。配置见 `run_config.yaml:20-23,51-52`，结果见实验 README `:28-39`。 |

如果下一次只允许选一个历史组合来检验“旧形式今天还能不能成功”，这组最干净。必须把 **完整 723b0f9 worktree、旧 Agent-tool 型会话（若今天仍可用）、1F pilot 同会话返工、六图全量 sidecar、外置 scorer** 作为一个组合；不能把 09-16 的 sm24 pilot 结果直接与 sm21 的 GT 100 分当同口径对照。

## 三、07-02 Sonnet：方法来源及可恢复边界

07-02 用 `claude-sonnet-5`，由 Agent tool 的 `model="sonnet"` 别名解析，主控是 Opus 4.8，干净树为 `1595981`；输入同样只含 sm21 图片、声明和 reading skill。证据：`run_2026-07-02_sonnet_flow_e2e/llm.yaml:2-24`。它没有现成工具箱，但历史 transcript 的专项取证记录 Sonnet 自己写了 PIL/NumPy/SciPy 流程：裁图、灰度掩膜、行列投影、总尺寸反推比例、连通域框窗；共 112 次工具调用（60 Bash/45 Read/7 Write），第一张约 30 分钟、后图复用。证据：`AI_agent/archive/.../improvement_methodology.md:49-72`。

这里的限制必须保留：这份 transcript 的**结论性取证文档存在**，但完整 transcript 本体未在 07-02 run 目录找到；所以能确认技法、调用数和时间线来自当时专项记录，不能逐条重放每个命令。完整原 spawn prompt同样缺失。其 scorer 和 reading JSON/render 都还在，可恢复结果与评价；不能恢复当时模型服务端权重、宿主视觉预处理、每轮对话或临时脚本原文。

## 四、07-07 sm24 与 09-16 实际复现的可证差异

### 已证实、最可能直接解释失败的差异

1. **实际完成的观察密度相差一个量级（首要原因，已证实）。** 历史 sm24 1F 用 11 次 crop、1 次标定、2 次墙 profiler、4 次窗检测、1 份 52 候选处置台账；最后是 14 墙、11 窗、51 尺寸，见历史 summary `:19-25` 及原 sidecar 目录。09-16 三轮累计快照只有 3 次 crop、2 次标定、2 次墙 profiler、1 次窗检测，始终没有 overlay 候选台账；输出依次是 `31墙/0窗/7尺寸`、`11/13/7`、`7/0/7`。证据：`2026-09-16_reading_method_reproduction/README.md:7-20`、`execution_audit.json` 的三轮 `cv_tools_in_snapshot/views`。这说明“提示里要求了”没有转成“动作上执行了”。
2. **09-16 没有完整转录图纸自己的尺寸证据（首要原因的另一面，已证实）。** 历史 51 条尺寸、11 条链闭合；09-16 三轮都只有 7 条尺寸。历史候选先量再裁再判，09-16 则把 profiler 峰直接扩成规则网格，第二轮又混用放大裁图坐标与原图坐标，第三轮虽把标定 RMSE 修到 1.55px，仍保留三道错误整长墙并把窗全删。证据：历史 `reading_summary.md:19-25`，复现 README `:9-11`，当前主控反馈 `pilot_02_feedback.md:7-34`、`pilot_03_feedback.md:3-30`。
3. **09-16 只验证到“旧 loader/gate 能过”，而历史成功还经过主控逐图原像素复核和最终完整五图检查（已证实）。** 09-16 三轮旧 gate 都 blocking=0，但肉眼明显错；旧 gate 主要管格式与局部关系，不覆盖漏墙、错墙、漏窗。证据：复现 README `:19-21`。因此 gate 通过不能当作历史验收被复现。

### 已证实存在，但因果强度未知的环境差异

4. **宿主变了。** 历史是 Agent-tool 子代理；09-16 是 Claude CLI 2.1.198，`claude -p --resume`。模型 ID 回执相同，传输、系统上下文、视觉预处理和服务端模型状态不可冻结。证据：历史 `sm24 .../llm.yaml:4-16`；当前 `reproduce.py:106-152` 与复现 README `:13-17`。这是合理嫌疑，但没有受控证据证明它单独导致退化。
5. **主控换了。** 历史 Fable 5，09-16 为开发 Astra；两边都不给 GT/正确坐标，09-16 的两份反馈甚至更具体地指出了标定、裁图逆变换和完整性问题。证据：`historical_recipe_audit.md:49-55`，当前反馈原文。不能把失败简单归因成“没有监督”；监督存在，模型仍未落实。
6. **完整历史 prompt 不存在。** 09-16 prompt 是根据 provenance 和历史结果重建的，并把历史返工纪律提前写入首轮；它不是原文。证据：`historical_recipe_audit.md:17,51-56,81-84`，当前 prompt `pilot_prompt.md:1-23`。这使 prompt 差异无法彻底排除，但当前 prompt 已明确要求关键动作，失败仍首先表现为未执行。
7. **09-16 是从 `723b0f9` 挑取 20 份文件到临时目录，不是完整 worktree。** 入口见 `reproduce.py:28-76`。历史 sm21 明确在完整 `723b0f9` 树；sm24 provenance 写的是 `723b0f9→891356d` 窗口，但同日总过程记录表明 E1 纪律/prescan 是成功跑完后才落地（实验 README `:59-71`），历史反馈也明确实际源点是 723。缺失完整树是否影响这次 reader 尚无直接证据；下一轮可以通过完整 worktree 消除这一变量。
8. **依赖环境有一个真实差异信号。** 09-16 pilot_01 自写 helper 尝试 `import cv2` 失败，随后仍可使用历史 PIL/SciPy 工具；证据在 `execution_audit.json` 的 `tool_errors`。它影响首轮探索，但不足以解释同会话两次返工后仍不做候选台账。

### 不应再列作主要原因的事项

- **不是“模型没拿到工具”。** 09-16 固定了 723 的工具/指南，实际也成功调用 profiler、calibrator、window detector 和 crop；问题是调用和回读不足。
- **不是“没有同会话返工”。** 三轮 session ID 相同，`--resume` 已使用；证据：`execution_audit.json` 与 `reproduce.py:119-120`。
- **不是“主控把答案泄露了，所以历史才成功”。** 历史记录和09-16反馈都只给流程/schema/自产物问题，没有给 GT 坐标或目标墙窗数。历史 sm24 确有两次打回（内容一次、schema一次），因此它本来也不是完全自主一次成功。
- **不能说旧方法只对 reading、所以无效。** 旧 reading 成绩应当承认为有效；它与当前源 BIM 全链验收是两个评价层。历史 sm24 correction 后来还改坏过正确 reading 值，说明必须另测 reading 到 BIM 的传递，而不是倒过来否定 reading。

## 五、原因排序与可证伪方式

| 排名 | 原因 | 当前证据状态 | 最短可证伪检查 |
|---:|---|---|---|
| 1 | 模型没有实际完成完整尺寸转录、局部裁图和候选接受/拒绝台账 | **直接证实**，与历史动作量差距最大 | 在完整 723 worktree 上把 pilot 验收门改成检查“尺寸/裁图/台账均真实存在且主控看过”，不预填正确坐标；若动作完整仍错，再降权 |
| 2 | 同名 Haiku 在当前 CLI/服务端/视觉宿主上的行为已变化 | **未证实假设**，历史宿主不可恢复 | 同一输入并行比较可用的 Agent-tool 宿主与 CLI；保持 worktree、prompt、主控和动作门一致 |
| 3 | 09-16 的挑文件临时环境遗漏了完整工作树中的隐含上下文 | **已证实环境不同，因果未知** | 直接用完整 `git worktree add ... 723b0f9`，不手选文件；若行为不变则降权 |
| 4 | 原始 prompt / Fable 反馈文本缺失造成关键措辞丢失 | **不可完全恢复** | 用保存的最小 directive + 原 skill；把验收放在实际动作而非猜措辞。若仍失败，只能记录为剩余不可控变量 |
| 5 | 随机方差 | **未排除**；三轮是同会话返工，不是三个独立冷启动样本，无法估计成功概率 | 配方与动作门先固定后做少量重复；不要在动作未执行时靠盲抽样解释 |

## 六、原件可恢复与缺失清单

**可恢复：** 两个 case 的原图与声明、07-02/07-07 输出 JSON/render、07-07 的全部 CV sidecar、旧 skill/tool 源码、sm21 的 GT scorer sidecar与容差、run config、模型 ID、主控型号、代码提交、pilot/batch组织、历史返工问题摘要、09-16 全 prompt/事件/工具调用/反馈/快照。

**缺失或不能冻结：** 07-02/07-07 完整 spawn prompt、逐轮完整对话、Fable 原反馈全文；07-02 完整 transcript 本体和临时 helper 源文件；历史 Agent-tool 宿主实现、服务端模型权重/采样、视觉预处理；sm24 当时独立 GT；sm24 精确 active tree 的逐字节证明（run provenance 只给时间窗，过程总账支持 723）；历史 token/费用底层账单；sm24 correction 改坏 reading 的完整逐项清单。

本审计最关键的判断是：**09-16 证明的是“同一 Haiku ID 在当前宿主下，即使拿到近似历史文件和明确指令，也可能不执行足量工序”；它没有证明“历史成功配方完整执行后仍失败”。** 下一次历史对照应优先消除完整树、宿主和动作验收三个差异；当前主线可以继续，但不宜再用 09-16 三轮把旧 reading 成功降格为偶然或不可复现。
