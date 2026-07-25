# 2026-07-25 立面批「六笔债」施工派工单

- **施工方**：Claude 侧执行档子代理（Opus 5，主控派）
- **审阅方**：GLM-5.2 结构化清单验证性对抗审（跨家族，谁写谁不批）+ 主控轻门（独立全量 + 亲核 diff）
- **基线**：`e13efd3`（= `7888ded` 代码态 + 文档同步）；全仓 **1556 passed, 10 xfailed**
- **合同**：`AI_agent/proposals/tarch_elevation_spec.md`（定稿）
- **上轮裁决书**：`AI_agent/logs/reviews/verdict/2026-07-24_elevation_construction_review.md`（0 BLOCKER / 2 MAJOR / 2 MINOR / 2 NIT）
- **本批终点**：债清 → 重生成 sm24 review bundle → 用户 G10 人签 → 晋升 anchor（晋升不在本批）

---

## 0. 本批性质与最高纪律

本批 = 上一批（天正命名立面）过审后登记的跟进债，**六笔一次清**。上一批的命脉（§9 必红矩阵）已经 Opus 逐门 neuter 复核为真红、零 false-lock，**本批不得让它退化**。

三条硬纪律：

1. **禁 false-lock**。每条新增的必红/回归锁，交付前必须自己做一次 neuter 自证：把目标门的判定逻辑改坏 → 跑该测试 → 必须由绿翻红 → `git checkout` 还原。自查表逐格写「我 neuter 了什么文件哪一行、跑了哪个测试、结果」。**禁伪造自查表**——GLM 会照单复验、主控会亲核抽查。上一轮转换器返工就死在「九门假锁」上，这是本项目最贵的教训。
2. **禁放松既有 fail-closed 语义**。不得为了让某个测试变绿而放宽门、加生产后门、加 `TARCH_NEUTER_GATE` 之外的新 env seam。
3. **诚实披露**。未竟项精确标出（对标 B4b Phase D 正面样板：「精确标 5 未竟、不藏假绿」），**禁把未做说成「留给审查」**。做不完就写做不完，不扣分；假绿扣分。

---

## 1. 工作项

### WI-1 —（MAJOR-1）实现 §6.5 converter ↔ GT 配对一致性 postcheck

**现状**：`_run_g9_v3_preflight`（`src/agent/judge/tarch_normalize.py:2039` 附近）只跑 `inspect_extraction_inputs` + `extract_gt_v3`，且**丢弃 `extract_gt_v3` 返回值**（只取副作用）。全仓 `tarch_elevation_pairing_drift` emit 引用数 = **0**（死码）。

**风险**（裁决书 MAJOR-1）：converter 审计行 z（request affine，`build_p2_report` 内）与 GT z（manifest affine，`_elevation_geometry` 内）是**两条独立代码路径**，其相等**当前无任何门强制**。今天实测一致（同源），但未来 units/wiring 漂移会让「人核看的审计表 z」与「权威 GT z」静默分叉——而 z（窗高）正是这一批唯一的新交付物。

**出口（合同 §6.5 [S]）**：完整 GT 产出后，按每个 `opening_elevation` source ref 的 generated handle 反查 evidence，与 converter pairing ledger 比较：

- view id 相同；
- opening id 相同；
- kind 相同；
- **z interval 等于 converter 计算值**；
- 每个 relevant pair **恰一组** refs（不多不少）。

不一致 → BLOCK，emit `tarch_elevation_pairing_drift`（把死码接上）。

**必红要求**：至少三条独立必红夹具，且各自 neuter 自证：
- z 漂移（把 GT 侧或 ledger 侧其一的 z 动一点点）→ 红；
- 一个 relevant pair 出现 0 组或 2 组 refs → 红；
- kind / view id 不一致 → 红。

**比较口径**：z 是浮点，用**该 case 已有的 z 容差口径**（不得新造一个宽容差把漂移放过去；若合同/现码没有明确容差，用精确相等或 ≤1e-9，并在简报里说明选择理由）。

