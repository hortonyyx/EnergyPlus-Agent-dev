> ⛔ **orchestrator 落库说明（2026-08-27）**：以下为 GLM 家族**写在 `/tmp/ep_f97` 里的原件逐字**，未改一字。
> **总判 APPROVE-WITH-FINDINGS / 0 阻断 / 5 条不阻断。** ⇒ **F-97 过审，可并回主线。**
>
> ⭐⭐⭐ **本轮三件值得单独记的事**：
> ① **三条阻断三格全过**，且第三格是**双份**的 —— 施工方自己跑过一轮，复核方**另换方向再找一轮**
> （fifo 子进程判别 / 时间窗 / 环境级目录 / 语料重数），**未击穿**。
> ② ⭐⭐ **复核方当场推翻了自己上一轮的逐字处方并写进裁决**：施工方指出「fifo 挂死没有 except 捕得到」
> 与「`RecursionError` 既非 `OSError` 也非 `UnicodeDecodeError`」——GLM 用**干净子进程 8 秒超时**实锤了前者，
> 并交代**它自己第一版探针被 `TimeoutError ⊂ OSError` 的围栏伪影骗过**、已排除；
> 全盘接受 `is_file()` 边界方向。⇒ 「本轮你没有维持一致的义务」这句写进请求单是有回报的。
> ③ ⭐ **A8 `.pth` 哨兵首次生效**：开工前与交件前两次均 `/workspaces/EnergyPlus-Agent-dev`、期间零 `pip install`
> （orchestrator 交件后独立复核一次，同值）。

---

# 跨家族复核裁决 · F-97 契约判别器【第二轮返工】（GLM 家族）

- **日期**：2026-08-27　**复核席位**：**GLM 家族**（`glm-5.3`）
- **施工席位**：Claude 家族（第二轮返工）　**被审 commit**：`c3fc3fd`（worktree `/tmp/ep_f97`，开工自检 HEAD 对上）
- **请求单** → [`../request/2026-08-27_f97_rework2_crossreview_glm.md`](../request/2026-08-27_f97_rework2_crossreview_glm.md)
- **返工依据（我上一轮的裁决）** → [`2026-08-27_f97_rework_glm_verdict.md`](2026-08-27_f97_rework_glm_verdict.md)（REWORK / 3 阻断 / 6 不阻断）
- 全部读数来自本席自己的探针、跑测与两次变异抽验；施工自述只作线索。探针/变异均已还原并核净。

---

## 总判：**APPROVE-WITH-FINDINGS**（0 阻断 · 5 不阻断）

三条阻断 BLK-A / BLK-B / BLK-C **三格全过**：①在 `f2a8ccf` 快照上我全部独立复现
（BLK-A 三个已登记值全部塌缩为 `reading_view_legacy/CONSUME`；BLK-C 三形态裸崩且
**账本写入函数自己就是抛点**；BLK-B `[1,2,3]` 死于 `AttributeError` @ `pipeline.py:1368`
且账不存在、正对照 `mystery.json` 同一棵树点名 + 有账——缺口纯由入口顺序造成）；
②在 `c3fc3fd` 上同一批夹具 + 我另造的六种同族形态全部不再复现；③我按自己的方向
（fifo 子进程判别 / 时间窗 / 环境级目录形态 / 语料重数）另找，**未发现任何「已修形态类
换同形输入仍击穿」的命中**。

⭐⭐ **§3.3 那五条我全部独立验证成立，其中 #1 / #2 是对我上一轮 BLK-C 处方的实质性证伪
——我认，且本席拿出了比施工方更强的证据**：fifo 的挂死我用**干净子进程**（无任何信号机制）
8 秒超时实锤——`read_text` 对无 writer 的 fifo 是阻塞、不是异常，**任何 except 元组都接不住**；
20 万层嵌套的 `RecursionError` 在**照我处方逐字实现**的函数里原样逃出。
我上一轮那句「捕 `OSError` 与 `UnicodeDecodeError`」是不完整的处方，本轮裁决里正式更正（见 §更正）。
施工方换成「`is_file()` 边界 + 命名路径 + 兜底网」的方向**正确且必要**。

