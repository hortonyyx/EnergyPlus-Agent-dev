# 跨家族复核裁决 · F-158 第三轮（返工 2）

- 日期：2026-09-03
- 复核方：GLM 家族
- 施工方：Claude 家族
- 复核对象：净 diff `b5dc426..2465c75`（c509b41 / 60a3258 / c3abb1a / 28148ea / 097803e / 2465c75）
- 复核工作树：`/tmp/f158_rework2_claude`
- **结论：✅ APPROVE-WITH-FINDINGS —— 阻断 0 / 不阻断 3**

## 〇、环境与范围自证

```
$ cd /tmp/f158_rework2_claude && pwd && git log --oneline -1
/tmp/f158_rework2_claude
2465c75 09.03y_F158_rework2 #8: orchestrator-run full suites, 3720 passed both with and without .env
$ python -c "import ep_no_billed_gate as m; print(m.__file__)"
/tmp/f158_rework2_claude/ep_no_billed_gate.py
```

- 未跑 `pip install -e .`；未修改任何跟踪文件；未写主树。
- 判据①在**独立临时 worktree**（`git worktree add --detach /tmp/f158_glm_old b5dc426`）上跑，未切换本树分支；全部探针放 `/tmp`（`f158_glm_probe` / `f158_glm_c`），树内临时探针测试文件每条命令后即删，取证完毕 worktree 与探针目录均已清理。收尾 `git status --porcelain` 仅剩本裁决单之外那张 staged 复核单（派工单本身）。
- `git diff --check b5dc426..HEAD` 干净；净 diff 共 5 文件（4 代码/测试 + 执行档）。
- 全程 `-n 6`（探针单文件腿用 `-n0` 串行以精确控制单进程时序，读数以 summary 行为准，无同机竞争假红嫌疑——每条跑都有 summary 行）。

## 一、⭐⭐⭐ §二 两问正面回答

### ① 上一轮阻断 B-1：**【缩小了，没有关掉】——且 GPT 那条具体探针今天仍原样复现**

我复刻了 GPT 裁决 §三③ 的探针形状（命令行 `-p` 插件在 **import 期**经禁代理 urllib 访问 `http://192.0.2.1/`，异常链含 `ProviderCallBlocked` 判 BLOCKED），新建探针未抄树内任何文件：

| 腿 | b5dc426（旧） | HEAD 2465c75（新） |
|---|---|---|
| control（ini 钉生效）| **BLOCKED**，1 passed | **BLOCKED**，1 passed |
| `-o addopts=` + `-p` 探针 | **NOTBLOCKED(TimeoutError; chain=['TimeoutError'])**，1 failed | **NOTBLOCKED(TimeoutError; chain=['TimeoutError'])**，1 failed |

- **判据①（通过）**：旧提交上同一探针精确复现绕过——异常链里没有 `ProviderCallBlocked`，调用确实越过门进了真实网络路径（TEST-NET、禁代理，未碰真 provider）。
- **判据②（如实报）**：同一探针在新提交上**读数逐字相同**。pre-parse 插件 import 期那个窗**原样开着**。

**但同时「缩小」也是实测事实**（这部分不是本轮施工缩小，是上一轮「仓库根插件 + conftest 薄壳」已带来、本轮复核实测确认）：

```
真实 tests/ 树 + -o addopts=（conftest 兜底仍在）⇒ T1:  1 passed
```

⇒ 「`-o addopts=` ⇒ 门失效」的旧表述**已不成立**：清掉 ini 钉后 conftest 一 import 就自装门（`tests/conftest.py:14` + `ep_no_billed_gate.py:278`，两处源码亲核），**所有真实测试体仍被拦**。剩余暴露面 = **pre-conftest 窗**（pre-parse 插件 import 期 + conftest 链更早一级，见判据③载体 C）。GPT 探针踩的恰是缩小后仍开的那个窗，所以探针读数原样。

### ② 甲案**算完成本轮任务书**；验收 #1 **确系派工方基于错误前提所写——判据错了，改判据**

**前提错在哪（亲测）**：「用 `-o addopts=` 起测试 ⇒ T1 红」隐含「`-o addopts=` 会让门没装上」。在真实 `tests/` 套件里这个蕴含为假：conftest 的 import 副作用把门装上，T1 在测试体发起的真实 connect **被拦**（上表 1 passed 即 BLOCKED 证据）。**T1 绿是正确行为，不是缺陷。**

**正确判据形态**：「任何**真的让门没装上**的起法 ⇒ T1 红」——施工方交付的牙锁证明的正是这一条，且施工方演示红所用的「无 conftest 最小树」不是逃避，而是唯一能把「门真关」造出来的合法实验设置（真实树里 conftest 兜底让门关不掉——这是防御在起作用）。

