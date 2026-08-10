# 交叉审请求书 · F-20 整批（修法 + 12+1 把锁）· sol

- **日期**：2026-08-10 · **审阅席**：**`gpt-5.6-sol`**，effort **max** · **只读**
- **为什么是你**：**你是本批设计稿的出稿方，但施工是 Claude 侧做的** ——
  按「谁写谁不批」，Claude 侧施工 ⇒ 审阶梯落 GPT 侧。
  ⚠️ **但请注意一个利益冲突并据此调整重心**：**这份设计稿是你写的**
  ⇒ 你天然倾向认为「按稿实现 = 正确」。
  **本审要防的不是「实现偏离了你的设计」，而是「实现照做了你的设计，但设计或实现里有洞」。**
  ⇒ **请把重心放在「锁到底绑没绑住」和「有没有洞是我们三方都没想到的」。**
- **审阅对象**：两个提交
  - **`3303eee`** = F-20 修法主体（4 文件，+698 −65）
  - **`ab694b4`** = 轻门 MAJOR-1 的补锁（2 文件，+15 −1）
- **命令**：`git show 3303eee` · `git show ab694b4` · `git log -3 --stat`

---

## 1. 背景（三步都已过审，本审是最后一道）

| 步 | 谁做 | 结果 |
|---|---|---|
| 调查 | Claude 侧 Sonnet | orchestrator 轻门 **PASS**；[全档](../../experiments/2026-08-10_f20_validate_case_v3_proof/README.md) |
| **设计稿** | **你（sol）** | orchestrator 对抗审两轮 ⇒ **APPROVE**（0 BLOCKER / 0 MAJOR / 2 NIT）；[稿](../../../proposals/f20_validate_case_v3_proof_design.md) |
| 施工 | Claude 侧 Sonnet | orchestrator 轻门 ⇒ **PASS-WITH-CHANGES**（1 MAJOR，已补掉）；[轻门裁决](../verdict/2026-08-10_f20_orchestrator_lightgate.md) |

**用户 2026-08-10 拍板的原则**：
> 有正式记账（V2）的 run 一律以账本指向的 accepted 产物为唯一权威；
> 没记账 / 旧格式（V1）记账的老 run 保留今天的 stage-root 入口。

---

## 2. orchestrator 声称的验收结果（**请逐条验，⛔ 别采信**）

| # | 声称 | 你要验什么 |
|---|---|---|
| **C1** | 独立全量 **2358 passed / 10 xfailed / 0 failed**（基线 2345 → +12 锁 +1 冻结锁） | 自己跑一遍。⛔ 不要 `-n auto`（16 worker 实测 ~98% 静默 OOM）；⛔ 输出中间不接管道 |
| **C2** | 三条禁令全守：未改 `stage_runner.py` · 无 fail-open · 新检查只在 `1_correction` | 读 diff 核实。**尤其 fail-open**：V2 分支任何失败路径是否**真的**没有回到 stage-root |
| **C3** | 两条 NIT 全落实（manifest 读不出来 ⇒ 单独 `FAIL` 不当成「无账本」· 零窗 v3 已参数化） | 核实这两条**各自有锁**，且锁**真绑** |
| **C4** | 真实产物 `run_2026-08-09_f18_e2e_verify`（全项目唯一 v3 产物）trust PASS · digest 非空 · `approve_geometry` 签发成功 | 自己重跑（**只读或 `/tmp` 副本**） |
| **C5** | 换方向 neuter：三态塌回二值 ⇒ **恰好 L6 红零连带** | 自己复现。**并判断：L6 是不是只对这一种塌法敏感？换别的塌法（比如让无账本落进 V2 分支）还红不红？** |
| **C6** | 补锁后：trust 行挪进 kernel report ⇒ **新冻结锁转红** | 自己复现。**并判断这把冻结锁的锚点选得对不对**（见 §3） |

---

## 3. ⭐ 本审最该盯的四处

1. **⛔ 冻结锁的锚点只有一个 run** —— 全仓扫描后**只有** `run_2026-08-07_f13_e2e_verify`
   能产出非空 `geometry_digest`（其余全是 `None`）。
   **请判断**：把「历史几何批准不失效」这条性质**押在单一 run 上**够不够？
   它 `blocked=True`（缺 `0_reading`），这会不会让锁本身脆弱？有没有更好的锚点或补充锁？
