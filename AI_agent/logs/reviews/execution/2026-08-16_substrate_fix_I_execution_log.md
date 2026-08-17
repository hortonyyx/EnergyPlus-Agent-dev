# 基座修法批·摊 I 执行日志 —— F-55 / F-56 / F-57

**席位**：Claude 侧执行档（Sonnet 5 子代理）
**派工单**：`AI_agent/logs/reviews/request/2026-08-16_substrate_fix_dispatch_I_cleanroom.md`
**改动文件**：`src/agent/execution/isolation.py` · `src/agent/execution/isolation_templates/guard.py` ·
`tests/test_isolation.py`（既有文件，16 处路径改法 + 1 处注释）·
`tests/test_substrate_sweep_policy.py`（既有文件，1 处路径改法）·
`tests/test_substrate_fix_cleanroom.py`（新建，23 个测试）。
**未改动**：`src/agent/execution/isolation_templates/run_cv_probe.py`（F-55 不需要动它；
F-56/F-57 判断为「不修」，同样不需要动它——且该文件本轮由摊 II 并发在改 F-54/F-52，未触碰减少冲突面）。
**备份**：`backup/src_history/2026-08-16_substrate_fix_I/{isolation,guard,run_cv_probe}.py.orig`（改前原文）。

**⚠️ 中途断线说明**：本单执行到"实现完成 + 回归跑绿 + 正在读 diff 确认无半截改动"这一步时，
上游 API 报错导致会话被硬切断。恢复后按主控要求，先核实了断线时的真实状态（见下方"断线状态核实"），
确认零残留、零半截改动后，才继续做 neuter + 本文件。

---

## 0. 断线状态核实（主控要求，恢复后第一时间做的事）

1. **有没有 neuter 没还原**：没有。断线时我正在做的是"读 diff 确认改动完整"（纯只读操作：
   `git diff`／`ps aux`／`wc -l`），neuter 验证**根本还没开始**——恢复后逐字核对了
   `isolation.py`／`guard.py` 的完整 diff，两份都是最终态实现，没有任何"临时改坏"的残留。
2. **有没有半截改动**：没有。`git status --short` + 逐文件 `git diff` 核对：我改动的 3 个既有文件
   （`isolation.py`／`guard.py`／`tests/test_isolation.py`）+ 1 个新文件
   （`tests/test_substrate_fix_cleanroom.py`）全部语法完整（`py_compile` 过）、逻辑自洽，
   无残留的调试代码、无 TODO 占位。
3. **完成到哪一步**：F-55 代码本体已完成（两条机制）+ 23 个新锁已写且全绿 +
   `tests/test_isolation.py` + `tests/test_substrate_sweep_policy.py` +
   `tests/test_substrate_fix_cleanroom.py` 三文件回归干净跑过（309 passed, 4 xfailed, 0 failed）；
   F-56/F-57 判断已在脑内定型但**执行日志文件本身当时确实还不存在**（主控指出的这一点核实成立）；
   neuter 验证当时**确实还没做**。恢复后按顺序补完：先 neuter（§5.3），再写本文件。

**断线后新发现（不属于上面三条，但必须一并说明）**：恢复后重新完整跑了一遍 §7 的四文件回归，
发现摊 II 并发的 F-52/F-54 修法已落地（`run_cv_probe.py` 的 diff 里能看到 F-54 的 try/except 包装），
导致 `tests/test_substrate_sweep_tools.py` 里 3 把 `xfail(strict=True)` 短暂 XPASS 报红——
**这不是我的改动造成的**（那 3 把锁测的是 F-52/F-54，摊 II 的项，且该文件不在我的改动范围内），
后续重新单独跑该文件时已确认摊 II 自己把 xfail 摘掉、变成 76 个正锁全绿，无需我处理。

---

## 1. F-55 —— 修法与理由

### 1.1 用户拍板的方向（前提，非我的选择）

> 把 `access_log.jsonl` 挪到读图器够不着的地方（净室之外）+ `guard.py`/`tools/` 等关键文件设成只读。
> ⛔ 不是在扫描器里加规则拦写这些路径的代码。

我按这个方向实现了**两条独立机制**，分别对应用户说的"两件事"：

