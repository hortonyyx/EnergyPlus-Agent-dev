# D1 执行报告：分工体系 v1

状态：实现、授权范围内验证及交接已完成；H 部分完成，不能报全绿。执行方 Astra，项目经理 Opus。基准 `e07764e6508b37898791f2b960e6980b97e192d8`，工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1`，分支 `dev/astra-d1-20261006`。开工状态干净。仅在派工范围修改源码、测试、配置与本实验记录；roadmap、决策、验收记录、设计正文未改。所有 Git 操作只读，没有提交、建分支、改配置或推送。

新 Agent 版本 **`t1-20261006-d1.1`** 已登记并校验 70 个文件，原有 22 个版本记录逐项保持一致。真实小测仅一次三题 GLM 订阅，共 **28 次请求**；真实整案、Paratera、DeepSeek 均 **0 次**。最终版的离线证据与开发中版本的真实小测分开报告，不把脚本回放当模型自主建模成功。

## 实施设计（开工先写，已按最终实现更新）

1. **角色与入口**：新增图纸专用 `role_division`，不改 `single_model` 的配置含义、指引及请求组装路径。角色固定 `coordinator`、`plan_reader`、`elevation_reader`；每个角色显式给出 `provider/model/reasoning_effort/output_tokens`，缺项报错，不继承。角色代码集中在 `src/agent/runtime_roles/`；既有 `src/agent/roles.py` 是空间用途模块，保持原样。默认并发 4，可配置；复用现有适配器、循环、预算与事件机制。
2. **平面产物**：仅 `plan/evidence/unresolved` 三个顶层字段；`plan` 直接是 `build_plan_bim` 的既有格式，依据逐项对应标定、外轮廓、隔墙、种子、开口，并限定本任务原图框。试建使用隔离的冻结 MCP 工作区，复用同一编译、源检查、平面差异、精度与回叠；不写全楼候选。失败返回具体原因和最小示例。已试建但未通过的稿可登记、读回、返工；`validation_passed:false` 禁止引用建层。
3. **量测传递**：试建先按现有顺序归一化字段、展开单位与 profile 坐标，保存原计划、数值稿、原图及 profile 哈希、量测绑定和试建收据。通过引用建层时校验原稿及数值稿哈希，再展开数值参数；不把读图员的临时 profile ID 当作全楼可访问资源。确定的字段别名使用同一计划身份，不能靠静默丢字段放行任意变化。
4. **立面产物**：单面方向、观看方向、横向标定、标高表、从左到右的开口表（层、门/窗、像素范围、宽、窗台/顶、依据类型、原图框）、每层门窗计数及未决项。数值为米、框为原图像素。基准 +X 东、+Y 北；从外面看，North/South 的屏幕横向分别对应世界 X 递减/递增，East/West 对应 Y 递增/递减。
5. **登记与恢复**：任务、交付 JSON、记录及摘要绑定哈希，并保存内容寻址 blob；读回核对任务身份、记录、文件及 blob。调度员状态保留引用，压缩后可读全文。建层日志同时记录模型引用和展开参数。恢复只重放已持久化完成结果；没有结果的未知写入不猜测成功，也不擅自重做。任务返工使用新 ID，附上上一稿与具体问题。
6. **对位与高度**：按正交外墙朝向、楼层、类型、顺序和沿墙位置匹配，明确列出匹配差值、两侧独有项与冲突。调度员在工具参数中确认后，沿用已有 `claim_transaction` 机制批量写入安全匹配项，依据指向原图框；源稿变动后拒绝使用过期对位结果。未匹配项保留待处理，不按数量相等强配。
7. **隔离、指引与总账**：读图员只看自己的图及允许的缩放、像素、尺寸链和参考工具，平面员另有隔离试建。角色指引从现有 CORE/DRAWING_METHOD 对应段落搬出并替换不可用工具；调度员换成派工、建层/组装、对位、复核返工和交付流程。所有角色共用全楼总账及总工具上限；任务可再显式设保护线，默认不另加任意的紧限额。单请求时间预留为总保护秒数/(并发数+1)，避免首任务独占共享时间；全案截止时刻不缩短。按角色记录请求时长、任务耗时和并发墙钟跨度，三者不混加。

## 派工执行与 A–I 对照

实际使用三个 **GPT-5.6 Sol，high** 子代理：读图/试建/指引，立面对位/离线贯通，配置/单模型兼容/独立核查。按派工单优先 5.6 系列，并以文件划分可独立验证的子包；Astra 负责运行集成、总账、产物与恢复、真实小测和总报告。开发子代理不计入产品运行请求账。

| 条款 | 当前结果与证据 |
|---|---|
| A 角色配置与计账 | 已实现。三角色独立路由，缺角色/字段、错误线路、过低输出明确拒绝；Anthropic 兼容与既有 OpenAI 兼容线路离线验证。并发默认 4，共享时间/token/金额/请求/工具总账；限流沿用原分类。按角色统计格式失败、补救成功/失败及交付结果。小测最终统计见 `small_test_posthoc.json`。 |
| B 两类读图员 | 已实现。单图隔离、既有平面格式、逐项依据、隔离试建及立面扁平表；不通过时保留原因但禁止引用建层。量测 profile 到数值稿的真实 MCP 离线验证通过。真实模型的平面最终格式仍失败，详见 G，不据单测宣称已稳定。 |
| C 产物状态与引用 | 已实现。哈希绑定任务、原图、记录和稿件；不可变完成记录、压缩状态中的引用、读回、引用建层及展开参数日志均有测试。文件/元信息篡改、过期高度依据、无结果的未知写入均拒绝。 |
| D 调度员 | 已实现。批量派工、读回、建层、组装、对位批量写高度、检查与交付；按问题新任务返工或直接修改。单模型指引未追加分工要求。 |
| E 立面对位 | 完成离线验证：sm21 **17/17**、sm24 **14/14**、sm25 **34/34**。sm24 为已有四立面原图参照；另外两例是好稿导出的自洽验证。漏/多一扇、整体偏移、左右反序、紧邻双窗、立面有门反例全部通过。见 `elevation_verification.json`。 |
| F 离线贯通与恢复 | **完成，5个独立场景最终通过**：sm24单层、sm25双层完整贯通，加三个中断恢复点。持久输出均为最终版本、completed/delivered；见 `offline_replay.json` 与 `final_validation.json`。 |
| G 真实三题小测 | 按授权执行一次，28/40 请求；两个立面各补救一次后交付，6/6 门窗宽度与上下标高符合参照；平面第4次试建通过，但最终交付哈希校验失败。首过0/3，补救后2/3。见下节。 |
| H 版本、检查、对照 | 新版本及旧记录保留已验证；两底座三例共享请求内容字节核对通过，六份对照配置备齐。运行层509通过，工具层368通过、1项Windows结束进程权限失败，角色76通过；因此H为**部分完成**，不能称全部检查通过。 |
| I 交付 | 全部变更留工作树，无Git写入。下文给出文件分组和建议提交说明，交Opus复核提交。 |

指引长度按 Python `len` 的 Unicode 字符计，不是 token：**单模型 9670；调度员 1167；平面 6252；立面 5436**。单模型源指引文件未改。

## E 与 F 的验证边界

`elevation_verification.json` 的 65/65 是对位算法结果。sm24 用 `2026-10-03_runtime_r1/facade_references.json` 的原图窗框与读数，以及 `2026-09-16_sm24_developer_reconstruction/elevation_observations.json` 的独立水平标定及门；sm21、sm25 从10-01好稿投影，不能称独立读图准确率。实现过程曾发现观看方向符号反了，已用真实参照纠正，并补四方向测试；原先单纯从源稿投影的自检没有独立发现力，未用它掩盖该问题。基础版只处理正交、轴对齐外立面，不宣称支持任意曲折/斜向立面。

F 脚本回复来自已知好平面，通过真实冻结 MCP 调用，不访问真实模型。持久结果：

| 案例 | 可查看稿 | 楼层/房间/门窗 | 读图产物 | 高度事务/应用 | 脚本请求/工具 | 离线耗时 |
|---|---|---|---:|---:|---:|---:|
| sm24 | [delivery.html](offline_replay/sm24/bim/delivery.html) | F1 / 8 / 21 | 5 | 4 / 14 | 26 / 20 | 42.78 s |
| sm25 | [delivery.html](offline_replay/sm25/bim/delivery.html) | F1+F2 / 29 / 61 | 6 | 4 / 34 | 33 / 26 | 169.06 s |

两例均为 `t1-20261006-d1.1`、`completed/delivered`。最终源哈希与交付选择一致，HTML本地引用均存在；见 `final_validation.json`。脚本请求是离线回复消费次数，不是外部API调用或自主模型耗时。

三个中断点为读图员试建后的检查点、全体读图结束但未建层、建层执行后但未完成运行。最终均验证恢复完成，已完成读图请求、试建、建层不重复。首轮26项（含21项立面对位）25过、1个测试路径断言失败：测试误以为子任务有独立journal，实际事件共用全楼journal。改为按事件 `task_id` 统计后，该点复跑1/1通过；总审再发现“全reader完成”断言也有同类0==0问题，已加强“中断前请求数大于0且恢复后不增加”，单点复跑1/1通过。两份复跑JUnit和原失败JUnit均保留，生产代码未为变绿改动。

## G：真实小测结果与失败链

仅使用显式只读的主树 `.env`，不打印、不复制、不入仓。线路 `glm-subscription-anthropic`，模型 `glm-5.3-flash`，medium，输出上限32768。无调度员模型请求、无自动服务回退。请求预算分给平面24、North8、East8；实际13/7/8，总28。脚本拒绝已有运行目录，未重启第二批。

| 任务 | 请求/工具 | 首次交付格式 | 一次补救后 | 本任务耗时 | 输入 / 缓存读 / 输出 token |
|---|---:|---|---|---:|---:|
| sm24 平面 F1 | 13 / 14 | 失败 | 失败 | 1056.93 s | 326368 / 147072 / 59300 |
| sm24 North | 7 / 10 | 失败 | 通过 | 139.79 s | 95423 / 45440 / 5705 |
| sm24 East | 8 / 16 | 失败 | 通过 | 236.71 s | 121081 / 47296 / 10699 |

三个任务并发，总墙钟 **1062.13 s（17分42秒）**。供应商报告 **542872 输入 + 239808 缓存读 + 75704 输出 = 858384 token**；缓存占输入侧 `cache/(input+cache)` 为 **30.64%**。另外的图片估算186959单独记录，保护账本扣量1045343，不能把它当供应商实际用量。订阅没有逐请求人民币账单，金额为 null，不能说费用为0。无服务错误/限流；平面为交付校验失败。最终统计含平面格式错误2、补救1失败；立面格式错误2、补救2成功。

具体行为与结果见 `small_test_diagnosis.json`，含事件号、原始blob及文件哈希：

- 平面4次试建依次为悬空墙段、D1找不到完整宿主、房间用途不在目录、第4次通过。第4次源稿8房间、11窗、10门，源几何可用，现有平面差异与精度报告均0条。最终答案却带说明文字/Markdown围栏，第一次JSON解析失败；唯一补救去掉外围文字后仍把 `trial` 摘要塞进 `plan`，使稿件哈希与通过试建的稿不同，因此拒绝交付。没有删除这个字段冒充通过，也没有补发第4道任务。
- 两个立面首答同样在JSON前写了说明，均一次补救后通过。North 1窗1门、East 3窗1门；按已有参照从左到右比较，6个开口的宽度/窗台/窗顶误差均为0，类型和数量一致。评价容差5 cm；这是两张图的读数结果，不等于全楼门窗准确率。
- 对**通过试建的中间稿**另做只读几何诊断，未把它登记成最终交付：与10-01好稿数量相同，外轮廓IoU=1.000，8房间一一分配最低IoU=0.9544；21个开口一一匹配中心XY平均/最大差0.0290/0.0590 m，宽度平均/最大差0.0628/0.1552 m。见 `small_test_plan_trial_assessment.json`。这不是精确GT评分、拓扑/用途验收或高度准确率。

**版本边界**：真实小测进程在最终 profile 传递、失败收据、记录封存与统计修复前启动；事件内注册标签仍为 `t1-20261006-win.3`，实际开发源码哈希另存 code manifest。不能把此小测称为最终 `t1-20261006-d1.1` 复测。最终版本修复只有离线证明，未追加真实模型调用。`small_test_result.json` 和 `small_test_summary.json` 保留原进程统计；`audit_small_test.py` 仅读原始证据另写 `small_test_posthoc.json`，原始文件前后哈希一致，后验统计才包含修复后的格式失败计数与完整任务耗时。

## H：检查与对照配置

全部 Python/pytest 在本树 `.venv`，`src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，临时目录在 `AI_agent/archive/local_backup/d1/`。没有放宽保护断言，也未跑项目全量。

