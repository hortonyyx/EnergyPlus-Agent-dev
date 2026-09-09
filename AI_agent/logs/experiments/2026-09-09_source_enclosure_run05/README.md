# 通用源 BIM：开敞与未知围护

[查看三个场景](index.html) · [汇总报告](report.json) · [代码与验证范围](implementation.json) · [测试日志](tests.txt)

本次为历史 sm21 几何上的明确受控例，不是原图灰空间识读，不改变旧 reading/correction。两项开敞例显式标记走廊 semi_open；未知例仅记录西侧信息未知，不擅自补空间类别。原有 14 空间 / 84 完整逻辑边界 / 15 窗全部保留。

| 场景 | 西侧几何表达 | 当前结果 |
|---|---|---|
| [整侧开敞](open_corridor/viewer.html) | 6 m² 逻辑父面保留，实体面为 0；1 条对外开敞连接 | 源几何通过 |
| [矮墙上部开敞](parapet_corridor/viewer.html) | 1.1 m 高矮墙 2.2 m²；上部开敞 3.8 m²；1 条对外连接 | 源几何通过 |
| [整侧围护未知](unknown_side/viewer.html) | 6 m² 琥珀色未知面，未当成开敞或新连通 | 源几何可查看，warning、围护信息不完整 |

查看器可切换完整逻辑边界、开敞/未知区域轮廓；点轮廓查看来源和假设。未知填充面随墙面开关。HTML 使用原有 Three.js CDN；本机无浏览器，未做 WebGL 截图验收。附图仅由显示投影生成西侧正投影，已核对矮墙高度和面积，不代表浏览器效果。

全部场景通过实际 `flow --target source-bim --enclosure-input ...`，每个场景的命令与 stdout 单独保存。基准 v2 与此前保存的源文件逐字节相同；读取/校正已接受输出摘要未变，没有旧 Stage 2–5、模型或求解器调用。已有上游目录中附带的历史 GT 图/分数不是此次生成依据或新评价结果。

新 v3 只增加通用几何语义；现有 EP 分叉直接拒绝 `source_bim_v3`，没有静默封墙，也没有运行空气交换/遮阳。关闭门与普通 v2 的已有 EP 行为由相关回归覆盖；本轮没有重复全年仿真。

107 项最终相关测试通过，16 条警告均来自既有测试 fixture 缺 run_config 的默认提示。覆盖源区域内外连通、共享区域中真实围护内孔、窗门冲突、非法区域、过期声明、原始声明保存、源/显示面积、未知告警和旧 EP/flow 兼容。早期及各助手局部测试与此重叠，不累计。

## 复现与输入

```bash
python scripts/tool_scripts/diagnose_source_enclosure.py --out AI_agent/logs/experiments/NEW_ENCLOSURE_RUN
```

从仓库根运行，使用已有 Python 环境。脚本复用 `2026-09-09_source_bim_run04/flow_sm21_run`，生成新输出，不读取外部凭据或调用模型。声明示例：[整面](open_corridor_input.json)、[局部](parapet_corridor_input.json)、[未知](unknown_side_input.json)。全部通过 `base_source_model_sha256` 绑定基准；输出内有声明原字节副本与来源记录。

[过期声明反例](stale_rejected/report.json) 明确失败。早期 run01 的首次两侧示例与现有 W07 重叠，被正确拒绝；最终改用无窗的西侧，没有放宽重叠检查。run02/03 均在绘图辅助步骤因缺 matplotlib/字体退出；后来改用已有 Pillow 默认字体，没有增加依赖。run04 已完整成功，run05 对齐最后的连接内孔修复及报告连接计数。早期目录和说明保留，不覆盖旧产物。

尚未接入原图灰空间自动观测、楼板/顶板洞口、挑空、独立屋盖与一般非正交区域；停点编辑、遮阳细化、空气交换和物性仍另行设计。
