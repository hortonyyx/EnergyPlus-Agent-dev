# 2026-09-10：部分推理阶段 1 输入准备

本实验完成两项输入准备，不把开发助手准备输入记作产品生成成功：

1. 从已有 Helsinki 城市瓦片中选定并裁出有公开用途依据的 Voimatalo 办公单体；
2. 从 `sm24_anchor` 隔离出只给四向立面的受控缺信息输入，供主助手启动首份部分推理生成。

## 实际产物

- 真实单体：[输入与来源](../../../../case_tests/textured_mass/single_buildings/voimatalo/README.md)，含 `input.glb`、完整 UV 离线查看页、三张面中心采色范围概览、公开轮廓叠图、`selection.json` 与 `inspection.json`。
- 可复用裁剪工具：`case_tests/textured_mass/prepare_single_building.py`。输入必须是先前去标签的瓦片 GLB，并由公开轮廓配置显式限定范围。
- 受控对照：[sm24 只给立面](../../../../case_tests/partial_inference/sm24_exterior_only/README.md)，含四张 PNG 和输入契约。

Voimatalo 用途由 Helsinki 市博物馆的公开建筑条目核实，范围取 OpenStreetMap way 15242619。按 Helsinki 城市模型公开局部原点把 OSM 轮廓换到米制坐标后，与瓦片可见外墙对齐。裁剪使用轮廓外扩 0.35 m 的三角面中心，不用 SUM 标签。输出 12,520 面、8,242 顶点，范围约 48.46 × 62.65 × 34.27 m，面数与纹理映射重新加载通过。没有被目标面引用的图集像素被中性化，目标面像素和 2 px 余量再有损重编码成 JPEG quality 95，不能报告逐像素往返。网格不闭合，楼脚可能保留狭窄上下文条带。

## 大资产引用与复制清单

| 资产 | 操作 | 进入 Git 的结果 |
|---|---|---|
| 主树忽略资产 `case_tests/textured_mass/derived/Tile_+1984_+2690/input.glb`，SHA-256 `10ed0a...b6ff` | 只读；按轮廓裁剪，没有修改源文件 | 单体 `input.glb`；保留目标面 UV 与被引用贴图像素，中性化未引用图集，移除 extras，无标签字段 |
| `sm24_anchor/case_data/{East,North,South,West}_view.png` | 原字节复制到隔离输入目录 | 四张立面；没有复制平面、prompt 的热区数、GT 或旧 run |
| 原始 SUM PLY/JPG | 未读取、未复制、未修改 | 无 |

## 验证与未完成

- `input.json` / `selection.json` / `inspection.json` JSON 语法通过，裁剪脚本 Python 编译通过。
- 源 GLB 哈希强校验；输出 GLB 重新加载的面数和贴图保留，属性白名单仅 `POSITION` / `TEXCOORD_0`，无 extras 或标签。
- 三张面中心采色范围概览和公开轮廓叠图已由开发助手实际打开，只用于检查范围/方向，不能精读门窗纹理。完整 UV 离线 HTML 已生成并检查 JavaScript 语法；环境没有 Chromium、Chrome 或 Firefox，因此交互浏览器运行明确记为未验证，没有安装共享依赖。
- 本任务没有模型、DeepSeek、付费 API、EP 或手写内部房间。主树后续独立运行的生成/评价证据由主助手记录，不写回本准备实验成绩。

下一步是让产品 Agent 读取 Voimatalo 外壳/贴图并生成首份有来源说明的通用 BIM。真实内部无独立参照，首份结果只能评价外部约束、几何自洽和假设合理性，不能报告恢复了真实房间。

后续主树验证：完整 UV 浏览器显示与旋转已通过，见 [独立浏览器记录](../2026-09-10_parallel_modelling_browser_qa/README.md)。准备时的检查报告不回写成后来的成绩；裁剪工具另补新目录保护，避免复现覆盖既有素材。
