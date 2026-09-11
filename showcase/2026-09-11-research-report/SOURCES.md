# 图片与仿真工具来源

## 图片

- `sm25-{1f,2f,North,South,East,West}.png`：仓库 `case_tests/e2e_tests/sm25-L_anchor/case_data/` 中六张原图的原字节副本。第 5 页同时显示两层平面与四个立面。
- `sm25-model.png`、`voimatalo-model.png`、`voimatalo-input.png`：既有真实查看器的显示截图；用于静态说明及 PDF。实际网页模型来自 `embeds/`。
- `simulation-reference.png`：复用旧 showcase 的 `shot1-building-simulation-clean.png`，只作第 2 页仿真结果示例，不是 sm25 或 Voimatalo 的仿真输出。
- `language-input.png`：复用旧 showcase 的 `Natural Language.png`，作文字意图输入的视觉例子。
- `aerial-reference.jpg`：[A-lehtien toimitalo 1](https://commons.wikimedia.org/wiki/File:A-lehtien_toimitalo_1.jpg)，Harria，2026-08-21，赫尔辛基 Kulosaari 的 A-lehtien 办公楼倾斜航拍。[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)，保留原文件，页面仅按框显示。此图为 Google Earth 类观察视角的真实航拍参考，不是 Google Earth 截图。详细下载、原始链接和校验见 [记录](../../AI_agent/logs/experiments/2026-09-11_research_slides_revision/aerial_reference/README.md)。

Voimatalo 的真实摄影测量单体来自 SUM / Helsinki，原 GLB 格式、来源及轻量 BIM 处理范围见 [模型说明](demos/textured-mass/README.md)。完全推理栏仅为输入参考图，没有以该航拍图新增生成建筑模型。

## 后端名称

第 4 页使用实际工具名称；EnergyPlus 标为已有通路，其余是拟扩展适配方向，没有因此新增后端代码或仿真运行。

| 图中名称 | 对应领域与官方来源 |
|---|---|
| EnergyPlus | [全建筑能耗仿真](https://energyplus.net/) |
| Radiance | [光环境、照明与采光仿真](https://www.radiance-online.org/about) |
| OpenFOAM | [计算流体力学](https://openfoam.org/) |
| Pachyderm | [建筑声学仿真](https://www.orase.org/pachyderm) |

上述工具名称与领域于 2026-09-11 核对官方页面。只在用户主动点工具名称时打开官网；汇报正常打开不请求这些网站。
