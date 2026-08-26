> ⛔ **orchestrator 落库说明（2026-08-27）**：以下为 GLM 家族**写在 `/tmp/ep_f97` 里的原件逐字**，未改一字。
> **总判 REWORK / 3 阻断（BLK-A/B/C）/ 6 不阻断（N-A…N-F）。**
> ⭐ **本单是第四次派出**：前两次 GPT 因我的题面错停下上报（第 37、38 次）；第三次 GPT 做完实体复核
> 却在交件时被自家 provider 安全过滤拦掉 ⇒ 改派 GLM。**GPT 那份探针文件作为「线索非证据」交给了 GLM，
> 它逐条复跑，其中 2 条升成了阻断（BLK-A / BLK-C），并自加了第三个同族形态（`*.json` 是个目录）。**
> ⭐⭐ **三条阻断全部出自请求单 §3.1 判据 ③「修法只堵住被举的那一种输入，换同形输入又走通」** ——
> 那是本轮唯一新加的一条判据。
> ⭐ **GPT 上一轮那三条阻断，GLM 复核后判定无一判错。**
> ✅ **本单题面零承重错、零停下上报**（38 次连败后的第一份干净派工单）；只有一处「病根概括过窄」，
> GLM 给了更好的写法，见 §六#3 —— 已采纳进下一轮返工单。

---

# 跨家族复核裁决 · F-97 契约判别器【返工轮】（GLM 家族）

- **日期**：2026-08-27　**复核席位**：**GLM 家族**（`glm-5.3`）
- **施工席位**：Claude 家族（返工轮）　**被审 commit**：`f2a8ccf`（worktree `/tmp/ep_f97`，开工自检 HEAD 对上）
- **请求单** → [`../request/2026-08-27_f97_rework_crossreview_glm.md`](../request/2026-08-27_f97_rework_crossreview_glm.md)
- **上一轮裁决（GPT sol，REWORK / B-01 B-02 B-03）** → [`2026-08-27_f97_contract_discriminator_gpt_verdict.md`](2026-08-27_f97_contract_discriminator_gpt_verdict.md)

## 总判：**REWORK**（3 条阻断 · 6 条不阻断）

返工是真修：GPT 举的三条夹具在 `8fda4c1` 上我全部独立复现（旧树快照探针 7/7，B-03 连
`AttributeError: 'list' object has no attribute 'get'` 的原文都一致），在 `f2a8ccf` 上**各自的原夹具**全部不再复现，
三次 neuter 各恰好红对应锁、零附带，全量 3070 绿。**GPT 三条阻断没有一条判错。**

但按本单 A2③ 的标准（**换一种同形输入照样走通 ⇒ 不通过**），三条里有两条只堵住了被点名的那一种输入，另有一条同族的账前崩溃被 GPT 的探针点名、被我证实并扩充：

1. **BLK-A（B-01 只修了「未登记」这半）**：声明**已登记** schema 值、但缺该契约必需键（= GPT 要求原文里的「**畸形**显式 schema」）+ legacy `strokes` ⇒ 仍塌缩为 `reading_view_legacy` 并**被静默消费**。三个已登记值（plan_v2 / plan_v0 / elevation_v0）**全部实测同塌缩**。违反 GPT 返工要求的"畸形"半，也违反本模块自己的纪律 #5（"Structural fallback is only for the **undeclared**"）。
2. **BLK-B（B-03 在生产组合入口原样保留）**：`run_pipeline(_artifacts)` 在调 `run_correction` **之前**就自己解析 `*_view.json`（`pipeline.py:1368` reading report → `load_reading_view`、`:1376-1379` 再解析一遍、v3 还有 `:1411` 的 catalog）。同一夹具在 `f2a8ccf` 的 `run_pipeline` 上仍死 `AttributeError: 'list' object has no attribute 'get'`（`reading/legacy.py:108 _is_legacy`），**无点名异常、无 ledger**——与 GPT B-03 记录的病灶逐字同形，只是位置从 `run_correction` 体内挪到它上游约 40 行。旧树同样崩 ⇒ **未覆盖，不是回归**。`_preflight_vector_contracts` docstring 声称 "Runs before ANY consumer that parses `*_view.json`"，在组合入口层面这句不成立。
3. **BLK-C（F-c 的「ledger 永不抛」前提不成立）**：`schema=[]/{}` ⇒ `TypeError: unhashable type`；非法 UTF-8 ⇒ `UnicodeDecodeError`；`0_reading/` 里名为 `*.json` 的**目录** ⇒ `IsADirectoryError`——三个形态**全部崩在 ledger 落盘之前**（我复跑了前两个并加测了第三个）：无账、无名。`ledger_for` 的 "never raises" 与 `pipeline.py` 注释 "`_write_vector_contract_ledger` never raises" 均为假。B-03 的病换了三个入口回来。

