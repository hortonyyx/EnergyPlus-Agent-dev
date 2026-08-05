# F-2c 收口 · 执行日志（GLM-5.2 席位）

- **日期**：2026-08-05
- **席位**：GLM-5.2（主工作树，分支 `6.15_ValidationArchM0toM4`）
- **派工单**：[`request/2026-08-05_f2c_closeout_dispatch_glm.md`](../request/2026-08-05_f2c_closeout_dispatch_glm.md)
- **状态**：✅ **DONE**（一条红收掉，零回归，双向 neuter 证分辨力，落库 `a8c367a`）
- **前序裁定**：[`request/2026-08-05_f2c_boundary_ruling.md`](../request/2026-08-05_f2c_boundary_ruling.md) §2/§3

## 0. 与派工单的对账（派工方自述「凡与代码实情不符处停下上报」）

逐条核过派工单点名处，**全部与代码实情相符，无「停下上报」项**：

| 派工单说法 | 核验结果 |
|---|---|
| `identify_reading_contract` 在 `reading_typed_adapter.py:60` | ✅ 第 60 行（已搬走） |
| `ReadingContractDecision` 是该文件 dataclass | ✅ 第 46–49 行 |
| `READING_PRODUCT_CONTRACT` 在 `score_schema.py:549`（**不在 adapter**） | ✅ 第 549 行 |
| `READING_CONTRACT_DETECTOR_VERSION` **两处**各一份（`score_schema.py:550` + `reading_typed_adapter.py:43`，值相同） | ✅ 两处都是 `"reading_contract_detector_v2"`；adapter 那处还**遮蔽**了同文件 21 行从 score_schema 的 import |
| 探测器自身零 judge 依赖 | ✅ 只用 `Literal` + dataclass + 常量（连 `ReadingView` 都不用——派工单括注里提到的 ReadingView 其实不在该函数体里） |
| `window_sources.py:23` 已 `from src.agent.reading import parse_reading_view`、`envelope.py` 也依赖 reading | ✅ 这条依赖边已存在且合法 |
| reading 包不 import judge（搬家不成环） | ✅ reading 包只 import 自己（`reading.schema`/`reading.legacy`）；`contract.py` 仅 `dataclass`+`typing` ⇒ judge/correction → reading.contract 单向边 |

**Literal 漂移收敛（§1.1 顺手项）**：选 **Option A「让 Literal 由常量导出」**，不选加断言。理由 = 真单一来源（常量定义是唯一一处字面 `"reading_views_v2"`），比「再加第三处字面当锁」更干净。容器 Python 3.12.13 实测 `Literal[Final常量, "unrecognized"]` 求值 == `Literal['reading_views_v2', 'unrecognized']`、dataclass 构造正常。

## 1. 改动摘要（落库 `a8c367a`，8 文件 +298/-41）

- **新建 `src/agent/reading/contract.py`**：四个符号（`READING_PRODUCT_CONTRACT` / `READING_CONTRACT_DETECTOR_VERSION` 均 `Final`；`ReadingContractDecision`（`contract_id: Literal[READING_PRODUCT_CONTRACT, "unrecognized"]`）；`identify_reading_contract`）的唯一规范定义处。函数体逐字照搬原实现 ⇒ 语义零变化。从 `reading/__init__.py` 导出。
- **judge 侧改 re-export**：`reading_typed_adapter.py` 删本地 `READING_CONTRACT_DETECTOR_VERSION` 重声明 + `ReadingContractDecision` dataclass + `identify_reading_contract` 函数定义，改 `from src.agent.reading.contract import ...`；`score_schema.py` 删 549–550 两行常量定义，顶部 `from src.agent.reading.contract import ...`。⇒ **调用点一字不改**（3 脚本 + 3 测试经 `reading_typed_adapter` 导入、`score_schema` 自身 1423/1446/1448 消费）全部仍可用，且绑的是**同一个对象**。
- **`window_sources.py`**：把函数内 `from src.agent.judge.reading_typed_adapter import (...)` local import 提到顶部、改源自 `src.agent.reading.contract`，并删掉那段「为何这个 local import 不违反边界」的辩解注释。
- **F-2c-1 / F-2c-2 主体（上轮照收）**：`isolation.py` `merge_isolated_output` 写扁平镜像；`window_sources.py` `verify_reading_stage_root_against_accepted_attempt` 按 accepted 契约形状重建镜像 + canonical hash 比对。
- **锁**：`test_e2e_break_r2_locks.py` 三把 F-2c 锁（上轮）+ 本轮新增一把「全仓只有一个探测器」锁 `test_f2c_single_contract_detector_is_canonical`（`rta.identify_reading_contract is rdc.identify_reading_contract` + 两个常量 `is` + `src/` 下 `def identify_reading_contract` 恰好一处 == `src/agent/reading/contract.py`）。
- **`run_stage.py`**：F-2c docstring 更新（上轮照收）。

