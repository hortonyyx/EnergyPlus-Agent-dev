# B1：分工模式的上下文缓存

执行方：Astra，单人执行，未派子代理。基准 `5927bb5f`，工作树 `dev/astra-b1-20261007`。依据 [派工单](brief.md) 与[验收 A–F](../../../project/unified_agent_acceptance.md#底座优化-b1分工模式的上下文缓存10-07-派出astra)。状态：实现和离线检查完成，283 项均有通过记录；F 的临时清理被自动审批拦截，未完成。主样本 run3 达到 80% 前缀复用目标；run4 调度员短样本为 79.31%，边界见 C。

已完整读取 [Agent.md](../../../Agent.md)、目标、路线、开发方式和当前交接；检查分支、工作树与近期提交。所有改动留在工作树，`.git` 只读。未合并主线 `28795b49`，未修改 `store.py`、正式 Agent 登记表及 D1h 的其他代码。本包模型服务请求 **0 次**，Paratera 0、DeepSeek 0。

## A. 诊断结果与证据

[逐次对照表](request_comparison.md) 给出每次实际总量、缓存读取量、改前/改后估算输入与相同前缀、压缩次数、首差位置和图像事件。[comparison.json](comparison.json) 另含事件编号、时间、原请求/重放 SHA256、完整策略、状态哈希、标记位置及原始用量。由 [analyze.py](analyze.py) 可重复生成 JSON。

- run3：80 次请求、80 次响应；原请求正文哈希校验与旧策略完整重放 **80/80 逐字节一致**。
- run4：72 次发出记录、71 次响应；旧策略重放 **72/72 逐字节一致**。与 Opus README 中的“71 次”口径差异来自 `plan_f1_r2` 第 2 次请求（`event-000982`）没有响应。该次只计算已发请求投影，用量记为未知，未冒充 0 消耗。run4 因目标名称死结被停止，调度员仅 7 次请求，作为补充样本。
- run3 调度员实际压缩 **7 次**（请求 9、14、18、25、31、35、39），平面读图员 1 次；原初步解释中的“调度员 8 次”应更正为全任务合计 8 次。run4 调度员未压缩，平面读图员压缩 5 次。

### 压缩解释成立，但可变状态尾部也是主要原因

run3 调度员原始输入在后半程约 6.2 万到 13.1 万 token 之间重复升降。压缩把历史前方的说明改写，相同前缀退回约 9,840 估算 token（主要为工具、系统与初始输入）；因此“频繁压缩损失前缀”成立。

另一个主要原因是 `reader-artifacts` 每次放入整个任务登记记录，包括输入、坐标约定、运行回执与验证记录。以请求 10 为例，紧凑序列化后的该项达 **132,258 字符 / 56,574 估算 token**；整个可变状态尾部为 56,984 token。尾部不写入追加历史，下一次被新增的工具交互顶替；即使登记记录不再变化，这部分也无法成为下一轮相同前缀。它还占据压缩目标，导致保留下来的历史很少、很快再次触发压缩。

run3 去图 42 次、历史重留图片 22 次；run4 去图 44 次、历史重留图片 2 次。去图全部伴随 token 阈值压缩，没有发现无压缩时独立删除旧图改写前缀的情况。`retrieve_image` 事件原因全部为 `retained history`：已有图片重新出现在保留历史中，不能据此声称模型主动调用了取回工具。逐次表和 JSON 把这些事件与真正的首差位置分开记录。

### 实际缓存与等待

| 任务 | 已报告总输入 token | 缓存读取 token | 读取 / 总输入 |
|---|---:|---:|---:|
| run3 调度员 | 3,663,558 | 637,440 | 17.40% |
| run3 平面首次 | 434,755 | 263,872 | 60.69% |
| run3 平面返工 | 136,789 | 58,432 | 42.72% |
| run3 立面 S / E / N / W | 128,848 / 102,534 / 88,033 / 113,666 | 47,104 / 55,296 / 30,016 / 71,744 | 36.56% / 53.93% / 34.10% / 63.12% |
| run4 调度员 | 121,193 | 19,840 | 16.37% |
| run4 平面首次 | 2,096,077 | 1,444,672 | 68.92% |

run3 调度员含输出的总消耗为 3,713,813 token；上表分母仅为输入，包含未命中输入、缓存读取、缓存写入，避免混用两个口径。其余任务的用量及 run4 未响应项见逐次表。

run3 调度员请求 4 距前次响应 **798.482 秒（13.31 分钟）**，距前次请求 823.626 秒（13.73 分钟），缓存读取为 0。run4 请求 5 相应间隔为 2,311.156 秒（38.52 分钟），也是 0。与等待后缓存失效的解释相容，但没有服务端淘汰记录或对照实验，**不能把过期原因或具体 TTL 当作已证事实**。

两组所有非零缓存读取数的最大公约数均为 **64**，观察到 7,616、32,768、65,536，也有 20,032、33,472 等非二次幂。可确认报告值呈 64 token 粒度，不能仅凭此断言服务端物理缓存块就是 64。

所有已存请求均有两个 `{"type":"ephemeral"}` 标记：系统部分和最新消息块。最新标记逐轮移动，因此原始 wire 的首次差异可能只是标记；分析另外记录这一原始差异。非零命中、稳定前缀下的零命中均存在，缺少有/无标记对照，**现有记录无法判定标记是否发挥作用**。本包保留原有标记位置，不把前缀复用估算当作服务端命中保证。

## B. 所选策略

1. 调度员保留原默认 **150,000 token 压缩触发阈值**与命令行覆盖；压缩目标从阈值的 60% 改为 **30%**，留出足够追加空间。
2. 调度员仅在发给模型的 `reader-artifacts` 尾部保留 `task_id / role_id / target / status / artifact / reason`，即任务、目标、状态、精确交付引用和失败原因。上述请求 10 的整个状态尾部从 **56,984 → 1,955** 估算 token。完整登记记录、证据来源、修订号仍保存于检查点；既有 `role_state`、`read_role_artifact` 可以取回全量记录和交付证据。
3. 平面和立面读图员保持原 **100,000 / 60%** 策略。run3 立面没有压缩；run4 平面虽然因业务死结运行 40 次、压缩 5 次，相同前缀占比仍有 81.54%。缺少提高其阈值的收益证据。

公共 ContextPolicy 只新增默认关闭的 `state_item_fields`，空值不进入序列化配置，保持旧检查点配置比较与单模型行为。投影只处理指定键的字典列表；不符合形状、没有任何指定字段的条目保留原值，避免未知记录被清空。完整状态不被修改。角色策略集中在新增 `runtime_roles/context_policy.py`，接入只改 entry 的策略构造和 session 的 run_reader 策略构造及必要导入。

曾测试仅扩大到 200,000 阈值、压缩到 20%：[deeper_candidate.json](deeper_candidate.json)。run3 调度员前缀占比只达 52.34%，平均请求量反增 25.48%；平面请求也显著变大。因此未采用单纯扩大窗口的办法。

## C. 离线量化

### 算法与边界

先验证归档请求的 wire SHA256，再按 task_id 读取每次请求前的完整历史与状态检查点，依次重放生产 ContextManager 与 Anthropic 消息转换。每个策略独立保留自己的压缩和图片决定，不在每次请求时重置压缩进度。旧策略须逐次与实际请求正文完全一致，否则脚本立即失败；同时核验当前模型估算档案与归档档案完全一致。

按工具定义、系统内容、消息内容顺序累计完全相同的内容块，首次不同块不计部分收益。仅在语义前缀比较时排除移动的 cache_control；原始差异另存。采用现有文字/图片模型档案估算，不声称复现供应商 tokenizer 或实际命中。用量按整批输入加权：相同前缀估算总和 / 请求输入估算总和。

按验收原文的主指标，只排除距上一响应超过 300 秒的首请求，保留最初冷启动请求并将其前缀记为 0；300 秒只是分析排除条件，不是服务端 TTL 结论。另列排除冷启动、仅比较有前序请求的口径，以及不排除任何请求的口径。前期记录的 39.90% → 83.54% 属于第二种，最终主指标为 39.82% → 83.34%。压缩触发使用生产逻辑消息估算，表格使用原生请求正文估算，两者数字不能混为阈值上限。

反事实只替换请求投影，固定原历史中的模型回答与工具结果；不预测模型看到较少即时历史后会不会增加取回动作。真实效果须合并后由 Opus 另行核对。

| 调度员指标 | run3 改前 | run3 改后 | run4 改前 | run4 改后 |
|---|---:|---:|---:|---:|
| 请求数 | 41 | 41 | 7 | 7 |
| **主指标：仅排长等后首请求，保留冷启动** | 39.82% | **83.34%** | 75.82% | **79.31%** |
| 另排冷启动，仅比较有前序请求 | 39.90% | 83.54% | 82.78% | 86.96% |
| 全请求占比，均不排除 | 39.47% | 82.68% | 74.33% | 78.54% |
| 压缩次数 | 7 | **4** | 0 | 0 |
| 平均输入估算 token | 122,972.07 | **105,231.39** | 21,332.00 | **20,188.57** |
| 最大输入估算 token | 190,753 | **172,413** | 29,769 | **27,101** |
| 输入估算合计 token | 5,041,855 | 4,314,487 | 149,324 | 141,320 |

run3 平均输入减少 14.43%，最大输入为旧值的 0.904 倍；run4 最大为 0.910 倍。两组最大请求量均低于 1.5 倍上限。按 Opus 补充说明，以 run3 调度员为主样本，已达到 80% 目标。run4 调度员仅 7 次请求、运行被业务问题提前终止，主指标提高 3.49 个百分点至 79.31%，没有达到 80%；不为补足短样本数字再改策略，也不把排除冷启动后的 86.96% 冒充主指标。

所有读图员改前/改后请求 **104/104 逐字节相同**，包括 run4 无响应的末次请求。按保留冷启动的主口径，run3 平面首次/返工的前缀占比为 70.33% / 65.53%；立面为 69.89%–80.10%。run4 平面首次为 81.54%，完整运行的三个立面为 74.78%–81.51%。立面未发生压缩，短序列的冷启动和新增内容比例影响较大，提高阈值不能解决这一点。被权限错误中断的西立面只有 2 次请求，返工只有 1 次，不据此扩大窗口。各任务三种口径、平均/最大值和逐次数字见[完整表](request_comparison.md)。

## D. 信息与恢复

新增三项行为检查覆盖：默认策略与基准代码的配置/连续原生请求字节一致（含图片、压缩与旧检查点加载）；角色压缩后完整登记记录、原始交付及图片仍可精确取回；新检查点保存/加载后投影与完整历史一致；读图员默认策略和显式覆盖保持。新策略复用现有按完整工具交互组压缩的逻辑，不拆调用与结果。

两组 152 次请求的改前/改后投影还逐次断言：投影后的完整 state（含值、来源、修订）与原检查点完全相同。旧策略投影的 152/152 wire 匹配证明回放未静默缺历史。既有工具配对、上下文来源、原图取回和中断续接检查纳入 E。跨 Agent 版本的旧运行不做静默迁移；新策略自身的检查点恢复按现有版本约束验证。

## E. 检查与复现

**30 个检查文件、283 个不同用例，最终全部有通过记录，0 项未解决失败、0 项跳过。** 复用相同代码下已通过的检查，未再重跑整批。明细见 [checks.json](checks.json)，原始记录为 [首轮](checks.xml)、[临时登记复核](registered_checks.xml)、[剩余失败项复核](final_recheck.xml)。

- 首轮：271 通过、12 失败，耗时 3,051 秒。11 项由 Agent 文件指纹校验拒绝，1 项由原有 900 秒时间保护停止。
- 临时登记复核：21 项通过，耗时 1,476 秒，包括 sm21/sm24/sm25 真实本地工具贯通、三处分工中断恢复、三例单模型首请求字节一致、真实工具 75 步历史回放。
- 剩余两项：2 项通过，耗时 504 秒；至此 11 项登记失败全部复核通过。时间保护用例在其他批次结束后独立完成长回放，调用阶段 494.47 秒，**原 900 秒保护和所有断言均未改**。

时间保护失败发生于两批检查并行期间：原记录在第 74 次响应后以 `time_budget_exhausted` 停止（`event-000942`），不属于源状态/恢复断言不一致。复核降低同时运行的检查量后通过。保留首轮失败记录，避免把分批通过写成首轮全绿。

首轮按正式登记表执行，受保护的真实入口正确拒绝 entry/session 文件指纹变化。没有放宽断言或改正式登记表；另复制临时登记表，登记本地代码和新策略文件后复核。原工具目录哈希保持，由真实 frozen-MCP 检查再次验证。临时登记证据见 [test_registry_manifest.json](test_registry_manifest.json)。

在工作树根目录复现离线回放：

```powershell
. .\scripts\activate_windows.ps1
python -u AI_agent/logs/experiments/2026-10-07_runtime_cache_b1/analyze.py `
  AI_agent/archive/local_backup/b1/runs/sm24_run3 `
  AI_agent/archive/local_backup/b1/runs/sm24_run4 --role-policy `
  --output AI_agent/logs/experiments/2026-10-07_runtime_cache_b1/comparison.json
```

检查使用本工作树 `.venv`、pytest `-n 2`，临时目录位于 `AI_agent/archive/local_backup/b1/pytest`。本包未调用在线模型服务，HTTP adapter 检查只用模拟/本地服务；贯通检查执行真实本地 MCP 工具，模型回答为脚本固定输入，不代表冷启动建模质量。

未合并登记前，检查环境准备与范围如下（在工作树根目录执行；只写临时登记副本）：

```powershell
. .\scripts\activate_windows.ps1
@'
import json, shutil
from pathlib import Path
from src.agent_runtime.agent_registry import register_agent_version
root = Path.cwd()
target = root / 'AI_agent/archive/local_backup/b1/registry/agent_versions.json'
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(root / 'src/agent_runtime/agent_versions.json', target)
registry = json.loads(target.read_bytes())
catalogs = registry['versions'][registry['current_version']]['tool_catalog_sha256']
register_agent_version(root, 't1-20261007-b1-offline', registry_path=target,
    catalog_hashes=catalogs,
    additional_files={'src/agent/runtime_roles/context_policy.py': 'guidance'})
'@ | python -
$env:BIM_AGENT_REGISTRY_PATH = (Resolve-Path 'AI_agent/archive/local_backup/b1/registry/agent_versions.json').Path
$env:STAGE2_FROZEN_REPLAY_OUT = Join-Path (Get-Location).Path 'AI_agent/archive/local_backup/b1/frozen-replay'
$taskChecks = @(rg -l 'src\.agent_runtime\.context|ContextPolicy' tests -g 'test_*.py') + `
  @(Get-ChildItem tests -Filter 'test_role*.py' | ForEach-Object { 'tests/' + $_.Name }) + `
  @('tests/test_runtime_compact_evidence.py', 'tests/test_runtime_stage2_integration.py',
    'tests/test_runtime_recovery_edges.py', 'tests/test_runtime_frozen_long_task.py',
    'tests/test_runtime_a2r_storage.py', 'tests/test_runtime_anthropic.py')
$taskChecks = $taskChecks | ForEach-Object { $_.Replace('\', '/') } | Sort-Object -Unique
New-Item -ItemType Directory -Force 'AI_agent/archive/local_backup/b1/pytest' | Out-Null
python -m pytest -n 2 @taskChecks `
  --basetemp AI_agent/archive/local_backup/b1/pytest/reproduce `
  -o cache_dir=AI_agent/archive/local_backup/b1/pytest/cache
```

工具目录复用正式登记的四组哈希，真实工具检查不允许目录内容变化。正式登记合并完成后可直接用正式登记检查，无需上述临时副本。

## F. 交付与合并建议

新增/修改文本均为 LF，差异核对通过；未提交、未创建分支或修改 Git 配置。Opus 提供的 `runs/` 原样保留，两个 events.jsonl 哈希与分析输入一致。

**清理未完成：自动审批拒绝删除临时目录。** 先前的批量命令被 `blocked by policy` 拒绝；随后只读核实所有目标均为本工作树内的真实目录，再缩小到单个固定绝对路径 `AI_agent/archive/local_backup/b1/registry`，仍被同一理由拒绝。工具没有提供更详细原因；没有换解释器或其他接口绕过。

以下本包临时产物仍在磁盘，均未纳入提交建议，供 Opus 在允许清理的执行环境中处理：

- `AI_agent/archive/local_backup/b1/pytest/`：三批检查及新增检查的临时运行。
- `AI_agent/archive/local_backup/b1/registry/`：临时 Agent 登记副本。
- `AI_agent/archive/local_backup/b1/frozen-replay/`：真实工具 75 步回放。
- `.pytest_cache/`：首次检查创建的缓存。
- `AI_agent/logs/experiments/2026-10-07_runtime_cache_b1/__pycache__/`：分析脚本缓存。

`AI_agent/archive/local_backup/b1/runs/` 是 Opus 拷入的输入，必须继续保留。清理约束与工具拒绝记录见 [checks.json](checks.json) 的 `cleanup`。

建议由 Opus 审核后分两组提交：

1. 公共可选投影项、角色策略接入、三项行为检查（4 个生产文件 + 1 个测试文件）。
2. 本实验目录的诊断脚本、逐次 JSON/表格、策略选择及检查证据。

与 D1h 合并时只组合两个入口的策略构造/导入；其余实现未触及。正式 Agent 版本由 Opus 合并后统一重新登记，需加入新文件 `guidance:src/agent/runtime_roles/context_policy.py`。主线 store.py 权限重试保持独立。后续真实核对重点：调度员的实际缓存读取、请求总量、按需取回动作和建模结果质量；本包不新增整案运行授权。
