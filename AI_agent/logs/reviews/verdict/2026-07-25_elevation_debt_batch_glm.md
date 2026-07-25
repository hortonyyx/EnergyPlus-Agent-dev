# 2026-07-25 立面批「六笔债」— GLM 跨家族验证性对抗审裁决书

- **审阅方**：GLM-5.2（GLM 家族，唯一独立裁决方）
- **施工方**：Claude 侧 Opus 执行档子代理
- **主控**：Claude 侧 Opus（轻门已过，**不参与本轮裁决**）
- **被审提交**：`70dceb8`（基线 `e13efd3`）
- **核验清单**：`AI_agent/logs/reviews/request/2026-07-25_elevation_debt_batch_glm_checklist.md`（**唯一权威**）
- **原则**：谁写谁不批。本裁决仅基于 GLM 亲手跑出的活体证据；凡未亲手验证的，标「无法判定」。

---

## 1. 总裁决

# **APPROVE-WITH-CHANGES**

**交付代码与产物合格**：12 条新增锁逐格 neuter 复现为真锁（**零 false-lock**）、fail-closed 门一条未松、sm21 legacy 逐像素不变（6/6 diff=0）、WI-1 §6.5 postcheck 是真门且是 z 漂移的唯一抓手、审计表与 GT 独立 join 14/14 一致、三个 hash 自算逐字等于声明、未触碰任何禁区。

**命脉 X-01 通过**：6 格抽样 4 格干净 GREEN→RED、2 格揭示真实机制（datum 复合承重 2/3、Z-06/Z-07 双门纵深防御）；命脉之命脉——WI-1 z 漂移 postcheck——是干净真锁（neuter 整门 → z 漂移立即放行）。

**with-CHANGES 的原因（全部是简报/文档精度问题，不是代码缺陷，不需改码）**：
- 2 条 MINOR：简报对 Z-06/Z-07「同一道门」、z_transform「单一抓手」的归因不精确（实际为多门纵深防御 / 多处同码检查）；方向都是**多强制、不少强制**，但措辞会误导未来审阅者对覆盖面的判断。
- §9.2 六格诚实标未竟（**加分项不扣分**）；其中 F-01 经我实测已被现有 `title_mismatch` 覆盖，F-02/F-06 才是真缺门，下批「先补门再补锁」立项正确。

**无 REWORK 触发条件**：自查表零造假、零 false-lock、零假绿 PASS 路径、零容差放宽、零禁区改动。

---

## 2. 逐条回填表

> 探针目录：`/tmp/glm_elev_debt_probe/`（零施工方 fixture 导入；期望值本清单给定或独立手算）。所有 neuter 经 `cp` 安全副本还原，结尾三生产文件 `diff -q` 与备份全一致、`git status -- src/ scripts/` 干净。

### §0 纪律与环境

| 编号 | 命令 / 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| C-00 | 探针放 `/tmp/glm_elev_debt_probe/`；只 import 生产 API + numpy/PIL/ezdxf/shapely；期望来自清单或手算 | 零 `tests/` helper 导入 | **成立** |
| C-01 | `git diff --name-only e13efd3..HEAD` + 投影函数体逐行核 | 改动=3 生产文件(tarch_normalize/gt_extraction/tarch_converter_schema)+render_gt_overlay+5 测试+4 文档；禁区(`case_tests/test_baseline/gt/`、`gt_sources/`、`case_data/`、`correction_score.py`、Va/Vg、legacy adapter、reading/correction/execution) **0 命中**；`_pixel_for_world_plan/elevation` 在 diff 中**只出现在调用点**(174/177/184/189/193)、`def` 体与 affine 系数零改动 | **成立** |
| C-02 | `python -m pytest -q -p no:cacheprovider`（独立干净单跑） | `1579 passed, 10 xfailed, 148 warnings in 583.29s` EXIT=0；基线 1556→+23、xfail 不变=10、failed=0、无新 skip | **成立** |

环境：python 3.12.13 / ezdxf 1.4.4 / Pillow 12.2.0 / numpy 2.4.4 / shapely 2.1.2 / pydantic 2.13.3 / pytest 9.0.3；HEAD=`70dceb8`。

