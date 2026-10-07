# Q1b 执行报告

- 执行：Astra；工作树 `D:\EnergyPlus-Agent-worktrees\q1b`，分支 `dev/astra-q1b-20261008`，基准 `d76d33e6`。
- 范围：domain 的 BIM rules、kernel、平面试建反馈与相关 guidance；共用编译路径影响单模型和分工模式。runtime、版本登记和全局项目文档不改。
- 已完整读取会话入口、产品目标、当前任务、工作方式、名词规范及当前任务指向的最新交接，并核对 Git 状态、工作树与近期提交。
- 本包依派工单实现编译前小偏差修整、墨线对齐原子更新与失败回退、可照抄的诊断，并保存历史稿离线回放。
- 只在本树写入；外部运行只读取派工单指定的既有证据，复制后处理。不启动或停止整案，不改 `runs-q`。
- work model 请求：0（Paratera 0、DeepSeek 0）。按派工单内部分工授权，使用三个 GPT-5.6 Sol（high）dev model 子代理处理墨线对齐、诊断/指引、离线证据；这是边界清楚的实现与复核任务，按项目偏好优先 5.6，由 Astra 集成验收。
- 检查计划：本包行为检查，指定的 `test_bim_*`、`test_plan_*`、`test_role_*` 与三例离线贯通；`-n 2 -p no:cacheprovider`，临时目录在本树已忽略位置，交付前删除。不跑全量。
- Git 不提交；完成时补实现结论、27 份失败稿逐项表、旧稿保持情况、指引字数、检查及建议提交分组。

## 实施与验证

实现、最终回放和指定范围检查已完成，交 Opus 复核。27 份原失败稿恢复 3 份；指定检查 748 通过、1 个未改动的 Windows 进程终止检查失败。未宣称整案质量恢复或全部检查通过。

1. 公共编译前修整：每轴容差为 `min(0.30m, max(0.05m, 3 × 米/像素))`。单条连接的总移动同样不超过 0.30m；特别粗的图像以 0.30m 上限优先。几何像素统一到九位小数，逆标定回写遵循同一精度。修端点、轮廓重复段、共线重叠、零长度段和整扇开口的法向投影；不裁短门窗、不增加墙、不删除空间种子。失败整稿回滚，原稿可编译时还比较房间和开口连接关系。沿用 Q1 的后续规整与硬约束，旧 Q1 显式窄条合并另有其审计，不混称为本次接头修整。
2. 墨线对齐：附着开口与交接端点使用同一个目标坐标直接赋值。分工入口保存对齐前数值稿，对齐稿失败而原稿预检可通过时回退。预检不提前消耗修整，实际更改由公共入口统一执行和记录。
3. 诊断：保留原声明编号、端点、原墙段和精确修复交点；如果原段够不到或修改会翻越相邻点，说明需要同步修改而不提供危险的单点坐标。双种子错误给出原像素坐标与两点之间核查区域，不推断生成缺墙。试修失败返回剩余错误并说明全部尝试已回滚。
4. 回放：只读冻结了 27 份本次失败稿、11 份旧试建稿、4 份旧交付层稿、10 份三例对照层稿、15 份 Q1 历史规整输入及 7 份历史 reader 输入。最终 [27 份逐稿表](failure_trials.md) 和 [机器报告](final_replay.json) 分别列出严格编译与公共 Q1 入口结果。原任务 `3946ca64` 的 `draft_010/011/014` 从失败恢复为两项均通过；其余 24 份仍失败并保留原稿。通过的三份修复了 `657.686 → 657.6856` 像素的开口宿主差，其中 011 还修复同量级墙端；没有增删空间种子或合并门窗。剩余首错为悬线/未闭合 12、同室双种子 9、无完整宿主 1、仅一个内部宿主 1、隔墙在外轮廓外 1；其中悬线包含超出本包接头容差或不适合沿墙延伸的情形，不能一概称为小数误差或实质缺墙。
5. 指引：替换原接头措辞，没有追加独立流程；计数见 [guidance_counts.json](guidance_counts.json)。字符数包含空白，英文单词以空白分词。

| 指引 | 字符数前 → 后 | 空白分词前 → 后 |
|---|---:|---:|
| 分工平面读图员 | 9145 → 9237 | 1184 → 1199 |
| 单模型 DRAWING_METHOD | 4149 → 4333 | 659 → 688 |
| 单模型 plan_partition reference | 8768 → 8898 | 1134 → 1154 |

## 验证过程与边界

- `uv sync --frozen --offline --python 3.12` 被主机 uv 缓存目录的读取权限阻断；未绕过。已有本树 `.venv` 可用，经 `scripts/activate_windows.ps1` 激活，`src.agent.__file__` 确认指向本树。
- 首次范围检查运行 747 条：723 passed / 24 failed。失败包括尚未正式登记的新代码哈希、旧指引字节断言、实际需修正的错误正文覆盖问题、一个过小的测试图像，以及 Windows 进程终止超时。保留原始 XML，不把初次结果计入最终通过数。
- 离线测试使用 [prepare_test_registry.py](prepare_test_registry.py) 生成本树忽略目录中的临时哈希快照；正式 `src/agent_runtime/agent_versions.json` 始终未改。它不是正式版本发布，编号由 Opus 合并后统一登记。
- 首轮六位像素回写曾让三个 Q1 历史组产生约 1e-8m 跨层数值残差，现改九位并复核；没有放宽严格编译器或 Q1 硬约束。
- Windows `terminate_subscription` 测试的函数与基准提交完全相同，见 [process_test_boundary.json](process_test_boundary.json)。两次范围检查均在 `process.wait(timeout=15)` 超时；这是仍未通过的边界，未定位到 Windows 拒绝终止的具体原因，本包没有改进程控制或运行中的 GLM。

