# 复验裁决 · 硬隔离脚手架批 r2（返工验收）

> 复验方 = 独立验证审阅席（主控 Opus 5 派工）· 2026-07-31
> 被验对象 = `40e1470` / `141f019` / `e3f3a3a` / `05ae23e` / `eb6c9e2` / `2676e04` / `5ecebb9` / `85b6695`
> 依据 = [返工单 r2](../request/2026-07-31_isolation_scaffold_rework_r2.md) · [sol 裁决书](2026-07-31_isolation_scaffold_sol.md) · [执行日志](../execution/2026-07-31_isolation_scaffold_glm.md) · [派工单](../request/2026-07-31_isolation_scaffold_construction_dispatch.md)
> 纪律：**只审不修**（主工作树零写入，仅跑只读 pytest）；全部破坏性实验在 `/tmp/isoverify/repo`（`git clone` 的独立副本，detached `85b6695`）进行，每次 `git checkout -- .` 复位并核 `git status` 为空；**未写 `case_tests/test_baseline/gt/**`**。

---

## 结论：APPROVE-WITH-CHANGES

**0 BLOCKER / 0 MAJOR / 2 MINOR / 3 NIT。**

R2-1 … R2-6 六项**全部成立**（逐项活体证据见 §1）。施工方执行日志里的 neuter 自查表经我独立重跑，**十处定点破坏的红数与真实变红测试名逐条吻合、零夸大**（§2）。§2A 八条安全性质全部仍为 deny（§3）。全仓 **1908 passed / 10 xfailed / 0 failed**，与施工方声称一致，`+27` 的净增可被机械核死（§5）。批次范围干净：`src/agent/judge/**`、`case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md` 三处零触碰，受保护答案树聚合 hash 逐字相同（§6）。

不给纯 APPROVE 的两条理由（均非阻断，但都需主控裁定）：

1. **R2-2 的死骨架第 2 条「wrapper 侧做同一约束、两处策略必须一致」只闭了一半** —— wrapper 的可写根定义仍是 `resolve(strict=False)`，没有同步 R2-3 给 guard 的「钉死真实目录」语义。活体实证：预置 `out -> tools` 后，绕过 hook 直接跑 helper **真在 `tools/**` 下落了 6 个条目**。生产路径不可达（guard 先 fail-closed，且子代理造不出 symlink），故评 MINOR 而非 MAJOR。
2. **R2-1 的 fail-closed 缺省把 F-4 的可用性缺陷原样搬到了「非 content 角色的自由文本参数」上** —— 活体实证 `TodoWrite` 的 `activeForm` 写「…」或「grade line」当场被拒、`Grep` 的 `pattern` 含 `..`/`~` 被拒。这**完全是返工单自己钉的硬要求**（「其余一律按 path 处理」），施工方照做无误，**且相对改造前基线 `f98d248` 不是回退**；但本批存在的理由正是消除这类摩擦，而复验轮马上要重跑识图，主控须在跑之前拍这一条。

---

## 0. 复验方法与环境

```text
主工作树 HEAD      85b66955ec3cd3933e6aae286033c9d6253e65b4
改造前基线         f98d248
r2 起点            6da9136  (= 40e1470^)
破坏实验副本       /tmp/isoverify/repo   (git clone, detached)
pytest             9.0.3 / python 3.12.13 / 16 核
```

- 活体探针一律经**生产 `build_isolation_workspace` 产出的真 staging**，以子进程驱动真 `guard.py` 与真 `tools/run_cv_probe.py`，不 import 施工方测试里的任何 fixture。
- neuter 全部在 `/tmp` 副本上做，为可读性用 `-n0` 串行跑（与施工方默认 `-n auto` 的红数逐条一致）。

---

## 1. 逐项判定 R2-1 … R2-6

### R2-1 · 词法检查改为「按参数角色的全函数」 — **成立**

**读码**：`guard.py:194-203` 的 `_param_role(key)` 只有 `"content"` / `"path"` 两个返回值，写法是 `return "content" if key in CONTENT_ROLE_KEYS else "path"` —— 全函数、无第三分支。`evaluate()` 的扫描循环（`guard.py:421-433`）对 path 角色**无条件**执行 `_lexical_check` + `_path_arg`，`_looks_like_path()` 已从该路径移除，只剩 `_validate_request_file` 里作**非输出参数的归一化选择器**（那里的 lexical 扫描本来就是无条件的），符合骨架「保留给 `_validate_request_file` 用、不再作 path-role 前置门」。

**活体（主控四条claim之一，我独立复现，结论一致）**：