### §1 WI-1 §6.5 配对一致性 postcheck

| 编号 | 命令 / 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| P-01 | grep emit + 静态读 postcheck + 真跑 sm24 | `tarch_elevation_pairing_drift` emit @ `tarch_normalize.py:2434`(引用≥1)；postcheck 消费 `_run_g9_v3_preflight` 第三返回值 `g9_document`(不再丢弃)；真 sm24 路径 postcheck 执行(基线 `_verify_pairing_consistency` 返回 `[]`) | **成立** |
| P-02 | 独立 `_verify_pairing_consistency` 调用，两侧各漂移 | **GT 侧**(测试 monkeypatch -0.05m)：`z_interval_drift:DEE`；**ledger 侧 +0.05m**：`z_interval_drift:DEE`；**ledger 侧 +1e-6m**：RED(tol=1e-9，1e-6 必红) | **成立**（容差口径与简报「精确相等/≤1e-9」一致） |
| P-03 | 独立构造 refs=0 / refs=2 | refs=0：`evidence_ref_group_count:DFB:0`；refs=2：`evidence_ref_group_count:DFB:2` | **成立** |
| P-04 | 独立篡改 evidence 的 view_id / kind | kind：`kind_mismatch:DEE:window!=door`；view_id：`view_id_mismatch:DEE:North_view!=South_view`；opening-id 经 generated_handle 链接(refs=0 覆盖) | **成立** |
| P-05 | neuter 整 postcheck 调用→`pairing_drift=[]` | `test_gt_side_z_drift...` rc=1 \| 1 failed → **GREEN→RED**（证 z 漂移只由 postcheck 抓，别处不兜底） | **成立** |
| P-06 | 跑 `test_declared_not_emitted...` | rc=0 \| 1 passed；displace along 5m → `v3_code=elevation_opening_no_candidate`(原码上浮，未改写) | **成立** |

### §2 WI-2 必红夹具 + 正向 e2e

| 编号 | 命令 / 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| Z-05 双 datum | neuter `for candidate in view.floor_datums:`→`[:1]` | rc=1 → GREEN→RED 真锁（datum 循环承重） | **成立** |
| Z-02/03/04 z_transform | neuter datum 复合判定→`if False` | 逐 param：`axis_mismatch` FAILED、`offset_shift` FAILED、`scale_unit` PASSED → datum 复合对 2/3 承重；`scale_unit` 实由 line:1640 scale 一致性预检(同发 `z_transform_mismatch`)抓 | **成立**（机制见 MINOR-2） |
| Z-01 datum 换屋顶线 | 跑施工方测试 | rc=0 绿；归 z_transform/along_direction_mismatch | 成立 |
| Z-06/07 跨楼层/超顶 | neuter extractor `if len(containing)!=1:`→`if False` + 活体探针 | 基线：`v3_code=elevation_opening_floor_ambiguous`(extractor 抓)；neuter 后：`v3_code=gt_opening_z_outside_floor`(GT validator 第二道独立门抓)→**仍红** | **成立**(双门纵深防御，非假锁；归因见 MINOR-1) |
| F-00 §9.2 未做诚实性 | grep 测试 + 独立验证 2 条技术判断 + 抽验 1 格 | 测试文件 frame/title 夹具 **0 命中**(无伪造)；①`frame_entity_handle` 仅 `frame is None` 存在性检查、无 bbox/几何校验(**真缺门**)；②`_inside` 只测质心(`clip.xmin<cx<clip.xmax`)、entity 跨 frame 边无校验(**真缺门**)；抽验「frame handle 不存在」→ 实测被 `tarch_elevation_title_mismatch` 抓、G1 红(**brief 对冲声明正确**) | **成立**（诚实未竟 + 技术判断准确） |
| E-01 §6.6 十断言 | 跑 `test_sm24_forward_e2e_post_conditions` | rc=0 \| 1 passed；10 项断言全在且非恒真(`len==14`/z∈{[1.0,2.8],[1.0,3.4]}/门 z=[0.2,2.6]>z_floor/11C 非 structural/canonical 逐字节一致…) | **成立** |
| E-02 无生产分支 | grep `==14`/`11C` 生产码 | `==14` 三处全在 docstring/注释(G4 gap 守恒说明)；`11C` 生产码 **0 命中**(仅 request 侧声明)；无 `if len(openings)==14` 类分支 | **成立** |

