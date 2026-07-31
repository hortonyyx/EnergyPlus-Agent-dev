# 执行日志 · 探针人体工学（识图崩盘归因候选 #1）

> 施工席（主控 Opus 5 派工）· 2026-07-31
> 依据 = [派工单](../request/2026-07-31_probe_ergonomics_dispatch.md)
> 基线 = `bd7af40`（1917 passed / 10 xfailed / 0 failed，主控已独立复核）
> 交付 = `ec70982` `7.31_ProbeDirectArgumentForm` + `9a1fd6f` `7.31_ProbeDirectFormLockHardening`

---

## 0. 结论速览

| 项 | 状态 |
|---|---|
| P1-1 守卫支持一次调用带参 | ✅ 落地（「恰好四个 token」→ 严格参数解析器） |
| P1-2 wrapper 侧对齐 | ✅ 落地（折成同一 request 形状 → 复用 `_request_to_argv`，落点策略仍只有一处） |
| P1-3 必须新增的锁 | ✅ 全部落地（含 E2E 真跑 helper + 整树 diff） |
| P1-4 directive 同步 | ✅ 落地 |
| 全仓 | **1951 passed / 10 xfailed / 0 failed**（基线 1917 → +34，零回归） |
| DENY→ALLOW 差分 | 相对本单基线 `bd7af40` = **2 处，均为本单授权的直接形式**；无未授权项 |
| neuter 自查 | **12 处定点破坏，全部真变红**；其中 **2 把假锁由本席自查发现并修到夹具层** |
| 骨架偏差 | **0 处自行改动**；1 处骨架未覆盖的边界按骨架字面推导补齐，见 §6 review-ask |

---

## 1. 改了什么

### P1-1 · `guard.py`

**删掉的规则**：`if len(parts) != 4: return False, "python command must be exactly: …"`。

**换上的规则**：`_parse_direct_probe_args(parts[2:], root)`，逐条 fail-closed：

1. `argv[0]` basename ∈ {`python`, `python3`}（未动）；`argv[1]` 必须恰好是
   `tools/run_cv_probe.py`（绝对路径 resolve 后等于 staging 内该文件；未动）。
2. 其余必须成对 `--key value`。**裸位置参数 / 重复 key / `--key` 后缺值（argv 结束，
   或值位坐着另一个 `--key`）一律 DENY**——解析器不猜哪个 token 是什么，歧义即拒。
3. key 归一化成 request JSON 的下划线拼法后，必须落在 `PROBE_DIRECT_PARAM_KEYS` 内，
   **未知即 DENY**。该元组是从 `scripts/tool_scripts/cv_probe.py` 的**每个 subparser
   逐个读出来的**（枚举依据写在代码注释里，并由 `test_direct_param_allowlist_matches_cv_probe_options`
   钉住不许漂移）：`_common` 六个 + `wall_line_profiler` 一个 + `px_m_calibrator` 三个 +
   `window_cc_detector` 十个 + `overlay_logger` 一个 + 两个 prescan 五个 + `--tool` 本身 = 27。
   归一化在白名单查表**之前**发生，所以 `--out-dir` 与 `--out_dir` 是同一个枚举 key、
   拿到同一份角色处理，不存在「换个拼法就绕过角色」的写法。
4. `--tool` 与 `--image` 必填。
5. 每个 value 走 **`_validate_probe_params`——与 request JSON 完全同一个函数**：
   `_lexical_check` 无条件；输出角色 key（`REQUEST_OUTPUT_ROLE_KEYS = ("out_dir",)`）
   走 `_path_arg` + **`_check_output_target`（R2-2 的既有实现，未写第二份）**。
6. `COMPOUND_TOKENS` 检查未动，仍对整串生效（`_check_bash` 顶部，早于任何解析）。
7. `python -c` 仍禁，且**改为具名早查**（`parts[1] == "-c"`）——原先它靠 `len(parts) != 4`
   顺手拦掉（r2 复审已登记该分支不可达），现在按自己的理由拒，理由文案也对靶。

