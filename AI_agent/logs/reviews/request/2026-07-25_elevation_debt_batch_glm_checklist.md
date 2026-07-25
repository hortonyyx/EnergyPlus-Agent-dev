# 立面批「六笔债」：GLM 结构化核验清单

**日期**：2026-07-25
**清单作者**：主控 Opus（只定义核验命题与红线，不作本轮裁决；主控非施工方）
**执行与裁决方**：GLM-5.2
**被核验施工方**：Claude 侧 Opus 执行档子代理
**核验对象**：`src/agent/judge/tarch_normalize.py`、`src/agent/judge/gt_extraction.py`、`src/agent/judge/gt_schema.py`、`scripts/tool_scripts/render_gt_overlay.py`、`tests/test_tarch_elevation_must_red.py`、`tests/test_gt_overlay.py` 及本批新增测试、`logs/experiments/2026-07-25_sm24_gt_review/` 产物
**权威顺序**：合同细稿 `AI_agent/proposals/tarch_elevation_spec.md` ＞ 2026-07-24 Opus 裁决书 ＞ 本批派工单 `2026-07-25_elevation_debt_batch_dispatch.md`；**施工简报与施工方自己的测试只算待验陈述，不算证据**
**基线**：commit `e13efd3`，全仓 `1556 passed, 10 xfailed`

---

## 0. 执行纪律与回填格式

### C-00 独立证据纪律

- **验什么**：你的反例期望必须独立于施工方的测试夹具与硬编码期望。
- **怎么验**：
  1. 全部命令从仓库根执行：`cd /workspaces/EnergyPlus-Agent-dev`。
  2. 记录 `git rev-parse HEAD`、`git status --short`、Python / ezdxf / Pillow / pytest 版本。
  3. 自建探针放新目录（建议 `/tmp/glm_elev_debt_probe/`）；探针只可 import 生产 API 与通用库，**不得 import `tests/test_tarch_elevation_must_red.py` / `tests/test_gt_overlay.py` 里施工方的 helper / fixture / 期望常量**。
  4. 所有 neuter（把生产码判定逻辑改坏）必须**直接改生产文件**。**还原方式：改之前先 `cp` 一份安全副本，跑完 `cp` 回来**（`git checkout -- <file>` 也可用，因为施工已 commit——但用 `cp` 更稳，能防你误判基线）。**结束时 `git status --short` 必须与开始时一致，且三个生产文件与安全副本 `diff -q` 全一致、无 `if False` 残留**。
  5. 每项回填：实际命令、退出码、关键原始数值、`成立 / 不成立 / 阻塞`。**不得只写「测试通过」**。
- **成立**：探针零施工方 fixture 导入；关键期望来自本清单或你的独立手算；每项有原始值与布尔结论。
- **不成立**：复用施工方 fixture / expected / golden，或只引用「施工方测试是绿的」而无独立活体探针——该项证据一律无效。

### C-01 变更范围与禁区

- **验什么**：施工没有借机改禁区。
- **怎么验**：`git diff --name-only e13efd3..HEAD`（若未 commit 则 `git status --short` + `git diff --stat`）；逐一检查是否触碰：`case_tests/test_baseline/gt/`、`gt_sources/`、`case_tests/e2e_tests/*/case_data/`、scorer（`correction_score.py` 的判分逻辑）、Va / Vg、v2 legacy adapter、reading / correction / execution 子系统、`render_gt_overlay.py` 的 `_pixel_for_world_plan` / `_pixel_for_world_elevation` 函数体与 affine 数学。
- **成立**：上述禁区改动数 = 0（`correction_score.py` 若仅因 WI-4 出现只读消费变化，须单列说明且不改判分公式）。
- **不成立**：任一禁区被改而无主控明确授权；或投影数学函数体有任何改动。

### C-02 回归基线

- **怎么验**：独立干净全跑 `python -m pytest -q -p no:cacheprovider`，记录完整尾行。
- **成立**：`passed ≥ 1556`（新增测试使其上升属正常）、`xfailed == 10`、`failed == 0`、无新 skip 未解释。
- **不成立**：任何 failed；或 xfail 数变化而简报未解释。

---

## 1. WI-1：converter ↔ GT 配对一致性 postcheck（原 MAJOR-1）

