# 行动清单（活计划）

> **职责**：只放**还没做完的事**和**当前一轮的日更**。**体量纪律 = [CLAUDE.md §0.5](CLAUDE.md)（唯一权威）**：
> ⛔ 不放历史叙述——做完的、翻篇的一律搬 [`logs/worklog/`](logs/worklog/)（见文末 §归档）；
> **本文 >900 行 或 出现上一轮日更 ⇒ 收工时当场搬**（§5#12 第 ② 步）。
> 当前状态看 [CLAUDE.md §2](CLAUDE.md) · 历史决策看 [decision_log.md](decision_log.md) ·
> 架构看 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) ·
> 标准工作流看 [guides/new_case_guide.md](guides/new_case_guide.md)。

---

## 当前焦点（2026-08-19）

> **唯一第一目标（用户 08-18 重申）= 恢复到 07-07 的 reading 水平。⛔ 不要再大量做无关紧要的东西。**
> 判断法则见 [CLAUDE.md §0.1](CLAUDE.md)：不做这件事，下一次跑测能不能跑起来、结果能不能读？能 ⇒ 登记，不做。

**卡在哪**：07-07/07-08 三次「满分级」reading 的工作方式，**22 抽没能再现**。
环境侧已还原到头（源头树 `723b0f9` / 07-07 文档与工具箱 / directive 经 git 证明是全文 / pilot 门 / gate① / 返工照记录原样），
**行为不回来**；指纹稳定 = **收到具体指令 → 产出「像是照做了」的东西 → 那件事没做**。

- **⭐ 全案报告（写给外部排查席，一份读完全案）** =
  [`logs/reviews/request/2026-08-18_reading_regression_external_investigation.md`](logs/reviews/request/2026-08-18_reading_regression_external_investigation.md)
- 逐抽过程档 = [`logs/experiments/2026-08-15_reading_restart/`](logs/experiments/2026-08-15_reading_restart/README.md)
  · [`2026-08-16_707_repro/behavioral_change_inventory.md`](logs/experiments/2026-08-16_707_repro/behavioral_change_inventory.md)
  · `case_tests/e2e_tests/sm21_anchor/run_2026-08-1*/`
- 回归门 = `scripts/tool_scripts/reading_regression.py`（08-18 新建；此前全仓**零门**在问「reading 还行不行」）

**下一步（⏸ 待用户拍板）**：orchestrator 建议**停止找病因，改建「让它做不到」**——
读图器只写像素锚点 + 证据引用，**换算由代码唯一执行** ⇒ 眼估米坐标写不进去。
直接证据 = J5「它算得出正确的 `px_per_m`(59.733)，只是不用来落笔」。

**⛔ 明确不做**：再动 guard 围栏（已称重、不再是瓶颈）· 补围栏 / 补审 / 补锁 / 补文档完备性。

**新瓶颈假说**：筛选纪律（候选 → 笔画那一步）。07-07 产物里有完整的拒绝台账（44 条）可作参照。

---

## 未闭合缺陷登记（reading 主线相关）

| 编号 | 内容 | 状态 |
|---|---|---|
| F-62 | guard 对多行命令 `shlex.split` ⇒ heredoc 正文、反斜杠续行被当命令参数 | **未修** |
| N-1 / N-2 | guard 双通道词表不一致（`grade line` 误伤）/ 一个笔记文件毒死全部脚本执行 | **未修** |
| F-63 | 跨轴门抓不住「两次单轴标定各自自洽、彼此矛盾」（`src/validator/checks/reading.py:1644-1690`）| 登记不做，排在 707 恢复之后 |
| F-64 | gate① 对「零产出」是瞎的 ⇒ **交白卷比交错卷更容易过门** | 登记 |
| — | v3 typed 判卷对 null `scale_origin` 判 `retain_as_miss` ⇒ 整条 plan 通道按 miss 计 | ⚠️ **跑 sm24 前必须先解**；只跑 sm21 走 legacy 判卷、零影响 |
| — | 全链无门校验「note 里的换算式 ↔ 笔画坐标」一致性 | ⭐ 确定性可查、成本低 |
| — | gpt-5.4-mini 判别臂未跑（`codex exec --dangerously-bypass…` 被权限层拦）| 正规替代 = codex MCP |

