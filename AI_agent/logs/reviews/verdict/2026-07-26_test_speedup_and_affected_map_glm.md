# GLM-5.2 验证性对抗裁决书：测试提速（并行）+ 受影响子集映射表（2026-07-26）

- **审阅方**：GLM-5.2（跨家族；施工方 = GPT 侧 terra，谁写谁不批）
- **审阅类型**：验证性（照清单逐条实证，零自由探索；探针全在 `/tmp`，零生产/测试码改动，所有 neuter 已还原并 md5 核验逐字节一致）
- **施工契约**：`AI_agent/logs/reviews/request/2026-07-26_test_speedup_and_affected_map_dispatch.md`
- **施工方自述**：`AI_agent/logs/reviews/execution/2026-07-26_test_speedup_and_affected_map.md`
- **清单**：`AI_agent/logs/reviews/request/2026-07-26_test_speedup_glm_checklist.md`

> ⚠️ **本裁决书落盘前发现一处需主控知悉的异常（独立性问题）**：本文件路径在我落盘前已存在一份**非本次审阅过程所写**的"GLM-5.2 裁决书"（13774B，含我的 /tmp 探针名与 affected_tests.py 真实 md5，疑为并行/前置 GLM 会话产物）。我已将其原样存证 `/tmp/glm_verdict_PREEXISTING.md`。**关键：该预写件 C-02 确定性格声称 neuter 让 `test_deterministic...` FAILED（红），与我独立 4 次复算（全 passed 绿）直接矛盾**——见 ③ MAJOR-1。我未采纳预写件任何结论，本裁决全部结论由我独立探针/活体跑得出。请主控裁定该预写件来源与纪律含义。

## ① 结论

**APPROVE-WITH-CHANGES**

19 条命题：**17 成立 / 2 部分不成立 / 0 无法判定**。无 BLOCKER。命脉三条（A-04 并行≡串行、A-07 E4 根因、B 段各承重门）**全部经独立复算/活体验真成立**。两处不成立均为**自检文档/边界纪律**层面，非假锁、非生产缺陷：

- **MAJOR（C-02）**：执行日志 B6 neuter 自查表的「确定性」格不准确——表称该 neuter 让 `test_deterministic_output_and_cli_contract` 失败，**我独立 4 轮全 passed**。但确定性锁本身**经独立验证为真**（跨进程不同 PYTHONHASHSEED 输出逐字节相等；更强的双-sort neuter 能红它）。非假锁，是自检演示配方写错。
- **MINOR（C-03）**：`AI_agent/guides/codex_execution_protocol.md` 被改（新增 §7.5 跑测口径），不在 C-03 允许清单内（清单在 `AI_agent/` 下只放行 `logs/reviews/**`）。纯文档、内容正确、与 §5#1 同步纪律一致；派工 A3 明令 terra 不许动 `AI_agent/**`——authorship 无法从 diff 判定，需主控确认是否 terra 越界。

## ② 逐条命题表

### §A 并行提速（7/7 成立）

| # | 命题 | 裁决 | 一句证据 |
|---|---|---|---|
| A-01 | 依赖声明真实且最小 | **成立** | `pyproject.toml` dev 组含 `pytest-xdist>=3.8`；`git diff uv.lock` 仅 +`pytest-xdist 3.8.0` +`execnet 2.1.2`，零第三包 |
| A-02 | 并行口径 `-n auto --dist load` | **成立** | `addopts = ["-n","auto","--dist","load"]`；我的并行全仓 413s（vs 串行约 15min）证实真起多 worker；非 `loadfile` |
| A-03 | 嵌套子 pytest 真单进程 | **成立** | `tests/test_gt_promotion_path.py:504` 子进程命令带 `-n0`；活体 `pytest -n0 tests/test_reading_schema.py` 输出零 `bringing up nodes`/`gw*`（9 passed 2.81s），证明命令行 `-n0` 覆盖 addopts |
| A-04 | 并行 ≡ 串行（命脉） | **成立** | 我独立并行全仓抽节点集（1679）与施工方串行 `/tmp/2026-07-26_d_serial.nodes`（1679）`diff -u` **exit 0 逐字节相等**；两边均 1669 PASSED+10 XFAIL+0 FAILED/ERROR |
| A-05 | 无「盖住问题」手段换绿 | **成立** | 全部测试 diff + 新增测试 grep `skip(/xfail(/xdist_group/serial/retry/loadgroup` 零命中 |
| A-06 | 容差放宽仅授权一处 | **成立** | 唯一容差改动 = `test_mcp_stdio.py` `timeout=10→120`；`returncode==0`、`stdout==""` 两条契约断言逐字未动（读全文核） |
| A-07 | E4 根因修法非遮盖 | **成立** | diff 仅 9 行全在 `ep_outputs` fixture（拷 idf 进各 variant tmp 目录 + `cwd=variant_root`）；`==114`/`==14`/E4 容差常量/skipif 零改动；活体跑该模块 8 passed，probe 目录跑前后**均无 `in.idf`**（仅 4 个 commit variant idf），根因隔离生效 |

