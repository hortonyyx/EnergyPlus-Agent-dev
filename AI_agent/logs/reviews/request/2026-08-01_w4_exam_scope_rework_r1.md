# 返工单 r1 · W4「run 级考试范围声明」—— 判卷侧接线越界

- **日期**：2026-08-01
- **座位**：GPT 侧 terra（`gpt-5.6-terra`，effort=high）· 通道 = `codex exec` CLI 后台
- **基线**：原派工单 [2026-08-01_reading_unsupervised_enablement_dispatch.md](2026-08-01_reading_unsupervised_enablement_dispatch.md) §4（W4）+ §5 交付要求
- **待返工的提交**：`2d2137e` feat(reading): support frozen run exam scopes（主控代提交）
- **W1 `15cfcb8` / W3 `0763164` 本轮不动**

---

## 1. 缺陷（主控轻门实证，已在 HEAD 上复现）

[`scripts/tool_scripts/run_stage.py:1404-1415`](../../../../scripts/tool_scripts/run_stage.py#L1404)
在 `_grade_typed_attempt_artifacts` 里新增了这一段：

```python
if stage == "0_reading":
    scope_verification = verify_view_manifest(
        _REPO_ROOT / "case_tests" / "e2e_tests" / case,
        attempt_dir.parents[2],
    )
    if not scope_verification.ok:
        raise RuntimeError(f"reading exam scope verification failed: {scope_verification.reason}")
```

两条独立的错：

1. **case 目录被硬编码成 `_REPO_ROOT / "case_tests" / "e2e_tests" / <case>`。**
   `run_stage.py` 的 CLI **明确支持 `--base-dir`**（同文件 `cmd_judge` 就是从
   `_resolve(args.base_dir, args.case, args.run)` 拿 `case_dir` 的，见 `run_stage.py:1856`）。
   主控 08-01 当天就用 `--base-dir` 在 scratch 目录跑过重判 ⇒ 这条会在真实用法上直接抛错。
2. **违派工单 §1.6「默认行为不变：不声明 = 全考，所有现有 run 与测试的行为逐字不变」。**
   该校验对 `0_reading` **无条件触发**，未声明 exam scope 的 run 也会走进去并可能抛错。

**活体证据（HEAD，主控独立复跑）**：

```
tests/test_c2_b4b_phase_d.py::test_gt_echo_fixture_preserves_runstage_cli_byte_parity
RuntimeError: reading exam scope verification failed: cannot rebuild expected manifest:
  no case metadata found under /workspaces/EnergyPlus-Agent-dev/case_tests/e2e_tests/b4b-contract
  (case_data/testdata_prompt.json or testdata_prompt.json)
```

**全仓现状 = 2040 绿 / 1 红 / 10 xfail**（改造前基线 2028 绿 / 0 红 / 10 xfail）。

**⚠️ 为什么三个 slice 自查都报「欠规格边界：None」却没抓到它**：这条只有**全仓**能抓到，
而交付前的全仓那一步被 `.git/index.lock` 卡住没跑完（主控轮询工作树抢锁所致，责任在主控，
已记为规约候选）。**本次返工全仓是硬要求，不跑完不算交付。**

---

## 2. 返工目标（唯一目标，别做别的）

让「本轮考哪几张」的**判卷侧消费**在下面这张**全参数表**上都正确。表以外的行为一律不许改。

| # | stage | 是否声明了 exam scope | 要求的行为 |
|---|---|---|---|
| A | `1_correction` | 任意 | **完全不进入任何 scope 逻辑**（与改造前逐字节相同） |
| B | `0_reading` | **未声明**（`run_config.yaml` 无 `reading_exam_scope` 且 `_run/reading_exam_scope.json` 不存在） | **零额外工作、零额外读盘校验、不抛错**；bindings 不做子集；与改造前**逐字节相同**。**这一格包含「case 目录根本不存在 / 没有 case 元数据」的合成夹具 run**（`b4b-contract` 就是这一类） |
| C | `0_reading` | **已声明且冻结件与声明一致** | bindings 必须收窄到 scope 的 `input_ids`；且必须验明 scope 绑定的正是本次判卷所用的那份基准 manifest（`scope.base_view_manifest_sha256 == base.content_sha256`），不等即 **fail closed 抛错** |
| D | `0_reading` | **声明与冻结件不一致**（run_config 改了 / 冻结件被删 / 冻结件在但声明没了 / 冻结件损坏） | **fail closed 抛错**，错误信息说清是哪一种漂移。这条是 §1.6「开考前定死、考中不可变更」的落点，**不许因为本次返工被削弱** |

**硬边界**：

1. **case 目录一律不得由判卷函数自行拼装。** 要么完全不需要它，要么由**调用方已有的**
   `case_dir` 显式传进来。`_REPO_ROOT / "case_tests" / "e2e_tests" / …` 这种拼法在本文件里
   **一处都不许留**（返工后 grep 该串应为 0 命中）。
2. **不许有第二把尺子。** exam scope 的合法性判据（上表 C/D 两格）当前唯一实现在
   `src/agent/execution/view_manifest.py` 的 `verify_view_manifest` /
   `_provision_reading_exam_scope` 里。**不得在 `run_stage.py` 里另写一套等价判定**；
   若需要一个不依赖 case_dir 的入口，**在 `view_manifest.py` 里抽出共享函数**，
   由 `verify_view_manifest` 与判卷侧**共同调用**（单一实现），不得复制粘贴。
3. **不动 GT、不动 `case_tests/test_baseline/gt/**` 任何文件、不动签名件、不动 case 元数据。**
4. **W1（`15cfcb8`）与 W3（`0763164`）的产物不许碰。**
5. **不许改测试去迁就实现。** `test_gt_echo_fixture_preserves_runstage_cli_byte_parity`
   的断言与夹具**逐字节不许动**；它现在红，是因为生产码错了。
   （若你认为该测试本身有问题 —— **停下上报，不要自行修改它**。）

---

## 3. 主控给的死骨架（方向已定，实现细节归你）

**推荐路线**：判卷侧根本不需要 case 目录 —— 它需要的只是「本 run 冻结下来的考试范围」，
而那份冻结件就在 `_run/reading_exam_scope.json`，且它自带 `base_view_manifest_sha256`，
可以直接跟判卷函数**已经加载好的** `base`（`_run/view_manifest.json`，见
`_typed_score_input_paths`）对账。

⇒ 在 `view_manifest.py` 里抽一个**不吃 case_dir** 的解析器，语义 = 上表 B/C/D 三格：

```
resolve_frozen_reading_exam_scope(run_dir, base_manifest) -> ReadingExamScope | None
  - 未声明且无冻结件            -> None            （B 格）
  - 声明与冻结件一致且绑定同一 base -> 返回 scope     （C 格）
  - 其余一切                    -> raise，理由分型   （D 格）
```

并让 `verify_view_manifest` **改为调用它**（消除重复实现）；`run_stage.py` 判卷处改成调用它，
删掉 `verify_view_manifest(...)` 那两行硬编码路径。

**⚠️ 你有权不走这条路线**，但只在下面两个条件都满足时：
① 你的路线在上表 A–D 四格上逐格给出证据；
② 你**写明**理由。**「我当时的意思是……」不是可接受的交付说明。**

**⚠️ 一个必须回答的问题（别自行降级为假设）**：
原实现把 `verify_view_manifest`（含「on-disk manifest vs 由 case 元数据重建」这道**漂移门**）
放进了判卷路径。**若按推荐路线拿掉，请说明：能到达判卷函数的每一条路径上，
这道漂移门还在不在、在哪一步执行**（已知 `provision_view_manifest` 与 `cmd_judge:1872` 各有一处）。
**若发现某条路径上确实没有了**，**如实上报、不要顺手补**（那是另一个决定，归主控裁）。

---

## 4. 验收（缺一不算交付）

1. **上表 A–D 四格逐格给证据**（命令 + 输出片段）。C/D 两格必须是**真跑**，不接受推理。
2. `grep -n 'case_tests" / "e2e_tests"' scripts/tool_scripts/run_stage.py` **0 命中**。
3. **`--base-dir` 活体证明**：在 `/tmp` 造一个不在仓库 `case_tests/e2e_tests/` 下的 case 目录，
   用 `--base-dir` 指过去跑一次 `0_reading` 判卷，**不因路径拼装报错**。
4. **全仓跑一次**（`python -m pytest -n auto`，别加 `-m` 过滤）：
   **必须 ≥ 2028 绿 + 10 xfail 且 0 红**，并给出与基线的对账（新增绿数来自哪些测试）。
   **这一步不许跳过、不许只跑子集交付。**
5. **sm24 未声明 scope 的既有 run 产物与 checks 逐字节不变**（原派工单 §4 验收第 5 条，本轮补做）。
6. **三个身份哈希（`case_metadata_sha256` / `base_view_manifest_sha256` / `gt_content_sha256`）
   逐字不变**，给出返工前后相同的证据。

---

## 5. 交付要求

- **执行日志**续写到
  [`AI_agent/logs/reviews/execution/2026-08-01_reading_unsupervised_enablement_terra.md`](../execution/2026-08-01_reading_unsupervised_enablement_terra.md)
  新开一节「W4 返工 r1」：改了什么 / 为什么 / 证据命令与输出 / 遇到的欠规格边界与你的处置。
- **提交**：一个 commit，message 仿 `<月.日>_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响。
  **不许 push**（推送需单独授权）。**不许 `git reset --hard` / force / 跳 hook。**
- **欠规格边界一律停下上报，不得自行降级为假设。**
- **回主对话只给简报**（不贴 diff、不贴文件内容）：四格结论 / 全仓绿数 / 改了哪几个文件 /
  **review-ask 段**（哪些处没把握、做了什么取舍、动了哪些不变量；无则写 "none"）。

## 6. 运维注意（本轮特有）

- **`.git/index.lock`**：主控本轮**只跑只读命令**监控，不会再跟你抢索引。你正常 `git add`/`commit` 即可。
- 若再撞锁：**停下上报，不要自行删锁**（删除需单独授权）。
