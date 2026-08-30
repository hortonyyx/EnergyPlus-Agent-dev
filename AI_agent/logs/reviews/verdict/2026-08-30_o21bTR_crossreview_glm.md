# 跨家族裁决书 · ②-1b-T-R（case 准入门返工：R1 两层门 + R2 固化 + R3 清扫 + R4 改口径）

- **日期**：2026-08-30 · **审阅方**：GLM 家族（跨家族审，F-146 发现方续审）·
  **请求书**：[`../request/2026-08-30_o21bTR_crossreview_glm.md`](../request/2026-08-30_o21bTR_crossreview_glm.md)
- **送审对象**：`93bdc33`（主）+ `e52d1ad`（补记）· **基线 `fdb0185`** ·
  一律以 `git diff fdb0185..e52d1ad` 为准（4 文件 + 执行记录 md）。
  被审四文件与工作树**逐字一致**（`git diff e52d1ad -- <四文件>` 输出 0 行）；范围外文件零触碰
  （`git diff fdb0185..e52d1ad -- tarch_normalize.py as_measured.py` = 0 行）。

---

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 0 条 · 不阻断 5 条）

四件都按返工单施工且验收成立：R1 两层门有真实反例支撑、字面收得紧（实测穷举过 Windows 盘符/
NUL/全角/空格等形态全被拒）；R2 三条固化的选取理由经逐维对账**成立**，且砍-verify 自证三条我
全部独立复核吻合；R3 清扫器落地但**结构上不可观测**（实测 neuter 后全绿）；R4 改对了点名的那段、
**漏了同文件里同一病族的另一句**（见 NF-1）。自陈的 docstring 引用不存在文件一事已修复，引用现为真。
我另实测坐实了 TOCTOU 窗口（字节真能落到根外）与清扫器误删并发写手在途 `.tmp` 两个边界——
两者今天实害均为零（该模块**全仓零生产消费者**），不构成本单阻断。

---

## 〇、独立复核记录（不信任何 RESULTS，全部重跑）

⚠️ **环境干扰先行声明**：主树工作树当前含 **F-147 席位在途改动**（`git status`: `M src/agent/judge/tarch_normalize.py`）。
在主树上跑受影响子集得到 **`1 failed / 69 passed`（连跑两次，红的是
`test_1_as_measured_matches_the_as_received_build_bit_for_bit`）**——归因链完整：该测试从 DXF 重建
as_measured，重建走 `as_measured.py:124` → `tarch_normalize`；重建哈希 `5591a8c3…` ≠ 落盘 `74b22e66…`
即 F-147 WIP 的产物。本单 diff 对该链 0 行。⇒ **本审全部读数取自 `git archive e52d1ad` 的 /tmp 干净副本**
（`/tmp/o21bTR_rev`，其 `tarch_normalize.py` 与 e52d1ad 逐字相同）。主树那条红**不计入本单读数**，
建议主控知会 F-147 席位：其 WIP 已让主树上一条既有测试转红。

| 项 | 我方读数（e52d1ad 干净副本） | 对照 |
|---|---|---|
| 受影响子集四文件（`-n 6`） | **70 passed ×2**（5.30s / 5.04s） | 执行记录 §五 `70 passed` ✅ |
| 逐文件计数 | admission 15 · gate 7 · sm25 8（=5+3）· revisions 40 | 与请求书 `18 = 15+3+0` 逐文件闭合 ✅ |
| 施工方 §2.2「砍 verify」自证 | #1/#2 → `Failed: DID NOT RAISE`、#3 → 仍 raise（**独立重放吻合**，2 failed + 6 passed） | 执行记录 §2.2 三条全对 ✅ |
| 基线红检查（fdb0185 + 四份新测试文件） | admission 整文件 ImportError（红）+ gate R3 红 + **14 passed**——sm25 三条 R2 在基线**是绿的**，符合事实：R2 读门在 ②-1b-T 就存在，这 3 条是给既有机制补锁 | —— |
| 全量 3348/13/0 | **未独立重跑**（席位纪律：子集即可，权威门归主控） | 采纳主控读数，标注未复现 |

---

## 一、findings

### 阻断（0 条）

无。

### 不阻断（5 条）

**NF-1 · ⭐⭐ R4 没改完：docstring 里仍有一句被同一文件内的函数签名直接证伪的话（「叙述比产物更合规」残句）**

