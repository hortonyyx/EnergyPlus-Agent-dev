# Dev model 手动 BIM 工具接口

本接口供 dev model 或外层执行者在已准备的冷启动 run 上手动调用当前 BIM 工具。它不调用 work model，不读取 GT，也不包含任何案例答案。工具定义始终来自当前 `scripts/tool_scripts/run_bim_agent.py` 启动的 MCP server；`bim_agent_bridge.py` 是唯一执行桥。

## 运行边界

- 输入必须是已有 run，其根目录含 `inputs.json`；新 runtime 形式的 run 也可传外层目录，helper 会自动使用其中的 `bim/`。
- 请求文件是 JSON 数组，每项严格为 `{"tool":"工具名","arguments":{...}}`。
- `review_detail` 被 bridge 明确排除，因此本接口不会启动任何模型或隐藏委派。
- 每批请求的完整原文、完整 MCP 回执和返回图片由 bridge 保存到 `<run>/bridge/<uuid>/`。helper 只在终端打印短摘要，不替代这些原始证据。
- 同一批按顺序执行，第一项错误即停止；需要依据前一项结果决定参数时，应拆成多批。
- Windows 上 helper 只为 bridge 启动的 MCP server 显式补入 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。MCP 的默认子进程环境白名单不继承这两个变量；缺少它们时，server 内未显式指定编码的文件回读可能按 GBK 解码 UTF-8 产物。此修复位于实验 wrapper，不修改生产 bridge、工具或 run 文件。

## 调用

在仓库根目录执行：

```powershell
$helper = "AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/dev_bridge_helper.py"
$run = "<已有 run 路径>"
.\.venv\Scripts\python.exe $helper call --run $run "<requests.json>"
```

示例请求只读取本次 run 的输入清单，不含 case 内容：

```json
[
  {"tool": "inputs", "arguments": {}}
]
```

执行摘要会给出：完整记录目录、是否整批完成、逐项工具名、错误、返回图片路径，以及候选/草稿等少量关键 ID。查看图片时直接打开摘要中的 PNG；需要精确判断时以该 PNG 和 `replies.json` 为准。

## 观察历史

以下命令只读扫描 bridge 记录，按请求文件时间排序，统计批次数、顶层工具请求/回执/成功/失败/待回执数和图片数，并列出每批工具及图片：

```powershell
.\.venv\Scripts\python.exe $helper history --run $run
```

`summary` 中首次 build、首次成功 build、assembly 和 finish 时间来自 bridge 文件时间戳：attempt 使用 `requests.json` 的 mtime，success 使用整批 `replies.json` 的 mtime。后者表示该批结束时间，不冒充逐调用 server 时钟。工具调用与失败只按顶层 bridge requests/replies 计算；不把 `tools.jsonl` 里的内部动作计为模型调用，因此 `claim_transaction` 内嵌的 `record_claim` 等动作不会重复。外部会话无法取得的 provider token 与费用保持 `unknown`。

完整行为审计仍应结合：

1. `<run>/bridge/*/requests.json`：执行者实际提交的参数；
2. `<run>/bridge/*/replies.json`：工具完整回执；
3. `<run>/bridge/*/*.png`：工具返回给执行者的确切图像字节；
4. `<run>/tool_calls.jsonl` 及候选、claim、校准、review、delivery 文件：server 侧落盘状态（存在时）；
5. `inputs.json`、`preparation.json`、`guide.txt`、`task.txt`：冷启动输入与指引边界。

不要从 `history` 的短摘要推断几何质量；它只回答调用了什么、是否报错、返回了哪些图。

## 完成与评价

生成阶段结束后，先确认 `delivery.json` / `delivery.html` 已存在，或明确指定一个未交付候选。然后运行现有离线评价入口：

```powershell
.\.venv\Scripts\python.exe $helper evaluate --run $run --case sm25
```

默认写入 `<run>/dev_evaluation/`；该目录必须尚不存在。若本轮没有 delivery，可显式加 `--candidate candidate_NN`。评价阶段才由现有 `scripts/dev/evaluate_run.py` 在生成结束后隔离读取 GT，并输出：

- `summary.json`：实质错误、5/10/30 cm 分档、查看地址；
- `display/`：公开命名的平面图与 BIM viewer；
- `overlays/`：只使用本 run 自身校准生成的回叠图；
- `evaluation/index.html`：完整独立评价页。

评价命令不调用模型，并在前后校验输入、候选和 GT 文件哈希，防止评价反写生成结果。它必须留到冷启动执行结束后，不能把评价产物反馈给正在生成的执行者。