三条同指向一句话：**F-97 的承诺是「点名 + 留账」，而现在的兑现只在「文件恰好能被 `json.loads` 读出、入口恰好是 `run_correction`」两个前提下成立。**

（以下全部读数来自本席自己的探针与跑测；施工自述仅作线索。探针与变异均已还原，方法与逐条读数见文内。）

---

## 一、§四 判据 A1–A8 逐条读数

| # | 判 | 读数 |
|---|---|---|
| **A1** | ✅ | 开工第一个动作后台全量 `python -m pytest -q -n 6`：**`3070 passed, 13 xfailed, 211 warnings in 396.53s (0:06:36)`，退出码 0**。无假红、无需重跑；与施工自述的 3070 一致（3035 基线 + 35 条 F97 测试，收集数 35 已核）。 |
| **A2** | ❌ | 双向都做了。**旧树 `8fda4c1`**（`git archive` 零注册快照 + 我的独立夹具，探针 7/7）：B-01（未登记值+strokes ⇒ `reading_view_legacy/CONSUME`，经 `_build` 原文进提示词）、B-02（畸形边车 ⇒ `stage_check_report/EXCLUDE`）、B-03（`[1,2,3]` 走真实 `run_correction` ⇒ `AttributeError` 且 ledger 不存在）**全部复现**。**新树 `f2a8ccf`**：三条**各自原夹具**全部不再复现（判别器 + `_build_correction_messages` + 真实 `run_correction` + 盘上 ledger 全过）。但 **A2③ 不通过 ×2**：B-01 的同形变体（已登记值+畸形+legacy 结构）仍被静默消费 ⇒ BLK-A；B-03 的同形输入走生产组合入口 `run_pipeline` 仍崩在账前 ⇒ BLK-B。B-02 双向全过，我另造三种变体（`stage` 类型错 / `results` 内元素错 / 多余顶层键）也全判 unknown 响亮红。 |
| **A3** | ✅（含缺口点名） | 12 条新锁逐条点名见 §二。没有任何一条是上轮 GPT 批的「helper proxy 冒充生产入口锁」形态；R1#2 / R3#2 走 `_build_correction_messages`（生产提示词组装本体），R4 三条走真实 `run_correction`（含 `out_dir`、断言盘上 ledger）。**缺口：入口层级止于 `run_correction` / `_build_correction_messages`，组合入口 `run_pipeline` 零锁——BLK-B 恰在那个层级。** |
| **A4** | ✅（含分辨力局限点名） | 三次 neuter、各跑全量（`-n 6`），每次还原并核净树：摘 B-01 否决 ⇒ `3 failed, 3067 passed, 13 xfailed`（红恰 R1 三条）；B-02 退回键名 ⇒ `2 failed, 3068 passed, 13 xfailed`（红恰 R3 两条畸形锁，**43 边车兼容锁仍绿** ⇒ 它锁的是兼容不是修法）；B-03 preflight 挪回 evidence 之后 ⇒ `3 failed, 3067 passed, 13 xfailed`（红恰 R4 三条）。三次 `passed+failed` 均 = 3070，零附带，与施工自述的红集 3/2/3 全部一致。⚠️ 按 [[neuter-proves-wiring-not-discriminating-power]] 点名：变红只证接线——**R1 锁对 BLK-A 的输入零分辨力（该输入没有任何锁覆盖），R4 锁对 BLK-B/C 的形态零分辨力（组合入口 / 非法字节 / 目录形态下全部仍绿）**。返工补修法时须连同这些形态的锁一起补。 |
| **A5** | ✅ | 自写脚本独立重数（不复用施工测试）：`0_reading` 目录 **69** 个、根部直连 `*.json` 者 **56** 个、共 **371** 份；判 `stage_check_report` **43**、`reading_view_legacy` **328**、unknown **0**；提示词字节不变目录 **49**、改变 **7**、整目录响亮失败 **0**；被移除的 `*_view.json` **0**。**170,455 B 复现到字节——口径 = 提示词块字节**（`\n[reading vector] {name}:\n\`\`\`json\n{strip 后内容}\n\`\`\`\n` 的完整块）；若按原始文件字节数则为 **168,149**。两个口径都对得上账，施工/GPT 用的是前者（题面第一次没写清口径，见 §六#6）。 |
| **A6** | ❌ | 独立找缝，**方向换到入口拓扑与账本健壮性**（GPT 探针打的是声明值/编码/清单方向，不复用）：命中 **BLK-B**（`run_pipeline` 上游解析，含正对照：同一毒文件改名非 `_view` 名 ⇒ 正确点名+记账，证明缺口纯由入口顺序造成）与 **BLK-C**（含我自加的 `*.json` 目录形态）；另两个不阻断形态：`{"strokes": []}` 零内容无声明文件被消费（N-D）、`out_dir=None` 时失败 run 无账（N-C）。**BLK-A 属静默消费形态，同时命中本条「找到任何一条能被静默消费的真实形态 ⇒ 阻断」。** |
| **A7** | ✅ | §五 5 条全部自己复跑（探针 22/22 绿；首跑 1 红是我探针自己的 ledger 路径笔误，修正后过）。逐条判定见 §三；其中 lead 2 ⇒ BLK-A、lead 3 ⇒ BLK-C 成立且阻断级，已并入 Findings。**没有任何一条「根本不成立」。** |
| **A8** | ✅ | N-01（as-drawn toolbox 无行为测试）未变——`tests/` 零引用（仅 `__pycache__` 残留 GPT 上轮探针的 pyc，源已删、gitignored，无害）。N-02（as-drawn checks 报告未登记）未变——`experiments/out` 下 `as_drawn_plan_v2` 声明值 **77** 份（= 32 读图产物 + 45 checks 报告）、无一在 `0_reading`；若真共置：checks 形状（`schema`+`mutation`/`role_assignment`/`checks`，无三键无 `strokes`）判 **unknown 响亮红**，fail-closed 未破。N-03（语料口径限本 checkout）未变。三条均未恶化。 |

