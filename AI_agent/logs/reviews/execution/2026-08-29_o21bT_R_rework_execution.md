# 收工报告 · ②-1b-T-R：堵住 case 参数路径穿越 + 三件配套

- **日期**：2026-08-29/30（跨额度窗口两段完成）· **施工**：②-1b-T 原席位续单
- **返工单**：`AI_agent/logs/reviews/request/2026-08-29_o21bT_R_rework.md`
- **裁决依据**：`AI_agent/logs/reviews/verdict/2026-08-29_o21bT_crossreview_glm.md`（APPROVE-WITH-FINDINGS，阻断 0）
- **基线**：`fdb0185`
- **改动文件**（`git diff --cached --numstat`，见 §六）：
  `src/agent/judge/gt_facts_staging.py`（改）·
  `tests/test_gt_facts_staging_case_admission.py`（新增）·
  `tests/test_gt_facts_staging_gate.py`（改，1 条既有断言收窄）·
  `tests/test_gt_facts_staging_sm25.py`（改，+3 条）

---

## 〇、⚠️ 自陈：docstring 引用了一个当时不存在的文件（额度中断留下的半成品）

上一段额度窗口里，我在 `gt_facts_staging.py` 的模块 docstring 里写下了：

> "``tests/test_gt_facts_staging_case_admission.py``'s symlink fixture proves..."

**但那个文件在撞额度上限、被中断的那一刻还不存在**——实现代码（`_validate_case_literal` /
`_facts_staging_dir` 两层校验）已经落地且语法完整，测试夹具文件却还没建。这正是本项目记忆库里点名过的
「设计稿描述了代码没实现的形态」病根的一个变种：**这次是文档引用了尚不存在的验证证据，而不是文档描述了
不存在的功能**——功能是真的（`_validate_case_literal`/两层 containment 检查当时已经在跑），
但 docstring 里"这条声明由某测试证明"这句话在写下的那一刻是假的。

**已修复**：本轮把 `tests/test_gt_facts_staging_case_admission.py` 实际建了出来（15 条测试，
§二），docstring 里那句引用现在指向一个真实存在、真实覆盖该场景的文件。**点名这件事是因为
如果我不说，读这份 docstring 的人会以为它一直都是这样。**

---

## 一、R1（必办）：`case` 参数路径穿越 —— 落地状态

### 1.1 实现（本次复核确认已在树上，语法完整）

`src/agent/judge/gt_facts_staging.py` 新增：

- `FactsStagingCaseError(ValueError)`：公开异常类型（加进 `__all__`，理由：调用方拿着一个自己
  不能完全控制的 `case` 字符串时，需要一个稳定的类型去 catch，不是裸 `ValueError`）。
