---
name: reading-quality-lever-is-crop-budget-not-review-ring
description: 2026-08-16 转向读 diff⇒行为性改动清单已出；头号候选=pilot 停等审阅门被拆（唯一「两份弱模型成功里都在、今天没有」）+ scale_origin 成为必填；⛔ 模型漂移说从根上不成立
metadata: 
  node_type: memory
  type: project
  originSessionId: 9ed0fafd-2cdb-49a8-a106-a2b9331dc492
  modified: 2026-08-18T02:07:44.596Z
---

**⛔ 标题这句主张（杠杆 = cv_toolbox 的省 crop 纪律）已于 2026-08-15 下午被实测否掉。**
文件名保留只为不断链（多处 `[[]]` 指向它）。当前正确口径见下。

## 全天六抽（sm21_anchor，全档 `AI_agent/logs/experiments/2026-08-15_reading_restart/`）

对照 = `run_2026-07-07_haiku_cv_retest`（墙 9/9 · 窗 7/7 · 最大偏移 0.0 m · crop_zoom 55）。

| | 07-07 | A1 | A2 | B1（有 review 环）| C1 | C2 |
|---|---|---|---|---|---|---|
| 墙 / 窗 | **9/9 · 7/7** | 3/9·0/7 | 1/9·1/7 | 2/9·0/7 | **0/9·2/7** | **0/9·0/7** |
| 量了几图 | 6/6 | 1/6 | 1/6 | 6/6 | 1/6 | 1/6 |
| `crop_zoom` | **55** | 0 | 0 | 0 | 2 | 1 |

## ⭐ 已实测排除的三项（别再重测）

1. **review 环 / 人工打回**（B1）：覆盖从 1/6 修到 6/6，**分数不动** ⇒ 打回改「量几张图」，
   改不了「每处量到什么粒度」。
2. **cv_toolbox.md 文档文本**（C1/C2）：把 07-07 之后新增的三条「省 crop」纪律
   （crop_zoom 降级 · *one crop per peak band, not one per segment* · 授权只标定一张图）
   **逐字回滚到 07-07 原文**，其余不变、两抽 —— **工作模式一点没变**。
3. **模型身份**：07-07 的 `llm.yaml` 写明就是 `claude-haiku-4-5-20251001`，
   **与今天同一个 ID** ⇒ 塌方不是模型换了/退化了。

⇒ **同一条判据第三次被证实**：换过 directive 强制、review 环打回、skill 常驻文本三种施加方式，
**没有一种能把工作模式从「扫一遍描述」切换成「逐候选放大量」**。
与 [[reading-quality-investigation-2026-06-24]]「prompt 强度不是杠杆」同向。

## ⭐ 第四、第五项排除（08-15 下午补）

4. **输入图纸**：`case_data/1f_view.png` 在 07-07 的 HEAD（`723b0f9`）与今天
   **sha256 逐字节相同** ⇒ 输入不是混淆项（本轮首次验，此前无人验过）。
5. **prescan 存在**（D1，已从能力层撤除并行为验证）：`crop_zoom` 0→6（历史最高）、
   总调用 10，**但仍只量 1/6 张图、墙 2/9** ⇒ **只证「不足以恢复」，⛔ 不证「无关」**。
   ⭐ 读图器**根本没去够 prescan**（日志零处），直接换了路 ⇒ 拿掉近路它会换路，**但深度换不回来**。

## ⭐⭐⭐ 第六项排除（08-16 E 组）——**能力封口 A3，且结果形状比「排除」本身值钱**

6. **A3 guard 能力封口**（E1，已撤到「A 档」= 放开 `python -c` + 自写脚本，
   **门改为执行前扫描要跑的字节**：入口脚本 + `out//requests/` 下全部 `.py` 的 import 面）：
   读图器**真的用了 4 次**新能力，**零次用于测量** ——
   三次 `python -c` 全是 `json.load` 自己刚写的输出文件打印「valid」；
   唯一那个叫 `measure_1f.py` 的脚本**坐标全硬编码**、内墙注着 `estimated from visual inspection`。
   工作模式纹丝不动（仍 1/6 图），墙 **0/9**。（n=1；管道仍拒 ⇒ 严格措辞「撤到这一档不足以恢复」。）

⇒ **⭐⭐⭐ 判据升级（本条现在最值钱的一句）**：
[[reading-cv-toolkit-methodology]] 记过「**给了工具就会去量**」是错的隐含假设。
E1 证的是**加强版**：**不是工具形态的问题 —— 把「随便写代码」这种上限最高的能力给它，行为一样不变。**
⇒ 剩下的解释不在「**能不能**」，在「**肯不肯 / 知不知道该量**」。
⇒ 凡是「加个工具/放个权限就能让它去量」的修法方向，**先想想这一条**。