**顺带的一处收紧（非骨架要求，理由见下）**：新增 `PROBE_PATH_ROLE_KEYS =
("image", "anchors_json", "candidates_json")`，path 角色**按 key 名判定**而不是靠
`_looks_like_path` 的字符串外形。原因是骨架 P1-3 明写「直接带参、`--image` 越界
（**含裸无后缀 symlink**）⇒ DENY」，而 `_looks_like_path("escape")` 返回 False
（无斜杠、无后缀、不以 `.` 开头）⇒ 该 value 根本到不了 `_path_arg`。本席实测到这一点：

```text
（修前）python tools/run_cv_probe.py --tool crop_zoom --image escape --out-dir out/cv
        → rc=0 ALLOW      （<staging>/escape -> /etc/passwd）
（修后）→ rc=2  path escapes staging: escape
```

这正是 R2-1 在工具参数侧关掉的那个洞，在探针参数侧原样残留。因为两种调用形式
**共用** `_validate_probe_params`，修好之后 request JSON 侧的同一形状也一并关上
（＝一处 ALLOW→DENY 收紧，见 §4）。

### P1-2 · `run_cv_probe.py`（staging 内的 wrapper）

`main()` 判形式：命中 `--request` 走**原样不动**的老路径（同一个 argparse、同一个
required 旗标、同样的报错）；否则 `_direct_to_request(argv)` 把直接形式**折成同一个
request 形状**，之后**两种形式都走 `_request_to_argv`**。

⇒ 落点策略（tool 白名单 / `PATH_KEYS` 解析 / `OUTPUT_ROLE_KEYS` → `_resolve_output`
→ `guard.writable_root`）**只有一处**，没有第二份可漂移。R3-2 建立的共享可写根实现未动。

`--no-cc` 是 cv_probe 的 `store_true` 旗标（不带值），而骨架要求严格成对 ⇒ 直接形式
写作 `--no-cc true`，由 `BOOLEAN_FLAG_KEYS` 在此处折回旗标，复用 `_request_to_argv`
既有的 bool 分支。`true`/`false` 以外的值报错。

**per-参数白名单没有在 wrapper 里复制第二份**：cv_probe 自己的 argparse 会拒绝其
subparser 未声明的选项，而且是**逐 tool** 判的，比一张平表更细；把守卫那 27 个 key
抄进第二个文件只会制造漂移面。

### P1-4 · `reader_directive.md`

§2 改成先给**一次调用**的三条确切样例（`wall_line_profiler` / `crop_zoom` /
`px_m_calibrator`），并明写「你**不需要**先写请求文件；量一次应该只花一次调用，多量」；
随后保留 `--request` 形式作为复杂请求的备选。§7 的「invoked as exactly four tokens」
同步改成两种形式各给一行。

⚠️ **该文件被 `.gitignore` 的 `20*_*/` 规则吞掉、整个实验目录零文件在版本控制内**
（`git check-ignore -v` 实证）。本席**未 force-add**（无授权，且根目录/gitignore 纪律
是本项目的活议题）。磁盘上已改好，复验轮直接可用；是否入库请主控裁定。

---

## 2. 跑测

| 轮次 | 命令 | 结果 |
|---|---|---|
| 受影响子集 | `python scripts/tool_scripts/affected_tests.py --changed src/agent/execution/isolation_templates/guard.py src/agent/execution/isolation_templates/run_cv_probe.py tests/test_isolation.py` → `SCOPE: SUBSET` → `pytest -q tests/test_isolation.py` | 149 passed |
| 交付前全仓 | `python -m pytest -q` | **1951 passed / 10 xfailed / 0 failed**（264.35s） |

