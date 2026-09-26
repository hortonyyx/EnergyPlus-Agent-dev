# Voimatalo：内院被裁突出体补全（09-26 Opus 5.5 开发候选，待用户验收）

**状态：待用户验收的开发候选。** 在 09-25 candidate_01（80 空间 / 300 窗 / 88 门，尚未验收）之上，只补一处实质外部缺失：内院长墙南段被“单体裁切”一起切掉的突出体，以及它所贴的南核院面。09-25 的其余空间、窗、门逐项不变。不是工作模型成绩，也不是冷启动；开发助手看过全部旧候选。

## 入口

[对照与旋转查看](result_02/index.html) · [原网格叠图与剖切](result_02/observations.html) · [源BIM](candidate_02/source_model.json) · [源检查报告](candidate_02/report.json) · [方案声明 v3](case_plan_v3.json)（由 [build_plan_v3.py](build_plan_v3.py) 从 09-25 v2 派生，改动清单在 `revision_from_v2`） · [量测记录](observations/protrusion_measure.json) · [验证](validation/candidate_02_validation.md) · [交接](HANDOFF.md)

对照页里每张图三格：原扫描 ｜ 09-25 候选叠在原扫描上 ｜ 本轮候选叠在原扫描上；另有南端局部平面新旧对照、塔体方向的离线查看截图（`validation/candidate_02_browser_qa/tower_*.png`）。

## 原扫描里看到了什么（观测）

只读原单体 `input.glb`（未用父瓦片、OSM、GT 或图纸），新脚本 [observe_protrusion.py](observe_protrusion.py) 渲染近景并做网格剖切：

| 证据 | 数值 | 文件 |
|---|---|---|
| 内院长墙上的“洞” | y ≈ -26.1 … -22.0（z 7–25 m 各层中位），从地面到约 27 m 每层都有；从内院看进去直接打到沿街墙背面 | `protrusion_measure.json` → `courtyard_hole_from_parent_buffer`（复用 09-25 保留的像素缓冲） |
| 洞口北侧侧墙残片 | 在 y≈-21.9 从院墙伸出，到 x≈2.38，高 1.4–25.6 m | `protrusion_sections.png`、`prot_north_stub_grid.png` |
| 洞口南侧侧墙残片 | 在 y≈-25.9 伸出到 x≈1.3，高 2.6–26.05 m | 同上 |
| 附属低体南墙 | y≈-21.75，从 x≈2.3 往东是扫描到的**朝南外墙**（法向全部朝南，带两扇高窗 z≈4.3–6.0） | `annex_south_face_grid.png` |
| 俯视 | 洞口外侧 x>0.8 没有任何屋顶残留 | `prot_top_grid.png` |
| 紧挨洞口南边的院面 | 一列多格玻璃（y≈-27.9…-26.0，略微内凹），有的层扫到、有的层是破洞 | 09-25 `court_strip_hi_grid.png` |

## 怎么判断（白话）

- 两侧都有从墙面伸出来的侧墙、洞口整层整高一致、屋顶也被一起切掉——这是一个**贴在内院墙上的全高小塔体被裁切掉了**，不是透空、不是通道，也不是一面缺资料的平墙。
- 宽度由两侧残片直接给出（约 4.2 m）。伸出多深：北侧残片说明至少到 x≈2.4；附属低体南墙从 x≈2.3 起是露在外面、带窗的外墙，说明塔体不可能再往东伸太多（不超过约 2.9）。取东面 x=2.5，即深 1.7 m（不确定范围约 1.6–2.1 m）。
- 高度：残片顶在 25.6–26 m，取与主屋面同高 25.25 m，多出的部分当女儿墙。
- 用途：4.2×1.7 m 的全高窄塔，紧贴 09-25 判为“电梯/服务核”的南核、位于南屋顶凸起（机房读法）旁边，读作**电梯井塔**；南核随之改读为电梯厅＋可放次楼梯的核心，旁边那列多格玻璃正好像楼梯间采光窗。主要替代读法：卫生间/服务竖向叠层或管井（那样东面可能有小窗）。

## 生成了什么（推断）