### 1.2 机制① —— 把 `access_log.jsonl` 挪出 staging_root

**改法**：新增 `_audit_dir(root)`，规则是 `root.parent / f"{root.name}.audit"`——staging_root 的**同级兄弟目录**，
永远不是它的子孙。`guard.py::_append_log` 改成写 `_audit_dir(root) / "access_log.jsonl"`；
`isolation.py::build_isolation_workspace` 在最开始就把这个目录 mkdir 好（保证读图器第一条命令跑之前它已存在）；
`_build_provenance`／`_archive_isolation_artifacts` 相应改成从新位置读/归档。

**为什么这样写不违反"两侧必须一致"**：`guard.py` 是逐字节拷进每个 staging 的**无状态模板文件**
（stdlib-only，见文件头注释），没法在拷贝时注入本次运行的专属路径，所以两边（`guard.py` 自己算、
`isolation.py` 也自己算）用**同一条确定性命名规则**各自推导，而不是共享一份运行时常量——
和 `writable_root`/`OUTPUT_ROOT_DIR` 在 `guard.py`/`run_cv_probe.py` 之间已有的镜像模式完全一致。

**为什么"读图器读不到也写不到"这句话成立**：这不是靠权限位（那是机制②的事），是靠**根本不在它知道的树里**——
staging_root 是读图器的 cwd，也是它被明确告知的唯一一棵树（MANIFEST.json／input_inventory.json／kickoff
prompt 全部只谈这棵树内部的路径）。想够到兄弟目录，要么写字面 `..`（guard 的 `_lexical_check` 无条件拒绝这个
token，对 Bash 命令文本和被执行的代码文本都生效）、要么写字面绝对路径（同样被"absolute path outside staging"
拒绝）、要么**不写字面路径、程序化推导**（例如 `os.path.dirname(os.getcwd())` 再 `os.listdir`）——最后这条路
guard 现有的 `EXEC_DENY_IMPLICIT_PATHS` 枚举表**没有覆盖到**，是一个已存在、和这次改动无关的旁路（详见 §6）。
按 2026-08-13 收窄的威胁模型（"防意外/常规路径，不防蓄意绕过"），这个旁路不在这次要关闉的范围内，但如实记录。

### 1.3 机制② —— 关键文件在 OS 层设只读 + 一个中途发现的重要限制

**改法**：新增 `_lock_down_readonly_surface(staging_root)`，在 `build_isolation_workspace` 的**最后一步**
（`manifest.save()` 之后）对 staging_root 下**除 `out/`／`requests/` 子树之外的每一个文件**去掉
owner/group/other 的写位（`chmod`，只清写位，不动读/执行位）。只 chmod 文件、不 chmod 目录——
理由写在代码注释里：目录写位管的是"能不能在这个目录里新建/删除/改名"，文件自己的写位管的是"能不能
`open(path,'a'/'w')` 改写一个已存在的文件"（dispatch 复现的两条攻击都是后者）；只锁文件既能挡住复现的攻击，
又不破坏 `shutil.rmtree`／pytest 自己的 `tmp_path` 清理（那只需要目录写位），也不破坏本仓大量既有测试
"直接在已建好的 staging 根新建一个文件做测试夹具"（比如 `_request()` 默认写 `staging/request.json`）的用法。

**⚠️ 验证过程中发现的重要限制（这不是拍板方向本身的问题，是这个容器的运行时事实）**：

这个沙箱**全程以 root 运行**（`whoami` → root，控制端、被 spawn 的读图器、每个 guard 子进程全部一样）。
**root 会绕过它自己拥有的文件的 DAC 权限检查**——`chmod 0444` 之后，`open(path,"a")` 作为 root 跑**照样成功**。
这个发现是我在给"guard.py 现在改不动了"写第一个新锁时实测撞到的（不是读代码猜的），核对方法：

1. 直接实测：`chmod 0444` 一个文件后，`python3 -c 'open(...,"a").write("x")'` 作为 root 跑，`exit=0`，内容真的被改了。
2. 排查过 `chattr +i`（不可变位，连 root 不先清位都写不进）——**这个容器不支持**：`chattr: Operation not
   permitted while setting flags`，因为 `/` 和 `/tmp` 都是 overlayfs，拒绝 `FS_IOC_SETFLAGS`。