**净增可机械核死。** `tests/test_isolation.py` 收集数在同一副本上实测
`bd7af40` = **115** → `9a1fd6f` = **149**，差 **+34**；全仓 1917 → 1951 也是 **+34**
（⇒ 本单一个测试文件之外零改动、零回归）。34 逐项拆开：

```text
 1  test_staging_run_cv_probe_direct_form_smoke
 1  test_guard_allows_direct_probe_form_and_logs
 1  test_direct_and_request_forms_produce_identical_output
19  test_guard_denies_illegal_direct_probe_shapes[...]        （P1-3 负锁矩阵）
 7  test_guard_direct_form_does_not_loosen_bash_boundary[...] （旧 Bash 边界仍在）
 1  test_direct_param_allowlist_matches_cv_probe_options      （白名单防漂移）
 3  test_e2e_direct_form_hook_then_helper_changes_only_writable_tree[...]
 1  test_wrapper_direct_form_independently_refuses_outside_output
```

零测试被删、零断言被弱化：`tests/` 的删除行只有被常量替换的两处夹具字面量、
两处参数化列表改成具名 `ids` 的重排，以及
`test_guard_rejects_symlink_and_request_paths_outside_staging` 结尾**新增**（非替换）
的裸 symlink 段。

⚠️ 按派工单 §3.5 提醒，`tests/test_gt_discipline.py` 的词法门结构上进不了子集，
本轮**跑了全仓**，未省。

---

## 3. neuter 自查表（12 处定点破坏，全部真跑）

破坏一律在 `/tmp/probeneuter`（`git clone` 的独立副本，`9a1fd6f`）上打，每次
`git checkout -- .` 复位；跑完副本 `git status` 为空。命令
`python -m pytest tests/test_isolation.py -q -n auto`。

| # | 定点破坏（生产码） | 红数 | 真实变红测试名 |
|---|---|---|---|
| N1 | `_parse_direct_probe_args`：`if key not in PROBE_DIRECT_PARAM_KEYS` → `if False` | 1 | `test_guard_denies_illegal_direct_probe_shapes[unknown_key]` |
| N2 | 裸位置参数不再 raise，改 `index += 1; continue` | 1 | `test_guard_denies_illegal_direct_probe_shapes[bare_positional]` |
| N3 | 重复 key 检查 `if key in seen` → `if False` | 1 | `test_guard_denies_illegal_direct_probe_shapes[repeated_key]` |
| N4 | 缺值检查砍掉「值位是另一个 `--key`」那半条 | 1 | `test_guard_denies_illegal_direct_probe_shapes[missing_value_taken_from_next_key]` |
| N5 | 必填 `--tool`/`--image` 检查 → `missing = []` | 3 | `…[missing_image]`、`…[missing_tool]`、`…[no_arguments_at_all]` |
| N6 | 直接形式的 value 不进共享校验（`return []`） | 9 | `test_e2e_direct_form_hook_then_helper_changes_only_writable_tree[outside_reference-reference-False]`、`[outside_tools-tools-False]`、`test_guard_allows_direct_probe_form_and_logs`、`…[candidates_json_bare_escaping_symlink]`、`…[image_bare_escaping_symlink]`、`…[image_slashed_escaping_symlink]`、`…[out_dir_reference]`、`…[out_dir_tools]`、`…[out_dir_underscore_spelling]` |
| N7 | `PROBE_PATH_ROLE_KEYS = ()`（退回字符串外形判定） | 3 | `…[candidates_json_bare_escaping_symlink]`、`…[image_bare_escaping_symlink]`、**`test_guard_rejects_symlink_and_request_paths_outside_staging`** ← 共用实现的证明：request 侧同时失守 |
| N8 | 共享校验里 `_check_output_target` 结果不看（`if False`） | 14 | 直接形式 E2E 两条 + request 形式 E2E 两条 + `…[out_dir_*]` 三条 + `test_guard_denies_request_output_dir_outside_writable_root` 全 7 参数 ← **两种形式一起红 = 确实是同一份实现** |
| N9 | 白名单静默丢掉一个真选项（`"axis"`） | 1 | `test_direct_param_allowlist_matches_cv_probe_options` |
| N10 | wrapper 不再真跑 cv_probe（`return 0`） | 5 | `test_direct_and_request_forms_produce_identical_output`、`test_e2e_direct_form_…[inside_out-out/cv-True]`、`test_e2e_hook_then_helper_…[inside_out-out/cv-True]`、`test_staging_run_cv_probe_direct_form_smoke`、`test_staging_run_cv_probe_smoke` ← **反空锁命脉**：不执行 helper 就红 |
| N11 | wrapper `if key in OUTPUT_ROLE_KEYS` → `if False` | 3 | `test_wrapper_direct_form_independently_refuses_outside_output`、`test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged`、`test_wrapper_refuses_when_the_writable_root_is_a_symlink` |
| N12 | wrapper 静默丢弃 `--sidecar-name` | 2 | `test_direct_and_request_forms_produce_identical_output`、`test_staging_run_cv_probe_direct_form_smoke` |

