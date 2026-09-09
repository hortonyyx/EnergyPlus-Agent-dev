# 独立源 BIM pipeline：解除 EP 切配依赖

日期：2026-09-09。实现提交 `d6fd8732`。本次用户调整：暂缓停点编辑，先推进不含物性、不依赖 EP 切配的丐版 BIM 生成；直接修改、自然语言/结合及热工物性挂载修改留待统一设计。目标与排期已同步 project/design/workflow。

## 做成了什么

源模型可以从校正输入直接生成，不需要先产出 EP 的切配面。新增 `flow --target source-bim --bim-out NEW_DIRECTORY`，在正常 reading/correction 之后进入独立源生成；另有 `bim CASE RUN --out NEW_DIRECTORY` 重建入口和显式候选预览。旧默认 EP flow 保留，当前没有重写其后端。

`source_bim_v2` 保存楼层、源空间、完整边界、实际接触区域、门窗及两侧宿主、相邻/连通、来源、假设、冲突和未建项。长墙邻接多个房间时保存多个接触区域，不切源墙。权威源文件没有物性、EP 边界条件、一一配对面或显示映射。显示投影另做窗/门洞扣除、相交部分的重复显示隐藏，展开时恢复两侧；显示片映射原源边界。

源检查复用多边形合法性、边界框与可信 B5 窗宿主核验，另检楼层轮廓覆盖、空间重叠、完整开口宿主、声明连通一致、重复/相交开口与未解决观测。旧内核 0.1 m 最短边下限不用于源空间；65 mm 合法源短边回归通过。EP 旧检查仍在其原消费者生效，没有全局放宽。

## 实际输出与限制

[当前查看入口](../experiments/2026-09-09_source_bim_run04/index.html) · [完整报告](../experiments/2026-09-09_source_bim_run04/report.json)。在实现提交后独立新建 run04，记录实现文件摘要、输入摘要及命令。

| 输入 | 源空间 / 完整边界 | 窗 / 门 | 评价 |
|---|---|---|---|
| sm21 历史校正 | 14 / 84 | 15 / 0 显式门 | 源几何检查通过；独立内部拆并信号 0，外边界参考面差异仍待核对；无显式门不能当全图没有门 |
| sm24 旧错分区 | 11 / 66 | 11 / 0 显式门 | 仍是严重分区反例，独立评价 7 条拓扑发现 |
| sm24 历史辅助模型 | 8 / 52 | 11 / 1 辅助门 | 局部源几何通过，但独立分区对照仍有 3 条严重发现；房间数相同不能证明正确 |
| sm25 历史辅助模型 | 29 / 190 | 31 / 29 | 60 个已建门窗坐标全部保留；已有两组未建门继续阻塞；独立内部拆并信号 0，外边界差异仍待核对 |

完整源边界数与旧 EP 派生面数不同，不能把面数下降写成删墙。sm21/sm24 旧档案没有源开口 ID 附带文件时，对比全部窗三维顶点多重集；sm24 辅助与 sm25 逐源 ID 对比门窗顶点并核对源空间完全相同。sm21 源 ID/顶点另外有当前代码回归。

实际 `source-bim` flow 使用新的 sm21 run，仅导入已接受的历史 reading/correction，然后正常 CLI 恢复并输出源模型。上游两个输出摘要不变，未创建旧 2_modelling/3_split_pairing/4_mep/5_intakeoutput，也未创建人工确认。它是历史输入重建，不是原图冷启动。

## 验证与调试记录

最终 **223 passed**，15 个警告来自 flow 测试缺省 run_config，非源模型失败：

```bash
python -m pytest -q -n 2 tests/test_source_bim.py tests/test_source_model.py tests/test_geometry_viewer.py tests/test_c2_b5_artifact_trust.py tests/test_c2_b5_legacy.py tests/test_wall_openings.py tests/test_run_stage_flow.py tests/test_source_checkpoint.py tests/test_partition_evidence.py
python scripts/tool_scripts/diagnose_source_bim.py --out AI_agent/logs/experiments/2026-09-09_source_bim_run04
```

覆盖长边界邻接多室、错邻室/误连室外/跨接点门不强建、窗错层/内墙/越界/重叠、源空间漏失/重叠、65 mm 短边、层间接触、扣洞面积与显示重叠、源文件修改后的摘要拒绝、B5 可信输入与修改拒绝、历史 EP 合同不变、源目标正常 flow、实际输出空间参与独立分区评价。

调试先发现共用 `_cell_polygon` 仍含 0.1 m 下限，改为复用不带该用途下限的 `cell_polygon`，其合法性/边界框核验仍生效。两项旧测试假定查看 HTML 内联在指针文件，实际 Stage 2 已迁移至不可变快照；测试改为打开所指向的快照，保留原扣洞/重复窗断言。

run01 在报告脚本比较原输入顺序与按 ID 排序的源输出时触发字典相等断言；这不是源几何失败。随后让独立评价服务直接消费实际输出源空间，并覆盖错误楼层回归，避免只验输入。run02 完成三案例，run03 加入真实 CLI source flow；均为开发中间证据。run04 是实现提交后的当前复现，后续只从它引用当前结果，不累计重复测试成绩。

本轮模型、模型 judge、EnergyPlus 调用均为 0。只核对到本地 GLM 订阅配置存在，未作连通/额度/能力探测；默认 LLM 配置仍含 DeepSeek，不能直接拿来做下一轮冷启动。查看器内联脚本语法、源摘要及本地链接核对；未运行浏览器 WebGL 交互，全仓测试未跑。

## 下一项

接通目标档原图 reading 自动入口，再沿正常 correction 与 source-bim 出口产生当前冷启动模型。现 `_draw_reading` 仍只检查预先生成的观测；已有 isolation/reading toolbox/CV 可按实际需要复用。先一张平面/一张立面做有界探针，再 sm21 整案；用户已授权 Claude/GLM 现有订阅，任何 DeepSeek 调用仍需本任务专项同意，禁止隐式回退。

sm24 辅助 8 空间与参照的差异、sm25 两组门仍待从输入定位；不为了通过而改 GT 或删房/删门。完整源编辑、物性挂载修改、EP 后端消费 v2、非正交/挑空等仍未完成，按当前主线安排。