## 二、A3 逐锁点名（12 条新锁走生产入口还是 helper）

| 锁 | 入口 | 判 |
|---|---|---|
| `r1_unregistered…is_unknown_not_legacy` | `classify_vector_json` 直调 | 单元锁（名实相符） |
| `r1_…fails_loudly_through_the_real_entry` | `_build_correction_messages` | **真实入口**（提示词组装本体） |
| `r1_…never_reaches_the_prompt` | `classify_vector_dir` 直调 | 门函数本体（两处入口共用的同一函数，非绕道 helper） |
| `r2_registered…still_ambiguous` / `r2_undeclared…recognized` | 判别器直调 | 单元回归锁 |
| `r3_malformed…unknown_not_excluded` | 判别器直调（前置断言 CheckReport 确实拒收） | 单元锁 |
| `r3_malformed…through_the_real_entry` | `_build_correction_messages` | **真实入口** |
| `r3_every_real_sidecar…(==43)` / `r3_all_real_legacy…(==328)` | 语料 | 兼容面锁（未冒充入口锁） |
| `r4_real_run_correction…[non_object / invalid_json]` | **真实 `run_correction`**（断言盘上 ledger） | **真实入口** |
| `r4_ledger_precedes_the_reading_evidence_preflight` | **真实 `run_correction`** | **真实入口（顺序锁）** |