红集对账抽验两次（N2 / N7）红集逐条吻合、零附带；超范围零；全量 `3113 passed` exit 0。
新缝两条（均不阻断）：preflight 与首个消费者之间的**时间窗**（`*_view.json` 名文件后到 ⇒
崩在 `:1416` 且账缺该文件行，实测）、`vector_dir` 本身是个文件 ⇒ preflight 静默跳过。

---

## 一、§四 判据 A1–A8 逐条读数

| # | 判 | 读数 |
|---|---|---|
| **A1** | ✅ | 开工第一个动作后台全量 `python -m pytest -q -n 6`：**`3113 passed, 13 xfailed, 211 warnings in 471.94s (0:07:51)`，退出码 0**。与施工自述 3113 一致；3070（本席上一轮在 `f2a8ccf` 亲测）+ 43 = 3113 算术吻合。启动器差异（施工时 `.pth` 指 `/tmp/ep_f97`、本轮指主树）：两读数恰好一致，未启用「先怀疑启动器」分支。 |
| **A2** | ✅ | **① 旧树**（`git archive f2a8ccf` → `/tmp/ep_f97_old2`，零注册快照）：BLK-A 三值 ⇒ `reading_view_legacy/CONSUME`；BLK-C `schema=[]` ⇒ `TypeError: unhashable type: 'list'`、`b"\xff\xfe\x00"` ⇒ `UnicodeDecodeError`、`backup.json` 为目录 ⇒ `IsADirectoryError`，三者**经 `_write_vector_contract_ledger` 裸冒**（账本写入函数自己 RAISED）；BLK-B `[1,2,3]` ⇒ `AttributeError: 'list' object has no attribute 'get'`，帧 = `pipeline.py:1368` → `legacy.py:178`，**账不存在**；正对照改名 `mystery.json` ⇒ `UnconsumableVectorFile` + 账在盘。**② 新树**：三值 ⇒ `unknown` + reason 点名所声明的值；双命中（三值 × 完整键集）**仍 AMBIGUOUS**；六形态（目录 / 断链 / 符号链环 / fifo / 非法 UTF-8 / `schema=[]`）经 `ledger_for` **零异常、各得具体 reason 的 error 行**；组合入口三毒（非对象 / 非法 JSON / 非法 UTF-8）⇒ 点名 + 账在盘 + `consumed==[]`。**③ 另找未击穿**（我的方向见 §3.5 结论）。 |
| **A3** | ✅ | 43 条逐条点名见 §二。真实入口覆盖：`_build_correction_messages`（R5×3）、真实 `run_correction`（R5×1 + R7×3）、真实 `run_pipeline_artifacts` / `run_pipeline`（R6×7）、spy 顺序锁走真实组合入口（R6×2）。`ledger_for` 直调的 12 条是**两入口共用的账本生产者本体**（preflight 体内调的就是它），名实相符。仅 `test_r7_ledger_writer_itself_never_raises_on_a_hostile_run_dir` 一条 helper 直调 `_write_vector_contract_ledger`，但它断言的正是该 helper 自己的 never-raise 契约（单元锁），且同名真实入口锁（`test_r7_a_hostile_run_dir_does_not_eat_the_named_refusal`）并存——不是 helper proxy 冒充入口锁的形态。 |
| **A4** | ✅（抽验 + 口径核） | **口径**：43 = 参数化展开后的测试条数（R5 17 + R6 9 + R7 17；测试函数 15 个），与 3113 − 3070 = 43 独立吻合。**抽验 2/9 个变异**（本席自己在被审树上做、锚点唯一性自核、`count==1` 断言式替换、跑完还原核净）：**N2**（摘组合入口 hoist）⇒ `9 failed, 69 passed`，红集 = **R6 全部 9 条**（含 `41a568a` 收紧后的 `directory_named_non_view`——它确实由绿转红，收紧生效的独立重现）；**N7**（把 `_detect_legacy_reading_view` 的未登记否决改回 `"schema" in raw`，即复现第一轮塌法）⇒ `6 failed, 72 passed`，红集 = **3 条新 AMBIGUOUS 守卫 + 3 条旧守卫**（`test_r2_registered…` / `test_b3_double_match…` / `test_b3_ambiguous_file…`），零附带。与施工自述逐条一致。其余 7 次变异未复跑；依据 = 两次抽验完全吻合 + 全量数字恒等 + 43 条断言逐条读过（点名路径锁全部断言「`UNEXPECTED_FAILURE_PREFIX` 不在 reason 里」——兜底网不能替被测机制撑绿的结构是真实在位的）。⚠️ 照 [[neuter-proves-wiring-not-discriminating-power]] 点名：**43/43 的主张范围是「每把锁至少在一个变异下红过」（接线），不是「每把锁对任意输入有分辨力」**——分辨力只在各自锁定的形态类上成立。 |
| **A5** | ✅ | 五条全部独立验证成立，#1/#2 构成对我上轮处方的证伪（我接受）。逐条见 §三。`is_file()` 边界这个修法方向：**接受**——它不是「第四个 except」，是唯一能接住「挂死」这种无异常失败的形态的边界；且一条规则同时覆盖目录 / 断链 / 环 / fifo 四形态。 |
| **A6** | ✅ | 两条自陈弱点均判**登记不阻断**（定性见 §四）：嵌套声明今天语料 **0/371 命中**（本席重数）且属契约数据面的前置；`pipeline.py:528` 结构性在 preflight 之后、门被 43 锁中的真实入口锁守着（门被挪走 ⇒ 锁红，fail-closed 而非静默）。 |
| **A7** | ✅ | `diff --numstat f2a8ccf HEAD` = `pipeline.py 53/5` · `vector_contract.py 165/25` · 测试 `582/0` · 报告 `495/0`，仅 4 文件。N-A 的 `DECLARED_SCHEMA_VALUES` frozenset 段零 diff；N-B 的 `==43`/`==328` 断言零 diff 且实测通过（F97 测试文件 78 条全绿含两条语料断言）；N-C/D/E 对应行为（结构回落 / `out_dir=None` / 大写扩展名）零 diff；`validation_run.py` 零 diff。**`vector_contract.py` 的改动按请求单 §七#2 更正口径计为范围内，不当超范围记。** |
| **A8** | ✅ | 开工前 `/workspaces/EnergyPlus-Agent-dev`；交件前 `/workspaces/EnergyPlus-Agent-dev`（两次读数一致，逐字见 §七）。期间未跑任何 `pip install`。 |