| 检查集合 | 结果 | 证据 |
|---|---|---|
| 历史运行、阶段0–3、R1–R3、C1–C3等，46个文件 | **509通过**，1318.10 s | `regression_scope.json`、`regression.xml` |
| 冻结工具、几何/指引及相关引用，40个文件 | **368通过，1失败**，278.40 s | `additional_regression_scope.json`、`tools_regression.xml` |
| 最终角色定向集，7个文件 | **76通过**，47.52 s | `role_regression_scope.json`、`role_regression.xml` |
| 最终F恢复/贯通 | **5个独立场景最终通过**；初轮测试误读路径及两次保护性复跑详见上节 | `final_e2e.junit.xml`、`final_e2e_reader_resume.junit.xml`、`final_e2e_all_readers_resume.junit.xml`、`offline_replay.json` |
| Agent登记 | 当前70文件全部校验，22个旧记录保持一致 | `version_registration.json` |

唯一历史失败是 `tests/test_bim_agent_tools.py::test_terminate_subscription_stops_parent_and_nested_session_child`：未修改的 `run_bim_agent.py` 调用Windows `taskkill` 时返回 **Access denied**，随后等待子进程超时。对自建2秒睡眠子进程做一次最小探测得到同一错误，子进程随后自然结束，见 `windows_process_probe.json`。未改终止逻辑、未忽略失败、未绕过沙箱；请Opus在其本机权限环境复核该条，再按原安排跑全量。