3. 验证过一个**真的有效**的替代方案：`setpriv --bounding-set=-dac_override,-dac_read_search,-fowner,-chown`
   把这几个能力从 bounding/inheritable 集合里去掉后，同样的 root 进程再写同一个只读文件，`PermissionError`，
   拒绝生效。这证明 chmod 机制本身没问题，缺的是"读图器进程本身不是无约束 root"这个前提。

**我的判断**：机制②的实现**按拍板方向如实做了**（关键文件在 build 之后拿到只读权限位，结构性可验证），
但**在这个容器里它当前不提供额外防护**——因为读图器和被保护文件同属一个无约束 root。把
`setpriv` 的能力削减接到 `spawn_command`（读图器整个会话的唯一发起点，drop 一次会被它 fork 出的所有子进程
继承，包括每次 guard.py hook）**可以**补上这个洞，但我判断这超出本批范围：
① 它改变的是"读图器整个会话怎么被启动"，影响面比"给几个文件去掉写位"大得多；
② 我没有办法在不真的拉起一个 `claude -p` 会话的前提下完整验证它不会破坏读图器自身需要的其它能力
（这件事我这轮做不到，也不该在没把握的情况下动读图器启动路径）；
③ 拍板原文只说"设成只读"，没有提"还要处理 root 绕过"这层——这是我在验证时才发现的新事实，不是拍板前提本身错了。
**已在 `isolation.py::_lock_down_readonly_surface` 的 docstring 里完整记录这个发现**（含
复现命令、`chattr` 结论、`setpriv` 验证结果），并在 §8 登记为后续跟进项（候选编号 F-59）。

**这条限制不影响机制①**：机制①（挪日志）是路径不可达，不依赖权限位，root 与否不影响它的有效性——
这也是为什么下面的行为验证里，机制①相关的新锁不需要 `setpriv` 就能验证"确实防住了"，
机制②相关的锁则拆成"结构性检查"（权限位本身对不对，root 无关）和"在非特权等价进程下真的写不进"
（用 `setpriv` 构造）两类，同时**诚实地保留了一把"以字面 root 身份仍能绕过"的正锁**，
不让沉默冒充"问题已解决"。

---

## 2. F-56 —— 判断：不修

**现象**：guard 不校验 `--tool` 的**值**，只校验键名是否在白名单里；已撤的 `prescan-plan`/`prescan-elevation`
在 guard 层依然放行（记一条 `allow`），失败发生在 wrapper 层。

**判断依据（先判该不该修）**：

1. `guard.py` 里 `PROBE_TOOL_NAMES` 上方的注释是**已声明的设计**："this is NOT an authorization list, the
   authorization list is wrapper's ALLOWED_TOOLS, this here is only used for phrasing error messages"；
   `run_cv_probe.py` 里 `ALLOWED_TOOLS` 上方的注释从另一侧印证同一个分工："guard.py's PROBE_TOOL_NAMES exists
   only to phrase error messages and defers to this list. Withdrawing a tool here is what actually removes
   the capability." 两处独立写死同一个结论，不是我推断出来的。
2. 我评估过"改分工"这条路（让 guard 也校验 `--tool` 的值，变成第二道权威）：唯一能不引入
   硬编码第二份列表（从而制造漂移面）的做法是让 `guard.py` 在运行时 `import run_cv_probe` 读它的
   `ALLOWED_TOOLS`（两者共同暂存在同一个 staging 根，`run_cv_probe.py` 本身也已经是这么处理
   `writable_root`/`parse_probe_batch` 的——延迟 import `guard`）。技术上可行（我验证过不会出现循环 import，
   因为 `run_cv_probe.py` 对 `guard` 的引用都在函数体内、不在模块顶层），但这会给 `guard.py` 引入一个新的
   "依赖第二个 staged 文件"耦合，且**改变了两个文件之间已声明的分工本身**——超出"该不该修"这一步该做的判断，
   是一次更大的架构决定，不该我一个人在"判缺陷"这道单子里顺手定。