### §3 WI-4 wall_thickness_m

| 编号 | 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| W-01 | 静态追证据链 + grep 字面量 | `_outer_skin_thickness_m`←`edge.thickness_native*mpu`(仅 `basis==outer_skin` 边)；生产码无 `0.24`/`240` 字面量 | **成立** |
| W-02 | 负锁测试 + neuter(X5) | `test_wall_thickness_is_none_without_complete_evidence` 3 情形(缺证据/不一致/空)→None；neuter 守卫→GREEN→RED | **成立** |
| W-03 | 读 bundle gt.json | `wall_thickness_m` set = `{0.24}`(12 外墙边全 240mm 全带 jamb 证据) | **成立** |
| W-04 | 读 sm21 v2 gt + scorer | sm21 顶层 `wall_thickness_m=0.24` 未动(v2 路径独立)；v3 改动不触 v2 | **成立** |

### §4 WI-5 出图质量

| 编号 | 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| R-01 | 独立重渲 sm21 legacy 六图 vs committed 基线逐像素 | 6/6 `diff_pixels=0`(`(fresh!=ref).any(-1).sum()==0`)；neuter `DIM 0.38→0.40`→GREEN→RED(X6) | **成立**（最硬一条） |
| R-02 | 独立复算墨迹亮度保留率 | 新(07-25)=**0.7655** ≥0.6；旧(07-24)=0.5195；提升 1.47x；底图灰度无色相(R==G==B) | **成立** |
| R-03 | 读 gt.json role + 静态追消费路径 | GT 全 8 zone role=`unspecified`；注记仅经 `build_gt_overlay_images_v3`(render:363-415)消费，不进 tarch_normalize/gt_extraction/gate；在 inventory 内 | **成立** |
| R-04 | grep 生产 import + 读 recalibrate_plan.py | `recalibrate_plan.py` 生产路径 **0 import**(离线脚本)；docstring 明示「只提议、converter 只校验」；converter 无自动回退 | **成立** |
| R-05 | neuter `_outline`→rectangle+return + 函数级测试 | `_outline` neuter→测试非绿(rc=4，rectangle 无法满足虚线断言)；函数级 `test_v3_outline_edges_are_equal_width...` 断言实线四边等宽(top==bottom==4)+虚线留隙 | **成立**（函数级权威；图像级测量受图例/虚线干扰为测量局限，见 NIT-1） |
| R-06 | 跑 8 个 fail-closed 测试 | rc=0 \| 8 passed(hash 漂移/sanitized collision/manifest 绑定不符/非 basename 路径/symlink 逃逸+四角越界/竞争 binding+奇异 affine/原子 out-dir 已存在 FileExistsError) | **成立**（≥6 项） |
| R-07 | 跑锚点测试 + neuter `_label_anchor`→bbox NW | rc=0 绿(8 zone 锚点含本区内)；neuter→GREEN→RED(polylabel 承重)；FIX-1 真锁 | **成立** |

### §5 WI-3 清理项

| 编号 | 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| M-01 | 读 schema diff + 跑锁测试 | 四死码「保留+文档化」(schema diff 纯注释块说明 §6.4 单通道设计)；`test_declared_not_emitted...` 绿(扫源码 0 emit + 真通道 v3_code 上浮) | **成立** |
| M-02 | monkeypatch `inspect_extraction_inputs` 抛 KeyError | **KeyError 透传**(未伪装成 BLOCK)；窄 except=`(ExtractionError,GtValidationError,PydanticValidationError)` | **成立** |
| M-03 | 临时计数 `extract_gt_v3` 调用次数 | 一次 `run_p2_conversion` 调用 **2 次**(plan-prepass + G9)，与简报「两次输入不同、不 dedup」声明一致；前置已包 try→BLOCK | **成立**（声明一致） |
| M-04 | 读镜像测试 docstring + gt_extraction diff | docstring 订正为「residual_ok 拥有、directed 手性由 lo/hi swap 那条覆盖」；`item is None` 死分支已删(改传真实 evidence binding) | **成立** |