**复审债（保留档，仍须换人审）**：甲-5（`reading.calibration_axes_agree` + `merge_isolated_output` 接线 + 动了 `disposition()`）
· 丙-1 / 丙-2（sol 老批里碰契约与判定的几项）。其余 8 笔按 [CLAUDE.md §0.2](CLAUDE.md) 探索档销账。

---

## 本轮日志（2026-08-19）

## 2026-08-19 · ⭐⭐⭐ **三臂判别跑完 · 病灶定位到「肯不肯把看放到放大镜后面」· 根治与 Haiku 回归打包归专项**

**用户 08-19 收口口径**：「根治打包收进 reading 专项。现在就是在最新基座上确认移植好，
**两项验收：GPT-5.4-mini 和 Sonnet 在 sm21、sm24 上都出好 reading**。后面怎么让这套机制变成强制、
让 haiku 水平回归，都收进 reading 专项。」+「先不考虑降低图片分辨率来降成本，**直接读原图**。」
⇒ 三包已收进 [`capability/reading/improvement_methodology.md §9`](capability/reading/improvement_methodology.md)。

### 一、三臂结果（全 1f 单图 · 探索档 n=1 · ⛔ 不得记成成绩）

| 臂 | 树 / staging | 模型 | 墙 | 窗 | `crop_zoom` | 标定误差 | 锚点形态 |
|---|---|---|---|---|---|---|---|
| **P1** | 历史树 `ebddada` | gpt-5.4-mini | r1 2/4 → **r2 4/4** | 3/3 | 3 | **0.016%** | 425/1816 整数 |
| **Q1** | 历史树 `723b0f9` | haiku-4-5 | r1 1/4 → **r2 1/4** | 0/3 | 0→3 | 35% | 270/1170 整数 |
| **Q2** | 同上 + F-51 帧修正 | haiku-4-5 | **0/4** | 0/3 | **0** | **6.4%** | 280/1235 整数 |
| **R1** | Q2 那份 staging **逐字节** | **claude-sonnet-5** | **4/4（首抽零返工）** | **3/3** | **16** | **0.15%** | **273.56/1172.48 亚像素** |
| （参照）07-07 | `723b0f9` | haiku-4-5 | 4/4（一轮返工） | 3/3 | **17** | 0.016% | **425.4/1815.9 亚像素** |

### 二、⭐⭐⭐ 病灶（实测定位，非推理）

**不是「Haiku 不用代码去量」——它调了工具**（Q1: profiler ×2 + calibrator ×4）。
缺口窄得多：**`px_m_calibrator` 收自由数字**，眼估的像素进去、出来一份带 `confidence: high` 的「测量结果」。

**07-07 的机制被证据改写**：它最终锚 `425.4/1815.9` 是**亚像素**，17 次 `crop_zoom` 是 2×–8×
⇒ **不是「让代码去量」，是「放大 8 倍再用眼睛看，然后除以 8」**。Sonnet 今天同形复现（亚像素锚 + 16 次 crop）。

**感知探针（合成图·帧无关·两次重复稳定）**：Haiku 按图宽比例报四条线位置，最大偏差 **26 个百分点**。
⇒ 眼估准不了。⇒ **杠杆 = 肯不肯把「看」放到放大镜后面**，而非工具可用性 / 指令 / 帧。

### 三、⛔ 本轮两处被自己证伪的判断（都要记）