`single_parity.json` 和 `test_role_single_parity.py` 对 `e07764e6` 验证：单模型配置/argv不变；共享system/task/tools规范字节和原图哈希在两个入口、sm21/sm24/sm25三例一致；Runtime可选timeout为None时与旧请求字节相同。Claude入口在真正启动模型前拦截，0模型进程、0请求。**核对范围是既有共享模型可见内容，不声称不同HTTP协议或Claude CLI内部封包完全相同。** 原服务适配器、单模型入口、原指引及runner源文件字节未改。

六份配置在 `configs/`：`sm21_single.json`、`sm21_role_division.json`、`sm24_single.json`、`sm24_role_division.json`、`sm25_single.json`、`sm25_role_division.json`。全部GLM Anthropic兼容、`glm-5.3-flash`、medium、32000输出；保护线10800秒/3000万token/400模型请求/800工具调用。一对的任务正文仅委派行不同，其余相同；**除模式和角色段外，输出路径也分别加single/role_division后缀，防止两模式写同一目录**。这项持久化身份差异不影响模型请求，但比验收文字“仅三处差异”多一项，特此说明。六份都只验证配置，未执行真实整案。

## I：建议提交分组（由Opus复核后执行）

1. **`feat(agent): add drawing role runtime with isolated readers and artifact assembly`**
   - `src/agent/runtime_roles/{__init__,config,guidance,readers,trial,elevation,artifacts,accounting,session,entry}.py`
   - `src/agent/runtime_configuration.py`
   - `src/agent_runtime/loop.py`
   - 原因：入口、角色、工具、引用与总账互相依赖，作为一个完整可回退能力包提交；loop只增可选并发预留参数，默认单模型路径保持不变。
