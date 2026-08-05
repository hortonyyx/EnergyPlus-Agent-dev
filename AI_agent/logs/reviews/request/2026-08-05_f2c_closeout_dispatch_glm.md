# 派工单（GLM 席位）· F-2c 收口 —— 把识图产物形状探测器搬出 judge 包

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **席位**：GLM-5.2
- **范围**：**只做本单**。F-7 已另派 Claude 侧 Sonnet 子代理并行开工，**⛔ 不要碰 `_claim_links` / `pipeline.py` 的 prompt 构造 / `step_orchestrator.py`**。
- **前序**：本单 = [F-2c 边界裁定](2026-08-05_f2c_boundary_ruling.md) §2/§3 的执行。裁定里已认过「派工方的题错了」，本单是更正后的版本。

> **⚠️ 并行席位纪律**：另一个席位正在同一个仓库的**独立 git worktree** 里改 `src/agent/correction/window_sources.py` 的**另一处区域**（`_claim_links` 附近，约 621 行起）。
> **你只改本单点名的地方；⛔ 提交时不许 `git add -A`，逐文件 `git add`。**（本项目实犯过：收工 `git add -A` 把并行席位的半成品扫进提交并推送。）

> **⚠️ 派工方自述**：本轮我已经出错四次。**本单里凡是与代码实情不符的地方，一律停下上报，不要硬做。**「停下上报」在本项目是记功不是记过 —— 你本轮三次停下上报，三次都是我的题错了。

---

## 0. 当前工作树状态（我已实测，不要重复核）

```
 M scripts/tool_scripts/run_stage.py        (F-2c docstring 更新)
 M src/agent/correction/window_sources.py   (F-2c-2 校验器按 accepted 契约形状重建)
 M src/agent/execution/isolation.py         (F-2c-1 merge 写扁平镜像)
 M tests/test_e2e_break_r2_locks.py         (F-2c 三把锁)
```

实测（`test_e2e_break_r2_locks.py` + `test_c2_b5_host_resolution.py` + `test_c2_b5_source_routing.py` + `test_isolation.py`，`-n 4`）：

```
1 failed, 302 passed in 130.39s
FAILED tests/test_c2_b5_source_routing.py::test_b5_a6_production_source_is_judge_blind
```

**唯一一条红的就是 B5 A6 judge-blind 守卫**，红因 = `window_sources.py` 现在 `from src.agent.judge.reading_typed_adapter import ...`。
**你上轮交的其余部分（merge 写镜像 + 三把锁 + 翻新的 docstring）全绿，照收，不要重做。**

**本单 = 只把这最后一条红收掉。**

---

## 1. 任务 —— 搬家

### 1.1 新建 `src/agent/reading/contract.py`，搬入四样东西

| 符号 | 现住处 | 备注 |
|---|---|---|
| `identify_reading_contract` | `src/agent/judge/reading_typed_adapter.py:60` | 自身**零 judge 依赖**（只用 `Literal` + dataclass + `ReadingView`）|
| `ReadingContractDecision` | `src/agent/judge/reading_typed_adapter.py`（dataclass）| |
| `READING_PRODUCT_CONTRACT` | **`src/agent/judge/score_schema.py:549`** | ⚠️ **不在 adapter 里** —— 裁定原文没写清这点，以本单为准 |
| `READING_CONTRACT_DETECTOR_VERSION` | **两处各声明一份**：`score_schema.py:550` + `reading_typed_adapter.py:43`（值相同）| ⚠️ 既存重复声明，**搬家时收敛成一份**，另两处改 import |

从 `src/agent/reading/__init__.py` 导出。

**⚠️ 顺手收一处漂移**：`ReadingContractDecision.contract_id` 现在硬写着
`Literal["reading_views_v2", "unrecognized"]`，与 `READING_PRODUCT_CONTRACT` 常量是**两处记载**。
让 Literal 由常量导出，**或**加一条断言二者相等的锁 —— 二选一，你判断哪个干净。

### 1.2 judge 侧改为 re-export

`src/agent/judge/reading_typed_adapter.py` 与 `src/agent/judge/score_schema.py` 从新位置 import 后 re-export，
**judge 侧所有调用点一字不改、语义零变化**。

### 1.3 `window_sources.py` 改从 reading 包 import

这条依赖边**本来就存在且合法**：
- `window_sources.py:23` 已经 `from src.agent.reading import parse_reading_view`；
- `correction/envelope.py:23-24` 也已依赖 `src.agent.reading`。

⇒ B5 A6 守卫恢复绿。**顺带把你上轮写的那段「为什么这个 local import 不违反边界」的辩解注释删掉** —— 搬完就不需要辩解了。

### 1.4 ⛔ 三条硬禁止

1. **B5 A6 那两条守卫（`test_c2_b5_source_routing.py:215`、`test_c2_b5_parent_and_verts.py:1162`）一个字不许改。** 它们是判据，不是障碍。
2. **⛔ 不许就地复刻一个薄形状判定** = 第二把尺子。本项目已多次栽在这上面（判卷双尺 / 词表双份）。
3. **⛔ 不许把守卫从字符串扫描收窄成 AST** 来迁就本次改动。

---

## 2. 追加一把「全仓只有一个探测器」的锁

按裁定 §3：

- 断言 `reading_typed_adapter.identify_reading_contract` **is**（同一个对象，不是同名函数）reading 包里那个；
- 断言全仓 `def identify_reading_contract` **恰好一处**（源码扫描）。

⇒ 以后谁再复刻一份，这条锁必红。

---

## 3. 验收（三项都要实跑并贴输出）

1. **B5 A6 两条守卫绿**；
2. **F-2c 三把锁仍绿且仍有分辨力** —— **两个方向各实跑一次**：
   - 摘掉 `merge_isolated_output` 里的镜像写入循环 ⇒ 必红；
   - 把 `verify_reading_stage_root_against_accepted_attempt` 的 canonical 比较改成恒真 ⇒ 篡改坐标那格必红。
   **把这两次的 pytest 输出原样贴进执行日志。**
   > **⭐ 判据纪律**：neuter 变红只证明「实现被调用了」，**不证明「判据有分辨力」**。本项目两次栽在这上面（2×2 px 退化 fixture 假绿 / 两堵墙探针假红）。
3. **全仓一次**（`-n auto`，**⛔ 不加 `-m` 过滤**）。基线 = HEAD 2193 绿 / 10 xfail / 0 红（`9fd8a9a` 的记录），本单预期净增 1–2 条锁、零回归。

---

## 4. 提交与交回

- **一个提交**，message 仿 `08.05_f2c_contract_detector_moved_to_reading`，body 含 ①改动 ②为何此刻 ③影响。
- **⛔ 逐文件 `git add`，不许 `git add -A`**（并行席位在跑）。
- **⛔ 不要 push**（收工时由 orchestrator 统一处理）。
- 执行日志落 `AI_agent/logs/reviews/execution/2026-08-05_f2c_closeout_glm.md`，含：
  状态（DONE / 停下上报 + 卡在哪）· diff 摘要 + 落库 SHA · **双向 neuter 的实跑输出** · 全仓尾巴三个数（passed / xfailed / failed）。
- **做完一件存一件**（容器 OOM 会带走会话，本项目实犯过两次、同样的活白做两遍）。