1. **「provenance 标注可当目测的判据」——错。** GPT 满分那份 17 条墙全 `seen`、引用 0/17。已收回。
2. **「Haiku 今天不会回头改自己写下的几何」——错。** 纯算术探针：告知「参照长度是 12.0 不是 15.0」
   ⇒ 一次改对（80→100，五个值全部重算正确）。⇒ 分界不在「肯不肯改」，
   在**修正给的是「具体替代事实」还是「方法」**——给方法它得重新去感知，那一步才塌。

### 四、本轮落地的脚手架改动（作者 = orchestrator，⛔ 零复审，进复审债）

- **`--vision-resize-tier {none,standard,high_res}`** 补上入口（此前**无任何入口**，08-17 复审记的 MINOR）；
  `prepare-single-plan` 一并透传。
- **默认改 `none` = 读原图**（用户拍板）。3 把 F-51 旧锁**改为显式钉 `standard`**（测的是机制，
  同 08-18 处理 `guard_profile` 的做法），**另加 2 把**钉住「默认 = 原图逐字节不动」+「显式要 standard 时仍真缩」。
- 行为验证：`standard → 1377×868` / `high_res → 2133×1345` / `none → 原图`，实跑确认非仅参数解析。

### 五、⛔ 隔离边界（用户 08-19 裁定，第 4 次适用同一条）

P1 那臂 orchestrator **先判卷后写返工** ⇒ 违反不变量 #7。用户裁定「信息没泄漏、只是物理上没隔离，
不阻塞，统一归 reading 专项」。**Q1 / R1 两臂已改为先写返工/裁定并封存哈希、再判卷**
（Q1 `3adb2355268bce46` · R1 `42764e8ab20cdf9e`）⇒ **这两臂从头到尾可审计**。
R1 那份封存裁定写的是 APPROVE，判卷结果 4/4·3/3 —— **只看产物就预测对了分数**。

### 六、⭐ reading 相关改动全表分流（用户 08-19：「该保留的保留、该纳入专项的纳入专项、该清理掉的清理掉」）

**盘面**：`ebddada`（最后一份好 reading）→ HEAD 共 **22 笔提交**碰过 reading，
读图器**真正读得到**的五份文档变动 = `session_kickoff +57/-17` · `guide +49/-7` ·
`cv_toolbox +77/-14` · `reading_guide +38/-0` · `pen_library +7/-0`；隔离壳 **+3298 行**。