3. "已撤的工具在 wrapper 层报裸栈"这个具体症状是 **F-54**（摊 II 的项，我不许碰 `main()` 的异常处理），
   和"guard 该不该校验 tool 值"是两个不同层面的问题——F-54 已经在本轮被摊 II 修掉（见 §0 断线后新发现），
   即便 F-56 不修，"裸栈"这个最刺眼的症状已经不存在了（现在是 `run_cv_probe.py: error: unsupported cv_probe
   tool: 'prescan-plan'`，退出码 2，wrapper 自己的干净路径）。
4. 剩下的代价是："guard 对已撤工具记一条 `allow`，而不是 `deny`"——这条本身不构成安全洞（wrapper 仍然是
   唯一权威，仍然拒绝），只是审计日志上这一条决策记录不够精确。给 F-55 记录的教训是"日志准确性很重要"，
   但这里的不精确和 F-55 那种"日志可被清空"不是同一等级的问题——它没有让任何东西变得可信但其实不可信，
   它只是让"guard 这层的决策"和"整条链路最终会不会跑"这两件事没有对齐，而 guard 从来就不承诺后者
   （guard 对任何"参数值本身合法但语义上会失败"的调用都不做语义预判，这是它一直以来的设计边界，不是
   F-56 特有的）。

**结论：不修**——保持现状的分工（wrapper 是唯一权威，guard 只做词法/结构层面的粗筛），
理由是①②两处已声明的设计，③④是代价评估。**新增哨兵锁**（见 §6）钉住"guard 松、wrapper 兜底"这个
现状的两半，防止未来有人在不知情的情况下把 wrapper 的兜底也拿掉。

---

## 3. F-57 —— 判断：不修

**现象**：guard 的 27 键参数白名单是跨工具扁平表，不校验"这个键属不属于这个工具"——
`--tool storey_line_profiler --axis row`（`axis` 不是它的参数）guard 放行，wrapper 的 argparse 拒绝。

**判断依据**：

1. `run_cv_probe.py::_direct_to_request` 的 docstring 是**已声明的设计**："The per-parameter allowlist is
   deliberately NOT duplicated here: cv_probe's own argparse rejects an option that its subparser does not
   declare, and it does so per tool, which is strictly finer than a flat list. Copying the guard's 27-key
   tuple into a second file would only create a drift surface." ——这段话**逐字**回答了"该不该修"：
   作者已经权衡过"guard 也做逐工具校验"这个选项，明确拒绝了，理由正是"制造漂移面"，
   和 F-56 我自己权衡出的理由完全同构。
2. 失败呈现方式已核实：`storey_line_profiler --axis row` 在 wrapper 层是 argparse 自己的
   `unrecognized arguments` 错误——**不是裸 traceback**，是 argparse 标准的"usage + 一行 error + 退出码 2"，
   这本身就是"可操作的错误"，不属于 F-45/F-53/F-54/F-58 那个"读图器拿到栈不是指导"的族。
3. 想在不复制 27 键表的前提下做到"逐工具校验"，需要 guard 知道**每个工具自己的参数集合**——这份信息目前
   只活在 `scripts/tool_scripts/cv_probe.py`（摊 II 的文件，我不许碰）的 `build_parser()` 里，唯一不复制的
   办法是像测试文件里 `_cv_probe_tool_keys()` 那样对源码做 AST 风格的字符串解析——这是**测试专用的取巧手法**，
   不适合搬进生产的 `guard.py`（脆弱：cv_probe.py 的写法稍微变一下解析就可能悄悄失效）。

**结论：不修**——理由与 F-56 高度同构：两条缺陷本质上是**同一根**（guard 只看键名、不看键值/键属主），
已声明的设计在两处独立文件里各自讲清楚了取舍，且**失败呈现本身是干净的**（argparse 的标准错误），
不构成"读图器拿不到指导"的可用性问题。**新增哨兵锁**（见 §6）钉住这个现状。

---

## 4. 我证伪 / 精化掉的前提

