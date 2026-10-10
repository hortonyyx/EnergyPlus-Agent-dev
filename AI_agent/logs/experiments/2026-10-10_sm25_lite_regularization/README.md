# sm25 Lite BIM 规整：人工调度实验准备

状态：`prepared_not_started`。本目录只准备配置、首次六任务和离线审计；没有初始化 run、派工、调用 HTTP/模型、运行整案或消费费用。当前准备基准为 `d5f5a5ef`，`run_config.json` 中的 `integrated_code_version` 仍是占位符。domain 集成、离线检查和版本登记完成后，项目经理必须先把它替换为实际版本，再执行任何包装器命令；`init` 会把配置哈希和已登记 agent 版本冻结到新 run。

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

运行中只读观察与人工协调：

```powershell
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py status --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/observe_runtime_accounting.py AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1 --format both
.\.venv\Scripts\python.exe AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/manual_dispatch.py tool --config AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/run_config.json --name <经审核的工具名> --arguments <本目录内经审核的参数JSON>
```

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
