# 派工单 · 探针人体工学（识图崩盘归因候选 #1）

> 主控 Opus 5 · 2026-07-31 · 用户当轮拍板「把 reading 崩盘那个一起修了再继续」
> **本单只修候选 #1（探针成本翻倍）。候选 #4（预扫信噪比）主控裁定本轮不动，理由见 §4。**

## 1. 问题（已量化，非推测）

2026-07-30 sm24 识图轮，同模型（Haiku 4.5）同工具箱，质量从 07-07 的 8/8 掉到 1/8。
四条归因候选中，守卫摩擦 / 样板件缺失 / directive 措辞三条已修。**本单修第四条：探针成本。**

**实况**（主控从 `run_2026-07-27_haiku_e2e/.../isolation_archive/access_log.jsonl` 算出）：

| 指标 | 07-07（prompt 级隔离） | 07-30（硬隔离） |
|---|---|---|
| 单次探针的最小调用数 | **1**（直接带参调用） | **2**（先 Write request JSON，再 Bash 执行） |
| 实际探针次数 | **19** | **8** |
| 允许的 Bash 探针执行 | — | 6 |
| 允许的 Write | — | 12（多为 request JSON） |

守卫当前硬性要求 Bash 命令**恰好四个 token**：
`python tools/run_cv_probe.py --request <json>`（`guard.py:_check_bash`）。

⇒ **机制把一倍成本正好加在「量」这个动作上**，而「量而非看」是本项目识图方法论的命脉。
弱模型预算有限，成本翻倍即测量次数减半 —— 与实况吻合。

## 2. 死骨架

### P1-1 · 守卫支持「一次调用带参」的探针形式

保留现有 `--request <json>` 形式**不变**（老路径不破），**新增**直接带参形式：

```
python tools/run_cv_probe.py --tool <name> --image <path> [--out-dir <path>] [--<key> <value> ...]
```

**「恰好四个 token」的规则必须换成严格的参数解析器**，不是放宽计数：

1. `argv[0]` 的 basename ∈ {python, python3}；`argv[1]` 必须**恰好**是 `tools/run_cv_probe.py`
   （绝对路径形式须 resolve 后等于 staging 内该文件）。
2. 其余必须是**成对**的 `--key value`；出现裸位置参数、重复 key、或 `--key` 后缺值 ⇒ **DENY**。
3. `--key` 必须来自**显式枚举的白名单**（按 cv_toolbox 实际 recipe 的参数逐个列全，不许靠猜；
   枚举依据写进代码注释）。**未知 key ⇒ DENY（fail-closed）**。
4. **每个 value 走与 `_validate_request_file` 完全相同的校验**：
   `_lexical_check` 无条件；path 角色的 key 再走 `_path_arg`；
   **输出角色的 key（至少 `--out-dir`）必须落在可写根内**，与 R2-2 的 request 侧口径**共用同一实现**。
5. `COMPOUND_TOKENS`（`;` `|` `&&` `` ` `` `$(` `>` `<`）检查**保持不变**，仍对整串生效。
6. `python -c` 仍禁。

### P1-2 · wrapper 侧对齐

`isolation_templates/run_cv_probe.py` 必须接受该直接带参形式，
并施加与 guard **同一份**输出根约束（沿用 r3 已建立的共享实现，不要再写第二份）。

### P1-3 · 必须新增的锁

| 锁 | 期望 |
|---|---|
| 直接带参、合法 `--out-dir out` | **ALLOW**，且真跑 helper 后产物落 `out/**` |
| 直接带参、`--out-dir tools` | **DENY** |
| 直接带参、`--image` 越界（含裸无后缀 symlink） | **DENY** |
| 直接带参、未知 `--key` | **DENY** |
| 直接带参、裸位置参数 / 重复 key / 缺值 | **DENY** |
| `--request <json>` 老形式 | 仍 **ALLOW**，行为不变 |
| `argv[1]` 指向别的脚本 | 仍 **DENY** |
| 含复合 shell token | 仍 **DENY** |

**E2E 锁**：沿用 R2-2 已有的「真跑 helper + 整树 diff」夹具，为直接带参形式各加一条
（合法 ⇒ 只在 `out/**` 新增；非法 ⇒ hook 即拒、树零变化）。

### P1-4 · directive 同步

改 `AI_agent/logs/experiments/2026-07-31_sm24_e2e_retry/reader_directive.md` §2 的调用说明：
写明现在可以**一次调用**跑探针，并给出确切样例；保留 `--request` 形式作为复杂请求的备选。
**这条必须做** —— 机制修好了但执行者不知道，等于没修。

## 3. 纪律

1. 骨架不许自行改动；有错**停下上报**。
2. **不许弱化任何既有安全性质。** 本批已有的八条红线 + r2/r3 新增的收紧全部必须保持。
   交付时请自证：把 r2 复审方做过的「44 形状 `f98d248` vs HEAD 差分」重跑一遍，
   报告 DENY→ALLOW 的条目；**除本单授权的探针直接形式外，不得出现任何新的 DENY→ALLOW**。
3. 每把新锁给 neuter 自查（定点破坏 → 真跑 → 报实际变红的测试名）。
   本批至今已抓到两把假锁（夹具形状、常量比对）—— 对自己的锁用同样怀疑。
4. 只碰 `src/agent/execution/isolation_templates/**`、`src/agent/execution/isolation.py`（若共享实现需要）、
   `AI_agent/logs/experiments/2026-07-31_sm24_e2e_retry/reader_directive.md` 及相关测试。
   **不碰** `src/agent/judge/**`（已 CLOSED、须字节稳定）、`case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md`。
5. 基线 = **1917 passed / 10 xfailed / 0 failed**（主控已独立复核）。
   中间轮用 `affected_tests.py` 算子集；交付前跑一次全仓。
   ⚠️ 已知：`test_gt_discipline.py` 的词法门**结构上无法被子集工具路由到**，只有全仓能抓 —— 别省那一次全仓。
6. 执行日志落 `AI_agent/logs/reviews/execution/2026-07-31_probe_ergonomics.md`。

## 4. 主控裁定：候选 #4（预扫信噪比）本轮不动

预扫在平面上产出约 803 个候选，含大量尺寸刻度与家具框，信噪比确实低。**但不在本轮改**：

1. **因果链是推测的**：07-30 真正画错的来源是**尺寸链算术**（15 条墙全 `dimension_derived`、
   北立面链 `540|1600|2520|4800|540` 的累加位置被画成四道内墙），不是预扫候选。
2. **预扫是喂给被测对象的输入**：在测量轮前夕对它做投机改动 = 自己制造新变量，
   而本轮已经动了三个变量（脚手架 / 判卷层 / directive）。
3. directive 已把预扫降级为「只是看哪儿、绝不是画的理由」，并要求执行者登记
   「预扫到底省了探针还是费了时间」。**拿这一轮的数据再决定**，比现在猜更省。