### §6 命脉 + 产物

| 编号 | 方法 | 关键原始数值 | 结论 |
|---|---|---|---|
| X-01 | 抽 6 格 neuter 自复现 | 见下「假绿专项」详表；4 干净 GREEN→RED + 2 真实机制；**零 false-lock** | **成立** |
| X-02 | 上批三门 neuter | G1 directed-endpoint(4 failed)、G3 door-union(4 failed)、G10 lo/hi(1 failed) 全 GREEN→RED | **成立**（命脉未退化） |
| X-03 | diff 审容差/阈值/if | datum 循环条件逐字未改(仅加深缩进进循环=收紧)；`_PAIRING_Z_TOLERANCE_M=1e-9` 新门新容差(6 数量级余量论证)；零既有容差放宽 | **成立** |
| B-01 | 独立重算三 hash | inventory_sha256 自算=`d6880bbe...`=声明(10 文件逐 sha256 对账)；content_sha256 自算(`compute_gt_v3_content_sha256`)=`f289b53d...`=声明；manifest_sha256=`f3926bf8...`=声明 | **成立** |
| B-01b | 独立 join 审计表↔gt.json | 14 行×18 字段(§7.4 全列)非空；`opening_id` 双向唯一 14/14=GT 集合；逐行 z/host_zone/plan_along 与 GT 逐位一致；host 跨 8 zone | **成立** |
| B-02 | inventory 算法 + 字节敏感性 | 算法显式写进 index；tamper 一文件 sha256→inventory hash 变；drop 注记文件→hash 变(证注记在被签集合内) | **成立** |
| B-03 | 查 promotion | `case_tests/test_baseline/gt/` 仅 sm21、`gt_sources/` 无 sm24、GT `verification.status=candidate`、G10 未过 | **成立** |

> **三 hash 跨 run 不可复现**（ezdxf 时间戳/GUID）= 先于本批存在的已知跟进债，本批不修；GLM 按清单要求**直接对交付目录文件重算**(不靠重跑转换器)，三 hash 逐字对得上，故不构成阻塞。

---

## 3. findings（分级）

### BLOCKER
无。

### MAJOR
无。

### MINOR

**MINOR-1：Z-06/Z-07 门归因不精确（简报，非代码）**
- **事实**：简报 §3.1/§8 称 §9.3 第 6/7 格「由 extractor 楼层包含性检查拥有（同一道门）」。GLM 活体探针：基线由 `elevation_opening_floor_ambiguous`(extractor) 抓；neuter extractor 该检查后，改由 GT validator `gt_opening_z_outside_floor`(gt_schema:600，先于本批存在) 抓——**两道独立门**，非「同一道门」。
- **风险**：方向安全（属性被双重强制，不少强制）；但措辞会误导下批审阅者以为去掉 extractor 检查就放行。
- **出口**：简报订正为「窗 z 越层由 extractor 楼层包含性 + GT validator 双门强制」。**不需改码。**

**MINOR-2：z_transform scale_unit 归因不精确（简报，非代码）**
- **事实**：简报自查表 row 6「datum 复合判定→if False」暗示单一抓手抓全部 3 个 z_transform 变异。GLM 逐 param：datum 复合对 `axis_mismatch`/`offset_shift` 承重(2 翻红)，`scale_unit` 实由 line:1640 scale 一致性预检(同发 `z_transform_mismatch`)在 datum 循环前抓。
- **风险**：同上，覆盖面归因偏窄。
- **出口**：简报/注释标注「scale_unit 由 scale 一致性预检(line:1640)抓，datum 复合承重 axis/offset」。**不需改码。**

### NIT