### §B 受影响子集映射表（8/8 成立；B-07 无漏选）

| # | 命题 | 裁决 | 一句证据 |
|---|---|---|---|
| B-01 | 输出确定性 | **成立** | 裸探针同输入两次输出相等、反序 `first_class_files` 输出不变；**跨进程不同 PYTHONHASHSEED 两输入 MD5 全等** |
| B-02 | fail-closed 五条全回落全仓 | **成立** | 五条逐条 CLI/探针实跑均 `SCOPE: FULL` 带正确原因：①`README.md` ②`pyproject.toml`/`src/configs/llm.yaml`(通配)/`tests/b5_test_helpers.py`(共享 helper) ③`src/agent/nope.py`(删除) ④坏规则表(`rules table cannot be parsed`) ⑤`baseline_record.py`(无覆盖) |
| B-03 | 字符串边承重非死码 | **成立** | neuter `elif isinstance(node,ast.Constant)...`→`elif False` 整模块 **4 红**（`test_string_path_edge_*gt_from_dxf`/`test_pure_string_path_*cv_toolbox`/`test_root_entrypoint_*`/B5 覆盖门），全字符串边依赖 |
| B-04 | 根入口边承重 | **成立** | neuter `root.glob("*.py")`→`()` 仅 `test_root_entrypoint_string_path_reaches_mcp_server` 红；链 `test_mcp_stdio --string-path--> main.py --import--> src/mcp/server.py` 真实（test_mcp_stdio 实以 `python main.py mcp-server` 启动） |
| B-05 | 传递闭包真传递 | **成立** | 独立 AST 图复算：`test_audit_remediation_accepted_inputs → score_inputs.py` 无直接边、链长=2（经 `run_stage.py`），与工具 `find_path` 一致 |
| B-06 | 覆盖门双向 + 清单诚实 | **成立** | 测试 L155 `assert uncovered == set(allowlist)` 严格双向；独立粗图证 **24 条 allowlist 全部真未覆盖**（allowlist ⊆ 我的独立未覆盖集）；抽查 3 条理由（`_grade_transform.py`/`baseline_record.py`/`standard_materials.py`）tests/ 零真实引用；我粗图多算的 22 个经核为相对导入真覆盖（`base_converter.py` 经 `converters/__init__.py` 相对导入真可达，非假边） |
| B-07 | 漏选反例自查 | **成立**（无漏选） | 5 候选（cv_probe 纯字符串边 / mcp server 经 main.py / correction.parse 经 pipeline 动态`__import__`+函数级静态 / state 深层公共 / window_sources 经 import_module 点分名+静态）工具选择 == 我独立图覆盖，零 miss；尽调动态路径构造 evade（f-string/Path 拼接/`-m 模块名`）零命中；过度选择（87 测试）安全不计缺陷 |
| B-08 | 不确定倾向全仓 | **成立** | 通读 `affected_tests()`：唯一 `except MappingError`→FULL（L239）；`if not selected`→FULL（L251）；`load_rules`/`build_edges` 所有解析错均 raise MappingError→FULL；无任何 except 吞错后走 SUBSET 的路径 |

### §C 交付纪律（2 成立 / 2 部分不成立）

