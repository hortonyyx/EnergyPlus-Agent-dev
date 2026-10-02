# 阶段 1 建筑契约与保存源 BIM 快照报告

## 结果

本工作包完成阶段 0 跟进项 3、4、5、8。没有改冻结工具、几何/修订内核、既有执行模块、项目文件或派工单，也没有网络、模型或 API 调用。

- `src/agent/runtime_snapshot.py` 新增保存源 BIM 快照生成器。入口只接收保存文件路径、模型版本 ID 和可选数字字段选择器，不接收调用方提供的语义清单。已支持仓库实际存在的 `source_bim_v1` 与 `source_bim_v2`。
- `src/agent/contracts/declarations.py` 将 `assemble_plan_bim(floors_json)` 纳入既有工具薄封装，并要求建模声明明确拥有每层 `floor_id` 和绝对 `z_floor`；没有另造装配语言。
- `src/agent/contracts/tasks.py` 删除建筑侧重复预算数字，`EvidencePackage` 只保存 `budget_reservation_id`。
- `src/agent/contracts/bundle.py` 接入底座 `BudgetLedger`，证据包必须引用存在、任务一致且用途为 `child_task` 的预留。
- 六份阶段 0 建筑样例及生成器已更新：建筑角色 ID 统一为 `local_observer`，证据包引用底座预留，还原样例增加两层装配声明。

## 保存源 BIM 快照的边界

`snapshot_source_bim()` 先读取保存文件的实际字节并计算 artifact SHA-256，再核对源 BIM 自带的内容 SHA-256。随后确定性生成：

1. 楼层、空间和墙清单；
2. 由保存的开口绝对顶点重新求出的两个平面端点和竖向范围；
3. 保存源 BIM 中的宿主边界引用，并核对开口顶点确实落在该墙面范围内；
4. 由门/通道的 `space_ids` 和 `exterior` 重建的连接，并与保存的 `connections` 逐项交叉核对；
5. 调用方指定 JSON Pointer 的数字字段。数值从保存文件读取，调用方不能传入值。

这里把保存的 `opening.vertices` 当权威几何，不从宽度/位置参数覆盖它。若未来出现另一种保存格式，生成器会明确报“不支持”，不会猜测。当前宿主贴合核对使用 `2e-5 m`，只容纳既有源生成中的浮点舍入缝，不作为建筑规整容差。

## 正反例

`tests/test_runtime_snapshot.py` 直接使用真实文件 `2026-10-01_opus_dev_sm25/candidate_04/source_model.json`：

- 正例抽出 2 层、29 空间、132 个墙边界、61 个开口、30 条连接，artifact 哈希绑定原文件；选定尺寸由保存 JSON Pointer 读取。
- 反例只把一面真实宿主墙平移 0.05 m、保留旧开口绝对坐标。内部内容哈希同步更新后，生成器仍因开口不再贴宿主墙而拒绝。
- 第二个反例把同一宿主墙和开口一起平移 0.05 m。生成器成功重算新开口端点；将前后快照交给现有 `NormalizationProposal` 时，因开口语义变化而拒绝“只改尺寸”的规整。
- 篡改保存内容但不更新内部哈希，以及未知 source BIM 版本，都会被拒。

`tests/test_building_contracts.py` 增加了装配声明正反例，以及证据包引用不存在、用途错误或缺总账预留的反例。

## 阶段 0 跟进项

- 3 语义快照：完成。由保存源 BIM 生成，调用方不能注入快照；宿主移动而开口未移动会报错，开口随宿主移动会进入前后语义比较。
- 4 多层装配：完成。`assemble_plan_bim` 的楼层身份、绝对标高及依据保留在工具 payload；契约强制 `floor_id`、`z_floor` 属于模型声明字段。
- 5 证据包预算：完成。建筑包只保留底座 `BudgetLedger` 的预留 ID，没有第二份 token、调用次数、秒数或金额。
- 8 角色 ID：完成。六份建筑样例和生成器统一为 `local_observer`。
- 1 名词：遵照“用户未确认前不改旧类型名”，本包没有改 `EvidenceItem`、`NormalizationProposal`、`BuildingDeclaration`、`InferenceHypothesis`；新增接口使用名词规范中的“保存源 BIM”“建模声明”“语义快照”。
- 2、6、7：不属于本工作包；分别由真实工具/角色工作包、底座核心工作包处理，样例体积本包没有另做可选压缩。

## 提交与文件

- `f31a9be2 Update building contracts for stage 1`
- `15acb37f Generate semantic snapshots from saved BIM`
- `0d100835 Bind assembly sample to recorded call`

代码和测试：`src/agent/contracts/{__init__,bundle,declarations,tasks}.py`、`src/agent/runtime_snapshot.py`、`tests/test_building_contracts.py`、`tests/test_runtime_snapshot.py`。

阶段 0 契约样例：`AI_agent/logs/experiments/2026-10-02_harness_stage0/build_samples.py` 及 `tests/fixtures/harness_stage0/` 根下六份建筑 JSON。历史实验源目录只读，没有覆盖原产物。

## 验证

- `tests/test_building_contracts.py`、`tests/test_runtime_snapshot.py`、`tests/test_harness_stage0_samples.py`、`tests/test_harness_stage0_boundaries.py`、`tests/test_harness_stage0_provenance.py`：63 passed。
- 加上阶段 0 核心与历史检查：90 passed、2 failed。两项失败均来自并行底座严格化尚未同步的测试/生成物：strict `RoleDefinition.model_validate` 仍收到 list；历史映射输出与 checked-in JSON 因核心费用形态变化不一致。已把精确位置交主代理处理，本包未越界修改底座核心或历史映射。
- `git diff --check`：本包文件通过。
- 工作模型、Paratera、DeepSeek、GLM、网络调用：0。

## 限制与后续

- 当前快照只接受保存的 `source_bim_v1/v2`；离线手写的阶段 0 `saved_excerpt` 不是正式源 BIM，不能冒充快照输入。
- `source_bim_v1/v2` 保存绝对开口顶点，因此生成器核对几何、宿主和连接，但不从旧计划参数重新执行整个几何内核。这样既不覆盖权威保存几何，也能发现宿主与开口脱离。
- 生成器只证明保存源 BIM 内部关系一致，不能证明图纸识读、空间推断或建筑质量正确。
- 数字字段选择器从保存 JSON Pointer 取值；若后续需要稳定的派生尺寸，应单独定义有身份的确定性派生规则，不能让调用方提交计算结果。