**NIT-1：R-05 图像级 envelope 等宽测量不可靠**
- **事实**：清单 R-05 要求程序化统计交付图四边像素厚度；GLM 图像测量受图例红色元素(legend/datum 箭头)+opening 虚线框干扰，bbox 被污染、底边测得 0（假象）。权威核验改走函数级：`_outline` 实线四边等宽 + 虚线留隙由 `test_v3_outline_edges_are_equal_width...` 断言，neuter `_outline`→测试非绿。
- **出口**：R-05 以函数级测试为准；如需图像级量化，建议隔离 envelope 矩形(按 `_ENVELOPE` 最长连续红行/红列)再测。**不需改码。**

### INFO（不计为问题，记录备查）

- **§9.2 六格诚实标未竟 = 加分项**。GLM 确认无伪造夹具；其中 **F-01(frame handle 不存在) 实测已被 `title_mismatch` 覆盖**（brief 对冲声明正确）；**F-02(bbox 相同 handle 指向第二框)、F-06(entity 跨 frame 边) 是真缺门**（frame 仅存在性检查 + `_inside` 仅测质心），下批「先补门再补锁」立项正确。
- **bundle 三 hash 跨 run 不可复现** = 已登记跟进债，本批不修；GLM 直接对交付目录重算三 hash 逐字对齐，可验证性（拿晋升文件重算 inventory hash 对签名）仍在，仅失「从源图重新推导出同一份」。

---

## 4. 假绿 / false-lock 专项结论

# **无 false-lock。**

GLM 亲手 neuter 的格子与结果（均经 `cp` 安全副本还原，结尾三生产文件 `diff -q` 与备份全一致、`git status -- src/ scripts/` 干净）：

| 格 | neuter（文件:改成什么） | 跑的测试 | 结果 |
|---|---|---|---|
| **X1 WI-1 z 漂移**(命脉之命脉) | z 比较条件→`if False` | `test_gt_side_z_drift_makes_g9_pairing_red` | GREEN→**RED** 真锁 |
| X1' WI-1 整门拆接线(P-05) | postcheck 调用→`pairing_drift=[]` | 同上 | GREEN→**RED** 真锁 |
| **X2 §9.3 双 datum** | `for candidate in view.floor_datums:`→`[:1]` | `test_two_datums..._make_g1_red` | GREEN→**RED** 真锁 |
| **X3 §9.3 z_transform 复合** | datum 复合判定→`if False` | `test_z_transform_mutations...` | 2/3 翻 RED(axis/offset)；scale_unit 由 line:1640 真门抓 |
| **X4 §9.3 Z-06/07 楼层** | extractor `if len(containing)!=1:`→`if False` | `test_window_z_outside_its_floor_blocks_g9` | 仍 RED——改由 GT validator `gt_opening_z_outside_floor` 抓（双门纵深防御，**非假锁**） |
| **X5 WI-4 墙厚守卫** | `if any(...thickness_evidence is None...)`→`if False` | `test_wall_thickness_is_none_without_complete_evidence` | GREEN→**RED** 真锁 |
| **X6 WI-5/R-01 DIM** | `DIM=0.38`→`0.40` | `test_sm21_legacy_overlay_pipeline_is_unchanged` | GREEN→**RED** 真锁 |
| X-02 G1 directed-endpoint | `endpoint_bad=...`→`False` | `test_south_datum_partial_mutations...` | GREEN→**RED** 真锁(4 failed) |
| X-02 G3 door-union | union 面积恒等→`if False` | `test_door_structural_union_mutations...` | GREEN→**RED** 真锁(4 failed) |
| X-02 G10 raster lo/hi | lo/hi 检查→`if False` | `test_raster_lo_hi_control_swap...` | GREEN→**RED** 真锁 |
| R-05 `_outline` | 体→`draw.rectangle`+`return` | `test_v3_outline_edges_are_equal_width...` | 非绿(rc=4，rectangle 无法虚线)→承重 |
| R-07 `_label_anchor` | →bbox NW 角 | `test_plan_zone_label_anchors...` | GREEN→**RED** 真锁 |

**结论**：12 条新锁逐格真绑目标门，无一条是恒真式或被别处兜底的假锁；上一批命脉（G1/G3/G10）未退化。施工方自报「第 9 格第一版假锁已重做」与 GLM 复现一致（重做后 `_outline` 以虚线为承重断言，rectangle 过不了）。

