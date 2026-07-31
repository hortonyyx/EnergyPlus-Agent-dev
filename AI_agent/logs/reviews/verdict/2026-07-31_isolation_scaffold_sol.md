# 独立审阅裁决 · isolation-scaffold（sol）

> 审阅对象：`78967eb` / `c42de85` / `f2a4efb` / `c9974fd` / `9d6c278`
> 改造前基线：`f98d248`
> 审阅方式：主工作树只读；破坏性 neuter 全在 `/tmp/isolation-scaffold-sol-neuter.0csPGC/repo`（detached `9d6c278`）进行；未写 `case_tests/test_baseline/gt/**`。

## 结论：REWORK

S1 的样板件落盘、MANIFEST 溯源和 hash 均正确；S2 规定的八个常规代表形状也全部仍为 deny；S3 正常落点与 copy guard 的 parity 锁是真锁；S4 缺件、多件和零内容改动的功能断言均成立；当前全仓无回归。

但不能批准，原因是：

1. 新写边界只约束 Write/Edit 类工具的直接目标，没有约束白名单 CV helper 的写副作用。合法 request 可令 helper 在明令只读的 `tools/**` 下真实写文件。
2. prose 放松仍以 `_looks_like_path(value)` 猜路径，而不是按参数角色识别路径。改造前 deny 的 bare `file_path="case_tests"` 现在 allow；无后缀顶层 symlink 也完全绕过 `_path_arg`。
3. `out` / `requests` 自身若是指向 staging 内受保护目录的 symlink，`resolve(strict=False)` 会把该受保护目录反而认成 allowed root；受支持的显式 `--staging-root` build 会接受这种预置形态，且可直接放行覆盖 `tools/run_cv_probe.py`。
4. S1 所称“kickoff 实际命名路径真 stat”的一致性锁是假的：把 kickoff 指针改到不存在的 `.missing` 后，三条 S1 测试仍为 `3 passed`。

以上均不是生产安全产品级的假想攻击要求，而是本批自己承诺的 clean-room harness 正确性边界；前三项证明“只可写 `out/**` + `requests/**`”和“八条性质保持 deny”目前都只对有限夹具成立。

---

## Findings

### MAJOR-1 · CV request 可绕过写目标约束，在 `tools/**` 下真实落盘

涉及：

- `src/agent/execution/isolation_templates/guard.py:103-113`
- `src/agent/execution/isolation_templates/run_cv_probe.py:21,50-73`

`_validate_request_file` 只检查 request 内字符串的禁词和“是否仍在 staging 内”；它没有区分输入路径与输出路径，也没有要求 `args.out_dir` 落在 `out/**` / `requests/**`。wrapper 的 `_resolve` 同样只要求 staging 内。

在生产 `build_isolation_workspace` 生成的干净 staging 中写入：

```json
{
  "tool": "crop_zoom",
  "args": {
    "image": "case_data/1f_view.png",
    "out_dir": "tools",
    "bbox": "0,0,2,2"
  }
}
```

再实际调用 hook 和 helper：

```text
tool_name = Bash
command = python tools/run_cv_probe.py --request requests/write_tools.json
guard rc=0
helper rc=0
```

真实新增：

```text
tools/cv_evidence/1f_view/001_crop_zoom.json
tools/cv_evidence/1f_view/001_crop_zoom_crop.png
tools/cv_evidence/1f_view/001_crop_zoom_overlay.png
```

这直接证伪“子代理只可写 `out/**` + `requests/**`”，也证伪 §2B① 中“guard 仍是权威写保护门”的安全理由。`settings.json` 增加 `requests/**` 权限本身是功能所需的最小改动，但现有 guard 并非覆盖 helper side effect 的权威门，因此该边界被低估。

出口：

- 按 request 参数角色验证；所有会写文件的 CV tool 的 `out_dir` 必须解析到指定可写根（通常应为 `out/**`），不能只要求“staging 内”。
- 在 wrapper 侧再做同一约束，避免 guard/wrapper 之间出现策略差。
- 新增真 E2E 锁：hook allow 后实际执行 helper，并比较执行前后 staging 树，断言 `out/**` / `requests/**` 外零新增、零改写。