提交粒度：逐文件 `git add`（**未用 `git add -A`**，**未 push**）。`AI_agent/plan.md` 与 `case_tests/` 下若干未跟踪 run 目录均**不在本提交**——plan.md 是 orchestrator 本轮对活计划的实时更新（非本席产物），已如实留在工作树未动。

## 2. 验收实跑

### 2.1 定向子集（52 绿）
`test_e2e_break_r2_locks.py`（F-2c 三锁 + 新 §2 锁 + F-2/F-3/MAJOR-1）+ B5 A6 judge-blind 守卫 + B5 C5 correction/geometry no-judge 守卫 + reading typed scoring slice0/slice1 + legacy envelope scoring：

```
52 passed in 20.01s
```
即派工单点名的「唯一一条红」`test_b5_a6_production_source_is_judge_blind` 已转绿，守卫本身一字未改。

### 2.2 双向 neuter（证分辨力，⭐ 判据纪律：变红 ≠ 有分辨力，须两向各栽一次）

**Neuter A**——摘掉 `merge_isolated_output` 的镜像写入循环（loop body → `pass`）⇒ `test_f2c1_isolated_merge_mirrors_views_and_verifies` 必红：
```
>       assert mirrored == sorted(f"{view_id}.json" for view_id in views)
E       AssertionError: assert [] == ['1f_view.jso...st_view.json']
E         Right contains 6 more items, first extra item: '1f_view.json'
FAILED tests/test_e2e_break_r2_locks.py::test_f2c1_isolated_merge_mirrors_views_and_verifies
1 failed in 5.12s
```

**Neuter B**——把 `verify_reading_stage_root_against_accepted_attempt` 的 canonical 比较改恒真（`if current_hash != accepted_hash:` → `if False:`）⇒ 篡改坐标那格必红：
```
>       with pytest.raises(WindowResolverInputError, match="accepted_attempt_mismatch"):
E       Failed: DID NOT RAISE <class 'src.agent.correction.window_sources.WindowResolverInputError'>
FAILED tests/test_e2e_break_r2_locks.py::test_f2c2_tampered_mirror_coordinate_is_rejected
1 failed in 5.36s
```

两向各红一次 ⇒ 锁真绑、有分辨力（非「实现被调用」假绿）。neuter 全程 backup→patch→run→restore，事后 `grep NEUTER` 零残留、`git diff` 只剩本席预期文件。

### 2.3 全仓（`-n auto`，⛔ 零 `-m` 过滤）

**2197 passed / 10 xfailed / 0 failed**（293s）。基线（派工单引 9fd8a9a 记录）2193 绿 / 10 xfail / 0 红；净 +4 = 上轮三把 F-2c 锁（先前未提交、本提交一并落库）+ 本轮一把 §2 锁；xfail 持平 10、零回归。

## 3. 过程中撞到并自修的一处（如实登记）

首次全仓跑出 **1 红 = `test_c2_b4b_phase_d.py::test_d5_..._d6_new_judge_modules_stay_judge_only`**。根因 = 我在 `contract.py` docstring 里写了字面 `` src.agent.judge.score_schema ``，而该守卫是**钝器字符串扫描**（reading/execution/correction 任意文件出现 `src.agent.judge.<forbidden>` 即红，含 docstring/注释）。修法 = 改写 docstring 不再拼出该 dotted 路径（**未动守卫**——派工单 §1.4#3 禁止收窄守卫迁就改动；错在我自己的 docstring）。复跑该守卫 + 全仓均绿。

## 4. 交回

- 落库 SHA：`a8c367a`（分支 `6.15_ValidationArchM0toM4`，**未 push**，等 orchestrator 收工统一处理）。
- F-2c 收口完成；全仓零红。下一步按裁定 §5 顺序：F-7（Claude 侧 Sonnet 子代理，独立 worktree，动 `window_sources.py` 另一区域）+ r4 押下轮。