| 项 | 归属 | 依据 |
|---|---|---|
| 物理 staging + gt 硬排除 + 审计兄弟目录（L1/L3） | ✅ **保留** | 净收益；07-08 那次 9/9 本就跑在 staging 里；08-19 实测 sm21/sm24 gt 均不在内 |
| pilot 停等门（08-17 恢复）+ 外部审批状态机（N2） | ✅ **保留** | 07-07/07-08 形态的机器化；08-19 三臂全部依赖它 |
| A1 同会话续跑 `--resume`（08-18） | ✅ **保留** | 是「07-07 模式」的定义组成；⛔ 但已证不是杠杆 |
| 实验 spec / `reader_invocations` 溯源（N3/N3b） | ✅ **保留** | 本轮全部可审计性的来源 |
| 中性 worked example（N1） | ✅ **保留** | 替掉「读别的 case 历史 reading」 |
| `reading_regression.py` 回归门（08-18） | ✅ **保留** | 此前全仓零门在问「reading 还行不行」 |
| 「先标定再写坐标」纪律（`15cfcb8`） | ✅ **保留** | 正是杠杆本身 |
| `local_x_positive` 文档自相矛盾（D1） | ✅ **已修**，划掉 | 08-19 复查：§4/§6 现已一致 |
| **`guard.py` 词法围栏**（L4，1528 行） | → **[硬隔离专项](proposals/hard_isolation_direction.md)** | 六条同族假阳性；`observe` 档下已不阻塞；**未清点有多少是 strict 档死代码** |
| F-62 / N-1 / N-2 / BLOCKER-1 / BLOCKER-2 / F-59 | → **硬隔离专项** | 全部在 `observe` 下影响归零 |
| wrapper 强制形态（A2）与非 Claude 读图器的隔离不对称 | → **硬隔离专项** | codex 不过 guard；两臂隔离强度不同，成绩口径要不要分标 |
| **`scale_origin` 必填 → SHOULD** | → **[标定出模专项](proposals/dimension_basis_and_wall_thickness_direction.md)** | 判「内角」必须判墙厚 = 该专项未定案的题；世界原点该由谁定也在那边 |
| 跨轴 RAISE → 合法出口 → rc=0 退化；F-63；F-34 | → **[reading 专项 §9.1](capability/reading/improvement_methodology.md)** | 修法 = 锚点只收 `candidate_id` + 两轴一次给全 |
| F-51 图像帧 / 分辨率取舍 | → **reading 专项 §9.3** | 默认已改「读原图」；Haiku 一代帧错位仍在 |
| gate① 对零产出瞎（F-64） | → **reading 专项** | 交白卷比交错卷更容易过门 |
| **prescan 半死状态** | → **reading 专项** | 实现在、授权撤了 ⇒ 读图器调不到。**2026-08-19 已从工作环境撤出并完整留档**（[`prescan_snapshot/`](capability/reading/prescan_snapshot/RESTORE.md)，与 `0cfa289` 逐字节相同）。⛔ **撤出 ≠ 放弃**；去留与 §9.1 根治修法**合并决策**（预扫的 234 个 `tick_candidate` 正是那条修法要的机器 tick 来源）|
| `reading_guide.md` +38 行（虚线/隐藏窗/非矩形/翼部） | ✅ 保留（不清理） | sm21/sm24 用不到，但 **C2 复杂建筑要用**；属能力线不属噪声 |
| v3 判卷 null `scale_origin` ⇒ `retain_as_miss` | ⛔ **必须先解** | **sm24 验收准入门**；碰判卷 = 工程档、作者不得是 orchestrator |

**⇒ 真正动了的只有 prescan 一项：从工作环境撤出、代码与方案完整留档、去留归专项。** 其余要么保留、要么已归专项。

### 七、⛔ orchestrator 本轮实犯：删 prescan 时删掉了 kickoff，而我的验证被「文件不存在」骗过去了

**做了什么**：用正则删 `_write_kickoff` 里那段介绍预扫候选的文字，正则吃到了**下一行**
—— `_write_generated(staging_root / "kickoff_prompt.md", ...)` 整句被删 ⇒ **staging 从此不再生成 kickoff**。

**⭐ 为什么当场没发现（这才是要记的）**：我跑的验证是
`grep -c prescan /tmp/prescandel/kickoff_prompt.md || echo "kickoff 零提及 prescan"`
—— 文件**不存在**时 `grep` 报错，`||` 落到 echo，于是打印「零提及」。
**我把「文件没了」读成了「检查通过」。**

⇒ 同族 [[absence-conflates-causes-in-observables]]：**缺席不是信号，除非显式变成信号。**
⇒ 判据修法：**先断言文件存在，再断言其内容** —— `test -f X && grep -c ... X`，
⛔ 不许用 `grep ... || echo 通过` 这种把「读不到」和「读到且干净」压成同一分支的写法。

**抓住它的是既有的锁**（`test_no_pilot_gate_kickoff_states_an_explicit_override` 报 `FileNotFoundError`）
—— 本轮第 N 次由测试锁抓住 orchestrator 手滑，与 §0.3「这类锁便宜、不该一刀切减」同向。

**已修**：`_write_generated(kickoff)` 补回；重新实建 staging，**先验文件存在**、再验内容完整且零 prescan。

### 八、prescan 删除的清尾：四把锁全部在干正事（其中一把抓出真死代码）