### MAJOR-2 · prose 放松跳过了明确的路径参数；`case_tests` 性质存在 deny→allow 回退

涉及：

- `src/agent/execution/isolation_templates/guard.py:127-149`
- `src/agent/execution/isolation_templates/guard.py:265-279`

当前逻辑先按 key 排除 content role，随后对其余字符串仍用 `_looks_like_path(value)` 猜形状。bare 相对路径既无 `/`、不以 `.` 开头、也无受识别后缀时，哪怕 key 明确是 `file_path`，也不会经过 `_lexical_check` 或 `_path_arg`。

同一 payload 在改造前后实跑：

```text
payload = {"tool_name":"Read","tool_input":{"file_path":"case_tests"}}

f98d248: rc=2 forbidden token: case_tests
9d6c278: rc=0 ALLOW
```

对照形状：

```text
file_path="case_tests/x"  -> rc=2 forbidden token: case_tests
file_path="case_tests"    -> rc=0 ALLOW
```

所以 §2A 的“case_tests 路径仍 deny”只被测试中的带 `/` 夹具锁住，性质本身没有保持。

同一缺口还跳过越界 symlink。先在显式 staging root 顶层预置 `escape -> /etc/passwd`，再调用正式 build；build 成功且保留该项。随后：

```text
payload = {"tool_name":"Read","tool_input":{"file_path":"escape"}}
escape_resolves_to /etc/passwd
guard rc=0
```

而 `file_path="./escape"` 因以 `.` 开头才会进入 `_path_arg`，结果为 `rc=2 path escapes staging: ./escape`。这说明 symlink deny 也依赖字符串表面形状。

出口：

- 延续 r1 的正确方向，完整按参数角色判断：content body 整体免扫；已知 path role（至少 `file_path`、`notebook_path`、Read/Glob/Grep 的路径参数）无条件做 lexical + `_path_arg`，不得再让 `_looks_like_path` 当 path-role 前置门。
- 增加 bare `case_tests`、bare extensionless escaping symlink 两条活体锁，并保留现有 prose allow 锁。

### MAJOR-3 · allowed root 自身为 symlink 时，解析结果反向授权受保护目录

涉及：

- `src/agent/execution/isolation.py:150-155,188-193`
- `src/agent/execution/isolation_templates/guard.py:152-179`

`build_isolation_workspace(..., staging_root=...)` 支持显式、已存在的 staging root，并以 `mkdir(..., exist_ok=True)` 接受已有目录形态。预置：

```text
<staging>/tools/          # real directory
<staging>/out -> tools    # symlink
```

正式 build 成功。之后：

```text
out_is_symlink True
(out/run_cv_probe.py).resolve() == (tools/run_cv_probe.py).resolve()  True

payload = {
  "tool_name":"Write",
  "tool_input":{"file_path":"out/run_cv_probe.py","content":"overwrite"}
}
guard rc=0
```

根因是 `_path_arg` 把 target 解析成 `<staging>/tools/run_cv_probe.py`；同时 `_check_write_target` 把 `(root / "out").resolve(strict=False)` 也解析成 `<staging>/tools`，于是受保护的 `tools/**` 被当成 allowed root。普通嵌套 symlink `out/to_tools -> ../tools` 会正确 deny；缺口专门在 allowed root 本身。

出口：

- build 必须要求新/空 staging，或至少用 `lstat` 明确拒绝 `out`、`requests`、`tools` 等固定根为 symlink/非预期类型。
- guard 应 pin 住真实且非 symlink 的 allowed roots；不能通过“解析一个可替换的 allowed-root 路径”定义授权集合。
- 新增 build + hook 联合锁，覆盖 `out -> tools`、`requests -> tools`。

### MAJOR-4 · S1 kickoff↔落点“一致性锁”未 stat kickoff 实际命名的路径

涉及：

- `tests/test_isolation.py::test_build_kickoff_points_at_staged_worked_example_path`

测试实现是：

```python
assert str(WORKED_EXAMPLE_STAGED) in kickoff
assert (staging / WORKED_EXAMPLE_STAGED).exists()
```