背景：合同 §6.5 [S] 要求完整 GT 产出后，按每个 `opening_elevation` source ref 的 generated handle 反查 evidence，与 converter pairing ledger 比较（view id / opening id / kind 相同 + **z interval 等于 converter 计算值** + 每 relevant pair **恰一组** refs），不一致 BLOCK。上一批此门完全缺失、诊断码 `tarch_elevation_pairing_drift` emit 引用数 = 0（死码）。

### P-01 死码已接线且真在生产路径上

- **验什么**：`tarch_elevation_pairing_drift` 不再是死码，且位于**正常 sm24 转换会走到**的路径。
- **怎么验**：
  1. `grep -rn "tarch_elevation_pairing_drift" src/ scripts/ tests/`，区分「定义/注册」与「emit」。
  2. 静态读 postcheck 实现，确认它消费的是 `extract_gt_v3` 的**返回值**（不再丢弃）。
  3. 跑一次真实 sm24 转换，确认 postcheck 被执行（可临时在门内加计数/断言式探针，跑完还原）。
- **成立**：emit 引用 ≥ 1；postcheck 消费 GT 返回值；真实 sm24 路径确实执行到该门。
- **不成立**：仍是死码；或只在测试里被调用、生产路径绕过；或它比较的是 ledger 与 ledger（自己跟自己比）。

### P-02 z 漂移必须变红（本门存在的唯一理由）

- **验什么**：converter 审计行 z 与 GT z 是两条独立代码路径，本门必须强制它们相等。
- **怎么验**：
  1. 先跑通一次真实 sm24（基线：postcheck 绿）。
  2. **只**在 converter ledger 侧（或只在 GT 侧，两侧各做一次）把某一个 opening 的 z interval 平移一个**很小**的量（建议 `+0.05 m` 与 `+1e-6 m` 各试一次），其他字段一律不动。
  3. 重跑生产转换，看 `tarch_elevation_pairing_drift` 是否 emit、report 是否 BLOCK。
- **成立**：`+0.05 m` 必红；`+1e-6 m` 的行为与施工简报声明的容差口径一致（简报声明精确相等 → 也必红；声明 ≤1e-9 → 也必红；声明更宽 → 该宽容差须有合同依据，否则记 finding）。
- **不成立**：z 漂移仍绿；或门只比较了 handle/kind 而**没比较 z 值**（这正是上一批的洞）；或容差宽到 `0.05 m` 都放行。

### P-03 refs 基数（恰一组）真被检查

- **怎么验**：构造两种反例——某 relevant pair 的 refs 变成 0 组、变成 2 组；各跑生产转换。
- **成立**：两种都 BLOCK。
- **不成立**：任一放行；或只检查了「≥1」而没检查「恰 1」。

### P-04 view id / opening id / kind 不一致真被检查

- **怎么验**：分别篡改一个 evidence 的 view id、opening id、kind，各跑一次。
- **成立**：三者各自独立触发 BLOCK。
- **不成立**：任一放行；或三者靠同一个笼统比较兜住而无法区分（后者不算 finding，但要在回填里写明实际机制）。

### P-05 postcheck 是真门，不是恒真式

- **验什么**：防「门在算但永远成立」的假绿。
- **怎么验**：neuter 该 postcheck 的判定核心（例如把不一致判断改成 `if False`），跑 P-02/P-03/P-04 的反例测试。
- **成立**：neuter 后这些反例**全部由红转绿**（证明是它在抓，不是别处兜底）。
- **不成立**：neuter 后反例仍红（说明别的门在兜，本门是摆设，且简报的对账声明不成立）。

### P-06 门序不被 WI-3 的「避免双跑」优化破坏

- **验什么**：施工方可能为消除 `extract_gt_v3` 双跑而复用 G9 结果；不得因此让 postcheck 在 G9 失败时被跳过、或让 G9 的 fail-closed 语义变松。
- **怎么验**：构造一个「G9 会失败」的输入（例如让 elevation assignment 抛错），确认整体仍 BLOCK 且 `tarch_v3_precondition.context.v3_code` 带原码上浮（合同 §6.4）。
- **成立**：G9 失败仍 BLOCK、原码不被吞不被改写成 PASS。
- **不成立**：出现「G9 失败但整体 PASS」、或异常被吞成通用 message 而丢失原码。