**顺带**：上一批简报（`execution/2026-07-24_elevation_construction_terra.md`）§11 row 10 声称「GT refs 与 converter ledger 一致 | G9 / audit 实测通过」是 overclaim（当时无门支撑）。**历史简报是过程痕迹、不改写**；在你本批的新简报里写一节「上批 §11 row 10 订正」，说明该对账项在本批之前无门支撑、现由 §6.5 postcheck 支撑。

### WI-2 —（MAJOR-2）补 §9.3 / §9.2 必红夹具 + §6.6 sm24 正向 e2e 断言

**现状**：`tests/test_tarch_elevation_must_red.py` 只覆盖 §9.4（along 四变异）+ 门 role/fingerprint/union + kind/missing-evidence + raster 三格。裁决书核实：z / datum / title 变异关键词命中 = **0**。相关门是真的（`title_mismatch`/`datum_missing`/`datum_invalid`/`z_transform_mismatch` emit 引用均 ≥1，`z_transform` 门是真跨源交叉检查、非恒真自比），缺的是**负例锁**。

**出口**：

1. **§9.3 z 组（本批安全命门，优先级最高）**——七类变异全部必红：
   - datum 换成屋顶线；
   - datum source axis 与 z axis 不符；
   - z scale 从 `0.001` 改成 `1.0`；
   - offset 平移 0.2m；
   - 两个 datum 推出不同 offset；
   - 窗框跨楼层；
   - 窗 z 高于 ceiling。
   合同明写：**不得因最终数值「仍像窗高」而放行**。
2. **§9.2 frame / title 组**——六类全部 BLOCK：frame handle 不存在 / bbox 相同但 handle 指向第二框 / 框内 0 个或 2 个标题 / `北立面图` 未显式列入 alias map 却 request 写 `北立面` / 两个 full North view 覆盖同 floor / entity 跨 frame 边。
3. **§6.6 sm24 正向 e2e 断言**——十条（source views = 1 plan + 4 elevation；四 facade projection key 落在正确 boundary segment；`len(openings) == 14`；11 个 window `z_interval` 全非空；window z 只出现 `[1.0,2.8]` 与 `[1.0,3.4]`；3 个 exterior door 有 source-observed z 且非 floor default 生成；door z 只来自受校验的 block structural outline、`11C` 在 excluded inventory 且不改变 z；每个 opening 有 plan ref、每个 relevant opening 有 elevation ref；7 个 interior door 不在 GT；canonical reload 逐字节一致）。
   - 现有 `test_sm24_v3_...overlays...` 已跑真 sm24 路径但只断言 overlay 渲染；可在其邻近加断言、或另起一个 sm24 e2e 测试，**不必等 anchor 晋升**。
   - 合同硬约束：**数值断言属真实 anchor fixture，生产算法不得按这些数字分支**（不许在生产码里写 `if len(openings)==14`）。

**必红要求**：§9.2/§9.3 每一格都要 neuter 自证「该门在算」——特别注意别让某条变异实际是被**别的**门（schema 层、hash 层）兜住的：若发现某格实际由另一道门抓，如实写在自查表里（这不是错，但必须写明是哪道门抓的）。

### WI-3 —（MINOR-1 / MINOR-2 / NIT-1 / NIT-2）登记面与鲁棒性清理