| # | 派工单/隐含前提 | 结果 |
|---|---|---|
| 1 | （隐含）"关键文件设成只读"这个机制在当前执行环境里能提供实际的写保护 | **精化**：机制本身正确、可验证（`setpriv` 证实），但在**这个容器**（全程 root）里，chmod 单独不提供任何额外保护——发现过程见 §1.3，已在代码注释和 §8 后续项里如实记录，不是拍板方向本身错，是环境细节此前没人验证过 |
| 2 | §2「⚠️前提」"access_log 挪走之后要保证 hook 仍写得进、merge/审计仍读得到、读图器读不到也写不到" | **核过·三点均成立**（对"读不到也写不到"的成立范围做了precise化：防的是常规/字面路径引用，不防程序化推导路径这条已存在、和本次改动无关的旁路，见 §1.2 末尾） |
| 3 | F-56/F-57「先判该不该修」的框架本身 | **未被证伪，反而被两处独立的源码注释直接印证**——这是本单少有的"派工单判断在代码里找到了逐字证据"的情形 |

其余我没有找到需要证伪的具体判断——§2 对 F-55/F-56/F-57 现象的描述（guard 放行、wrapper 兜底、日志被清空的复现）
逐条核对，均属实。

---

## 5. 行为验证三向证据（仅 F-55，F-56/F-57 无代码改动、见 §2/§3 的哨兵锁）

### 5.1 正向（原来能干的坏事现在干不成 / 变得可观测）

- **机制①**：`open("access_log.jsonl","w").write("")`（dispatch 复现原话）在 staging 根跑，
  真实审计日志（新位置）**条目数、内容逐字不变**——测试
  `test_python_c_write_to_access_log_jsonl_in_staging_root_does_not_touch_the_real_log`。
  结构性佐证：真实日志确实不在 staging_root 子树内——`test_access_log_lives_outside_staging_root`。
- **机制②（结构性，root 无关）**：build 完成后 `guard.py` 等文件的 mode 位确实没有写位——
  `test_guard_py_mode_bits_lose_write_permission_after_build`、
  `test_other_key_files_lose_their_write_bit_too`（5 个目标：MANIFEST.json / isolation_settings.json /
  tools/run_cv_probe.py / session_kickoff.md / case_data 源图）。
- **机制②（行为性，在非特权等价进程下）**：`open("guard.py","a").write("# tampered\n")`（dispatch 复现原话）
  在 `setpriv` 削减能力后的子进程里跑，真实失败（`PermissionError`）、内容逐字节不变——
  `test_python_c_append_to_guard_py_is_refused_under_a_nonprivileged_process`；
  同一形状扩到另外 5 个目标——`test_other_key_files_are_refused_under_a_nonprivileged_process`。
- **诚实的反例（不是正向证据，是防止过度声称）**：同一条 `guard.py` 追加攻击，**以字面 root 身份**跑，
  仍然成功——`test_known_limitation_plain_root_bypasses_the_chmod_lockdown`，锁的是 §1.3 的已知限制本身。

### 5.2 反向（原来该能干的正常事仍能干）

- `out/`／`requests/` 下的合法写入仍然成功——`test_legitimate_out_and_requests_writes_still_succeed`。
- A3（同日更早批次）放开的"读图器写自己的测量脚本并跑"仍然成立，不被这次的只读锁定误伤——
  `test_reader_authored_script_under_out_can_still_be_created_and_run`。
- 既有测试大量使用的"直接在 staging 根新建一个测试夹具文件"（如 `_request()` 默认写法）不受影响——
  `test_request_json_can_still_be_staged_directly_at_root_by_the_test_harness`。
- guard 对"复现命令"本身的**判定**（allow/deny）没有被这次改动动过——
  `test_guards_own_decision_for_the_repro_command_is_unchanged`（明确本批不加扫描器规则）。
- 真实 hook 在日志搬家后仍然正确、持续地追加条目，F-44 的既有契约（allow 记 excerpt/executed_code，
  deny 记 excerpt）逐字段核对未退化——`test_real_guard_hook_keeps_appending_to_the_relocated_log_across_many_calls`。
- 完整 merge 链路（formal build → 真实 guard 调用 → merge）仍然把（搬家后的）日志正确归档进
  `isolation_archive/`，`isolation_provenance.json` 的 `access_log_sha256`/`access_log_entries` 字段
  正确反映新位置的内容——`test_merge_still_archives_the_relocated_log_and_binds_its_hash`。