- **实测**：`src/agent/judge/gt_facts_staging.py:41-42` 声称两个公开函数
  "**neither one hands a caller a ``Path`` to this directory**"——而
  `write_facts_candidate` 的签名就是 `-> Path`（`gt_facts_staging.py:251-252`），`return out_dir`（`:275`）。
  于是**全公开面、两行**就能拷目录，连 docstring 自己承认的那条「私有 helper 三行」路线都不需要：
  ```python
  out = gfs.write_facts_candidate(case, am, rev, sig)   # 公开 API，返回目录 Path
  shutil.copytree(out, <答案根>/facts)
  ```
  本审在 e52d1ad 副本实测：该两行路线与私有 helper 路线**都**把三件套完整拷出（`['as_measured.json',
  'as_signed.json', 'revisions.json']`）。配套：gate 测试只锁了读侧
  （`test_r3_read_facts_candidate_returns_typed_documents_never_a_path`，`tests/test_gt_facts_staging_gate.py:179`），
  写侧返回值无对应测试——因为一写就会红。
- **定性**：这句**先于本单存在**（`fdb0185:100-117` 已有 `-> Path` + 该句），且**我上一轮的 F-5
  也漏了它**（当时 E5 只查了 `import *` 面、判「公开面无 Path ✅」，没查返回类型）——施工方照单施工，
  单子的处方本身有盲区，这是我方责任。但 R4 的验收是「措辞改到与实测相符」：改写段（`:44-76`）如实承认了
  私有 helper 路线，一屏之上却留着一句被签名证伪的反话——同一病族改了一半。
- **不阻断理由**：纯文档句；R3 本来就只是 discoverability bar（本审再次实测两条路线都通，价值判断不变）；
  零生产消费者。**移交 ②-1c**：改一句 docstring，并裁 `write_facts_candidate` 要不要改回 `-> None`
  （行为变更、gate:82 等测试在用返回值，归下一单而非本单顺手改）。
- 复现：见附录 V-1。

**NF-2 · A2 实测坐实：TOCTOU 窗口是真的——字节确实能写到根外；但自报「当前场景不构成实际风险」的论证成立，且 ②-1c 现计划不推翻它**

- **注入实测（两次同结果）**：monkeypatch `verify_as_signed_reproduction`（write 路径里层2 之后、
  `_write_atomic` 之前的真实 ~8.5ms 窗口），把 `<root>/<case>/facts`（或 `<root>/<case>`）换成指向
  `/tmp` 的符号链接 ⇒ **三件套字节全部落到根外、write 静默返回 OK**（swap=facts：3 文件；
  swap=case：3 文件 + 新建 `facts/` 目录）。对照（不换链）：字节只在根内。
- **但利用前提**是「能在毫秒窗口内换符号链接的**并发文件系统对手**」，不是并发合法写手。
  ②-1c 的 `AnswerCompiler` 按 plan.md:85 是「**单一确定性**编译器」（读 facts 派生四种出模形式），
  **不引入对同一 staging 目录的并发写**；该模块今日全仓零生产消费者 ⇒ 「单进程单线程」前提在 ②-1c
  现计划下**不失效**。真正会被并发化击穿的是 NF-3 的清扫器，不是这道门。
- **结构性正解不变**：出口全检（答案根读侧同构 verify）对 TOCTOU 同样免疫——它不问字节怎么到的，
  只问现在复不复现。建议 ②-1c 派工单把「写侧 TOCTOU」记为已知边界而非待修项。
- 复现：见附录 V-2。

**NF-3 · A3 三问全部实测：清扫器是「新增的会删文件动作、零锁」——自报属实，判小净收益 + 一个记在案的新风险面**

1. **会不会删掉不该删的？会（实测）**：确定性两线程探针——victim 线程写好 `as_measured.json.tmp`
   挂起在 replace 前；主线程跑 `_sweep_stale_tmp_orphans` ⇒ 在途 `.tmp` **被删**，victim 的
   `replace` 落 `FileNotFoundError`（响亮失败，非静默损坏）。今天实害 0：测试全在 tmp_path 隔离根、
   无生产并发写手；**②-1c 若引入对同一 case 目录的并发写/retry 会踩**。
2. **读侧无害声明为真（grep + 读码核过）**：`read_facts_candidate` 只打开三个具名文件
   （`gt_facts_staging.py:287-291`）；全模块唯一的 glob 是清扫器自己（`:247`）。
   「读侧从不 glob」这句**逐字为真**——但注意它只覆盖读侧，清扫器本身是新增的 glob+delete。
3. **不加它有哪条测试会红？没有（实测）**：把 `_sweep_stale_tmp_orphans` neuter 成 no-op 后跑
   受影响子集 ⇒ **70 passed**；全 tests/ 目录 grep `_sweep_stale_tmp_orphans` **零引用**。
   它确实结构上不可观测。行为本身在跑（植入陈旧 `.tmp` → 下次 write 后消失，实测 True）。
