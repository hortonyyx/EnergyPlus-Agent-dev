---
name: green-suite-is-a-property-of-tree-and-launcher
description: 「全仓绿」不只是这个提交的属性，还是【哪棵工作树】+【哪个启动器】的属性——并行席位报的绿/红一律不作数
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 88303e82-7787-4f6b-a409-b4861f320753
  modified: 2026-08-16T08:34:04.738Z
---

**2026-08-14 三席并行时实测**（同一 commit，三种环境三种结果）：

| 环境 | `test_gt_from_dxf` / `test_inspect_dxf` | `test_zone_agent` |
|---|---|---|
| 主树 `/workspaces/EnergyPlus-Agent-dev` | ✅ 16 passed | ✅ passed |
| 干净 worktree + Claude 子代理 | ⛔ 2 failed | ⛔ failed |
| 干净 worktree + GLM 席位 | ⛔ 2 failed | ✅ **passed** |

## 两个根因（都不是代码缺陷）

1. **CLI 子进程跨树导入**：测试用 `subprocess` 跑 `python scripts/tool_scripts/<x>.py`。
   **脚本式启动时 `sys.path[0]` 是脚本所在目录、不是 cwd** ⇒ `import src...` 落到 **editable 安装** ⇒
   子进程内 `REPO_ROOT`（`gt_schema.py:38 = Path(__file__).resolve().parents[3]`）解析成
   **editable 安装指向的那棵树**，而测试传的是本树路径 ⇒ 自家防线拒绝（`gt_vg_config_path_forbidden`）。
   **⛔⛔ 当日更正（很重要）**：我最初把根因写成「指向**主树**」——**错**。
   准确说法 = **指向【最后一次跑过 editable 安装】的那棵树**，其余每棵树都会跨树导入。
   **实证**：并行席位在自己 worktree 里跑了一次 editable 安装（`.pth` 时间戳落在它的会话窗口内）
   ⇒ **共享 venv 的 `.pth` 被改成指向那棵 worktree** ⇒ 此后**连主树**都跨树导入到 worktree
   （三棵树的 `REPO_ROOT` 全部打印成同一棵 worktree）。
   ⇒ **一个施工席可以静默地把整台机器的「权威树」挪走，让 orchestrator 的权威全量失去权威性。**
   ⭐ 救回来靠的是**时间戳对账**：权威全量 `.rc` 落盘 07:32 vs `.pth` 被改 07:35 ⇒ 那次跑在污染之前、结论仍有效。
   ⇒ **纪律：① 席位一律不许在 worktree 里跑 editable 安装 / `pip install -e .`；
   ② 权威全量前后各查一次 `.pth` 指向；③ 判「这次测量干不干净」用时间戳对账，别靠回忆。**
   ⚠️ 顺带一条：该席位拿「我这棵树不红」当证据来推翻 orchestrator 的预测，
   **而那个环境状态正是它自己制造的** ⇒ **「我实测没复现」必须先排除「是不是我把环境改了」。**
2. **`.env` 被 gitignore** ⇒ worktree 里没有 `OPENAI_API_KEY`。
   而 **`scripts/glm_code.sh` 会 `source` 主仓 `.env` 注入子进程**、Claude 子代理不会
   ⇒ **同一棵树、同一份代码，换个启动器全量结果就不同。**

## ⭐ 判别问法

**「这个『绿』是这个提交的属性，还是这棵树 / 这个启动器 / 这台机器工作目录的属性？」**

⇒ **纪律**：
- **并行席位在自己 worktree 里报的「全仓绿/红」一律不作为权威**；权威全量**只在主树跑**。
- 席位报红时，**先在【干净基线树】跑同一条**（不含任何改动）——红就是环境、不是回归。
- **对账要能逐位闭合**才算数：本例 `2603（基线）− 3（worktree 必红）+ 15（新增）= 2615` ✅。
- ⛔ 别让席位「为了让它变绿」去改测试 / 改 `REPO_ROOT` / 往 worktree 塞 `.env`。

## ⚠️ 顺带一条探针纪律（差点自己栽）

我第一版探针用 `python -c "import src..."` 想复现跨树导入，**复现不出来** ——
因为 `-c` 的 `sys.path[0]` 是 cwd，而被测对象是**脚本式启动**（`sys.path[0]` = 脚本目录）。
⇒ **探针必须复刻被测对象的【启动形态】，不只是它的输入。**
同族：[[neuter-must-cover-wiring-not-just-mechanism]] · 08-13「探针有输出也不等于那输出说的是被测对象」。