- `_validate_case_literal(case)` —— **层 1，字面校验**：拒绝空串、拒绝 `"."`/`".."`、
  拒绝含 `/` 或 `\` 的值、拒绝 `pathlib` 认为是绝对路径的值、拒绝不匹配
  `^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$` 的值——**每种失败都带具名原因**。
- `_facts_staging_dir(case)` —— **层 2，解析后 containment**：`.resolve()` 后断言候选路径
  仍是 `_FACTS_STAGING_ROOT.resolve()` 的子孙，不是就响亮拒绝。
- `write_facts_candidate`/`read_facts_candidate` 都在**最先**调用 `_facts_staging_dir(case)`
  （比 `verify_as_signed_reproduction` 还早），恶意/畸形 `case` 不会浪费一次 verify 的算力，
  也不会构造出一个越界的 `Path`。

### 1.2 我自己找到的第三种逃逸——符号链接

返工单点名要求"再找第三种写法"，我找到的不是又一种**字符串**写法，而是一种**字面校验管不到**
的逃逸：**staging 根目录里已经存在一个符号链接**，且它的名字是一个完全合法的 bare token
（比如 `"innocent_case"`——没有分隔符、不是 `..`、不是绝对路径、字符集也合法）。层 1 对着这个
字符串本身无法看出任何问题；只有层 2（`.resolve()` 之后判断是否仍在根下）能抓住它，因为逃逸不在
`case` 这个字符串里，而在**这个字符串所指向的、已经存在的文件系统状态**里。

反过来我还补了一个方向对称的例子：`case="."` 会被层 1 拒绝，但**如果只有层 2**、没有层 1，
`case="."` 解析后落在 `<root>/facts`——这确实还在根**之下**，层 2 不会报错，但这是一次
**静默命名冲突**（所有传 `"."` 的调用者都会落到同一个未加区分的目录，架空了"每个 case 一个子目录"
的设计意图）。这两个例子合起来完整证明了返工单那句「只查字面会被下一种写法绕过，只查解析结果读不出
为什么拒」——**两个方向都各有一个真实反例**，不是空对空的套话。

### 1.3 夹具文件（本轮新建）：`tests/test_gt_facts_staging_case_admission.py`（15 条）

| 覆盖的输入 | 断言 | 自证"不加这处改动本来是绿的" |
|---|---|---|
| `../gt/sm25-L_anchor`（返工单点名 #1） | `FactsStagingCaseError`，具名 `..._contains_a_path_separator` | 先用裸 `pathlib` 拼接证明这条路径**真的**解析到 tmp_path 之外，再断言我们的门拦住它；`unittest.mock.patch` 把 `_facts_staging_dir` 换回旧的无校验版本重放该测试体 → 实测 `Failed: DID NOT RAISE` |
| `/tmp/evil`（返工单点名 #2） | `FactsStagingCaseError`，具名 `..._contains_a_path_separator` | 先证明 `Path("/a")/"/b" == Path("/b")`（staging 前缀被整体吞掉），再断言门拦住；同样的 patch 重放 → `Failed: DID NOT RAISE` |
| `""` / `"."` / `".."` / `"a/../../x"` / Windows 分隔符 `"a\\evil"` / `"C:\\evil"` / 内嵌 NUL `"a\x00b"` | 各自具名的 `FactsStagingCaseError` | `test_r1_edge_tokens_would_not_have_been_caught_by_pathlib_itself` 实测：这些输入**裸 `pathlib` 拼接全部不报错**（连内嵌 NUL 都不报错——`Path.exists()` 会把 OS 层错误吞成静默 `False`），证明"没有我们的门，这些输入会被默默接受" |
| **符号链接逃逸**（自己找到的第三种，§1.2） | `FactsStagingCaseError`，具名 `..._escapes_root`，消息里带真实落点路径 | 先证明层 1 单独放行（`_validate_case_literal` 不报错），再证明只加层 2 才拦住；额外用**真实公开 API**（`write_facts_candidate`/`read_facts_candidate`，不是内部函数）重放一遍，并断言 `outside` 目录里**没有任何文件被写入** |
| `case="."`（反向例子，§1.2） | 层 2 单独放行（落在 `<root>/facts`，仍是根的子孙），层 1 拒绝 | 用 `pytest.MonkeyPatch.context()` 临时禁用层 1，实测层 2 确实放行；恢复层 1 后确认被拒 |
| `sm25-L_anchor`（合法 case） | 写得进、读得出，哈希一致 | 不误伤的正向对照 |
| 对**真实**（非 mock）staging 根跑两个具名攻击 | 真实 `case_tests/test_baseline/gt/` 目录树跑前跑后一致 | 证明这不只是 tmp_path 隔离环境里的理论，真实仓库路径下同样被拦 |

跑测：
```
$ python -m pytest -p no:cacheprovider -q tests/test_gt_facts_staging_case_admission.py
15 passed in 10.55s
```

---

## 二、R2：真实 sm25 形状的篡改回归固化（`tests/test_gt_facts_staging_sm25.py` +3）

### 2.1 选取理由（判据：它声称覆盖的每种量各自有没有被真的量到，⛔ 不是凑够三条）

复核方在真实 sm25 形状上补了 20 维矩阵（18 红：14 个 `AsSignedReproductionError` / 4 个
`ValidationError`）。这个文件在返工前**已有**两条真实数据篡改测试
（`test_3_a_hand_tampered_integer_in_the_staged_as_signed_is_caught` /
`test_3_hand_tampering_a_revisions_action_moves_as_signed_and_its_hash`），但它们都：
（a）只碰 `as_signed` 或 `revisions`，**从没碰过 `as_measured.json`**；
（b）都是**在内存里**构造篡改对象、直接调用 `verify_as_signed_reproduction`，**从没有一条
真的把字节写到磁盘上、再走 `read_facts_candidate` 这个真实入口**——而 `read_facts_candidate`
正是 ②-1c 将来会调用的那个函数，也正是本单 R2 的原始验收对象。

所以我没有"挑三条看起来能过的"，而是先问「现在这个文件声称测了什么量、实际测到了什么量」，
找出三个**互不重叠**的缺口，各补一条：

1. **`as_signed.json`，磁盘篡改，走 `read_facts_candidate`**——补的是"内存篡改 vs 磁盘篡改+真实
   入口"这个缺口（既有测试只覆盖前者）。
2. **`as_measured.json`，磁盘篡改**——补的是"这份文件在这个测试文件里 0 覆盖"这个缺口。
   选的维度是翻转 `source_dxf_sha256` 一个十六进制字符（`Hex64` 模式本身还合法，不会被 schema
   拦，只会被 `derive_as_signed` 自己的哈希链路第一步—— `as_measured_content_sha256` 交叉
   校验——拦住），确保测的是"哈希链路"这个机制，不是"字段格式"。
3. **`revisions.json`，磁盘篡改成 schema 层就拒绝**——补的是复核方 F-2 的**头条发现**：
   18 红里有 4 个根本没走到我们自己的 `verify_as_signed_reproduction`，而是被 `pydantic`
   在 `model_validate_json` 阶段直接拦下（这个模块的 docstring 从没提过这第二道防线，
   这份测试文件此前也是 0 覆盖）。做法：把一个 DXF handle 改成小写——`DxfHandle` 的模式是
   `^[0-9A-F]+$`（大写-only，`gt_schema.py`），小写立刻不匹配。

三条覆盖三个**不同的文件** × 两种**不同的失败机制**（我们自己的复现门 / pydantic 的 schema
校验），而不是"三次同一种手法换个字段"。

### 2.2 三条各自的"本来是绿的"实测

用 `unittest.mock.patch.object(gt_facts_staging, "verify_as_signed_reproduction", lambda *a,**k: None)`
砍掉 R2 的复现门后重放：

```
test_r2_on_disk_as_signed_tamper_is_caught_through_the_real_read_path
    -> 砍掉 verify 后: Failed（DID NOT RAISE）—— 证明这条测的确实是 R2 这道门