1. **死登记码**（MINOR-1）：`tarch_elevation_opening_no_candidate` / `tarch_elevation_opening_assignment_ambiguous` / `tarch_elevation_opening_kind_mismatch` / `tarch_interior_opening_elevation_not_applicable` 四码 emit 引用 = 0。前三者与 §6.4「G9 extraction 错误经 `tarch_v3_precondition.context.v3_code` 原码上浮」设计冗余（实测走 raw code），第四条是 INFO 从未 emit。**出口二选一**：接线为真 emit（并配必红/正例锁），或删冗余码 + 在诊断码文档/注释里说明「G9 立面失败统一走 `tarch_v3_precondition`」。选哪条你判断，简报写理由。
2. **宽 except**（MINOR-2）：`_run_g9_v3_preflight` 末尾 `except Exception as exc: return False, str(exc)` 把任意异常（含 coding bug）伪装成合法 BLOCK。窄化到 `(ExtractionError, ValidationError)` 一类具体异常；真 bug 应该炸出来。
3. **前置 `extract_gt_v3` 未包裹 + 双跑**（MINOR-2）：`run_p2_conversion:2254` 附近为取 plan_gt 先跑一次 `extract_gt_v3`、未包 try（过了 P2 plan 门但过不了 extraction 输入 → 崩溃而非 blocked report），且同一函数在 G9 又跑一次。**出口**：包 try 转 BLOCK，或复用 G9 结果避免双跑（后者更好，但别为省一次调用破坏门序——WI-1 的 postcheck 也要用到这个 GT）。
4. **NIT-1 docstring**：`test_raster_horizontal_mirror_in_bounds_makes_g10_calibration_red` 的 docstring 称靠 directed lo/hi 抓手性，实测是靠 elevation `residual_ok` 抓。订正 docstring（或另补一条「镜像 + 同步镜像 source 点使 residual 仍成立、只 directed 手性能抓」的夹具，二选一，后者更有价值但非硬要求）。
5. **NIT-2 死分支**：`gt_extraction.py:585` `(item is None or item.kind == opening.kind)` 中 `item is None` 恒假。删或留注释说明是防御性，二选一。

### WI-4 —（用户 Q2）sm24 GT 补 `wall_thickness_m`

**问题**：sm24 gt **没有 `wall_thickness_m` 字段**（sm21 有 `0.24`）。判卷侧两种尺寸口径换算（外墙外包 ↔ 中轴，`src/agent/judge/correction_score.py:341` 起消费该字段把中轴 correction 外扩 wall/2 去对外包 GT）需要它；缺了这条判卷路径只能退化。

**现状**：`src/agent/judge/gt_extraction.py:647` 硬写 `wall_thickness_m=None`；`src/agent/judge/gt_manifest.py:123` 已有 `default_wall_thickness_m` 字段。

**出口**：让 v3 提取按**证据**发射墙厚（sm24 外墙 240mm = 0.24m）。硬约束：

- **不得瞎猜**——值必须来自 manifest 声明的 `default_wall_thickness_m`、或转换器已有的厚度证据体系（上一轮 G7/G8 就是墙厚门，厚度已绑证据）。选哪条来源你判断，简报写清「这个 0.24 是从哪条证据链来的」。
- **fail-closed**：没有证据时保持 `None`，**不许填默认值蒙混**。
- 加断言：sm24 GT `wall_thickness_m == 0.24`；加一条负例（证据缺失 → None 或 BLOCK，按你选的语义）。
- 注意：这会改 GT 内容 ⇒ canonical hash 变 ⇒ review-index 重签（本来就要重签，见 WI-6）。检查 sm21（v2 legacy 路径）与判卷侧现有测试是否受影响，全仓回归为准。

### WI-5 — 出图质量做到 sm21 级

用户对上一批出图的验收意见（Q1）：**图糊 + 局部没完全对齐**，达不到 sm21 的水平。这是本批**用户唯一直接可见**的交付，权重高。

参照物（请直接打开对比）：
- 目标：`case_tests/test_baseline/gt/sm21_anchor/renders/overlay_1f_view.png`
- 现状：`logs/experiments/2026-07-24_sm24_gt_review/gt/renders/overlay_1f_view.png` 与四张 `overlay_*_view.png`