| 红掉的锁 | 抓到什么 | 处理 |
|---|---|---|
| `test_isolation::test_direct_param_allowlist_matches_cv_probe_options` | ⭐ **guard 的 `PROBE_DIRECT_PARAM_KEYS` 里留了 5 个 prescan 专属死键**（`capability_profile`/`no_cc`/`min_strength`/`min_line_len_px`/`label`）——我先前只清注释没清这张表 | 清掉；重新对账 cv_probe 现存 21 选项 ⇒ **死键 0 / 缺键 0** |
| `test_substrate_sweep_policy::test_g8_dead_keys_and_no_missing_keys` | 同一处，另一角度 | 同上 |
| `test_substrate_fix_tools::f52_neuter…` | ⭐ **neuter 退化成「红得不是原因」**：冻结夹具因 prescan 已删而崩在 `ImportError`，不再复现它该复现的 argparse 崩溃 | 只剥掉夹具里**附带的** prescan import/子命令（被测的 bbox 解析器逐字节未动），docstring 记明为何动它 |
| `test_gt_discipline::test_prescan_entry_points_stay_gt_blind` | 它断言 prescan 入口**存在**；主体已删 ⇒ 断言存在就是钉错东西 | 改写为**哨兵锁**（prescan 保持删除，除非专项另有决定）|

#### ⛔ 我改哨兵锁时又犯了本仓的老毛病

第一版哨兵写成 **grep 源码找 `prescan_plan`**，结果**被我自己那句「记述删除」的 docstring 绊倒**
—— 与 F-49 → F-60 → N-1/N-2 → F-61 → F-62 六条同族缺陷**同一形状：用词法匹配判无界文本**。

**已改成行为断言**：① `cv_toolbox` 模块无 `prescan_plan`/`prescan_elevation` 属性
② `cv_probe.build_parser()` 的子命令集合无 prescan ③ `run_cv_probe.ALLOWED_TOOLS` 无 prescan。
**neuter 验证**：把 `prescan-plan` 放回授权表 ⇒ 锁变红 ⇒ **真绑，非假锁**。

⇒ **新判据：给「某东西已删除」写哨兵时，断言要【问代码】不要【问字符】**
（`hasattr` / parser choices / 授权表），⛔ 不用 grep 源码——记述删除这件事本身就会把词法锁绊倒。
同族 [[lexical-guard-cannot-be-completed]]。

### 九、下一步 = 两项验收（⏸ 待排）

**在最新基座上**，`gpt-5.4-mini` 与 `claude-sonnet-5` × `sm21` + `sm24` 各出好 reading。
⚠️ **sm24 开跑前必须先解 v3 判卷对 null `scale_origin` 的 `retain_as_miss`**
（详 [专项 §9.4](capability/reading/improvement_methodology.md)，作者不得是 orchestrator）。
⚠️ GPT 侧额度 2026-08-20 07:29 恢复。

---

## 2026-08-19（早些时候）· GPT 判别臂第一格：历史栈今天仍能出满分 reading（一轮返工，4/4 · 3/3）

**全档** `/workspaces/ep_708_tree/case_tests/e2e_tests/sm21_anchor/run_2026-08-19_gpt54mini_historystack_P1/`
（含 r1/r2 产物 · CV 侧车 · 两份判卷侧车 · 两份 transcript · 返工原文 · PROVENANCE.json）。
⛔ 探索档 n=1 ⇒ **不得记成成绩**。

### 一、结果

| | 1f 墙 | 1f 窗 | 备注 |
|---|---|---|---|
| r1 pilot（返工前） | 2/4 | 3/3 | 两道走廊墙完全缺失 |
| **r2（一轮纯过程返工后）** | **4/4** | **3/3** | max_offset 0.07 m |
| 07-08 那次的**终态**（同模型同树） | 4/4 | 2/3 | **今天的 r2 反而好一格** |
| N4（Haiku · **当前栈**） | 0/4 | 0/3 | 对照 |