```text
Read {"file_path":"case_tests"}      -> rc=2  forbidden token: case_tests
Read {"file_path":"case_tests/x"}    -> rc=2  forbidden token: case_tests
Read {"file_path":"escape"}          -> rc=2  path escapes staging: escape      (escape -> /etc/passwd)
Read {"file_path":"./escape"}        -> rc=2  path escapes staging: ./escape
Read {"mystery":"case_tests"}        -> rc=2  forbidden token: case_tests
Read {"o":{"d":{"n":"case_tests"}}}  -> rc=2  forbidden token: case_tests
Glob {"pattern":"**/gt.json"}        -> rc=2  forbidden token: gt.json
Grep {"path":"case_tests"}           -> rc=2  forbidden token: case_tests
Write out/reading_summary.md, content = "Windows on 2026/07/31: grade line at z=0, span ~1.2 m. See ../notes."
                                     -> rc=0  ALLOW        （r1 的 prose ALLOK 锁性质保住）
```

四条必须新增的锁全部落地且真绑（neuter 见 §2）。

**⚠️ 附带发现 → MINOR-2**：见 §4。

### R2-2 · helper 写副作用受同一约束 + 真 E2E 锁 — **成立**（核心闭合；骨架第 2 条附 MINOR-1）

**骨架第 1 条（逐个核 cv_toolbox 写文件的 tool、列全输出落点参数）—— 我独立复核并确认结论正确**：
`run_cv_probe.ALLOWED_TOOLS` 八个 tool 中，`crop_zoom` / `wall_line_profiler` / `storey_line_profiler` / `px_m_calibrator` / `window_cc_detector` / `overlay_logger` 的落点全部由 `allocate_sidecar_path(args.out_dir, …)` 派生（`cv_probe.py:158-177,236-244`：`crop_path` / `overlay_path` 均为 `sidecar_path.with_name(...)`）；`prescan-plan` / `prescan-elevation` 落点 = `evidence_dir(out_dir, image)/label`。另外两个能塑形落点的名字组件都被正则钉死、不含分隔符：`_SIDECAR_NAME_RE = ^\d{3}_[A-Za-z0-9_-]+(\.json)?$`（`sidecar.py:12`）、`_PRESCAN_LABEL_RE = ^[A-Za-z0-9][A-Za-z0-9_.-]*$`（`recipes.py:250`）。⇒ **`out_dir` 确是唯一输出角色参数**，`REQUEST_OUTPUT_ROLE_KEYS = ("out_dir",)` 的枚举完备。
我另外从请求侧构造了两个穿越尝试，双双被拦：

```text
args.sidecar_name = "001_x/../../../tools/evil"   -> guard rc=2，helper 未执行，可写根外零新增
args.label        = "a/../../tools"               -> guard rc=2，helper 未执行，可写根外零新增
```

**hook 侧**：`_check_output_target`（`guard.py:309-323`）要求 `out_dir` 解析进 `out/`；七个形状逐条实跑，**拒绝理由全部对靶**（不是被别的门顺手拦住）：

```text
out_dir='tools'             rc=2  request output path must land under out/: tools
out_dir='tools/cv_evidence' rc=2  request output path must land under out/: tools/cv_evidence
out_dir='requests/evidence' rc=2  request output path must land under out/: requests/evidence
out_dir='prescan'           rc=2  request output path must land under out/: prescan
out_dir='reference'         rc=2  request output path must land under out/: reference
out_dir='case_data'         rc=2  request output path must land under out/: case_data
out_dir='.'                 rc=2  request output path must land under out/: .
out_dir='out'               rc=0  ALLOW → helper rc=0，真产
    out/cv_evidence/1f_view/001_crop_zoom.json / _crop.png / _overlay.png
```

**E2E 锁的质量 —— 主控点名重点，逐条核过，成立**：
`test_e2e_hook_then_helper_changes_only_writable_tree` 确实①先跑真 hook、②**只在 hook ALLOW 时用 `subprocess` 真跑 `tools/run_cv_probe.py`**（`_run_helper`）、③用 `_staging_snapshot` 对**整棵 staging** 建签名（`rglob("*")` 覆盖目录、普通文件内容 hash、symlink target），④`_protected_tree_diff` 同时抓 `added` / `removed` / `rewritten`。豁免是**断言内的显式具名白名单**、不是静默 skip：

```python
_E2E_WRITABLE_PREFIXES = ("out/", "requests/")
_E2E_EXEMPT_NAMES = ("access_log.jsonl",)   # the guard's own append-only audit log
_E2E_EXEMPT_PARTS = ("__pycache__",)        # interpreter byte-cache of the staged tools
```

⑤合法形状 `inside_out` 另断言 `produced` 非空并附文案 `"the helper wrote no files under out/ — the E2E diff would be vacuous"`，**防的正是「不执行 helper 也绿」的空锁**。这一防线经我独立 neuter 验真（§2，R2-2c：把 wrapper 在 `cv_main` 调用点改成 `return 0` ⇒ 该参数变红）。⇒ **「只断言 hook 决定、不跑 helper」的不合格形态不存在。**

