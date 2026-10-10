# sm25 Lite BIM 规整：domain v57 与首次实测

状态：**`failed`，完整规整 BIM 目标未达到。** 2026-10-10 约 17:24–18:26（Asia/Singapore），一次六读图员实测已终止，耗时 62分24.5秒（初始化至根终止事件，含收口；平面角色保护线为60分钟，立面为30分钟）。四立面完成，两平面失败，未进入装配、交付或 GT 评价。没有重复冷启或模型回退。

运行来自冻结树 `D:\EnergyPlus-Agent-worktrees\lite-sm25-run-20261010`，HEAD `3484cae5`；已复制回主树 `AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1`，5,763 个文件 / 44,444,654 bytes 逐文件哈希一致。配置的 `prepared_not_started` 是包装器要求的不可变输入，不是运行终态。实际终态以 `receipt.json`、生命周期和下表为准。

生产代码集成为 `851b62ce`，登记 `runtime-v2-20261009 / domain-v57-20261010`；仅 domain 变化，三个分工角色的 fingerprint 更新，单模型 fingerprint 保持。定向检查、独立审查与离线预检已完成。全量 5,969 passed / 12 failed；12 项均为旧测试夹具或指引断言，修复后六个完整文件 61/61 通过，生产代码保持，未重复全量。详见 [集成验证](integration_validation.md)。配置哈希与登记版本已冻结。

## 实测结论与查看入口

| 项目 | 本次结果 |
|---|---|
| work model | 平面：Qwen3.8-27B / thinking；立面：Qwen3.8-Flash / thinking，均经 Paratera |
| 模式 / 范围 | 项目经理人工调度；runtime v2 不变，domain v57 的 BIM rules、kernel、tools、methods、roles、guidance；只改变分工路径，单模型参照保持 |
| 完成状态 | 四立面 accepted；F1 五次失败声明；F2 无声明；无有效平面、整楼候选或 BIM 交付 |
| 已见规整 | 四立面共118项原始/采用读数，4项改变，最大2.34cm；均采用0.1m政策且保留原读数 |
| 实质质量 | 四立面对照原图未见实质漏项/高度错误，但尚未与平面装配；F1仍有两组门合一、门宽误读，种子数不等于正确房间数 |
| 精度分档 | 房间、门窗位置及整楼高度的≤5cm、5–10cm、10–30cm、>30cm均不可评价：没有最终源BIM；不是零误差 |
| 人工介入 | 初始派工、原图只读复核、准备F2盘点/六尺寸链和F1门组意见；后续恢复任务均未派发，输入未进入work model |
| 评价边界 | 未读GT；没有最终BIM可评价，不执行空结果GT评分；旧产物离线回放单列，不能替代本次结果 |

- [本次报告查看页](report.html)；[一层失败声明诊断叠图](F1_trial005_raw_declarations_NOT_BIM.png)（**不是 BIM**，坐标原样叠加，未修复）。
- 最终平面图、最终回叠图和 BIM 查看页：**未生成**。二层没有可绘制的完整声明。
- [逐角色行为](observer_notes.md)、[平面原图核对](plan_visual_review.md)、[立面原图核对](elevation_visual_review.md)、[规整实际采用量](lite_adoption_current.json)。
- [最终记账](final_accounting.json)、[逐文件归档清单](run_file_manifest.json)、[恢复阻断原因](recovery_blocker.md)、[trial003离线定位](trial_003_dimension_order_diagnosis.md)。

## 耗时、用量与缓存

| 项目 | 数值 / 边界 |
|---|---|
| 整次墙钟时间 | 3,744.525秒，62分24.5秒；初始化至root stop，包含收口 |
| 模型 / 工具 | 99请求，98响应，1超时失败，0在途；130次工具，6次错误（5平面trial、1立面schema） |
| 已知输入 / 输出 | input 4,934,883，output 345,672，provider total 5,280,555；仅98个有usage响应 |
| 已知缓存 | 3,999,232 / 4,934,883 = 81.04%；F1为63.70%，F2为87.67%，立面合计81.20% |
| 已知费用 | 9.1655892 CNY：27B 8.4641562，Flash 0.7014330；缺超时请求usage，总实际费用未知，非发票 |
| 图片 / runtime charge | provider image 578,810已包含在input；runtime预算token 5,859,365按原计费口径另计图片，不能重复加入provider total |
| 上限与恢复 | 20 CNY / 180请求 / 700工具 / 10,800秒；未触及全局金额上限，但超时缺usage触发不可恢复的`money_cny_usage_unavailable` |
| 人工调度员 | runtime模型HTTP 0；Codex/GPT开发用量未取得，不称全部零成本 |
| 其他线路 | DeepSeek / Claude / GLM调用0，自动fallback 0 |

