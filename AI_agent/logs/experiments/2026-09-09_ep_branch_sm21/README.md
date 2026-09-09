# 同一份源 BIM 的 EP 分叉：sm21 实跑

2026-09-09。当前证据为 **run02**：共同主干输出源 BIM 后，EP 分叉直接读取该文件，派生 14 热区 / 100 面 / 15 窗，EnergyPlus 25.1 全年运行成功，**0 severe、4 warnings**。源 BIM 仍为 14 空间 / 84 完整边界 / 15 窗，与上一程停点文件字节一致。

- [源 BIM 查看](flow_bim/viewer.html)、[源模型](flow_bim/source_model.json)
- [EP 运行报告](run02/report.json)、[实际完成文件](run02/EP/eplusout.end)、[完整警告](run02/EP/eplusout.err)
- [派生 IDF](run02/model.idf)、[源对象对应关系](run02/source_mapping.json)、[EP 几何](run02/building_geometry.json)
- [几何检查](run02/geometry_checks.json)、[IDF 配对检查](run02/idf_pair_checks.json)
- [输入来源](inputs/provenance.json)、[整体证据](evidence.json)、[完整 EP 输出压缩包](run02/EP_outputs.tar.gz)

## 输入与诚实边界

几何来自上一程保存的源 BIM；该 BIM 的上游是历史已接受 reading/correction 重放，不是本轮原图冷启动。物性复用 sm21 07-02 成功案例中的材料、作息、负荷和理想负荷系统，先移除全部 Zone、建筑表面、窗及旧坐标设置，再单独保存无几何模板。历史模型只提供源空间 ID 与物性热区名的绑定，不向新 EP 后端提供任何几何。没有模型调用，也没有新增人工源模型确认。

run02 的 4 条警告分别为：未指定时间步（默认每小时 4 步）；要求设计日但未提供设计环境；采用天气文件地点覆盖模板地点；未提供地温（默认全年 18℃）。这是几何与后端贯通实验，物性尚未校准，不以仿真成功证明源分区准确或能耗准确。

首版一个源空间派生一个热区，最低源楼层假设接地。源北向存在时覆盖物性模板北向；未知时记录采用模板值的假设，采用 Relative 坐标与全零热区平移/旋转。复用的 EP 写入器将坐标保留 4 位小数；源坐标不改。切配端点 1 微米数值裁剪按明确的 2 微米覆盖容差核对，不许可源隔断、开口或关系被丢弃。

支持正交空间和外窗。显式门/空开口、非正交形状、一般 HVAC 模板，以及不满足当前切配和源覆盖核对的模型会明确停止。完整编辑和物性修改交互仍待设计。源保真沿用上一程独立评价：sm21 内部未见拆并信号，但外边界参考面差异仍待核对。

## 复现

从仓库根执行，输出必须使用新目录。已有停点直接接 EP，无上游或模型调用：

```bash
python scripts/tool_scripts/run_stage.py backend-ep \
  --source AI_agent/logs/experiments/2026-09-09_source_bim_run04/flow_sm21_bim/source_model.json \
  --physics-template AI_agent/logs/experiments/2026-09-09_ep_branch_sm21/inputs/physics.idf \
  --zone-bindings AI_agent/logs/experiments/2026-09-09_ep_branch_sm21/inputs/zone_bindings.json \
  --out AI_agent/logs/experiments/NEW_EP_BRANCH \
  --with-ep --epw data/weather/Shenzhen.epw
```

run02 实际通过 `flow --target ep` 验证：复制上一程 `flow_sm21_run` 到本目录 `flow_run`，RUN 传其绝对路径；`--bim-out` 为本目录 `flow_bim`，`--backend-out` 为 `run02`，使用上述物性/绑定，附 `--with-ep --judge off`。reading/correction 接受产物哈希不变，无旧 Stage 2–5 目录。完整 stdout 保存在 [flow_stdout.txt](flow_stdout.txt)。重新演练请复制上游 run 并换用新的两个输出目录，不能覆盖本次证据。

## 验证和早期产物

234 项相关检查通过，另 27 项补充检查通过（含重叠的 EP 检查，不累计为 261 项）；日志见 [234 项](tests_234.txt) 与 [补充](tests_27_supplement.txt)。覆盖源窗修改实际进入 IDF、源文件不变、禁止旧几何混入物性、源墙丢失/接触丢失/相邻关系错误/未建项拒绝、源北向驱动 IDF、共同主干 EP 路由。普通测试离线。

run01 是独立 `backend-ep` 的首次成功运行，早于明确 Relative 坐标约定；模板北向恰为 0，因此也成功且没有几何差别。保留其报告与全部 EP 原始输出，不覆盖它。一次 flow 调用误传相对 RUN，解析进 case 内错误目录，读图检查在任何模型/EP 调用前停止；该目录已完整移动到 `failed_relative_run`，stdout 单独保留。后续改用绝对 RUN，run02 才是完整命令成功证据。

两个 `EP_outputs.tar.gz` 均已逐文件比对原始输出字节；便于阅读的 end/err 文件另行保存。实现版本和产物哈希见 `implementation.json`。
