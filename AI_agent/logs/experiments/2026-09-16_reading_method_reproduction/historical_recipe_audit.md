# 07-07 成功 reading 方法：可执行历史配方审计

本审计只回查仓库原件，不把 07-07 reading 高分扩大为完整源 BIM 成功。历史 sm24 当时没有 GT，质量结论是用户人工肉检；后续 correction 还被登记为改坏了部分正确 reading 值。

## 成功时实际条件

| 项目 | 可复原事实 | 证据 |
|---|---|---|
| reader | `claude-haiku-4-5-20251001`，冷启动 Agent-tool 子代理；主控/定性 judge 为 Fable 5 | [sm24 llm provenance](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/llm.yaml)、[总过程记录](../2026-07-07_haiku_cv_retest/README.md) |
| 代码树 | 历史回顾指向 `723b0f9` 的 pre-prescan 工具；run provenance 只定位到 `723b0f9→891356d` 窗口，精确运行树不能完全证实。`891356d` 包含后续 prescan 和工具纪律，不能整体倒灌进原跑测 | [历史纠偏原件](../../../archive/2026-09-08_claude_memory/container/reproduce-the-form-not-the-run.md)、[当前冻结清单](input_manifest.json) |
| 输入 | sm24 的五张原始 PNG（1F、东南西北四立面）及未改 `testdata_prompt.json`；声明含 200 m²、1 层、`thermal_zones: 8`，它是用户输入先验，不是坐标 GT | [case_data](../../../../case_tests/e2e_tests/sm24_anchor/case_data)、[输入散列](input_manifest.json) |
| 规则与格式 | 完整 `session_kickoff.md`、`guide.md`、`reading_guide.md`、`pen_library.md`、`cv_toolbox.md`，并以 `smalloffice_20/0_reading/1f_view.json` 只作格式示例 | [723 冻结副本](frozen_input/skills/intake_pipeline/0_reading)、[格式示例](frozen_input/case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json) |
| 额外指令 | kickoff 当时把 CV 工具写成 Optional；本 run 明确提升为必用：`cv_toolbox.md is REQUIRED`，墙线、窗框、层线位置必须先用 `cv_probe.py` 测量再画 | [sm24 llm provenance](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/llm.yaml) |
| 隔离 | 只给本 case 图片、声明、reading skill 和格式例；禁 GT、旧 attempts、judge 产物及其他 run。是 prompt 级隔离，不是 OS 硬隔离 | [总过程记录](../2026-07-07_haiku_cv_retest/README.md) |
| 会话与检查 | 先只做 1F pilot，停等主控审；反馈回到同一连续会话返工；pilot 通过后才批量逐图；主控反馈只谈流程/schema，不给 GT 坐标或正确房间答案 | [kickoff 冻结副本](frozen_input/skills/intake_pipeline/0_reading/session_kickoff.md)、[07-09 对照日志](../2026-07-09_prescan_narrowing/HAIKU_RETEST_LOG.md) |

完整原始 spawn prompt 没有随 07-07 run 保存。仓库只能恢复上述规则文件和 provenance 中的 directive，不能声称逐字复原整份 prompt。

## 实际逐图工序

reader 先从尺寸链 tick 取锚并运行 `px_m_calibrator`，再用 `wall_line_profiler` / `storey_line_profiler` 提候选、`window_cc_detector` 在墙带或立面局部找开口，用 `crop_zoom` 放大判别，最后用 `overlay_logger` 保存每个接受/拒绝候选及理由。工具只量像素，墙、家具、门、真实无门开放段等语义仍由模型判断。

sm24 最终留下 38 份 CV JSON sidecar：

| 图 | crop | 标定 | 墙/层线投影 | 窗 CC | 候选台账 | 结果摘要 |
|---|---:|---:|---:|---:|---:|---|
| 1F | 11 | 1 | 墙 2 | 4 | 1 | 14 墙、11 窗、51 尺寸；L 形走廊保持连贯；真实开放段不治愈 |
| East | 1 | 1 | 层线 1 | 1 | 1 | 3 窗，门只登记不画 |
| North | 1 | 1 | 层线 1 | 1 | 1 | 1 个 4800×2400 大窗，双门登记 |
| South | 1 | 1 | 层线 1 | 1 | 1 | 2 窗，单门组件登记 |
| West | 0 | 1 | 层线 1 | 1 | 1 | 5 窗；为暗绿色尺寸链降低阈值复扫 |

逐图数值、空字段、像素量测台账和 schema 反馈见 [原 reading summary](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/reading_summary.md)。关键表达规则是：外周墙用外皮线、内部隔墙用中线，这一混合基准只写在各 stroke 的 note 中，没有结构化字段；未标注 H6 和七处内门明确记为像素量测，`dimension_refs` 不伪造；门触发墙线治愈，真实无门开放段不治愈。

## 主控干预和返工

sm24 不是一次自主提交成功：

1. pilot r1 已调用工具，但锚很粗（RMSE 86 mm）、只描“主要墙”、漏窗，并出现像素到米换算矛盾。主控只要求锚收紧到约 ±1 px、完整处理全部墙/窗、统一换算公式和留痕，没有给正确坐标。
2. pilot r2 内容达标：36.33 px/m、RMSE 9.2 mm，14 墙和 38 个拒收候选均有算术/理由；但 51 个 `dimensions[].anchor` 被写成自创 dict，历史 schema 要 `list[float] | null`，因此再打回一次纯机械 schema 修订。
3. loader 通过后才批量四立面；每张独立标定，立面 facade 保持 image-local，mirrored 留 unknown。最终 gate blocking 为零；`dimension_chain_closure` 因 overall 与 segment 分在不同 chain_id 被当作已知 advisory，不能据此宣称所有 gate 全绿。