## ⚠️ 2026-08-16 又栽一次（同一形状，主树内）

主树里**同时存在两个 venv**：`/opt/venv`（PATH 上的，`python -m pytest` 用的，**真环境**）
与仓内 `.venv/`（**numpy 自 08-01 起就是坏的**：913 条 RECORD 只剩 227 个文件、`__init__.py` 都没了）。
我图省事写了 `.venv/bin/python -m pytest` ⇒ 四个测试模块全 ImportError
⇒ **差点把「环境坏了」读成「我的改动把测试搞挂了」。**
换成规约里写的 `python -m pytest -p no:cacheprovider -q`（走 `/opt/venv`）⇒ **371 passed**。
⇒ **纪律：跑测一律用规约 §7.5 的原文命令形态，⛔ 别自己拼解释器路径。**
仓内 `.venv/` 是坏的残留，别用（也别顺手修，没人用它）。

## 出处

[[real-chain-run-exposes-what-tests-cannot]] 的 F-8 面（「全仓绿是这台机器工作目录的属性」）**第三、四面**。
同日另一例：`case_tests/e2e_tests/smalloffice_23/4_mep/` 被 `.gitignore:320` 排除
⇒ orchestrator 预扫说的「21 份产物」在干净检出里只有 20 份（`git check-ignore -v` 一行就能发现，没跑）。

## ⛔ 第三种「不是代码缺陷」的红：**我自己在全量跑着的时候动了树**（2026-08-22 实测）

把全量丢到后台后，我又手跑了一次判分验证（`run_stage.py artifacts <case> <run> 0_reading`）——
它会**重写 `case_tests/` 里的 `grade.png` / `score_vs_gt.json` / `renders/`**。
而 `test_d6_judge_scoring_path_leaves_case_tests_byte_for_byte_unchanged`
**对真实 `case_tests/` 树做前后指纹比对** ⇒ 我的命令正好落进它的前后之间 ⇒ 报红。

**代价**：白跑 16 分钟全量；**而且我差点把这条红记到并行施工席位头上**
（当时正在复核 GLM 交付的立面判卷绑定，第一反应是「他改判卷语义导致判分不幂等」）。
排查中我甚至先做了「连跑两次看字节变不变」的实验并得出「每次都在重写=真回归」——
**那个实验本身也被我自己的并发污染了**。真相：干净树上单独跑 d6 一次就过。

⇒ **规矩**：**全量在跑的时候，⛔ 不许再跑任何会写仓库的命令**
（判分 / `flow` / `artifacts` / `record` / 任何产 attempt 的动作）。
要验证就等全量结束，或到独立 worktree 里验。
⇒ **推论（更重要）**：**全量的结果是「这段时间内这棵树」的属性，不只是这个提交的属性。**
判一条红之前先问：**这段时间里有没有别的东西（包括我自己）在动这棵树？**
同族 [[repeat-the-run-before-accusing-a-seat}]] —— 那条讲「一次红不是证据」，
这条讲「红之前先查现场有没有被自己污染」。


## ⭐⭐⭐ 2026-08-27 第四种假象：**跑测途中，启动器被第三方改掉**

前三种假象都是**开跑前**就定了（树不对 / 启动器不对 / 同机竞争）。这一种在**跑测窗口内**发生：

共享 venv 的 editable 装机文件
`/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth`
内容被从主树改成了 **`/tmp/ep_f97`**（某个席位在自己的 worktree 里跑了 `pip install -e .` 之类）。
`mtime = 11:52:41`，而 orchestrator 那轮**主树权威全量**的窗口是 **11:44 → 12:07** ⇒ **正好被穿过**。
⇒ 那个 `3046 passed` 的**合并门**读数只能作废重跑。

⭐ **发现它的是施工席位**（在自述里写「那句『裸跑会串到主树』的警告现在方向是反的」），
**而且它没有去动它** —— 处置正确。⛔ 我没有直接证据指认是谁执行的安装，故不追责
（[[repeat-the-run-before-accusing-a-seat]]）。

**How to apply（新增两条）**：
1. ⛔⛔ **所有派工单/复核单固定写一条硬禁令**：
   **席位绝对不许跑 `pip install -e .` / `pip install .` / 任何写 `site-packages` 的命令**
   —— 这个 venv 是**全机器共享**的，改它 = 把别的席位和主树一起拖下水。
   import 有问题**一律用 `python -m …` 或 pytest 入口解决，⛔ 不许靠重装解决**。