上轮被 GPT 批的两条 helper 直调锁（`test_b3_ledger_is_written_into_the_run_meta_dir` / `…_even_when_classification_fails`）仍在文件里，但它们本来就是单元锁，返工没有拿它们冒充入口锁。**缺口＝零条锁走 `run_pipeline(_artifacts)`。**

## 三、§五 5 条线索逐条我自己的判定

| # | GPT 探针主张 | 我的复跑 | 判定 |
|---|---|---|---|
| 1 | 三夹具已在真实入口被拦、点名、记账 | 三条全过（判别器 + `_build` + 真实 `run_correction` + ledger 在盘、`consumed==[]`） | **成立**；但「真实入口」只覆盖到 `run_correction`——组合入口不成立（= BLK-B） |
| 2 ⭐ | 顶层声明 as-drawn schema、只带 legacy `strokes` ⇒ 仍判 `reading_view_legacy` 并被消费 | `classify_vector_json({"schema": as_drawn_v2.SCHEMA, "strokes":[…]})` ⇒ `reading_view_legacy/CONSUME`；经 `_build_correction_messages` 原文进提示词。**另测 v0 / elevation_v0 两个已登记值同样塌缩（清树实测）** | **成立 ⇒ 阻断（BLK-A）** |
| 3 ⭐⭐ | `schema=[]/{}`、非法 UTF-8 崩在 ledger 之前（与 B-03 同形） | `TypeError: unhashable type` / `UnicodeDecodeError`，ledger 文件不存在 | **成立 ⇒ 阻断（BLK-C）**；我加第三个同族形态：`0_reading/backup.json` 是**目录** ⇒ `IsADirectoryError` 同样崩在账前 |
| 4 | 空文件 / BOM ⇒ 点名且记账（好消息） | `b""` 与 BOM 两条参数化均 `UnconsumableVectorFile` 点名 `1f_view.json` + ledger 在盘 | **成立，非缺陷**（`json.loads` 对两者抛 `JSONDecodeError`，已被 `_classify_rows` 捕获成账行） |
| 5 | `MYSTERY.JSON`（大写）与子目录 json 不进 ledger 清单 | ledger `files` 恰为 `["1f_view.json"]` | **成立，判不阻断**：同一个 `glob("*.json")` 也是**粘贴路径**的选择器 ⇒ 这些文件同样不会被粘进提示词（F-a/F-b 未破）；受损的只是 ledger 作为「目录清单」的完备性（N-E） |

## 四、§三 六处逐条结论

**3.1 三条阻断双向验证** — 见 A2。B-01：旧 ✓ / 新（原夹具）✓ / **同形 ✗**（BLK-A）；B-02：旧 ✓ / 新 ✓ / 同形 ✓（含我另造三种变体）；B-03：旧 ✓ / 新（`run_correction` 内）✓ / **组合入口同形 ✗**（BLK-B）。GPT 三条无一判错。

**3.2 `DECLARED_SCHEMA_VALUES` 第二处手写清单** — **没有机械对账**：`CONTRACTS` 的 detect 是闭包、schema 值不在 `ContractSpec` 数据面上，无法派生；全仓（含测试）无一处引用该集合做等价锁（已验证——测试文件零提及）。**今天不会错配**（探针证三值 ↔ 三契约一一对应、逐一分类到各自契约）。**加契约时会静默**，两个漂移方向都实测演示过（monkeypatch，不动源码）：只加 spec 不进集合 ⇒ 原 AMBIGUOUS 文件**静默塌缩成单判**（丢 #4 纪律）；只进集合不加 spec ⇒ **B-01 经漂移重开**（声明了已登记值 + `strokes` ⇒ 照样被消费）。**判不阻断**（今天零真实输入命中，属工程债），但这是「第二个定义」病的第三次现形，建议下轮给 `ContractSpec` 加 `declared_schema_value` 字段从源头派生。

