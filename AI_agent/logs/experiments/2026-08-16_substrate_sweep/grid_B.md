# 摊 B 对照表 —— 守门件↔执行件一致性 / 沙箱环境 / 证据留痕（S-4 / S-5 / S-6）

**席位**：GLM 执行档（glm-5.3）· 2026-08-16
**派工单**：`AI_agent/logs/reviews/request/2026-08-16_substrate_sweep_dispatch_B_glm.md`
**证据产物**：同目录 `B_evidence/`（4 个探针脚本 + 3 份 JSON 报告，全部可复跑）
**锁**：`tests/test_substrate_sweep_policy.py`

## 完成情况

| 段 | 状态 |
|---|---|
| S-5 环境（解释器/库/可写面/可读面/网络） | ✅ 全部实测（`s5_env_probe.py` + `s4_quadrant_probe.py` 的 S5w/S5net 段） |
| S-4 一致性 G1–G9 | ✅ 全部实测（`s4_quadrant_probe.py`，59 格） |
| G8 逐键对账（双向） | ✅ 全部实测（`g8_param_audit.py`） |
| S-6 留痕 F-35/F-50/F-44/F-39 | ✅ 全部实测（`s6_evidence_probe.py`，真 merge ×4 场景） |
| 锁文件 + neuter | ✅ 见 `tests/test_substrate_sweep_policy.py` 与本文 §6 |

## 0. 方法与真实入口

- **staging**：`build_isolation_workspace(case_tests/e2e_tests/sm21_anchor, staging_root=/tmp/ep_isolation/<prefix>_)`（S-6 的 merge 场景用 sm21 私拷 + `provision_view_manifest` formal 模式）。
- **guard**：subprocess 起 `/opt/venv/bin/python -c '<driver> <staging>'`，driver 内 `sys.path.insert(0, staging); import guard; guard.evaluate(stdin payload)` —— guard 的 `_staging_root()` = `Path(guard.__file__).parent` = 真 staging 根。**派工单 ⚠️前提「要在 staging 里 import」核过·成立**（若 import 仓库里的模板 `isolation_templates/guard.py`，其目录无 `out/`、`requests/`，`_assert_writable_roots` 会让一切 deny——所以必须在 staging 里 import）。
- **wrapper**：subprocess 跑 `staging/tools/run_cv_probe.py`，cwd=staging，env=`{PATH, HOME, PYTHONPATH=staging}`（即 `clean_spawn_env` 形态）。
- **四象限**：`guard 判定`（allow/deny + reason）× `wrapper 结果`（直接 subprocess 的 rc/stderr，模拟 guard 放行后的真实执行 / TOCTOU 直调）。
- 探针自身踩过的三个 bug 已修（count_files 前缀、request 形态漏必需参数、overlay_logger fixture 形状），修正后**全量重跑**，下表数字来自重跑后的报告。

---

## 1. S-5 沙箱环境（优先级最高段）

### 1.1 解释器（派工单点名「这一格优先做」）

| 探测 | 结果 |
|---|---|
| 读图器环境（`clean_spawn_env(staging)`）里 `command -v python` | **`/opt/venv/bin/python`**（PATH 首位 `/opt/venv/bin`；`type -a` 两个条目都是它） |
| `command -v python3` | `/opt/venv/bin/python3` |
| `python -c 'sys.executable'` | `/opt/venv/bin/python`，3.12.13 |
| 仓内 `.venv/bin/python` 的 numpy | **坏的**：`numpy.__file__` 为 `None`、`dir(numpy)` 仅 7 项、无 `zeros`/`__version__`（`AttributeError`）；PIL 反而可用（12.2.0） |

**结论（单独回答派工单 §8-4）**：沙箱里读图器敲 `python` 拿到的是 **`/opt/venv/bin/python`（3.12.13，numpy/PIL/scipy 全好）**，不是坏的仓内 `.venv`。派工单 ⚠️前提两条（真环境=/opt/venv；.venv numpy 残缺）**核过·均成立**，但推论不适用：**读图器自写测量代码不会因解释器坏而失败**——08-16 那抽「自写脚本没用来测量」不能用解释器坏解释（与主控 08-16 晚更正一致：F-49 尺子坏才是当时原因，且 F-49 已修，见 §2 G1b）。

### 1.2 库（读图器自己的 `python` 下）

| 库 | import | 版本 |
|---|---|---|
| numpy | ✅ | 2.4.4 |
| PIL | ✅ | 12.2.0 |
| scipy | ✅ | 1.17.1 |