test_r2_on_disk_as_measured_hash_break_is_caught
    -> 砍掉 verify 后: Failed（DID NOT RAISE）—— 同上
test_r2_on_disk_revisions_schema_break_is_caught_before_verify_even_runs
    -> 砍掉 verify 后: 仍然 raise —— 证明这条测的是 pydantic schema，和 verify 无关
       （机制归因验证：这条测的不是"我们加的东西"，是"复核方指出的、一直都在但没人固化过的
       第二道防线"，所以它对 verify 的存废不敏感，这正是它该有的行为，不是 bug）
```

跑测：
```
$ python -m pytest -p no:cacheprovider -q tests/test_gt_facts_staging_sm25.py
8 passed in 11.64s
```
（5 条既有 + 3 条新增）

---

## 三、R3：`.tmp` 孤儿清理 —— 落地状态

`_write_atomic` 加了 `try/except BaseException`：`write_bytes` 成功但 `replace` 之前若抛出
任何异常（权限错误、磁盘满、Ctrl-C），主动 `tmp.unlink(missing_ok=True)` 再重新抛出。

**如实声明剩余边界**（不是隐瞒，是主动写在 docstring 和这里）：这挡不住**进程被硬杀**
（SIGKILL / 断电）——那种情况下没有任何 Python 级 `except` 能跑，孤儿 `.tmp` 会留下来。
对这个残余边界的处理是**两步**：

1. `write_facts_candidate` 在每次真正写入前调用新增的 `_sweep_stale_tmp_orphans(out_dir)`，
   清掉**上一次**遗留的 `*.json.tmp`——即便一次崩溃没能自己清理，下一次对同一目录的写入会清理它。
2. **声明为无害**（而不是假装已被彻底清干净）：`read_facts_candidate` 只打开
   `as_measured.json`/`revisions.json`/`as_signed.json` 三个具名文件，从不 glob、从不打开
   `*.tmp`——一个孤儿 `.tmp` 对读侧完全不可见，不会被误当成真数据读出。

本轮**未新增**针对 R3 的专门夹具文件（未在返工单验收项里被点名要"各自有夹具"，只要求"清掉，或
显式声明为已知残留并说明为什么无害"——两者本轮都做了：清理 best-effort + 声明剩余边界无害）。

---

## 四、R4：过强表述改写 —— 落地状态

模块 docstring 的 R3 段落原文声称"未来的晋升实现在类型层没有拷目录这条路"。已改写为
（原文见 `src/agent/judge/gt_facts_staging.py` "## R3" 段落）：

> "it raises the *discoverability* bar, not an *accessibility* one... ``gfs._facts_staging_dir(case)``
> followed by ``shutil.copytree`` is THREE LINES and works today... A sufficiently motivated
> ``promote_gt_v3`` can reach the private helper, or skip this module entirely and hardcode the
> literal staging path string, or... walk straight through R1's own case-name admission gate..."

并记下了 GLM 给的更结构性正解（**本单不实现**）：把 `verify_as_signed_reproduction` 同构地挂到
**答案根 `gt/<case>/facts/` 的读侧**——"出口全检"而不是"入口收窄"，因为出口门不关心字节是怎么
到那儿的（拷目录、硬编码路径、还是绕过 R1 的写入），只看现在是否复现；入口收窄再怎么收紧也只能
枚举"想到的进来的路"。这段记录直接写进了 docstring 的"## R3"段落末尾，供 ②-1c / 晋升接缝单直接
引用，不需要重新发现。

---

## 五、跑测声明（前台，⛔ 未起后台等待器）

受影响子集（`affected_tests.py` 判定）：
```
$ python scripts/tool_scripts/affected_tests.py --changed src/agent/judge/gt_facts_staging.py \
    tests/test_gt_facts_staging_sm25.py tests/test_gt_facts_staging_gate.py \
    tests/test_gt_facts_staging_case_admission.py
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q tests/test_gt_facts_staging_case_admission.py \
    tests/test_gt_facts_staging_gate.py tests/test_gt_facts_staging_sm25.py \
    tests/test_gt_revisions_and_as_signed.py
