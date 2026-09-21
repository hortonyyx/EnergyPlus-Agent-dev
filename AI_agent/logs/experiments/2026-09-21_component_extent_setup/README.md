# 完整同色框范围的方法迁移

从上一程run08只采用端点、误认墙窗的失败出发，先做[开发原图探路](../2026-09-21_component_extent_developer_probe/README.md)，再给目标模型原两图与通用方法。开发选定的坐标、颜色、阈值、候选及分组没有送入工作模型；GT与旧BIM也未输入。

生产提交`d4d45d28`只修订现有工具说明与facade_correspondence参考：背景RGB参数也能选墨迹，如何检查过滤/完整范围、处理断框与同一开口内分格；无新算法、源修改或自动语义接受。14项相关检查通过，10.87秒：

```bash
python -m pytest -q -n 2 tests/test_pixel_region.py tests/test_pixel_region_overview.py tests/test_bim_agent_tools.py -k 'pixel_region or on_demand_reference'
```

新run10保留run08的局部任务、Sonnet medium和1200秒预算，要求实际查看连通块，并记录相关块组成/不组成物理开口的理由。颜色和种子仍由模型自己选。这是特定方法的迁移验证，不是整栋自主任务组织或稳定性实验。

```bash
python AI_agent/logs/experiments/2026-09-21_component_extent_setup/run_observation.py --out AI_agent/logs/experiments/2026-09-21_sm24_component_extent_run10 --timeout 1200
```

已有run目录拒绝覆盖；不要重复调用已有命令。只用现有Claude订阅、只读MCP，没有DeepSeek/付费API回退。`verify_observation.py`复用上一程验证并增加overview/region数值、返回图像和存盘的精确重放，语义另行根据原图评价。

本批run10已在477.77秒完成并通过一门三窗的水平原图复核，高度只查大窗；随后给Haiku单原East图的竖向窄任务run11，278.28秒仍错链/坐标，未采纳。[水平结果](../2026-09-21_sm24_component_extent_run10/README.md)与[竖链失败](../2026-09-21_sm24_vertical_chains_run11/README.md)分别保留，均没有新BIM。

```bash
python AI_agent/logs/experiments/2026-09-21_component_extent_setup/run_vertical_observation.py --out AI_agent/logs/experiments/2026-09-21_sm24_vertical_chains_run11 --timeout 600
```

上条仅记录已完成的实际命令。run11输入没有run10答案；用`verify_observation.py --run RUN --vertical-only`核其声明范围，不要求与竖向无关的横向比较。额外四次原始pixel_profile成功调用在run11/numeric_call_verification.json重放核对。
