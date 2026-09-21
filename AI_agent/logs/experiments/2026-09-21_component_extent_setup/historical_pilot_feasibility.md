# 07-07 sm21 一层旧 reading pilot：白名单 MCP 可行性核查

本记录只核下一次历史 pilot 的最小执行面。没有创建 worktree、没有调用模型/API、没有读取 GT、旧 case 输出或凭据，也没有修改生产代码。

## 结论

**可以不做完整容器、mount namespace 或整套操作系统隔离，直接用“无原生工具的 Claude 订阅 CLI + 单一白名单 MCP”运行这次 pilot。** 模型不应再拥有 Bash、Python、Read、Write、Edit、Glob 或 Grep；只给一个 reading 专用 MCP。MCP 内部由可信代码读取固定的 723 字节、返回固定的 1F 原图、执行六个旧 CV 子命令并把结果写到固定实验目录。这样答案边界由“模型没有任意文件/命令能力”保证，不再依赖 Claude settings 的路径 deny，也不要求先把整机文件系统做成隔离容器。

这是一种**能力隔离**，不是操作系统安全沙箱。其成立条件是 MCP 接口不能接收任意路径、任意命令或任意 Python；每个文件和动作都必须由枚举值选择，输出位置由服务端固定。如果以后重新给模型 Bash、Python、通用 Read 或能执行任意参数的 MCP，这个结论立即失效，届时才需要 next pilot plan 所述的 OS 文件可见性隔离。

完整 detached worktree 也不是本次启动条件。控制侧可以像 09-16 `reproduce.py:32-47` 一样，直接用 `git show 723b0f98...:<path>` 提取逐字节白名单投影并保存 SHA-256。提交对象已经是确定的字节来源；额外 worktree 只会增加需要隐藏的 `.git`、旧 run 和 GT 表面。实验口径应写成“723 白名单投影视图”，而不是“完整 723 worktree 内运行”。

## 最小可运行结构

另建新的实验入口，不改 09-16 旧实验。保留其会话、回执和进程管理代码，替换准备阶段与工具面。

### 1. 控制侧只投影这些输入

从 `723b0f98ed37285b66cb3d1d30caa8e42eb01a74` 取：

- `skills/intake_pipeline/0_reading/{session_kickoff,guide,reading_guide,pen_library,cv_toolbox}.md`
- `scripts/tool_scripts/cv_probe.py`
- `src/agent/reading/cv_toolbox/{__init__,tools,recipes,sidecar}.py`
- `scripts/tool_scripts/render_vector_to_png.py`，只用于候选自产 render
- 必要的空包标记 `src/__init__.py`、`src/agent/__init__.py`、`src/agent/reading/__init__.py`
- `case_tests/e2e_tests/sm21_anchor/case_data/1f_view.png`
- 原 `testdata_prompt.json`

不要投影 `smalloffice_20` worked example、sm21 目录中 `case_data` 之外的任何文件、GT、scorer、旧 run、`.git`、当前仓库或 home。旧 kickoff 可保留原字节；首轮 prompt 明说它提到的 worked example 因同墙网而不可用，格式以 `guide.md` 的 schema 为准。

这两个实际输入在 723 与当前仓库字节相同：

- `1f_view.png`：2133×1345，SHA-256 `ac62091683dde4ab7ca647f27a87a14eb386a6784a0e5bdf8852c7a9da1628a4`
- `testdata_prompt.json`：SHA-256 `f73f98876e6ffef262629f0effe9ed7e364ce4878618241c97e59fe766f6dbfb`

仍应从 723 对象提取并在 manifest 中记录来源，避免“碰巧与 main 相同”替代版本证据。声明中的 `thermal_zones: 7` 原样提供并明确标为正式输入先验，不能扩写成墙窗答案。

### 2. reading 专用 MCP 只注册七类能力

建议新实验脚本用当前已安装的 `mcp.server.fastmcp.FastMCP`，服务名固定为 `reading`。接口如下：