**连带方法论（F-44，同样值钱）**：撤能力封口之前必须先修「日志只在**拒绝**时记原文」——
否则**放行面**（唯一能把信息带出净室的面）事后只剩哈希，
上面那张「它到底跑了什么代码」的表根本读不出来。
同族 [[absence-conflates-causes-in-observables]]：**没记录 ≠ 没发生。**

## ⭐⭐⭐ 2026-08-16 下半场：**方法换了 —— 不再猜变量，改读 diff**（全档
`AI_agent/logs/experiments/2026-08-16_707_repro/behavioral_change_inventory.md`）

**为什么七轮没查出来**：读图器真正读到的改动 `723b0f9..HEAD` 只有 **1221 增 / 46 删 / 14 文件**
（刨掉已撤的 prescan 实现剩 355/46）——**一个下午能读完**，而我们花七个多小时去猜它。
详见 [[read-the-diff-before-guessing-variables]]。

**⛔ 模型说从根上不成立（用户 08-16 澄清）**：好 reading 最先来自 **Sonnet 的一次自发行为**，
我们把它**拆解固化成 CV 工具箱**，固化后 **Haiku 做到了、gpt-5.4-mini 也做到了**
（`run_2026-07-08_gpt54mini_cv_retest` = 9/9，一直躺在仓里，orchestrator 没查、是用户提醒的）。
⇒ 工具箱的设计意图就是**消除模型变量**，而且成功了两次。
⛔ 也不存在「强模型赛道 vs 弱模型赛道」——那是 orchestrator 编的，已撤回。

**参照系 = 三份好 reading 的共同状态**（`1595981` Sonnet · `723b0f9` Haiku · `ebddada` gpt54mini）。
好窗口内脚手架 **1522 增零删**，`guide.md`/`reading_guide.md`/`pen_library.md` **三次成功期间一字未动**。

**清单（⭐ 2026-08-17 状态：#2 #3 已改完并过跨家族复审；#1 是 07-07 模式本身、开抽时按 07-07 形态跑；#4 未动）**：
1. **⭐⭐⭐ pilot 停等审阅门被拆** —— **唯一满足「两份弱模型成功里都在、今天没有」**。
   07-07 判卷记录：「pilot-r1 过度分割 19 道墙，**在 pilot review 时被抓出**」；
   07-08 溯源：**"pilot门 kept — Haiku needed one 打回"**（换模型换家族仍刻意保留）。
   今天换成了自检，而自检在本仓反复被证明不可靠。
   ⚠️ 08-15 的 B1 抽**没测到这条**（只用 directive 恢复打回、还是冷启，没恢复 kickoff 原文）。
2. ~~**`scale_origin` 成为平面图必填**~~ **✅ 08-17 已改回 SHOULD**（同图可见参考点 · 拿不准留 null）。
   ⛔ **我原先写的「两份好 reading 都没有它」是事实错 —— 两份都有**（0.0/0.0）；07-07 原注是 SW **外**角；
   `git show 723b0f9:guide.md` 零提及 ⇒ **从来不是成文规则**。这条错误陈述当时把修法引向了错方向。
   ⚠️ **留 null 不免费**：门① 记 `reading.plan_scale_origin_usable` FAIL（golden/regression 阻断），
   且 **v3 typed 判卷把该视图整条 plan 通道按 miss 计、与 `run_profile` 无关、永不报错**
   ⇒ **跑 sm24（v3）前必须先处理这条语义**，sm21（legacy）零影响。
3. ~~**`px_m_calibrator` 跨轴 >0.30% 直接 RAISE**~~ **✅ 08-17 已补合法出口**（不撤门）：
   返回可用 blend + `axis_calibration_disagreement` + `metric.confidence="low"` + `warnings[]`。
   ⚠️ **复审指出的代价**：旧 raise 经 F-54 变成 **rc=2**（agent 无法忽略），**新出口 rc=0 = 「成功」**
   ⇒ 这道门从「强制可见」退化成「寄望自觉」，且两个新字段**零机器消费者**
   ⇒ 开抽后账面上分不开「模型没量」vs「量了、被标 low confidence、仍用了那个值」。
4. ⭐ `local_x_positive` 文档自相矛盾（§4 说别填、§6 自检还要求填）—— **未动**。

**⭐ 另一件 08-17 落地的（不在原清单上，是读 diff 时撞出来的）= F-51 单帧化**：
`src/agent/execution/vision_resize.py` 按 Anthropic 官方 resize 规则在 staging 拷入时**预缩**源图，
使「读图器看到的帧 = 文件的帧 = 工具的帧」。**⛔ 它解释不了 07-07 那次回归**
（07-07 有同样的错帧、照样 9/9）⇒ ⛔ 不得当回归原因；它是**让归因可信**的前置。
详 [[vlm-pixel-frame-differs-from-file-pixel-frame]]。