第21个F1请求已有settlement事件，但usage为missing、费用估算为空；因此`pending=0`与“总费用未知”可以同时成立。预算仍保留该请求0.370086 CNY的完整预留，已知费用加此预留为9.5356752 CNY；预留不是实际账单。当前runtime重启也会恢复fatal，不能靠新task绕开。未编辑账本、虚构usage或新开独立run。

| 角色 | 首稿/提交里程碑 | 请求 / 工具 | 结果与问题归属 |
|---|---|---:|---|
| 平面F1 | 首trial约33.6分；5次均失败；约60分超时 | 21 / 24 | 自修格式、漏底墙、近轴接头和北侧门组；最后南侧两门组误合，西上外门宽误读。work model读法与domain机械返工并存；超时后的恢复阻断属runtime |
| 平面F2 | 从未trial；约46.9分耗尽40请求 | 40 / 51 | 22次看图、28次剖面，却无完整声明。指引与“先完整近似稿”提醒未兑现为行为减负 |
| 北立面 | 约5.5分schema拒绝，6.0分接受 | 8 / 13 | 多填floor_id，自修后完成；1次工具错误 |
| 南立面 | 约6.2分接受 | 10 / 16 | 完成，原图复核未见实质错误 |
| 东立面 | 约5.9分接受 | 10 / 15 | 完成，门底离地读数已保留并规整到0.2m |
| 西立面 | 约4.2分接受 | 10 / 11 | 完成，4.32m窗宽采用4.3m |

里程碑以首个保存事件为起点，角色初始化/第一HTTP与root初始化不同，不能把每列直接相减成工具纯耗时。F1两次长请求分别643秒、596秒且cache=0；没有服务端时序证据把它们全归因于思考或缓存。

## 对照与下一步

| 可比观察 | 10-09 domain v56 | 本轮 domain v57 |
|---|---|---|
| 一次人工调度结果 | 两次定点返工后29空间、61门窗、30门连接 | 四立面完成，两平面失败，无BIM |
| 墙钟时间 | 45分32秒，含成功后的复核/返工 | 62分24.5秒，失败收口；不能按完成速度比较 |
| 请求 / 已知provider token | 98 / 5,259,001 | 99 / 5,280,555，另1超时usage未知 |
| 费用 / 缓存 | 8.7029404 CNY / 75.81% | 已知9.1655892 CNY / 81.04%；缓存更高没有转成出模改善 |
| F1首trial | 28.6分、此前48次剖面 | 33.6分、此前8次观察（其中2剖面）；观察次数减少，但首稿更晚 |
| 平面规整 | 冻结结果仍有非网格尾数 | 旧稿离线回放可全部落网格；新看图实测尚未到达完整采用值 |

这不是纯模型A/B，每版只一次且结局不同。**本版没有证明整案减负或人工调度成功。** 压缩返工artifact的离线消息体积下降94.52%，只证明服务端投影有效，本次没有实际返工请求验证其耗时收益。

下一步先处理已被本次证据定位的三个接口问题，再定有界模型验证，不追加冷启：

1. domain：完整原始声明即使尚未编译，也应有受哈希保护、保留未改对象的局部修订入口；当前native恢复只接受已有numeric identity，F1五份完整声明因此无法直接复用。
2. domain：尺寸链落位前的近轴接头整理需与连接节点原子联动。trial003仅4.59cm的移动就被旧近轴线误差阻断；不能靠放松拓扑守卫，也不能声称现有Q1前置即能解决。
3. runtime候选（本轮未改）：人工能及时介入活动/阶段性读图，以及缺usage时有保守预留或可审计补账路径。否则“有人工调度”仍可能只能等任务耗尽后面对永久停止。

