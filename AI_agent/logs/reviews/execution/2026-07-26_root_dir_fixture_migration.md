# 执行日志：根目录清理 + 测试夹具入库（2026-07-26）

- **施工方**：GLM-5.2
- **派工单**：`AI_agent/logs/reviews/request/2026-07-26_root_dir_fixture_migration_dispatch.md`
- **基线**：HEAD `c912f03`，全仓 1671 passed / 10 xfailed / 0 failed
- **交付态全仓**：**1671 passed / 10 xfailed / 0 failed / 0 skipped**（删 logs/output 后重跑，222.10s）—— 计数不降、无 skip

---

## 0. 改了哪些文件

| 文件 | 改动 |
|---|---|
| `tests/fixtures/sm24_review/`（新建） | 6 个 JSON 夹具 + `README.md`，落点非日期命名（`bundle_07_24/`、`bundle_07_25/`），避开 `.gitignore:7` `20*_*/` |
| `tests/test_gt_overlay.py` | `:156` 07-24 root → `tests/fixtures/sm24_review/bundle_07_24`；`:159` `source.dxf` 改指 tracked DXF 并**暂存进 tmp**（见 §1）；`:349` `_SM24_REVIEW_BUNDLE` → `bundle_07_25` |
| `tests/test_gt_promotion_path.py` | `:24/:25` `REQUEST`/`ANNOTATIONS` → `bundle_07_25`；`_mirror_repo` 删冗余显式 JSON 拷贝块（夹具现随 `tests/` copytree 进镜像，见 §4.4 验证） |
| `tests/test_tarch_converter_reproducibility.py` | `:21/:22` `REQUEST`/`ANNOTATIONS` → `bundle_07_25` |
| `tests/test_tarch_elevation_must_red.py` | `:22` `ROOT` → `bundle_07_24`；`:23` `SOURCE` → tracked DXF；`_run` 与 `green_sm24` 加 tmp 暂存（见 §1） |
| `tests/test_gt_discipline.py` | `:76` 文档串去掉失效的 `logs/experiments/<date>_…/work/` 引用（纯文字） |
| `main.py` | import 期不再建文件 sink（仅 console）；文件 sink 移到 `if __name__=="__main__"`，改指 `./AI_agent/logs/runtime/app.log`（`*.log` 已 gitignore） |
| `.gitignore` | **未删** `output/` 行——派工单前提有误，见 §2 review-ask（加注释保留） |
| 根 `logs/`（15M）、根 `output/`（空） | 整目录删除 |

**未动**：`AI_agent/**`（除本日志）、`src/`（除 main.py，且 main.py 在根不在 src/）、任何测试的断言/容差/期望值。

---

## 1. 关键发现：`assert_staging_input` 保护守卫（派工单未覆盖）

派工单 §1 称「source.dxf 字节同已入库那份 ⇒ 不需要搬 DXF，测试改指已入库那份即可」。**实测发现**：`run_p2_conversion`（`src/agent/judge/tarch_normalize.py:2387`）首行调 `assert_staging_input`，**拒绝受保护路径**（`case_tests/test_baseline/gt_sources/` 属受保护答案根）上的 DXF 输入，直传即 `ValueError: tarch_staging_input_protected_path`。

- 另两个消费文件（`test_gt_promotion_path.py`、`test_tarch_converter_reproducibility.py`）本就**先把 tracked DXF 拷到 tmp 再传入**，故只改路径即过。
- `test_tarch_elevation_must_red.py` 的 `_run`（默认 `source=SOURCE`）与 `green_sm24` fixture，以及 `test_gt_overlay.py:159`，原本**直传** SOURCE（旧值在 `logs/` 非受保护故可行）；改指 tracked 后撞守卫。

**修法（遵 §1「不重复入库 DXF」意图）**：SOURCE 仍指 tracked DXF（不重复入库 722KB 二进制），在 `_run`/`green_sm24`/overlay 测试里**运行时暂存一份到 per-test tmp**再传 `run_p2_conversion`——与 `test_tarch_converter_reproducibility.py:28` 的既有模式一致。`run_p2_conversion` 显式读传入的 `dxf_path`（不扫 work_dir）、输出 `work_dir/normalized.dxf`（与 `source.dxf` 不撞），故暂存进 work_dir 无害（已核源码）。这是被 fail-closed 守卫强制的最小逻辑增补，**未改任何断言/容差/期望值**，转换输入字节不变 ⇒ 结果不变。