- **判**：净收益成立（清的是本模块自己命名约定的 `*.json.tmp`，失败模式响亮），但按本项目
  「新加破坏性动作必须问锁」的标准记此条。**移交 ②-1c**：引入任何并发写之前，给清扫器加年龄阈值
  （如只删 >5 分钟的）或只清即将写的三个名字。
- 复现：见附录 V-3。

**NF-4 · gate 测试改写理由与它自己的断言相矛盾（A4 病族微发现）**

`tests/test_gt_facts_staging_gate.py:153-157` 的改写理由说：断言精确两名集合「会在每次未来合法新增时
失败……所以：断言本单关死的具名名字保持关死，**而不是把 `__all__` 冻结在两个条目**」——而 `:160-162`
的实际断言仍是**精确集合相等**（3 名）。未来第 4 个合法名字照旧会让它红，正是它自己批评的
「量的是集合变没变，不是有没有路径访问器」。与所声称意图相符的写法应是
`set(__all__) <= 允许集`（或具名坏名字不出现 + 允许名都在）。量级小、纯测试注释与断言错位，不阻断；
顺手改。

**NF-5 · A5 逐维对账结论：18 红里没有一维「完全落在锁外」；三条选取理由成立（此前提我核过，非默认采纳）**

- **机制分布**（e52d1ad 上重放 20 维矩阵）：(a) pydantic `ValidationError` **5 维**（T3/T8b/T16/T18/T20）
  · (b) `as_signed_revisions_do_not_target_this_as_measured` 哈希链 **4 维**（T6/T7/T11/T17）
  · (c) `as_signed_does_not_reproduce…` 复现比对 **9 维**（T1/T2/T4/T5/T9/T10/T12/T13/T19）
  · T14 绿（字节层非规范化，设计边界）；T15 本轮未重跑（08-29 已验为设计边界）。
- **每个机制都有真实形状的锁**：new#1 → (c)（真实读入口）；new#2 → (b)（真实读入口，消息名断言到
  `as_signed_revisions_do_not_target_this_as_measured`）；new#3 → (a) 的**字段 pattern 子族**。
  (a) 的**跨文档子族**（T3 的拦截者实测 = `as_measured_wall_line_ledger_broken` 等 pydantic
  model_validator，`as_measured.py:427-545` 一族）在 `tests/test_as_measured_facts_layer.py` 有成体系的
  篡改侧锁（真实 as_received 形状：`test_r2_the_ledger_identity_has_teeth` `face_lines.pop()`、
  `test_r2_a_dangling_reference_is_refused`、S1 台账三条）——与 `read_facts_candidate` 的 parse 步是
  **同一段代码**。
- **且 (a) 每维都有独立兜底**（实测推演 + 结构验证）：若跨文档校验器失效，T16/T18 落入 (b)、
  T3/T8b/T20 落入 (c)——内容一变哈希必断。即「某条校验器静默退化」的实害 = 诊断变差（晚一步、
  消息不点名），**不是防线消失**。
- **真正落在一切锁外的只剩 T14/T15**——都是设计边界（staging 信任级 = 0），正解就是被推迟的出口门，
  不是这 3 条该背的。revisions 侧 schema-valid 篡改（T9/T10/T12/T13）无**直接**锁，但全部走 (c)
  机制、已被 new#1 在真实读入口锁住。
- 结论：施工方「三个不同文件 × 两种失败机制」的选取经核**成立**；「每声称覆盖的量是否真被量到」
  的答案是「是」。上一轮 18 红 → 本轮 3 固化，其余 15 维经机制漏斗全部仍被量着。

---

## 二、A1–A5 逐条结论

### A1（⭐⭐⭐ 形状：入口收窄 vs 出口全检）

1. **挡住了哪类**：公共 API 上 `case` 的一切路径化——无论意外（调用方拿文件名/用户字段拼出来的）
   还是恶意（`../gt/…`、绝对路径、以及**字面完全合法但指向预置符号链接**的 bare token）。这是把
   F-1 那个「门没装门框」的洞在**类型层**真正堵死：未来任何调用方想让公开 API 写出根外，
   得不到静默成功，只能得到具名异常。**放过了哪类**：进程内蓄意绕行（私有 helper 三行——
   以及本审新发现的**公开返回值两行**，NF-1）；一切不经过本模块的写（`promote_gt_v3`、脚本、
   直接文件操作）；TOCTOU 竞态（NF-2）。
