# 移植基座普查（2026-08-16）—— 合并结果表

> **用户拍板（2026-08-16 晚）**：「先总体解决一下【移植】的基座问题，至少保证能调用的 tool、
> 环境这些是 ok 的，再说脚手架的问题。**不要一个个去撞了，这样太笨了。**」
>
> **本文 = 两摊的合并权威表 + 统一编号**。分表：[`grid_A.md`](grid_A.md)（工具面）· [`grid_B.md`](grid_B.md)（政策/环境/留痕面）。
> 派工单：[dispatch_A](../../reviews/request/2026-08-16_substrate_sweep_dispatch_A_claude.md) ·
> [dispatch_B](../../reviews/request/2026-08-16_substrate_sweep_dispatch_B_glm.md)。

---

## 一、一句话结论

**基座能用，但有 7 处缺陷，其中一处（F-55）比预期严重得多**——
它不在工具面，在**净室的写入面**：读图器一条被放行的命令就能改写守门件自己、清空审计日志。

**⇒ 一次普查撞出的缺陷数（7）≈ 前面串行撞了一整天的两倍多（3），耗时约 40 分钟/摊、两摊并行。**
这直接验证了用户那条判断：**当一类缺陷需要「跑一次才发现一个」时，缺的是一次普查和一层锁，不是更多实验。**

---

## 二、规模

| | 摊 A（工具面） | 摊 B（政策/环境/留痕面） |
|---|---|---|
| 席位 | Claude Sonnet 子代理 | GLM 5.3 席位 |
| 实跑格数 | 43 ✅ / 0 ⚠️ / 4 ⛔ / 0 ⬜ | 见 grid_B §S-4 总判（G1–G9 + 环境 + 留痕） |
| 锁 | 43 正锁 + 4 `xfail(strict=True)` | 38 正锁 + 4 `xfail(strict=True)` |
| neuter 自证 | 3 把（5 / 10 / 3 锁精确变红，零连带） | 3 把（G8 / G6 / G3，零连带） |

**新增 89 条测试用例**（81 passed + 8 xfailed），**全部走真实入口**
（真 staging + 子进程跑 staged wrapper / 子进程 `guard.evaluate`），
⛔ 无一把是「直接 import 工具函数」的库层测试——那正是 F-49 潜伏五周的原因。

**主控轻门（独立复跑，不看席位自述）**：
`tests/test_substrate_sweep_tools.py` = **43 passed / 4 xfailed**；
`tests/test_substrate_sweep_policy.py` = **38 passed / 4 xfailed**；
`git diff -- src/ skills/` **为空**（两摊 neuter 均已还原，零残留）；既有测试文件零改动。

---

## 三、缺陷登记（统一编号 F-52 … F-58，⛔ 本轮全部未修）

> **编号对照**：摊 B 原稿用 `F-52B…F-55B` 后缀避免撞号，本表统一重排为 **F-55…F-58**。
> 读 `grid_B.md` 时按此表换算。

| # | 缺陷 | 面 | 严重度 | 出处 |
|---|---|---|---|---|
| **F-55** | ⭐⭐⭐ **写入面只在 Write/Edit 工具形态设防**：`python -c 'open("guard.py","a")…'` 被 guard 判 **allow** 且**实跑真的改写了守门件自己**；`access_log.jsonl` 同样可被清空。对照组（Write 工具写同一路径）被明确拒绝。**主控已独立复现**（guard.py 1224→1225 行） | 净室边界 | **最高** | grid_B F-52B |
| **F-52** | `bbox` 写成**原生 JSON 数组** `[x0,y0,x1,y1]` 时，`--request` / `--batch` 两形态崩溃（退出码 2）；写成字符串完全正常。根因 = `bbox` 不在 wrapper 的 `JSON_OR_PATH_KEYS` 里 ⇒ 被通用分支 `json.dumps` 成单 token，撞上 `_bbox` 的朴素逗号切分。**与 F-49 同族**。**主控已独立复现** | 参数语义 | 高 | grid_A F-52 |
| **F-56** | **guard 根本不校验 `--tool` 的值**（只校键名）⇒ ① 08-15 撤除的 `prescan-plan`/`prescan-elevation` 在**守门层依然放行**（然后在 wrapper 层裸栈崩）——「已撤」这件事在门上不可见；② guard 的 `PROBE_DIRECT_PARAM_KEYS` 仍保留 prescan 的 5 个专属键 | guard↔wrapper | 中高 | grid_B F-53B |
| **F-58** | `overlay_logger` 的 `--candidates-json` 传错**形状**时，吐的是裸 `AttributeError` traceback（`tools.py:711`），不是可操作的校验错误。读图器从文档学形状、学错时拿到的是栈不是指导 | 错误可操作性 | 中 | grid_B F-55B |
| **F-54** | `run_cv_probe.py::main()` 对参数/文件解析**零 try/except** ⇒ `ValueError`/`OSError`/`JSONDecodeError` 以裸 Python 堆栈冒出（退出码 1），而非 `parser.error` 干净文案。产品路径下多被 guard 提前拦住，但真入口直连时可复现 | 错误可操作性 | 中 | grid_A F-54 |
| **F-57** | guard 的参数键白名单是**跨工具扁平表**，不校验「这个键属不属于这个工具」（`storey_line_profiler --axis row` guard 放行、wrapper argparse 拒）。与 F-56 同根 | guard↔wrapper | 中低 | grid_B F-54B |
| **F-53** | `cv_toolbox.md` 里 `--batch requests/<name>.json` 的**占位符尖括号**，逐字粘进真 shell 会被解析成重定向，报错完全指错方向。**与 F-45 同族但机制不同**——F-45 挡在 guard，F-53 挡在 shell 元字符解析，guard 与 wrapper 都管不到 | 文档 | 低（一行可修） | grid_A F-53 |