它没有从 kickoff 文本提取被命名路径；substring 与 stat 都依赖测试侧硬编码常量。独立 clone 中只破坏生产指针、保留真实拷贝：

```diff
- text.replace(WORKED_EXAMPLE_SOURCE, WORKED_EXAMPLE_STAGED)
+ text.replace(WORKED_EXAMPLE_SOURCE, WORKED_EXAMPLE_STAGED + ".missing")
```

实跑：

```text
pytest -q \
  tests/test_isolation.py::test_build_stages_worked_example_byte_identical_and_in_manifest \
  tests/test_isolation.py::test_build_kickoff_points_at_staged_worked_example_path \
  tests/test_isolation.py::test_worked_example_staged_path_is_not_guard_denied

3 passed
```

此时 kickoff 明确指向不存在的 `reference/worked_example_plan.json.missing`，却全绿。施工方以“删除 `_copy_worked_example(...)`”同时拆掉落盘端，只证明“文件不存在会红”，没有拆开测试真正声称的两侧一致性 seam。

出口：

- 从 staged kickoff 的实际语法位置解析 backtick 内路径，再 stat 该解析结果；不要对常量做 substring + stat。
- 独立指定 pointer-only neuter（例如上面的 `.missing`），该一致性测试必须红；copy-call neuter 继续用于样板件存在/MANIFEST 锁。

### MINOR-1 · `NotebookEdit` 可用无关 `file_path` 遮蔽真实 `notebook_path`

`_write_target` 不按 tool 选择目标 key，而是固定先取 `file_path`、再取 `notebook_path`。实跑：

```text
NotebookEdit {
  "file_path":"out/decoy.txt",
  "notebook_path":"tools/protected.ipynb",
  "new_source":"x"
}
-> rc=0 ALLOW

NotebookEdit {
  "notebook_path":"tools/protected.ipynb",
  "new_source":"x"
}
-> rc=2
```

若下游内建工具 schema 拒绝额外 `file_path`，该形状会在 hook 之后被拦；本审没有把它上升为 MAJOR。但 hook 自身的目标判定确有歧义，不应依赖下游额外字段策略。

出口：按 tool 精确选择唯一 target key，并拒绝出现另一 target key。

### MINOR-2 · 存在但损坏的 `output.json` 被当作“不存在”，超出 S4 授权放松

派工骨架允许的是“没有单一聚合件时”机械聚合。当前 `_load_isolated_views` 对已存在但非法 JSON、或 shape 不合法的 `output.json` 都静默 fallback。

直接探针：

```text
out/output.json = "{this is not valid JSON"
out/a_view.json = {"id":"a_view","observations":[]}

_load_isolated_views(...) ->
{'views': {'a_view': {'id': 'a_view', 'observations': []}}}
```

这改变了原路径“损坏 aggregate 响亮报错”的行为，不是 S4 必需的放松。施工日志虽主动披露，理由仍未得到派工授权。

出口：区分“不存在”和“存在但损坏/错 shape”；前者 assembly，后者保留原 ValueError。若主控确要接受 fallback，应先明确改契约并补双分支锁。

### MINOR-3 · S4 glob neuter 自查漏报一条共享变红测试

将：

```diff
- out_dir.glob("*_view.json")
+ out_dir.glob("*_NOPE.json")
```

对 S4 四锁一起实跑，真实结果是：

```text
FAILED tests/test_isolation.py::test_merge_assembles_per_image_views_byte_equal_and_accepts
FAILED tests/test_isolation.py::test_merge_per_image_extra_is_rejected
2 failed, 2 passed
```

执行日志只登记第一条。原因合理：extra 锁也共享同一 glob，glob 被 neuter 后先报 missing，无法达到 `unexpected` 断言；但“变红的测试”总账仍少报了共享依赖。

出口：更正 neuter 总账，并注明 positive/extra 两锁共享 discovery seam；不需要改产品逻辑。

---

## §2A 八条标准形状活体结果

所有 probe 都通过临时 staging 根内的真实 `guard.py` 进程执行，结果如下：

