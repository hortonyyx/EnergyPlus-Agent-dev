# 派工单 · F-10：`check_mep()` 签名漂移

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **席位**：执行档（GLM-5.2 主工作树 / 或 Claude 侧 Sonnet 子代理）
- **基点**：`6.15_ValidationArchM0toM4` @ `ce27167`（**不是 `origin/main`**）
- **性质**：单点接口修复 + 行为锁。**零设计自由度**，修法唯一。

> ⚠️ **派工方本轮已出错记录（如实登记，供你判断我的题对不对）**：08-05 一轮共 6 次「施工席停下上报」，
> **6 次全是派工方的题错了**（跨 GLM/Claude 两个家族复现）。其中两次是**工作基点**的题（worktree 从 `origin/main` 切）。
> **⇒ 如果本单的任何前提与你看到的代码事实不符，停下上报，不要硬做。** 这是被鼓励的行为，不扣分。

---

## 1. 背景（一句话）

任何走 `flow` 跑到 **4_mep** 的 run 都会当场硬崩，**已断整整一个月无人发现**——
因为这一个月没有任何东西走到过 4_mep（前面的 F-9 一直挡着）。

```
TypeError: check_mep() got an unexpected keyword argument 'run_profile'
```

## 2. 缺陷事实（orchestrator 已独立核实，你仍应自己复核）

| 侧 | 位置 | 事实 |
|---|---|---|
| 被调方 | [`src/validator/checks/mep.py:95-103`](../../../src/validator/checks/mep.py) | `check_mep(...)` 形参**没有** `run_profile`（07-01 定） |
| 调用方 | [`scripts/tool_scripts/run_stage.py:572-578`](../../../scripts/tool_scripts/run_stage.py) | 传了 `run_profile=policy.run_profile`（07-06 加） |

**`check_mep` 是 `src/validator/checks/` 里唯一不收 `run_profile` 的检查函数**，其余四个全收并原样传给 `CheckReport`：

- `check_assembly`（`assembly.py:28,36`）· `check_correction`（`correction.py:100,106`）
- `check_evidence_debt_coverage`（`correction.py:189,194`）· `check_kernel`（`kernel.py:65,70`）· `check_reading_view`（`reading.py:126,134`）

## 3. 修法（唯一形态，**照抄 `check_assembly` 的模式**）

在 `check_mep` 上补 `run_profile: RunProfile = "exploratory"` 关键字参数，并**原样传给 `CheckReport`**：

```python
def check_mep(
    mep: dict | object,
    *,
    used_constructions: set[str] | None = None,
    zone_names: set[str] | None = None,
    geometry_idf: str = "",
    testdata: dict | None = None,
    capability_profile: str = "rectangular",
    run_profile: RunProfile = "exploratory",   # ← 新增
) -> CheckReport:
    rep = CheckReport(
        stage="4_mep",
        capability_profile=capability_profile,
        run_profile=run_profile,               # ← 新增
    )
```

`RunProfile` 从 `src.validator.checks.schema` 导入（与 `assembly.py:20` 同）。

**⛔ 不许做的事**：
- ⛔ 不许改调用方去掉 `run_profile=`（那会让 4_mep **永远** 停在 `exploratory`，等于把门焊死）
- ⛔ 不许顺手改 `check_mep` 里任何一条检查的 `status` / `layer` / `check_id`
- ⛔ 不许放宽或跳过任何既有断言

## 4. 这不是纯签名修复——**它改变了 4_mep 的阻断行为**

现状 4_mep 的报告恒以默认 `exploratory` 构造 ⇒ 它的检查在 `regression` 档下**从来没有真正阻断过**。
补上之后，4_mep 才第一次真正受 `run_profile` 管辖。**所以必须配锁。**

## 5. 验收条件（缺一不可）

### A. 真实入口锁（**必须走真实调用路径**）
断言 `run_stage.py` 那条路径（4_mep 段）能跑通且不抛 `TypeError`。
⛔ **不许**只在测试里直接 `check_mep(..., run_profile=...)` 就算数——那只证明签名接受了这个词。

### B. 行为锁（**必须落在具体 check-id 行上**）
构造一份**必然产生至少一条 FAIL 的 mep 输入**，断言：
- `run_profile="exploratory"` ⇒ 该 check-id 出现在报告里且 **不进** `blocking()`
- `run_profile="regression"` ⇒ **同一个 check-id** 进 `blocking()`

⛔ **不许**断言「`blocking()` 不是 None」「总数变了」这类形状——本项目已因此栽过两次假锁。

### C. 默认值锁
不传 `run_profile` 时报告的 `run_profile` 字段 == `"exploratory"`（防止有人日后改默认值悄悄改变全局阻断面）。

### D. neuter 验分辨力（**两个方向**）
1. 把新增的 `run_profile=run_profile` 传参摘掉（保留形参）⇒ **C 之外的 B 必须红**；
2. 把形参默认值改成 `"regression"` ⇒ **C 必须红**。

> ⚠️ **neuter 前必须先确认改动真的落下去了**（`git diff` 看到实际行变化再跑）。
> orchestrator 本轮实犯：一次正则替换命中 **0 处**（空操作）却拿到「22 绿」——
> 据此判「已验」或「锁不绑」**两个结论都是错的**。

### E. 全仓
`pytest -n auto`（**不加 `-m` 过滤**）。基线 = **2220 绿 / 10 xfail / 0 红**。要求**净增锁、零回归**。

> ⚠️ **F-8 已知坑**：本仓「全仓绿」目前是**这台机器工作目录**的属性——干净检出会红 5 条
> （619 个被 `.gitignore` 挡住的文件里混着测试活输入）。**你在主工作树跑即可**，
> 但**新加的锁不许依赖任何 gitignored 文件**，否则就是给 F-8 添砖。

## 6. 交付

1. 代码改动（**只动** `src/validator/checks/mep.py`）+ 测试锁
2. 执行日志落 `AI_agent/logs/reviews/execution/2026-08-05_f10_check_mep_signature_<席位>.md`，含：
   全仓数字、B/D 两项的**实际命令与实际输出**、neuter 的 `git diff` 证据
3. **提交自己做**（message 仿 `08.05_f10_check_mep_run_profile`，body 含 ①改动 ②为何此刻 ③影响）。**不要 push。**

## 7. 跑测档位

一律 `exploratory`（用户 08-05：「现在你确保不会拦端到端就行」）。

---

## 8. 停下上报的合法出口（**明确允许**）

以下任一情况**立刻停下上报，不要硬做**：
- 本单陈述的任何代码事实与你看到的不符
- 基点 / 派工单文件 / cwd 与本单不一致
- 验收条件 B 在不放宽断言的前提下做不到
- 你认为修法方向本身有问题

**如实说「做不到」不受惩罚。** 硬做出一把假锁才是本项目最贵的错误。
