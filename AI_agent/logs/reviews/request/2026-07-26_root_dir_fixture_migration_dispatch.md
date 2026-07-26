# 派工单：根目录清理 + 测试夹具入库（2026-07-26）

- **施工方**：GLM-5.2（用户拍板）
- **审阅方**：GPT 侧 **sol**（执行审升一档·跨家族·谁写谁不批）
- **主控**：轻门（独立全量 + 亲核 diff + 裁决）
- **基线**：`HEAD = c912f03`（工作树干净）·全仓 **1671 passed / 10 xfailed / 0 failed**（主控实测 4:34，默认并行）

## 0. 这批要解决的真问题（不是洁癖）

根目录有两个未授权目录 `logs/` 与 `output/`。用户 2026-07-26 立规矩：**未经授权不许在仓库根目录落文档/新目录**，过程痕迹一律归 `AI_agent/logs/`。但清理之前先看清一件更重的事：

**根 `logs/experiments/` 里的文件是 4 个测试文件的活输入，却不在版本控制内**（`.gitignore:7` 的 `20*_*/` 把所有日期命名目录都忽略了）⇒ **换台机器 / 新克隆，这几个测试会 skip 或红，绿只绿在这台机器上**。这已经是同型问题的第三次（07-25「用户签收的候选包整个不在 git 里」、07-26「算清单指纹的代码只存在于未入库脚本」）。所以本批的实质 = **把测试真正依赖的输入变成受版本控制的夹具**，顺带让根目录干净。

## 1. 主控已核实的事实（不用再查，直接用）

| 事实 | 证据 |
|---|---|
| `logs/experiments/2026-07-24_sm24_gt_review/source.dxf` 与**已入库**的 `case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf` **字节相同** | 两边 md5 均 `79d19b210c2cd1e75df3721fd44c3fa3` ⇒ **不需要搬 DXF，测试改指已入库那份即可** |
| 真正需要入库的只有 **6 个 JSON、合计约 80 KB** | 见 §2 表 |
| 其余约 **15M 是 PNG / 派生 DXF** | 由源图 + 冻结 request **逐字节可重生成**（07-26 可复现地基）；签名证据已随转正入库在 `case_tests/test_baseline/gt/sm24_anchor/review/`（5 份受控） ⇒ **用户拍板：直接删** |
| **夹具落点不能用日期命名目录** | `.gitignore:7` `20*_*/` 忽略任何 `20xx_xxx/` 目录（`AI_agent/logs/experiments` 下那 39 个被跟踪文件是当年 `git add -f` 硬塞的，别学） |
| 真正依赖根 `logs/` 的是 **4 个**测试文件 | `test_gt_overlay.py`、`test_gt_promotion_path.py`、`test_tarch_converter_reproducibility.py`、`test_tarch_elevation_must_red.py`。另两处是**假线索**：`test_gt_discipline.py:76` 只在文档字符串里提到、`test_checks_reading_correction.py:20` 指的是 `AI_agent/logs/`（合规，别动） |

## 2. 工作包 A：测试夹具入库 + 根 `logs/` 清零

**A1 建夹具目录**（名字自定，但**不得**日期命名；建议 `tests/fixtures/sm24_review/`，两个来源包各一个子目录以免混淆），把下列 6 个文件复制进去：

| 现位置 | 大小 |
|---|---|
| `logs/experiments/2026-07-24_sm24_gt_review/request_v3.json` | 6 KB |
| `logs/experiments/2026-07-24_sm24_gt_review/request_v3_calibrated.json` | 16 KB |
| `logs/experiments/2026-07-25_sm24_gt_review/request_v3_calibrated.json` | 16 KB（**与上一行不是同一个文件**，别去重） |
| `logs/experiments/2026-07-25_sm24_gt_review/review_annotations.json` | 1.8 KB |
| `logs/experiments/2026-07-25_sm24_gt_review/manifest.json` | 17 KB |
| `logs/experiments/2026-07-25_sm24_gt_review/gt/gt.json` | 21 KB |

**A2 夹具必须真入库**：`git check-ignore -v <每个夹具文件>` 必须**无输出**（否则换个不被忽略的落点，**不许**用 `git add -f`）。夹具目录里放一份简短 `README.md`：这些文件是什么、来自哪次审阅包、如何重生成（指向 `build_review_bundle` 那条链）。