| 性质 | payload 摘要 | 结果 |
|---|---|---|
| 读 `gt.json` | `Read out/gt.json` | `rc=2 forbidden token: gt.json` |
| `case_tests` 路径 | `Read case_tests/e2e_tests/x.png` | `rc=2 forbidden token: case_tests` |
| 越界绝对路径 | `Read /etc/passwd` | `rc=2 absolute path outside staging` |
| 越界 symlink | `Read out/escape_link`，link→`/etc/passwd` | `rc=2 path escapes staging` |
| 非白名单命令 | `Bash cat out/input.png` | `rc=2 command is not allowlisted: cat` |
| `python -c` | `Bash python -c 'print(1)'` | `rc=2` |
| 复合 shell token | allowlisted command 后加 `; id` | `rc=2 compound shell token forbidden: ;` |
| request JSON 禁词 | request 内含 `case_tests/test_baseline/gt/gt.json` | `rc=2 request contains forbidden token` |

因此施工方的八个代表夹具不是假绿；问题是其形状覆盖不完整。`file_path="case_tests"` 和 bare symlink 反例见 MAJOR-2，不能把上表外推成无条件安全性质。

写目标补充矩阵：

| 形状 | 结果 |
|---|---|
| `out/../tools/run_cv_probe.py` | deny |
| `out/to_tools/run_cv_probe.py`，`to_tools -> ../tools` | deny |
| `out/to_outside/passwd`，`to_outside -> /etc` | deny |
| `out/./nested/item.json` | allow（安全归一化） |
| staging 内绝对 `out/absolute.json` | allow |
| `Out/item.json` | deny（当前 Linux 大小写语义） |
| allowed root 自身 `out -> tools` | **allow，见 MAJOR-3** |
| request `args.out_dir="tools"` 后实际执行 helper | **allow 且真实写 `tools/**`，见 MAJOR-1** |

---

## §2B 四项边界独立判断

| 边界 | 判断 | 独立证据 |
|---|---|---|
| ① settings 加 `requests/**` 是最小一致改动，guard 仍权威 | **被低估** | 权限增加本身合理；但 request `out_dir="tools"` 能让白名单 helper 在 `tools/**` 写文件，guard 并不覆盖全部写副作用（MAJOR-1）。 |
| ② S3 只查末级 `cv_evidence` / `prescan` | **机械描述准确；风险真实，未再低估** | `--out-dir .../cv_evidence/1f_view` 实跑 `rc=0`，落到 `.../cv_evidence/1f_view/cv_evidence/1f_view/prescan/candidates.json`，`_is_run_prescan_path(...) == False`。这是已如实登记的骨架边界；新 guide 的固定样例降低概率，但没有消除该输入。建议本次 rework 顺手按最终规范路径做结构判定。 |
| ③ parity 锁只用 oracle-side neuter | **未低估，锁有效** | 施工方 neuter `_is_run_prescan_path -> False` 真实红两条；本审另在 CLI 侧把 `out_dir=args.out_dir` 改为 `args.out_dir/"shifted"`，`test_cv_probe_prescan_echoes_landing_matching_copy_guard` 单独变红，嵌套拒绝两参数仍绿。说明锁会抓两侧任一布局漂移。 |
| ④ S4 只扫 `*_view.json` | **机械描述准确；当前不阻断** | 本批实跑的 sm21/sm24 expected IDs 均以 `_view` 结尾；构造 future `expected_output_id="plain"` 且存在 `plain.json`，会响亮 `ValueError ... missing ... ['plain']`，不是静默接受。它是前向兼容/可用性债；schema 又未把 `_view` 后缀固定为 invariant，未来 family 上线时必须同步改 discovery。 |

---

## S1 溯源与污染门

正式临时 build 的三方 hash：

```text
source_sha256  d3424c42c7ffc6c7dd242a56aa153dcd5ac5795c1f58a1e2dcd4ba320853b5ab
staged_sha256  d3424c42c7ffc6c7dd242a56aa153dcd5ac5795c1f58a1e2dcd4ba320853b5ab
MANIFEST.sha256 d3424c42c7ffc6c7dd242a56aa153dcd5ac5795c1f58a1e2dcd4ba320853b5ab
```

MANIFEST entry：