### 3.1 ⚠️ 本席自查出的两把假锁（第一轮 neuter 时红数为 0）

派工单 §3 明写「本批至今已抓到两把假锁 —— 对自己的锁用同样怀疑」。第一轮 12 个 neuter
里 **N4 与 N12 各得 `148 passed`，即零红**，两条都是我自己写的锁绿得不对靶：

| 假锁 | 为什么绿 | 修法 |
|---|---|---|
| N4 `missing_value_before_next_key` = `--tool crop_zoom --image --out-dir out/cv` | 该形状 token 数为**偶数**。摘掉「值位是另一个 `--key`」这半条后，配对只是整体错位，`out/cv` 变成裸位置参数 ⇒ **仍被另一条规则拒**，断言照样成立。这条锁从来没有钉住它声称钉住的那半条检查。 | 新增 `missing_value_taken_from_next_key` = `--tool crop_zoom --image --out-dir`（无余项，摘锁后真 ALLOW）。旧形状保留为独立用例 `missing_value_shifts_the_pairing`，它本身也是应拒形状。 |
| N12 直接形式夹具用 `--sidecar-name 001_crop_zoom` | 该值**恰好等于** `allocate_sidecar_path` 自动编号产生的第一个名字 ⇒ wrapper 把这个参数整个丢掉，落点文件名不变，5 把相关锁全绿。**与本批已抓的两把假锁同型（夹具形状恰好自洽）。** | 夹具改 `042_crop_zoom`（自动编号永远产不出），并抽成 `_DIRECT_SIDECAR_NAME` / `_DIRECT_SIDECAR_REL` 常量。直接形式那串参数里其余每一个都各自承重：`--image`/`--out-dir` 是 cv_probe 的 `required=True`，`--bbox` 缺了 `crop_zoom` 直接报错，`--tool` 缺了 wrapper 显式 raise。 |

修完（`9a1fd6f`）**十二处 neuter 全部真变红**，即上表。

---

## 4. DENY→ALLOW 差分（派工单 §3.2）

方法：在**同一个生产 `build_isolation_workspace` 产出的真 staging** 内，把同一份
payload 矩阵**分别喂给两个版本的真 `guard.py` 子进程**（老版经
`git show <ref>:src/agent/execution/isolation_templates/guard.py` 取出，放在 staging
根下当 `guard_base.py`，`_staging_root()` 解析一致）。矩阵 **70 个形状**：
复审方 §3 的八条安全性质 + §3.1 的十三处收紧 + §3.2 的十四条逃逸面 + Bash 各形状 +
本单新增的直接形式 17 条。脚本与逐行结果留在本轮工作痕迹里。

### 4.1 相对**本单基线** `bd7af40`（＝只含本单改动）

