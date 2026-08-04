# 批 D（判卷图恢复）+ R4-a（成绩分账）执行日志（施工 = Claude 侧执行档，独立 worktree）

派工单：[2026-08-04_batchD_and_R4a_dispatch.md](../request/2026-08-04_batchD_and_R4a_dispatch.md)
顺序：R4-a（先）→ 批 D（后）。

---

## 环境笔记（开工前）

本 worktree（`agent-a03990d733f96334f`）开工时 checked out 在一个陈旧、无关的本地分支
（`worktree-agent-a03990d733f96334f` @ `52698e3`，2026-06-10 era），与派工单声明的前置
`HEAD f254c56` 完全对不上。working tree 干净、`52698e3` 及其祖先在其它地方仍可达
（非丢失），故 `git reset --hard f254c56` 把本 worktree 的分支指针拨到派工单声明的
起点。**如实披露**：这是一次非常规的 worktree 状态修正，不在派工单纪律条款覆盖范围内，
但属于"不修就无法开工"的前置动作，未见其它更安全路径。

---

## R4-a · 成绩分账（`reading_mode` 溯源块）

### 设计

**记账口径**：逐字照抄 `AI_agent/CLAUDE.md` §1.5 #7——两条正式 lane
（`autonomous` / `controlled`），另有一个 dev 期职能（`dev_function`，不是第三条 lane，
不产生正式成绩）。

**挂载位置**（派工单授权由施工方判断，理由记录于此）：

- `reading_mode` 声明为 `run_config.yaml` 的可选 `reading_mode:` 段（与既有的
  `run_profile`/`capability_profile`/`models` 同层，操作员已经在编辑的同一份文件）。
- 冻结写入 `<run>/_run/reading_mode.json`，唯一写者 `provision_reading_mode()`；
  唯一只读消费者 `resolve_reading_mode()`（永不 raise，缺失 ⇒ `legacy_unknown`）。
  两者的"声明 → 冻结 → 解析"结构逐字仿照既有的
  `src/agent/execution/run_policy_freeze.py`（`provision_run_policy` /
  `resolve_frozen_run_policy`），这是本仓库已确立的同类先例
  （另一个是 `GeometryApproval` 的 `run_profile`/`capability_profile`/`source`/
  `legacy_defaulted` 四字段，R1-5 批次加的）。

**L-R2 fail-closed 的挂载点 —— 本轮最大的一处设计取舍，如实披露**：

派工单原文"新 run 若产不出 reading_mode ⇒ 不得静默按 autonomous 记"字面读像是要求
**每一个**新 run 都必须声明 reading_mode，否则拒绝。但全仓 `_draw_reading`/
`provision_run`/`record_baseline()` 这几条路径被 **数百个既有测试** 直接或间接调用
（`record_baseline()` 本身就有 27 处直接调用，`_draw_reading` 是几乎所有 gate①
测试的必经路径），没有一个声明过 `reading_mode:`。把 fail-closed 焊死在这些路径上
会大面积打红 2115 基线，明显超出 R4-a"小、prerequisite"的定位，且派工单纪律
明令"基线须保持 2115 passed + 10 xfailed 零红"。

**裁定**（施工方自行判断，供审阅方复核）：fail-closed 只焊在
`record_baseline()`——这是本仓库唯一的"这个 run 的分数从此成为正式记录"的时刻
（对应 CLAUDE.md §6 #12"记录这次跑 <case> <tag>"仪式），与 R4-a 自己写的动机
"决定后面所有实验的成绩记在谁头上"精确对应。`record_baseline()` 新增
`require_reading_mode: bool = False` 参数，**默认 False**（保 27 个既有直接调用零改动）；
唯一把它设为 `True` 的调用点是 `run_stage.py` 的 `flow --record` CLI 分支——
经 `grep -rn "cmd_flow(" tests/` + 逐个检查 `args.record`/`--record` 用法确认
**该分支在改动前零测试覆盖**（`tests/test_run_stage_flow.py` 24 处 `cmd_flow(` 调用
无一传 `record=True`），故把它焊死为 strict 对 2115 基线零风险，同时是
**真实存在、此后每个新 run 都会经过**的入口。