**标定**：r2 补调 `px_m_calibrator` ⇒ `92.7093 px/m`（真值 92.6945，**偏差 0.016%**），
残差 0.36 px，`confidence: high`。锚点 **px 425 → 1816**；
⭐ **07-07 Haiku 拿满分那次的锚点是 425.4 / 1815.9 —— 同一组图元**。
对照 Haiku 在当前栈上那抽：锚点落在**绿色标注层最外沿**（87→1258）⇒ 78 px/m，错 30%。

### 二、⭐ 这一抽排掉了什么 / ⛔ 没排掉什么

**排掉**：模型服务端整体退化 · 图纸 · CV 工具 · 判卷尺 · 容器/网络环境 ·
**配方本身**（含「一次返工」这个组件，今天仍然有效）。**历史栈是活的。**

**⛔ 没证明「就是 Haiku」**：本抽跑历史树、N4 跑当前栈 = **两个变量**。
2×2 还缺 **GPT × 当前栈**（单变量，脚手架已就位）⇒ 下一格。

### 三、两条反直觉的（与成绩一并说）

1. **满分那份产物，17 条墙全 `provenance: "seen"`、证据引用 0/17**，返工点了这条它也没照做
   ⇒ **provenance 标注不具分辨力**，⛔ 不得再拿它当「目测」的判据（orchestrator 08-19 早些时候用过，已收回）。
2. **`self_check` 照样说谎**：r1 声明 `all_visible_strokes_captured=true`，而它自己的 `uncaptured`
   点名了那两道没画的走廊墙 ⇒ **自检不可靠不是 Haiku 的毛病，是共性**，与换不换模型无关。

### 四、⛔ 隔离边界（用户 08-19 当面裁定）

返工文本**干净**（纯过程 + 自相矛盾对账，零坐标 / 零 gt 值 / 零「少了几道墙」，全文 `_run/feedback_r1.md`），
**但 orchestrator 在写返工之前已用 gt 判过 r1** ⇒ 严格说违反不变量 #7。
**用户裁定：信息没泄漏、只是物理上没隔离 ⇒ 不阻塞本抽；该类问题统一归 reading 专项。
⛔ 不得再把它当拍板项反复上报。**
⇒ 本抽记作**受控/有监督**结果，⛔ 不得宣称「模型自己做到的」；与对照组口径一致（07-08 / Haiku 各抽同为 orchestrator 审 pilot）。

### 五、⛔ 新缺陷 · `codex exec resume` 不继承 `-m`

一次 resume 未带 `-m`，CLI **静默落回 `gpt-5.6-sol`**（旗舰档）。session header 当场查出并杀掉；
rollout jsonl 证明该窗口内 **`response_item` 计数 = 0**、产物 md5 与归档 r1 逐位相同 ⇒ 零污染。
⚠️ 本仓此前只记了「resume 不继承 sandbox」。**任何 codex 调用必须显式带 `-m`，且开跑后核 session header。**
⇒ 同族 [[verify-the-path-works-before-blaming-the-model]]：工具坏掉与模型行为在产物上同形，只有过程日志分得开。

### 六、下一步（⏸ 待拍）

跑 **GPT × 当前栈**（2×2 最后一格，单变量）：崩 ⇒ 是这套东西坏了；照样好 ⇒ 才轮到「就是 Haiku」。
⭐ 建议改执行顺序为**先写返工存档、后判卷**，让那一抽从头到尾可审计（免费，纯顺序问题）。

---

## 中期（粗）—— 能力升级（原 B5–B7）

按 **[capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md)** 的 C 阶梯推进（内核先行 + 守卫同步）：
- **C2 正交多边形 + 多平面立面**（含 shapely 覆盖完整性门提前落地）
- **C3 退台 / 挑空**（墙配对 by_floor → z 区间重叠驱动、切配扩到切墙）
- **C4 斜交墙**

