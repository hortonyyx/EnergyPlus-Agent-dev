# 派工单 · F-20 轻门 MAJOR-1 补锁：把「历史几何批准不失效」变成真锁

- **日期**：2026-08-10 · **席位**：GPT 侧 **`gpt-5.6-terra`**（中档执行）· effort **high**
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = `3303eee`**（F-20 修法已落库），工作树干净
- **全仓基线**：`python -m pytest -p no:cacheprovider -q -n 8` ⇒ **2357 passed / 10 xfailed / 0 failed**
  （⛔ 不要 `-n auto`：16 worker 实测在 ~98% 处**静默 OOM**）
- **上游裁决**：[orchestrator 轻门](../verdict/2026-08-10_f20_orchestrator_lightgate.md)（PASS-WITH-CHANGES，本单修的就是其中的 MAJOR-1）

---

## 1. 缺陷（已实测坐实）

`tests/test_c2_b5_artifact_trust.py` 的 **L6** 里，本该守「老产物几何指纹不变」的那条断言是：

```python
assert res_a2.geometry_digest == res_a.geometry_digest  # stable across repeat runs
```

`res_a` 与 `res_a2` 是**同一份代码**的两次调用 ⇒ **digest 公式一变，两边一起变、断言照样绿。**

**设计稿 §4 的 L6 逐字要求的是另一回事**：

> 旧 digest 用**施工前冻结的** fixture 值（或等价 frozen report）对比，
> **不在修后临时「算一个期望值」**。

**⇒ 实现做的正是设计明令禁止的那件事。**
这就是本项目 2026-08-07 记下的 **「恒等锁 ≠ 正确性锁」**：
恒等锁证明「两次算法一致」，**不证明这套算法与历史一致**。

**orchestrator 已机械查实两条**：

1. **`grep` 全 `tests/`，没有任何一处把 `geometry_digest` 钉在字面值上**
   ⇒ **「历史几何批准不失效」这条性质，全仓零锁。**
2. **换方向 neuter 实测**：把 trust 行挪进 kernel report（= 一次「重构时挪了位置」）
   ⇒ **8 把 F-20 锁一把没红**，只有 `test_check_parity` 红，而它红是因为新 check_id
   出现在未豁免的 stage —— **属间接命中，不是在守这条性质**。
   ⇒ 若某次重构改了 kernel report 的形状**而没有新增 check_id**，全仓一条都抓不到。

⚠️ **公平地说**：F-20 施工席**确实验过**这条性质（用 `git archive` 取修前只读快照与工作树逐字节对比，
两个 golden 基线的 `blocked` / `blocking_summary` / `digest` 全同）——**那是一次有效的人工验证**。
**问题是它没有变成锁**：今天是对的，但没有任何东西守着它明天还对。

---

## 2. 要做的事

把那条自比自的断言，换成**钉在修前实测字面值**上的冻结锁。

### ⛔ 2.0 【r2 更正 2026-08-10】本单 v1 的锚点选错了 —— 派工方错误率 15/15

**terra 按合法退出口停下上报，且它是对的**：v1 指定的两个 golden 正基线
**在修前修后 `geometry_digest` 都是 `None`**（orchestrator 已独立复核，当前代码亦为 `None`、`blocked=True`）
⇒ **根本没有可冻结的值**，继续加断言就是造伪锁。

**⚠️ 由此连带炸出一件更要紧的事（已登记）**：F-20 施工席验收④声称
「两个 golden 正基线 `blocked`/`blocking_summary`/`digest` 逐字节相同」——
其中 **`digest` 那一维是空的（`None == None` 恒真）**。
`blocked`/`blocking_summary` 的比较仍然有效，但**「历史几何批准不失效」这条性质从未被真正验过**。
orchestrator 在轻门裁决里把它写成「一次有效的人工验证」，**说过头了，已更正**。

**⇒ 新锚点（orchestrator 已亲自量过、确认可行，⛔ 不要再自己找）**：

全仓扫描 `case_tests/e2e_tests/**/run_*`（凡有 `1_correction/correction_geometry_snapped.json` 的），
**只有一个 run 能产出非空 `geometry_digest`**：

```
sm21_anchor/run_2026-08-07_f13_e2e_verify
  修前（2c7e0a4）digest = bed87c03e4c9947858f540a638ee495658fca56545f120352ef9e4003de8a5c8
  修后（3303eee）digest = 同上，逐字符相同
  policy = RunPolicy()（默认）
  注：该 run blocked=True（缺 0_reading，是定向重验），但 digest 照常签出 —— 即 F-21 那条已结案的登记
```