1. `manifest()`：返回允许的输入名、尺寸、散列、原声明和实验边界，不返回任何文件路径。
2. `get_rule(name)`：`name` 只能是上述五个规则文件的枚举；返回 723 原字节文本和散列。不存在任意路径参数。
3. `view_original(box=None, scale=1)`：只读取固定的 `1f_view.png`；bbox 必须在 2133×1345 内，返回图像及原图坐标变换。缩放只作用于返回视图，不改源图。
4. `run_cv_probe(tool, params)`：`tool` 只能是 `crop_zoom`、`wall_line_profiler`、`storey_line_profiler`、`px_m_calibrator`、`window_cc_detector`、`overlay_logger`。源图、recipe 和输出根由服务端固定；模型只能传旧命令本来允许的数值/结构参数。
5. `list_artifacts()`：返回本轮自产 sidecar/crop/overlay 的不透明 artifact ID、类型和散列，不返回真实绝对路径。
6. `view_artifact(id)`：只能查看第 4 项产生且已登记的图像，拒绝路径、`..` 和未登记 ID。
7. `submit_pilot(reading, coordinate_frame, candidate_ledger, self_check)`：将一次提交版本化写入固定 `0_reading/submissions/NNN/`，生成 `1f_view.json`、显式坐标框架 sidecar、候选处置台账、自检、旧式独立 render 和原图框架 overlay；返回散列和两张图，不接受输出路径。

`run_cv_probe` 要执行旧 CLI 语义，但不把 CLI 暴露给模型。最稳妥的短实现是服务端用参数列表调用冻结的 `cv_probe.py`，绝不使用 shell：

- `--image` 固定为投影中的 1F 原图；
- `--out-dir` 固定为本实验的 `0_reading`；
- `--recipe` 固定为 `clean_vector_v1`；
- `--sidecar-name` 由服务端分配；
- `anchors_json` 与 `candidates_json` 先由 MCP 校验为 list/dict，再写到服务端固定的请求文件，传固定文件名给旧 CLI；不允许模型传路径字符串；
- bbox、scale、axis、连通域阈值只接受有限数值并检查 finite/bounds；
- 每次运行以前后文件集合差得到新 sidecar，登记 artifact ID，并将 JSON 与对应 crop/overlay 一并返回。

也可以直接导入旧 `cv_toolbox` 函数，但调用冻结 CLI 更接近历史命令的 sidecar 分配和落盘行为。模型失去自写 helper 的能力是有意缩窄；六个历史工具仍完整可用。

`submit_pilot` 中的 `coordinate_frame` 至少保存 x/y 各两组 `[source_pixel, local_metre]` 锚。旧 schematic renderer 只给独立白底图，不能自动叠回原像素；实验 wrapper 用这组显式锚做确定性仿射换算并画原图 overlay。这是为 next pilot plan 的“原图框架下回看”新增的实验支撑，不冒充 723 原工具，也不改 reading JSON。

### 3. 订阅 CLI 调用方式

09-16 runner 以下部分原样复用：固定 `claude-haiku-4-5-20251001`；保存 prompt、stream JSON、stderr、实际模型、CLI 版本、耗时和 usage；首轮保存 session ID，内容返工用同一 `--resume`；超时终止整个进程组；每轮完整快照并散列输出。

工具启动改用当前 `scripts/tool_scripts/run_bim_agent.py:142-166` 已实际使用的白名单形态：

```text
claude -p
  --model claude-haiku-4-5-20251001
  --tools ""
  --allowedTools "mcp__reading__*"
  --permission-mode dontAsk
  --strict-mcp-config
  --setting-sources ""
  --settings '{"disableAllHooks":true}'
  --disable-slash-commands
  --mcp-config '<only the reading stdio server>'
  --output-format stream-json
  --verbose
```

首轮不要加 `--no-session-persistence`，否则不能返工 `--resume`；这点与当前无状态 JSON correction 路径不同。第二轮只追加保存的 session ID。CLI cwd 用新的空临时目录，不用投影目录或仓库。环境沿用 `src/agent/execution/subscription_json.py:33,75-77` 的 `PATH/HOME/LANG/LC_ALL` 白名单，再加无敏感值的 `ENABLE_TOOL_SEARCH=false`、`PYTHONDONTWRITEBYTECODE=1`。不要传 API key/base URL/Anthropic API 环境变量，也不要配置 `--fallback-model`。`HOME` 仅供现有订阅 OAuth；模型没有 Read/Bash，MCP 也没有 home 路径接口。

当前离线 `claude --help` 确认 `--tools ""`、`--allowedTools`、`--strict-mcp-config`、`--resume` 和 `--disable-slash-commands` 均可用；当前 CLI 是 2.1.198。`run_bim_agent.py` 已用同一关键组合运行过仅 MCP 的订阅实验，因此不需要先实现新的订阅通道。

## 实际代码依赖与最短改动

旧 CV CLI 的依赖只有冻结的四个 `cv_toolbox` 文件及 NumPy、Pillow、SciPy。此次离线导入和 `cv_probe.py --help` 已成功：NumPy 2.4.4、Pillow 12.2.0、SciPy 1.17.1；`mcp` 也可导入。旧独立 renderer 只依赖 Pillow。

