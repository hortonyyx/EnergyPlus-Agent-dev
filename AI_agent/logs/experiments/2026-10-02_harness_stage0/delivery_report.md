# Astra 阶段 0 交付报告（10-02）

原样保存 `codex exec` 最终回复；文中链接是工作树 `.worktrees/astra-stage0` 内的绝对路径，合入后对应仓库内同名相对路径。

阶段 0 已完成，交付在分支 `dev/astra-stage0-20261002`，共三笔提交。**86 项新增检查全部通过，工作树干净；未合入 main、未 push。** 冻结工具、几何内核、原有执行模块及项目计划/验收文件均未修改。

本次交付证明接口与离线约束成立；没有运行工作模型，也没有把样例通过当作整楼建模质量通过。正式验收结论交 Opus。

1. 已交付的接口

公共核心位于 [src/harness_contracts](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/src/harness_contracts)，建筑共用层位于 [src/agent/contracts](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/src/agent/contracts)。

| 接口文件 | 用途 |
|---|---|
| 核心 `refs.py` | 保存来源、文件哈希、原图与实际发送图片的对应。 |
| 核心 `events.py` | 记录最终请求、响应、五类思考信息、工具原始及所见返回、版本和生命周期。 |
| 核心 `roles.py` | 分离角色与模型绑定，通过白名单限制只读权限，推荐模型不自动成为回退模型。 |
| 核心 `budget.py` | 将主任务、子任务、摘要和重试计入同一份预留与结算账。 |
| 核心 `validation.py` | 校验事件顺序、恢复前状态读取、重试关系和重复写入。 |
| 建筑 `refs.py` | 复用对象和 view/claim/inference 编号，补充运行身份、原图哈希与坐标关系。 |
| 建筑 `evidence.py` | 分开用户要求与四类依据，支持继承、冲突及原值到保存值的计算链。 |
| 建筑 `declarations.py` | 封装三个现有 BIM 工具入口，表达范围、模型与代码分工、重复和例外。 |
| 建筑 `tasks.py` | 定义带图证据包、三栏局部返回、旧版本拒绝及单层起草草案。 |
| 建筑 `quality.py` | 定义几何、拓扑、覆盖检查，以及保护墙、房间、门窗和连通的尺寸规整建议。 |
| 建筑 `bundle.py` | 核对全部交叉引用，并从变化的依据反查受影响声明和模型版本。 |

基础类型与导出文件、字段说明及旧工具对应关系集中在[接口入口文档](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/design/unified_agent_stage0_interfaces.md)。两层均可通过 Pydantic 校验并导出 JSON Schema；未实现运行循环、压缩、委派或规整算法。

2. A–J 自评

以下“满足”均限于阶段 0 的格式、样例和离线校验范围。

| 条件 | 自评 | 证据与实际结果 |
|---|---|---|
| A 三线共用 | 满足 | 还原和部分推理实际使用同一套公共接口；完全推理无需图纸或网格字段，推理方案标为假设。 |
| B 事件记录 | 满足 | 最终请求含实际本地图像字节；原始与所见返回分开；签名、内容、用量和缺失不混写。 |
| C 历史映射 | 满足 | run99 与 Sol 桥接各映射六条事件，保留原消息、来源位置和哈希；历史缺口明确记录。 |
| D 依据与需求 | 满足 | 依据可继承并共存；sm25 标注与像素标定对应；实际替换依据后可反查声明和版本。 |
| E 声明边界 | 满足 | 使用原有三个工具入口；支持楼层、翼、对象组、跨层空间和重复例外。 |
| F 角色与证据包 | 满足 | 只读越权、擅自采用推荐模型、旧版本返回和夹带未下发图片均有拒绝反例。 |
| G 检查规整覆盖 | 满足 | 删墙、并房、移动门窗及改变连通的反例被拒；真实 Sol 精细档缺项不能靠理由或事后改粗档过关。 |
| H 恢复与预算 | 满足 | 未知写须先查保存状态；省略重试链接、重复应用或修改重试参数均被拒；缺用量不记零。 |
| I 范围 | 满足 | 全部变更在许可范围；冻结及保护路径 diff 为空；未调用工作模型或付费 API。 |
| J 验证 | 满足 | 六个测试文件共 86 项通过，包含依赖方向和模块实际加载路径检查。 |

