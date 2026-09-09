# Stage 2 源模型确认与恢复

日期：2026-09-09。用户授权继续推进。实现提交 `76aad9fe`；[独立执行及查看入口](../experiments/2026-09-09_m1_source_checkpoint_run01/index.html)、[输入与范围](../experiments/2026-09-09_m1_source_checkpoint_run01/README.md)、[执行报告](../experiments/2026-09-09_m1_source_checkpoint_run01/report.json)。

## 结果与影响

正式确认从 Stage 3 后移到了 Stage 2 后。用户可以在源房间、边界、门窗形成可查看模型时确认，再进入下游序列化；不必先让仿真格式接受源模型才能产生确认版本。确认与恢复已实际接通，持久编辑和完整冷启动还未完成。当前是 M1 的有界流程改造，不代表 M0 所有几何/语义缺口已关闭。

sm21 复用历史 reading/correction，当前代码重建 14 空间模型，在 Stage 2 停下。未确认时尝试 Stage 3 被拒绝；使用明确标注的 `diagnostic:auto` 模拟确认后，自动定位 Stage 3，确定性序列化通过，上游 0/1/2 输出未重抽，源确认保持有效。该记录不是用户人工确认。

sm25 复用前一程 29 空间候选，只生成查看快照，确认被拒绝。2 条未建门记录及两条短边检查问题未被隐藏或放宽；无新审批记录，也未把源映射通过当成整图完整通过。

## 实现

- `source_checkpoint.py` 从接受记录读取 Stage 1/2，核对输出和检查文件摘要、当前报告及已有阻塞 judge；使用可信校正/B5 入口确定性重建，再比较源对象和实际显示几何。当前检查采用 run 冻结的档位，不依赖 Stage 3 输出或 EP。源映射严重问题、未建/未支持观测、未接受候选或不一致版本不可确认。
- 查看输出保存不可变 HTML、source_model、building_geometry 和 checkpoint 快照，当前指针另记文件摘要。确认入口必须提供实际所看版本 `--digest`，审批记录还绑定显示快照；源数据、接受记录、检查或显示文件变化后不能沿用旧确认。旧 2+3 摘要保持历史审计可读，不能授权新的源确认。
- orchestrator 在 Stage 2 检查之后停下，恢复进入 Stage 3。要求确认的策略也保护直接进入 Stage 3、4、5；缺少确认回调不会默认放行。自动实验继续显式记录 auto，不冒称人工看过。
- full validation 对已有新查看记录采用源确认状态，同时保留下游独立错误报告；没有新记录的旧 run 继续原审计配方。仅下游验证的既有隔离路径未改动。
- 失败候选有可用几何时尽可能提供带状态查看页，源对象及未完成项、检查文件可从页面打开；硬建模失败无几何时仍无法生成新模型。

## 验证与调试

最终相关测试 **171 passed、8 xfailed**（原有预期失败），命令：

```bash
python -m pytest -q -n 2 tests/test_source_checkpoint.py tests/test_step_orchestrator.py tests/test_run_stage_flow.py tests/test_validation_run_baseline.py tests/test_c2_b5_artifact_trust.py
```

覆盖实际 Stage 2 暂停/Stage 3 恢复、直接下游入口、7 类版本/文件变化的失效、旧审批不自动升级、快照校验、冻结策略、新审批与完整审计相互独立、历史 B5 接受链拒绝与仅下游隔离。CLI help 已核对新 `--digest` 必填和 `--geometry required/auto` 参数。

初次回归暴露旧测试仍在 Stage 3 造确认，以及若干 flow 测试以占位字典代替校正几何；已更新为有效几何和新的真实查看/确认入口，没有删除旧产物信任断言。新测试开发时一次把验证结果字段写成不存在的 passed 属性，已改为实际 Stage 3 报告断言。重复运行不累计成绩。14 个警告来自临时 fixture 没有 run_config、沿用默认配置。

固定 run 在实现提交后新建，报告记录代码版本和输入摘要。当前快照摘要、HTML 相对链接、内联脚本语法通过；详情见 [文件验证](../experiments/2026-09-09_m1_source_checkpoint_run01/artifact_validation.json)。模型/judge/EP 调用均为 0，未运行浏览器 WebGL 或全仓测试。没有用人工辅助产物报告冷启动能力。

## 下一程

完成一次有界的持久修改：修改源输入而非仅改显示几何，保留对象/来源，重新建模检查和查看，验证旧确认失效及重新确认后的恢复。已有 sm21 正向链可复用，sm25 的剩余两组跨 T 接点门另按已有证据定位。目标档冷启动、一般房间/墙面语义和新开口仿真出口继续列为未完成。

设计和操作说明已同步 architecture、implementation、run_case、详细计划与 roadmap；无本地独存项目事实，无新增临时树。保持一条 main，按正常提交推送交付。
