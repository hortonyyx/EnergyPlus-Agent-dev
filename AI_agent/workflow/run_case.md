# 运行与检查案例

当前入口是自有 runtime 与共同 domain，不要求准备旧 reading/correction 阶段目录。能力范围见 [配置说明](../design/model_configuration.md)，模型调用遵守 [模型约定](models.md)。

## 准备和离线预检

本案输入放独立目录，例如 `D:/Sim-BIM-Agent/cases/my-building/input`，不混入 GT、旧答案或其他案例。新结果放 `D:/Sim-BIM-Agent/runs`。复制 [配置示例](../../product/config.example.json)，设置 input_root、run_root、input/output、mode、模型和保护线。

图像入口读取目录直接包含的有效 PNG；JPEG/PDF 需预先转换。单模型 mesh 输入指向 GLB；分工仅接图纸。预检不证明材料可正确建模。

```powershell
. ./scripts/activate_windows.ps1
python sim_bim.py doctor
python sim_bim.py check D:/Sim-BIM-Agent/my-run.json
python -m src.agent.runtime_configuration command D:/Sim-BIM-Agent/my-run.json --case my-building
```

以上命令检查环境、配置与输入或显示启动命令，不发送推理请求。示例型号不构成新的选型决定或整案批准。

## 在已确认范围内运行

```powershell
python sim_bim.py run D:/Sim-BIM-Agent/my-run.json --case my-building
python sim_bim.py run D:/Sim-BIM-Agent/my-run.json --case my-building --resume
```

新实验使用新输出名；resume 用于同次运行的合法恢复，不编辑日志或检查点伪造完成状态。控制与恢复见 [runtime_controls](runtime_controls.md)。

Dev model 观察、记录与评价。若派任务或修建模结果，记为开发辅助，不与独立 work model 冷启动混报；不暗中换模型或扩大调用范围。

## 交付检查

核对选定源 BIM、查看页、平面/回叠、未完成项与假设，再核对输入对应、空间划分、宿主和连通。预算结束、工具成功或自报完成不是独立质量通过。

正文用表格报告案例/输入、版本/模式/角色模型、质量/终态、耗时、请求/响应/失败、token/费用、返工和干预。未生成、未评价的项明确标出。

待安排的 GPT-6 Sol 标杆和候选调研/实测仍需讨论具体方案，本轮整理不启动。

## 历史流程

旧 `run_stage.py`、`run_full_pipeline.py` 和顺序 intake 管线仅按明确追溯任务调用，历史 stage ID 与产物结构不改名。资源见 [legacy](../../src/agent/legacy/README.md)。旧操作说明与启动 prompt 已保存在 [归档索引](../reports/archive-index.md)，不作为新任务入口。
