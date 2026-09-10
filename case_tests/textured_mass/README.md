# 带贴图三维体量：首批素材

2026-09-10 已实际取得 **3 个真实城市网格片区 + 2 个人工建模对照**，共 8 个下载文件、149,624,062 字节。当前完成输入获取、几何/纹理检查和预览，未运行 BIM 生成，尚未裁出单栋目标。三片真实素材均来自同一城市和数据系列，不代表跨地区泛化。

[可查看案例与调研证据](../../AI_agent/logs/experiments/2026-09-10_textured_mass_survey/README.md) · [路线判断](../../AI_agent/design/textured_mass_route.md)

| 本地 ID | 内容与用途 | 实际三角面数 | 贴图 |
|---|---|---:|---|
| `Tile_+1985_+2693` | 道路分隔的独立体量；建议先选择其中右侧完整主体，识别用途仍需补信息 | 217,967 | 8192 × 4096 |
| `Tile_+1984_+2690` | 连续多层街区、多内院；试验建筑范围、院落与相邻楼体的区分 | 385,685 | 8192 × 4096 |
| `Tile_+1986_+2690` | 连续街区及大片树木遮挡；试验缺失外墙、周边场景和显式假设 | 460,115 | 8192 × 8192 |
| `village_house` | 小住宅人工建模对照，不能称作真实摄影测量样本 | 738 | GLB 内嵌材质与图片 |
| `pbr_building` | 多层建筑人工建模对照，供导入/贴图/门窗工具检查 | 9,654 | glTF 外部图片，7 个网格 |

三片 SUM 网格包围盒均为约 251.9 × 251.9 个坐标单位（数据系列为米制城市网格）；坐标覆盖含瓦片边沿，不以页面中的“250 m²”文字作为面积真值。高程极差包含地面、树木等，不能作为单栋楼高。完整坐标参考系与地理原点尚未校验，不从瓦片名直接推绝对位置。

## 位置与输入边界

- `raw/`：原始下载文件，仅本地保存；SUM 的 PLY 包含评测标签，不可整包直接交给生成 Agent。原件不得改写。
- `derived/<tile>/input.glb`：重新构造的纯几何/UV/图片输入，清除了标签、标注颜色、分段 ID、置信度和原始 PLY 元数据。局部化原点及坐标换轴见 `inspection.json`；没有补墙、补洞、简化或生成内部。
- `derived/<tile>/viewer.html`：复用仓库 Three.js 和轨道控制器的离线贴图查看页；旋转/缩放、网格和贴图开关。已检查脚本语法，当前环境未实际运行浏览器。
- `acquisition.json`：公开地址、大小、SHA-256；`inspection.json`：加载、导出、纹理及去标签检查；`control_inspection.json`：对照样本检查。
- `melbourne_regions.json`：另一个官方数据源的 570 个公开区域链接；`melbourne_download_probe.json` 记录两次 HEAD 200 及文件大小，未下载完整墨尔本网格。

大文件和派生查看页通过本目录 `.gitignore` 留在本机；Git 保存清单、脚本、检查结果、缩略预览和说明。新机器需重新获取素材后生成本地查看页。

```bash
python AI_agent/logs/experiments/2026-09-10_textured_mass_survey/fetch_samples.py
python AI_agent/logs/experiments/2026-09-10_textured_mass_survey/prepare_samples.py
```

脚本使用已有 requests、numpy、Pillow、trimesh；不调用模型、付费 API 或仿真。下载脚本复用且校验已有文件，发现变动会停下并保留原件。准备脚本只处理三个 SUM 片区；PBR zip 解包是本轮临时检查，后续需要时用普通 zip 工具安全解包。

## 来源与署名

- 实景原始几何：City of Helsinki，城市模型官方声明 CC BY 4.0。[官方介绍](https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/helsinki-3d) · [城市数据目录许可](https://kartta.hel.fi/paikkatietohakemisto/pth/?id=266)。本次从 TU Delft 发布的 [SUM 数据](https://3d.bk.tudelft.nl/projects/meshannotation/) 取得；研究署名 Weixiao Gao, Liangliang Nan, Bas Boom, Hugo Ledoux，2021，DOI `10.1016/j.isprsjprs.2021.07.008`。SUM 的标注增量与城市原始数据分别记录，不把城市许可自动扩大到所有后续研究资产；本轮原包仅本地保留。
- 小住宅：verkhohlyad，House / Village house，Objaverse UID `c5e7d6c7b782404dad43bd5806f5d8ed`。归档对象元数据为 `license: by`，[Objaverse 官方数据卡](https://huggingface.co/datasets/allenai/objaverse) 说明对象 CC-BY 4.0；精简来源见 `house_metadata.json`。模型真实尺度未证实，不能把 GLB 数字直接当米。
- PBR 建筑：volkanongun，OpenGameArt 由 brylie 发布，CC BY 4.0。[原页面](https://opengameart.org/content/pbr-textured-building)。真实尺度未证实。
- 墨尔本：City of Melbourne，Photomesh 2020，CC BY 4.0。[官方目录](https://data.melbourne.vic.gov.au/explore/dataset/city-of-melbourne-3d-textured-mesh-photomesh-2020/information/)。本轮只保存下载索引及可达性证据。
