# 六审裁决（GLM，续同一线）：三处修全部为真 · 本轮没找到赚钱的作弊 · 放行书写，成绩闸随层

- **送审对象**：commit `4b3877d` 的工作树（HEAD `f9ca2ba` 只含请求书；送审期间树未被送审方改动，进场时干净）
- **审阅方**：GLM 家族（glm-5.3）· **日期**：2026-08-24
- **限制遵守**：未 commit / push；未改 `src/`、`case_tests/`、gt、送审方任何既有**源**文件。
  status 里的 `out/*.json` 改动 = 我按请求书重跑 `run_all.py` 及本轮新夹具所致（这些脚本本就重写产物）。
  本轮新增文件全部 `glm_` 前缀，清单见文末。

---

## 复验基线（全表逐位复现）

```bash
python3 AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/run_all.py
```

sm25 1F **110 目标 / C1 100.0 / C2 98.6 / C3 0 / C4 0.722 / C5 100.0(31/31)** ·
2F 106 / 98.1 / 97.0 / 1 / 0.524 / 100.0(30/30) · sm24 70 / **95.7** / 97.5 / 1 / 5.786 / 95.2(20/21)；
gt 侧 sm25 **93.3** / sm24 **100.0**。诚实门状态：sm25 两层**十一门全绿**；
sm24 = spacing 红（未申报 120 墙，已知）+ reconcile/forward degraded（78 条弃权、无家具层，已知）。
墨列组直方图：**1F {1:49} · 2F {1:46} · sm24 {1:98}**（含 4 条真实心带），与请求书一字不差。
`skip_unscored_tails` 三案全红（1F [spanacct,runs] · 2F [runs] · sm24 [spanacct,runs,spacing]）
——**你作废「分辨率级盲区」的声明属实，我接受**。口径变化（misname/drop_opening_role 的 gt 侧=诚实、
改由 openrole 门负责）核对代码属实：`_extent` 桥接只读命名（F-87），族角色另由 openrole 门守。

### 三处修的独立复验（不信 RESULTS，直接对夹具跑新门）

```bash
cd <repo根>
for f in sm25_1f_GLM_band_collapse sm25_1f_GLM_fab_fabricated_profile; do
  python3 .../tools/checks_as_drawn_v2.py .../out/$f.json .../tools/cfg_1f_full.json /tmp/chk.json; done
# 2F band_collapse 换 cfg_2f_full
```

| 夹具 | 新门组实测 |
|---|---|
| band_collapse 1F | **support 红 10 + runs 红 10**，其余九门绿 |
| band_collapse 2F | **support 红 11 + runs 红 11**，其余九门绿 |
| fab_fabricated_profile | **gap_evidence 红 1**，其余十门绿 |
| fab_honest_profile（对照） | opennaming 红 1（零墨命名 door）|

三处修（完整性门 / WIDTH_COEFF 1.0 / 候选 profile 重算）**全部为真且方向正确**。

---

## 总裁决：**APPROVE —— 可以开始动 gt（写 as-drawn 层）**；四条成绩闸随层落库（见 Q3）

**判据**。五审我承诺「1–3 落地后一轮即可放行书写」；本轮 1–3 落地且经我独立复验，
Q1 我又系统性打了**八个攻击面**（含你点名的两处），**没有找到一个能在这套（门+判分器）上
赚钱的真实作弊形态**——这与五审（band_collapse 两项优于诚实+八门全绿）有本质差别。
本轮新发现（矩阵卫生 ×1、未锚孔径 ×2）都不触碰 denominator 与层内容，且验收是机械的。
残余风险随层写成**成绩闸**，不阻塞书写。

---

## Q1：新作弊搜索——主答：没找到赚钱的；两处点名各给了硬答案；另交两条实测发现

### 攻击面清点（每条都实测过，含阴性）