**A3 改 4 个测试文件的路径常量**（只改路径，**断言/容差/期望值一字不许动**）：
- `tests/test_gt_overlay.py`：`:156` 一带的 07-24 包 root、`:349` 的 `_SM24_REVIEW_BUNDLE`（读 `gt/gt.json` 与 `manifest.json`）
- `tests/test_gt_promotion_path.py`：`:24/:25` 的 `REQUEST`/`ANNOTATIONS`，**以及 `:478/:479` `_mirror_repo` 的拷贝清单**（25 格变异矩阵靠它把夹具复制进镜像仓库——漏了这处矩阵会整片红）
- `tests/test_tarch_converter_reproducibility.py`：`:21/:22`
- `tests/test_tarch_elevation_must_red.py`：`:22/:23`（`source.dxf` 改指已入库那份）
- `tests/test_gt_discipline.py:76` 的文档字符串顺手改准（纯文字）

**A4 fail-closed（本批命脉，别偷懒）**：夹具缺失必须**硬红**，不许 skip、不许软路径静默退化。已知软路径：`tests/test_tarch_converter_reproducibility.py:28` 的 `if not source.exists():` —— 查清它现在缺文件时到底会 skip 还是红，改成硬失败（缺夹具 = 仓库损坏，不是"环境没准备好"）。**其余三个文件同样自查一遍有没有类似软路径。**

**A5 删根 `logs/`**：确认无人再引用后整目录删除（15M 派生件按用户拍板直接删，不备份）。

## 3. 工作包 B：根 `output/` 清零

- 根因：`main.py:24` 的 loguru sink `log_file_path=Path(f"./output/logs/{logger_time}.log")` —— **import 一次就建一个文件**（绝大多数零字节；跑测试也会触发，主控已删掉 478 个存量）。
- 改法自定，二选一：① sink 惰性化（真有日志才建文件）② 改指到仓库外或 `AI_agent/logs/` 下**非日期命名**的 gitignored 运行时目录。**不许**只删目录不改代码（下次 import 又长出来）。
- 同步删 `.gitignore` 里的 `output/` 条目（该行因此失去意义）+ 删空目录。
- 主控已 grep：全仓只有 `main.py:24` 写这个路径；你自己再复核一遍（含 `src/`、`scripts/`、`docker/`、MCP）。

## 4. 验收（缺一条即返工）

1. **根目录只剩** `README.md` / `main.py` / `pyproject.toml` / `uv.lock` + 既有目录（`AI_agent backup case_tests data docker scripts skills src tests tests_scripts`）；`logs/` 与 `output/` **都不存在**。
2. **全仓绿且计数不降**：默认并行跑一次，`1671 passed / 10 xfailed / 0 failed`（新增夹具锁可使 passed 上升；**下降或出现 skip 就是空跑**）。原始输出尾部进执行日志。
3. **fail-closed 活体证明（交付物）**：把夹具目录临时改名（**在 `/tmp` 的仓库副本里做，不许在工作树改了再还原**——主控随时在跑门），证明那 4 个文件的相关用例**变红而不是 skip**，把实跑输出贴进执行日志。
4. **变异矩阵仍全绿**：`tests/test_gt_promotion_path.py` 那 25 格（`-m mutation`）必须照跑不误——它依赖 `_mirror_repo` 把夹具复制进镜像仓库。
5. **`git check-ignore`** 对每个夹具文件无输出（真入库，非 force-add）。
6. 中间轮用 `python scripts/tool_scripts/affected_tests.py --changed <你改的路径>...` 算子集并把它输出的**跑测声明**贴进执行日志。

## 5. 纪律

- **不 commit、不 push**。
- **不改 `AI_agent/**`**，唯一例外 = 执行日志 `AI_agent/logs/reviews/execution/2026-07-26_root_dir_fixture_migration.md`（新建）。**尤其不要碰 `AI_agent/guides/`**（上一批施工方就因为改它被判越界）。
- 除本单点名处，不动任何测试的断言/容差/期望值；不许加 skip/xfail/retry 换绿。
- `src/` 只允许动 §3 说的 `main.py` 那一处（`main.py` 在仓库根、不在 `src/`）。
- 全仓测试默认并行（`addopts` 有 `-n auto`），要串行显式 `-n0`；长跑后台重定向 + 轮询。
- 回主对话只给简报：改了哪几个文件 / 测试计数 / 逐条验收结论 / **review-ask**（没把握或做了取舍的地方，没有写 none）。