中间轮首轮子集因此暴露 17 failed + 10 errors（全在 elevation）+ 1 failed（overlay），逐一定位到上述守卫后修复，子集回到 114 全过。

## 2. Review-ask（顶部最重要）：`.gitignore` `output/` 行——派工单前提有误

派工单 §3 指示「同步删 .gitignore 里的 output/ 条目（该行因此失去意义）」。**核查发现前提不成立**：该行是**全局** ignore，覆盖**所有** `output/` 目录，不只是 main.py 的 `output/logs`。删它后立即暴露 **16 个既有 e2e 测试 output 目录**（`backup/tests_history/SmallOffice/smalloffice_*/output/`、`case_tests/e2e_tests/smalloffice_21/output/`，时间戳 2026-03/05，是历史 e2e EnergyPlus 产物，**非本批创建**），全部变成未跟踪 `??`——一个与本批「根目录清零」目标无关的回归。

派工单真意 = 根 output/ 消失 + main.py 不再重建。两者均已达成（output/ 已 `rm -rf`、main.py import 不再建 output/logs），**与该 gitignore 行无关**。故我**保留该行**（加注释说明为何保留），维持 e2e output 被 ignore 的现状，避免无意回归。`git check-ignore -v` 确认 e2e 目录已重新被 `.gitignore:237 output/` 覆盖，git status 回到干净（仅本批 7 个改动 + 新夹具目录 + 既有派工单）。

**请主控裁决**：若仍要从 gitignore 移除全局 `output/`，需配套给 e2e output 目录加定向 ignore（如 `case_tests/**/output/`、`backup/**/output/`），否则回归。我判断保留全局行是最低风险且契合派工单真意。

---

## 3. §4 验收逐条

### §4.1 根目录只剩允许项；`logs/` 与 `output/` 不存在 ✓
删后根目录：`README.md` / `main.py` / `pyproject.toml` / `uv.lock` + 既有目录（`AI_agent backup case_tests data docker scripts skills src tests tests_scripts`）+ 点文件。`logs/`、`output/` 均 absent（全仓跑后亦未重建）。

### §4.2 全仓绿且计数不降 ✓
- 删 logs/output **前**：`1671 passed, 10 xfailed, 150 warnings in 229.83s`（EXIT 0）
- 删 logs/output **后**（交付态）：`1671 passed, 10 xfailed, 150 warnings in 222.10s`（EXIT 0）
- 无 `failed`、无 `skipped`。计数与基线一致（未加新测试，故未升）。

### §4.3 fail-closed 活体证明（交付物）✓
在 `/tmp/glm_fc/repo`（tar 拷贝，排除 .git/.venv/output/logs/backup）把 `tests/fixtures/sm24_review/` 改名为 `sm24_review_GONE` 模拟「仓库损坏」，跑 4 个消费文件（`-m "not mutation"`）：

```
29 failed, 23 passed, 14 warnings, 50 errors in 7.27s
```
- **0 skipped**（`-rs` 无 SKIP 行）。29 failed + 50 errors = 79 红；23 passed 是不依赖 sm24 夹具的合成输入用例（如 `test_r2_1`/`r2_4`/`r2_5` 用 tmp 合成、`test_r1_3` 用合成 hash）。
- 代表性报错（硬红非 skip）：
  ```
  FileNotFoundError: [Errno 2] No such file or directory:
    '/tmp/glm_fc/repo/tests/fixtures/sm24_review/bundle_07_25/request_v3_calibrated.json'
  ```