检查落在 `record_baseline()` 函数体最开头（`validate_case` 等重活之前），
使 L-R2 的锁与"其余产物是否是一次完整可跑的真实 run"完全解耦——锁只需要
`cmd_flow` 的阶段循环跑到 `--record` 分支即可，不需要构造一次端到端全绿的
真实仿真。

`lane` 与 `reading_agent` 一致性另加一条 `model_validator`：`autonomous`
按定义"零 reading-agent"，`controlled` 按定义"reading-agent 在场"——
两者不一致的声明本身就不合法，在 pydantic 校验层直接拒绝。

### 改动清单

- `src/agent/execution/reading_mode.py`（新文件，296 行）——
  `ReadingAgentInfo` / `ReadingWorkerAgentInfo` / `ReadingModeRecord` /
  `ReadingModeResolution` 四个 pydantic 模型 + `provision_reading_mode` /
  `resolve_reading_mode` / `require_reading_mode` 三个函数。
- `src/agent/execution/run_config.py:120-127`（`RunConfig.reading_mode: dict | None = None`
  字段）+ `:178-190`（`_parse_run_config` 里新增
  `reading_mode = raw.get("reading_mode") if isinstance(...) else None`）。
- `scripts/tool_scripts/record_baseline.py:32`（新增 import）+
  `:490`（`record_baseline(..., require_reading_mode: bool = False)`）+
  `:505-513`（函数体最前的 fail-closed 调用）+ `:565`（`resolve_reading_mode` 只读解析）+
  `:567`（`baseline["reading_mode"] = ...`）。
- `scripts/tool_scripts/run_stage.py:2561-2568`（`cmd_flow` 的 `--record` 分支
  新增 `require_reading_mode=True`）。
- `scripts/tool_scripts/report_assembly.py:765-798`（新增 `_format_reading_mode()`）+
  `:838`（`_render_model_config` 里插入调用）。
- `tests/test_reading_mode.py`（新文件，15 个测试，覆盖 L-R1..L-R4 + 底层事务）。

### neuter 自查（全部在 `/tmp/r4a_neuter` 隔离 clone 里跑，`PYTHONPATH=$PWD`）

| # | 摘掉的实现 | 预期变红 | 实测变红 | 连带 |
|---|---|---|---|---|
| 1 | `cmd_flow` 里 `require_reading_mode=True` 那一行 | `test_L_R2_flow_record_fails_closed_without_declared_reading_mode` | 该条 + `test_L_R2_flow_record_succeeds_with_declared_reading_mode`（同一改动的正反两面，均属预期） | 0（其余 13 条绿） |
| 2 | `ReadingModeRecord._lane_reading_agent_consistent` 整个 validator | `test_lane_reading_agent_contract_autonomous_rejects_reading_agent` + `test_lane_reading_agent_contract_controlled_requires_reading_agent` | 恰好这 2 条 | 0（其余 13 条绿） |
| 3 | `_format_reading_mode` 函数体换成 `return []` | `test_L_R1_report_lane_label_changes_with_declared_lane` + `test_L_R3_report_legacy_unknown_does_not_crash_and_does_not_impersonate_lane` + `test_L_R4_report_flags_dev_function_as_not_official` | 恰好这 3 条 | 0（其余 12 条绿） |
| 4 | `provision_reading_mode` 的 `declared is None: raise` 改成静默填 `lane=autonomous` 默认值（= 派工单点名的最危险失败形态"静默按 autonomous 记"） | `test_provision_reading_mode_fails_closed_on_absence` + `test_L_R2_flow_record_fails_closed_without_declared_reading_mode` | 恰好这 2 条 | 0（其余 13 条绿） |

四次 neuter 均在同一份隔离 clone（`git clone` 本 worktree 到 `/tmp/r4a_neuter`，
`git log --oneline -1` 确认落在 `794b47a`）上做，每次 `git checkout -- <file>` 复原后
复跑确认回到 15 passed 才做下一条。**第 4 条尤其值得记**：它精确复现了派工单原文
点名的失败形态（"缺失即 fail-closed，不得静默按 autonomous 记"），证明这条锁不是
在测"函数存在"，而是在测"这个具体的失败模式真的被挡住"。