`cv_toolbox.md`「numpy/PIL/scipy 可用」**核过·属实**（在读图器环境里）。

### 1.3 可写面

| 入口\位置 | `out/` | `requests/` | staging 根 | `tools/` | `case_data/` | `guard.py` | `MANIFEST.json` |
|---|---|---|---|---|---|---|---|
| Write 工具（guard 判定） | ✅ allow | ✅ allow | ⛔ deny | ⛔ deny | ⛔ deny | ⛔ deny | ⛔ deny |
| **`python -c 'open(...)…'`（guard 判定）** | — | — | **✅ allow** | （同左，无差别） | | | |
| **`python -c` OS 层实测** | — | — | **真落盘**（`rootwrite_probe.txt` 出现在 staging 根，rc=0） | | | guard 对 `open("guard.py","a")` 判定也是 **allow** | |

**判定：⚠️ 两边不一致（guard 宽、OS 实况严不了）**——写入面这道门只在 Write/Edit 工具形态上；A3 放开 `python -c` 后，**OS 层写面完全不受限**：staging 根可落文件、`guard.py` 自身可被 append/改写（改写守卫 ⇒ 后续所有判定形同虚设）、`access_log.jsonl` 可被清空（擦审计）。派工单预期「其它位置实测拒」对 Write 工具成立、对 python -c **不成立**。登记 **F-52B**。

### 1.4 可读面（只记目录名与文件数）

```
staging 根文件 6：MANIFEST.json binding.json guard.py input_inventory.json isolation_settings.json kickoff_prompt.md
case_data/ 7 · out/ 0 · requests/ 0 · reference/ 1
skills/intake_pipeline/0_reading/ 5（无 judge_rubric.md ✓）
src/agent/reading/cv_toolbox/ 8（+__pycache__ 4）· tools/ 2（run_cv_probe.py + cv_probe.py）
```
（formal build 时另有 `prescan/cv_evidence/...`。）读图器可读到 `guard.py`/`MANIFEST.json`/`binding.json` 全文——属设计内（净室纪律只限制写与外传），如实记录。

### 1.5 网络（只测判定，未真连）

| 形态 | guard 判定 |
|---|---|
| `python -c 'import urllib.request; …'` | ⛔ deny（network egress: urllib） |
| `python -c 'import socket; …'` | ⛔ deny（network egress: socket） |
| `curl http://…` | ⛔ deny（not allowlisted: curl） |

**判定：✅ 与「净室无外传通道」的政策一致**（词法级；威胁模型 2026-08-13 明示不防蓄意绕过）。

---

## 2. S-4 守门件↔执行件一致性（四象限表）

判据：guard 放行的形态 wrapper 必须真能跑；wrapper 会拒的形态 guard 不该毫无痕迹地先放行。

### G1 六授权工具 × 三形态（18 格 + 1 内联格）

| 工具 \ 形态 | 直接 `--key value` | `--request` | `--batch` |
|---|---|---|---|
| crop_zoom | ✅/✅ rc=0 sidecar×3 | ✅/✅ rc=0 sidecar×3 | ✅/✅ rc=0 sidecar×3 |
| wall_line_profiler | ✅/✅ rc=0 | ✅/✅ rc=0 | ✅/✅ rc=0 |
| storey_line_profiler | ✅/✅ rc=0 | ✅/✅ rc=0 | ✅/✅ rc=0 |
| px_m_calibrator（anchors 走文件） | ✅/✅ rc=0 | ✅/✅ rc=0 | ✅/✅ rc=0 |
| window_cc_detector | ✅/✅ rc=0 | ✅/✅ rc=0 | ✅/✅ rc=0 |
| overlay_logger（candidates 走文件） | ✅/✅ rc=0 | ✅/✅ rc=0 | ✅/✅ rc=0 |
| **G1b px_m_calibrator + 内联 anchors JSON（F-49 形态）** | **✅ guard allow / ✅ rc=0** | — | — |