## 二、A3 逐锁点名（43 条按组）

| 组 | 条数 | 入口构成 |
|---|---|---|
| **R5**（BLK-A） | 17 | 7 × `classify_vector_json` 直调（单元：三值 × 残缺键集变体，断言 reason 点名所声明的值 + 无兜底网前缀）· 3 × `_build_correction_messages`（**真实入口**）· 3 × `classify_vector_dir`（门函数本体）· 3 × AMBIGUOUS 守卫（判别器单元，三值全覆盖——N7 的红集主体）· 1 × 真实 `run_correction` + 盘上账本 |
| **R6**（BLK-B） | 9 | 3 × 真实 `run_pipeline_artifacts` 负例（非对象 / 非法 JSON / 非法 UTF-8）· 1 × `run_pipeline` 包装层 · 3 × 文件系统形态走组合入口（目录 / 断链 / 非 view 名目录，断言**拒绝先于 reading report 落盘**）· 2 × 顺序锁走真实组合入口（点名式 spy + **消费者无关式拦 `Path.read_text`**——第四个消费者接上当天即被抓，不需要有人想起来加 spy） |
| **R7**（BLK-C） | 17 | 9 × `ledger_for`（**两入口共用的账本生产者本体**：目录 / 断链 / 环 / 三种非法字节 / 三种非字符串声明，各断言具体 reason + 无兜底网前缀）· 1 × TOCTOU 消失向 · 1 × fifo 不挂死（SIGALRM 围栏）· 1 × 兜底网可达（`RecursionError`，断言**前缀在**）· 2 × 真实 `run_correction` 形态锁 · 1 × 目录经 `run_correction` · 2 × 恶劣 run 目录（1 真实入口 + 1 helper 单元锁，并存） |