2. ⭐ **权威全量必须带哨兵**：跑之前与跑完各记一次 `.pth` 的哈希与内容，
   **两次相同才算这次读数有效**。命令形状：
   `echo BEFORE=$(sha256sum $PTH); python -m pytest -q -n 6; echo AFTER=$(sha256sum $PTH)`
   ⇒ 「绿」是**树 + 启动器 + 这段时间**的属性，而**启动器现在被证明是会在跑测中途变的**。
   同族复核单里加一条 `.pth` 哨兵判据（开工前 + 交件前各读一次，变了即停下上报）。

⭐ **它同时是债 D-2（删 `.pth` + 全走 `python -m`）迄今最硬的一次实证**：
**A 案（给裸跑脚本加自举）只收窄「裸跑」这一个暴露面，而这次被改的是 `.pth` 本身** ——
A 案那把机械锁对此**完全沉默**。


## ⭐⭐⭐ 2026-09-01 第五种，且它**改写了上面第四种的归因**：**没有任何席位跑过安装**

**现象**：我给三方各建了一棵 worktree 派活。审阅进行中，`.pth` 从主树变成 `/tmp/o22m2_review_glm`
（某个席位的 worktree），`mtime` 正是那个席位**启动的那一秒**。
GPT 席位据哨兵不符 **A 层停报 —— 停得对**（题错 #69，累计 69/69）。

**⛔ 我的第一判定是错的**：我判「GLM 席位违纪跑了 `pip install -e .`」。
去读它的会话记录（`~/.claude/projects/-tmp-.../<uuid>.jsonl` 里逐条 `tool_use` 的 Bash command）
⇒ **20 条 Bash 调用全部只读**，零 install。**差点冤枉席位**（[[repeat-the-run-before-accusing-a-seat]]）。

**真因（判别实验，⛔ 不是推理）**：
```
$ cat .mcp.json      → {"EnergyPlus-Agent":{"command":"uv","args":["run","python","main.py",…]}}
$ env | grep UV_     → UV_PROJECT_ENVIRONMENT=/opt/venv
--- 前 --- /tmp/o22m2_review_glm
$ cd /tmp/o22m4_review_orch && uv run python -c "pass"
      Built energyplus-agent @ file:///tmp/o22m4_review_orch     ← 一句就改掉了
--- 后 --- /tmp/o22m4_review_orch
```
⇒ **本项目 `.mcp.json` 用 `uv run` 起 MCP server，而 `UV_PROJECT_ENVIRONMENT` 全局指向共享 venv
⇒ 任何以 worktree 为工作目录启动的【claude 家族】席位，光是【启动】就把共享 editable 安装改指过去。**
（`codex` 席位不吃 `.mcp.json` ⇒ **不触发**；实测同轮 GPT 席位全程没动过它。）
恢复 = 回主树 `uv run python -c "pass"`。

## ⇒ 两条更新（⛔ 覆盖上面第四种的处方）

1. ⛔⛔ **「禁止席位跑 `pip install -e .`」这条纪律【必要但不充分】** ——
   这次没有任何人打过那条命令。**归因时不许从「.pth 变了」直接推「有人违纪」**：
   先查会话记录里的实际命令，再查有没有**启动即触发**的机制（`uv run` / MCP / 钩子）。
   ⚠️ 08-27 那次「某席位跑了 `pip install -e .` 之类」的归因**很可能也是这个机制**，⛔ 别当已证事实引用。
2. ⭐⭐⭐ **`.pth` 哨兵哈希是【代理量】** —— 同族 [[proxy-mistaken-for-the-thing]]。
   席位真正需要的承重不变量是：**「我这次导入的，是不是我该测的那份代码」**：
   ```
   python -c "import <被测模块> as m; print(m.__file__)"   # 必须落在我自己的工作目录里
   ```
   **cwd 胜过 `.pth`**（实测：`.pth` 指向别处时，从 worktree 跑 pytest 仍解析到本 worktree）
   ⇒ 哈希不符**不一定**说明读数脏，而 `__file__` 不对**一定**脏。
   **派工单/复核单的环境判据改用 `__file__`，哈希降为「记一条、不停报」。**
   ⭐ 变异实测尤其要把 `__file__` 和 pytest **同一条命令里一起跑并贴出来**——
   否则「变异注入了却没生效」与「锁没牙」在读数上长得一模一样。
3. ⭐ **权威全量前仍要把 `.pth` 恢复到主树并核哈希**（那条没变）；
   ⛔ 但别再指望「哈希没变」能证明没人动过环境 —— 它只证明**结束时**指向对。