```text
DENY -> ALLOW : 2
    + D01 direct legal          python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv --bbox 0,0,20,20
    + D02 direct prescan legal  python tools/run_cv_probe.py --tool prescan-plan --image case_data/1f_view.png --out-dir out/ps --no-cc true
ALLOW -> DENY : 1
    - B05 request 形式 image = 裸无后缀越界 symlink   [path escapes staging: escape]
unchanged     : 67   (deny/deny=55, allow/allow=12)
```

⇒ **两处 DENY→ALLOW 全部是本单授权的探针直接形式，没有任何第四条。**
唯一的方向性变化之外是一处收紧（§1 说明的 path 角色按名判定）。

### 4.2 相对**改造前基线** `f98d248`（派工单点名要重跑的那一份）

```text
DENY -> ALLOW : 8
    + D01 direct legal                      ← 本单授权
    + D02 direct prescan legal              ← 本单授权
    + W09 Write out/summary.md（prose 含 grade line / 2026/07/31 / ~）   ← r2 授权（复审方 §3.1 唯一那处）
    + R13 TodoWrite activeForm "Marking the grade line on North"        ← r3 R3-1 授权
    + R14 TodoWrite activeForm "Tracing 1f walls..."                    ← r3 R3-1 授权
    + R15 Grep pattern "wall_..[0-9]"                                   ← r3 R3-1 授权
    + R16 Grep pattern "z ~ 0.0"                                        ← r3 R3-1 授权
    + R17 未知工具 description "Measuring wall thickness..."             ← r3 R3-1 授权
ALLOW -> DENY : 16
    - B02 request out_dir=tools · B05 request image 裸越界 symlink
    - W01 Write tools/run_cv_probe.py · W02 guard.py · W03 MANIFEST.json · W04 isolation_settings.json
    - W05 reference/worked_example_plan.json · W06 case_data/1f_view.png · W07 staging 根散件
    - W08 out/to_tools/run_cv_probe.py（嵌套 symlink） · W12 Edit tools/cv_probe.py
    - W13 NotebookEdit tools/x.ipynb · W14 NotebookEdit 双 target key 遮蔽 · W15 Write 无 target key
    - R06 Read 裸无后缀越界 symlink · R12 未知 key 携带越界路径
unchanged     : 46   (deny/deny=40, allow/allow=6)
```

**说明（如实登记，不含糊）**：复审方在 `85b6695` 上量到的是「1 处 DENY→ALLOW」，
那是 **r3 施工之前**的状态。r3 的 R3-1 明令把识图子代理实际会用到的自由文本参数
按名移进 `CONTENT_ROLE_KEYS`，那一批本身就产生了 5 处相对 `f98d248` 的 DENY→ALLOW
（上表 R13–R17），**均为主控在 r3 返工单里明写授权、且带正例锁的项**。
本单新增的只有 D01/D02 两条。§4.1 那份「相对本单基线」的差分正是为了把这件事切干净，
避免把上一批的授权项算到本单头上、也避免本单的项藏在上一批的账里。

ALLOW→DENY 我量到 16 条、复审方当时是 13 条：差额来自我的矩阵是超集
（多了 W15「Write 无 target key」、R12「未知 key 携带越界路径」、以及本单新增的
B05），并且复审方列表里的 `skills/**/guide.md`、`src/**/tools.py` 两条在本 case 的
staging 里不存在，我换成了同性质的 `reference/` 与 `case_data/` 路径。
**方向一致：守卫净效果更严。**

---

## 5. 范围与受保护资产

本单触碰文件全集（`git diff --stat bd7af40..HEAD`）：

```text
src/agent/execution/isolation_templates/guard.py
src/agent/execution/isolation_templates/run_cv_probe.py
tests/test_isolation.py
```

外加**未入版本控制**的 `AI_agent/logs/experiments/2026-07-31_sm24_e2e_retry/reader_directive.md`
（P1-4，见 §1）与本执行日志。