下一轮最短实现是两个实验文件，不碰生产代码：

1. `run_historical_pilot.py`：由 09-16 `reproduce.py` 复制后改 case、投影清单、CLI flags、MCP config、临时 cwd 和快照目录；保留 session/receipt/超时逻辑。
2. `historical_reading_mcp.py`：实现上述固定接口、参数校验、旧 CLI 子进程和提交/overlay。它只读投影视图，只写本实验 `0_reading` 与内部请求目录。

不需要复制当前整套 `run_bim_agent.py`，也不需要把当前 BIM 工具、production guidance 或 `src/agent/execution/isolation.py` 拉进实验。现有 BIM MCP 只证明订阅 CLI 的白名单形态可行；它的工具范围与本次旧 reading 不同，不能直接开给 reader。

评分侧仍放在模型不可见的控制目录。source-only 检查结束或两轮用尽后，先冻结提交 hash，再运行已有 723 loader/gate 和旧 scorer；分数不回灌。控制侧 scorer 可以读取 GT，不代表 reader MCP 可以读取。

## 启动前只需做的离线自检

不需要展开一套 OS 隔离工程。启动前完成以下小检查即可：

- manifest 中每个源文件都来自 `git:723b0f98...:<path>` 且散列固定，清单中没有 worked example、GT、旧 run、scorer 或 `.git`；
- 启动命令解析后内置 tools 为空，只允许 `mcp__reading__*`，strict MCP 配置里只有一个 reading server；无 `--add-dir`、plugin、Agent/Task/Web 或 fallback；
- 离线列 MCP tools，名称恰为预期集合；对 `../`、绝对路径、未知 rule/image/artifact/tool、非有限数值和越界 bbox 的直接调用全部拒绝，且投影目录外没有新文件；
- 在 scratch 中对 1F 副本跑一次旧 CLI `--help`/导入和一个不含答案的 crop smoke，确认 sidecar、crop 和 overlay 都落在固定输出根；
- `submit_pilot` 用合成小 JSON 验证版本化写入、散列、render/overlay 和不可覆盖，不用 GT 或旧 case 答案。

模型运行后再复用 09-16 的事件审计：核实际模型、session 连续性、MCP 调用/错误、返回图像与本地产物像素，以及每轮完整快照。由于模型根本没有 Bash/Read，负向自检不再要求“同权限 Bash 打不开答案”；应改为证明该权限集中不存在 Bash/Read，且所有 MCP 参数都无法表达答案路径。

## 不能保持的历史条件

即使上述方案成功，也只能称为“723 旧规则/CV 在当前 Claude CLI 宿主下、去答案输入的独立 pilot”，不能称逐环境原样重放。以下条件无法保持或被主动改变：

- 07-07 完整 spawn prompt、逐轮原对话和 Fable 5 原反馈全文缺失；
- 历史 Agent-tool 宿主、服务端权重/采样、视觉内部预处理、订阅额度状态和历史依赖版本不可冻结；
- 为独立性主动排除了与 sm21 一层墙网相同的 worked example；旧 kickoff 因此有一个明确不可满足的引用；
- reader 看到的是按白名单投影的 723 字节，不是完整 worktree；规则经 MCP 返回，原图经 MCP 返回，旧 CV 经 MCP 包装调用；
- 模型没有历史 Bash/Python、自写 helper 和任意文件浏览能力，动作可达面比 07-07 更窄；
- 原图 overlay 与版本化 `submit_pilot` 是本次实验新增 harness，不是 723 原工具；
- 当前 NumPy/Pillow/SciPy 版本只证明能运行，不能证明与 07-07 环境相同；峰值或连通域边界若出现版本敏感差异，需按实际产物记录；
- 当前主控已经知道部分历史答案，因此仍必须按预先冻结的 source-only 检查表反馈，不能给正确坐标、数量或目标格局。

这些变化不会妨碍本次核心问题：在不给答案和通用 shell 的情况下，当前 Haiku 能否真正完成尺寸转录、局部观察、候选处置和一层旧 schema reading。它们只限制结果的历史归因范围。

## 直接执行顺序

下一轮可直接按以下顺序推进：先写上述两个实验文件并跑离线自检；生成投影 manifest 和首轮 prompt；以新 session 只跑 1F；保存 source-only 检查与首轮快照；若内容不合格，只在同一 session 做一次不含答案的返工；两轮后冻结 hash，再由控制侧评分。无需先建 worktree、容器或完整 OS 隔离，也不进入 2F、立面、correction 或 BIM。