## 三、§3.3 五条的独立验证（A5 展开）

| # | 施工方主张 | 本席复跑 | 判 |
|---|---|---|---|
| 1 | `*.json` 名 fifo 使 `read_text` 永久挂死、无 except 能捕 ⇒ 修法必须是 `is_file()` 边界 | **干净子进程**（`subprocess.run` 8 s 超时，进程内无任何信号机制）读无 writer 的 fifo ⇒ **超时**——挂死实锤，非异常。新树真实 `ledger_for` 对 fifo **立即返回** error 行。⚠️ 本席先撞上一个伪影再排除：带 SIGALRM 围栏测 fifo 时，围栏抛的 `TimeoutError` **是 `OSError` 子类**，会被「加长 except 元组」的退化实现意外接住——我第一版探针因此误读「处方版也能过 fifo」；子进程判别后推翻。生产锁 `test_r7_a_fifo…` 因断言 reason 措辞（`"not a readable regular file" in reason`），对「退化成 except 元组」的变异**仍有分辨力**（TimeoutError 的 reason 措辞不同 ⇒ 红） | **成立；`is_file()` 方向接受** |
| 2 | 深嵌套 JSON ⇒ `RecursionError`，不在 `OSError`/`UnicodeDecodeError`/`JSONDecodeError` 内 ⇒ 照处方逐字做仍崩 | 本席在探针内**逐字实现处方版**（捕 `OSError` + `UnicodeDecodeError` + `JSONDecodeError`，无边界无兜底）喂 20 万层 ⇒ **`RecursionError` 原样逃出**；新树真实路径 ⇒ 兜底网行，reason 带前缀且点名 `RecursionError` | **成立；我上轮处方对深嵌套不充分** |
| 3 | v3 catalog（`:1411`）无毒文件也丢账 | 旧树：合法 legacy 视图 + `orthogonal_polygon` ⇒ `WindowResolverInputError: observation_reference_catalog_unavailable`（`window_sources.py:627`，经旧 `pipeline.py:1411`），**账不存在**；新树：同样失败、**账在盘**（帧 = 新 `pipeline.py:1459`，行号偏移 +48 与 diff 量吻合） | **成立**（F-c 破的第三个轴：run 因什么失败） |
| 4 | `_run` 不可写时 F-c 存储失败把 F-b 点名一起毁掉 | 旧树：`_run` 是文件 + 毒文件 ⇒ **`FileExistsError` 直接吃掉点名**；新树：同样布局 ⇒ **`UnconsumableVectorFile` 照常点名**（写账失败记 warning 后分类判决照常落地） | **成立**（第四个轴：账本自身写不进时 F-b 须独立成立） |
| 5 | `:1376` 结构上被 `:1368` 遮蔽、不可能先崩 ⇒ 用顺序锁代替夹具 | 静态核：`compute_reading_report_from_vector_dir`（`execution/evidence_preflight.py:203`，体内 `:229` 处 `for path in sorted(vector_dir.glob("*_view.json")): view = load_reading_view(path)` **无任何 try/except**）与旧 `pipeline.py:1376` 的 glob **逐字同模式、调同一 `load_reading_view`**，且 `:1368` 先行 ⇒ 任何杀死 `:1376` 的载荷必先杀死 `:1368`。**判：诚实替代，不是回避**——顺序断言锁的正是承诺本体（「账先于任何消费者」），比伪造一个走不通的载荷更贴；点名式锁的「只认识三个消费者」短板由消费者无关锁补上，两者并存的设计正确 | **成立** |

## 四、§3.2 两条自陈弱点的定性（A6 展开）

