# 派工单 —— 基座修法批·摊 I：净室写入面 + 守门件的 tool 值校验（F-55 / F-56 / F-57）

**席位**：Claude 侧执行档（Sonnet 5 子代理）
**并行摊**：摊 II（工具面 F-52/F-54/F-58/F-53）由另一席位同时进行，**文件集合与你不相交**。
**用户已拍板的两件事（⛔ 这是前提，不是可选项）**：
1. **F-55 的修法方向 = 「把审计日志挪出读图器的可写面 + 关键文件设成只读」**，
   ⛔ **不是**「在扫描器里加规则去拦写这些路径的代码」；
2. 本摊三条合并给一个席位做，**因为三条的判据互相牵制**（见 §2）。

---

## 0. ⭐ 先读：「停下上报」分层

- **① 承重前提错 ⇒ 停下上报**：本单赖以成立的东西不成立（例如「审计日志能挪出 staging」在架构上做不到）⇒ 停。
- **② 外围论据错 ⇒ 记录后继续做完**：本单任何一句具体判断（凡标 ⚠️前提）错了 ⇒ 写下来照常做完。

**⛔ 派工方错误率 25/25**。本单凡「一律 / 全部 / 共 N 处 / 应该是」当作**可能错的前提**，请主动证伪。

---

## 1. 背景

reading 的读图器跑在隔离净室里，守门件 `src/agent/execution/isolation_templates/guard.py`
判每一条命令的 allow/deny。今天（2026-08-16）的基座普查逐格实跑，撞出三条同族缺陷。
全表：[`../../experiments/2026-08-16_substrate_sweep/README.md`](../../experiments/2026-08-16_substrate_sweep/README.md)。

---

## 2. 你要修的三条（⚠️ 三条互相牵制，必须一个口径）

### F-55 ⭐⭐⭐ 写入面只在 Write/Edit 工具形态设防

**现象（主控已独立复现）**：
```
python -c 'open("guard.py","a").write("# tampered\n")'   → guard 判 allow，实跑真的改了 guard.py（1224→1225 行）
python -c 'open("access_log.jsonl","w").write("")'        → guard 判 allow
Write 工具写同一个位置（对照组）                            → guard 判 deny
```
`WRITE_ALLOWED_DIRS`（只许 `out/` 与 `requests/`）只约束 Write/Edit **工具形态**；
2026-08-15 放开 `python -c` 之后，**OS 层的写面完全不受限**。

**为什么这条严重**：它与 F-44 那笔修法**目标直接冲突** ——
F-44 花力气让 access_log 可信（allow 也记参数原文 + `executed_code` 哈希），
而**被审计的一方能把那份日志清掉**。
今天上半场「E1 那一抽没碰答案」这个结论就建立在读那份日志上 ⇒ 该结论已被降级为
「**我们手上这份日志显示它没碰**」。

**⚠️ 注意威胁模型的边界（别修过头）**：用户 2026-08-13 已明文收窄威胁模型 ——
**防「产物自称经过确定性核」，⛔ 不防「有 run 目录写权的主体蓄意改盘」**。
所以这条**不是**要做防蓄意篡改，是要做到两件事：
① **「它做过什么」这件事不可被它自己抹掉**（审计日志离开它的可写面）；
② **一次手滑（脚本把输出写错路径）不能悄悄毁掉守门件或审计**（关键文件只读）。

**用户拍板的方向**：
- **把 `access_log.jsonl` 挪到读图器够不着的地方**（净室之外），
- **`guard.py` / `tools/` 等关键文件设成只读**。

⚠️前提（请核）：access_log 现在落在 staging 根、`guard._append_log` 写它、
`_staging_root()` 定位它。挪走之后要保证：hook 仍写得进、merge/审计仍读得到、
**读图器读不到也写不到**。

### F-56 守门件根本不校验 `--tool` 的值

只校键名，不校值 ⇒ ① 2026-08-15 撤除的 `prescan-plan` / `prescan-elevation`
**在守门层依然放行**（allow + 记一条 log），然后在 wrapper 层裸栈崩
—— **「已撤」这件事在门上完全不可见**；
② guard 的 `PROBE_DIRECT_PARAM_KEYS` 仍保留 prescan 的 5 个专属键
（`capability_profile` / `no_cc` / `min_strength` / `min_line_len_px` / `label`）。

⚠️ 注意 `guard.PROBE_TOOL_NAMES` 现有注释明写「这不是授权表，授权表是 wrapper 的 `ALLOWED_TOOLS`，
这里只用来措辞报错」。**修这条时必须想清楚：你是在改这个分工，还是在保持分工的前提下让门看得见撤除。**
⛔ 两个都行，但**必须在 grid 里把选择和理由写出来**，别默默改掉一个已声明的设计。