sm21 同方法只经历一轮内容返工；它的 1F r1 错把墙端/文字行当尺寸 tick、量成 14.52×8.90 m，并未经 crop 核候选而画 19 道内墙。r2 改为尺寸 tick 标定、44 个候选逐项拒收、8 门治愈和窗的 CC/尺寸链双证据后才放批量。sm21 有 GT，最终墙 9/9、平面窗 7/7、立面窗 15/15；sm24 无 GT，不应沿用“机器满分”说法。

## 与 07-09 失败的区别

07-09 不是 07-07 完整配方复现。它增加 prescan 收窄和硬隔离，同时没有独立的 per-run `measure-before-draw` directive 槽，也没有同一会话连续返工；每轮都是一次性 `-p` 冷启，只靠 feedback 文件重新 spawn。结果 5 个会话、约 1.03M 新 token，四轮 pilot 仍锚错、漏墙漏窗并保留幻觉短墙。prescan 批次记录 CV 调用从 86 降到 2–6 且候选被消费，但这些同时变化的条件没有受控消融，不能认定任一差异为失败的直接原因，也不能据此判定 prescan 的质量作用。见 [07-09 原执行日志](../2026-07-09_prescan_narrowing/HAIKU_RETEST_LOG.md) 与 [run 配置](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-09_haiku_prescan_triage/run_config.yaml)。

## 本次复现与历史的差异

- 本次固定 `723b0f9` pre-prescan 字节，这是按历史回顾选择的可核近似基线；sm24 的 run provenance 只写了 `723b0f9→891356d window`，不能写成已证实全部历史环境逐字节复原。
- 历史 Agent-tool transport 换成当前 Claude 订阅 CLI；固定请求相同 Haiku ID，实际回执与 CLI 版本按 invocation 保存。模型服务端权重、采样和 2026-07-07 的 Agent 宿主不可复原。
- 当前 [pilot prompt](pilot_prompt.md) 已把历史首轮返工所得的 tick 锚、候选接受/拒绝台账和诚实像素来源提前写进首轮。因此它验证“最终有效组合能否再工作”，不重演历史 r1 的自然失败轨迹。
- 当前由开发 Astra 代替 Fable 做外部 pilot 审；只允许给流程/schema反馈，不得给 GT、旧正确坐标或房间答案。二者主控能力不能视为相同。
- 本次保留原像素文件帧，并明确不 resize；历史视觉 transport 是否对图像做过服务端缩放没有底层记录，文件像素与模型实际视觉帧是否完全相同无法证明。
- 当前为 prompt 级 Bash 约束，和历史隔离强度相近，但不是 OS sandbox。reader 工作区不含本历史 gate，避免检查源码反向提示答案。

## 可运行入口与验收顺序

本次实验入口为 [reproduce.py](reproduce.py)：`prepare` 冻结输入；第一次 `invoke` 做 pilot；后续必须带 `--resume` 让返工和批量继续同一 session。先审盘上 JSON、sidecar 和叠图，再给流程性 feedback；通过后才发批量提示。不要加入 prescan、换 schema、压预算或改成无状态重 spawn。

历史 reader 不是旧 flow 的自动 stage runner，而是先由 Agent 会话直接写 `0_reading/*_view.json`。reading 已产生后，历史全链入口为：

```bash
python scripts/tool_scripts/run_stage.py --base-dir case_tests/e2e_tests \
  --date 2026-07-07 flow sm21_anchor run_2026-07-07_haiku_cv_retest \
  --judge stop --to 3_split_pairing --geometry required
```

本轮不得调用 DeepSeek，因此只复现 reading。先用冻结 schema/gate 检查，不执行今天新增的 gate：

```bash
python AI_agent/logs/experiments/2026-09-16_reading_method_reproduction/controller_legacy_gate/check_legacy.py \
  --pretty /tmp/ep_reading_reproduction_20260916_sm24/0_reading/1f_view.json
```

[controller_legacy_gate](controller_legacy_gate) 内的 `src/agent/reading/{schema,legacy}.py`、`src/agent/roles.py`、`src/validator/checks/{reading,schema}.py` 均逐字节取自 `723b0f9`；其余 `__init__.py` 仅作轻量包标记，避免导入今天的 Agent、IDD 或 validator。脚本默认 `dimensioned=false`，与历史 sm24 accepted attempt 的 gate 元数据一致；如实验另有明确元数据再显式传 `--dimensioned true`。

验收至少分四层记录：schema 可载入；历史 gate 无 blocking；开发主控逐项核真实像素/候选处置；完整五图与原图人工比较。完成后再另测 reading 到当前源 BIM 的传递，不能让 correction/装配结果反向替 reading 成绩背书。

## 仍不能复原的条件

- 07-07 完整原始 spawn prompt、逐轮对话全文、Fable 的原 feedback 文本没有保存；只能按 provenance 和过程记录重建。
- 历史模型服务端状态、采样随机性、订阅会话额度中断点与视觉内部缩放不可冻结。
- sm24 没有当时独立 GT；“用户肉检好”不能改写成量化满分或稳定成功率。
- 历史 token 数（sm24 约 0.65M/96 次往返）来自过程总账，没有底层账单；只能作二手规模参考。
- 好 reading 到 correction/源 BIM 的保真没有由该实验证明；sm24 correction 改坏 reading 的具体逐项清单仍未完整恢复。