### 受影响子集结果

```
tests/test_reading_mode.py tests/test_run_stage_flow.py tests/test_orchestrate_baseline.py \
tests/test_provenance_baseline.py tests/test_run_config.py tests/test_report_assembly.py
—— 100 passed, 1 xfailed, 0 failed
```

### 缺口 / 披露

1. **L-R2 的 fail-closed 范围是"opt-in 但真实"，不是"全局无条件"**（见上文"设计"节的
   详细论证）。如果审阅方判定派工单原意就是要在 `_draw_reading`/`provision_run`
   这类 gate① 通用路径上无条件焊死，那需要另外一轮设计（波及面会远超 R4-a
   "小、prerequisite"的定位，且会打红当前 2115 基线中大量不关心 reading_mode 的
   既有测试）——这是本轮唯一一处认为"值得升级为欠规格边界上报"但仍选择先做出
   一个可论证、可回退的具体实现、把决策权交还审阅方的地方。
2. **未接 gate①**：`src/validator/checks/reading.py` 未新增任何检查项去消费
   `reading_mode`（派工单没有要求，判卷/gate①层未触碰，属故意不做）。
3. **`toolbox_version`/`isolation_profile` 目前是自由字符串**，未与仓库里实际的
   工具箱版本号/隔离档位标识符做枚举绑定（派工单没有给出这两个字段的合法取值集合，
   保持自由字符串以免虚构一个不存在的枚举）。
4. 未触碰任何 `AI_agent/` 下的管理文档（除本执行日志）、未碰 sm24 testdata、未 push。

---

## 批 D · 判卷图恢复（六 panel + 图例）

### 设计

**病灶复核**：`render_typed_grade()`（`scripts/tool_scripts/render_grade.py:1288` 起，
v3 typed 路径）此前只画每层平面的多边形 + 每个 opening 一条判定色带，**完全没有立面
panel、也没有图例**——用户能看的只有"墙的形状对不对"，看不出立面（sill/head 等
垂直方向数据）对不对。legacy 六 panel（`render_grade()`，仍原样保留、按要求不回退用它）
画的是矩形变换下的两层平面 + 四立面几何叠图带图例，但它的坐标假设（W/D 矩形）
对 v3 多边形不成立，不能直接复用。

**关键发现（复用已有资产,降低风险）**：`src/agent/judge/gt_render_model.py` 已有
`GtRenderModel.elevation_surfaces`（`ElevationRenderSurface` 含
`facade_family`/`segments`/`openings`/`world_along_coverage`，由 `gt_to_render_model()`
从 GT v3 的 `sources[].views[kind=="elevation"]` 结构化产出）与一个纯 GT 自证的
`render_elevation_model()`（sm21 形态：网格 panel + 尺寸链 + 窗框）。两者都只读
**GT 自己声明的 `facade_family`**，与"产品的 mirror/local-x 声明"是完全不同的字段
——满足派工单 #4 的边界（`render_typed_grade` docstring 那条"不读产品 mirror/local-x
声明"的边界原样保留，本批未碰）。判定色（`ClaimScoreRowV8.result`）里没有产品自己的
坐标，只有 complete/within_tolerance/miss/conflict/not_applicable 五档结果——与既有
平面 claim-rail 完全同源（同一个 `rows_by_target` 查表），故立面 panel 的着色逻辑
（"取一个 opening 名下所有 claim 里最差的一档"）与平面 panel 同构，不新造判据。

**布局设计**：
- 六 panel = 2 层平面（既有,未改动核心逻辑）+ 4 立面（North/South/East/West,
  `FACADE_CODES` 固定顺序,新增,2×2 网格)。
- **图例**（新增,`_typed_legend()`）：四档判定色 + gt-truth 线型,插在标题与平面行
  之间，与既有 `render_grade()`（legacy）legend 用同一套词汇（颜色=判定档,画法=类别）。