| # | 攻击面 | 实测 | 结果 |
|---|---|---|---|
| 1 | **免费桥**：把 7 个「有墨但判 not_opening/ambiguous」的候选改名 door（命名门只要 1 px 墨） | gt 侧 93.3 → **93.3** | 零收益 |
| 2 | 命名面上限：**全部** 85 个候选当门桥掉 | gt 侧 93.3 → **93.3** | 整条命名攻击面关闭：失败目标全是欠读墨（0.12 m 残段 SHORT/NO_CANDIDATE），不是没桥 |
| 3 | **pos_m 滑动**（recompute 门只锚 pos_m↔edges 的相对仿射，runs_m 只验长度 ⇒ pos_m 无绝对锚） | 逐线扫描 δ∈[−0.12,+0.12]：最大收割 L012 0.257→**0.247**；统一 +0.08 ⇒ C1 100→90.0 | 不赚钱 |
| 4 | **缩画框**（drawing_box 产物自报）：sm24 target 包络实测铺满 x[0,10]×y[0,20]（70 target+50 allowed+21 opening 全域） | 任何边切都吃周界墙覆盖 | C2 赔，不赚钱 |
| 5 | 标定缩放谎（mm_per_px 相对自洽） | ±0.5% 内不可检出但远端 C1 赔 | 不赚钱 |
| 6 | launder/弃权洗 C4 | 已知亏本（54.3），本轮未重测 | 维持五审结论 |
| 7 | C5 面（多命名不罚） | honest 31/31 无头部空间 | 无利可图 |
| 8 | **外来 1px 产物**（见 Finding 1） | C4 洗到 0，被 runs_match 独力拦下 | 门承重，见下 |

### Finding 1（⭐⭐⭐，实测，答 Q1(b)）：`runs_match_the_strip` 整数精确=外来观测层的硬墙，且这堵墙**是承重的**——契约必须先落字

夹具 `out/sm25_1f_GLM_foreign_1px.json`：诚实 1F 产物、每条 run 端点削 1 px（≈5.9 mm，
模拟一个抗锯齿阈值略严的外来提取器；runs_m 按生产者仿射重算，仿射复现误差 worst **0.00006 m**）：

```bash
python3 .../tools/checks_as_drawn_v2.py .../out/sm25_1f_GLM_foreign_1px.json .../tools/cfg_1f_full.json ...
python3 .../tools/reading_grade.py   .../out/sm25_1f_GLM_foreign_1px.json .../out/denominator_sm25_F1.json ...
```

| | 十门 | runs_match | C1 | C2 | C4 | C5 |
|---|---|---|---:|---:|---:|---:|
| 诚实 | 11 绿 | 绿 | 100.0 | 98.6 | 0.722 | 100 |
| foreign_1px（削 134 处端点） | **10 绿** | **红 49/49** | 93.6 | 98.1 | **0.0** | 100 |

两个读数：
1. **过严属实**：一份与参考提取器只差 1 px（5.9 mm，一切在用容差之内）的合理外来读数，49 条面线全红、
   其余十门全绿。`truth` 表还按 `(axis, c0, c1)` **逐整数**键匹配——外来产物哪怕 runs 全对、
   support_cols 取整方式不同也红。**当前形态下没有任何外来观测层能通过它。**