2. **它值不值「防绕过」？不值，且 docstring 现在基本说清了**：`:44-76` 的改写段如实定位为
   discoverability bar、亲口承认三行可用、记下出口全检才是结构性正解——这段合格。两处残句：
   `:41` 的反话（NF-1，**必须改**）与 `:35` 的旧标题 "structurally, not lexically"（下一段刚说完
   不挡可达性，标题还在说 structural——建议顺手弱化）。
3. **出口全检推迟到 ②-1c 对不对？对，且今天零代价（实测依据）**：`find case_tests/test_baseline/gt
   -name facts` = **0**；模块**零生产消费者**——出口门今天没有出口可装，装了也没有真实读路径可测。
   ②-1c 造出消费者（`AnswerCompiler`）的那一单装它，才是它该在的单元。**一个条件**：
   docstring（`:64-76`）与 CLAUDE.md §2⑤ 都记录了，但两处都是 prose——按本项目 prose↔gate 落差的
   老病，**②-1c 派工单必须把出口全检写成硬验收第一条**（含 NF-1 的返回值裁定与 NF-3 的并发前置），
   不能只引 docstring。②-1c 开工不会为 R1 本身付代价——准入门不拦合法 case 名，编译器照常读写。

### A2（TOCTOU）——见 NF-2：窗口实测坐实（两种换法、字节全落根外、静默 OK）；
自报的前提论证成立（②-1c 现计划 = 单一确定性编译器，不引入并发访问）。

### A3（清扫器）——见 NF-3：三问全部实测作答（会误删【并发场景下】/ 无害声明逐字为真 / 结构上不可观测）。

### A4（docstring 逐句核）

判据「每处『由某某证明』，那个东西存在吗、真覆盖吗」逐处过：

| 断言 | 位置 | 核验 |
|---|---|---|
| symlink 夹具证明层1放行+层2拦截 | `:117-123`、`:200` | ✅ `test_r1_symlink_in_the_staging_root_escapes_layer_1_but_not_layer_2`（含层1-must-not-raise 自证）+ 公开 API 重放版 + 根外零写入断言 |
| 「本模块自己的测试就在显式 import 私有名」 | `:53` | ✅ `tests/test_gt_facts_staging_sm25.py:21` import `_facts_staging_dir` |
| `StableId` 允许 `:` 而本模块刻意更窄 | `:146-152` | ✅ `gt_schema.py:31` pattern 含 `:`；`_CASE_NAME_RE` 无 `:`（顺带实测：含 `:` 的 case 名被拒） |
| `Path("/a") / "/b" == Path("/b")` | `:96-97` | ✅ admission 测试 `:79-83` 自带该断言 |
| 读侧从不打开 `*.tmp` | `:226-227`、`:238-240` | ✅ 读码 + grep（`287-291` 三个具名文件；唯一 glob 在 `:247` 清扫器自身） |
| 「case 在 verify 之前、任何文件系统触碰之前被拒」 | `:263-267` | ✅ `:269-271` 顺序如实（`.resolve()` 的 stat 是只读的，措辞可接受） |
| **「两个公开函数都不把 Path 交给调用方」** | `:41-42` | ⛔ **假**——NF-1，本轮 A4 的头条 |
| gate 测试改写理由 | gate`:153-157` | ⛔ 与 `:160` 断言矛盾——NF-4 |
| 自陈「docstring 曾引用不存在的文件」已修复 | 执行记录 §〇 | ✅ 该文件今在、15 条、覆盖所引场景（symlink 夹具正是被引的那条） |
| admission 文件头「每个夹具双向证明、对返工前模块必红」 | admission`:27-31` | ✅ 基线实测整文件 ImportError（红）；关键夹具（两名攻击/`.`/symlink/edge tokens）各带「本该是绿」的内嵌自证 |

**A4 总评**：自陈值钱、修复为真；剩两处残句（NF-1 必改、NF-4 顺手改）+ 一处旧标题（建议改）。

### A5——见 NF-5：**无维度完全落在锁外**；选取理由成立；T14/T15 是仅有的锁外量且属设计边界、归出口门。

---

## 三、本审实测清单（全部在 /tmp 副本，主树零写入；脚本留在 `/tmp/o21bTR_rev/`）