**判定：✅ 两边一致（18+1 格全绿）。** F-49 的「内联 JSON 跑不通」已修（最近提交 `e0367e1` 标题即 F49_F51_Fixed）：guard 侧 `anchors_json` 虽在 `PROBE_PATH_ROLE_KEYS`，内联 JSON 串不含禁词、拼 staging 前缀后仍在 staging 内 ⇒ 放行；wrapper 侧 `JSON_OR_PATH_KEYS` 按 `[`/`{` 分派内联 ⇒ 跑通。
**附带观察（登记 F-55B）**：`overlay_logger` 的 `--candidates-json` 传错形状（传 `{"results":…}` 而非 `[...]` 列表）时，wrapper 报的是**裸 `AttributeError: 'str' object has no attribute 'get'` traceback**（tools.py:711），不是可操作的校验错误——读图器从文档学形状，学错时拿到的是栈不是指导。

### G2 已撤的 prescan-plan / prescan-elevation（4 格）

| 形态 | guard | wrapper |
|---|---|---|
| 直接 `--tool prescan-plan` | **✅ allow**（"allowed run_cv_probe direct arguments"） | ⛔ rc=1，`ValueError: unsupported cv_probe tool: 'prescan-plan'`（裸 traceback） |
| `--request` prescan-plan | **✅ allow** | ⛔ rc=1（同上） |
| 直接 `--tool prescan-elevation` | **✅ allow** | ⛔ rc=1 |
| `--request` prescan-elevation | **✅ allow** | ⛔ rc=1 |

**判定：⚠️ 两边不一致（guard 宽、wrapper 严）。** 撤工具只撤了 wrapper 的 `ALLOWED_TOOLS`（与 guard 的 `PROBE_TOOL_NAMES`——但后者只用于报错提示文案）。guard 的参数键表 `PROBE_DIRECT_PARAM_KEYS` **仍保留 prescan 的 5 个专属键**，且对 `--tool` 的**值**从校验（只校键名）。后果：读图器照旧文档/记忆调 prescan，guard 放行并记一条 allow，然后 wrapper 裸栈崩——「已撤」这件事在守门层不可见。登记 **F-53B**。
（批次形态 `--batch` 里 tool=prescan 同理：guard 的 `_validate_probe_request_data` 不查 tool 值 ⇒ allow、wrapper 拒——与 G2 同根，未单列格。）

### G3 `out_dir` 越界（4 格）

| 形态 | guard | wrapper |
|---|---|---|
| `--out-dir tools/x` | ⛔ deny `request output path must land under out/` | ⛔ rc=1（`output path must land under out/, not 'tools/x'`） |
| `--out-dir requests/x` | ⛔ deny（同上） | ⛔ rc=1 |
| `--out-dir /tmp/x` | ⛔ deny `absolute path outside staging` | ⛔ rc=1 |
| `--out-dir out/../tools` | ⛔ deny `parent traversal token is forbidden` | ⛔ rc=1 |

**判定：✅ 两边一致（4/4 双拒）。**

### G4 `image` 越界（4 格）

| 形态 | guard | wrapper |
|---|---|---|
| 绝对路径 `/etc/passwd` | ⛔ deny `absolute path outside staging` | ⛔ rc=1 |
| 含 `..` | ⛔ deny `parent traversal token` | ⛔ rc=1 |
| 含 `~` | ⛔ deny `home token is forbidden` | ⛔ rc=1 |
| staging 内软链→staging 外 | ⛔ deny `path escapes staging: lnk.png`（symlink 解析） | ⛔ rc=1 |

**判定：✅ 两边一致（4/4 双拒）。**

### G5 `--request` 文件内容含禁词（2 格）

| 内容 | guard | wrapper（TOCTOU 直调） |
|---|---|---|
| `args.image = "../../case_tests/gt.json"` | ⛔ deny `forbidden token: gt.json` | ⛔ rc=1（`..` 被拒） |
| `args.image = "/workspaces/EnergyPlus-Agent-dev/..."`（repo 根绝对路径） | ⛔ deny `forbidden token: /workspaces/EnergyPlus-Agent-dev` | ⛔ rc=1（绝对路径越界被拒） |

**判定：✅ 两边一致**（注：wrapper 直调时只做「越界」不做「禁词」——对这两格恰好同拒；若 request 内容只含 `case_tests` 等禁词而路径本身在 staging 内，则 guard 拒、wrapper 直调不拒。这是设计内分工（词法边界归 guard、路径边界两边都有），如实记录，不算缺陷）。

### G6 `--batch` 边界（5 格）