---

## 2. WI-2：§9.3 / §9.2 必红夹具 + §6.6 正向 e2e（原 MAJOR-2）

### Z-01 ~ Z-07 §9.3 z 组七类变异逐条必红

对下列每一类，独立构造变异并跑生产门，**逐条回填**：

| 编号 | 变异 |
|---|---|
| Z-01 | datum 换成屋顶线 |
| Z-02 | datum source axis 与 z axis 不符 |
| Z-03 | z scale `0.001` → `1.0` |
| Z-04 | offset 平移 0.2 m |
| Z-05 | 两个 datum 推出不同 offset |
| Z-06 | 窗框跨楼层 |
| Z-07 | 窗 z 高于 ceiling |

- **怎么验**：每条：① 跑施工方新增的对应 must-red 测试确认为红；② **你自己**独立造同类变异（不复用其 fixture）跑生产门确认为红；③ neuter 你判断的目标门 → 该条必须由红转绿。
- **成立**：三步全过，且第 ③ 步证明「该门在算」。
- **不成立**：任一条无对应测试；或你的独立变异放行；或 neuter 目标门后测试仍红（= false-lock，与上一轮「九门假锁」同族，**这是本次核验的头号目标**）。
- **特别注意**：合同明写「不得因最终数值仍像窗高而放行」——若某条变异后 z 仍落在 `[1.0,2.8]` 之类合理区间却被放行，直接记 MAJOR。

### F-00 §9.2 六格「未做」的诚实性核验（**本组只验这一条，F-01~F-06 本批不适用**）

施工方**诚实交接：§9.2 六格必红夹具 0 条、未做**（上下文预算耗尽，按派工单优先级排在最后一档）。主控已接受并登记为下一批。

- **验什么**：这条「未做」的自述是否属实——**没有伪造夹具冒充已做**，且它对「其中两格现在根本红不了」的判断是否成立。
- **怎么验**：
  1. `grep -rn "frame\|title\|alias" tests/test_tarch_elevation_must_red.py`，确认确实没有 §9.2 六类的夹具（不是改名藏起来了）。
  2. 独立验证施工方的两条技术判断：① 现实现对 `frame_entity_handle` 是否**只检查存在性**（`frame is None`）而不校验几何/bbox ⇒ 构造「bbox 相同但 handle 指向第二框」的反例，看是否**真的不红**；② 「entity 跨 frame 边」是否确实无对应校验。
  3. 抽验一格施工方说「大概率已被 `tarch_elevation_title_mismatch` 覆盖但没实测」的（如 frame handle 不存在 / 框内 2 个标题），实际跑一次，回填真实结果。
- **成立**：确无伪造；①② 两条判断经你独立复现属实（即**真缺门、不是缺测试**）。
- **不成立**：发现有夹具冒充；或①②判断不成立（若你验出其实能红，如实写——这对下一批的施工范围很重要）。

### F-01 ~ F-06 §9.2 frame / title 组六类必须 BLOCK（**本批不适用，留给下一批**）

| 编号 | 变异 |
|---|---|
| F-01 | frame handle 不存在 |
| F-02 | bbox 相同但 handle 指向第二框 |
| F-03 | 框内 0 个标题 |
| F-04 | 框内 2 个标题 |
| F-05 | `北立面图` 未显式列入 alias map 却 request 写 `北立面` |
| F-06 | 两个 full North view 覆盖同 floor；entity 跨 frame 边 |

- **怎么验**：同 Z 组三步法。
- **成立**：六类全 BLOCK，且各自能指出是哪道门抓的。
- **不成立**：任一放行；或多条实际被 schema 层笼统兜住而目标门从未参与（此时不算假绿，但须在回填里写明真实机制，并核对施工简报是否诚实描述）。

### E-01 §6.6 sm24 正向 e2e 十条断言齐备

