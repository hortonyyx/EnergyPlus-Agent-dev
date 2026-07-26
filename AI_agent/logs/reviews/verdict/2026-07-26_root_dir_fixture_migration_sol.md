# 裁决：根目录夹具迁移（2026-07-26）

## ① 结论

**APPROVE**

本批 8 条命题均成立；没有 BLOCKER / MAJOR / MINOR 级的不成立项。施工方关于 `.gitignore` 保留 `output/` 的取舍正确。其自述的“16 个既有 output 目录”数量略少：本机实况是 20 个目录、其中 17 个非空；删规则会暴露 17 个非空目录下 75 个文件。该口径误差不改变取舍，新增注释也准确。

说明：工作区 `.venv` 的 numpy 安装在审阅开始时已残缺（只剩 namespace 目录，直接跑产生 84 个收集错误），因此正式独立复算使用 `uv run --isolated --frozen` 的锁文件隔离环境；未修、未同步工作区虚拟环境。

## ② 逐条命题表

| # | 判定 | 一句证据 |
|---|---|---|
| 1. 夹具真承重 | **成立** | `/tmp/sol_fixture_fc_vuwgdJ/repo` 中改名夹具后，四文件实跑为 **29 failed + 50 errors + 23 passed + 0 skipped**，代表报错是缺 `tests/fixtures/sm24_review/...json` 的 `FileNotFoundError`，与施工方量级精确一致。 |
| 2. 没有静默空跑 | **成立** | 正式全仓为 **1671 passed / 10 xfailed / 0 skipped**；单跑 mutation 为 **25 passed**；直接调用 `_mirror_repo` 后，镜像内 request/annotations 均存在且与源夹具 SHA-256 相同、逐字节相等。 |
| 3. staging 未改变行为 | **成立** | overlay 与 `green_sm24` 的 staged DXF md5 均为 canonical 的 `79d19b210c2cd1e75df3721fd44c3fa3`；must-red 篡改源与 staged 副本 md5 均为 `a32b541a...` 且不同于 canonical；三条真实用例 3 passed，测试 diff 无任何断言、容差或期望值改行。 |
| 4. `main.py` 日志改动 | **成立** | 成功 import 的 `/tmp` 探针前后只存在预置 `data` symlink，`output/`、`AI_agent/`、`*.log` 均未生成；`git check-ignore -v AI_agent/logs/runtime/app.log` 命中 `.gitignore:72:*.log`；直接执行路径实证同时向 stderr 和 `AI_agent/logs/runtime/app.log` 写入同一 INFO sentinel。 |
| 5. 保留 `.gitignore` `output/` | **成立** | 实查 20 个既有 output 目录、17 个非空；在 `/tmp` 删除该规则后，未跟踪量由仅 `.gitignore` 自身增至 76 项，即额外暴露 75 文件/17 根；保留规则与解释性注释均符合实况。 |
| 6. 越界检查 | **成立** | HEAD 仍为 `c912f03`；裁决落盘前 status 仅 `.gitignore`、`main.py`、5 个测试文件、7 个新夹具文件和 request/execution 两份审轨，无 `src/`、`case_tests/`、`AI_agent/guides/` 改动。 |
| 7. 夹具可正常入库且根目录干净 | **成立** | 6 JSON + README 的 `git check-ignore -v` 全部 rc=1/空输出，普通 `git add --dry-run`（无 `-f`）逐个列出；根 `logs/`、`output/` 均 absent，HEAD 未提交。 |
| 8. 主动假绿排查 | **成立（发现非阻断脆点）** | 两个 sm21 `_HAS` 输入当前都存在且受 git 跟踪，故正常新克隆不跳；但在缺资产的 `/tmp` 镜像中，`test_gt_overlay.py` 会 **16 passed + 5 skipped + exit 0**，是本批之外仍存的最脆 fail-open 点。 |

补充内容锁：6 个 JSON 均可解析；三个 conversion request 的 `source_dxf_sha256` 都等于受控 DXF 的 `92885d52...`；07-24 与 07-25 calibrated request 的 SHA-256 分别为 `eea8d2b...`、`34b7d749...`，没有被误去重。旧根目录原件已在审阅前删除，故无法再做“旧原件 vs 新夹具”的现场 `cmp`；上述 schema、内容哈希、消费路径与全套活体锁共同闭合当前交付。

## ③ 不成立项、出口与级别

**无。**

sm21 的 5 个 `skipif(not _HAS)` 是既有、超出本批迁移范围的残余脆点，不构成本批不成立项；建议另批将“受控资产缺失”改为 collection/fixture 硬失败。

## ④ 实跑关键原始输出尾部

### 正式全仓（默认并行）

```text
..........................x....xx.....x................................. [ 98%]
.......................
========== 1671 passed, 10 xfailed, 150 warnings in 249.59s (0:04:09) ==========
```

全输出中搜索 `skip|skipped` 无匹配。

### 25 格 mutation

```text
bringing up nodes...
bringing up nodes...

.........................                                                [100%]
25 passed in 103.83s (0:01:43)
```

### 缺夹具硬红

```text
E FileNotFoundError: [Errno 2] No such file or directory:
E   '/tmp/sol_fixture_fc_vuwgdJ/repo/tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json'
...
29 failed, 23 passed, 14 warnings, 50 errors in 18.47s
```

输出中无 `SKIPPED` / `skipped`。

### staging 活体

```text
...                                                                      [100%]
3 passed in 13.88s

79d19b210c2cd1e75df3721fd44c3fa3  canonical source.dxf
79d19b210c2cd1e75df3721fd44c3fa3  green_sm24/source.dxf
79d19b210c2cd1e75df3721fd44c3fa3  overlay/source.dxf
a32b541ab3a29f4b1aed92f17ebc407d  two_datums.dxf
a32b541ab3a29f4b1aed92f17ebc407d  run/source.dxf
```

### import / runtime 日志

```text
BEFORE_TREE
data l
IMPORT_OK /workspaces/EnergyPlus-Agent-dev/main.py
AFTER_TREE
data l
ABSENT output
ABSENT AI_agent
ABSENT *.log
```

```text
AI_agent/logs/runtime/app.log  f  80 bytes
2026-07-26 15:40:14.977 | INFO | __main__:<module>:9 - SOL_RUNTIME_SENTINEL
APP_EXIT 0
```

### 主动 sm21 缺资产探针

```text
SKIPPED [1] tests/test_gt_overlay.py:33: sm21_anchor case_data / gt not present
SKIPPED [1] tests/test_gt_overlay.py:39: sm21_anchor case_data / gt not present
SKIPPED [1] tests/test_gt_overlay.py:47: sm21_anchor case_data / gt not present
SKIPPED [1] tests/test_gt_overlay.py:54: sm21_anchor case_data / gt not present
SKIPPED [1] tests/test_gt_overlay.py:325: sm21_anchor case_data / gt not present
16 passed, 5 skipped, 16 warnings in 5.83s
```

## ⑤ 最脆一处及理由

**最脆的是 `tests/test_gt_overlay.py` 的 sm21 `_HAS` 总门。** 它把两个受控资产任一缺失解释为环境未准备好，五条用例会静默 skip 且 pytest 仍以 0 退出；这正是“看起来绿其实没跑”的形态。当前两个输入均被 git 跟踪，正式全仓也是 0 skipped，因此不阻断本批；但若发生仓库损坏、错误 sparse checkout 或未来资产迁移，它会比本批已改成 fail-closed 的 sm24 链更晚暴露。