2. **`test(agent): cover role isolation, alignment, parity and crash recovery`**
   - `tests/role_d1_fixtures.py`
   - `tests/test_role_{configuration,elevation,end_to_end,guidance,readers,session,single_parity,trial}.py`
   - 说明：包括单图权限、预算、格式修复、哈希篡改、实际MCP profile试建、四方向对位与三个恢复点；保留Windows权限失败的原断言。
3. **`chore(agent): register D1 version and prepare GLM comparison pairs`**
   - `src/agent_runtime/agent_versions.json`
   - 本实验 `configs/` 的六个JSON、`version_registration.json`
   - 说明：登记冻结源码与工具目录哈希，保留旧版本；不启动对照运行。
4. **`docs(evidence): record D1 replay, small-test results and validation limits`**
   - 本实验 `README.md`、`verify_elevations.py`、`replay.py`、`run_small_test.py`、`audit_small_test.py`
   - `elevation_verification.json`、`single_parity.json`、`windows_process_probe.json`
   - `regression_scope.json`、`additional_regression_scope.json`、`role_regression_scope.json`及对应JUnit XML；`final_e2e.junit.xml`、`final_e2e_reader_resume.junit.xml`、`final_e2e_all_readers_resume.junit.xml`、`final_integrity.json`、`final_validation.json`
   - `offline_replay.json`、`offline_replay/` 的可查看稿、事件、收据、冻结材料、blob和脚本夹具
   - `small_test/` 原始事件、输入、试建、收据、blob与行为记录；`small_test_summary.json`、`small_test_posthoc.json`、`small_test_diagnosis.json`、`small_test_plan_trial_assessment.json`
   - 说明：建议把原始运行证据单独提交，保留失败链。`writer.lock` 等运行锁不作为版本化成果，`AI_agent/archive/local_backup/d1/` 临时测试目录不入提交。本次未删除、整理历史数据。

