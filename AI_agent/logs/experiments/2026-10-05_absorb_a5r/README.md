# A5-R：共用输入准备与评价侧约定差

状态：开发与离线验证中，尚未完成验收。派工：Opus 5.5；执行：Astra。

## 范围与边界

- 按 [派工单](brief.md) 和 [验收 A–C](../../../project/unified_agent_acceptance.md#吸收包第五批-a5-r两底座共用输入准备评价侧约定差10-05-派出astra) 执行。
- 只在 `dev/astra-a5r-20261005` 小步提交，不合入 main、不推送；不修改 A5-T 所属工具目录、指引、命名与版本登记。
- 全程离线，模型请求为 0；不读取或打印凭据。历史原始证据和参照保持不变。

## 计划与进度

1. A：抽出两入口共用的输入准备函数，统一评分所需运行目录；离线验证三例输入逐字节相同、Claude Code 启动到模型进程边界，以及历史运行兼容。
2. B：按既定类别与容差区分约定差，分别输出规整前读数与交付稿质量。重评 10-04 sm24、sm25、两次 27B 与 10-01 亲做三例，逐项保存改记与保留问题。
3. C：运行指定阶段及所有直接引用改动模块的检查，显式使用本树 `PYTHONPATH`、`pytest -n 2 -s` 和树内临时目录；清理解包临时证据。

已完成：读取规定上下文与交接；共用输入准备、旧运行直接评分、三类约定差及两份独立报告已实现。七份历史运行已按压缩包及逐文件哈希核验解包，正在重评并保存原始输入不变证据。新增局部检查最终 26/26 通过，涵盖拆并房、悬空开口/连通和读数与交付分离反例。

### 集成依赖（03:36 UTC）

`run_bim_agent.py` 被 `agent_versions.json` 按整文件哈希登记。提取其 `run_experiment` 的输入准备必然改变文件哈希，普通入口会正确拒绝使用旧登记。派工单将登记文件归 A5-T，本分支尚未修改它；已请求协调本分支的临时新版本登记，最终须由 Opus 在 A5-R/A5-T 合并后登记共同版本。不能用跳过哈希检查来声称正式入口通过。

## 验证与交付

首轮新增检查：`PYTHONPATH="$PWD" TMPDIR=<本树 .tmp> pytest -n 2 -s tests/test_bim_input_preparation.py tests/test_bim_evaluation_conventions.py --basetemp=<本树 .tmp/pytest-unit>`，21 通过；日志在 `validation/unit.log` / `unit.xml`。三例准备核对在同一时刻和同一范围下，除明确的 provider 路由字段外所有清单值相同、图片字节相同；同选项调用共用函数时 `inputs.json` 字节相同。另一次包含全部新反例的检查 26 通过，见 `validation/unit-final.log` / `unit-final.xml`。

初稿提交：`76c4797a`。后续记录检查、证据、提交和未完成项；本包无模型请求。

## A：两套入口共用输入

`src/agent/bim_inputs.py::prepare_bim_inputs` 是两入口唯一的清单生成与输入冻结实现。保留原 Claude Code 的 PNG、原生网格、用户声明、候选恢复和失败平面恢复行为；时间、楼层范围、输入内容及实现哈希不再各写一份。Claude Code 的运行根目录和新底座的 `bim/` 都是同一种 BIM 工作目录；底座事件、账目等仍在外层。

新底座结束时直接保存 `bim/summary.json`。评价器接受两种入口的运行根目录或 BIM 目录；老底座运行缺少 summary 时直接读已有终态 receipt，不复制目录、不补写 `inputs.json`。旧的清单字段缺项不再阻挡评分。没有修改工具、指引或 `run_experiment` 以外的 Claude Code 入口代码，见 [范围核对](scope_audit.json)。

## B：评价口径与七份重评

约定规则只在评价侧生效，以原参照和独立原图观测的 SHA-256 锁定；目标线来自既有参照线，不能由候选或平均值决定。保留原比较 2 cm 残余误差口径；地坪必须是已记录的首层 0.2 m 门槛、顶标高不变且外门高度能佐证；单线规则只允许记录的半墙厚转换；跨层对齐限相关墙厚内的既有目标线。拆并房、多漏空间/开口、改变门窗挂接或连通、超限位移另行保留，不参与降级。

每份运行同时保存 `reading_readings.json`（所有已保存草稿、读数、原值和哈希，失败及损坏草稿亦保留）与 `delivery_quality.json`（各候选质量及完整子报告链接）。有原编译记录时，对未施加约定差的读数另做严格分区比较。历史运行没有独立的规整前后账本，报告明确写为“未单独记录”，不会根据最后模型反推“模型已经读准”。报告是所列几何、原图开口位置/挂接/连通和外部高度的诊断；内部高度、竖向空洞等没有据此获验收。

[汇总及逐项差异](reevaluation.json)包含每项改记依据、原严重项、仍保留的严重项、原图位置/挂接/连通读数，以及所有被保护文件重评前后的哈希。压缩包与逐文件核验见 [archive_verification.json](archive_verification.json)。本次无重新生成。

| 历史交付 | 原严格分区 → 约定后分区 | 改记为约定差 | 交付诊断仍保留 |
|---|---|---|---|
| [节点 sm24，新底座](evaluation/sm24_runtime_anthropic/index.html)，candidate_03 | severe → severe | 无 | 7 项边界差、内部隔墙差；开口位置 18/21，3 项位置偏差 |
| [节点 sm25，新底座](evaluation/sm25_runtime_anthropic/index.html)，candidate_07 | severe → severe | 无 | 首层 14 项标高差、29 项边界差、走廊错拆；额外门/窗；位置 48/61、挂接 58/61、门连通 28/30；外部高度 33/34 |
| [27B 首次](evaluation/sm24_qwen27b_paratera/index.html)，candidate_06 | minor → minor | 无 | 原有微小分区差；开口位置 20/21，1 项位置偏差，因此交付诊断仍 severe |
| [27B A2 后](evaluation/sm24_qwen27b_after_a2/index.html)，candidate_01 | severe → severe | 无 | 7 项边界差、内部隔墙差、额外外窗；已有参照开口 21/21 对位不抵消多窗 |
| [Opus 10-01 sm21](evaluation/opus_dev_sm21/index.html)，candidate_04 | pass → pass | 无 | 29/29 开口位置/挂接、14/14 门连通、17/17 外部高度；本报告范围内 pass |
| [Opus 10-01 sm24](evaluation/opus_dev_sm24/index.html)，candidate_02 | severe → pass | 8 个首层空间的 0.2 m 地坪差 | 21/21 开口位置/挂接、10/10 门连通、14/14 外部高度；本报告范围内 pass |
| [Opus 10-01 sm25](evaluation/opus_dev_sm25/index.html)，candidate_04 | severe → minor | 14 个首层地坪差；6 个空间边界半墙厚差（对应两层共 4 段墙）；2 个被这些差异完全覆盖的楼层隔墙汇总项 | 12 项原有微小分区差；61/61 位置/挂接、30/30 门连通、34/34 外部高度；本报告范围内 minor |

七份最终稿均没有实际采用办公室跨层对齐，因此本次没有历史跨层差异被改记。该规则用保存的 sm25 复制数据做离线正反例验证：只将首层既有办公室隔墙对齐至二层既有 16.06 m 线；原历史模型及其 6 cm 接触细条保持原样。本包不把它称为已规整完成。

## C：检查进度

完整范围共 82 个测试文件：保留阶段 0–3、R1–R3、C1、A1-R～A4-R，加入直接引用两入口/新评价模块的文件，以及测试辅助模块的传递引用。清单见 `validation/selected_tests.json`；正在按 `validate.py all` 执行。正式登记依赖仍未解决，结果将按实际失败原因记录。

已用现有登记接口在本报告目录生成 **独立的登记建议文件**，核对四种真实本地 MCP 目录；没有改生产登记，也没有关闭哈希校验。三例核对已通过，见 [runner_parity.json](runner_parity.json)：每例 Claude Code 恰好到达一次被拦截的进程启动边界，未启动模型；任务、指引、工具目录和三份 8.6–8.8 KB 完整输入清单（同范围、同钟表，仅 provider 路由不同）均逐字节一致，新底座均产出可直接评分的 summary。核对脚本只在自己的进程内显式选择该建议登记，结果明确是**以建议登记为条件**，当前默认入口未因此放行。默认校验阻挡的唯一文件为 `run_bim_agent.py`，证据在 `validation/default_registration_check.json`。

为了在不越权修改登记的前提下把集成改动验证完，另备离线 pytest 配置 `proposed_registry_checks.py`，把登记选择指向该建议文件；原校验函数、四种真实工具目录、历史版本和文件篡改断言全部保留。登记复制测试仅改其 JSON 输入来源。将单独记录此配置下的补验，原默认登记的失败结果不覆盖。75 步历史真实工具重放已在此条件下启动，模型响应均为录制的本地脚本。

提交：`76c4797a` 初稿；`0f1f4bb0` 共用输入准备与对应检查；`d8747fc4` 约定差、原读数/交付分离及反例。未合入、未推送。