**a. 底图别压太暗**。`scripts/tool_scripts/render_gt_overlay.py:38` `DIM = 0.38`。sm24 的原图是**黑底 CAD 截图**，0.38 一压，原图墨迹几乎全灭——四张立面上原本能看见的窗框线现在看不见了，人核就失去了「gt 是否忠实于图」这个对照面。
- 出口：让底图墨迹在成图上**清晰可辨**（自适应亮度、或对暗底图改用不减亮/提亮策略，方案你定），给一个**可量化的判据**（例如原图墨迹像素在成图上的平均亮度保留率 ≥ 某阈值）写进简报，并附**改前/改后对比图**。
- ⚠️ **硬约束**：`DIM` 与 `overlay_plan`/`overlay_elev` 是 **sm21 legacy 路径共用**的，sm21 的 overlay 是**已锁定基线资产**。改动后 **sm21 legacy 路径输出必须逐像素不变**，并**加一条测试锁住**（比如对 sm21 legacy 渲染结果做像素级 / hash 级回归）。

**b. 平面按房间用途上色 + 标签**（对齐 sm21 形态：半透明填充 + `zone_id role` 文字，见 sm21 overlay 的 `F1_N1 office` / `F1_COR corridor`）。v3 plan 分支现在只描边、无填充，label 只有 zone id、默认色一片灰蓝。
- **房间用途来源 = 主控目检的受信人工注记**：`z0` 会议 / `z3` 接待 / `z5` 门厅 / 其余（`z1 z2 z4 z6 z7`）办公。
- **硬约束（信任边界）**：这份注记是 **review-only**——① **不得回写 `gt.json`**（GT 里 role 保持 `unspecified`）；② **不得参与任何 gate 判定 / 不得影响任何 hash 之外的机器结论**；③ 必须**纳入 review-index inventory**（用户签的是整包，注记也在被签之列）；④ 未注记的 zone 退到中性灰、不得猜。
- 落地形式你定（bundle 内一个 review 注记文件是自然选择），简报写清它在信任链里的位置。
- ⚠️ 请自行核对 zone id ↔ 图上位置的对应关系是否与上述用途自洽（`z0` 是那间摆长会议桌的大房间、`z3` 是北端带 L 形沙发的房间、`z5` 是南侧带门厅的小间）。**若你核出的对应关系与主控给的不一致，停下来在简报里报出来，不要自己改用途**。

**c. 立面 envelope 补底边**。`render_gt_overlay.py:321` 用 `draw.rectangle(..., width=3)`，PIL 的矩形底边实际只有 1px。改成显式四条线（或等效画法），四边等宽。

**d. 校准精度做到 sm21 级**。sm21 用的是自动密度框（`_calibrate` / `_box_gray` / `_box_white`，同文件 57–98 行）精确框出图形范围；sm24 的 v3 路径用的是**主控目检**的像素控制点（`logs/experiments/2026-07-24_sm24_gt_review/calibration_maincontrol.json` + `calibration_plan_maincontrol.json`），有几个像素残差，这是「局部没完全对齐」的根。
- 出口：写一个**离线检测助手**（可复用上述密度框思路），从 `case_tests/e2e_tests/sm24_anchor/case_data/*.png` 检出建筑轮廓角点 / datum 端点的精确候选控制点，产出：候选控制点 + 与现有控制点的像素差 + 残差报告 + 可视化验证图（把候选点画在原图上）。
- ⚠️ **信任边界不许变**：**机器只提议、主控声明、converter 只校验**。你**不得**让 converter 自动采信检测结果、不得加图像启发式进生产判定路径（合同 §7.3 明写「不得退回 legacy v2 的自动密度框校准」）。
- 落法：把精修控制点写进**新的** request 文件（例：`logs/experiments/2026-07-25_sm24_gt_review/request_v3_calibrated.json`），**保留旧的 07-24 目录原样**供对比；主控核对后决定采信哪版。
- 已知限制（**不用你解决，但简报要写明**）：sm24 平面截图本身只有 790×1111（sm21 平面是 2133×1345），底图糊有一半是案例输入自身分辨率的限制。**不得改 `case_data/` 原图**——那是识图阶段的输入资产、hash 绑在 request 上。若你认为在合成时对底图做无损放大能明显改善可读性，**给方案 + 影响面分析，别直接落**（会改输出像素尺寸，可能牵动 hash/测试）。