| 形态 | guard | wrapper | sidecar 产出 |
|---|---|---|---|
| 33 条（超上限 32） | ⛔ deny `probe batch has 33 requests; maximum is 32` | ⛔ rc=1 | **0** |
| 重复 id | ⛔ deny `duplicate probe batch request id: same` | ⛔ rc=1 | **0** |
| 非法 id（`bad id!`） | ⛔ deny（regex 不匹配） | ⛔ rc=1 | **0** |
| 空 requests | ⛔ deny `must contain at least one request` | ⛔ rc=1 | **0** |
| 部分非法（1 好 + 1 条 out_dir 越界） | ⛔ deny `request output path must land under out/` | ⛔ rc=1 | **0** |

**判定：✅ 两边一致 + 零 sidecar（5/5）。**（两边共享 `parse_probe_batch`/`_request_to_argv`，preflight 全量后才执行——「一个都不产出」的属性成立。）

### G7 畸形直接参数（5 格）

| 形态 | guard | wrapper |
|---|---|---|
| 裸参数（`--tool crop_zoom crop_zoom`） | ⛔ deny `unexpected bare argument`（带 `did you mean --tool` 提示） | ⛔ rc=1（同文案） |
| 重复参数（两个 `--image`） | ⛔ deny `repeated probe parameter --image` | ⛔ rc=1 |
| 缺值参数（`--image` 结尾） | ⛔ deny `missing its value` | ⛔ rc=1 |
| 缺 `--tool` | ⛔ deny `direct probe form requires --tool` | ⛔ rc=1 |
| 缺 `--image` | ⛔ deny `direct probe form requires --image` | ⛔ rc=2（cv_probe argparse：--image required） |

**判定：✅ 两边一致（5/5 双拒；缺 --image 一格两边拒绝层级不同但都拒）。**

### G8 参数键逐键对账（两个方向）

**方向 A（guard → 工具）：guard 的 27 键里，有几个没有任何授权工具接受？**

| # | guard 键 | 接受它的授权工具 | 判定 |
|---|---|---|---|
| 1 | tool | 全部（subparser 选择器） | 活 |
| 2–7 | image / out_dir / recipe / bbox / scale / sidecar_name | 全部（`_common`） | 活 |
| 8 | axis | wall_line_profiler | 活 |
| 9–11 | anchors_json / residual_warn_px / residual_warn_m | px_m_calibrator | 活 |
| 12–21 | min_area / min_width / min_height / max_width / max_height / min_aspect / max_aspect / merge_gap / merge_overlap_ratio / merge_iou | window_cc_detector | 活 |
| 22 | candidates_json | overlay_logger | 活 |
| 23 | capability_profile | **无**（仅 prescan-plan/-elevation） | **死面** |
| 24 | no_cc | **无**（仅 prescan） | **死面** |
| 25 | min_strength | **无**（仅 prescan） | **死面** |
| 26 | min_line_len_px | **无**（仅 prescan） | **死面** |
| 27 | label | **无**（仅 prescan） | **死面** |

**方向 B（工具 → guard）：授权工具接受的键（并集 22 = 7 公共含 tool + 15 专属），有没有 guard 不认的？**

| 工具 | 键数 | 不在 guard 27 键里的键 |
|---|---|---|
| crop_zoom | 7 | 无 |
| wall_line_profiler | 8 | 无 |
| storey_line_profiler | 7 | 无 |
| px_m_calibrator | 10 | 无 |
| window_cc_detector | 17 | 无 |
| overlay_logger | 8 | 无 |

**派工单两个 ⚠️前提的核验结果**：
- 「27 键里 5 个只属已撤 prescan ⇒ 死面」——**核过·成立**（capability_profile / no_cc / min_strength / min_line_len_px / label，行为验证：direct 形态带这 5 键 guard 全部 allow、wrapper rc=1/2 拒）。
- 「反方向一个都不缺」——**核过·成立**（22 键全在 guard 表内，零缺）。
- 第二个前提「wrapper 的 `BOOLEAN_FLAG_KEYS = {"no_cc"}` 同理死面」——**核过·成立**（no_cc 仅 prescan 声明；direct 形态 `--no-cc true` 对授权工具 = guard allow + wrapper 折叠成 flag 后 argparse 拒）。
- **附带发现（登记 F-54B）**：guard 的键白名单是**跨工具扁平表**，不校验「键属于该工具」——`--tool storey_line_profiler --axis row`（axis 不是它的参数）guard allow、wrapper argparse 拒。与 G2 同形（guard 宽、wrapper 严），wrapper 注释明说 argparse 每工具校验「strictly finer」是设计选择，但代价 = 一切键级错配都以 argparse 裸错误在 wrapper 层爆炸，guard 层零痕迹。与 F-53B 合并看：「guard 不看 tool 值」是同一根。