- **怎么验**：定位本批新增/扩充的 sm24 e2e 测试，逐条对照合同 §6.6 十项（source views = 1 plan + 4 elevation；四 facade projection key 落在正确 boundary segment；`len(openings) == 14`；11 window `z_interval` 全非空；window z 只出现 `[1.0,2.8]` 与 `[1.0,3.4]`；3 exterior door 有 source-observed z 且非 floor default；door z 只来自受校验 structural outline、`11C` 在 excluded inventory 且不改变 z；每 opening 有 plan ref、每 relevant opening 有 elevation ref；7 interior door 不在 GT；canonical reload 逐字节一致）。
- **成立**：十项全部有可指认的断言语句。
- **不成立**：缺项而简报声称已落（诚实性 finding）；或断言写得恒真（例如断言 `>= 0`）。

### E-02 生产算法没有按 sm24 数字分支

- **验什么**：合同硬约束「数值断言属真实 anchor fixture，生产算法不得按这些数字分支」。
- **怎么验**：`grep -rn "== *14\|11C\|== *11\b" src/agent/judge/` 逐处判断是生产分支还是合法的 exact role map / excluded inventory 声明。
- **成立**：生产路径无「按 opening 数量 / z 具体值」的分支；`11C` 出现处仅为 request 侧声明的 exact 排除项。
- **不成立**：生产码里出现 `if len(openings) == 14` 之类。

---

## 3. WI-4：`wall_thickness_m` 发射（用户 Q2）

### W-01 值有证据链、不是硬编码

- **怎么验**：静态追 `wall_thickness_m` 的赋值来源（原为 `gt_extraction.py:647` 的 `None`）；确认它来自 manifest 声明的 `default_wall_thickness_m` 或转换器厚度证据体系，而非字面量 `0.24`。
- **成立**：能画出「来源字段 → GT 字段」的链路；无字面量。
- **不成立**：代码里出现 `wall_thickness_m=0.24` 之类硬编码；或来源是「猜的默认值」而无证据。

### W-02 fail-closed：无证据不许瞎填

- **怎么验**：构造一个证据缺失的输入（例如 manifest 不声明厚度），跑提取。
- **成立**：结果为 `None` 或 BLOCK（与简报声明的语义一致），**不出现「悄悄填一个默认值」**。
- **不成立**：无证据时仍产出具体数值。

### W-03 sm24 实测值正确

- **怎么验**：读本批新 bundle 的 `gt/gt.json`，取 `wall_thickness_m`。
- **成立**：`== 0.24`（sm24 外墙 240 mm）。
- **不成立**：缺字段、为 null、或数值不符（注意单位：应为米，不是 240）。

### W-04 不破坏 sm21 与判卷侧

- **怎么验**：确认 sm21（v2 legacy 路径）的 `wall_thickness_m` 未被改动；跑判卷相关测试族。
- **成立**：sm21 gt 与判卷测试零变化。
- **不成立**：sm21 资产被写、或判卷结果漂移。

---

## 4. WI-5：出图质量（**你看不了图，以下全部是可编程判据**）

### R-01 sm21 legacy 输出逐像素不变（最硬的一条）

- **验什么**：`DIM` 常量与 legacy `overlay_plan` / `overlay_elev` 是 sm21 已锁定基线资产的生产路径；本批为改善 sm24 观感而动亮度合成，**绝不能**让 sm21 的图变。
- **怎么验**：
  1. 用**当前工作区代码**重新生成 sm21 的 legacy overlay（six 张：`overlay_1f_view` / `overlay_2f_view` / 四立面）。
  2. 与 `case_tests/test_baseline/gt/sm21_anchor/renders/overlay_*.png` 逐像素比较（`numpy` 数组 `array_equal`，或 SHA256）。
- **成立**：六张全部逐像素相等（或施工方给出的等价严格证明成立），且有一条测试锁住这一点。
- **不成立**：任一张有像素差；或只有「看起来一样」的口头声明；或没有测试锁。

### R-02 底图可见度确有改善且有量化判据

- **怎么验**：读简报给出的量化判据（如原图墨迹像素在成图上的亮度保留率），**自己独立复算**：取 `case_tests/e2e_tests/sm24_anchor/case_data/South_view.png` 与新 bundle 的 `overlay_South_view.png`，用「原图非背景像素」掩膜比较两者亮度统计。
- **成立**：新图的墨迹亮度保留率显著高于旧 bundle（`logs/experiments/2026-07-24_sm24_gt_review/gt/renders/overlay_South_view.png`）的同一指标；简报的判据可复现。
- **不成立**：指标无改善；或简报判据复算不出来（数字须随稿落盘——这是本项目登记过的教训）。