### F-57 参数键白名单是跨工具扁平表

不校验「这个键属不属于这个工具」（`--tool storey_line_profiler --axis row` guard 放行、wrapper argparse 拒）。
⚠️ wrapper 的 `_direct_to_request` 注释明写：**故意不在 wrapper 里复制 guard 的 27 键表**，
理由是 cv_probe 的 argparse 每工具校验「strictly finer」，复制过来只会制造漂移面。
⇒ **这条同样先判「该不该修」再判「怎么修」。** 如果结论是「现状是有意为之、只是错误消息不好」，
**那就如实写「不修 + 理由」**，这也是合格交付。

### ⭐ 三条为什么必须一个人做

F-55 的方向是**把判据从「扫命令文本」搬到「OS 层物理不可写」**；
F-56/F-57 的方向是**往扫描那一层再加检查**。
**同一份判据往两个相反方向搬 ⇒ 必须一个口径。**
本仓已有的判据：**撤掉一道「按形态封杀」的门时，工作量不在放开，在把判据搬到新的测量点上；
搬家时旧判据覆盖过的每一种形态都要重新问一遍「新判据看得见它吗」**（08-16 搬了两次才搬对）。

---

## 3. 交付

1. **修法本体**（`src/agent/execution/isolation.py` / `isolation_templates/guard.py` /
   `isolation_templates/run_cv_probe.py`，按需）；
2. **行为验证**（每条都要，⛔ 不接受只跑测试）：
   **正向**（修法生效：原来能干的坏事现在干不成）+ **反向**（原来该能干的正常事仍能干）
   + **neuter**（把修法中和掉 ⇒ 新锁必须变红 ⇒ 还原 ⇒ `git diff` 零残留）；
3. **新锁**：每条至少一把，走真实入口（真 staging + 子进程），加进
   `tests/test_substrate_fix_cleanroom.py`（新建）；
4. **执行日志** → `AI_agent/logs/reviews/execution/2026-08-16_substrate_fix_I_execution_log.md`：
   写清每条的**选择与理由**（尤其 F-56/F-57 的「修 / 不修」判断）。

---

## 4. ⛔ 回归口径（本摊最容易翻车的地方）

改守门件必然牵动既有锁。**`tests/test_isolation.py` 现有 107 个测试**，
`tests/test_substrate_sweep_policy.py` 有 38 正锁 + 4 xfail（**今天刚立的，正是钉住当前行为的**）。

- **必须跑**：`pytest tests/test_isolation.py tests/test_substrate_sweep_policy.py tests/test_substrate_sweep_tools.py tests/test_cv_toolbox.py -n0 -q`
- **凡是被你改红的既有锁，⛔ 不许直接改锁让它变绿** ——
  逐条判断「这把锁钉住的旧语义，是不是本次有意推翻的」，
  **有意推翻的要在执行日志里逐条列出来（第几把、旧语义、为何该翻）**。
  本仓的固定教训：**「我以为共 N 处」是错误率最高的句式**，所以这份清单要逐处列值。
- **今天新立的 4 把 `xfail(strict=True)`**：如果你的修法让它们意外变绿，pytest 会报红
  —— 那是**正确行为**（提醒摘掉 xfail），照实处理并在日志里说明。

---

## 5. 纪律

- **⛔ 不许碰**：摊 II 的文件（`scripts/tool_scripts/cv_probe.py` · `src/agent/reading/cv_toolbox/**` ·
  `skills/intake_pipeline/0_reading/cv_toolbox.md` · `tests/test_substrate_fix_tools.py`）·
  `AI_agent/` 下除你那份执行日志以外的文档。
- **⛔ 不 commit**（主控统一提交）。**⛔ 不跑 `pip install -e`**。**⛔ 不跑全仓测试**（跑 §4 那四个文件即可）。
- 真解释器 `/opt/venv/bin/python`。
- **改 `src/` 前先备份**：`cp` 到 `backup/src_history/2026-08-16_substrate_fix_I/`（本仓硬纪律）。
- 工作量必须能在一个窗口内收尾；做不完时**优先 F-55**，F-56/F-57 可只交「该不该修」的判断。

---

## 6. 回什么

① 三条各自的**修法与理由**（F-56/F-57 含「修/不修」判断）；② 行为验证三向的证据；
③ 被改红的既有锁**逐处清单**（第几把、旧语义、为何该翻）；④ 新锁清单 + neuter 结果；
⑤ 你证伪掉的我的前提；⑥ 没做完的部分。