### G9 同名 sidecar 第二次调用（3 格，无预期·实测记录）

| 形态 | 第 1 次 | 第 2 次 | 行为 |
|---|---|---|---|
| 显式 `--sidecar-name 001_g9probe` | guard allow / rc=0，写 `001_g9probe.json` | guard allow / **rc=1 `FileExistsError: sidecar already exists`** | **报错（不覆盖、不 append）** |
| `auto` | guard allow / rc=0，写 `001_…json` | guard allow / rc=0，写 `002_…json` | **append-only 递增编号** |

**实测记录：显式名=append-only 语义下的防覆盖报错；auto=递增槽位。**（与 `sidecar.py` docstring 声明一致；guard 对第二次调用不设卡——sidecar 冲突是 wrapper 层的事，判定为 ✅ 一致。）

### S-4 总判

| 组 | 判定 |
|---|---|
| G1（18+1 格） | ✅ 两边一致 |
| G2（4 格） | ⚠️ 两边不一致：**guard 宽（allow + 无 tool 值校验 + 死键仍在表）**、wrapper 严（ValueError 裸栈）→ F-53B / F-54B |
| G3–G7（24 格） | ✅ 两边一致（全双拒） |
| G8 | ✅ 键集零缺；死面 5 键（前提成立） |
| G9 | ✅ 一致（显式报错 / auto 递增） |
| 派工单漏测补格 | S5w python-c 写面（§1.3）⚠️ 不一致 → F-52B；wrapper 形状校验缺失（G1 附带）→ F-55B |

---

## 3. S-6 证据留痕

### F-35：CV 证据在 merge 之后进不进 attempt？

**实测（真 formal staging + 真探针 + 真 merge）**：探针真实产出 `out/cv/cv_evidence/1f_view/001_storey_line_profiler.json`（merge 前 staging 里确认存在）→ merge 成功（attempt 001 accepted）→ **attempt 树里没有任何 cv_evidence**（只有 checks.json / isolation_provenance.json / output.json / isolation_archive/{MANIFEST, guard.py, isolation_settings}.json）；stage 根也没有。`_archive_isolation_artifacts` 只搬 4 个白名单文件，`out/cv/**` 不在内。
**判定：⛔ CV 证据不进 attempt——留在 staging，staging 一清就没了。** 判卷侧/审计侧事后读不到本轮的 CV 证据（F-35 维持未修，实测坐实）。

### F-50：中途状态归档不了

| 形态 | 结果 |
|---|---|
| per-image 文件形态（**kickoff 教的正是这个**）、只有 pilot 一张 `out/1f_view.json` | ⛔ `ValueError: no aggregate output.json and missing per-image view files for expected_output_ids: ['2f_view', 'East_view', 'North_view', 'South_view', 'West_view']`，**零 attempt 归档**（attempts/ 空） |
| aggregate `output.json` 形态、只放 1 张 view | ✅ merge 成功，attempt 001 **filed**（`reading.view_manifest_coverage: fail`，missing 5 张），**accepted=false** |

**判定**：F-50 的报错文案与派工单预期一致（"missing per-image view files"）。**细化**：存在一条合法中途归档通道（aggregate output.json 形态可 filed-not-accepted），但 kickoff 教的 per-image 形态在图未齐时**整单拒收、零归档**——pilot 停等门（08-16 已恢复常态）恰好停在这个形态上 ⇒ 停等时点的东西归不了档。F-50 维持、且「没有任何合法归档通道」的说法要修正为「per-image 形态无通道，aggregate 形态有」。

### F-44 修法实测确认

真 hook（subprocess 跑 `staging/guard.py` + stdin payload，即产品形态）×4 次调用后读 `access_log.jsonl`：

| 调用 | decision | tool_input_excerpt（含参数原文） | executed_code（sha256） |
|---|---|---|---|
| wrapper 直接参数（allow） | allow | ✅ 有（119 字符，含完整命令） | null（无代码执行） |
| `python -c 'print(1+1)'` | allow | ✅ 有 | ✅ `[{"path":"-c","sha256":"df5db254…"}]` |
| Write out/note.md | allow | ✅ 有（content 原文可见） | null |
| `cat case_tests/x` | deny | ✅ 有（deny 面也记） | null |

**判定：✅ F-44 修法实测成立**——allow 面记参数原文 + 被执行代码 sha256，deny 面照旧。