### WI-6 — 重生成 sm24 review bundle（本批最后一步）

全部代码改完、全仓回归绿之后，用最终代码 + 精修 request 重跑，产出新的 review bundle 到 **`logs/experiments/2026-07-25_sm24_gt_review/`**（新目录，旧目录原样保留）：

- `gt/gt.json`（candidate，含新的 `wall_thickness_m`）
- `gt/renders/` 原子整包：`gt_plan.png` / `gt_elev.png` / `overlay_1f_view.png` / 四张 `overlay_{East,North,South,West}_view.png`（合同 §7.2 的原子 rename 语义不变，不得先落 `renders/` 再搬）
- `opening_elevation_audit.json`（14 行，逐 opening 的 z_interval + datum 端点映射，供人核）
- `review_index.json`（整包 inventory hash 重签）+ conversion report

简报里给出：**新 candidate GT hash + 新 review-index inventory hash + 14 行审计表摘要（每行 opening id / kind / host zone / along 区间 / z 区间）**。

**不做 promotion**：不写 `case_tests/test_baseline/gt/`、不写 `gt_sources/`。G10 保持 candidate，等用户人签。

---

## 2. 边界（不许碰）

- 不写 `case_tests/test_baseline/gt/`、`gt_sources/`、`case_tests/e2e_tests/*/case_data/`。
- 不动 GT v3 wire 语义、scorer / Va / Vg、v2 legacy adapter、reading / correction / execution 子系统（WI-4 若必须动 v3 提取的 wall thickness 发射点，限于该点，并说明影响面）。
- 不动 `render_gt_overlay.py` 的投影数学：`_pixel_for_world_plan` / `_pixel_for_world_elevation` / affine 系数。WI-5 全部是 draw-only + 亮度合成层的改动。
- 不放松任何 fail-closed 门；不加生产后门；不为过测试改容差。
- **施工前备份**（项目硬纪律 §5#4）：`cp` 到 `backup/src_history/2026-07-25_elevation_debt/` 与 `backup/scripts_history/2026-07-25_elevation_debt/`。

---

## 3. 交付物

1. **代码 + 测试**（工作区改动，不要 commit、不要 push——主控轻门后由主控 commit）。
2. **全仓回归**：`python -m pytest -q -p no:cacheprovider`，报完整尾行（基线 **1556 passed, 10 xfailed**）。零回归是硬要求；若有新 xfail/skip 必须解释。
3. **执行简报** → `AI_agent/logs/reviews/execution/2026-07-25_elevation_debt_batch.md`，必须含：
   - 逐工作项：改了什么文件哪几处、为什么这么改、留白判断；
   - **§9 必红自查表**：每条新锁一行「neuter 了什么（文件:行 + 改成什么）/ 跑了哪个测试 / 绿→红 结果」；
   - WI-1 的 z 比较容差选择理由；
   - WI-4 的墙厚证据链来源；
   - WI-5 的底图可见度量化判据 + sm21 legacy 逐像素不变的证明方式 + 校准候选点与旧点的像素差；
   - 上批 §11 row 10 订正节；
   - **诚实交接节**：未竟项精确列出（做不完写做不完），已知限制（平面底图分辨率）写明。
4. **产物**：`logs/experiments/2026-07-25_sm24_gt_review/` 新 bundle + 校准验证图。

---

## 4. 验收（主控轻门 + GLM 验证性对抗审）

主控会做：独立干净全量复跑逐字对齐 + 亲核 WI-1 postcheck 与 §9.3 z 组的核心 diff + 抽查 neuter 自查表若干格 + 目检出图。
GLM 会拿一份结构化核验清单**逐条独立验真**（每条写死「验什么 / 什么算不成立」），重点是：**新锁是否真绑目标门（防 false-lock）**、postcheck 是否真在算、墙厚是否有证据、sm21 legacy 是否真没变。

自查表造假 / 未竟说成已竟 = 直接 REWORK。诚实标未竟 = 不扣分。