**3.3 两处各分类一遍** — **构造不出能让两处给出不同结论的静态输入**，凭据 = 两处调的是**同一个纯函数**：`pipeline.py` `_preflight_vector_contracts` 内（:694）与 `_build_correction_messages` 内（:427-429）都走 `classify_vector_dir(vector_dir, discover_vector_files(vector_dir))`，读同一目录、无隐藏状态；5 类目录（纯 legacy / +边车 / unknown / ambiguous / 未登记）实测两处判决一致。分歧只能来自 run 中途目录内容变化（TOCTOU）：彼时 `_build` 自己的分类仍是门（照样响亮），但盘上 ledger 停在 preflight 快照、新 offender 不入账。维持两处有理由（B-03 账先行 + 提示词组装自持门），风险是未来只改一处口径——施工自陈与此一致。

**3.4 兼容面独立重数** — 全数对上（A5），含 170,455 的口径澄清。**`==43`/`==328` 语料快照常量判不阻断但记 N-B**：本批第③步「产出新方案产物」一落地、任何新 `0_reading/*.json` 入库都会让它们红——合法增长被当失败，诱发后来者机械放宽；且语料根 `Path(".")` 依赖 cwd。建议改不变量断言（unknown==0、被移除 `*_view.json`==0、每份被判边车可由 `CheckReport` 解析）替代计数快照。

**3.5 独立主动找缝（换方向）** — 见 A6。命中：`run_pipeline` 上游解析（BLK-B）、账本写入自身的三个崩溃面（BLK-C）、`out_dir=None` 无账（N-C）、`{"strokes":[]}` 被消费（N-D）；工具性演示：双清单漂移两方向（§3.2）。方向与 §五（声明值/编码/清单）不重叠。

**3.6 信任根回溯生产者代码** — **本席已核，代码侧成立**（施工自陈的「只验了产物侧」缺口由此补上）：判别器 import 的 `CheckReport` 与生产者 `validator/checks/reading.py:124 check_reading_view(...) -> CheckReport` 是**同一个类**；写盘 `validation_run.py:653 _write` ⇒ `rep.model_dump_json(indent=2)`，`stage`（必填）、`report_schema_version`、`results`（default_factory）**恒在**；且 `checks/schema.py:345 ConfigDict(extra="forbid")` ⇒ 判别器「三键显式 + 类型解析」与生产者**双向镜像**（缺键 ⇒ 三键约束拦；多键 ⇒ forbid 拦；类型错 ⇒ 校验拦）。生产者不可能写出判别器认不出的边车，反之亦然。

## 五、Findings

### 阻断（3）

#### BLK-A｜已登记值的「畸形声明」仍回落 legacy 并被静默消费（B-01 只修了「未登记」这半）
- **证据**：`{"schema": <任一已登记值>, "strokes": [合法 stroke]}`（缺该契约必需键）⇒ `reading_view_legacy / CONSUME`；`as_drawn_plan_v2`（经 `_build` 原文进提示词）与 `as_drawn_plan_v0` / `as_drawn_elevation_v0`（判别器直测）三值全测。
- **为何阻断**：GPT B-01 返工要求原文 =「**未登记/畸形**显式 schema + legacy 结构必须判 unknown」——"畸形"半没交付；也违反本模块纪律 #5（结构回落只给**没声明过**的文件）。A2③「修法只堵住被举的那一种输入」的典型。
- **返工要求（行为级）**：声明过 `schema` 而该声明**不匹配任何已登记契约**的文件，永远不得被解析为 legacy CONSUME（判 unknown）；「已登记声明 + legacy 结构**双命中** ⇒ AMBIGUOUS」的现行为**保留**（R2 守的就是它）。实现上可在 `classify_vector_json` 加后置规则（唯一命中为 legacy 且 `"schema" in raw` ⇒ 改判 unknown 并说明原因），不必把双命中也否决掉。补一条 registered-but-malformed 的真实入口锁（R1 组同款三件套）。

