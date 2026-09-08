# 2026-09-08d · GPT 接手：基线与 W#1 新题面矛盾停报

状态：**遵照本轮「题面不对就停下上报」暂停施工；不是四项修复完成报告。**
本轮已采用修订后的 `/opt/venv/bin/python` 命令。此次停报仅涉及 W#1 的零分判断。

## 你以为是 X，实际是 Y，证据是……

**你以为** `reading.plan_scale_origin_usable` 所说的 “the plan channel would score zero”
证明这份 as_drawn 产物存在必然零分的真缺陷，必须与 `dimensions_present` 的格式假红分开修。

**实际是** 本树标准入口已经按产物契约走独立的 as_drawn 评分分支；该分支消费
`observations.face_lines` 的米制位置和长度，不要求 legacy `scale_origin`。
题面所引用的同一个归档已经有非零平面分数，而且 `judge_packet.json` 已消费这些分数。
因此不能把旧门的警告文字当成新腿评分必为零的证据。

证据链（均为本树只读核查）：

1. `scripts/tool_scripts/run_stage.py:2404` 在 typed/legacy 评分前调用
   `_grade_as_drawn_reading_branch`，命中后直接返回。
   `:2324` 的分支复用 `vector_contract` 按产物契约分派；`:2359` 起将平面
   `C1_C2_targets_drawn_pct` 放入 `score_criteria`。
2. `src/agent/judge/as_drawn/flow_wiring.py:172` 的 `grade_as_drawn_plan` 调用原生
   `reading_grade.grade`；`src/agent/judge/as_drawn/reading_grade.py:127` 起实际读取
   `observations.face_lines[].constant_world_axis/pos_m/edges_m/runs_m`。
3. `case_tests/e2e_tests/sm25-L_anchor/run_wallhunt/0_reading/attempts/001/score_vs_gt.json`：

   | 产物 | 契约 | C1_C2_targets_drawn_pct | C2_length_coverage_pct |
   |---|---|---:|---:|
   | 1f_view | as_drawn_plan | 100.0 | 99.2 |
   | 2f_view | as_drawn_plan | 98.1 | 97.8 |

   同目录 `judge_packet.json` 的 `score_criteria` 包含
   `c1_c2_drawn_plan-F1: readout=100.0, passed=true` 和
   `c1_c2_drawn_plan-F2: readout=98.1, passed=true`。
   这些是具体评分指标，不能称为整条能耗管线的总分。
4. 当前 `1f_view.json`、`2f_view.json`、`East_view.json` 与归档 `output.json`
   对应对象逐对象相等。两张平面均无顶层 `scale_origin`，却有
   `observations.calibration.mm_per_px/world_zero_px`：分别为
   `21.635842 / [281.763, 1234.682]`、`21.808431 / [240.754, 1258.205]`。
5. `src/validator/checks/view_manifest.py:104` 对这些新契约对象仍调用
   `parse_reading_view`；`src/agent/reading/schema.py:122` 默认
   `image_kind="plan"`，并默认 `strokes=[]`、`dimensions=[]`、`scale_origin=None`。
   实测 East 立面也被解析为 `plan` 和两个空数组。
   因而同一个零分警告出现 **6 次，包含全部 4 张立面**。

**证据边界**：本轮未重新运行 judge 开启的完整 flow。现有 `run_wallhunt/run_config.yaml`
确实是 `judge.mode: off`，所以既有评分工件不能冒充本轮总验收通过。
不过它们与当前代码的契约分派一致，已足以推翻「缺少 legacy 字段必然导致这条
as_drawn 平面评分为零」的具体断言。没有擅自给新产物添加旧字段，也没有改评分器或放宽门。

## 基线与工作树

- 固定工作目录 `/tmp/w1_flow_glm`，分支 `wt/09.07h_w1_flow`。
- 接手 HEAD `673e0405`；W#3/W#6 的既有提交在历史中，未重做。
- 接手时暂存区、已跟踪文件无改动，仅未跟踪的
  `case_tests/e2e_tests/sm25-L_anchor/run_wallhunt/`；该目录未修改、未暂存。
- 未发现本树或父目录适用的 `AGENTS.md`。
- 导入自检输出 `/tmp/w1_flow_glm/src/agent/__init__.py`，断言通过。
- 全量结果：**4049 passed, 2 skipped, 13 xfailed, 211 warnings in 491.80s (0:08:11)**；
  退出码 0，**0 failed**。前序半份工作在本次全量基线上没有失败；本轮没有安装输出。

本轮实际执行的基线命令：

```bash
cd /tmp/w1_flow_glm
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python -c 'import src.agent; from pathlib import Path; p = Path(src.agent.__file__).resolve(); print(p); assert p.is_relative_to(Path("/tmp/w1_flow_glm"))'
PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python -m pytest -n 6 -q
```

## 已核实的格式检查对照表

范围是 `check_reading_stage → parse_reading_view → check_reading_view`，以及其每视图检查。
下表记录现有读取字段和可观察结果；**不是已实施的适配方案，也不宣称完成全项目消费面审计**。
检查 ID 均省略 `reading.` 前缀；PASS/N/A 是现有归档读数，不能据此认定新格式证据合格。