1. **嵌套声明 `{"meta": {"schema": …}}` 仍被当 legacy 消费 —— 登记不阻断。**
   实证：两树同形（本席在旧树 / 新树各测一次，均 `reading_view_legacy/CONSUME`）；**全仓 `0_reading` 语料 371 份中嵌套声明形状命中 0**（顶层无 `schema`、一层子 dict 内有 `schema`——本席独立重数）。定性理由：顶层无 `schema` 键 ⇒ 按「未声明」走结构回落是纪律 #5 的字面语义，不违 F-a；要收紧就得先在契约数据面定义「什么算一次声明」（与 N-A 的 `ContractSpec` 派生是同一张单子）。施工方「producer 哪天把声明包进信封它就是 BLK-A 的孪生」的风险评估正确——**这是下一轮该挂号的债，不是本轮该拦下的错**。
2. **`pipeline.py:528`（`_reading_window_stroke_count`，实测 :521–536，调用点 :797）是同一错误的第二份拷贝 —— 登记不阻断。**
   实证：其 `except (JSONDecodeError, OSError)` 确漏 `UnicodeDecodeError`（`ValueError` 族）、对非对象 JSON 会 `AttributeError`；但它唯一调用点在 `run_correction` 体内 :797，**结构性在 preflight（:765）之后**，两个毒形态都被 preflight 的分类先行点名（R4/R7 的真实 `run_correction` 形态锁全绿 ⇒ `invalid_utf8`/`non_object` 在 :797 之前就死于 `UnconsumableVectorFile`）。「靠另一道门挡着」确是本项目登记过的脆弱形态，但这道门本身被多条真实入口锁守着——**门被挪走 ⇒ 锁红（fail-closed）**；会静默现形的只剩「未来有人新增绕过 preflight 的分支」，与 N-A「加契约会静默漂移」同级。施工方不修的两条理由（复用判别器 = 扩本轮范围；再抄一遍 except 清单 = 本轮已判定为错误方向的修法）均成立。**建议下轮与 N-A 同单处理。**

## 五、§三 六处逐条结论

**3.1 三条阻断 × 三格** — 全过（A2）。①全复现（含 BLK-B 正对照，证明缺口纯由入口顺序）；②全不复现（含双命中 AMBIGUOUS 三值、六种文件系统/编码形态）；③我另找未击穿。
**3.2 施工方自陈两条弱点** — 均登记不阻断（§四）。
**3.3 五条独立验证** — 全部成立（§三）；#1/#2 是对我上轮处方的证伪，本轮正式更正（§更正）。
**3.4 红集对账** — 口径成立（43 = 参数化展开，独立吻合 3113−3070）；两次抽验（N2/N7）红集逐条吻合零附带；5 把假锁的收紧在断言源码中核实（具体 reason + 兜底网前缀不在）；最后一把（`directory_named_non_view`）「变异确实生效」的自证**够硬**——三重独立：`apply.py` 的 `count==1` 锚点断言（打不中即中止）、同一变异下同函数另 2 参数红（函数确实跑到了）、以及本席 N2 抽验的独立重现（9 failed 里它在场）。⚠️ 分辨力主张的范围按 A4 的点名收窄。
**3.5 独立找缝（换方向）** — 我的方向与施工方（文件系统形态 / 编码 / 声明值变体 / 入口顺序 / 递归深度）错开：**(a) 时间窗**：preflight 写账之后、首个消费者之前，外部写入 `late_view.json`（匹配消费者 glob）⇒ **实测 `AttributeError` @ 新 `pipeline.py:1416` + 账在盘但缺该文件行**（F-c 对它不成立）——新缝，不阻断（触发前提 = 并发外部写，超出「run 的输入」承诺面；非 view 名的后到文件会被 `run_correction` 的第二次 preflight 兜住，实测 `late.json` 进账且点名——施工方保留第二次 preflight 的决定在这里意外兑现了防御价值）；**(b) 环境级目录形态**：`vector_dir` 本身是文件 ⇒ `discover_vector_files` 抛 `FileNotFoundError` 被两处 except 捕获 ⇒ preflight **静默跳过**（不写账不点名），下游消费者自己崩（响亮、无账无名）——与 N-C 同族（没有目录就没有账本位），不阻断；**(c) fifo 判别的围栏伪影**（SIGALRM `TimeoutError` ⊂ `OSError`）——方法论发现，见 §三#1；**(d) 语料嵌套声明 0/371**（支撑 3.2#1 的定性）。**未找到阻断级新缝。**
**3.6 N-A…N-E 未动 + 兼容面** — 超范围零、`==43`/`==328` 原值通过（A7）。