#### BLK-B｜`run_pipeline` 在分类/ledger 之前自己解析 `*_view.json`（B-03 在组合入口原样保留）
- **证据**：`run_pipeline_artifacts` 于 `pipeline.py:1368`（`compute_reading_report_from_vector_dir` → `load_reading_view` 逐个解析 `*_view.json`）、`:1376-1379`（再解析一遍）、v3 `:1411`（catalog）全部先于 `:1414` 的 `run_correction`。夹具 `1f_view.json = [1,2,3]` 在 `f2a8ccf` ⇒ `AttributeError: 'list' object has no attribute 'get'`（`reading/legacy.py:108`）、ledger 不存在；非法 JSON 同形。**正对照**：同一毒文件改名 `mystery.json` 走 `run_pipeline` ⇒ 正确 `UnconsumableVectorFile` + ledger 在盘——缺口纯由入口顺序造成。`8fda4c1` 同样崩 ⇒ 未覆盖、非回归。
- **为何阻断**：`_preflight_vector_contracts` 的 docstring "Runs before ANY consumer that parses `*_view.json`" 在组合入口层面为假；F-b（点名失败）与 F-c（失败 run 必留账）在**生产组合入口**双双落空，且与 GPT B-03 记录的病灶**逐字同形**。
- **返工要求**：把 `_preflight_vector_contracts(vector_dir, out_dir)` 提到 `run_pipeline_artifacts` 中**任何 `*_view.json` 消费之前**（至少先于 :1368），或让 reading-report / catalog 消费复用同一次分类结果；补一条走 `run_pipeline(_artifacts)` 的真实入口负例（非对象 + 非法 JSON 两条）。

#### BLK-C｜「ledger 永不抛」前提不成立：至少三个输入崩在账落盘之前（B-03 同族）
- **证据**（三形态全实测，ledger 文件均不存在、异常均非点名异常）：
  1. `{"schema": [] /* 或 {} */, "strokes": […]}` ⇒ `raw.get("schema") not in DECLARED_SCHEMA_VALUES` 对 frozenset 判成员 ⇒ `TypeError: unhashable type`；
  2. 非法 UTF-8（`b"\xff\xfe\x00"`）⇒ `read_text` 抛 `UnicodeDecodeError`，`_classify_rows` 只捕 `json.JSONDecodeError`；
  3. `0_reading/backup.json` 是**目录** ⇒ glob 收进目录名、`read_text` 抛 `IsADirectoryError`。
  三者均发生在 `_write_vector_contract_ledger` 内部 ⇒ `ledger_for` 的 "never raises" 与 `pipeline.py:731-732` 注释 "`_write_vector_contract_ledger` never raises" 为假；`run_correction` 的 F-c 兑现在这些输入上与返工前一样不存在。
- **为何阻断**：这三个不是对抗性输入，是普通文件系统/编码现实（截断的 UTF-16 产物、错位的 `mkdir`）。F-c 的承诺原文 =「**包括那次 run 最终失败**的情形」都要有账。
- **返工要求**：`_classify_rows` 的异常面收宽为「读不出/解不开 ⇒ 账上一行 error + offender」：捕 `OSError`（含 `IsADirectoryError`）与 `UnicodeDecodeError`；`_declares_unregistered_schema` 先 `isinstance(raw.get("schema"), str)` 再判成员（非字符串声明值一律按畸形声明处理 ⇒ 不回落 legacy）。补三条对应真实入口锁。

### 不阻断（6）

1. **N-A**｜`DECLARED_SCHEMA_VALUES` 无机械对账的第二处清单（§3.2；今天一致、加契约会静默漂移、双方向实测；建议从 `ContractSpec` 派生或加元测试）。
2. **N-B**｜`==43`/`==328` 语料快照常量（§3.4；本批第③步新产物一入库即红、诱发机械放宽；`Path(".")` 依赖 cwd；建议改不变量断言）。
3. **N-C**｜F-c 的账以 `out_dir` 非空为前提（`run_correction`/`run_pipeline` 不带 `out_dir` 的合法调用失败时无处留账；没有 run 目录就没有账本位，可接受，但应写进文档）。
4. **N-D**｜`{"strokes": []}` 零内容无声明文件仍判 legacy 消费（结构回落的字面定义所容；要更严需最小键集/非空约束，属设计裁量）。
5. **N-E**｜ledger 清单对大写扩展名/子目录 JSON 不可见（= lead 5；同一 glob 也是粘贴选择器 ⇒ 不发生静默消费，受损的只是清单完备性）。
6. **N-F**｜A4 分辨力局限（neuter 变红只证接线：R1 锁对 BLK-A 输入、R4 锁对 BLK-B/C 形态零分辨力——这些形态下现有锁全绿；返工须连同新形态的锁一起补）。