**另有三条旧缺陷本轮实测坐实、维持未修**：
**F-35**（CV 证据不进 attempt，随 staging 一起消失）· **F-50**（pilot 停在中途时状态归档不了）·
**F-39**（产物引用的 sidecar 缺失**不在任何检查的视野里**——`src/validator/` 对 `cv_evidence`/sidecar 零引用）。
**F-44 的修法实测成立**（allow 也记参数原文 + `executed_code` 哈希）。

---

## 四、被证伪 / 被证实的前提（本轮的另一半产出）

### ✅ 被**证伪**的（可以不用再查了）

1. **「沙箱里的 `python` 可能指向坏的解释器」** —— 实测：读图器环境下 `python` 与 `python3`
   **都解析到 `/opt/venv/bin/python`（3.12.13）**，numpy 2.4.4 / PIL 12.2.0 / scipy 1.17.1 全部可 import。
   仓内 `.venv` 的 numpy 确实是坏的，但**读图器碰不到它**。
   ⇒ **「自写测量代码因解释器失败」这条解释死了。**
2. **摊 B 派工单里两条我写的前提不成立**：① G2「guard 侧记录实际」——实况比预期**更宽**（allow 且零 tool 值校验）；
   ② S-5「其它位置实测拒」——对 Write 工具成立、对 `python -c` **不成立**（即 F-55）。

### ⚠️ 被**证实**的（含我自己提的候选缺陷）

- 主控读代码时提的 **bbox 候选缺陷成立**（F-52），由摊 A 实跑 + 两把 xfail 锁双重确认，主控独立复现。
- 摊 A 派工单里标 ⚠️ 的 6 条前提**逐条核过、全部成立、零证伪**（本仓罕见）。

### ⛔ F-55 对一条既有结论的影响（必须一起说）

08-16 上半场报出的「**E1 那一抽没碰答案**」，其依据是**逐条读了 `access_log` 与 `executed_code`**。
F-55 说明：**被审计的一方能改那份日志**。
⇒ 该结论的严格措辞必须降一档：**不是「它没碰答案」，是「我们手上这份日志显示它没碰」**。
「没看到痕迹」正是本仓记过的坑（**缺席不是信号，除非你显式把缺席变成信号**）。
⚠️ 该口子由**撤能力封口（A3）那批改动**带进来，08-15 之前不存在。

---

## 五、⛔ 没普查完的面（下一轮补，别当成已过关）

1. **S-2 参数形态表未逐格穷举**（51 格中优先做了 bbox 三写法 / `anchors_json` / `candidates_json`
   关键写法 / `scale` 等价性 / window 过滤参数机制）。未正式锁定：
   `recipe` · `sidecar_name` · `axis` · `residual_warn_px` · `residual_warn_m` ·
   window 10 个过滤参数逐个拆开 · B 形态下两个 JSON 参数的**文件路径写法** ·
   `image`/`out_dir` 的**绝对路径**写法。
2. **文档示例的守门件一侧**：摊 A 做了 S-1b（示例经 wrapper 逐条实跑），
   `cv_toolbox.md`「Writing Your Own Measurement Code」那两条**经 guard 的一侧**未单独立格。
3. **⛔ 普查本身尚未交叉审**（谁写谁不批）——两张表都是施工席自己写的，
   主控只做了轻门（复跑 + 抽验 F-55/F-52 两条）。

---

## 六、下一步

**修法批（用户已拍板「出全表 → 一次性修一批」，具体排工待拍）**。建议顺序：

1. **F-55**（净室写面）—— 单独一摊，因为它牵涉「把判据搬到新的测量点」这件事本身
   （本仓已记：撤掉一道按形态封杀的门，工作量不在放开，在搬判据；上一次搬了两次才搬对）；
2. **F-52 + F-54 + F-58 + F-53**（工具面 + 错误可操作性 + 文档）—— 可并一摊；
3. **F-56 + F-57**（guard 不看 tool 值、跨工具扁平键表）—— 同根，可并一摊；
4. 留痕面 **F-35 / F-39 / F-50** —— 归 reading 专项还是本批，待定。