- **每个 panel 独立标题**（"{floor_id}  polygon" / "{facade} elevation"）。
- **标签不互压**：所有布局尺寸（图例 y、`floor_top`、四个立面 panel 的宽高/间距/
  网格行列）提到模块级常量（`_TYPED_PLAN_*`/`_TYPED_ELEV_*`/`_TYPED_LEGEND_Y`/
  `_TYPED_FLOOR_TOP`），画布尺寸由这些常量公式化推出（不是拍脑袋的数），并留足
  legend 与平面行标题之间的垂直间隙（早期草稿在这两者之间只留 4px、实测肉眼可见
  轻微贴近，已改为公式化留白 22px 予以修正,详见"缺口/披露"）。
- **缺立面 = 明确占位**：某立面在 GT `elevation_surfaces` 里没有任何条目 ⇒ 该
  panel 画成整格红字"NO SUCH ELEVATION IN GT" + 全 panel 斜线 hatch（复用既有
  `_typed_hatch()`），**占据与真实立面同样大小的网格格**（不缩小布局悄悄吞掉）。

### 改动清单

- `scripts/tool_scripts/render_grade.py`：
  - `:1130-1144` 新增布局常量（`_TYPED_PLAN_PANEL_W/H/MARGIN/GAP`、
    `_TYPED_LEGEND_Y`、`_TYPED_FLOOR_TOP`、`_TYPED_ELEV_PANEL_W/H/GAP/COLUMNS/ROWS/
    CELL_H/TOP`）。
  - `:1146-1160` 新增 `_typed_worst_claim_result()`（同一 opening 多条 claim 取
    最差档，缺 claim 或全 NA ⇒ `not_applicable`）。
  - `:1164-1189` 新增 `_typed_legend()`。
  - `:1193-1275` 新增 `_draw_typed_elevation_panel()`（单个立面 panel：无该立面 ⇒
    占位；有 ⇒ 画 envelope + 楼层分割线 + 逐 opening 判定色框 + 局部裁切/z 缺失提示）。
  - `:1301-1407` `render_typed_grade()` 本体：改用上述模块级常量替换原硬编码
    `420/360/36/28`/`82`/`62`；新增图例调用；floor loop 的 `oy`/标题 y 改用
    `floor_top` 变量（原硬编码 `82`/`62`）。
  - `:1409-1417` 平面 loop 结束后新增 4-panel 立面网格绘制循环；`:1421`/`:1435`
    （`result_footer_bottom`/`panel_top` 两处 status 面板定位）原 `height + 102`
    改为 `content_bottom + 20`（随立面网格顺延）。
- `tests/batch_d_four_facade_fixture.py`（新文件）：北/南/东/西四立面均声明真实
  elevation view + 每面各一窗的 GT v3 fixture（既有 `tests/b4b_contract_fixture.py`
  只接了北/南两面,不够验 L-D1 的"六 panel 均有真实内容"）。
- `tests/test_batch_d_typed_grade.py`（新文件,7 个测试）。

### neuter 自查（`/tmp/batchd_neuter` 隔离 clone,`PYTHONPATH=$PWD`）

| # | 摘掉的实现 | 预期变红 | 实测变红 | 连带 |
|---|---|---|---|---|
| 1 | `render_typed_grade()` 里画 4 个立面 panel 的 for 循环整段删除 | `test_L_D1_six_panels_render_with_titles_and_exact_canvas_size` + `test_L_D2_missing_facade_renders_explicit_placeholder_not_omission` | 恰好这 2 条 | 0（其余 40 条绿，**尤其 `test_L_D2_missing_facade_does_not_shrink_the_grid` 仍绿**——它只验图幅尺寸不验内容，证明两条断言彼此独立、不是同一件事的两次断言） |
| 2 | `_draw_typed_elevation_panel` 里"无此立面"分支从画占位改成直接 `return`（静默省略） | `test_L_D2_missing_facade_renders_explicit_placeholder_not_omission` | 恰好这 1 条 | 0（其余 40 条绿） |
| 3 | `_typed_legend()` 函数体换成 `pass` | `test_L_D3_legend_lists_every_judgement_tier` | 恰好这 1 条 | 0（其余 40 条绿） |