## 交回Opus的明确未决项

- H的Windows结束进程测试在本沙箱未通过；完整项目回归按派工由Opus合并后跑。
- 原始证据约325 MiB，嵌套试建目录存在超过260字符的路径（本次最长311字符）。Git只读枚举出现 `Filename too long` 提示；Python产物/哈希回读正常。正式入库时请Opus按项目证据存放约定处理；本轮没有改Git配置，也没有删改运行证据。
- G的平面中间稿试建已通过，但最终格式/稿件身份失败；三个角色首答格式通过率均低，不能宣称小模型交付已稳定。后续可针对“完整JSON交付及不在plan内夹带试建摘要”做最小修复，再由Opus安排获批验证；本轮不追加任务/请求，不扩成整案。
- 最终D1版本未做真实重测；共享请求内容的字节核对不覆盖Claude CLI私有HTTP封包。

## 证据归档（Opus，10-06）

`small_test/`（真实小测原始运行，1,907 个文件）与 `offline_replay/`（离线贯通输出，5,813 个文件，约 309 MB）已用 `2026-10-05_node_regression_c3/pack_evidence.py` 打包：分别为 4.1 MB 与 18.8 MB 的 tar.xz，放在证据分支 `evidence/role-division-d1-2026-10-06`；主线只保留 [evidence/](evidence/) 下的逐文件哈希清单。上文指向这两个目录的链接，需先从证据分支取出压缩包并解开。离线贯通可用 `replay.py` 重新生成。