### 5.3 Neuter（两条机制分开中和，逐条验证锁的分辨力）

**方法**：改前用 `cp` 把 `isolation.py`/`guard.py` 快照到 scratchpad，中和后用 `diff` 确认逐字节还原，
全程用 Edit 工具做中和（可逐字追溯），用 `cp` 做还原（跳过手工重打字风险）。

| # | 中和目标 | 改法 | 结果 | 还原确认 |
|---|---|---|---|---|
| 1 | 机制①（挪日志） | `guard.py::_append_log` 的 `log_path` 改回 `root / "access_log.jsonl"`（一行） | 跑 `test_substrate_fix_cleanroom.py`：**恰好 4 把变红**（`test_python_c_write_to_access_log_jsonl_in_staging_root_does_not_touch_the_real_log`／`test_access_log_lives_outside_staging_root`／`test_real_guard_hook_keeps_appending_to_the_relocated_log_across_many_calls`／`test_merge_still_archives_the_relocated_log_and_binds_its_hash`），其余 19 把仍绿，零连带 | `diff guard.py guard.py.preneuter` 逐字节相同 |
| 2 | 机制②（只读锁定） | `isolation.py::build_isolation_workspace` 里注释掉 `_lock_down_readonly_surface(staging_root)` 这一行调用 | 跑 `test_substrate_fix_cleanroom.py`：**恰好 13 把变红**（`test_guard_py_mode_bits_lose_write_permission_after_build`／`test_python_c_append_to_guard_py_is_refused_under_a_nonprivileged_process`／`test_known_limitation_plain_root_bypasses_the_chmod_lockdown`【因其自身前置断言"mode 位确实没写位"失败，这是预期内的正确变红，不是误连带】／`test_other_key_files_lose_their_write_bit_too` 5 格／`test_other_key_files_are_refused_under_a_nonprivileged_process` 5 格），其余 10 把仍绿，零连带 | `diff isolation.py isolation.py.preneuter` 逐字节相同 |

还原后重跑 `git diff --stat -- src/agent/execution/`：与中和前完全一致（171 insertions/11 deletions，
两文件），`grep -rn "NEUTER-A-TEMP\|NEUTER-B-TEMP" src/` 零命中，确认零残留。

---

## 6. 新锁清单（`tests/test_substrate_fix_cleanroom.py`，23 个测试，全部真实入口）

**方法论**：全部经真实 `build_isolation_workspace` 建出的 staging + 真实子进程
（staged `guard.py` 的 `main()`，或裸 `python -c`，或 `setpriv` 包裹的子进程）——
零 monkeypatch、零直接 import guard.py 内部函数当库用。

| 分组 | 测试 | 验的是什么 |
|---|---|---|
| F-55 结构 | `test_guard_py_mode_bits_lose_write_permission_after_build` | build 后 guard.py 的 mode 位确实无写位（root 无关的静态检查） |
| F-55 结构 | `test_other_key_files_lose_their_write_bit_too`（5 格） | MANIFEST/settings/wrapper/skill-doc/源图同样无写位 |
| F-55 决策不变 | `test_guards_own_decision_for_the_repro_command_is_unchanged` | 复现命令本身的 guard 判定仍是 allow（本批不加扫描规则的证据） |
| F-55 行为·非特权 | `test_python_c_append_to_guard_py_is_refused_under_a_nonprivileged_process` | setpriv 降权后，guard.py 追加攻击真实失败且内容不变 |
| F-55 行为·非特权 | `test_other_key_files_are_refused_under_a_nonprivileged_process`（5 格） | 同上扩到另外 5 个目标 |
| F-55 已知限制 | `test_known_limitation_plain_root_bypasses_the_chmod_lockdown` | 诚实记录：字面 root 身份仍能绕过 chmod（正锁，非 xfail） |
| F-55 机制① | `test_python_c_write_to_access_log_jsonl_in_staging_root_does_not_touch_the_real_log` | dispatch 复现命令2：真实日志不受影响 |
| F-55 机制① | `test_access_log_lives_outside_staging_root` | 结构性：真实日志确实不在 staging_root 子树内 |
| F-55 反向 | `test_legitimate_out_and_requests_writes_still_succeed` | out/requests 合法写入不受影响 |
| F-55 反向 | `test_reader_authored_script_under_out_can_still_be_created_and_run` | A3 放开的"写脚本再跑"能力不受影响 |
| F-55 反向 | `test_request_json_can_still_be_staged_directly_at_root_by_the_test_harness` | 既有测试夹具写法（root 新建文件）不受影响 |
| F-55 反向 | `test_real_guard_hook_keeps_appending_to_the_relocated_log_across_many_calls` | F-44 契约（excerpt/executed_code）在新位置逐字段不退化 |
| F-55 端到端 | `test_merge_still_archives_the_relocated_log_and_binds_its_hash` | 完整 merge 链路正确归档+哈希绑定新位置的日志 |
| F-56 哨兵 | `test_f56_guard_allows_withdrawn_prescan_tool_value_but_wrapper_still_refuses` | 「不修」判断依赖的兜底属性：guard 松、wrapper 仍拒绝 |
| F-57 哨兵 | `test_f57_guard_allows_key_tool_mismatch_but_wrapper_argparse_still_refuses` | 「不修」判断依赖的兜底属性：guard 松、wrapper argparse 仍拒绝 |