**wrapper 侧**：`run_cv_probe.py:64-72` 的 `_resolve_output` 确实独立执行 `out/` 约束，绕过 hook 直调对 `out_dir="tools"` 返回非零且受保护树零变化（我实跑：`rc=1`，protected-tree diff `[]`）。TOCTOU 也由它兜住：hook 放行良性 request 后把文件改写成 `out_dir="tools"`，helper 仍拒、`tools/` 零新增。

**⚠️ 未闭的半条 → MINOR-1**：见 §4。

### R2-3 · 可写根自身是 symlink 时反向授权 — **成立**

`_writable_root`（`guard.py:273-298`）要求 `root/name` **是真实目录、非 symlink、`resolve(strict=True)` 等于字面路径、且在 staging 内**，否则 `raise`；`_assert_writable_roots` 在 `evaluate()` **每次判定开头**重验（`guard.py:381-384`），任一异常 ⇒ 整次调用 deny，不是跳过坏根。骨架的「不是跳过该根」被精确实现（`_check_write_target` 的 `except ValueError: return False`，而非 `continue`）。

**活体（主控 claim 之三，复现一致）**：

```text
预置 <staging>/tools/ 真目录 + <staging>/out -> tools，正式 build 成功，out 仍是 symlink
Write {"file_path":"out/x.txt"}              -> rc=2  writable root out/ must be a real directory inside staging …
Write {"file_path":"out/run_cv_probe.py"}    -> rc=2  同上
Read  {"file_path":"case_data/1f_view.png"}  -> rc=2  同上      ← fail-closed 连读也拒，符合骨架
build 后把 requests/ 删掉                     -> Read 亦 rc=2   ← 缺根同样 fail-closed
```

### R2-4 · S1 一致性锁改为解析实值 — **成立**