```json
{
  "category": "reference",
  "path": "reference/worked_example_plan.json",
  "source_path": "case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json",
  "sha256": "d3424c42c7ffc6c7dd242a56aa153dcd5ac5795c1f58a1e2dcd4ba320853b5ab"
}
```

staged kickoff 当前命名 `reference/worked_example_plan.json`，且文件真实存在。`git diff --unified=0 f98d248 9d6c278 -- src/agent/execution/isolation.py` 中 `_assert_manifest_clean`、`_assert_rel_allowed`、`HARD_BLOCK_*` 无增删；活体复核：

```text
worked_example -> ALLOW
case_tests/test_baseline/gt/sm21/gt.json -> DENY forbidden source file
case_tests/e2e_tests/sm21_anchor/report/verdict.json -> DENY forbidden generated judgment artifact
```

所以 S1 产品态的溯源和污染门成立；阻断项是 MAJOR-4 的一致性假锁，不是当前文件/hash 错误。

---

## Neuter 独立对账

| 定点破坏 | 本审真实变红测试 |
|---|---|
| 删除 build 中 `_copy_worked_example(...)` | `test_build_stages_worked_example_byte_identical_and_in_manifest`；`test_build_kickoff_points_at_staged_worked_example_path`（`2 failed, 1 passed`，与日志一致） |
| kickoff pointer 改为 `WORKED_EXAMPLE_STAGED + ".missing"` | **无红，`3 passed`**（MAJOR-4） |
| 删除 `evaluate` 的 `if tool in WRITE_TOOLS:` 块 | `test_guard_denies_write_outside_out_or_requests[...]` 12 个参数（`tools/run_cv_probe.py`、`tools/cv_probe.py`、`guard.py`、`isolation_settings.json`、`MANIFEST.json`、`binding.json`、`skills/.../guide.md`、`src/.../tools.py`、`case_data/1f_view.png`、`prescan/.../candidates.json`、`reference/worked_example_plan.json`、`stray_root_file.txt`）+ `test_guard_denies_overwrite_of_tools_run_cv_probe` + `test_guard_r1_denies_write_to_tools_with_innocent_prose_content`；`14 failed, 4 passed`，与 r1 总账一致 |
| `_is_run_prescan_path` 强制 `False` | `test_cv_probe_prescan_echoes_landing_matching_copy_guard`；`test_run_prescan_source_path_is_allowed`（与日志一致） |
| CLI prescan 额外插入 `shifted/` | `test_cv_probe_prescan_echoes_landing_matching_copy_guard`（证明 oracle-side neuter 未遮蔽 CLI 漂移） |
| 删除 missing 检查 | `test_merge_per_image_missing_is_rejected`（其余抽检绿；与日志一致） |
| 删除 extra 检查 | `test_merge_per_image_extra_is_rejected`（其余抽检绿；与日志一致） |
| `glob("*_view.json") -> glob("*_NOPE.json")` | `test_merge_assembles_per_image_views_byte_equal_and_accepts` **以及** `test_merge_per_image_extra_is_rejected`（日志漏报后一条，MINOR-3） |
| 每个 view 注入 `"_mutated": true` | `test_merge_assembles_per_image_views_byte_equal_and_accepts`（其余三条绿；与日志一致） |

---

## 回归结果

```text
pytest -q tests/test_isolation.py tests/test_cv_toolbox.py
102 passed in 34.47s

pytest -q
1881 passed, 10 xfailed, 150 warnings in 315.56s
```

无 `src/agent/judge/**` / reading-typed 并行批失败。

## 返工验收出口

至少须同时闭合：

1. request 中所有写出路径受与直接 Write/Edit 相同或更严的根约束，并有“实际执行 helper 后树外零变化”的 E2E 锁。
2. 非 Bash 参数改为 path-role/content-role 分流；bare `case_tests` 与 bare escaping symlink 必须 deny，合法 prose 仍 allow。
3. build/guard 拒绝 allowed root symlink；`out -> tools` 联合探针必须 deny。
4. S1 一致性测试解析并 stat kickoff 实际指针；pointer-only `.missing` neuter 必须红。
5. 修正 S4 neuter 总账；明确裁定损坏 `output.json` 是报错还是 fallback。若沿原派工骨架，应恢复报错。