**甲案兑现判定（我用自己的载体验证，见 §二判据③载体 A）**：真实树 + `-o addopts=` + `--noconftest`（两道接线全剥）⇒ **T1 红 rc=1**，文案直说「the way it was started disabled the no-billed-calls gate」。⇒ 「任何门没装上的状态都撞同一堵墙」这个甲案承诺**在真实树成立**。

**边界（诚实账，不构成返工理由）**：pre-conftest 窗仍开着，且甲案对它**发现不了**（窗内出网发生在 T1 能跑之前；载体 C 组合读数实证：窗内 NOTBLOCKED + T1 仍绿）。这是任务书 §一自己拍板的路线（⛔ 不逐个堵启动形态）+ T2 docstring 已如实声明「detector, not an interceptor / 钱已花」。**B-1 的「这一类缺陷已关闭」没有发生；但本轮的题（用户甲案）本来就不是「类关闭」——按题判，不按上一轮已被推翻的题判。**

## 二、§三 三条判据（逐条）

### ① 旧提交复现：通过

（见 §一① 表格左列；worktree `b5dc426`，control BLOCKED / 变异 NOTBLOCKED 1 failed，异常链无 `ProviderCallBlocked`。）

### ② 新提交同探针：如实报——**变异腿仍 NOTBLOCKED、测试红**，与旧提交逐字同读数

解释见 §一：窗口（pre-parse 插件 import 期）原样；真实测试体被 conftest 兜底（A2 腿 T1 绿）。

### ③ 自造【不同形】载体：**三个**，均不复用施工方四载体（import 期 socket 四形态）、均不只复用 GPT 的 `-o addopts=` 形状

**载体 A —— `--noconftest` 启动开关（开关形态，非「无 conftest 文件」的树形态；真实树、跑常驻 T1 本体而非拷贝副本）**

```
A1: 真实树 -o addopts= --noconftest ⇒ T1 红 rc=1
    AssertionError: F-158 egress gate did NOT intercept a connection to TEST-NET
    ('192.0.2.1', 80): connect() returned instead of raising ProviderCallBlocked.
    The gate is not installed in this pytest process — the way it was started
    disabled the no-billed-calls gate …
    （本沙箱 connect() 假成功，走的是 T1 的 else 分支——该分支真实有牙）
A2: 真实树 -o addopts=（不剥 conftest）⇒ T1 绿 1 passed（= 门在拦，见 §一①）
```

⇒ **甲案核心承诺（门真没装 ⇒ T1 必红点名）在真实树被不同形载体验证成立。**

**载体 B —— `PYTEST_ADDOPTS` 环境变量注入探针、不清 ini 钉（阴性对照，兼验 docstring 加载序声明）**

```
PYTEST_ADDOPTS="-p f158_glm_addopts_probe"（ini 钉原样）⇒ BLOCKED，1 passed
```

⇒ 门（ini addopts）先于 PYTEST_ADDOPTS 注入的探针加载；docstring「ini → PYTEST_ADDOPTS → 命令行」的顺序声明**在此向量上实测成立**，该向量单独不构成绕过。

**载体 C —— rootdir 一级 conftest.py（conftest 形态的 test-owned import 期代码，非 `-p` 插件）**

tmp 树：根 `conftest.py`（import 期 urllib 出网）+ `tests/conftest.py`（拷真薄壳）+ T1 拷贝，两腿：

```
腿1 门钉在（pyproject 钉 -p gate）⇒ root conftest 出网 BLOCKED；2 passed
腿2 -o addopts=（钉被清）        ⇒ root conftest 出网 NOTBLOCKED(TimeoutError)；
                                    1 failed(读数断言) + T1 仍 1 passed
```

⇒ 同一个 pre-conftest 窗**不止 `-p` 插件一种形态**；且组合读数实证甲案对它测不到红（窗内出网成功、T1 绿）——与 T2 声明一致，登记为 N-2。

## 三、§四 P-1 / P-2 / P-3

### P-1（T1 是真·行为自检）：通过

- 真发起连接：`sock.connect(("192.0.2.1", 80))`（`tests/test_f158_gate_behavioral_selfcheck.py:74`）。
- 地址 = RFC 5737 TEST-NET-1（:51），不可路由、永不可能是真 provider。
- 禁代理：raw `socket.connect` 直连 IP，不读 `*_proxy`（HTTP 代理是客户端层概念）。
- 超时 `settimeout(0.05)`（:55,:71）。
- ⛔ 不读 `_INSTALLED`：模块级不 import 门（:33-34 有明确理由注释），异常按 `cls.__name__ == "ProviderCallBlocked" and cls.__module__ == "ep_no_billed_gate"` 识别（:63）。
- `else` 分支兜底「connect 意外返回成功」形态（:90-97）——本沙箱该形态真实发生（载体 A1 走的就是它），证明这不是死代码。

### P-2（牙锁有牙）：通过