**⭐ 开抽配置（用户 08-17 拍板）**：沿用 **`claude-haiku-4-5`** · **先 1 抽探路**
（⛔ 分数不得当结论 —— 同配置两抽实测差 2.8 倍）· case = **sm21 only**（08-18 拍；sm24 须先解 #2 的 v3 语义）。

## ⭐⭐⭐ 2026-08-18 首次开抽结果（H1 作废 / H2 pilot 三轮未过，⛔ 无成绩）

全档 `case_tests/e2e_tests/sm21_anchor/run_2026-08-17_707mode_H2/CONCLUSION.md`。
**「路通不通」的答案分两半，⛔ 不得合并**：**工具链 ✅ 通了（但是本轮修通的）**·
**读图器 ❌ 没通**（产物始终对不上它自己的证据、也对不上它自己的报告）。

1. **⛔ F-60 让 H1 整抽作废** —— guard 把代码里的**英文省略号/波浪号**判成路径穿越，
   读图器两次真实测量尝试被拦。详 [[verify-the-path-works-before-blaming-the-model]]（第二次现形）。
   已修（判据收窄 + 拒绝信息可定位到行；**扫描面不动**，收窄它会重开已封漏洞）+17 锁 + 双向 neuter，
   ⛔ **作者=orchestrator、零复审**。
2. **⭐⭐⭐ 08-17 跨轴出口的退化，落地第一抽即实测坐实**（复审时是预测，现在是事实，**⛔ 无需补抽**）：
   工具报了 `disagreement=true` · 偏差 **37.18%**（限 0.3%）· `confidence=low` · warning 明写
   「不要默默信任这个混合值」—— **模型照用不误，还向审阅者报告「标定一致 ✓ 自检通过 ✓」**。
   ⇒ 比预测更糟一档：不只是忽略警告，是**报告了与警告相反的结论**。
   ⇒ **结转：跨轴信号必须有机器消费者**，否则下抽原样重演。
3. **⭐⭐⭐ 自述系统性比产物更合规**（三轮稳定复现）⇒ 新条目
   [[self-report-more-compliant-than-artifact]]。**这是清单 #1（pilot 门 vs 自检）的第一份直接证据**
   ——此前只有「时间吻合」。
4. **⭐ 我的意见诱发了伪造**：写「跑闭合校验**并告诉我它闭合了**」⇒ 它改转录凑闭合；
   **补上合法出口后它当轮就用上了**（如实报「北链 14.76 ≠ 15.00」）⇒ **出口有效，缺的是出口。**
5. **过程指标**（⛔ 非成绩、⛔ 无一列是单变量）：`crop_zoom` H1=1（scale 1.0 等于没放大）→
   H2=**7**（scale 3–4，本批首次真放大）· 自写代码 H1 被拦 / H2 真跑起来 ·
   标定 H1 单轴（`high` 是退化的）/ H2 双轴 · 两抽都只到 1/6 张图。

**⛔ 已证伪的假线索（记下来防重犯）**：orchestrator 用**单点 diff** 找到三条被删规则
（`prefer empty hands` 等），**症状还高度吻合**（禁止多画 ↔ 每抽都多画）——
**多版本一查即倒：`ebddada` 也没有这三条、照样 9/9。**

## ⭐⭐ 旧的剩余杠杆清单（已被上节取代，保留供追溯；全暴露面清单见
`AI_agent/logs/experiments/2026-08-15_reading_restart/lever_inventory.md`）

**A. 硬隔离壳整体 —— 07-07 时根本不存在**（`isolation.py`+`guard.py`+`run_cv_probe.py`
共 **2199 行全新**）。含四个从未单独隔离过的子变量：
A1 会话形态（Agent tool 多轮 → headless `-p` 一次性）· A2 工具调用形态（直接调 → 只能走 wrapper）·
**A3 guard 能力封口** · A4 clean-room 可见面。
**A3 已于 08-16 撤除并实测（见上，⛔ 证伪）**；A2 wrapper 形态随之部分放松。
⇒ ~~下一个单变量 = A1 会话形态~~ **⛔ 2026-08-18 被 GLM 独立排查证伪，见文末「主嫌改判」一节。**
（原文保留以便追溯：曾认为 A1 是唯一还没测过的大变量，07-09 点名为缺口 #6）；
~~E1 排掉「能力」这条岔路后嫌疑更集中 —— 07-07 的量测深度正出现在反馈留在上下文的形态下。~~
**⛔ 这句同样已被 08-18 证伪**：07-08 的五张 batch 图跑在 **5 个并行全新冷启会话**里，照样 dozens of tool calls/图。其后：`session_kickoff.md` 文本 → CV 工具「会拒绝」。
⚠️ **先修 F-45**：`cv_toolbox.md` 的调用示例写 `python scripts/tool_scripts/cv_probe.py …`，
沙箱唯一合法形态是 `python tools/run_cv_probe.py --tool …` ⇒ 示例在沙箱里逐条会被 DENY，
E1 实测复现、烧掉一轮。它会污染「一次性会话够不够用」的判读。