2. **⛔ 一个刚被戳破的空断言，可能不止一处** —— 轻门 v1 曾把施工席的
   「两个 golden 基线 digest 逐字节相同」当成有效验证，**而两边都是 `None`（`None == None` 恒真）**。
   ⇒ **请横扫这 13 把锁，找有没有别的「结构上恒真」的断言**
   （比较两个都为 `None`/空集/空列表；比较同一次调用的两个引用；断言落在「非 None / 总数变了」这类弱谓词上）。
   **这是本审的头号任务。**
3. **⛔ 锁粒度缺口（施工席已如实登记，orchestrator 判不追加，请你复核这个判断）** ——
   neuter②（trust BLOCK 后越权碰 stage-root）下 **L4/L5/L6/L7/NIT-1 不敏感**，
   只有 L2/L3/L8 红。施工席与 orchestrator 都认为「L2/L3/L8 已独立覆盖该防线、不需重复」。
   **你同意吗？还是说存在一条 L2/L3/L8 覆盖不到的越权路径？**
4. **⭐ 设计与实现的偏离（你最有资格判）** —— §2.2 那 11 行状态表，
   **实现是否逐行都有对应分支且语义一致**？特别是
   「V2 + legacy(v1/v2) 几何 ⇒ `PASS`、proof/evidence 为空」这一行 ——
   实现走的是 accepted attempt 而非 stage-root，**这对现有 V2 legacy run 是行为改变**
   （orchestrator 实测盘上 4 个有 accepted 记录的 V2 run 两份产物 DIFF=0 ⇒ 今天零影响，
   **但那是语料属性、不是代码不变量**）。**这个风险接受得对不对？**

---

## 4. 操作与边界

```bash
cd /workspaces/EnergyPlus-Agent-dev
git log -2 --stat
git show 3303eee
python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20_sol_full.log 2>&1; echo $? > /tmp/f20_sol_full.rc
```

⚠️ **观测通道纪律**：输出**直接重定向到文件**、退出码**单独落一个只属于该命令的文件**、
⛔ **中间不接任何下游管道**（`pytest | tee | head` 会因 `head` 关 stdin ⇒ `tee` 收 SIGPIPE
⇒ **连带打断 pytest**，而你看到的「退出码 0」其实是 `head` 的）。
⚠️ **另两条本轮实犯**：
① orchestrator 把 `nohup … &` 又叠进后台机制 ⇒ 外层报的「退出码 0」是**包装器的、不是 pytest 的**
（同上一条同病）⇒ **判据必须是「汇总行 + 属于该命令的 `.rc`」两者俱在**；
② ⛔ 但 **`.rc` 缺失只说明「没跑完」，不等于「被杀」** —— orchestrator 一度把一次
「停在 51%、日志 1438 字节」判成中断，`pgrep` 一查 **7 个 worker 全活着**、内存还剩 11 GB，
**它只是还在跑**（全量约 **7 分 45 秒**）。⇒ **判活查进程，⛔ 不许拿日志字节数/进度百分比当哨兵。**

**边界**：
1. ⛔ **只读审阅，不改任何代码。** neuter 只在 `/tmp` 副本里做（⚠️ 副本要拷 `data/` —— orchestrator
   本轮因漏拷 `data/dependencies/Energy+.idd` 拿到过一次「10 条红」的假结果）。
2. ⛔ 不许 `git add` / `commit` / 切分支。
3. ⛔ 不许读 `case_tests/test_baseline/gt/`。

## 5. 交付物

裁决书落 `AI_agent/logs/reviews/verdict/2026-08-10_f20_crossreview_sol.md`：

1. **总裁决** + BLOCKER / MAJOR / MINOR / NIT 计数。
2. **C1–C6 逐条**，各附**你自己的**证据（命令 + 输出片段 / 文件行号）。⛔ 不许以他人日志当证据。
3. **§3 四处的判定**，尤其**第 2 点（横扫恒真断言）的完整结果**。
4. **你没能验证的部分**，明确列出。⛔ 宁可留白，不要用推理填。

⚠️ 本项目里 **「放水比冤枉危险」**。拿不准就报出来让 orchestrator 裁决，
**不要因为设计稿是你写的就倾向放行。**