三次 neuter 均在 `git clone` 隔离副本（落在 `8336bd5`）上做，每次 `git checkout --` 复原后
复跑确认回到 5/5 passed（子集）才做下一条。

### 受影响子集结果

```
tests/test_batch_d_typed_grade.py tests/test_c2_b4b_phase_d.py tests/test_c2_b5_parent_and_verts.py \
tests/test_judge_batch_b.py tests/test_reading_typed_scoring_slice0.py tests/test_render_grade.py
—— 115 passed, 0 failed（42 条 DeprecationWarning,均为既有 `Image.getdata()` 用法,与本批无关）
```

### 缺口 / 披露

1. **legend 与 floor 标题的垂直间距是肉眼校准的**（先用 `render_typed_grade` 生成
   真实 PNG 人工检视，发现 legend 与 "F1 polygon" 标题贴得太近后手工把 `floor_top`
   从 82 调到 100、`legend_y` 从 58 调到 56），不是数学证明的"绝不重叠"（不同
   floor_id/facade 名字长度、不同 DPI/字体渲染在极端情况下仍可能贴近）。已实测的
   四种典型 payload（全通过、reading_stage 带状态面板、顶层 not_applicable、四立面
   全实心）均无肉眼可见重叠，见 `/tmp` 预览截图（未入库,过程产物）。
2. **立面 panel 内的判定色是"整个 opening 取最差档"，不是逐 claim 分别在立面上
   再画一次 chip**——sill/head/existence/along/width 五个 claim 的逐项色带**已经
   由既有的平面 claim-rail 完整画出**（`validate_typed_render_totality` 的
   totality 契约本就要求每个 `{opening}:{claim}` 都有至少一个渲染位置，平面 rail
   早已满足），立面新增的是"这个 opening 综合看对不对"的**空间位置**视图（这正是
   平面视图给不出的东西：sill/head 是垂直方向数据，二维平面画不出高度对不对）。
   若审阅方认为立面上也应逐 claim 单独打色块，需要另外一轮改动，本批未做。
3. **多个 elevation view 落在同一 facade 时做了合并**（例如某立面同时有 full+detail
   两个 view）——直接把所有匹配 `facade_family` 的 surfaces 的 segments/openings
   拼起来画在同一个 panel，不再区分是哪个 view 提供的。派工单没有要求逐 view
   拆分,按"六 panel = 四个 facade"字面理解处理。
4. **未削弱、未触碰 legacy `render_grade()`**（六 panel 矩形路径）——按 §1.2 "⛔ 不得
   回退到 legacy 渲染器"原样保留，本批唯一改动面是 v3 typed 路径。
5. `render_typed_grade()` 已有的既有测试（`test_d3_typed_polygon_hatch_audit_and_
   unknown_target_rejection`）断言 `audit["O1:appearance"].startswith("rail:")`——
   本批新增的立面绘制**刻意不写任何新的 `audit[...]` key**（既有平面 loop 已经把
   每个 target/claim 的审计位置写全），避免覆盖掉那条既有断言依赖的字符串前缀。
   如实记录这个约束,以免后续改动误以为立面也该占用 audit key。

---

## 追加·orchestrator 轻门抓到的一条必修（8.04，批 D 合并入主线后）

### 病灶

orchestrator 把本批两条并入 `6.15_ValidationArchM0toM4` 主线后独立跑权威全量，
命中一条真红：

```
FAILED tests/test_affected_tests_map.py::test_every_production_module_is_mapped_or_honestly_allowlisted
E   Extra items in the right set: 'scripts/tool_scripts/render_grade.py'
```