**Neuter 结果**：见 §5.3——两把 neuter 精确打红对应的锁组（4 把 / 13 把），零连带，已还原确认零残留。

---

## 7. 被改红的既有锁 —— 逐处清单（本仓最容易踩错的地方，逐条列值，不写「共 N 处」）

严格意义上，下面这些锁**在我的改动过程中从未被观测到处于"红"状态**——因为我是把
"改实现"和"改这些测试自己读日志的路径"放在**同一批**改动里完成的，不存在"先跑红、再改绿"的中间态。
但它们的**旧语义**（"access_log.jsonl 就在 `staging/access_log.jsonl`"）确实被本次改动**有意推翻**——
这正是 F-55 修法的核心内容，所以逐条列在这里，而不是含糊地说"顺手改了几个路径"。

**旧语义**：以上所有测试都直接读 `staging / "access_log.jsonl"` 来验证 guard 的判定/日志字段。
**新语义**：审计日志的物理位置搬到 `staging.parent / f"{staging.name}.audit" / "access_log.jsonl"`
（`_access_log(staging)` 辅助函数）。**为何该翻**：这就是 F-55 要修的东西本身——日志留在 staging 内部
正是"读图器能力所及"这件事的根源，搬家是拍板方向的字面要求，不是我自选的重构。
**每一处验证的属性本身（谁在什么条件下 allow/deny，日志字段有没有 excerpt/executed_code）完全没变**，
变的只是"去哪读这份日志"。

### `tests/test_isolation.py`（16 处，按测试函数名逐一列出）

| # | 测试函数 | 改法 |
|---|---|---|
| 1 | `test_build_kickoff_probe_forms_match_live_guard` | `staging / "access_log.jsonl"` → `_access_log(staging)` |
| 2 | `test_guard_allows_legal_run_cv_probe_and_logs` | 同上 |
| 3 | `test_guard_with_transcript_path_still_denies_illegal_tool_input` | 同上 |
| 4 | `test_guard_rejects_forbidden_bash_shapes` | 同上 |
| 5 | `test_guard_allows_reading_summary_with_prose_forbidden_tokens` | 同上 |
| 6 | `test_guard_r1_allows_reading_summary_content_with_slash_and_grade_line` | 同上 |
| 7 | `test_guard_r1_excludes_content_role_params_from_path_scan` | 同上 |
| 8 | `test_guard_r3_free_text_params_of_non_write_tools_are_allowed` | 同上 |
| 9 | `test_guard_allows_direct_probe_form_and_logs` | 同上 |
| 10 | `test_probe_help_is_allowlisted_and_documents_all_three_forms` | 同上 |
| 11 | `test_guard_probe_shape_receipts_include_a_minimal_correct_repair` | 同上 |
| 12 | `test_guard_denies_illegal_direct_probe_shapes` | 同上 |
| 13 | `test_guard_allows_bounded_probe_batch_and_logs_every_request_path` | 同上 |
| 14 | `test_access_log_records_the_payload_on_allow_too` | 同上 |
| 15 | `test_access_log_hashes_every_scanned_script` | 同上 |
| 16 | `test_scanned_non_code_files_are_not_logged_as_executed_code` | 同上 |