- 新增 1 个连续竖向空间 `TOWER_C_lift_tower`（x 0.8–2.5、y -25.9–-21.7、z 0–25.25），不加中间楼板；F1–F7 楼层外轮廓各加上这 7.14 m² 塔体，其他楼层/附属低体/屋盖不变。
- 每层一扇门从南核进塔（F1–F7 共 7 扇，代表电梯厅门，位置尺寸是假设）。塔体西面与南核整面相邻（106 m²），北面首层段与附属低体相邻（11.4 m²），其余是外墙。
- 塔体外墙无窗——这是“电梯井”读法的结果，不是扫描看到了实墙（东面和屋顶已被裁掉）。
- 南核院面多格玻璃列在 F2–F7 补为 6 组逐层推断窗（y -27.75 … -26.15，窗台/窗顶沿用同层旁边已观测院面窗）。
- 南核院面原来 6.1 m × 25.25 m（约 154 m²）的“未知”区域缩到只剩玻璃列首层段 2.0 m × 5.6 m（约 11 m²）；退台层塔顶以上的扫描洞仍未知（理由已更新）。

## 前后差异（相对 09-25 candidate_01）

| 项 | 09-25 | 本轮 candidate_02 |
|---|---|---|
| 空间体 | 80 | 81（+塔体） |
| 窗 | 300 | 306（+6 组玻璃列推断窗；原 300 组坐标与宿主全部不变） |
| 门 | 88 | 95（+7 扇南核—塔体门；原 88 扇不变） |
| 楼层外轮廓 | — | F1–F7 各加 7.14 m² 塔体矩形；其他完全相同 |
| 含未知区域的边界 | 15 | 15（个数不变；南核那一处面积从约 154 m² 缩到约 11 m²） |
| 南核 | “电梯/服务核” | 同一几何，文字改为“电梯厅＋次楼梯，电梯在塔体” |
| 源摘要 | `56b6a912…` | `6e2b4688…`（完整值见验证报告） |

## 验证

一次运行，除 README 链接（写本文前）外全部通过；写完本文后重跑结果见 [validation/candidate_02_validation.md](validation/candidate_02_validation.md)。复用 09-16/09-25 已有检查，另加：方案重建和装配字节一致重放、09-25 全部空间/窗/门逐项不变、外轮廓只多出塔体矩形、塔体接触面积/每层一门/外墙无开口/位置在量测范围内、无中间楼板、从室外经门可达、离线浏览器三种模式与对准塔体的截图。塔体宽 1.7 m 不适用房间 2.4 m 宽度规则，已在检查里单列豁免理由。未运行 pytest：没有改公共源码。

技术检查通过不等于用户验收。

## 重放

在仓库根执行（输出目录须不存在；浏览器检查需要既有 `/tmp/ep-bim-browser-qa` 环境）：

```bash
E=AI_agent/logs/experiments/2026-09-26_voimatalo_opus_completion
PYTHONPATH=$PWD /opt/venv/bin/python $E/observe_protrusion.py --out /tmp/voim26-obs
PYTHONPATH=$PWD /opt/venv/bin/python $E/build_plan_v3.py --out /tmp/voim26-plan.json
PYTHONPATH=$PWD /opt/venv/bin/python $E/assemble_candidate.py --plan $E/case_plan_v3.json --out /tmp/voim26-c2
PYTHONPATH=$PWD /opt/venv/bin/python $E/package_result.py --candidate /tmp/voim26-c2 --out /tmp/voim26-r2
PYTHONPATH="$PWD:/tmp/ep-bim-browser-qa/lib/python3.12/site-packages" PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /opt/venv/bin/python $E/verify_candidate.py
```

装配器是 09-25 装配器的副本，只多两点：推断窗可带各自依据；`extends_storey_footprint` 让院外塔体并入所跨楼层外轮廓（房间分区仍只按原冻结外壳裁切）。

## 待用户决定 / 未完成

- 是否认可“被裁的是全高电梯井塔”的读法；若改判卫生间/服务叠层，只需把塔体改成逐层小间并在东面加推断小窗，其余不动。
- 塔体深度 1.7 m 只在约 1.6–2.1 m 内受约束；需要更准时可补一张内院照片或平面。
- 仍未处理：短翼内院东端扫描洞（x>15.3）、退台两端、玻璃列首层段、塔顶以上的扫描洞；09-25 遗留的内部组织与贴邻山墙条件仍待用户核。
- 验收通过后才提炼方法交工作模型；本轮未运行任何工作模型。

Astra合并前另校正继承的后端断言及推断措辞，几何不变；详见[协调复核](coordinator_review.md)。