**根因（好红，守卫在正常工作）**：`scripts/tool_scripts/affected_tests_rules.yaml`
的 `uncovered_allowlist` 里原有一条
`scripts/tool_scripts/render_grade.py: "manual render CLI; no project-side test exercises it"`。
本批新增的 `tests/test_batch_d_typed_grade.py` 让这条登记过期——**但不是通过
`import render_grade`（那是运行时 `sys.path` hack，`affected_tests.py` 的静态
AST 分析认不出裸模块名）**，而是通过一处**巧合**：`test_L_D1_six_panels_render_
with_titles_and_exact_canvas_size` 的 docstring 里为了写清楚 neuter 说明，
字面写了 `render_typed_grade (scripts/tool_scripts/render_grade.py) — the 4` ——
这句话里的字符串 `scripts/tool_scripts/render_grade.py`（一个已登记的 first-class
文件路径）被 `affected_tests.py::build_edges` 的 `ast.Constant` 字符串扫描当作
**string-path 边**收进图（`ast.walk` 会遍历到嵌套函数体内的文档字符串常量节点）。
用 `affected_tests.py --changed ... --explain` 直接验证：

```
SCOPE: SUBSET
EXPLAIN: tests/test_batch_d_typed_grade.py: tests/test_batch_d_typed_grade.py --string-path--> scripts/tool_scripts/render_grade.py
```

这条边是**真实**的（该测试文件确实完整地导入并调用了 `render_grade.render_typed_
grade`），只是触发它的具体机制（docstring 里恰好写全了文件路径）是巧合，不是我
特意去满足这条静态规则。

### 为什么上一轮没发现（如实说明）

派工单纪律要求交付前跑一次全仓 `pytest -q -n 4`；我在本 worktree 里确实发起了这次
跑测（后台任务 `bvr20ms01`），但**在它跑完之前，orchestrator 的合并 + 独立权威全量
就先到达了**——即我这边的全量还没来得及产出结果、我也就还没看到这条红。
（该任务后来跑完，结果与 orchestrator 描述吻合：本 worktree 因缺失若干未跟踪
EP 产物额外多出 5 条环境相关的红，加上这条 affected-map 红共 6 条；orchestrator
在主树上跑，主树有完整 EP 产物，只剩这 1 条真红——两边观察一致，唯一差别是主树
先出结果。）**教训**：批 D + R4-a 这种改动面较大的任务，`tests/test_affected_tests_
map.py` 这类"全仓自省"性质的守卫测试必须显式包含在交付前的确认清单里，不能只
跑"受影响子集"就当验证完毕——这条锁的性质决定了它**只可能在全仓跑测里被触发**
（受影响子集选择器不会把自己包含进"受影响"范围）。

### 改动清单

- `scripts/tool_scripts/affected_tests_rules.yaml`：删除 `uncovered_allowlist`
  下 `scripts/tool_scripts/render_grade.py` 一行（该模块现有真实测试覆盖，登记
  为"无覆盖"已不诚实）。

### 核验

- `python scripts/tool_scripts/affected_tests.py --changed scripts/tool_scripts/render_grade.py --explain`
  → `SCOPE: SUBSET`，边 = `tests/test_batch_d_typed_grade.py --string-path--> scripts/tool_scripts/render_grade.py`。
- `python scripts/tool_scripts/affected_tests.py --changed src/agent/execution/reading_mode.py --explain`
  → `SCOPE: SUBSET`，边 = `tests/test_reading_mode.py --import--> src/agent/execution/reading_mode.py`
  （**真实 `import` 边，不是靠 allowlist 蒙混**——`reading_mode.py` 从未在
  `uncovered_allowlist` 里出现过，本来就是靠 `tests/test_reading_mode.py` 顶部
  `from src.agent.execution.reading_mode import (...)` 的正规模块化导入被图正确
  收录，与 render_grade.py 的 string-path 巧合边不是同一种机制）。
- `pytest -q tests/test_affected_tests_map.py` → 15 passed（含目标锁
  `test_every_production_module_is_mapped_or_honestly_allowlisted`）。
- 全仓 `pytest -q -n 4`：见下方"跑测尾部"。

### 边界

未动 `AI_agent/` 下除本执行日志外的管理文档；未碰 gt / sm24 testdata；未做批 C /
R1.5。本次改动只有一个 yaml 文件删一行，无生产逻辑改动，未额外新增 neuter 台账
条目（这不是一条"新锁"，是给一条既有守卫更新它自己的登记表）。