- 常驻实跑：`test_behavioral_selfcheck_has_teeth` + 钉锁 + 双载体锁 **3 passed**（聚焦，`-n 6`）。
- 牙锁在子进程里对**同一个 T1 文件**做两态对照：门关（`-o addopts=`、无 conftest 树）rc≠0 + `1 failed` + 文案含 "egress gate"/"billed"；门开（显式 `-p ep_no_billed_gate`）rc=0 + `1 passed`。
- **「红只在无 conftest 最小树里出得来」——算数。** 牙锁保护的命题是「T1 具备分辨力（门关必红）」，该命题的正确证法就是在门真关的环境里跑 T1；真实树里造不出「门关」状态正是 conftest 兜底在起作用，不是牙锁的缺陷。且此两态对照已固化为常驻锁，防「恒绿=不可观测」。

### P-3（T2 改诚实）：通过，附一条残留（N-1）

我自己 grep（`structurally impossible` / `no test can ever` / `cannot ever` / `never reach the network` / `任何测试`，含 py/md 面）：

- 其余命中全部是别的语境（`deterministic.py` segfault 类、`schema.py` drift 类、`validator/checks/correction.py` shadow、`test_checks_mep_assembly.py:725` disposition()、`test_f9_…` report 构造）——均与「测试出网」无关。
- `ep_no_billed_gate.py:9` 的命中恰是**否定**绝对断言的句子（"It is **not** true, however, that *no test can ever* reach the network…"）。
- 必含的半句在：`detector, not an interceptor` + `has already spent the money`（:17-20）。
- ⚠️ 残留：`:12-15`「goes **red** for any run whose gate is off」与 T1 文档同句式仍偏绝对——见 N-1。

## 四、§五 全量读数核对（未重跑，按复核单只核读数）

- 执行档 #8（orchestrator 代跑，处理方式正确、无占位符）：两跑均 `3720 passed / 2 skipped / 13 xfailed`、exit 0，带/不带 `.env` 逐位相同。
- 逐位闭合：基线 `3717`（GPT 上轮自跑）`+ 3 = 3720` ✓；skipped 2 / xfailed 13 与基线一致 ✓。
- `+3` 的算术亲核：净 diff 新增 `def test_` 恰 3 条（T1 行为自检 / 牙锁 / T3 镜像锁），三条聚焦实跑全绿（T1+T3 2 passed；牙锁含上节 3 passed 内）。

## 五、不阻断 findings（3）

| # | 内容 | 依据 |
|---|---|---|
| **N-1** | T2 残留过度承诺：门 docstring「goes red **for any run** whose gate is off」与 T1 文档「you will *see red* for a run whose gate was off」——「any run」在**没收集 T1 的跑**上不成立。实测：`-o addopts= --noconftest`（门真关）只跑 `tests/test_affected_tests_map.py` ⇒ **15 passed 零红**。应限定为「any run **that collects the self-check**（全量及常规 `tests/` 跑均收集）」。文字修正一轮即可。 | 载体 A1 同环境对照实验 |
| **N-2** | pre-conftest 窗的形态登记不全：门 docstring「Residual gap」一节点名了 `sitecustomize`/`.pth`/更早 addopts 插件，**没点名「conftest 链上更早一级（rootdir conftest）」形态**——载体 C 实测它可越门而 T1 不红。今天仓库根无 `conftest.py`（已核），实害=0；补进 residual gap 文字即可。 | 载体 C 腿2 |
| **N-3** | T3 锁只覆盖**当前已存在**的镜像站点（`_mirror_repo`）；未来新增「拷 pyproject 去跑子 pytest」的站点不会被自动锁住。施工方已诚实标注并给归属（词法护栏固有边界）——维持其登记口径，不阻断。 | `tests/test_gt_promotion_path.py` 新锁 + 执行档 #5 残留声明 |

## 六、裁决理由（为什么不因「GPT 探针仍漏」而 REWORK）

上一轮 GPT 的返工目标（「让 `-o addopts=` 也不能使早期插件越门 + 为有效启动配置补永久回归」）已被本轮任务书 §一**明令取代**（用户甲案拍板：⛔ 不逐个堵启动形态）。本轮按甲案交付的三件事全部有效：T1 行为自检有牙（判据③载体 A 实证）、T2 承诺改诚实（含 detector-not-interceptor 半句，残留仅 N-1 文字级）、T3 镜像锁落地；全量 3720=3717+3 逐位闭合。若因「窗还开着」判 REWORK，等于用已被推翻的题判卷。pre-conftest 窗的真实关闭路径（进程/OS 层 deny）任务书已注明出 harness 范围。

**最终：APPROVE-WITH-FINDINGS，阻断 0，不阻断 3。**

裁决完成后的最终状态：

```
$ git status --porcelain
A  AI_agent/logs/reviews/request/2026-09-03ab_f158_rework2_crossreview.md   （派工单本身）
?? AI_agent/logs/reviews/verdict/2026-09-03ab_f158_rework2_crossreview_glm.md（本裁决）
```

除上述两份文档外工作树干净；临时 worktree 与全部探针已删除。