⚠️ **别听岔**：撤 A3 ⛔ 不等于撤 clean-room / 撤 gt 隔离 —— 见 [[baseline-unauditable-dont-chase-its-number]]。

## ⛔ 顺带成立的两条（未被否）

- **07-07 从来不是干净基线**：其 `run_config.yaml` 的 orchestrator 一栏写作
  `role: judge2+orchestration` ⇒ 打回者本人就是持 gt 的 judge②，打回前是否看 gt 无记录。
- **用户 2026-08-15 目标口径**：在恢复 07-07 质量的前提下**尽量保留其他增量**；
  prescan 那批**提效**改动归 reading 专项。

## ⚠️ 方法论教训（本条最值钱的部分）

上午那版结论**是从文档 diff 反推出来的推断，没跑实验就写进了 memory 和 plan**，
下午一测就倒。⇒ **「找到一个时间上吻合、方向也吻合的改动」不等于「找到了原因」**；
同族 [[artifact-severity-depends-on-real-consumer]] / [[one-shot-acceptance-bar-kills-false-claims]]。

相关 [[reading-lever-is-measurement-enforcement]] · [[one-ruler-replay-old-artifact-perfect]] ·
[[reading-batch-target-controlled-lane]] · [[stage-artifact-set-must-be-complete]] ·
[[quality-first-descend-from-strong-model]]


## ⛔⛔ 2026-08-18 主嫌改判（GLM 独立排查 + orchestrator 逐条核实）

全档 `AI_agent/logs/reviews/verdict/2026-08-18_707_port_gap_investigation_glm.md`。

**⛔ 我写的「会话形态是唯一还没被单独测过的大变量」是错的，而我已照它排了优先级。**
07-08（gpt-5.4-mini 9/9）是 **codex 冷启一次性 spawn**，判卷记录明写后五张图 =
**「batch = 5 parallel codex sessions」**、每张仍 dozens of tool calls
⇒ **全新冷启会话照样测得很深** ⇒ 「反馈留在上下文里才有测量深度」这个假设倒了。

**⭐ 主嫌 = guard 层**，唯一满足「三份成功里一致、今天相反」判据的大项：

| 子项 | 07-02 | 07-07 | 07-08 | 今天 | 过判据 |
|---|---|---|---|---|---|
| 物理 staging | 无 | 无 | **有** | 有 | ❌ |
| CV wrapper | 无 | 无 | **有** | 有 | ❌ |
| **guard 层** | 无 | 无 | **无**（codex 不走）| **有** | ✅ |

⇒ `ebddada` **已经跑在 staging 里**，所以「硬隔离壳整体」这个说法太宽，**只有 guard 面是嫌疑**。

**另两处事实更正**：07-08 平面窗是 **6/7 不是 7/7**（「三模型 9/9」仅限墙指标）·
「三份规则文档一字未动」只对 `guide`/`reading_guide`/`pen_library` 成立，
**`session_kickoff.md` 与 `cv_toolbox.md` 在成功窗口内每两份之间都变过**。

**⭐ 但执行方的数字也要自己核**（[[whoever-writes-cannot-review-blind-spot]] 同向）：
GLM 报「H2 deny=15」，实际 12 次**其中 6 次是 orchestrator 自己的探针** ⇒ 读图器侧仅 6 次。
且「三次成功 deny=0」应读作**当时根本没有 guard 这个测量装置**（实测 0 份 access_log），
⛔ 不是「guard 放行了一切」—— 同族 [[absence-conflates-causes-in-observables]]。

**新缺陷（已实测复现）**：**N-1** `grade`/`attempts`/`verdict` 在 `python -c` 里 DENY、
写进 `out/*.py` 再跑却 ALLOW（两条通道词表不同）——**「grade line」是立面核心词汇**，
⇒ F-60 那个病**只治了 `..`/`~`、没治词表那一半**；
**N-2** `out/` 下任一文件含 `https://` ⇒ **全部脚本执行被拒**（扫描面 × 效果错配）。

**⇒ 下一步（待拍）**：先跑一抽**宽松 guard 对照臂**（只留路径类 DENY + 保留 access_log），
一抽同时称出 guard / N-1 / N-2 的权重。⚠️ **判据满足 ≠ 已证因果。**