### 最终有效结果

- 79 个指定文件、749 条检查：**748 passed / 1 failed，805.41s**。唯一失败为上面的 Windows 进程终止检查；完整 [XML](pytest_final.xml) 与 [摘要](verification_summary.json) 已保留。新增行为、原有公共 BIM/plan/role 路径均在这个范围内。
- sm21、sm24、sm25 的真实冻结 MCP 离线贯通 **3/3 通过**；三例提交契约 **3/3 通过**；四个恢复边界 **4/4 通过**。这些使用脚本化模型响应，只验证工具贯通和恢复，不代表 work model 识图质量。
- 最终代码与离线测试哈希快照一致，正式登记表未变；`git diff --check` 通过，全部本轮写入文本为 LF；[最终核对](final_verification.json) 固定分支和基准提交。
- 交付前已用 Python `shutil.rmtree` 删除且回读确认本轮 `pytest` 临时目录不存在，移除 21,132 文件、逻辑大小 628,417,234 字节、318 个仅指向该临时目录内部的链接；没有选择其他目录。见 [清理记录](cleanup.json)。

复现检查时，先生成临时测试快照，避免把未正式登记的开发代码当成正式版本：

```powershell
. .\scripts\activate_windows.ps1
python AI_agent/logs/experiments/2026-10-08_quality_q1b/prepare_test_registry.py
$env:BIM_AGENT_REGISTRY_PATH = Join-Path (Get-Location) 'AI_agent\archive\local_backup\q1b\test_registry\agent_versions.json'
$q1bTests = @(rg --files tests -g 'test_bim_*.py' -g 'test_plan_*.py' -g 'test_role_*.py')
python -m pytest @q1bTests -n 2 -p no:cacheprovider --basetemp AI_agent/archive/local_backup/q1b/pytest --junitxml AI_agent/logs/experiments/2026-10-08_quality_q1b/pytest_final.xml -q
```

## 历史回放结果

全部 74 份的严格编译通过数从 39 增至 42；原先可编译稿新增失败为 0，编译几何变化为 0。失败稿的试修若不能整体通过就原样回滚，不能把尝试次数记作实际修复。

| 对照 | 编译前 → 后 | 结论 |
|---|---:|---|
| `merged/sm25_role_n1` 旧试建 11 份 | 3 → 3 | 8 份原失败仍失败，原通过稿不变 |
| 同组旧交付层稿 4 份 | 4 → 4 | 几何不变 |
| 三例对照交付层稿 10 份 | 10 → 10 | 几何不变 |
| Q1 历史规整输入 15 份 | 15 → 15 | 编译前修整不改变这些原稿 |
| Q1 历史 reader 输入 7 份 | 7 → 7 | 编译前修整不改变这些原稿 |

按原分组继续调用 Q1：20/20 组通过，其中有原变化数基准的 15 组计数逐项一致；5 个 reader 组另外重放完整墨线/尺寸路径，7 层结果与原 Q1 记录逐项 JSON 哈希一致。墨线 7/7 可交付；有尺寸 fixture 的 5 层仍是 4 可交付、1 拒绝，与原记录一致，没有把原有的合理拒绝改成通过。

冻结输入已装入 [replay_inputs.zip](replay_inputs.zip)，共 121 个物理文件（清单含 123 个逻辑引用），原始 4,724,051 字节、压缩后 1,530,848 字节，逐个解压内容与源快照字节校验一致。这样收回工作树后仍能重放，不依赖运行中目录。校验见 [replay_archive.json](replay_archive.json)。从工作树根目录恢复并复核：

```powershell
. .\scripts\activate_windows.ps1
python -m zipfile -e AI_agent/logs/experiments/2026-10-08_quality_q1b/replay_inputs.zip AI_agent/archive/local_backup/q1b
python AI_agent/logs/experiments/2026-10-08_quality_q1b/replay_q1b.py --verify-snapshot
```

## 建议提交分组（由 Opus 复核执行）

1. `domain · BIM rules/kernel/tools`：公共接头修整、精度、依据转移、事务回滚、公共入口审计及对应 `test_plan_regularization` 行为检查；影响单模型和分工。
2. `domain · kernel/roles/tools`：原子墨线移动、分工预检回退、对齐前原稿证据、可照抄诊断，以及对应 reader/诊断检查；共享移动函数也供尺寸对齐使用。
3. `domain · guidance` 与执行证据：两种模式指引替换、授权文本差异与 parity 检查、历史回放脚本/快照清单/报告、最终验收记录。未改 methods 或 runtime。

这些分组建议在一起合入后由 Opus 统一正式登记。Astra 没有提交、推送或修改任何 `.git` 文件，也没有改全局目标、路线、当前交接；没有启动或停止 `runs-q` 整案。