- `src/agent/judge/**`、`case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md`
  **一个都没碰**：`git diff --quiet bd7af40..HEAD -- src/agent/judge case_tests/test_baseline/gt AI_agent/CLAUDE.md` → exit 0。
- `src/agent/execution/isolation.py` **未改**（共享实现 R3-2 已在 guard 里，本单不需要动它）。
- 破坏性实验全部在 `/tmp/probeneuter` 与 `/tmp/claude-0/**` 的临时 staging 内；
  主工作树除源码/测试编辑外零写入。
- `tests/` 的**删除行只有被替换的夹具常量与两处参数化的重排**，无任何断言被弱化、
  无测试被删。

---

## 6. Review-ask（给主控）

1. **骨架未覆盖的一处边界，我按骨架字面推导后补齐了，请复核判定**：骨架 §2 第 4 条写
   「path 角色的 key 再走 `_path_arg`」，但现码里「谁是 path 角色」在 request 路径上
   是由 `_looks_like_path` 的**字符串外形**决定的；而骨架 P1-3 的验收表又明写
   `--image` 越界「**含裸无后缀 symlink**」必须 DENY——外形判定给不出这个结果（实测见 §1）。
   我的取法是**按 key 名判定 path 角色**（`PROBE_PATH_ROLE_KEYS`），并因共用实现而
   顺带收紧了 request 侧同一形状。这**不是**放松，但它比骨架字面多做了一步，且改到了
   老路径的行为（一处 ALLOW→DENY）。若主控认为 request 侧应保持字节不动，回退方法是
   给 `_validate_probe_params` 加一个只对直接形式生效的开关——但那样两条路径就不再是
   「完全相同的校验」了，与骨架 §2 第 4 条冲突，所以我没这么做。
2. **`--no-cc` 的成对写法是我的判断**：骨架要求严格成对，而它在 cv_probe 里是不带值的
   `store_true`。我取「直接形式写 `--no-cc true`，wrapper 折回旗标」，保住了严格成对
   这条硬规则、也没有丢功能。另一条路是直接形式干脆不支持该参数（要用就回 `--request`），
   我认为更差（prescan 是本轮 directive 里的常规动作）。
3. **wrapper 侧没有复制守卫的 27 key 白名单**，理由是 cv_probe 的 argparse 已经逐 tool
   拒绝未声明选项、比平表更细，抄一份只会制造漂移面。若主控要求 wrapper 也显式持有
   白名单（纵深防御口径），这是一个小改动，但请一并指定用哪一份作为权威、以免出现
   第二处策略。
4. **`--tool` 的取值没有在守卫里校验**（不检查是否属于 `ALLOWED_TOOLS`）。理由：它不是
   路径、逃不出边界，而 wrapper 的 `_request_to_argv` 已经拒绝未知 tool；把 tool 白名单
   也抄进 guard 会是第二处策略。骨架未要求，故未做，如实登记。
5. **P1-4 的目标文件不在版本控制内**（`.gitignore` 的 `20*_*/`）。我未 force-add。
   这与本项目已登记过三次的「关键输入不在 git 里」是同一族问题——复验轮读的是磁盘上
   这份，没问题；但它无法随本单的 commit 一起被审、也无法证明主控跑的就是我改的那份。
   请主控决定是否入库。
6. **复验轮的必读产物**：r2 复审 MINOR-2 的第三条出口（「跑完必须读 `access_log.jsonl`
   统计守卫拒绝次数」）仍然成立，本单额外给它加了一个直接读数——直接形式在 log 里的
   `reason` 是 `allowed run_cv_probe direct arguments`（与 request 形式的
   `allowed run_cv_probe request` 区分开），所以**「这一轮到底有没有用上一次调用」
   可以从 access log 直接数出来**，不必靠执行者自述。建议主控在复验轮 report 里把
   这两个计数与 07-30 的 19/8 并排列出。