## 六、Findings

### 阻断（0）

无。

### 不阻断（5）

1. **N-G（新，本席实测）**｜**preflight 与首个消费者之间的时间窗**：账落盘后、`compute_reading_report` 调用前，目录里新出现 `*_view.json` 名文件 ⇒ 消费者裸崩（`AttributeError` @ `pipeline.py:1416`）且账不含该文件。单线程管线不触发；**根治方向正是 BLK-B 返工要求的另一半「让 reading-report / catalog 消费复用同一次分类结果」**，建议与 N-A 同单排队。
2. **N-H（新，本席实测）**｜`vector_dir` 本身是文件 ⇒ preflight 的 `except FileNotFoundError` 把它当「没有 `*.json`」静默放过，run 死在下游消费者（响亮、无账、无点名）。环境级畸形，与 N-C 同族；若要覆盖，在 preflight 对 `vector_dir` 非目录的形态显式记录一行即可。
3. **N-A 维持**｜`DECLARED_SCHEMA_VALUES` 第二处手写清单未做机械对账（本轮明令不做）。施工方报告的「唯一产生静默消费的漂移方向已被后置规则堵死、剩余方向只丢歧义报告」读数本轮未重验（monkeypatch 演示），按线索采信并维持登记。
4. **N-B 维持**｜`==43`/`==328` 语料快照常量未动、原值通过；本批第 ③ 步产物入库前须先改掉（派工单已挂硬闸）。
5. **方法论备忘**｜fifo 类「挂死」形态的测试围栏本身有伪影面：SIGALRM 抛的 `TimeoutError` 是 `OSError` 子类，会被「加长 except 元组」的退化实现意外接住——**围栏测试的通过判据必须落在 reason 措辞上**（现有锁恰是这么写的，故仍有分辨力）；另施工方自记的两条残余风险（兜底网行可能被读成「文件坏了」而非「代码坏了」；消费者无关锁依赖 `load_reading_view` 保持函数内 import——挪到模块级会让点名式锁变红而非静默，fail-closed）本席核过代码，自评准确。

## 七、orchestrator 题面写错的地方

本轮**未发现承重级题面错，零次触发停下上报**。外围三条记录：

1. **请求单 §3.3 标题写「四条」、表列 5 行**——#5（`:1376` 遮蔽）不是「处方没覆盖的东西」而是载荷构造的替代，归两类。措辞歧义未误导复核（本席按 5 条逐一验）。
2. **派工单「不要动 `src/agent/pipeline` 以外的模块」与 BLK-A/BLK-C 逐字要求冲突**——orchestrator 已在请求单 §七#2 自认并更正（`vector_contract.py` 在范围内）；本席按更正口径执行，A7 未记超范围。**连带一条**：派工单那句「裸跑会静默串到主树」在施工当时方向是反的（`.pth` 那时指 `/tmp/ep_f97`，主树裸跑才会串进 worktree）——施工方 §七#7 已观察并留证，请求单 §〇 只记了事故未记这句方向反了，补记。
3. **§七#3「基线 3070 未重跑、替代够不够」——判：够**。3070 是本席上一轮在 `f2a8ccf` 上的亲测读数（非施工自述）；算术恒等 3070+42=3112、3070+43=3113 与三次干净树全量（359.99 s / 357.39 s / 361.12 s）自洽；本席本轮独立实测 3113 passed exit 0；两次变异抽验红集吻合 ⇒ 其跑测记录可信。**§七#5 启动器差异**：两读数一致，未启用怀疑分支（留档：`.pth` 现已还原主树，17:18 mtime）。