逐条测试函数名和证据路径见[覆盖与验收说明](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/logs/experiments/2026-10-02_harness_stage0/coverage.md)。其中 `test_write_cannot_bypass_recovery_by_omitting_retry_link` 验证未知写不能绕过恢复检查；`test_fine_failure_cannot_pass_as_rationale_or_unapproved_coarse_merge` 验证精细档缺项不能被改口解释掉。

3. 样例与映射材料

接口 × 六类样例的覆盖表也在上述覆盖说明中；材料来源见 [source_mapping.md](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/logs/experiments/2026-10-02_harness_stage0/source_mapping.md)，事件字段映射与缺口见[历史映射说明](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/tests/fixtures/harness_stage0/history/README.md)。

还原样例将 sm25 的 4.00→3.94 米建议绑定到原生隔墙编号，另存前后快照，没有修改历史 BIM。部分推理保留已验收的 `CORE_E` 连续跨层空间、成对门和单门例外，并把 Sol 实际保存的两窗办公室接入精细档失败覆盖链。

完全推理使用明确标注的贴图扫描渲染替代照片，尺寸和两层片段均为显式假设。混合输入的跨实验对象对应单列为待核实推断。粗细比较共用输入和观察依据，精细表达保留两间房，粗档依据明确简化要求合并为一个片段。

4. 提交、diff 与验证

| 提交 | 内容 |
|---|---|
| `a9602e20` | 公共与建筑契约、接口说明及核心正反例。 |
| `7234eddd` | 真实历史来源节选和 CLI/桥接映射，保留缺失。 |
| `82d536cc` | 六类连接样例、集成检查、覆盖表、验证回执和开发交接。 |

完整 **69 个文件**名单见 [changes.txt](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/logs/experiments/2026-10-02_harness_stage0/changes.txt)；与实际提交 diff 逐项一致，`git diff --check` 通过。

最终实际运行六个新增测试文件，使用 `python -m pytest … -n 4 -s`，结果为 **86 passed in 11.52s**。其中核心24项、建筑34项、边界2项、历史映射5项、来源6项、集成15项。原始输出见 [validation.txt](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/logs/experiments/2026-10-02_harness_stage0/validation.txt)，命令、时间及59份被测文件哈希见 [validation.json](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/logs/experiments/2026-10-02_harness_stage0/validation.json)。

联调发现并修复了恰好6厘米的浮点误拒、未知写绕过恢复检查，以及图片引用取错依据项等问题。最终被测文件哈希已再次核对一致。

5. 未决事项

需要与 Opus 定的技术项：阶段1如何从实际保存源模型生成可信语义快照；建筑证据包的小预算怎样映射到底座总账；大请求落文件前如何核验注入位置与图片字节；历史缺口下的重放验收边界。当前结构校验不能替代几何联动检查，也不能证明外观解释或室内推断正确。`InferenceHypothesis` 的名称是否改得更中性，可在首次接入前定稿。

需用户决定的产品事项：完全推理后续采用哪栋建筑的真实照片及允许的补充材料；粗细档名称、默认简化程度与全局容差。后续真实整案的模型、次数、预算仍按节点回归约定另提方案，本轮没有预先采用这些选择。

6. 阶段1–3估算

阶段1预计 **2–3轮**，完成单角色记录闭环、历史兼容读取和分层重放；阶段2预计 **1–2轮**，完成60–120步离线故障注入、上下文恢复和预算停止；阶段3预计 **1–2轮**，接通外层MCP协调和只读带图委派，再提交整案实测方案。

合计 **4–7轮开发会话**，另计获批整案执行和必要返工。最大风险是历史日志缺口，以及适配器、保存状态和真实模型行为之间的联调；离线契约通过不能消除这些风险。

7. 子代理与用量

| 子代理 | 型号／推理档 | 用途与结果 |
|---|---|---|
| core_contracts | gpt-5.6-sol／high | 完成核心契约、历史映射及恢复反例，核心24项通过。 |
| building_contracts | gpt-5.6-sol／high | 完成建筑契约、保存覆盖与规整保护，34项通过。 |
| source_fixtures | gpt-5.6-terra／high | 完成来源节选、哈希核查和只读复核，来源6项通过。 |

Astra 负责总体接口、六类连接样例、整合复核、文档与提交。主代理及子代理的 token、缓存和订阅金额未从协作接口取得，均记为**未核实**；本次代码执行中的工作模型、Paratera、DeepSeek、GLM及其他付费API调用为0。分工、修复过程和交接记录保存在[开发记录](/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0/AI_agent/logs/worklog/2026-10-02_astra_harness_stage0.md)。