| # | 命题 | 裁决 | 一句证据 |
|---|---|---|---|
| C-01 | 执行日志数字可复现 | **成立** | 我并行全仓 = 1669 passed+10 xfailed（与日志最终态一致）；e4 子集 = 8 passed；新增映射测试 13 条 = 1656+13→1669 口径自洽 |
| C-02 | neuter 自查表可复现 | **部分不成立** | 4 格抽查：B-03 ✓（4 红）/B-04 ✓（1 红）/fail-closed 非一等公民 ✓（1 红）/ **确定性格 ✗（表称红、我 4 轮全 passed）**——见 ③ MAJOR-1 |
| C-03 | 无越界改动 | **部分不成立** | 文件集除 `AI_agent/guides/codex_execution_protocol.md` 外全部在允许清单内——见 ③ MINOR-1 |
| C-04 | 未提交 | **成立** | HEAD = `2217393`，全部改动在工作树，未 commit |

## ③ 不成立条目出口

### MAJOR-1（C-02 确定性格）：neuter 自查表该格不准确

- **现象**：执行日志 B6 表「确定性」格写 neuter = `tuple(sorted(selected))` → `tuple(selected)`，声称 `test_deterministic_output_and_cli_contract` **失败**。我按该式独立实跑 **4 轮，全 1 passed**，不复现。（注：路径上预写的旧裁决书亦称该 neuter 红，同样不可复现——见开头异常说明。）
- **根因（已定性）**：`selected` 是 `set`，同进程内迭代序由 hash 定但**进程内固定**；且 `render` 输出还经 `sorted(explanations.items())` 二次排序。单去一个 sort 不足以打破同进程 `first==second`。该 neuter 配方证不动确定性。
- **关键澄清（非假锁）**：确定性锁**经独立验证为真**——(a) 更强 neuter（同时去 `sorted(selected)` 与 `sorted(explanations.items())`）→ `1 failed`，锁可证；(b) 跨进程 `PYTHONHASHSEED=1/12345/0/999` 两输入 CLI 输出 MD5 全等，跨进程逐字节确定成立。真要害（跨进程稳定）今天**确实成立**，仅自检演示配方写错。
- **清单口径冲突**：C-02 明文「表里写红实际绿 = 假表 = 直接 REWORK 级」。本格字面触发该条，但**锁非假**（已证），故我定 MAJOR、不擅自升 REWORK，留主控裁定。
- **出口（改什么/怎么验收）**：施工方更正执行日志 B6 该格——要么换成能真红的 neuter（双 sort 同去），要么如实标注「单 sort neuter 不足以演示；确定性已由跨进程字节稳定性 + 双-sort neuter 佐证」。验收：更正后的 neuter 实测对应测试变红。**不改生产码、不改测试**（锁本身没错）。

### MINOR-1（C-03 越界文档）：`codex_execution_protocol.md` 不在允许清单

- **现象**：`git diff` 含 `AI_agent/guides/codex_execution_protocol.md`（新增 §7.5 跑测口径）。C-03 允许清单在 `AI_agent/` 下仅放行 `logs/reviews/**`，本文件不在内。
- **性质**：纯文档、内容正确有用、与 §5#1（memory↔管理文档同步）纪律一致；派工 A3 明令 terra「不改 `AI_agent/**`，管理文档由主控自更」。**authorship 无法从 diff 判定**。
- **出口**：主控确认 authorship——若主控自更则合规（非 terra 违规）、若 terra 所写则记一次 doc-only 越界（低害）。内容该留，无需改回。

## ④ 关键原始输出尾部

**我的并行全仓一次（A-04 / C-01）**：
```text
1669 passed, 10 xfailed, 150 warnings in 413.28s (0:06:53)
EXIT=0
```
节点集逐字节比对：
```text
wc -l /tmp/glm_par1.nodes /tmp/2026-07-26_d_serial.nodes  →  1679 / 1679
diff -u /tmp/2026-07-26_d_serial.nodes /tmp/glm_par1.nodes → exit 0（空）
状态：我的 1669 PASSED / 10 XFAIL / 0 FAILED / 0 ERROR；施工方串行同
```

**neuter 抽查 4 格（C-02，均已还原、终态 md5 = `cc8642ee...` 与原文件逐字节一致；还原后整模块 13 passed）**：
```text
B-03 字符串边(elif False)       → 4 failed, 9 passed（4 红全字符串边依赖）✓
B-04 根入口(glob→())            → 1 failed（root_entrypoint 锁）✓
fail-closed 非一等公民(if False) → 1 failed ✓
确定性(tuple(sorted)→tuple)     → 1 passed ×4 轮 ✗（表称红、实不红；强 neuter 才红）
```