### R-03 房间用途注记不回写 GT、不参与任何机器判定

- **验什么**：信任边界。用途注记是 review-only 人工输入。
- **怎么验**：
  1. 读新 bundle `gt/gt.json`，确认所有 zone 的 `role` 仍是 `unspecified`（或原值），**未被注记污染**。
  2. 静态追注记的读取点，确认它只进入绘图/标签路径，**不进入任何 gate 判定、不进入 GT canonical hash 的语义字段**。
  3. 反例：把注记文件里某个 zone 的用途改掉，重跑，确认**除了图与 inventory hash 之外没有任何机器结论变化**（GT canonical hash 的语义部分、门结论、审计表 z 全不变）。
- **成立**：三步全过。
- **不成立**：GT 的 role 被写入；或注记影响任何门/判定；或注记未纳入 review-index inventory（用户签的是整包，注记必须在被签之列——见 B-02）。

### R-04 校准信任边界未被自动化侵蚀

- **验什么**：合同 §7.3 明写「不得退回 legacy v2 的自动密度框校准来尽量画一张」。本批允许写**离线检测助手**提议控制点，但**机器只提议、主控声明、converter 只校验**。
- **怎么验**：
  1. 静态确认检测助手**不在**生产判定路径上（不是 `tarch_normalize` / `gt_extraction` / overlay 生产分支的依赖）。
  2. 确认 converter 仍只做「校验声明的控制点」（残差、三点非共线、有向 lo/hi、四角反投影），没有「校验失败就自己重新检测」的回退。
  3. 反例：把 request 里一个控制点改坏，确认 G10 / calibration 门仍 BLOCK 而不是自动纠正。
- **成立**：三步全过。
- **不成立**：检测助手被接进生产判定；或出现自动回退/自动纠正。

### R-05 envelope 四边等宽

- **怎么验**：对新 bundle 的四张立面 overlay，程序化统计白色 envelope 描边在上/下/左/右四条边上的像素厚度（沿边采样若干列/行，数连续白像素）。
- **成立**：四边厚度一致（均为设定线宽，允许 ±1 px 抗锯齿）；旧 bundle 的底边应显著更细（作为对照，证明确实修了）。
- **不成立**：底边仍是 1 px；或四边不等宽。

### R-07 8 个区在交付图上全部有标签，且标签锚点落在本区多边形内

- **背景**：主控轻门在第一版交付图上抓到 **z4（6 顶点 L 形）无标签**——锚点用了外接框西北角，该点落在 z5（8 顶点 C 形）内，随后被 z5 的填充盖掉。已要求返工（锚点改为保证落在本多边形内的点 + 标签统一在所有填充之后画 + 加锁）。
- **怎么验**：
  1. 读最终 `logs/experiments/2026-07-25_sm24_gt_review/gt/renders/overlay_1f_view.png`，程序化确认 **8 个 zone id 的标签像素都存在**（例如按各 zone 的锚点邻域检测非背景文字像素，或直接复算锚点并检查该处有标签描边色）。
  2. 独立复算每个 zone 的标签锚点，用点在多边形内测试（射线法自己写，别用施工方 helper）验证 **8/8 落在本区多边形内部**，特别核 z4、z5 两个非凸区。
  3. neuter：把锚点算法退回 bbox 角 → 对应的锁必须变红。
- **成立**：三步全过。
- **不成立**：任一 zone 无标签；或任一锚点落在区外；或退回 bbox 角后锁仍绿（false-lock）。

### R-06 overlay 的 fail-closed 门一条没松

- **怎么验**：对合同 §7.3 列出的每一项（raster 缺失 / hash 漂移 / symlink 逃逸 / view id 不存在或重复 binding / affine 奇异 / 三点共线 / 残差超限 / 有向 lo/hi 对调 / 四角反投影越界 / manifest hash 不一致 / 名字碰撞 / out-dir 已存在），至少抽验其中 **6 项**（必含 hash 漂移、lo/hi 对调、四角越界、out-dir 已存在），构造反例跑生产 overlay 生成。
- **成立**：抽验各项全部 raise / BLOCK。
- **不成立**：任一放行（尤其 `write_gt_overlay_images_v3` 的「目标目录已存在即拒绝」被为了原子打包而放松——合同 §7.3 明写不得放松）。