`tests/test_isolation.py:682` 新增 `_KICKOFF_POINTER_RE = re.compile(r"Canonical worked-example file:\s*`([^`]+)`")`，测试从 staged kickoff 的**语法槽里解析出实际命名的路径**，再对**解析值**做 `is_file()` 与字节同一性比对；原来那两条拿常量 `WORKED_EXAMPLE_STAGED` 自证的断言已删除（r2 对 `tests/` 的**全部删除行只有这两条断言 + 旧 docstring**，见 §5）。

我独立核对了生产侧唯一指针来源：`skills/intake_pipeline/0_reading/session_kickoff.md:14` 的 `Canonical worked-example file: \`case_tests/…/1f_view.json\``，由 `_copy_skill_kickoff`（`isolation.py:549-556`）字符串替换成 staging 路径 —— 解析槽与生产槽同一处，不存在「测试解析 A、reader 读 B」的第二处漂移面。活体 build 后：

```text
kickoff pointer            = reference/worked_example_plan.json
staged 文件真实存在         = True
source/staged sha256       = d3424c42c7ffc6c7dd242a56aa153dcd5ac5795c1f58a1e2dcd4ba320853b5ab（两侧相同）
MANIFEST entry             = {"category":"reference","path":"reference/worked_example_plan.json",
                              "source_path":"case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json","sha256":"d3424c42…"}
requests/ 已预建           = True
staging 内 case_tests/     = 不存在
```

污染门未被放宽：`git diff f98d248..HEAD -- src/agent/execution/isolation.py` 在 `HARD_BLOCK_*` / `_assert_rel_allowed` / `_assert_manifest_clean` / `_assert_source_allowed` 上**只有注释行新增，零逻辑改动**（`HARD_BLOCK` 段 `diff` 为空）。

pointer-only neuter 必红已验（§2，R2-4）。

### R2-5 · `_write_target` 取首个命中 key 可被遮蔽 — **成立**

`_write_targets`（`guard.py:220-248`）先收集全部 present target key，`len(present) > 1` 直接 `raise ValueError("ambiguous write target: …")`；`evaluate()` 再对每个 target 校验。三个形状活体全 deny 且**理由绑歧义语义**：

```text
NotebookEdit {file_path:"out/decoy.txt", notebook_path:"tools/protected.ipynb", new_source:"x"}
    -> rc=2  ambiguous write target: more than one target key present (file_path, notebook_path) — refusing rather than guessing which one lands
NotebookEdit {notebook_path:"out/decoy.ipynb", file_path:"tools/protected.py", content:"x"}   -> rc=2 同上
NotebookEdit {file_path:"out/a.txt", notebook_path:"out/b.ipynb", new_source:"x"}             -> rc=2 同上（两个都合法仍拒 = 规则确实是关于歧义）
NotebookEdit {notebook_path:"tools/x.ipynb", new_source:"x"}  -> rc=2 write target must be under out/ or requests/（单 key 正常路径）
```

附 NIT-3（§4）。

### R2-6 · 损坏 aggregate 响亮报错 + S4 表更正 — **成立**

`_load_isolated_views`（`isolation.py:494-505`）现在**只在 `out/output.json` 不存在时**才进 per-image assembly；存在则只读一次，非法 JSON ⇒ `ValueError("aggregate output.json is not valid JSON: …")`，外形不是 `{"views": dict}` ⇒ `ValueError("aggregate output.json must be shaped …")`，即使 per-image 件齐全也不把 corruption 解释成 absence。锁 `test_merge_existing_corrupt_aggregate_is_rejected_instead_of_assembled[invalid_json|wrong_shape]` 并断言失败前不创建 attempt。

MINOR-3 的自查表更正已落执行日志（S4 局部表与总账两处均从「1 FAILED」改为「2 FAILED」，并注明 positive/extra 两锁共享同一 discovery seam），我独立复跑 glob neuter 得到**同样的 2 条**（§2，S4-glob）。

---

## 2. neuter 独立对账表（十处定点破坏，全部我自己实跑）

破坏一律在 `/tmp/isoverify/repo` 打，跑完 `git checkout -- .` 复位，最后 `git status` 为 **(clean)**。

| # | 定点破坏（生产码） | 施工方声称 | 我实跑 | 真实变红测试名 | 对账 |
|---|---|---|---|---|---|
| R2-1a | `evaluate` 恢复 r1 的 `if not _looks_like_path(value): continue` 前置门 | 5 failed, 9 passed | **5 failed, 9 passed** | `test_guard_r2_bare_and_slashed_forbidden_path_both_denied[case_tests]`；`test_guard_r2_bare_extensionless_escaping_symlink_denied[escape]`；`test_guard_r2_unknown_key_defaults_to_path_role[unknown_key_bare_deny_token-tool_input0]`、`[unknown_key_bare_escaping_symlink-tool_input1]`、`[unknown_nested_key_bare_deny_token-tool_input2]` | ✅ 逐条吻合。**带斜杠的对照形状 `[case_tests/x]` 与 `[./escape]` 保持绿** ⇒ 精确复现原洞、非泛化破坏 |
| R2-1b | `_param_role()` 恒 `return "content"` | 8 failed, 6 passed | **8 failed, 6 passed** | 上述 5 条 + `[case_tests/x]` + `[./escape]` + `test_guard_r2_param_role_is_total_over_keys` | ✅ 结构锁与每种 live 形状都非空锁 |
| R2-2a | guard `_check_output_target()` 恒 ALLOW | 9 failed, 2 passed | **9 failed, 2 passed** | `test_guard_denies_request_output_dir_outside_writable_root` 全 7 参数（`tools`/`tools/cv_evidence`/`requests/evidence`/`prescan`/`reference`/`case_data`/`.`）+ `test_e2e_hook_then_helper_changes_only_writable_tree[outside_tools-tools-False]`、`[outside_reference-reference-False]` | ✅ 逐条吻合；E2E 的全树 diff 确是承重件 |
| R2-2b | wrapper `_resolve_output()` 退回普通 `_resolve()` | 1 failed, 10 passed | **1 failed, 10 passed** | `test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged` | ✅ |
| R2-2c | wrapper 在 `cv_main(cv_argv)` 调用点直接 `return 0`（成功但不执行） | 1 failed, 2 passed | **1 failed, 2 passed** | `test_e2e_hook_then_helper_changes_only_writable_tree[inside_out-out/cv-True]` | ✅ **这条是 R2-2 反空锁的命脉**：证明 E2E 锁真的执行 helper，不执行就红 |
| R2-3 | `_writable_root()` 退回 `(root/name).resolve(strict=False)` | 3 failed | **3 failed** | `test_guard_denies_writes_when_allowed_root_symlinked_after_build`；`test_guard_denies_writes_when_an_allowed_root_is_a_symlink[out]`、`[requests]` | ✅ |
| R2-4 | 只改生产 kickoff 指针 `WORKED_EXAMPLE_STAGED + ".missing"`（保留真实拷贝） | 1 failed, 2 passed | **1 failed, 2 passed** | `test_build_kickoff_points_at_staged_worked_example_path` | ✅ **sol 抓的假锁已真闭**（sol 当初同一破坏得 `3 passed`） |
| R2-5 | 删 `len(present) > 1` 拒绝，只返回 `present[0]` | 3 failed | **3 failed** | `test_guard_denies_ambiguous_multiple_write_targets[both_targets_legal_still_ambiguous-tool_input2]`、`[decoy_file_path_masks_notebook_path-tool_input0]`、`[decoy_notebook_path_masks_file_path-tool_input1]` | ✅ |
| R2-6 | aggregate 存在分支改 `if False and output_path.exists():` | 2 failed, 4 passed | **2 failed, 4 passed** | `test_merge_existing_corrupt_aggregate_is_rejected_instead_of_assembled[invalid_json]`、`[wrong_shape]` | ✅ |
| S4-glob | `out_dir.glob("*_view.json")` → `glob("*_NOPE.json")` | 2 failed, 2 passed（**已更正**） | **2 failed, 2 passed** | `test_merge_assembles_per_image_views_byte_equal_and_accepts`；`test_merge_per_image_extra_is_rejected` | ✅ MINOR-3 的更正属实 |

**总账：十处定点破坏，红数与红测试名 10/10 与执行日志一致，零夸大、零漏报。**

---

## 3. §2A 八条安全性质活体复核 — **八条全部仍为 deny**

全部经真 staging 内的真 `guard.py` 进程执行：

| # | 性质 | payload 摘要 | 结果 |
|---|---|---|---|
| 1 | 读 `gt.json` | `Read {"file_path":"out/gt.json"}` | `rc=2 forbidden token: gt.json` |
| 2 | `case_tests` 路径 | `Read {"file_path":"case_tests/e2e_tests/x.png"}` | `rc=2 forbidden token: case_tests` |
| 2′ | **bare** `case_tests`（sol MAJOR-2 的回退形状） | `Read {"file_path":"case_tests"}` | `rc=2 forbidden token: case_tests` |
| 3 | 越界绝对路径 | `Read {"file_path":"/etc/passwd"}` | `rc=2 absolute path outside staging: /etc/passwd` |
| 4 | 越界 symlink | `Read {"file_path":"out/escape_link"}` | `rc=2 path escapes staging: out/escape_link` |
| 4′ | **bare 无后缀**越界 symlink | `Read {"file_path":"escape"}` | `rc=2 path escapes staging: escape` |
| 5 | 非白名单命令 | `Bash cat out/input.png` | `rc=2 command is not allowlisted: cat` |
| 6 | `python -c` | `Bash python -c 'print(1)'` | `rc=2`（理由 `python command must be exactly: …`，见 §4 观察） |
| 7 | 复合 shell token | `Bash ls out ; id` | `rc=2 compound shell token forbidden: ;` |
| 8 | request JSON 禁词 | request 内含 `case_tests/…` | `rc=2 request contains forbidden token: forbidden token: case_tests` |

### 3.1 净效果差分：只有一处 DENY→ALLOW，且是本批授权的那一处

我把同一 payload 矩阵（44 个形状）在同一真 staging 内**同时**喂给改造前 `f98d248` 的 `guard.py` 与 HEAD 的 `guard.py`：

```text
DENY -> ALLOW 回退：1 处 = ['Write out/summary.md, content = "grade line ~1.2 on 2026/07/31 ..."']   ← 本批唯一授权的放松
ALLOW -> DENY  新收紧：13 处 = Write tools/run_cv_probe.py · guard.py · MANIFEST.json ·
    isolation_settings.json · skills/**/guide.md · src/**/tools.py · case_data/1f_view.png ·
    reference/worked_example_plan.json · staging 根散件 · out/to_tools/run_cv_probe.py（嵌套 symlink）·
    Edit tools/cv_probe.py · NotebookEdit tools/x.ipynb · NotebookEdit 双 target key 遮蔽 ·
    Read bare escaping symlink · Bash helper request out_dir=tools
```

⇒ **守卫的净效果确实更严**，派工单 §4.1 的红线满足。

### 3.2 我自己找的新逃逸面（14 条），未发现新洞

```text
out/../tools/run_cv_probe.py                  DENY   write target must be under out/ or requests/
out/to_tools/run_cv_probe.py（to_tools->../tools） DENY
out/to_outside/passwd（to_outside->/etc）       DENY   path escapes staging
out/./nested/item.json                        ALLOW  （安全归一化，正确）
staging 内绝对路径 out/absolute.json           ALLOW  （正确）
Out/item.json（大小写）                        DENY
Write 无任何 target key                        DENY   Write requires a file_path/notebook_path
未知 key 携带 bare 禁词 / 深层嵌套未知 key      DENY
Glob pattern / Grep path 携带禁词              DENY
request 里 out_dir 为非字符串（["tools"]）      DENY  （list 元素继承外层 key，仍被检）
sidecar_name / label 穿越                      DENY  （见 §1 R2-2）
TOCTOU：hook 放行后改写 request 再跑 helper     helper 拒，tools/ 零新增
requests/ 下写 .py 后试图执行                  DENY   only tools/run_cv_probe.py may be executed
删掉 requests/ 根后任意调用                     DENY   fail-closed
```

---

## 4. Findings

### MINOR-1 · guard 与 wrapper 的「可写根」定义不一致，R2-2 骨架第 2 条只闭了一半

涉及：
- `src/agent/execution/isolation_templates/run_cv_probe.py:60-61`
- 对照 `src/agent/execution/isolation_templates/guard.py:273-298`

R2-3 把 guard 的可写根从「解析出来的路径」改成「钉死的真实目录」，但 wrapper 的同名函数没跟：

```python
# guard.py（R2-3 后，钉死）
def _writable_root(root: Path, name: str) -> Path:
    path = root / name
    if path.is_symlink() or not path.is_dir():
        raise ValueError(...)
    resolved = path.resolve(strict=True)
    if resolved != path or not _under(resolved, root):
        raise ValueError(...)
    return path

# run_cv_probe.py（仍是 R2-3 之前的语义）
def _writable_root(root: Path, name: str) -> Path:
    return (root / name).resolve(strict=False)
```

活体：预置 `<staging>/tools/`（真目录）+ `<staging>/out -> tools`，正式 build 成功。

```text
hook（guard）      rc=2  writable root out/ must be a real directory inside staging …   ← 正确
wrapper 单独执行    rc=0  真实新增：
    tools/cv/  tools/cv/cv_evidence/  tools/cv/cv_evidence/1f_view/
    tools/cv/cv_evidence/1f_view/001_crop_zoom.json
    tools/cv/cv_evidence/1f_view/001_crop_zoom_crop.png
    tools/cv/cv_evidence/1f_view/001_crop_zoom_overlay.png
```

即 sol MAJOR-3 的那个形状在 wrapper 这条防线上**原封未动**。返工单 R2-2 第 2 条的原话是「wrapper 侧做同一约束，不要只在 guard 做 —— **两处策略必须一致，避免 guard/wrapper 策略差**」，本批也确实新增了 `test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged` 把 wrapper 声称为**独立防线**；该声称对 `out_dir="tools"` 成立，对「可写根本身被换掉」不成立。

**为什么不升 MAJOR**：生产路径不可达 —— ① guard 每次判定都先 `_assert_writable_roots`，根被换掉时连 Read 都拒，Bash 调 helper 更进不去；② 子代理**造不出 symlink**（`ln` 不在 `READ_ONLY_COMMANDS`，Bash 只放行 `ls`/`file`/`python tools/run_cv_probe.py`，`Write` 只产普通文件）。这是纵深防御的一个缺口，不是活的逃逸路径。

**出口**：wrapper 的 `_writable_root` 与 guard 同语义（真目录 + `resolve(strict=True) == 字面路径` + 在 staging 内，否则拒），并把 R2-3 的 `out -> tools` 形状加进 wrapper 独立锁的参数化。

### MINOR-2 · R2-1 的 fail-closed 缺省把 F-4 的可用性缺陷搬到了「非 content 角色的自由文本参数」上

涉及：`guard.py:194-203`（`_param_role`）+ `guard.py:421-433`（扫描循环）+ `isolation.py:656-666`（hook matcher）。

`isolation_settings.json` 的 PreToolUse `"matcher": ""` = **匹配所有工具**。R2-1 之后，凡不在 `CONTENT_ROLE_KEYS`（`content`/`old_string`/`new_string`/`new_source`）里的字符串参数一律按 path 角色**无条件**过 `_lexical_check`。于是任何工具的自由文本参数只要出现 `...`、`~` 或 `grade` 就被拒。同一 staging 内把 guard 换成 r1 版本做对照：

| 形状 | HEAD | r1 | HEAD 的拒绝理由 |
|---|---|---|---|
| `TodoWrite` `activeForm="Tracing 1f walls..."` | **DENY** | ALLOW | `parent traversal token is forbidden` |
| `TodoWrite` `activeForm="Marking the grade line on North"` | **DENY** | ALLOW | `forbidden token: grade` |
| `Grep` `pattern="wall_..[0-9]"` | **DENY** | ALLOW | `parent traversal token is forbidden` |
| `Grep` `pattern="z ~ 0.0"` | **DENY** | ALLOW | `home token is forbidden` |
| 未知工具 `description="Measuring wall thickness..."` | **DENY** | ALLOW | `parent traversal token is forbidden` |
| （对照）`Write out/summary.md` content 含 `grade line ... ~` | ALLOW | ALLOW | — |
| （对照）`Read case_data/1f_view.png` | ALLOW | ALLOW | — |

这**不是施工方的错**：返工单 §R2-1 明写「其余一切 key（含未知 key）→ 按 path 角色处理（无条件检查）= fail-closed」「**『其余一律按 path 处理』是硬要求，不是可选项**」，施工方精确照做。它也**不是相对改造前基线的回退**（`f98d248` 扫整个序列化 tool input，这些形状当年同样被拒），故不列为安全或回归缺陷。

但它值得单独登记，理由有三：① 本批存在的唯一理由就是 F-4 那类摩擦（07-30 首轮 8 次拒绝里 7 次是与守卫搏斗，零安全价值）；② `TodoWrite` 的 `activeForm`/`status`、`Grep` 的 `pattern` 是识图子代理的常规工具面，而这批锁里**没有任何一条覆盖 Write/Edit 之外的工具的可用性**；③ 返工单自己给了 sanctioned 出口 ——「要豁免必须显式加进 content 角色表」—— 只是 `CONTENT_ROLE_KEYS` 至今只列了 Write/Edit/NotebookEdit 的四个文本体参数，**没人枚举过隔离 reader 实际会用到的其余自由文本参数**。

**出口（建议，需主控裁定）**：在复验轮重跑识图之前，① 按名把已知自由文本参数并入 `CONTENT_ROLE_KEYS`（至少 `activeForm`、`description`；`status` 之类枚举值也可一并），② 为「非 Write/Edit 工具的自由文本参数含 `~`/`...`/`grade` 仍 ALLOW」补一条可用性正例锁，③ **复验轮跑完后必须读 `access_log.jsonl` 统计守卫拒绝次数**，把它当成本批成败的一个直接读数 —— 否则「脚手架摩擦」这条归因候选在下一轮依旧无法证伪。

### NIT-1 · `test_guard_r2_param_role_is_total_over_keys` 的第一条断言是同义反复

```python
roles = {guard_mod._param_role(k) for k in guard_mod.CONTENT_ROLE_KEYS}
assert roles == {"content"}
```

`_param_role` 的实现就是「在不在 `CONTENT_ROLE_KEYS` 里」，这条断言在任何实现下都恒真。真正承重的是随后那个对 `PATH_ROLE_KEYS + (None, "", "mystery_param", …)` 的循环；而 `PATH_ROLE_KEYS` 被生产码注释明确降格为「documentation-only … does not have to be exhaustive」，即结构锁的强度挂在一个生产码自称非权威的元组上。**非阻断**：性质本身由 R2-1 的四把 live 锁承载，且 R2-1b neuter 下本测试确实变红。

### NIT-2 · E2E 豁免 `__pycache__` 是按路径部件匹配、不限深度

`_E2E_EXEMPT_PARTS = ("__pycache__",)` 配 `any(p in _E2E_EXEMPT_PARTS for p in parts)` ⇒ 任何层级的 `__pycache__/**` 都被豁免，包括 `tools/__pycache__/**`。写进受保护目录字节缓存的改动对这把 E2E 锁不可见。返工单**明确授权**了该豁免、且 `tools/**` 由写保护门独立兜住，故仅作登记。

### NIT-3 · R2-5 之后 `evaluate()` 里「逐个 target 校验」的循环按构造不可达

`_write_targets` 在 `len(present) > 1` 时直接 `raise`，因此返回值永远是 0 或 1 个元素，`for target in targets:` 的多元素分支永不执行。行为正确（更严的规则吸收了更弱的规则），但代码读起来像同时执行两条规则。

### 观察（不计 finding）· `python -c` 的专用分支不可达

`_check_bash` 里 `if parts[3] == "-c": return False, "python -c is forbidden"` 位于 `parts[1] == "tools/run_cv_probe.py"` 与 `parts[2] == "--request"` 之后，而 `python -c '…'` 只有 3 个 token，先被 `len(parts) != 4` 拦掉。性质仍 deny（§3 性质 6），且我核实 `_check_bash` **与 `f98d248` 逐字节相同**（本批完全没碰 Bash 路径，符合派工单要求），故属既有状况、不归本批。

---

## 5. 回归与数字对账

**主工作树、HEAD `85b6695`、独立全量：**

```text
$ pytest -q
1908 passed, 10 xfailed, 150 warnings in 333.94s (0:05:33)
EXIT=0
```

与施工方声称的 `1908 passed / 10 xfailed / 0 failed` **逐字相同**。

**+27 的净增可机械核死。** r2 区间（`40e1470^..HEAD`）只动了 5 个文件，其中测试只有 `tests/test_isolation.py`：

```text
$ git diff --stat 40e1470^..HEAD
 AI_agent/logs/reviews/execution/2026-07-31_isolation_scaffold_glm.md | 166 +++-
 src/agent/execution/isolation.py                                     |  17 +-
 src/agent/execution/isolation_templates/guard.py                     | 258 +++++--
 src/agent/execution/isolation_templates/run_cv_probe.py              |  31 +-
 tests/test_isolation.py                                              | 368 ++++++++-
```

收集数直接对账：

```text
$ pytest -q -n0 --collect-only tests/test_isolation.py        # HEAD
106 tests collected
$ git checkout 6da9136 -- tests/test_isolation.py && pytest -q -n0 --collect-only tests/test_isolation.py
79 tests collected
```

`106 − 79 = 27`，逐项拆开 = 新增 11 个测试函数的参数化用例总数
`2(bare/slashed) + 2(escape) + 3(unknown key) + 1(param_role 结构) + 7(out_dir) + 1(wrapper) + 3(E2E) + 2(root symlink) + 3(ambiguous) + 1(symlinked after build) + 2(corrupt aggregate) = 27`。

**零测试被删、零断言被弱化。** r2 对 `tests/**` 的**全部删除行**只有 R2-4 那两条假断言与其旧 docstring：

```text
-    """S1 consistency lock: … a real stat, not a hardcoded string compare …"""
-    assert str(WORKED_EXAMPLE_STAGED) in kickoff
-    assert (staging / WORKED_EXAMPLE_STAGED).exists()
```

替换件严格更强（解析 + `is_file()` + 与仓库源逐字节比对），并保留了原有的 `WORKED_EXAMPLE_SOURCE not in kickoff` 与 `not (staging/"case_tests").exists()`。派工单 §4.2「不许改测试迁就实现」满足。

**关于 `1881 → 1908` 的基线复核**：我在 `/tmp` 副本上于 `6da9136` 跑全量得 `1867 passed / 8 skipped / 6 failed / 10 xfailed`；6 failed + 8 skipped 全是**克隆环境缺件**（无 `.env` 凭据 → `test_zone_agent`；无 gitignored run 产物 → `test_sm21_anchor_ep_clean`；DXF/评分等夹具同理），`1867 + 8 + 6 = 1881` 与主控在主工作树复核的基线一致，总收集数 `1891 → 1918`，差 `+27`。⇒ **基线数字与净增两侧对得上，零回归。**

---

## 6. 范围与受保护资产

**① 本批 13 个 commit 触碰的文件全集**（`78967eb` `c42de85` `f2a4efb` `c9974fd` `9d6c278` `40e1470` `141f019` `e3f3a3a` `05ae23e` `eb6c9e2` `2676e04` `5ecebb9` `85b6695`）：

```text
AI_agent/guides/new_case_guide.md
AI_agent/logs/reviews/execution/2026-07-31_isolation_scaffold_glm.md
scripts/tool_scripts/cv_probe.py
src/agent/execution/isolation.py
src/agent/execution/isolation_templates/guard.py
src/agent/execution/isolation_templates/run_cv_probe.py
tests/test_cv_toolbox.py
tests/test_isolation.py
```

**`src/agent/judge/**` / `case_tests/test_baseline/gt/**` / `AI_agent/CLAUDE.md` 三者一个都不在内。** 逐 commit 复核（`git show --stat <c> -- src/agent/judge case_tests/test_baseline/gt AI_agent/CLAUDE.md`）13 次全空。

**② r2 区间显式核**：

```text
$ git diff --quiet 40e1470^..HEAD -- src/agent/judge case_tests/test_baseline/gt AI_agent/CLAUDE.md
exit 0
```

**③ 受保护人签答案树逐字节未动**：

```text
$ git diff --quiet f98d248..HEAD -- case_tests/test_baseline/gt   # exit 0
$ find case_tests/test_baseline/gt/sm24_anchor -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
e78c6e7e015746c14d8f70521551a71ee77b6e726259000ecf6133f91d61771f  -
$ find case_tests/test_baseline/gt/sm24_anchor -type f | wc -l
14
```

与主控给的基准值 **逐字相同**。

**④ `src/agent/judge/**` 在 `f98d248..HEAD` 上确有改动，但全部来自并行 sol 席位的 reading-typed-scoring 批**（本批区间内为 0）；按审阅单 §3.5 单独报给主控，不计入本批。

**⑤ 破坏实验隔离**：全部在 `/tmp/isoverify/repo`；结束时该副本 `git status` 为 `(clean)`；主工作树除只读 pytest 外零写入（`git status` 只余本轮四份未跟踪的审轨文档）；`src/agent/execution/isolation_templates/` 下无遗留 `access_log.jsonl`。

---

## 7. 对主控的验收出口

**返工单 r2 的六项 = 6/6 成立，sol 裁决书 §「返工验收出口」的五条 = 5/5 闭合**：

| sol 出口 | 判定 | 依据 |
|---|---|---|
| 1. request 写出路径受同等或更严约束 + 「执行 helper 后树外零变化」E2E 锁 | **闭合** | §1 R2-2 + §2 R2-2a/b/c |
| 2. path-role/content-role 分流；bare `case_tests` 与 bare escaping symlink 必 deny，合法 prose 仍 allow | **闭合** | §1 R2-1 + §3 性质 2′/4′ + §3.1 |
| 3. build/guard 拒绝 allowed root symlink | **闭合** | §1 R2-3 + §2 R2-3 |
| 4. S1 一致性测试解析并 stat 实际指针；pointer-only `.missing` 必红 | **闭合** | §1 R2-4 + §2 R2-4 |
| 5. 修正 S4 neuter 总账；裁定损坏 `output.json` 恢复报错 | **闭合** | §1 R2-6 + §2 R2-6 / S4-glob |

**须主控处置的两条（均非阻断）**：MINOR-1（wrapper 可写根语义补齐，纯纵深防御）、**MINOR-2（复验轮跑识图之前必须拍：`CONTENT_ROLE_KEYS` 要不要按名补入自由文本参数；并把 `access_log.jsonl` 的拒绝计数列为复验轮的必读产物）**。三条 NIT 可随下批顺手清。