（GPT 上轮 N-01/N-02/N-03 现状复查均未恶化，见 A8。）

## 六、orchestrator 题面写错的地方

本轮**未发现承重级题面错，零次触发停下上报**。逐项核过：

1. **§〇 全部 git 读数逐字复测一致**（HEAD、两段 `--numstat`、3 提交链、`ed0ba09` 为 `534b5a2` 祖先、开工时恰 2 份 untracked）。「本单全貌（代码面）」标注了口径：`ed0ba09→f2a8ccf` 实际 8 项（4 md + 4 代码/配置），单子列了 4 项代码项——**口径已声明，不记错**。
2. **§七#2 自认「返工要求列压缩过」**：与 GPT 原文核对**无出入**——关键的「畸形」二字没被压掉；那半是被施工漏掉的，不是被题面吃掉的。
3. **§七#3「B-03 病根 = helper proxy 冒充生产入口锁」**：作为 GPT 原话的归纳不算错，但**作为病根概括不完整**——本轮实测显示更深的根是「账先行的承诺既不覆盖组合入口（BLK-B）、也不抗崩（BLK-C）」，这两条与 helper proxy 无关（锁全走真实入口也拦不住）。下次病根句建议直接写成「F-c 的『失败必留账』要在**所有**会碰 `0_reading` 的入口与所有输入形态下成立」。
4. **§七#4 自认「§五表可能读歪」**：逐条与我复跑对上，**无读歪**。唯一可点名处：lead 1 的措辞「已在**真实入口**被拦」容易读成覆盖 `run_pipeline`——GPT 探针断言走的确实只是 `_build`/`run_correction`，表没读歪，是「真实入口」一词本身有入口层级歧义（正是 BLK-B 藏身之处）。
5. **§七#5「未核 ledger 是否真排在 preflight 前」**：`run_correction` 体内 = 真（我核了）；`run_pipeline` 层面 = 假（BLK-B）。
6. **§3.4 的 170,455 题面没错但口径第一次被写清**：= 提示词块字节（含包装、strip 后内容）；原始文件字节数是 168,149。A2（GPT 上轮）与施工自述同用前一口径，本单沿用；建议以后此类数字注明口径。

## 七、本席跑的全量 summary 行（逐字）

- **干净树（开工第一个动作，后台）**：`3070 passed, 13 xfailed, 211 warnings in 396.53s (0:06:36)`（退出码 0）
- **neuter-1（摘 B-01 未登记否决）**：`3 failed, 3067 passed, 13 xfailed, 211 warnings in 315.33s (0:05:15)`——红恰 R1 三条，零附带
- **neuter-2（B-02 类型校验退回键名）**：`2 failed, 3068 passed, 13 xfailed, 211 warnings in 307.54s (0:05:07)`——红恰 R3 两条畸形锁，零附带；43 边车兼容锁仍绿
- **neuter-3（B-03 preflight 挪回 evidence 之后）**：`3 failed, 3067 passed, 13 xfailed, 211 warnings in 309.73s (0:05:09)`——红恰 R4 三条（两条参数化 + 顺序锁），零附带
- 三次变异均在全量结束后 `git checkout --` 还原并核净（`status --porcelain` 只剩 2 份 untracked 请求单）；跑测期间未动树。

## 八、交件时工作树状态

被审源码与测试相对 `f2a8ccf` **零 diff**（三次 neuter 均已还原并逐次核验）。`git status --porcelain` 应为：

```text
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_glm.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md
```

即 §〇 预告的 2 项 + 本裁决文件，共 3 项。探针与方法留存：`/tmp/f97_glm_probe/`（`test_old_probe.py` 旧树复现 7 条 · `test_new_probe.py` 新树 22 条 · `recount.py` 兼容面重数），旧树快照 `/tmp/ep_f97_old`（`git archive 8fda4c1`，零注册、未挂 worktree）——均在仓库外，不污染交件状态。
