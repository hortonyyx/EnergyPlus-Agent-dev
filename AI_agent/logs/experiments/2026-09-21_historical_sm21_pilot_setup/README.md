# sm21 07-07 旧 reading 一层独立 pilot harness

本目录提供历史方法对照入口；已完成一轮冷启动和一次同会话原图反馈返工，两轮均失败，见[实际结果](../2026-09-21_historical_sm21_pilot_run01/README.md)。它从提交
`723b0f98ed37285b66cb3d1d30caa8e42eb01a74` 提取白名单字节，只提供 sm21
一层原图、原建筑声明、旧 reading 规则、旧 schema、旧 CV 六工具及旧独立
render。不会投影同墙网 worked example、GT、scorer、旧 run、答案或 `.git`。

模型侧没有 Bash、Python、Read、Write、Edit、Glob、Grep、Agent、Web 或其他
原生工具，只允许一个 `mcp__reading__*` stdio server。MCP 参数不接受输入/输出
路径：原图、旧脚本、recipe 和输出根由服务端固定，自产物只能用不透明 artifact
ID 查看。

## 已完成的离线验证

运行：

```bash
python AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_setup/verify_offline.py
```

该脚本使用真实 MCP stdio `ClientSession`，不调用模型。它核对精确 tool 列表，
读取完整旧规则，验证原图返回像素一致，实际运行一次冻结的 `crop_zoom`，验证规则
名/自产物 ID/越界 bbox 拒绝，并用空的合成 reading 检查 `submit_pilot` 不含构件
数量门槛。结果写入 `offline_verification.json`。离线MCP像素正确不保证宿主实际收到相同像素：本次CLI流中的大图出现缩放，逐轮核验及诊断见实际结果。

## 准备实际 run

实际输入和输出不写在 setup 目录内。选择一个全新的 run 目录：

```bash
python AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_setup/run_historical_pilot.py \
  prepare \
  --out AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_run01
```

准备后先由主控检查：

- `input_manifest.json`：16 个 723 原字节输入、2 个空包兼容标记及 SHA-256；
- `implementation_manifest.json`：runner、MCP、离线验证代码和首轮 prompt 散列；
- `workspace/projection_manifest.json`：MCP 启动时再次强校验的输入白名单；
- `workspace/`：只含冻结输入、空 `0_reading/`、空 `requests/`；
- `cli_cwd.json`：指向 `/tmp` 下同一 run 首轮与 `--resume` 共用的稳定空 cwd；
- `invocations/`：每轮独立记录和快照，不覆盖前轮。

`prepare` 拒绝已有 `--out`，避免覆盖旧 run。

## 首轮启动命令

主控审核参数、权限和 manifest 后，首轮命令为：

```bash
python AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_setup/run_historical_pilot.py \
  invoke \
  --out AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_run01 \
  --label pilot_01 \
  --timeout 1200
```

默认 prompt 为本目录 `pilot_prompt.md`。它只要求完整处理可见信息和诚实记录
未查范围，不包含正确坐标、构件数、候选数或历史分数，也不设置调用/crop/候选/
墙窗尺寸数量下限。预算默认 1200 秒，可显式调整并会进入 request/receipt。

runner 固定请求 `claude-haiku-4-5-20251001`，不配置 fallback，不传 API key 或
base URL。CLI 使用 `--tools "" --allowedTools "mcp__reading__*"
--strict-mcp-config --setting-sources "" --disable-slash-commands`；实际模型、CLI 版本、
stream、stderr、usage、session ID、耗时及超时状态均保存。超时终止整个进程组。

## 可选同会话返工

主控只能依据原 1F 图、声明、模型自产 sidecar/台账/render/overlay 和旧 schema 写
流程性反馈，不给目标坐标、正确数量、历史值或目标格局。将反馈写到一个新文件，
再执行：

```bash
python AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_setup/run_historical_pilot.py \
  invoke \
  --out AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_run01 \
  --label pilot_02 \
  --resume \
  --prompt /absolute/path/to/source_only_feedback.md \
  --timeout 1200
```

每个 label 必须匹配 `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`，因此不能用 `../` 逃出
run。`--resume` 读取该 run 自己的 `session_id.txt`；首轮和返工都从同一持久
`cli_cwd.json` 所记的仓库外空目录启动。每轮保留原 prompt、精确命令、stream、stderr、receipt、
`0_reading/`、内部结构化请求、MCP 工具日志和逐文件 snapshot 散列。
两轮之间不要清理该 `/tmp` cwd；它不含输入，但其稳定绝对路径用于 Claude 会话续接。

## MCP 输出结构

旧 CV sidecar 位于 `workspace/0_reading/cv_evidence/1f_view/`。每次
`submit_pilot` 会保留新版本：

```text
workspace/0_reading/submissions/001/
  1f_view.json
  coordinate_frame.json
  candidate_ledger.json
  pilot_self_check.json
  1f_view_render.png
  1f_view_source_overlay.png
```

顶层同名文件指向最新提交内容，旧版本不覆盖。提交只做旧 Pydantic schema 和
机械字段/坐标检查；返回的墙、窗、尺寸和候选数只是报告，不是通过门槛。原图
overlay 使用模型显式提交的 x/y 像素—米锚生成，是本实验新增的可审 harness，
不会改 reading JSON，也不冒充 723 原工具。

## 冻结后评价

source-only 检查通过或两轮用尽后，主控先冻结候选 hash，再在 reader 不可见的
控制侧运行 723 loader/gate 和旧 scorer。GT 分数不得回灌本次会话。此 setup 不
包含评分入口，避免 scorer/GT 进入 MCP 可见面；也不进入 2F、立面、correction
或 BIM。

## 已知且不可恢复的差异

- 07-07 完整 spawn prompt、逐轮原对话、Fable 原反馈、旧 Agent-tool 宿主、服务端
  权重/采样、视觉内部预处理、订阅额度状态及历史依赖版本不能恢复。
- 为了独立性，主动排除了同墙网 worked example；旧 kickoff 中该引用明确不可用。
- reader 得到的是 723 白名单投影，并经 MCP 读规则/图像、调用旧 CV；不是完整
  worktree，也没有历史 Bash/Python、自写 helper 或任意文件浏览能力。
- `submit_pilot` 版本化和原图 overlay 是新实验支撑。当前依赖可运行不等于历史
  NumPy/Pillow/SciPy 字节环境相同。
- 当前开发主控知道部分历史答案，故反馈必须遵守 source-only 边界。

因此结果只能称为“723 旧规则/CV 在当前 Claude CLI 宿主下、去答案输入的一层
独立 pilot”，不能称逐环境原样重放。

## 本次完成后的只读检查

新增 `verify_invocation.py` 核真实流、输入和快照，`evaluate_frozen.py` 在两轮及原图review冻结后运行旧loader/gate和旧一层scorer，`write_report.py` 生成原图/两轮叠图对照。后三者与结果README不属于模型执行时冻结的四文件，不改写旧候选。评测读取723版本GT，只留在控制侧；旧结构放行和外围数字边界命中不证明原图配准或房间分隔正确。
