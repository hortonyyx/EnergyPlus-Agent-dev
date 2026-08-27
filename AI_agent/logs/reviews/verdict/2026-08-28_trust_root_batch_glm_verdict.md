# 跨家族裁决 · 信任根三条 + 语料快照常量（`b1ad92a`）

- **日期**：2026-08-28 · **复核方**：GLM（跨家族）· **被审对象**：commit `b1ad92a`（仅此一个提交）
- **开工自检**：`git rev-parse --short HEAD` = `b1ad92a` ✅ · `.pth` = `/workspaces/EnergyPlus-Agent-dev`（主树）✅
  · `git show --numstat --format="" b1ad92a` 与复核单 §〇 **逐字一致** ✅
- 工作树核对：`git diff b1ad92a --stat -- src tests case_tests scripts` = **空**（未提交改动全在 `AI_agent/`，确系 orchestrator 的，不在范围内）✅

---

## 1. 裁决：**APPROVE-WITH-FINDINGS**（0 阻断 · 6 不阻断）

四条需求（F-116 / F-117 / F-118 / N-B）的**承重部分全部落地且被本复核独立验证**；
三条红线（位置不承权 · fail-closed · 不为绿动指纹）经变异实验**均未发现被触碰**。
本单没有会让 sm25 掉出 `reproduced` 或让全量出真红的问题。

**阻断**：无。

**不阻断 findings**（G-1 … G-6，见 §3；G-1 是本轮最值钱的一格）。

---

## 2. 对 §二 O-1 / O-2 的独立复核

> ⚠️ 先记一行外围数值错（按 §五 分层不停工）：复核单 §二 引用的行号全部对不上文件。
> 实际位置：`tests/test_f97_vector_contract.py:476`（`_REPO_ROOT` 行）、`tests/test_gt_raw_layer.py:394`（`LOGS_EXPERIMENTS_ROOT`）、`:414-417`（四条计数断言，非单子上写的 95/115/117/118）。
> **内容本身全部属实**，且 §〇 numstat、分布表（我独立重算，逐字一致）、复现门读数均复现无误——只有行号错。

### O-1（同一 commit 立了 `_REPO_ROOT` 范式，又在另一文件用 cwd 相对）——**成立**

实测从 `/tmp` 跑 `test_f116_0` ⇒ **响亮红**，但红在 O-1 点名的那三行**之前**：
`_signed_request_sha256` helper 读 cwd 相对的 ack 路径直接 `FileNotFoundError`。
即：**cwd 依赖是 `test_gt_raw_layer.py` 的模块既有风格**（f111 系 helper 同样如此），
本 commit 的新增行只是延续了它，不是新开的坏头。后果等级 = **fail-loud（摩擦），非 fail-silent（假绿）**——
`== 4`（414 行）在 cwd 错位时也会先于 `== 0` 两条失败，真空绿通道被堵死。
判：成立、不升档，登记统一（G-5）。

### O-2（`==4`/`==1` 是快照，承重的只是 ≥1）——**成立，且你对 `==0` 那两条说轻了**

我做了单子要的攻防实验（三格齐全）：

- **施加变异**：往 `AI_agent/logs/experiments/`（新建探针目录）拷一份 sm25 的签字 `request.json`
  ——即「新实验顺手拷一份」这个**合法动作**（logs 是声明可清理的过程目录，拷份数天然波动）。
- **结果**：`test_f116_0` 红（`tests/test_gt_raw_layer.py:414` AssertionError，4→5）；**`test_f116_a` 仍绿**
  （牙在 5≥1 下完全不受影响）⇒ **`==4` 不承重，`>=1` 就够**。探针删后复跑恢复绿。
- **对「有没有理由必须精确」的回答：没有**。唯一辩护是「多一份副本该被看见」，但那应显式声明成清点闸，
  且对 logs 这种可清理目录做清点没有信任价值。你单子里的替代读法是对的，照它办。

**但 `==0` 两条不是你说的「真不变量」**（`:415` sm24-logs==0、`:417` sm25-fixtures==0）：
它们同样是**当前磁盘状态的事实**。把 sm24 的签字 request 拷进 logs（同样合法）⇒ `:415` 红。
四条里真正结构承重的只有两条方向断言（sm25-logs ≥1、sm24-fixtures ≥1）——那正是两把存货锁的牙所在。
`==0` 的红只有「失明分布变了、请重看 f116 注释」的提醒价值，用 `assert` 表达过重（G-2）。

---

## 3. §四 那一格的产出：五个变异实验（每个都按三格交付）

### ⭐ G-1（主产出）｜实验 B：**os.walk 实现的第三方向回退腿，10 把锁全绿骗过**

- **施加的变异**：`find_signed_request` 主查找后加「向后兼容」回退腿，用 **`os.walk`** 实现（不经
  `Path.glob/rglob`），根 = `case_tests/test_baseline/gt`（其下 `gt/<case>/review/` 当前**无任何** `request*.json`——已实测确认，两份 case 的 review/ 都只有那五件审计文件）。