## 八、⭐ 本席上一轮的更正（触发器 #5，直说）

1. **BLK-C 的处方不完整，两处被施工方证伪、本席独立复现确认**：(a) fifo 是**挂死不是异常**，「捕 `OSError` 与 `UnicodeDecodeError`」接不住它——干净子进程 8 s 超时实锤；(b) 深嵌套 `RecursionError` 不在处方枚举内，照处方逐字实现仍崩。**正确形态是「边界（`is_file`）+ 命名异常路径 + 兜底网」三层，异常枚举永远补不完**（[[lexical-guard-cannot-be-completed]] 的异常面孪生）。施工方的修法方向本席全盘接受。
2. **病根句不完整**：「所有入口 × 所有形态」漏了两个轴——**那次 run 因什么原因失败**（v3 catalog 无毒文件也无账，§三#3）与**账本自己写不进时 F-b 须独立成立**（§三#4）。施工方给的四轴扩写更准，建议下次派工单直接采用其原文：
   > F-b 的点名与 F-c 的留账，要在所有会碰 `0_reading` 的入口上、对所有输入形态、不论那次 run 最终因什么原因失败、且在账本自己写不进去的时候，都各自独立成立。
3. **范围口径裁定（施工方 §六#8 请裁）**：「所有会碰 `0_reading` 的入口」按病根句字面会把 `execution/validation_run.py:253,281,315`（validate_case 的 0_reading 自检）也包进来；本席裁定**它不在 F-97 承诺面内**——它是校验器不是 1_correction 的消费者，不把内容喂进 correction prompt；F-97 的「入口」= 不经判别器就把 `0_reading` 内容交给 1_correction 消费的调用点。维持登记，不扩本轮范围。

## 九、本席跑的全量 summary 行（逐字）

- **干净树（开工第一个动作，后台，`python -m pytest -q -n 6`）**：`3113 passed, 13 xfailed, 211 warnings in 471.94s (0:07:51)`（退出码 0）
- **变异抽验 N2**（摘 `run_pipeline_artifacts` 的 preflight hoist；`tests/test_f97_vector_contract.py` 子集）：`9 failed, 69 passed in 6.59s`——红集 = R6 全部 9 条，零附带
- **变异抽验 N7**（`_detect_legacy_reading_view` 的未登记否决改回 `"schema" in raw`；同子集）：`6 failed, 72 passed in 5.81s`——红集 = 3 新 + 3 旧 AMBIGUOUS 守卫，零附带
- F97 测试文件单独跑：`78 passed in 5.93s`（= 旧 35 + 新 43，含 `==43`/`==328` 两条语料断言）
- 两次变异均在跑完后 `git checkout --` 还原并核净（`status --porcelain` 只剩 5 份 untracked md）；跑测期间未动被审对象。

## 十、`.pth` 哨兵两次读数（逐字）

- **开工前**：`/workspaces/EnergyPlus-Agent-dev`
- **交件前**：`/workspaces/EnergyPlus-Agent-dev`（mtime `2026-08-26 17:18`，本轮会话期间未被改动）
- 两次一致 ⇒ 本轮全部读数有效；期间未运行任何 `pip install`。

## 十一、交件时工作树状态

被审源码与测试相对 `c3fc3fd` **零 diff**（两次变异均已还原并逐次核验）。`git status --porcelain`：

```text
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework2_crossreview_glm.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework2_dispatch.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_glm.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework2_glm_verdict.md
```

= 请求单预告的 5 项 + 本裁决文件，共 6 项。探针与方法留存于仓库外 `/tmp/f97_glm2/`
（`p1_old.py` 旧树复现 · `p2_new.py` 新树② + §3.3 + 独立找缝 · `p3_followup.py` fifo 子进程判别 + TOCTOU 变体 ·
`p4_old_contrasts.py` 旧树对照），旧树快照 `/tmp/ep_f97_old2`（`git archive f2a8ccf`，零注册、未挂 worktree）——均不污染交件状态。