- **A4 自查结论**：4 个消费文件对 sm24 夹具全为直读（`.read_text()`/`model_validate_json`/`ezdxf.readfile`）→ 缺夹具即 FileNotFoundError = 硬红；`test_gt_overlay` 的 5 处 `skipif` 全门 sm21（`_HAS`）不门 sm24；`test_tarch_converter_reproducibility.py:28` 的 `if not source.exists()` 守的是 **tmp 副本**不是夹具（SOURCE 缺即 `SOURCE.read_bytes()` 硬红）。无软路径需硬化——命脉「绿但在空跑」风险已活体排除。

### §4.4 变异矩阵仍全绿 ✓
`tests/test_gt_promotion_path.py` 25 格（`-m mutation`）：
```
25 passed in 63.09s (0:01:03)   EXIT 0
```
我删了 `_mirror_repo` 的冗余显式 JSON 拷贝块——夹具现随 `tests/` copytree（`_mirror_repo:468`）进镜像，镜像内 `REPO/tests/fixtures/sm24_review/...` 与模块引用路径一致。25 格全过证明此改动正确（若漏了镜像拷贝，矩阵会整片红）。

### §4.5 `git check-ignore` 对每个夹具文件无输出 ✓
6 个夹具 + README 的 `git check-ignore -v` 全部空输出（真入库，非 force-add）。落点 `tests/fixtures/sm24_review/` 非日期命名，不触发 `20*_*/`。

### §4.6 受影响子集跑测声明 ✓
```
$ python scripts/tool_scripts/affected_tests.py --changed main.py .gitignore \
    tests/test_gt_overlay.py tests/test_gt_promotion_path.py \
    tests/test_tarch_converter_reproducibility.py tests/test_tarch_elevation_must_red.py \
    tests/test_gt_discipline.py tests/fixtures/sm24_review/
SCOPE: FULL
跑测声明：受影响子集 = 全仓（原因：changed path is deleted or absent: tests/fixtures/sm24_review）
```
工具因新夹具目录尚未 `git add`（本批不 commit）而视为 absent → 回退全仓。故中间轮按语义跑「4 消费文件 + test_gt_discipline + test_mcp_stdio」子集（114 过），交付前跑全仓（§4.2）。

---

## 4. 工作包 B（根 output/ 清零）

- **根因**：`main.py:24` loguru sink `log_file_path=Path(f"./output/logs/{logger_time}.log")` + `setup_logger` 里 `parent.mkdir` → 每次 import 建 `output/logs/` + 一个时间戳日志（绝大多数零字节；跑测试也触发）。
- **改法**（只动 main.py，未碰 `src/utils/logging.py`）：import 期 `setup_logger(console_output=True)`（无 file path → 不建文件/目录）；文件 sink 移到 `if __name__=="__main__":`，改指 `./AI_agent/logs/runtime/app.log`（`*.log` 已 gitignore；固定文件名 append，不再每次 import 攒零字节日志）。
- **复核写入点**：`grep "output/logs" src/ scripts/ docker/ main.py` 仅 `main.py:24`（已改）。`test_mcp_stdio` 以子进程跑 `python main.py mcp-server`（走 `__main__`），文件 sink 不碰 stdout，仍 `returncode==0 && stdout==""`（全仓跑通过）。
- **副作用**：`convert_idf`（main.py:42）仍写 `./output/idf/`、`run_agent` 默认 `output_dir=Path("output")`——这俩是显式命令时产物，非 import 触发，派工单 §3 仅点名 main.py:24 sink，故未动（见 review-ask 第 2 条）。

## 5. 其余 review-ask

1. **（最重要，见 §2）** `.gitignore` `output/` 行未删——派工单前提有误，保留以避免 e2e output 回归，请主控裁决。
2. **convert_idf / run_agent 仍引用 `output/`**（`output/idf/`、默认 `output_dir`）——显式命令时才写，非 import、非本批目标；派工单 §3 未点名。若主控要彻底「根 output/ 不可重建」，需另批处理这两处（本批不动，避免越界）。
3. **`assert_staging_input` 守卫强制暂存**（见 §1）：派工单「改指已入库 DXF」对直传 SOURCE 的两处（elevation `_run`/`green_sm24`、overlay `:159`）不可行，已按兄弟文件既有模式加 tmp 暂存。这是被守卫强制的最小逻辑增补，断言不变。

无其他拿不准处。