- **红在哪**：**没红**。`f116 or f111` 全部 **10 passed**。结构锁 `f116_c` 只拦 pathlib 的 glob/rglob（施工方自陈 §一.1，实证确认）；存货锁 `f116_a`/`f111_c` 只覆盖 logs-sm25 / fixtures-sm24 两个已知方向。**两类锁的交集盲区 = 非 pathlib 枚举 × 第三方向**。
- **②变异确实生效的独立证据（关键）**：同一变异下往 `gt/sm25-L_anchor/review/` 暂放一份签字
  request（探针）⇒ `f116_a` **立刻红**（腿捞到真件返回非 None，`:430`）；探针删除后恢复全绿、`case_tests/` 干净。
  ⇒ 腿不是「没跑」，是「跑了但那个方向暂无货」。**骗过的机制是潜伏，不是失效。**
- **③实害路径是真实的，不是我编的**：派工单 §〇 自己记录了 F-117 的登记原文就是
  「`promote_gt_v3` 的拷贝清单加 `request.json`」——**拷的正是 `gt/<case>/review/`**。谁哪天照登记原文补一刀，
  这条腿就活了；F-118 README 刚写的「the ONLY place … will ever look」被静默打破。
- **处置判断：登记即可，不必现在补**（§0.1：不做它，下一次跑测照样能跑能读；且「新枚举原语」黑名单按
  `lexical-guard-cannot-be-completed` 的教训永远补不完）。但有两个便宜动作值得记：
  ① `f116_c` 的 docstring 把「no fallback of ANY shape」收窄成「no widening of the **search-root** face」——
  现在的声称比锁的真实牙强；② 若要补牙，方向是把 os.walk/scandir/listdir 一并纳入记录器（接受它仍是黑名单），
  或让「有存货的方向必有存货锁」成为派工时的显式检查项（本单 logs-sm25 正是这个思路的兑现）。

### 实验 A（对照）：同一 os.walk 腿指向 logs 方向 ⇒ 被抓

- 变异同上、根改回 `AI_agent/logs` ⇒ `test_f116_a` **红**（`tests/test_gt_raw_layer.py:430`，返回的正是
  logs 里捞到的 `d738d0ac…` 真件——失败消息本身就是变异生效证据）；`f116_c` 仍绿（结构锁确实看不见 os.walk）。
- **结论**：施工方自陈 §一.1 完全属实；「结构锁 × 存货锁」的组合在**两个已知方向**上互补成立，
  盲区只在第三方向（G-1）。

### 实验 C：`SIGNED_REQUEST_GLOB` 放宽成 `*.json` ⇒ 全绿，且**无实害（锁不红恰好正确）**

- 变异：`SIGNED_REQUEST_GLOB = "*.json"`。10 把锁全绿；生效证据 = 真实根下 `find_signed_request`
  仍解析成功（宽 pattern 确实在跑，把 manifest 等也喂给了解析器）。
- 分析：**根内 pattern 回宽不扩大信任面**——内容重算是唯一权威（红线 1），解析失败 continue、
  哈希不匹配不放行。这与 `f116_c` 守「搜索根面」的牙**恰好同构**：锁看不见的回宽（pattern）正是无实害的回宽。
- 处置：登记（归入 G-1 的 docstring 收窄动作）。顺带记录：派工单 3.1 ③ 曾把「glob 放宽成 `*.json`」列为
  候选第三方向——若施工方当时选了它做第三格变异，会发现它**不红**；实际选的 review/ 方向（glob 实现）恰好有牙。
  三格③通过是**真的**，但「自选方向恰好避开无牙形态」这一点单上没人提。

### 实验 D：F-117 回滚不对称 ⇒ 孤儿实锤，缝隙当前不可达

- 变异：在 `_promote_signed_inputs(...)` 调用行**之后**加 `raise`（模拟未来在 sources 写入后追加的步骤失败）。
- 结果：`f117_b` 红（crash 形态：promote 抛异常）、`f117_c` 绿（其注入点在 copyfile=写入中，造不出
  「写入成功后失败」形态）。**孤儿实测**：失败后 `gt/sm24_anchor/` 被回滚**不存在**，
  但 `gt_sources/sm24_anchor/{request.json, source.dxf}` **残留**——正是「签字输入落地、答案没落地」的半成品。
  根因：`except` 块只 `rmtree(destination)`（gt 侧），对 `sources_destination` 无清理。
- **缓解（因此不阻断）**：① 当前 commit 里 sources 写入是 try 的最后一句，**该缝隙不可达**
  （顺序运气而非结构保证——docstring 的「or neither does」声称比实际强，G-3）；② 孤儿会让下次 promote 撞
  `promotion_sources_target_exists` 响亮挡住，fail-closed 仍在。
- 处置：登记。补法便宜：except 分支加 `if sources_destination.exists(): rmtree`，或 f117_c 加一个
  replace-后-失败注入格。

### 实验 E：N-B 非空守卫攻另一端 ⇒ **找不到骗过的形态（锁好）**