| # | 实验 | 结果 |
|---|---|---|
| V-0a | 主树子集 ×2 | 69+1failed ×2 → 归因 F-147 WIP（`as_measured.py:124`→`tarch_normalize`），不计入 |
| V-0b | **e52d1ad 干净副本子集 ×2**（`-n 6`） | **70 passed ×2** |
| V-0c | fdb0185 + 四份新测试 | 1 failed（gate R3）+ 14 passed + admission ImportError |
| V-0d | 砍 verify 重放 sm25 | #1/#2 DID NOT RAISE、#3 仍 raise（2 failed + 6 passed）——与执行记录 §2.2 逐条吻合 |
| V-1 | 公开返回值 copytree / 私有 helper copytree | 2/2 拷出三件套（NF-1） |
| V-2 | TOCTOU 注入（swap=facts/case + 对照）×2 轮 | 字节全落根外、write 静默 OK；对照正常（NF-2） |
| V-3a | 确定性两线程在途 `.tmp` | 清扫器删之、victim `FileNotFoundError`（NF-3.1） |
| V-3b | neuter 清扫器跑子集 | 70 passed ⇒ 结构上不可观测（NF-3.3） |
| V-3c | 陈旧 `.tmp` 行为探针 | 下次 write 后消失（功能在跑，但无锁） |
| V-4 | 20 维矩阵重放（e52d1ad，带异常类型） | 18 红（5a+4b+9c）+ T14 绿（NF-5） |
| V-5 | 答案根 facts 计数 | **0**（A1.3 排期依据） |

---

## 四、给 ②-1c 的移交清单（在上一轮四条之上增补）

1. ⛔ **派工单硬验收第一条 = 出口全检**（答案根 facts 读侧同构 verify）——不能只靠 docstring/CLAUDE.md 的 prose 记录。
2. 裁 `write_facts_candidate` 返回类型（NF-1）：要么改 `-> None`（连带 gate:82 等三处测试），
   要么 docstring 那句改成与 `-> Path` 相符。
3. staging 信任级 = 0、T15 重造自洽三门全绿是设计边界——编译产物在重签前不得记成绩（沿上轮 F-3）。
4. 引入任何并发写 staging 之前：清扫器加年龄阈值或收窄到三个具名 `.tmp` 名（NF-3）；届时 TOCTOU
   边界（NF-2）一并重审——正解是出口门，不是给入口加锁。
5. AnswerCompiler 生命周期缓存三对象；⛔ 禁分层校验/快慢两档（沿上轮 A4）。

---

## 附录 · 复现命令

**V-1（NF-1）**
```bash
git archive e52d1ad src tests pyproject.toml case_tests/test_baseline | tar -x -C /tmp/o21bTR_rev && cd /tmp/o21bTR_rev
python - <<'PY'
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/tmp/o21bTR_rev")
import src.agent.judge.gt_facts_staging as gfs
am, led, sig = gfs.read_facts_candidate("sm25-L_anchor")
root = Path(tempfile.mkdtemp()); gfs._FACTS_STAGING_ROOT = root
out = gfs.write_facts_candidate("sm25-L_anchor", am, led, sig)   # 公开 API
dest = Path(tempfile.mkdtemp()) / "gt/sm25-L_anchor/facts"; dest.parent.mkdir(parents=True)
shutil.copytree(out, dest)                                        # 两行，拷出三件套
print(sorted(p.name for p in dest.iterdir()))
PY
grep -n "neither one hands" src/agent/judge/gt_facts_staging.py   # :41
grep -n "def write_facts_candidate\|return out_dir" src/agent/judge/gt_facts_staging.py  # :251 :275
```

**V-2（NF-2）**：脚本 `/tmp/o21bTR_rev/e_a2_toctou.py`（A2 段：monkeypatch `verify_as_signed_reproduction`
在真 verify 前换符号链接）。输出：`swap=facts`/`swap=case` 两种均 `bytes landed under EVIL root:
[as_measured.json, as_signed.json, revisions.json]`、write OK；对照组正常。

**V-3b（NF-3.3）**
```bash
cd /tmp/o21bTR_rev
cat > sweep_neuter_plugin.py <<'PY'
import src.agent.judge.gt_facts_staging as _gfs
_gfs._sweep_stale_tmp_orphans = lambda out_dir: None
PY
python -m pytest -p no:cacheprovider -p sweep_neuter_plugin -q -n 6 \
  tests/test_gt_facts_staging_case_admission.py tests/test_gt_facts_staging_gate.py \
  tests/test_gt_facts_staging_sm25.py tests/test_gt_revisions_and_as_signed.py | tail -1
# -> 70 passed
```
（V-3a 确定性两线程探针在同脚本 A3 段：victim `FileNotFoundError`。）

**V-4（NF-5）**：脚本 `/tmp/o21bTR_rev/e_a5_matrix.py`（20 维重放，逐维打印异常类型与消息名）。