### F-39：缺件有没有门拦

| 缺件 | 门 | 实测 |
|---|---|---|
| 少一张图（per-image 形态） | 有 | merge 整单拒（F-50 文案） |
| 少一张图（aggregate 形态） | 有 | coverage fail → filed-not-accepted，`accept=True` 不可覆盖 block（代码 + 实测 accepted=false） |
| 少 sidecar / CV 证据 | **无** | `src/validator/` 对 `cv_evidence`/sidecar **零引用**（grep 全仓）；叠加 F-35（sidecar 不进 attempt）⇒ 「产物引用的 sidecar 缺失」这个状态不在任何检查的视野里 |

**判定：⚠️ 图有门、sidecar 无门**（F-39 维持）。

---

## 4. 派工单 ⚠️前提 逐条核验汇总

| # | 派工单原文 | 核验 | 结果 |
|---|---|---|---|
| 1 | guard 靠 `_staging_root()` 定位 staging，要在 staging 里 import | 实测 | **成立**（模板目录无 out/requests ⇒ 全 deny） |
| 2 | G2 预期「wrapper 拒；guard 侧记录实际」 | 实测 | **前半成立**（wrapper 拒）·**guard 实况 = allow 且无 tool 值校验**（比「记录实际」更宽，已按实况记录并登记 F-53B） |
| 3 | G6 预期「两边都拒，且一个 sidecar 都不产出」 | 实测 | **成立**（5 格全双拒 + 0 sidecar） |
| 4 | G9「无预期，实测记录」 | 实测 | 显式名报 FileExistsError；auto 递增（append-only） |
| 5 | guard 27 键中 5 个只属已撤 prescan ⇒ 死面 | 逐键+行为 | **成立** |
| 6 | 反方向一个都不缺 | 逐键 | **成立** |
| 7 | `BOOLEAN_FLAG_KEYS={"no_cc"}` 死面 | 逐键+行为 | **成立** |
| 8 | 真环境是 /opt/venv | 实测 | **成立** |
| 9 | 仓内 .venv numpy 坏（08-01 残缺） | 实测 | **成立**（`__file__=None`、无 zeros；PIL 反而好） |
| 10 | ⛔隐含推论「沙箱 python 可能指向坏的 ⇒ 自写测量代码失败」 | 实测 | **不适用**（沙箱 python=/opt/venv，是好的） |
| 11 | F-50 报错文案 ≈ `missing per-image view files` | 实测 | **成立**（逐字吻合） |
| 12 | F-44 修法 = allow 也记参数原文 + executed_code sha256 | 实测 | **成立** |
| 13 | 「G1 两边都通」 | 实测 | **成立**（18+1 格；F-49 内联形态也已通——派工单背景里的 F-49 描述已过时/已修） |
| 14 | S-5 §3「其它位置实测拒」 | 实测 | **Write 工具成立；python -c 不成立**（F-52B） |

（派工单里「派工方错误率 24/24、请主动证伪」——本轮证伪/细化 2 条：#2 guard 实况比预期宽、#14 可写面在 python -c 形态失守；其余 12 条核过成立。）

---

## 5. 缺陷清单（F-52B 起，⛔ 本轮不修）

### F-52B —— 写入面只在 Write 工具形态设防；`python -c` 的 OS 层写面完全敞开（含改写 guard.py 自身）
- **现象**：guard 对 `python -c 'open("rootwrite_probe.txt","w")…'` 判 **allow** 且文件真实落在 staging 根（实测 file_landed=true）；对 `python -c 'open("guard.py","a")…'` 同样 allow。A3 放开 `python -c` 后，`WRITE_ALLOWED_DIRS` 只约束 Write/Edit 工具，OS 层写不受限。
- **影响面**：读图器一条命令可 append/改写 `guard.py`（后续所有判定用被改的守卫）、清空 `access_log.jsonl`（擦审计）、在 staging 根覆盖 `kickoff_prompt.md`/`binding.json` 等。威胁模型（2026-08-13）明示不防蓄意破坏，但这是「一条 easy-path 命令」级别的口子，且与「F-44 让审计可信」的目标直接冲突（审计日志可被同一通道抹掉）。
- **复现**：`B_evidence/s4_quadrant_probe.py` 的 `S5w/python-c-root-write`、`S5w/python-c-append-guard` 格（报告 `s4_quadrant_report.json`）。
- ⛔ 不要修（登记）。