```
实跑（前台，单次命令跑完，未起后台等待器）：
```
$ python -m pytest -p no:cacheprovider -q tests/test_gt_facts_staging_gate.py \
    tests/test_gt_facts_staging_sm25.py tests/test_gt_facts_staging_case_admission.py \
    tests/test_gt_revisions_and_as_signed.py
70 passed in 14.34s
```

逐文件测试数变化：

| 文件 | 返工前 | 返工后 | 变化 |
|---|---|---|---|
| `tests/test_gt_facts_staging_case_admission.py` | 0（不存在） | 15 | **+15**（新文件） |
| `tests/test_gt_facts_staging_sm25.py` | 5 | 8 | **+3** |
| `tests/test_gt_facts_staging_gate.py` | 7 | 7 | 0（1 条既有断言改写，未增删测试函数） |

**全量未跑**（按返工单：权威门归主控，本单不占全量时间）。

---

## 六、`git diff --cached --numstat` 原文

```
185	27	src/agent/judge/gt_facts_staging.py
243	0	tests/test_gt_facts_staging_case_admission.py
24	4	tests/test_gt_facts_staging_gate.py
97	1	tests/test_gt_facts_staging_sm25.py
```

（`git status --porcelain`（暂存前）：
```
 M src/agent/judge/gt_facts_staging.py
?? tests/test_gt_facts_staging_case_admission.py
 M tests/test_gt_facts_staging_gate.py
 M tests/test_gt_facts_staging_sm25.py
```
只 add 了这四条明确路径，没有用 `git add -A`。）

---

## 七、⛔ 不做清单核对（如实核过，未越界）

- 未碰 `promote_gt_v3` / F-128 / F-132：`git diff fdb0185 --stat` 只列出上面 4 个文件。
- **`AXIS_SNAP_MAX_DEVIATION_M` 一个字节未变**：`git diff fdb0185 -- src/agent/judge/tarch_normalize.py src/agent/judge/as_measured.py` 输出 **0 行**。
- 签字件哈希不变：
  `request.json` = `e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396df`，
  `request_as_measured.json` = `55305752145f3f44cf5c895956d5095c9ee0784f373c7380545e66685d0a7796`
  ——两者都不在本轮改动文件列表里。
- 未实现"出口全检"（记在 docstring 里，未写代码）；未碰 `AnswerCompiler` / 出模形式 / correction 侧；未重签任何答案。

---

## 八、最薄弱的一处

`_facts_staging_dir` 的层 2（resolved-path containment）依赖 `Path.resolve()` 在**当前调用时**
去 stat 文件系统——如果 `case` 目录在 `_facts_staging_dir` 校验通过之后、`_write_atomic` 真正
写入之前的这个极短窗口内，被替换成一个指向别处的符号链接（TOCTOU：check-then-use 竞态），
校验时看到的是"安全"路径，实际写入时文件系统状态可能已经变了。这个窗口在单进程、单线程、
无外部并发写手的当前使用场景下（本单没有引入任何多进程/多线程访问 staging 目录的场景）不构成
实际风险，但如果未来 ②-1c 或晋升流程引入并发写入同一 staging 目录，这个假设需要重新审视——
本单没有加锁或原子性更强的目录级保护，因为返工单的范围是"字符串/路径本身的穿越"，不是
"并发竞态"，但这是我认为除了返工单已点名的三件事之外，最值得记一笔、留给下一单的边界。

---

**commit**：`93bdc33`（`08.29_O21bTR_case穿越准入门加真实形状回归锁定`）。