并行支线：识图→建模质量主线见 [capability/recognition_modeling_capability.md](capability/recognition_modeling_capability.md)；再拓扑 leg（休眠）见 [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md)。

---

## 远期 —— 开源模型 + Pivot（原 B8–B9）

- 部署 vLLM + Qwen2.5-VL / DeepSeek-VL；切 [llm.yaml](../src/configs/llm.yaml) `intake` section（A2 已就绪）；跑同一套评测横向对比。
- LoRA SFT（phase1=(图,矢量JSON) VLM / phase2=(矢量JSON,IntakeOutput) 纯文本，两数据流独立），holdout ≥ Opus 80% 后切默认 provider。
- 双阈值见 [reference/pivot_criteria.md](reference/pivot_criteria.md)。

---

## 分出去的独立模块（指针）

| 模块 | 文档 | 状态 |
|---|---|---|
| CAD→gt 满配答案 / CAD 输入模态种子 | [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md) | 设计待审，工具链就位 |
| reading 提升（诊断+Phase A/B/C+CV 工具箱方法论）| [capability/reading/improvement_methodology.md](capability/reading/improvement_methodology.md) | **已动工**（Phase A ✅ 落地）→ 统一管理文档；原 proposal 已折入并删（2026-07-03）|
| 0–3 复杂度升级路径（C2/C3/C4）| [capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md) | 骨架已立，随中期推进 |
| 再拓扑 leg（热区积木 zonification）| [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) | 强力支线·休眠·**Fable5 B3(07-06)已更新启动条件**（绑 C2 开工·stage 1.5·`method` run_config·比原设想更易落地，见其 §9）|
| 可编辑几何确认环节 | [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md) | DEFERRED，先讨论 |

---

## 搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）：等协作者侧 MCP 全线重写交付。
- **token 优化**（[deferred/token_optimization.md](deferred/token_optimization.md)）：等 idfpy 切换后大量 CRUD 工具消失再评估。
- **fenestration/construction SimpleGlazing 兼容性 prompt 修**：等 idfpy schema 原生覆盖（当前几何优先，不动 prompt）。
- **Sonnet 4.6 降级测试**（本环境够不到，需用户独立会话；**Haiku 4.5 降级测试已跑 ✅ 2026-07-05，见 N2b ③**）；**OpenStudio 几何验收**（用户人工，不卡代码）。

---

## 已完成（一行汇总，详见 [decision_log.md](decision_log.md)）

A 代码跑通 ✅ · B1 旧 skill 迁移恢复 ✅ · 两步法 POC + 切主线 + InterZone 门 + 正式指南 ✅ · 0–5 阶段重构（几何确定性化）✅ · EP 跑通 + schedule 门 ✅ · 完整体检 4H/3M/3L 全修 ✅ · 仓库整理 + 标准 case 布局 ✅ · 0–5 校验架构 M0–M4 ✅ · 新 baseline 方案 + 主 Agent 操作手册 + gt ✅ · 逐段 judge 编排 + 离线 3D 查看器 ✅ · CAD→gt 工具链 + gt 渲染 ✅

---

## 归档（过程痕迹，⛔ 非活文档）

| 归档 | 内容 |
|---|---|
| [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md) | plan 日更 2026-08-01 → 08-18（reading 重启七抽 · 基座普查 · 验收 3/3 · 下游断链 · F-22 批）|
| [`logs/worklog/2026-07_plan_log.md`](logs/worklog/2026-07_plan_log.md) | plan 日更 2026-07-31 + 原「当前焦点」章节正文（sm24 端到端 / 判卷器身份与度量批）|
| [`logs/worklog/2026-06_backlog_closed.md`](logs/worklog/2026-06_backlog_closed.md) | 原「近期（细）」整节（2026-06 批次，绝大多数已 ✅）|
| [`decision_log.md`](decision_log.md) | 里程碑与决策详档（历史决策的唯一归档）|
