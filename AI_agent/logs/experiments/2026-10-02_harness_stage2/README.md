# 阶段 2：长任务与恢复交付

工作树 `.worktrees/astra-stage2`，分支 `dev/astra-stage2-20261002`，派工起点 `c5926024`。主体实现和离线验证由 Astra 负责，正式验收由 Opus 决定。本分支不合入、不推送 main；历史实验只读。

实现说明见[长任务设计](../../../design/runtime_long_tasks.md)。验收依据是[阶段 2 A–H](../../../project/unified_agent_acceptance.md#阶段-2长任务与恢复)，本目录没有修改验收口径或派工单。

## 第一次验收后的补充

首次验收要求补足 B 在真实长任务上的证据。本次补充见[补充报告](supplement_report.md)，正式结论仍由 Opus 给出。原交付报告和三份旧归档保留；原两个长故障样例属于隔离写模拟，B 的真实长任务证明以本补充为准。

- [真实冻结工具归档](evidence_frozen_run99.compact.tar.xz)：按历史原参数顺序执行75次工具调用，模型响应为脚本；完整保留事件、真实产物、附件和请求。1,542,988字节，78种图片均按仓库来源及哈希引用，没有重复嵌入。
- [独立核验](frozen_replay_audit.json)：26个view_id、3个claim、5次候选更新、真实报告未决项和待办、72次压缩及3次精确取图。
- 状态清单：[20步](state_step_20.json)、[40步](state_step_40.json)、[75步](state_step_75.json)；[逐步状态大小](state_growth.csv)；[76份请求预算](request_budgets.csv)。
- [逐调用差异与7次历史错误](replay_differences.md)、[本次测试与用量](supplement_validation.json)、[补充文件及提交清单](supplement_changes.json)。

`verify_delivery.py` 现在同时核验三份旧归档和新归档。新格式由 `compact_evidence.read_archive()` 无磁盘解包地恢复原文件，再逐文件验证哈希；依赖仓库中原有的run99图片和压缩流，不能脱离这些来源单独验证。旧冻结入口归档的 `code_files_matching_current_worktree=false` 是因为本次修正了两个建筑适配文件，旧归档原字节未动；新75步归档该项为true。

真实冻结入口测试已自行使用工作树内临时目录，不再要求调用者把pytest的basetemp设在树内才能通过。下面复验命令仍将全部测试临时文件限制在本工作树，以遵守本次派工范围。

```bash
mkdir -p .stage2-followup-check/tmp
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.stage2-followup-check/tmp" \
  python -m pytest -q -n 0 -s tests/test_runtime_frozen_long_task.py \
  tests/test_runtime_compact_evidence.py \
  --basetemp="$PWD/.stage2-followup-check/tests" \
  -o cache_dir="$PWD/.stage2-followup-check/cache"
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 \
  python AI_agent/logs/experiments/2026-10-02_harness_stage2/verify_delivery.py
```

须在本工作树根目录执行，并显式设置 `PYTHONPATH`；共享安装可能指向另一工作树。测试默认自动清理真实重放目录；如需保留，可设置 `STAGE2_FROZEN_REPLAY_OUT` 为本工作树内尚不存在的目录。脚本中的20 token/回包属于测试用量，不能当作服务商token或账单。

## 实现

- 完整历史与当前状态、活动请求分开保存；去重、旧摘要失效、图片取回都有可追溯事件。
- 图片按原 view_id 与哈希取回，最终请求按字节哈希去重；固定证据与容量冲突时明确停止。
- 用户要求、约束原文来源、依据、源 BIM、未决项、待办、尺寸和对象编号保持机器可读。摘要不能把推断改成事实，不能成为几何的唯一来源。
- 主任务、摘要、重试与子任务预算预留共用根账本；子任务实际运行属于阶段 3。缺失用量不归零，费用估计不冒充账单。
- 事件式检查点、后缀回放、显式破尾修复；已记录成功的写不重复执行，未知写先查真实保存状态再安全停止。

## 证据入口

| 材料 | 内容 |
| --- | --- |
| [validation.json](validation.json) | 实际测试命令、数量、结果、历史失败的解释、外部调用量 |
| [pytest_final.log](pytest_final.log)、[JUnit](pytest_final.xml) | 原 132 项加 42 项新增短检查，174 passed |
| [长夹具说明](long_fixture_report.md)、[源清单](source_manifest.json) | run99 的 75 组调用/回包、67 个原图片块及改编边界 |
| [故障报告](fault_report.md) | 最终长任务各注入点、预期、实测结果与写次数 |
| [delivery_audit.json](delivery_audit.json) | 冻结范围、归档事件契约、全部本地哈希引用、实际请求和图片校验 |
| [evidence_archives.json](evidence_archives.json) | 完整长任务和未知写归档的逐文件哈希、事件数及写入账 |
| [evidence_frozen_entry.tar.gz](evidence_frozen_entry.tar.gz) | 真实冻结工具的小型离线闭环，含事件、附件、源 BIM、查看文件和六层版本 |
| [evidence_complete75.tar.gz](evidence_complete75.tar.gz) | 75 步中断恢复完成记录，完整事件、附件、检查点与隔离 BIM |
| [evidence_unknown_write.tar.gz](evidence_unknown_write.tar.gz) | 未知写保存状态检查及安全停止记录 |
| [交付报告](delivery_report.md) | A–H 自评、阶段 1 跟进、文件与提交、未决项、阶段 3 估算 |

长记录来自真实历史，但模型序列是脚本，token 数是明确标注的测试值；隔离后端映射历史写入，不代表重新生成了原建筑。真实冻结入口也是两房间的运输与恢复小夹具。本阶段没有新增整案实测。

## 独立复验

必须把 `PYTHONPATH` 显式指向本工作树，避免共享 editable 安装把导入解析到其他树。工具不读取凭据、不访问外部模型、不向归档内解包：

```bash
STAGE2_WORKTREE=/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage2
cd "$STAGE2_WORKTREE"
PYTHONPATH="$STAGE2_WORKTREE" PYTHONDONTWRITEBYTECODE=1 \
  python AI_agent/logs/experiments/2026-10-02_harness_stage2/verify_delivery.py
```

它核对冻结路径、日志契约、哈希附件、实际请求注入位置、图片字节、工具实际呈现和检查点历史；要求最终 `missing_archives` 为空。归档只有普通相对路径文件，不含锁文件或临时文件。工具会更新本目录的 `delivery_audit.json`。

运行测试须把 `TMPDIR` 和 `--basetemp` 放在本树内，且各并行执行者用独立目录。具体命令见 `validation.json`，不要把整个共享临时目录当作单次 pytest 的 basetemp。

## 仍然保留的边界

Paratera 0 次，DeepSeek 0 次，GLM 0 次；未读取 Paratera 凭据。服务的真实上下文上限、缓存、图片限制与当前价格未核实，本地策略不宣称代表这些服务规则。远端模型别名仍未核实为固定版本。

摘要是受约束的状态索引；任意长文本自由摘要没有开启。未知写没有自动幂等恢复，孤立预算预留没有自动释放；两者会明确停止。当前逐次日志前缀校验和每图决策记录有开销，性能优化留到后续。名词草案仍待用户确认，既有类型不改名。