---

## 5. 诚实性对账（施工简报声明 vs GLM 独立验证）

| 简报声明 | GLM 验证结果 |
|---|---|
| 全仓 1579 passed / 10 xfailed、零回归 | **验真**（独立单跑逐字一致） |
| 12 条新锁全部 neuter 自证为真锁、其中 1 条自查抓出假锁已重做 | **验真**（12 格全复现；第 9 格重做后真锁） |
| WI-1 postcheck 死码接线、z 容差 1e-9 | **验真**（emit≥1、消费 GT、两侧 z 漂移 RED、1e-6 必红） |
| WI-4 墙厚来自 12 外墙边 jamb 证据=0.24、fail-closed | **验真**（gt.json 0.24、3 负锁情形 + neuter） |
| sm21 legacy 6/6 逐像素不变 | **验真**（diff=0×6） |
| 底图墨迹保留率 0.747、~2x legacy | **验真量级**（实测 0.7655；比 07-24 bundle 0.5195 提升 1.47x；legacy DIM=0.38 为另一基线） |
| 审计表 14 行 18 字段、与 GT 双向 join | **验真**（独立 join 14/14 全一致） |
| 三 hash 最终值 | **验真**（自算逐字相等） |
| GT role 全 unspecified、注记 review-only | **验真** |
| §9.2 六格未做、其中两格真缺门 | **验真**（无伪造；frame 仅存在性 + `_inside` 仅质心 = 真缺门；F-01 实测已被 title_mismatch 覆盖） |
| Z-06/07「同一道门(extractor 楼层检查)」 | **验伪**（实为 extractor + GT validator 双门）→ MINOR-1 |
| z_transform row 6 暗示单一抓手 | **验伪**（scale_unit 由 line:1640 抓，datum 复合承重 2/3）→ MINOR-2 |
| extract_gt_v3 不 dedup、两次输入不同 | **验真**（计数=2，与声明一致） |
| bundle hash 跨 run 不可复现=跟进债 | **验真**（直接对交付目录重算可对齐；不可复现性本身属实） |
| z5→corridor（主控裁定） | **无法判定**（属主控人核裁定权，非 GLM 验证范围；几何上 z5 确为 8 顶点 C 形中央区，与裁定自洽） |

---

## 6. 环境与探针位置（供主控复现）

- 仓库：`/workspaces/EnergyPlus-Agent-dev`（分支 `6.15_ValidationArchM0toM4`，HEAD `70dceb8`）
- 环境：python 3.12.13 / ezdxf 1.4.4 / Pillow 12.2.0 / numpy 2.4.4 / shapely 2.1.2 / pydantic 2.13.3 / pytest 9.0.3
- 探针目录：`/tmp/glm_elev_debt_probe/`
  - `full_regression.log`（独立全仓回归）
  - `bak/{tarch_normalize,gt_extraction,render_gt_overlay}.py`（安全副本）
  - `neuter_x01.py`（X-01 六格命脉 harness）
  - `neuter_x4_x3.py` / `investigate_x4_x3.py`（Z-06/07 双门 + scale_unit 机制深挖）
  - `wi1_pseries.py`（WI-1 P-02/03/04 独立 `_verify` 调用）
  - `p05_p06_x02.py`（P-05 整门 neuter + P-06 原码 + X-02 三门）
  - `wi5_quant.py` / `r05_outline.py`（R-01 像素 / R-02 墨迹 / R-05 envelope）
- 还原校验：三生产文件 `diff -q` 与备份全一致；`git status -- src/ scripts/` 干净；唯一 `NEUTER` 字样为合法 env seam `TARCH_NEUTER_GATE`(line:145，派工单明示、既有提交码)。
- **GLM 未修改任何生产代码**（neuter 探针已全部还原）。

---

**裁决生效条件**：主控接受 2 条 MINOR 为简报/注释订正项（不需改码、不需重跑），即可进入用户签字流程。签字收官的剩余人核项（四条地面基准线 + 8 区房间用途，z5=corridor）按主控既定裁定进行。