另新增 1 个辅助函数 `_access_log(staging)`（供以上 16 处复用），以及给 `_E2E_EXEMPT_NAMES`
补了一段注释说明它现在是"vestigial"（access_log.jsonl 搬出去后，`_staging_snapshot` 的
`root.rglob("*")` 根本看不到它，这条 exempt 规则不再会被触发，但留着无害，故未删除）——
**这条是纯注释补充，不改变任何断言逻辑，不算语义翻转**。

### `tests/test_substrate_sweep_policy.py`（1 处）

| # | 测试函数 | 改法 |
|---|---|---|
| 1 | `test_f44_access_log_allow_carries_excerpt_and_executed_code` | `log = staging / "access_log.jsonl"` → `log = access_log(staging)`（本文件内新增的同名辅助函数） |

### 未改动、且旧语义与我的改动无关的既有 xfail 逐条核对（避免被误认为"我打红了它们"）

`tests/test_substrate_sweep_policy.py` 里今天新立的 4 把 `xfail(strict=True)`，回归全程保持 xfail
（一把都没有意外变绿）：

1. `test_f53b_withdrawn_prescan_should_be_denied_by_guard[direct]` —— 旧语义（应然）："guard 应拒绝已撤工具"；
   现状仍是 F-56（我判断不修），**未翻转**。
2. `test_f53b_withdrawn_prescan_should_be_denied_by_guard[request]` —— 同上，**未翻转**。
3. `test_f52b_python_c_root_write_should_be_denied` —— 旧语义（应然）："guard 应拒绝 python -c 写 staging 根 +
   文件不落盘"；这条测的是**一个新建文件名**（`f52b_probe.txt`，之前不存在），不是覆盖已存在的关键文件——
   我的机制②只锁"build 完成时已存在的文件"，机制①（挪日志）也不覆盖这个场景（它写的文件名和日志无关）；
   guard 的判定本批未加值校验，所以两个条件都不成立，**保持 xfail，未翻转**，与 §1.3 的已知限制是同一件事
   在两个不同锁上的体现。
4. `test_f35_cv_evidence_should_reach_attempt` —— F-35，完全不在本单范围内，**未触碰、未翻转**。

---

## 8. 没做完的部分

1. **`setpriv` 能力削减接入 `spawn_command`**（登记为候选 F-59）：能让机制②在这个全 root 容器里真正生效，
   已验证机制本身可行，但改动面（读图器整个会话的启动方式）超出本批时间盒，也无法在不真的拉起一个
   `claude -p` 会话的前提下完整验证不会破坏读图器自身需要的能力。留在 `_lock_down_readonly_surface`
   的 docstring 和本文件里，供下一轮决定是否/怎么接。
2. **F-56/F-57 只做了判断 + 哨兵锁，没有代码改动**——这是"不修"判断本身的正常结果，不是没做完，
   但按主控口径如实列在这里，避免被误读为"本该改代码但漏做了"。
3. **"程序化路径推导"这条旁路**（§1.2 末尾提到的 `os.path.dirname(os.getcwd())` 类构造）
   未被本批关闭——它是一个已存在、和 F-55 无关的 gap，按 2026-08-13 威胁模型不在本次要求的范围内，
   如实记录，未处理。

---

## 9. 回归结果（派工单 §4 点名的四个文件，全部真实跑过，非估计）

```
pytest tests/test_isolation.py tests/test_substrate_sweep_policy.py tests/test_substrate_fix_cleanroom.py -n0 -q
  → 309 passed, 4 xfailed in 591s   （0 failed，恢复断线后重新完整跑过一次，结果一致）

pytest tests/test_substrate_sweep_tools.py tests/test_cv_toolbox.py -n0 -q
  → 76 passed in 57s   （0 failed，0 xfailed——摊 II 已自行把 F-52/F-54 的 xfail 摘掉）
```

`git diff --stat -- src/agent/execution/`：`isolation.py`（126 行改动）+ `guard.py`（56 行改动），
与中和还原前一致，`grep` 确认零 neuter 残留标记。