### F-53B —— 已撤的 prescan 工具在守门层不可见：guard 放行 + wrapper 裸栈拒
- **现象**：`--tool prescan-plan`（直接/request/batch 三形态同）guard 全部 **allow**（guard 不校验 `--tool` 的值；prescan 的 5 个专属键也仍在 `PROBE_DIRECT_PARAM_KEYS`），wrapper `ValueError: unsupported cv_probe tool`（**裸 traceback**，rc=1）。
- **影响面**：读图器照旧文档/记忆调 prescan 时，守门层零痕迹（access_log 记一条 allow），失败以裸栈呈现。08-15 撤能力是「改 wrapper 一处」，守门件与 skill 文档的说法没有同步收紧点。
- **复现**：`s4_quadrant_probe.py` G2 段。
- ⛔ 不要修。

### F-54B —— guard 参数键白名单是跨工具扁平表，键-工具错配在守门层不可见
- **现象**：`--tool storey_line_profiler --axis row`（axis 不是它的参数）：guard allow（axis 在 27 键表内）、wrapper argparse 拒（unrecognized）。死面 5 键（F-8 前提5）行为相同：guard allow + wrapper rc=1/2。
- **影响面**：与 F-53B 同根（guard 不看 tool 值）——所有「键合法但工具不对」的错配都漏到 wrapper 层以 argparse 错误爆炸。wrapper 注释明说这是「strictly finer」的设计选择，本条登记的是其守门侧代价，供下轮修 F-53B 时一并定夺。
- **复现**：`g8_param_audit.py` behaviour 段。
- ⛔ 不要修。

### F-55B —— wrapper 对 `--candidates-json`/`--anchors-json` 的形状错误裸抛工具内异常
- **现象**：`overlay_logger` 的 candidates_json 传 `{"results":[…]}`（dict 而非 list）⇒ `AttributeError: 'str' object has no attribute 'get'` 裸 traceback（tools.py:711），非可操作校验错误。第一轮探针自己就撞上了。
- **影响面**：读图器从文档学形状，学错时拿到栈不是指导——弱模型一轮预算就烧掉（与 F-45「文档示例被 DENY」同族的可用性缺陷）。
- **复现**：`B_evidence/f55b_repro.txt`（staging 里写 `requests/bad_cand.json` = `{"results":[…]}` 后跑 `python tools/run_cv_probe.py --tool overlay_logger --image case_data/1f_view.png --out-dir out/f55 --candidates-json requests/bad_cand.json` ⇒ rc=1 裸 `AttributeError`）。
- ⛔ 不要修。

### 维持未修（实测再坐实，无新编号）
- **F-35**：CV 证据不进 attempt（§3）。
- **F-50**：per-image 形态中途归档零通道（§3；aggregate 形态可 filed——表述细化）。
- **F-39**：sidecar 缺失无门（§3）。

---

## 6. 锁（`tests/test_substrate_sweep_policy.py`）

全部走真实入口（真 staging + 真 guard 子进程 `guard.evaluate` + 真 wrapper 子进程；formal merge 场景用 sm21 私拷 + provision）。
实跑结果：**38 passed + 4 xfailed（strict），零红**（`pytest tests/test_substrate_sweep_policy.py -n0 -q`）。

**正锁（16 个测试函数，parametrize 展开 38 条）**：