**它正是理想锚点**：V2 账本 + legacy schema ⇒ 走的正是 F-20 改动的那条分支，
而修前修后指纹相同 ⇒ **能证明 F-20 没有改变老产物的几何指纹**；
同时 digest 哈希整份 kernel report ⇒ **能抓住 §2.3 那个 neuter**。

⇒ **§2.1 的取值步骤已由 orchestrator 代做完，你直接用上面那个值。**
若你要复核（欢迎），命令是：
`git archive 2c7e0a4 src | tar -x -C /tmp/x && cp -a data /tmp/x/` 然后在 `/tmp/x` 下调 `validate_case`。

---

### 2.1 取冻结值（**必须从修法之前的代码取**）〔已由 orchestrator 代做，见 §2.0〕

`3303eee` 是 F-20 修法提交，**其父提交 `2c7e0a4` 是修法之前**。
请从 `2c7e0a4` 取出**修前代码**（`git worktree add` 到 `/tmp`，或 `git archive | tar -x` 到 `/tmp`），
在那份修前代码上跑 `validate_case`，量出**两个 golden 正基线**的 `geometry_digest`：

- `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline`
- `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e`

⚠️ **两者都没有 `_run/run_manifest.json`**（走 legacy 分支），且都是
`tests/test_validation_run_baseline.py` **当前在用**的 golden 正基线。
⚠️ **policy 必须与被锁的调用一致** —— 请照 `test_validation_run_baseline.py` 里现有的调用姿势，
⛔ 不要自己另挑一套 `RunPolicy`（挑错了锁的就是另一回事）。

### 2.2 落锁

在合适位置（`tests/test_validation_run_baseline.py` 更贴切，或 L6 所在文件，你判断并说明理由）
加一把锁：**断言这两个 golden 基线今天算出的 `geometry_digest` 恰好等于上一步量到的字面值**。

- 字面值**写进源码常量**并**加注释说明它是从哪个提交量的、为什么冻结**。
- ⛔ **不许**用「同一版本跑两次相等」「非 None」「长度为 64」这类替代。
- **L6 里那条 `res_a2 == res_a` 可以保留**（它锁的是「可重复性」，是另一条性质），
  但**不得**继续冒充「历史不失效」那条锁 —— 请把注释改准。

### 2.3 自证前提（硬要求）

按本项目纪律，**这把锁必须自证前提**：

- 先证明**它真的能红** —— 用 §1 那个 neuter（把 trust 行也 `krep.add(...)` 进 kernel report，
  在 `/tmp` 副本里做）验证**这把新锁会红**。
- ⛔ 若新锁在那个 neuter 下**不红**，说明锁没绑住目标 ⇒ **停下上报，不要交付**。

---

## 3. ⛔ 边界

1. ⛔ **不改生产码**（`src/`）。本单只动 `tests/`。
2. neuter 实验**只在 `/tmp` 副本 / `/tmp` worktree 里做**，⛔ 不许动工作树。
   ⚠️ 若用 `git worktree add`，**用完 `git worktree remove` 清干净**。
3. ⛔ 不许 `git add` / `commit` / 切分支（由 orchestrator 提交）。
4. ⛔ 不许读 `case_tests/test_baseline/gt/`。
5. ⛔ 不许改动那两个 golden 基线目录里的任何文件。

## 4. 验收（原始输出都要落进执行日志）

1. **独立全量**：`python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20m1_full.log 2>&1; echo $? > /tmp/f20m1_full.rc`
   ⚠️ **观测通道纪律**：输出**直接重定向到文件**、退出码**单独落一个只属于该命令的文件**、
   ⛔ **中间不接任何下游管道**（`pytest | tee | head` 会因 SIGPIPE 打断 pytest，
   你看到的退出码其实是 `head` 的）。以**汇总行 + 退出码**为准。
2. **neuter**：§2.3 那个变异下，**恰好新锁红**（报告有无连带）。
3. 说明冻结值是从**哪个提交、用什么命令**量出来的。

## 5. 交付物

执行日志落 `AI_agent/logs/reviews/execution/2026-08-10_f20_major1_frozen_digest_lock_terra.md`。

## 6. 合法退出口

- 修前代码在 `/tmp` 跑不起来（缺依赖/缺数据）⇒ 停下上报；
- 两个 golden 基线在修前算不出 digest（是 `None`）⇒ **那本身是重要发现**，停下上报；
- 新锁在 §2.3 的 neuter 下不红 ⇒ 停下上报；
- 本单某两条要求互相冲突 ⇒ 停下上报。

**⛔ 派工方（orchestrator）自陈错误率 = 14/14** —— 迄今每一次执行席「停下上报」，
事后都证明是派工单的题错了。**顶住不照做、如实上报是期望行为，不是失败。**