---

## 5. WI-3：清理项（MINOR / NIT）

### M-01 死登记码处置一致

- **怎么验**：确认四个原死码（`tarch_elevation_opening_no_candidate` / `..._assignment_ambiguous` / `..._kind_mismatch` / `tarch_interior_opening_elevation_not_applicable`）要么被真接线（有 emit + 对应锁），要么被删且有文档/注释说明「G9 立面失败统一走 `tarch_v3_precondition`」。
- **成立**：处置一致、无「既没删也没接线」的残留；若选接线，须有反例证明能真 emit。
- **不成立**：注册表里仍留零引用码而无说明；或声称接线但构造不出触发路径。

### M-02 宽 except 已窄化且不吞真 bug

- **怎么验**：读 `_run_g9_v3_preflight` 的 except 子句；构造一个「非预期异常」（例如 monkeypatch 让内部抛 `KeyError`），确认它**炸出来**而不是变成一条不透明的 BLOCK message。
- **成立**：预期的提取/校验异常 → BLOCK 且带原码；非预期异常 → 抛出。
- **不成立**：仍 `except Exception`；或窄化后反而吞掉了本该 BLOCK 的合法失败（跑 P-06 交叉确认）。

### M-03 前置 `extract_gt_v3` 不再裸崩 / 不再无谓双跑

- **怎么验**：构造「过了 P2 plan 门但过不了 extraction 输入」的用例，确认返回 blocked report 而非 traceback 崩溃；并确认 `extract_gt_v3` 在一次转换中的调用次数（可临时计数）符合简报声明。
- **成立**：不崩、有诊断产物；调用次数与声明一致。
- **不成立**：仍崩；或声称消除双跑但实际仍跑两次（诚实性 finding）。

### M-04 NIT 处置

- **怎么验**：镜像测试 docstring 是否已订正为「靠 elevation `residual_ok` 抓」（或另补了 directed 手性夹具）；`gt_extraction.py` 的 `item is None` 死分支是否已删或已加注释。
- **成立**：二者各有明确处置。
- **不成立**：docstring 仍描述错误机制（会误导未来审阅者对覆盖面的判断）。

---

## 6. 全局：假绿 / false-lock 专项与产物

### X-01 新增锁的 neuter 抽样复验（本次核验的命脉）

- **怎么验**：从施工简报的必红自查表中**随机抽 6 格**（必含 §9.3 的至少 3 格、WI-1 的至少 1 格），逐格按简报声明的 neuter 方式**自己动手复现**：改坏 → 跑测试 → 看是否真由绿翻红 → 还原。
- **成立**：抽样 6 格全部复现成功，与简报声明一致。
- **不成立**：任一格复现不出来（= 自查表造假或 false-lock）→ 直接判 REWORK，并把该格作为 BLOCKER 写进裁决。

### X-02 上一批命脉未退化

- **怎么验**：跑 `pytest -q tests/test_tarch_elevation_must_red.py`；并对上一批已验真的门中抽 3 类（G1 有向端点、G3 门 union 面积恒等、G10 raster lo/hi 对调）各做一次 neuter 复验。
- **成立**：三类仍真红；must-red 文件全绿。
- **不成立**：任一退化为假锁。

### X-03 无「为过测试而放松」的痕迹

- **怎么验**：审 diff 中所有容差、阈值、`if` 条件的改动；确认没有为了让某测试变绿而放宽判定。
- **成立**：零此类改动；WI-1 新引入的 z 容差有合同或明确理由支撑。
- **不成立**：发现放宽。

### B-01 新 bundle 完整且与声明 hash 一致

- **怎么验**：核 `logs/experiments/2026-07-25_sm24_gt_review/` 下：`gt/gt.json`、`gt/renders/`（7 张：`gt_plan.png` / `gt_elev.png` / `overlay_1f_view.png` / 四立面）、`opening_elevation_audit.json`（14 行）、`review_index.json`、conversion report；自己重算 GT canonical hash 与 review-index inventory hash，与简报声明比对。
- **成立**：文件齐备；两个 hash 自算值与简报声明逐字相等；audit 恰 14 行且每行含 opening id / kind / host zone / along 区间 / z 区间 / datum 端点映射。
- **不成立**：缺件；hash 对不上；audit 行数不符或字段缺失。