| # | 测试 | 锁的属性 |
|---|---|---|
| 1 | `test_g1_six_tools_three_forms_guard_and_wrapper_agree` | 六工具直接形态：guard allow + wrapper rc=0 + sidecar 真落盘 |
| 2 | `test_g1_request_and_batch_forms_pass` | request/batch 形态同上（crop_zoom） |
| 3 | `test_g1b_inline_anchors_json_direct_form_passes` | F-49 回归：内联 anchors JSON 两边都通 |
| 4 | `test_g3_out_dir_escapes_denied_by_both_sides`（4 格） | G3 四形态双拒 |
| 5 | `test_g4_image_escapes_denied_by_both_sides`（4 格） | G4 四形态双拒（含软链） |
| 6 | `test_g6_batch_edges_denied_and_zero_sidecars`（5 格） | G6 双拒 + 零 sidecar |
| 7 | `test_g7_malformed_direct_args_denied_by_both_sides`（5 格） | G7 双拒 |
| 8 | `test_g8_dead_keys_and_no_missing_keys` | 方向 A 死面恰为 5 键 / 方向 B 零缺（键集从 cv_probe 源机械提取） |
| 9 | `test_g8_wrapper_boolean_flag_keys_are_dead_surface` | `BOOLEAN_FLAG_KEYS` ⊆ {no_cc} 且属死面 |
| 10 | `test_g9_sidecar_semantics` | 显式名第二次 FileExistsError；auto 两次 = 001/002 |
| 11 | `test_f53b_wrapper_still_refuses_prescan` | G2 的 wrapper 侧（当前正确行为） |
| 12 | `test_s5_interpreter_and_libraries_in_reader_env` | 读图器环境 python = /opt/venv/bin/python（红 = 环境变了要重核）+ numpy/PIL/scipy 可 import |
| 13 | `test_s5_network_shapes_denied`（3 格） | urllib/socket/curl deny |
| 14 | `test_s5_write_tool_surface`（7 格） | Write 工具面 out/requests allow，其余 deny |
| 15 | `test_f44_access_log_allow_carries_excerpt_and_executed_code` | 真 hook 后 allow 有 excerpt、python -c 有 executed_code sha256、Write 记 content、deny 面照记 |
| 16 | `test_f50_partial_archive_gates` | per-image 单张 merge 报 `missing per-image view files` + 零 attempt；aggregate 单张 filed 且 accepted=None |

**xfail 锁（strict=True，3 个测试函数 / 4 条；断言的是「修好后应然」，现状红 ⇒ xfail；修好后变绿 ⇒ strict 报红提醒摘除）**：
1. `test_f53b_withdrawn_prescan_should_be_denied_by_guard`（direct+request 两格）—— 应然：guard 拒已撤工具；现状 allow（F-53B）。
2. `test_f52b_python_c_root_write_should_be_denied` —— 应然：guard 拒 python -c 写 staging 根 + 文件不落盘；现状 allow 且落盘（F-52B）。
3. `test_f35_cv_evidence_should_reach_attempt` —— 应然：merge 后 CV 证据进 attempt；现状不进（F-35）。

⛔ 说明：**没有一把锁把错误行为写成正向预期**——xfail 体断言的是修好后的正确行为；现状锁（#16）锁的是门本身的设计行为（拒绝/不 accept），不是缺陷行为。

---

## 7. neuter 记录（锁必须自证有分辨力）

判据：把被测实现临时改坏 ⇒ 锁红 ⇒ 还原 ⇒ `git diff` 零残留。被 neuter 的都是 `src/agent/execution/isolation_templates/guard.py`（模板；锁测试每次新建 staging，改模板立即生效），每把快进快出。

| # | 锁 | 改法（临时） | 锁反应 | 还原 |
|---|---|---|---|---|
| 1 | G8 | 从 `PROBE_DIRECT_PARAM_KEYS` 删 `"axis",`（制造「工具接受但 guard 不认」） | `test_g8_dead_keys…` **红**（方向 B 命中 `['axis']`） | diff=0 ✅ |
| 2 | G6 | `MAX_PROBE_BATCH_SIZE` 32→64 | `test_g6…[33-entries]` **恰好红这一格**、其余 4 格仍绿（零连带） | diff=0 ✅ |
| 3 | G3 | `REQUEST_OUTPUT_ROLE_KEYS = ("out_dir",)` → `()` | `test_g3…[tools]` `[requests]` **红两格**；`[abs-tmp]` `[traversal]` 仍绿——符合分层（那两格归词法层管，锁测的正是输出角色层） | diff=0 ✅ |

还原后全文件重跑：**38 passed + 4 xfailed**，`git status` 零已跟踪文件改动。（命令与原始输出见 `B_evidence/neuter_log.md`。）

---

## 8. 没做完的格子

无。派工单 §3/§4/§5 全部格子已实测；锁 38 绿 + 4 strict xfail 零红。

**证据产物索引（`B_evidence/`）**：
- `s5_env_probe.py` + `s5_env_report.json` —— 解释器/库/可读面
- `s4_quadrant_probe.py` + `s4_quadrant_report.json` —— G1–G9 + S5w/S5net 全格原始判定
- `g8_param_audit.py` + `g8_param_audit_report.json` —— 键级对账 + 行为验证
- `s6_evidence_probe.py` + `s6_evidence_report.json` —— F-35/F-50/F-44 真 merge 实测
- `f55b_repro.txt` —— F-55B 复现
- `neuter_log.md` —— 三把 neuter 原始记录