2. **但这堵墙不能松**：削尾家族是当前利润最高的作弊——foreign_1px 把 C4 0.722→0 且十门全绿；
   `skip_unscored_tails`（聪明版，只削不计分尾）C1 100/C2 98.6/**C4 0.215**，
   现在**只**被这道门拦（2F 上只被它一道拦），而 2F 版每端只削 **1–2 px**——
   任何 ≥1 px 的容差都直接放行。**门必须保持整数精确。**

⇒ 结论不是改门，是**把后果写进层契约**（Q3 条件 4）：observations（runs_px / support_cols_px）
只能由参考提取器机器产出；外来/模型输入只限 perception 字段（族角色、配对、分桶、逐洞口命名）。
这条必须在冷启读图器（前置组 #5）设计**之前**落字，否则冷启读图器要么对着一个不可能的及格线、
要么门在压力下被放松。

### Finding 2（⭐⭐，实测）：永久矩阵在 HEAD 上对五审夹具「静默吃陈旧产物」——页面上有两个旗舰作弊显示为全绿

```bash
cd <repo根> && python3 .../tools/glm_rework.py
# → AssertionError: width rule source drifted (glm_rework.py:403, 经 sweep_coefficient → line 499)
# out/glm_rework.json 的 mtime 停在 19:51:17 —— WIDTH_COEFF 改动之前，本轮重跑未重写它
```

- 断言是我五审写的漂移守卫，**它正确地开火了**（reading_grade 的 0.5→WIDTH_COEFF 使源码锚失效）；
  但处置是把断在请求书里预告给我，而不是修矩阵。
- `run_all.py:254-257` 对 glm_rework **不看 rc**（对照：glm_cheats 分支检查 `rc == 0`），
  只要旧文件存在就打包 ⇒ `RESULTS_v2.json` 的 glm_rework 段 = **陈旧快照**，
  其中 band_collapse / fabricated_profile 是**修前九门全绿**的状态。
- 后果：README §三之四「band_collapse ⇒ 红」在矩阵层面无凭据；任何今天读 RESULTS_v2 的人
  会看到五审两个旗舰作弊**全绿**。「十一门每道真红过真绿过」的机器统计本轮仍成立
  （经 glm_cheats 四夹具真跑），但五审夹具那份是旧账。
- 同类前科你们自己记过两条：显示错误照样是页面上的一个错数；退出码/陈旧产物被当本轮结果。
  门是好的（我已独立复验，见上表），坏的是矩阵这层皮。修法机械：适配断言（改锚 WIDTH_COEFF
  或读常量）+ run_all 对 glm_rework 检查 rc + 产物文件必须本轮重写才许打包。

### Finding 3（⭐⭐，实测）：`drawing_box_px` 与 `calibration` 是「产物自报、零门重算」的承重孔径——今天不赚钱，但正是五审根因的同款

实测（结构族墨 vs 自报画框）：

| | 结构族总墨 | 框外 | 占比 | 框边切墨 |
|---|---:|---:|---:|---:|
| sm25 1F | 36,608 px | **15,167 px** | **41.43%** | 48 px |
| sm25 2F | 35,805 px | 14,517 px | 40.54% | 24 px |
| sm24 | 36,258 px | 7,575 px | 20.89% | 11 px |

也就是说：**画框是「本图 vs 同图纸其余内容」的分离孔径，诚实产物自己就靠它丢弃四成结构族墨**；
而两道新门 + forward + reverse 全部**按产物自报的框**裁剪后再重算，没有任何门从原图重导框或标定。
今天它不赚钱（攻击面 #4/#5 实测：target 包络钉死了框的可用范围）；但它与五审根因
「所有自洽门都锚在产物自选的观测孔径上」同构——观测层一旦从别处来（恰恰是本批的下一层），
自选框+自选标定就是敞开的。处置写进 Q3 条件 4：要么由门重算（镜像生产者定义），
要么在层契约里声明为已知盲区并记上面这组数字。

### Q1(a) 的答案：镜像**完备**（对它所测的量）；FILL_RATIO 不在缺口上

逐行比对过 `_ink_groups`（as_drawn_v2.py:161-212）与 `check_support_strip_is_one_stroke`：

- FILL_RATIO（`along = keep[:,g].mean(1) >= 0.5`，:184）作用于**沿轴 run 提取**，不进
  **列组**定义（列组 = keep→support≥min_support→gap>1px，门逐条镜像，含同一个
  `vertical_runs_mask`）。沿轴那一步由 `runs_match_the_strip` 镜像——它直接调 `_ink_groups`。
- 生产者 `if not runs: continue`（:186）会**丢掉**无 run 的列组，门不丢 ⇒ 门只会**更严**，
  不会更松。方向安全。
- 实测分辨力（本轮复跑）：诚实 1F{1:49}/2F{1:46}/sm24{1:98} vs 塌缩带 10/10、11/11 全 2。
- 两个小注（不承重）：① 门把 `min_run_px=14/min_support=10` **硬编码**为默认参，
  而生产者/runs_match 读 cfg——今天三份 cfg 都不覆盖这两键（已核），等价；未来某 cfg 覆盖即静默分叉，
  建议顺手改成读同一 cfg。② 两条墨线间隔 ≤1 px 时生产者自己就并组（gap≤1 join），
  门与生产者一致、非作弊差分；当前方言两线相距 ~34 px，不构成面。

---

## Q2：四处改动有没有「迎合被测对象」——没有

判据沿用：(a) 答案本源 (b) 迎合检测（是否以被测产物/分数为输入）(c) 完备性代价。

| 改动 | (a) 输入 | (b) 分数输入 | 裁定 |
|---|---|---|---|
| `support_strip_is_one_stroke` | 原图 + 产物声明条 | 无 | **纠正尺子**。镜像生产者自身定义（同 [[recompute-gate-must-mirror-producer-definition]]），分辨力经我独立复验 |
| `WIDTH_COEFF` 0.5→1.0 | 我的扫描表 + 诚实 sm24 下界 1.146 | 无（扫描输入=夹具与诚实产物，非答案） | **纠正尺子（收紧向）**。诚实三案成绩分毫未动（100.0/98.1/95.7），partial 家族被杀。⚠️ watch：对诚实下界只有 **1.15×** 余量——未来若有比间距更窄的诚实带方言，第二面作答会假阴（覆盖风险，非完整性风险） |
| 重算扩到 `opening_candidates` | 原图（同源同函数） | 无 | **纠正尺子**。fabricated_profile 实测红 |
| `runs_match_the_strip` | 原图 + **cfg**（参数不来自产物） | 无 | **纠正尺子**。其精确性是承重的（Finding 1），不是过设计 |

**四处没有一处以被测对象的分数为输入，不构成迎合。** 你们自己最担心的两处
（镜像不严 / 过严）实测分别是「完备」与「过严但承重、须以契约承接而非放松」。

---

## Q3：够不够格开始动 gt？——**够，APPROVE**；四条成绩闸随层落库

五审的顾虑（把可被骗的尺子冻结进答案）本轮被实测解除：观测层的表示法塌缩家族
（band/两线塌缩/削尾/伪造 profile）每条都有门独力拦下，且我用八个新攻击面没能翻掉。
denominator/层内容自五审以来未被任何发现污染。**可以开始书写。**

随层落库的硬条件（⛔ 违反任一条 ⇒ 该层产物**不得记成绩、不得在文档引用分数**；前三条不阻塞书写）：

1. **`span_min` 签字**（沿用五审：C1 是带阈值判定、C2 才是主读数）。附一个本轮实测供签字参考：
   诚实 1F 有 **7 个目标覆盖恰在 0.841**（0.72 m 残段 ×3 组），span_min=0.80 离诚实值只有 0.04 的余量——
   签字时值得知道这个悬崖在哪。
2. **冷启隔离读图器首考**（不阻塞书写、阻塞记成绩；落库后第一件事）。
3. **修复永久矩阵**（Finding 2）：glm_rework.py 断言适配至 HEAD 可跑通 + run_all 对 glm_rework
   检查 rc + 陈旧产物不得打包。验收 = `run_all.py` 一条命令后 `RESULTS_v2.glm_rework` 里
   band_collapse/fabricated_profile 显示**今天的、带新门的**状态（红）。
4. **层契约落字**（Finding 1 + Finding 3）：
   - observations（runs_px/support_cols_px）**只能由参考提取器机器产出**；外来/模型输入只限
     perception 字段。`runs_match_the_strip` 保持整数精确，任何「为外来产物放宽容差」的改动
     都必须先证不放过 1px 削尾（2F 夹具就是验收）。
   - `drawing_box_px` 与 `calibration`：要么加门从原图重导（镜像生产者定义），要么在契约里
     **声明为已知盲区**并记入「框外结构墨 41.43%/40.54%/20.89%」这组数。

---

## 本轮文件改动（全部新增，`glm_` 前缀；未改任何送审方源文件）

- 夹具产物：`out/sm25_1f_GLM_foreign_1px.json`（1px 外来产物）、`out/sm25_1f_GLM_freebridge.json`、
  `out/sm25_1f_GLM_allbridge.json`（命名面攻击）
- 判分/门输出：`out/sm25_1f_GLM_foreign_1px_checks.json`、`out/grade_sm25_1f_GLM_foreign_1px.json`、
  `out/sm25_GLM_{honest,freebridge,allbridge}_gt.json`
- 另：按请求书重跑 `run_all.py` 改写了 `out/RESULTS_v2.json`、`out/glm_cheats.json` 等既有产物
  （`out/glm_rework.json` **未被重写**——它正是 Finding 2 的证物，保持 19:51 原样）；
  五审夹具的复验输出落在 `/tmp`（不入仓库）。
- 裁决文件：本文件。

## 实测与推断的边界

- **实测**：本文所有表格数字（复验基线、三处修独立复验、八个攻击面、框外墨占比、
  断言栈与文件 mtime、直方图、诚实覆盖悬崖 0.841×7）均由所列命令在 `4b3877d` 工作树产出。
- **推断**（已标注）：(1) 「≥1px 容差会放行 2F 削尾」由「2F 版削 1–2px/端」+ 门的逐整数比较推出，
  未逐容差值实测；(2) 「未来更窄诚实带方言会触 WIDTH_COEFF 假阴」是余量推算；
  (3) 冷启读图器对 runs_match 不可能及格——由门的逐整数匹配推出，未跑（要花钱，归 #5）。