读图层仍需区分“读清对象关系”与“继续抠坐标”：D6两组门合一和D1门宽误读要靠正确关联原图；F2没有结构稿要靠可保存、可反馈的阶段产物。不能把这些都交给更粗网格修复。

以下为冻结实验的复现协议，**不代表新的执行授权**；已用运行目录不可重初始化。

## 备份与收尾

完整run、旧稿离线回放、实现patch及测试日志合计5,792文件/98,164,389 bytes，压缩包22,516,390 bytes；5,793个包成员（含manifest）逐项校验、配置秘密值扫描均通过。证据分支`evidence/sm25-lite-2026-10-10`，提交`f80d9613391b06d25cbad785254a90ff2720ce30`；主线保存报告与逐文件哈希，详见[evidence_backup.json](evidence_backup.json)。

两棵实现工作树已收回；运行树Git登记已收回，但实体删除遇`Filename too long`，随后清理被自动审批拒绝（`blocked by policy`）。未重试或换路径规避，保留D盘本次目录33,890文件/约3.04GiB残留，完整原始证据另有主树与远端备份。C/D剩余约17.46/177.23GiB；其他任务的旧工作树保持。[清理回执](cleanup_receipt.json)记录准确范围。

静态报告页已实际浏览器核对：图像加载、9个本地资源链接存在、无横向溢出、0控制台错误/警告；[UI回执](report_ui_qa.json)。临时浏览器和localhost服务已关闭，HTML可本地打开。这不是最终BIM查看器验收。

## 固定范围

- 输入沿用 `case_tests/e2e_tests/sm25-L_anchor/case_data` 原图，输出使用独立目录 `AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1`。
- 首次派工是 `tasks_initial.json` 中两张平面和东南西北四张立面。任务只有图像、角色、目标和共同原点，不含旧坐标、旧尺寸、库存/计数、GT、楼层标高答案或旧 BIM。
- 两层平面绑定 Paratera `Qwen3.8-27B` + thinking，四立面绑定 `Qwen3.8-Flash` + thinking。根协调员模型请求为 0；总保护为 180 次模型请求、700 次工具调用、10,800 秒和 20 CNY。
- 禁止自动 provider/model fallback，禁止 DeepSeek、Claude、GLM，禁止重复冷启动。首次 `delegate` 必须同时显式覆盖六个任务；旧包装器会在 HTTP 前拒绝隐藏补派、未列任务、coordinator 任务和线路错配。
- 本轮产品调用固定采用 `0.1 m` 步长。domain 函数可接收其他步长，但尚未贯通为运行配置或用户控件；配置中的 `preparation.lite_bim_grid_m` 只记录本次政策，不控制工具。并未实现“读完所有标注后自动选择多种更粗/更细步长”的完整策略，也不能在报告中这样声称。没有新增专用 OCR 服务。
- 规整目标是代码先归并整图尺寸、按共享尺寸链/节点统一落位，再给 work model 一个统一精度首稿；最终验收仍需确认空间划分、开口、共墙、跨层关系及图纸符合性。单纯网格通过不能代替这些检查。

## 复用入口及其限制

本轮直接复用 10-09 的三个脚本，不复制旧运行目录：

- `../2026-10-09_sm25_dev_and_tier4/manual_dispatch.py`：`validate` 和 `self-test` 都是离线命令；`init` 要求兼容性闸门 `--after-first-run-complete`，输出已存在时拒绝覆盖；初始化后配置哈希或登记版本变化会拒绝继续。
- `../2026-10-09_sm25_dev_and_tier4/finalize_manual_dispatch.py`：只做离线生命周期收口；有活动 reader 时拒绝完成。
- `../2026-10-09_sm25_dev_and_tier4/observe_runtime_accounting.py`：只读汇总 EventStore、角色用量与费用估算。

`manual_dispatch.py tool` 只用于零模型调用的协调工具；包装器拒绝 `delegate_readers` 和可能隐式启动其他模型的 `review_detail`。后续读取、装配、检查、局部返工与交付参数必须由项目经理基于本轮产物另存为本目录 JSON，再逐次审核调用。