- 形态①（非空、合法 JSON、全垃圾→unknown）：语料根指到 /tmp 垃圾目录，`_require_nonempty_corpus`
  **通过**（非空守卫放行——正确，它管空不管脏），但测试1红（`assert excluded`，"ran zero times"）+
  测试2红（`assert not unknown`）——**双闸都有牙**。
- 形态③（非空、纯 legacy 无 sidecar）：测试1红（excluded 空）、测试2绿——**正确**（纯 legacy 是合法 slice）。
- 软点（G-6）：`assert excluded` / `legacy > 0` 仍是**语料组成下限快照**——sidecar 形态若整体退场（合法演变）
  会红；但比 `== 43` 软一个量级，且本批第③步只会增不会删 sidecar，可接受。
- ⚠️ 过程记录：我的首版探针用字面量字符串比较常量（真实值是 `'unknown'` 等，不是 `'CONTRACT_UNKNOWN'`）
  ⇒ **假红**，靠「unknown=0 却报绿」这个反直觉读数当场抓住后修正。探针每一步先自证——这条纪律又挣了一回饭钱。

### 施工方自陈 §一 三条的处置

| 自陈 | 复核结论 |
|---|---|
| 1. 结构锁只拦 `Path.glob/rglob` | **实证确认**（实验 A：f116_c 对 os.walk 绿；实验 B：全绿骗过）——处置见 G-1 |
| 2. `promotion_sources_target_exists` 游离在矩阵外 | **属实**：该前置在 `tests/` 下零直接测试（grep 零命中），矩阵字典里只有旧前置 `promote_target_not_exists` 的格。**不升格**：其实害（覆盖已签字输入）被内容重算兜住（坏件 ⇒ `inputs_unavailable`，响亮不静默），一个 3 行单测可补，登记即可 |
| 3. N-B「无 UNKNOWN」是经验事实非结构保证 | **已被本单提升为被守卫的不变量**（实验 E：垃圾语料会红）——这正是那把锁的职责本身，不需升格 |

---

## 4. 独立全量（`-n 6`，不带 `-m`，HEAD = `b1ad92a`）

**汇总行原文**：

```
3138 passed, 13 xfailed, 212 warnings in 1005.47s (0:16:45)
```

**`.pth` 哨兵**（跑前 / 跑后两次相同 ✅）：
`58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`（内容 = 主树路径）。

**我自己的增量算术**：`3138 = 3130（08-27 权威基线 `3fe0d29`）+ 8（本 commit 新增测试）`，
8 = `test_f116_{0,a,b,c}`（4）+ `test_f117_{a,b,c}`（3）+ `test_n_b_empty_corpus_root…`（1）；
两个 `test_r3_*` 是改写非新增。与 orchestrator 权威全量（3138）**一致**；
与施工方拆分口径 `3113（not mutation）+ 25（mutation）= 3138` 也一致——其中 **25 格我实读复核**
（`pytest -m mutation --collect-only` ⇒ `25/72 tests collected (47 deselected)`），
§6.2 的疑点就此销账：矩阵确实是 25 格。

---

## 5. 两份 case 复现门读数（对照派工单 §四 预期）

| case | 读数（本复核独立跑 `verify_raw_layer_reproduction`） | 预期 | 判 |
|---|---|---|---|
| `sm25-L_anchor` | `reproduced` | `reproduced`（不许退化） | ✅ |
| `sm24_anchor` | `implementation_drift`（moved: `converter_sha256`, `vg_implementation_sha256`） | `implementation_drift` = **通过** | ✅ |

与派工单预写读数逐字一致；本 commit 未动任何指纹（红线 3 遵守）。

另：F-116 分布表独立重算（走生产哈希重算路径、非文本 grep）——
sm25 `d738d0ac…`：gt_sources=1 · logs=4 · fixtures=0；sm24 `ae0fec08…`：gt_sources=1 · logs=0 · fixtures=1——
与派工单 §〇 逐字一致 ✅。

---

## 6. 我最没把握的地方

1. **G-1 的「登记即可」判级**。潜伏型缺口按 §0.1 不做不影响跑和读，但它的活化条件（F-117 登记原文照做）
   是一份**真实存在、已被派工单 §〇 记录、但没人销账的建议**——登记的债会不会被还，取决于 plan.md 的纪律，
   不取决于结构。若 orchestrator 认为「活化条件有书面出处」足以升格，我不反对。
2. ~~**变异矩阵格数**~~ **已销账**：起草时我用正则数 `MUTANTS` 字典得 ~50 个 key、与「25 格」对不上；
   全量结束后以 `--collect-only` 实读复核 = **恰好 25 格**（见 §4）。教训照旧：数格子用收集器，不用正则。
3. **O-1 的严重性**。我按「fail-loud 摩擦」定级，依据是单一形态（/tmp cwd）的一次实测；若存在某种
   **从子目录跑 pytest 却恰好有同名相对路径**的世界（例如某个 case 工作目录下有 `AI_agent/logs`），
   它会从响亮红变成静默错读——我没穷举这种巧合面。