| 检查 | 实际使用的 legacy 字段 | 新格式对照／现有结果 |
|---|---|---|
| `plan_scale_origin_usable` | `image_kind`, `scale_origin.world_{x,y}_m` | 平面有 `observations.calibration` 和米制 face lines；立面有顶层 `calibration`；6 次 FAIL，连立面也被误判为平面 |
| `dimensions_present` | `dimensions[]` | 平面链在 `observations.calibration.{x,y}.cum_mm`；立面是 `calibration.{x,z}`、`dimension_witnesses`；6 次 FAIL |
| `raw_field_presence` | 原始 `uncaptured` 存在性 | 新产物顶层有 `ledger`；检查没有消费它；6 次 FAIL。ledger 是否满足所有旧审计语义尚未裁定 |
| `stroke_provenance_coverage` | `strokes[].pen/provenance` | 平面结构在 `observations.face_lines` 与 `hypotheses`；检查看到 0 strokes；6 次 FAIL，不能据此断言原生证据缺失 |
| `stroke_ids_unique`, `pen_kind_valid`, `no_topology_fields`, `nondegenerate_geometry` | `strokes[].id/pen/kind/geometry` 与 extra 字段 | 空 strokes 导致全部 PASS，未量到新格式几何 |
| `dimension_ids_unique`, `dimension_parseable`, `axis_endpoint_consistent`, `dimension_endpoints_in_bounds` | `dimensions[].id/value_m/text/axis/from/to` | 空 dimensions 导致全部 PASS，未量到原生尺寸链 |
| `facade_fields` | `image_kind`, `facade.view_facade` | 原生立面有 `facade_label`；但默认 plan 导致 6 次 N/A，立面检查被漏掉 |
| `uncaptured_present` | `uncaptured` 与 legacy 兼容位置 | schema 默认空列表使 6 次 PASS；原始字段缺失由另一检查报出；并未验证原生 ledger |
| `dimension_p1a_fields` | `dimensions[].text_verbatim/value_m/chain_id/role/order` | 原生链不采用该数组形状；6 次 N/A（no dimensions to inspect） |
| `dimension_chain_closure` | `dimensions[].chain_id/axis/role/value_m/order` | 平面校准链确实存在；6 次 N/A（no chain_id-tagged dimensions），没有检查那些链的闭合 |
| `dimension_derived_refs` | `strokes[].provenance/dimension_refs` 和 dimensions ID | 6 次 N/A（no dimension_derived strokes）；不等于验证了新格式引用 |
| `ocr_anchors_in_bounds` | `ocr_texts[].anchor` 与 strokes 结构范围 | 默认空 OCR 列表导致 6 次 PASS；没有检查原生见证位置 |
| `room_label_roles_valid`, `room_label_basis_valid`, `room_label_anchors_in_bounds` | `room_labels[].role/basis/anchor` | 默认空列表使函数提前返回，归档中没有对应行；原生可选语义是否适用尚未裁定 |
| `stroke_dimension_consistency` | strokes 墙位置与 dimensions 累计位置 | 6 次 N/A（no chain_id-tagged x/y dimension cumulative positions） |
| `door_heal_traced` | `strokes[].note` 与 uncaptured | 6 次 N/A（no healed door openings）；未建立原生账本的等价检查 |
| `partition_on_window_jamb` | legacy strokes 几何 | 只登记现有 6 次 N/A；属于本轮禁改的窗相关范围，未修改 |

另外，`check_calibration_evidence`（`reading.py:1603`）读取 CV calibrator sidecar，
并非读取 legacy `ReadingView` 字段；它是独立入口，不在上述每视图链内。
manifest 覆盖检查按产物 ID 集合工作；该步也不是把新产物强转旧字段的环节。

归档中的 FAIL 计数准确为四类各 6 条，共 24 条。
除了假红，表中还发现空壳导致的 PASS 与 N/A，不能用清除 24 条警告代替契约适配。

## 工件定位与可复核性

以下 SHA256 对应 `run_wallhunt/0_reading/attempts/001/` 的接手时工件；未重新生成它们：

| 工件 | SHA256 |
|---|---|
| `output.json` | `1fadfbb39d92567707a4f8a4f1c173fe297b0e1828a54aa023972286686de91c` |
| `checks.json` | `4213f371220eb791938edbd54749aa11145d46ab7c83038b0258b9e371080b2e` |
| `score_vs_gt.json` | `030a8da2be8fbe20e078601ef27efd08c329013718ba7191ba64e9cf63e8f6b4` |
| `judge_packet.json` | `1fe80b4810beff19215679dcf56c8433e7e193f883f8cba1935bc1bf87cee339` |

已有 `tests/test_j_grade_wiring.py::test_plan_view_grades_through_the_wire` 使用真实
平面产物和签名 DXF，明确断言 `C1_C2_targets_drawn_pct > 0.0`；属于此次全量基线。
未新增或改写测试来迎合这个判断。

## 未完成范围与凭据来源

W#1 的生产修复、W#4 过期失败记录清理、W#5 归档异常保留报告均未开工。
W#2 的完整逐字可重跑 flow 序列也未验收；下面只记录已授权的凭据来源前置命令，
不将它冒充完整 flow 验收命令：

```bash
cd /tmp/w1_flow_glm
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
export PYTHONPATH=/tmp/w1_flow_glm
```

后续 flow 使用 `/opt/venv/bin/python scripts/tool_scripts/run_stage.py` 标准入口。
未读取、输出、复制或提交 `.env` 内容。W#7、窗相关实现和另一工作树均未修改。
本轮无生产代码变更；写本报告前没有待提交代码，仅提交此明确路径的文档。

待派工方修订的是 **W#1 的真假分类与验收表述**：旧 `scale_origin` 检查应按实际消费
契约评估，不能预设该缺字段已让 as_drawn 得零分。确认前按停报要求不继续四项施工。

## 我这次最薄弱的一处

非零分数读数来自接手时既有归档，虽已核对产物一致性、当前标准入口分派和全量内的真实
评分测试，但本轮没有新跑 judge 开启的完整 flow；因此不能证明整条能耗管线已经跑通出分。