## 执行命令

以下命令均在仓库根目录运行。先完成 domain 集成，填写实际 `integrated_code_version`，确认新输出目录尚不存在，再做离线预检：

```powershell
.\.venv\Scripts\python.exe -m py_compile AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/finalize_manual_dispatch.py AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/audit_lite_source.py
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py validate --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py self-test --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/audit_lite_source.py --self-test
```

项目经理确认预检输出中的登记版本、输入、固定路由、20 CNY 上限和输出不存在后，才初始化并立刻派发首批六任务：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py init --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json --after-first-run-complete
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py delegate --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json --tasks AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/tasks_initial.json
```

活动 `delegate` 持有根 EventStore 的 writer lock；运行中只能用不打开 EventStore 的只读统计：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/observe_runtime_accounting.py AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1 --format both
```

等待该次 `delegate` 返回并释放锁后，再执行状态、装配、复核或同次局部返工：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py status --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py tool --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json --name <经审核的工具名> --arguments <本目录内经审核的参数JSON>
```

当前 runtime 没有向活动 reader 注入追加指导的入口；stdin、修改任务文件及 checkpoint 都不是消息渠道。人工提示须通过既有同次局部返工任务进入，并记录介入内容；不直接改活动事件或状态。最终装配、四立面回叠与交付参数见 [协调复核配方](coordinator_qa_recipe.md)。

结束时先确认所有 reader 已终止，再离线收口：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/finalize_manual_dispatch.py finalize --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json --status completed
```

若运行失败，使用 `--status failed --reason <原因>`，不能把未规整稿或回退稿记为完成。

## 最终离线审计

审计器只枚举最终采用的几何坐标，不扫描任意数字字段。它分别统计 floor footprint、space polygon、z 下沿、z 上沿、boundary vertices、opening vertices 和 boundary-relation region/hole vertices；默认用绝对容差 `1e-8 m` 判断是否位于 `0.1 m` 网格，并按类别输出越格数及样例。关系检查覆盖对象 ID、楼层/空间引用、counterpart 互引、boundary relation、opening host 和 connection。面积、法向、容差、置信度、证据图框、原始观察和报告数值明确排除。

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/audit_lite_source.py AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1/bim/candidate_N/source_model.json --grid-m 0.1 --abs-tol-m 1e-8 --json-output AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/final_source_grid_audit.json
```

若本轮另存了规整前、稳定 ID 不变的 `source_model.json`，可加 `--baseline <同一次运行的规整前source_model.json>`，得到对象库存、opening hosts、connections 的前后保持检查，以及实际移动坐标数和最大移动量。10-09 冻结结果只能用作离线旧结果诊断，不能作为本轮 reader 上下文，也不能冒充同次运行 baseline。

最终还需在运行结束后独立执行公共评价与视觉复核；网格审计只证明数值网格和引用保持，不证明图纸还原质量、空间划分正确或自主稳定。

## 已完成的离线自检

`audit_lite_source.py` 已通过 Python 编译和内置自检；自检确认能检出单个越格坐标及连接关系变化，网络请求和模型请求均为 0。`run_config.json` 与 `tasks_initial.json` 已通过 JSON 解析，首次任务数为 6。

两份 10-09 冻结 source 均被完整只读审计，报告保存在本目录：

| 冻结结果 | 枚举坐标 | 越格坐标 | space polygon | z 下沿 | z 上沿 | boundary vertices | opening vertices | floor footprint | relation vertices | 关系检查 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| manual candidate_10 | 4,366 | 1,554 | 122 / 264 | 0 / 31 | 0 / 31 | 732 / 2,376 | 362 / 732 | 8 / 32 | 330 / 900 | pass，0 error |
| Sol candidate_12 | 4,366 | 2,524 | 220 / 264 | 0 / 31 | 0 / 31 | 1,320 / 2,376 | 422 / 732 | 16 / 32 | 546 / 900 | pass，0 error |

表中分类单元为“越格 / 枚举”。这证明审计器能发现旧结果的非 0.1 m 尾数；它不评价哪份旧结果更准确，也不支持把人工辅助成功外推为自主稳定。