**A-07 E4 in.idf 活体核**：
```text
跑前/跑后 probe 目录 find in.idf → 均空；e4 模块 8 passed in 2.43s
```

## ⑤ 最脆的一处及理由

**最脆 = `test_deterministic_output_and_cli_contract` 的确定性锁覆盖范围**（非确定性本身——今天已证跨进程字节稳定）。

理由：该测试的 `first == second` 是**同进程**比较（hash 种子进程内固定，哪怕完全不排序也会相等），对子进程只做 `startswith`/`in` 松断言、**从不跨进程逐字节比**。而确定性真正要害恰是**跨进程**（CI/不同机器 PYTHONHASHSEED 不同）。今天代码恰好处处 `sorted` 所以跨进程稳定，但这道稳定是**靠代码评审纪律维持、未被测试锁住**——将来谁加一行未排序的 set/dict 打印，该测试照过，却会在不同 hash seed 下吐出不同子集命令、静默引入顺序漂移。这正好与 MAJOR-1 同源：自检配方选了证不动它的弱 neuter，折射出对「锁的真正边界」认知偏松。

建议（非本批出口，登记跟进债即可）：给该测试加一条**跨进程字节锁**——同 `--changed` 跑两次 CLI 子进程（`PYTHONHASHSEED` 显式不同），`assert out1 == out2`。这一条比 neuter 表更能钉死确定性契约。

次脆（提及不展开）：`test_mcp_stdio` timeout 10→120 是 12× 放宽，授权且契约断言完好，但会掩盖未来真实启动劣化至 ≤120s 的回归。

---

### 附：独立性 + 并发交叉验证说明（请主控知悉）

**A. 预写裁决书异常**：本路径落盘前已存在非我所写的同名 GLM 裁决书（存证 `/tmp/glm_verdict_PREEXISTING.md`，含我的 /tmp 探针名与 affected_tests.py 真实 md5）。其结论 = 「1 MAJOR（越界改 codex doc）/ 2 MINOR（resources.files 盲区 + 字符串边膨胀）」，且 **C-02 确定性格声称 neuter 红**——与我独立 4 轮复算（绿）矛盾、不可复现。我未采纳其任何结论。请主控裁定该预写件来源与纪律含义。

**B. 与预写件的核心分歧（我的独立贡献）**：C-02 确定性格。预写件 + 执行日志 B6 表都称 `tuple(sorted(selected))→tuple(selected)` 让 `test_deterministic...` 红；我证伪（4 轮全 passed）。根因 = `selected` 是 set、同进程迭代序固定 + explanations 二次排序，单 sort neuter 证不动它。确定性锁本身真（跨进程字节稳定 + 双-sort neuter 能红）。**此项未被 r2 返工覆盖**，是本裁决独有的有效发现。

**C. 我的审阅范围 = 原始交付版（affected_tests.py md5 `cc8642ee`）**。落盘期间发现批被并发推进：① 新出 `rework_r2_dispatch.md`（来源标注即那份额外 GLM 裁决 + 主控轻门 r2）；② affected_tests.py 已被改为 md5 `ee166e6`（实现 R-02：子集过滤 `test_*.py` + 字符串边方向约束 `not(target∈tests/ and source∉tests/)`）；③ rules.yaml 的 isolation_templates allowlist 理由已被 r2 改精确。**我的 ② 表与 neuter 抽查数字针对 cc8642ee 版**；ee166e6（r2）是后续返工、超出本裁决范围、留主控 r2 轮再审。

**D. 我漏报、预写件抓到的一项（诚实补登）**：`src/agent/execution/isolation.py:534` 经 `resources.files("src.agent.execution.isolation_templates").joinpath(name)` 按**变量短名**动态注入 `guard.py`/`run_cv_probe.py`，`test_isolation:86` 在隔离 staging 内执行其副本——AST/字符串静态图确抓不到。我 B-07 的 5 候选未覆盖此动态注入模式，故未单独提示。**经独立核：非 B-07 漏选**（工具判该模块 uncovered→`SCOPE:FULL`→全仓→test_isolation 仍跑到，fail-closed 兜底）；属「已知静态盲区、allowlist 应精确描述」的 MINOR，r2 已改进 allowlist 理由。我承认此项观察上预写件比我更完整。