### B-01b 审计表字段齐备（合同 §7.4 [S]，主控轻门返工项 FIX-3）

- **背景**：主控轻门发现 07-25 首版审计表比 07-24 版**少了三个字段**——`opening_id`、`plan_world_along_interval`（两者均为合同 §7.4 [S] 明文要求）、`host_zone_id`（用户核房间归属所需）。已要求补回并加锁。
- **验什么**：最终交付的 `opening_elevation_audit.json` 能真正支撑合同 §7.4 要求的人核动作。
- **怎么验**：
  1. 读最终审计表，确认 14 行**每行**都含 §7.4 清单的全部字段（`opening_id` / `evidence_id` / `view_id` / `facade_family` / `floor_id` / `kind` / `plan_world_along_interval` / `elevation_source_along_interval` / `world_along_interval` / `z_interval` / `datum_entity_handle` / `datum_source_start_point` / `datum_source_end_point` / `declared_world_along_lo_source_endpoint` / `mapped_endpoint_pair` / raw+structural handles）且非空。
  2. **独立 join**：用 `opening_id` 把审计表 join 到 `gt/gt.json` 的 `openings[]`，双向核 14/14 一一对应；逐行核 `z_interval` 与 GT 逐位一致（≤1e-9）、`host_zone_id` 落在该楼层 8 个 zone id 内、`plan_world_along_interval` 与 GT 对应值一致。
  3. 核 overlay 上标注的 opening id 与表里的 `opening_id` 是同一套（抽验 3 个）。
  4. neuter：删掉补回字段的赋值 → 对应的锁必须变红。
- **成立**：四步全过。
- **不成立**：任一字段缺失/为空；join 对不上；或锁 neuter 后仍绿。
- **注意**：这条是「交付物能否支撑人核」的验收，不是代码风格问题——合同明写该表是整面镜像残余风险的**强制 backstop**，缺字段等于该 backstop 失效。

### B-02 review-index 覆盖整包（含房间用途注记）

- **怎么验**：核 `review_index.json` 的 inventory 是否覆盖用户最终会看的全部产物；特别确认 WI-5b 的用途注记文件在其中；改动其中任一文件一个字节 → 重算 inventory hash 必须变。
- **成立**：整包覆盖；任一文件变动都会改变 inventory hash。
- **不成立**：有产物游离在 inventory 之外（用户签的是整包，游离件等于没签）。

### B-03 未 promotion

- **怎么验**：确认 `case_tests/test_baseline/gt/`、`gt_sources/` 零写入；GT `verification.status` 仍为 `candidate`；G10 未通过。
- **成立**：三者全部满足。
- **不成立**：任一被提前晋升（严重——人签未完成）。

---

## 7. 裁决格式

回填完全部条目后出裁决书 → `AI_agent/logs/reviews/verdict/2026-07-25_elevation_debt_batch_glm.md`，须含：

1. **总裁决**：`APPROVE` / `APPROVE-WITH-CHANGES` / `REWORK`（**X-01 任一格复现失败 ⇒ 必须 REWORK**）。
2. **逐条回填表**：编号 / 命令 / 关键原始数值 / `成立·不成立·阻塞`。
3. **findings**：按 BLOCKER / MAJOR / MINOR / NIT 分级，每条写清事实、风险、出口。
4. **假绿 / false-lock 专项结论**：明确写「有 / 无」，并给出你亲手 neuter 的格子清单与结果。
5. **诚实性对账**：施工简报的声明中，哪些你独立验真、哪些验伪、哪些无法判定（**无法判定就写无法判定，不要猜**）。
6. **你的环境与探针位置**，便于主控复现。

**纪律提醒**：你的强项是「照单验证性审阅」——把每条命题当成一个必须给出布尔结论的实验，动手跑、不靠阅读推断。凡是你没亲手跑出来的，写「无法判定」，不要写「应该没问题」。
