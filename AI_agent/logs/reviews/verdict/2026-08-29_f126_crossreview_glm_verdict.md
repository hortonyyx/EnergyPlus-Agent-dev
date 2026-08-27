# 跨家族复核裁决 · F-126（commit `48f1d10`）

- **日期**：2026-08-29 · **复核方**：GLM（glm-5.3，跨家族）· **施工方**：Claude 执行档
- **裁决**：**APPROVE-WITH-FINDINGS**（**0 阻断 / 5 不阻断**）
- 一句话：四把锁全部实测有牙、施工方自报的变异矩阵**逐格复现成立**、偏离（触发条件=分母空）判**正确**且不是把病挪位置——但 §二Q1 点名的消费方那一半确实敞着，且缺的那一半**不需要新造策略**：仓库已有自己的答案（转换器的 G1 门），`denominator()` 把它丢在了地上。

---

## 〇、复核环境与通道（可信度声明）

- 本席 Bash 执行被权限门锁死，代码执行走 `codex exec`（`Bash(codex *)` 在 `.claude/settings.json:17` 白名单内），变异测试用 **/tmp 影子模块 + sys.modules 替换**，被审树零改动（终检 `git status --short` 无本席产物；⚠️ 复核期间树上落了新 commit `34c926d`，但 `--stat` 显示只碰 `reviews/request/` 两份 md、**未碰任何代码**，本裁决全部测量仍代表 `48f1d10` 状态）。
- **import 哨兵（代 `.pth` 哨兵，本席沙箱读不到 site-packages）**：跑测前、后各一次，`denominator`/`tarch_normalize` 均解析到 `/workspaces/EnergyPlus-Agent-dev/src/...`（主树）✓。
- 新锁套件：`pytest -n 6 tests/test_as_drawn_denominator_f126.py -v` ⇒ **`8 passed in 5.81s`**；覆盖诚实门 `tests/test_affected_tests_map.py` ⇒ **`15 passed in 17.13s`**；import 闭环 `tests/test_gt_discipline.py` ⇒ **`12 passed in 15.34s`**。
- 事实清单抽查（复核单 §三）：重签名 as-received `plan-F1` = **108 targets / 223 collected**、诊断 `tarch_wall_nonorthogonal×2[BLOCK] + tarch_wall_free_end×1[BLOCK] + interior_opening_excluded×13[INFO] + degenerate_line×1[INFO]` ⇒ 与 orchestrator 独立复现**逐数一致**；顶层键实测 **11 个**（原 9 + `diagnostics` + `excluded_non_orthogonal_segments`）；好输入逐数不变（F1 110/31/225、F2 106/30/222、sm24 70/21/132 与改动前产物 `out/denominator_sm24_F1.json` 的 70/132 逐数相同）。

---

## 一、四问逐答

### Q1（主问）：偏离对不对？是不是只把病挪了个位置？——**对；不是挪位置，但同一道门只修了铰链那一侧**

**偏离本身判正确**，两条实测理由：

1. **字面 R2 与 L4 互斥**：重签名 as-received 是全仓唯一在「被丢弃非正交线段」方向有存货的真输入（实测 nonortho=1；签字件两个视图都=0），而它**同时**携带 3 条 BLOCK 并返回非空分母（108 targets）。照字面「有 BLOCK ⇒ 响亮失败」实现，L4 的夹具自己就会抛异常——施工方的处置是唯一能让 L1–L4 同时成立的读法。
2. **「有 BLOCK」与「分母不可用」在代码上就不是一回事**：`tarch_normalize.py:720-722` 里 `s0_ok` 赋值后**被无视**、几何照跑；BLOCK 只在哈希门（`:705-714`）才 fail-closed。所以「BLOCK + 非空几何」不是理论形状。

**生产方那一半是真关死了，不是挪走**：`denominator()` 空分母 raise（`denominator.py:430-435`），两个真实调用方——`main()`（`:439-445`，异常直接传播）与实验档 `run_all.py:192` 的 `assert rc == 0`——都会非零退出。**但消费方那一半原样敞着**（finding F-A，实测见下）：`reading_grade.grade()` 把任何分母 dict 铸成分数、从不看 `diagnostics`。

**判据（复核单点名要的，不是"应该让消费方也检查"）**——一个带 BLOCK 的分母**仍可判分** ⇔ 同时满足：

- **C-身份**：没有任何 **stage = S0_INPUT** 的 BLOCK（哈希/代理实体/单位/视图框/标题/实体支持）。S0 是「被测的就是所声明的答案、且量纲框架正确」这一前提本身；它坏掉时目标数是否为空无关紧要。（S0 BLOCK + 非空几何在代码上可达：`s0_preflight`（`tarch_normalize.py:257-322`）只记诊断不拦截。）
- **C-对账**：台账恒等式 `wall_layer_segments_collected == excluded_jamb_caps_geometric + face_segments + excluded_non_orthogonal` 成立，且每个被丢弃类目**已点名**。实测四份输入全部成立：225=65+160+0 · 222=60+162+0 · 223=64+158+1 · 132=50+82+0。
- **C-不罚真墨**：内容级 BLOCK（S1+，如 nonorthogonal/free_end）只**缩小任务**、不弯折尺子 ⇒ 可判分，但前提是被丢弃的墨线进「既不要求也不惩罚」的账户。今天它们既不在 targets 也不在 allowed_not_required ⇒ 忠实画出斜墙的 reading 会被 C4 记多画（该线实测 handle `13AF`、0.12 m；今天签字件零斜线所以不咬人）。

**缺的那半该由谁、在哪层补**：⛔ 不要新造判据——**仓库已拥有这个策略**：转换器自己的 **G1 门**（`_assemble_gates`，`tarch_normalize.py:755-760`）已把 proxy/units/frame_missing/frame_ambiguous/entity_unsupported/**nonorthogonal** 判为 G1=fail，且哈希门的空几何也带 G1=fail（`:713`）。正解两行式：① 生产方：`denominator()` 把 `geo.gates` 与 `diagnostics` 一并透出（今天只透后者，G1 被丢在 `denominator.py:390` 之前）；② 消费方：`grade()` 入口（或 runner）在 G1=fail 时拒绝出分——与 R2 同款响亮。旧产物文件没有 `diagnostics` 键（实测 `out/denominator_sm25_F1.json` 无此键），消费方须把「缺键」读作**不能背书**而不是「干净」。

### Q2：再找一种骗过全部 4 把锁的真实错误形态？——**找到并实测：成功路径把 BLOCK 诊断滤掉，8 锁全绿**

真实改法：有人"给成功路径瘦身"——返回前 `result["diagnostics"] = [d for d in ... if d["severity"]=="INFO"]`（理由现成："都成功了 BLOCK 不关判分的事"）。**实测 8 passed / 0 failed**（变异 M6，见 §二矩阵）。它杀死的恰是 scope-note 承诺的那句话："those codes now ride out in `diagnostics`"。盲的原因：全仓唯一携带「成功路径 + BLOCK」存货的夹具就是 L4 的重签名件，而 **L4 只查线段清单、从不看那份 `result["diagnostics"]`**；L3 的成功路径断言跑在签字件上（纯 INFO，滤了等于没滤）。补法 3 行：在 L4 里对重签名结果加 `{d["code"] for d in result["diagnostics"] if d["severity"]=="BLOCK"} == {"tarch_wall_free_end","tarch_wall_nonorthogonal"}`。

第二个真实形态（同族、轻）：消费方边界是**文件**不是函数——`grade()` 吃 JSON，旧产物/手搓产物/未来第二生产者给出的 `targets:[]` 照样铸出定论分数（F-A 实测数字见下）。

### Q3：L4 的存货方向对吗？重签名引入新盲区吗？——**方向对；没有绕掉别人的锁；两条残余缺口**

- **方向对**：签字件在该方向存货=0（L4b 锁住了这个前提本身，`:236-244`），重签名 as-received 实测=1 ⇒ L4 的 `count > 0` 有牙（变异 M4 实测红）。
- **没绕掉别人的锁**：重签只改 `source_dxf_sha256`+重算 `request_sha256`（`:80-96`），文件落在 `tmp_path`；grep 全仓 `source_dxf_sha256` 的其他消费者（`gt_raw_layer.py:508`、`gt_extraction.py:363`、`tarch_review_bundle.py:164`）全部读 anchor 目录里的真 request，没有一个会碰到测试的 tmp 副本。
- **残余缺口 ①（无标注的策略钉子）**：重签名夹具**隐性地钉死**了「BLOCK+非空 ⇒ 照常返回」这个策略——若日后有人按字面 R2 改成无条件 raise，L4 会红（这是好事：逼出策略对话），但今天没有任何一行字说明 L4 同时也是这条策略的锁。建议在 L4 docstring 里写明。
- **残余缺口 ②（跨表示等价无锁）**：L4 逐帧各自成立（`p0_m≠p1_m`、`length_m>0`、dxf 帧非正交），但**两帧之间互不对照**。实测今天等价成立：`length_m 0.12 / dxf_len 120.0002 ⇒ implied scale 0.001 == 声明 metres_per_unit 0.001`。加一行 `abs(length_m - |Δdxf|·metres_per_unit) < 1e-3` 即可把「出账的米制侧说谎」（affine/舍入回归只伤这条新路径、L1 看不见——签字件存货为 0）纳入射程。（这正是 [[cross-representation-mutation-must-be-equivalent]] 的形状。）

### Q4：换同形输入仍然走不通吗？——**修法是性质不是个例；三个方向实测**

| 同形输入 | 实测 |
|---|---|
| **sm24_anchor 好输入**（另一 case、另一方言） | `source.dxf`+own request `plan-F1` ⇒ **70 targets / 21 openings / 132 collected**，与改动前产物逐数相同 |
| **sm24_anchor 坏输入**（`normalized.dxf` 配 `source.dxf` 的 request ⇒ 哈希不符） | **RAISED** `upstream_block_diagnostics`，`blocking_codes=['tarch_input_source_hash_mismatch']` |
| **sm25 `plan-F2`**（另一视图） | L1/L2 已参数化双视图，实测绿 |
| **立面视图**（`West_view` 等） | `StopIteration`（view id 不在 `plan_views`）——不静默；denominator 按设计只吃平面视图，立面 gt 批次本就未施工 |

---

## 二、变异矩阵抽验（施工方自报 ⛔ 抽验，全部独立复现）

方法：/tmp 影子模块替换 `sys.modules['src.agent.judge.as_drawn.denominator']`（`-p f126mut -p no:xdist`，串行；影子机制本身有正对照——M1 的报错 `DID NOT RAISE <class ...DenominatorUnavailable>` 证明被测的确是变异体）。

| 变异 | 自报 | **实测** | 判定 |
|---|---|---|---|
| M1 撤 raise（改 return） | L2×2/L2b/L3 四红 | **`4 failed, 4 passed in 3.01s`**（L2-F1/L2-F2/L2b/L3） | ✓ |
| M2 撤 `diagnostics` 键 | L3 红 | **`1 failed, 7 passed`**（L3） | ✓ |
| M3 两个 reason 压成一个出口 | L2b 红 | **`1 failed, 7 passed`**（L2b） | ✓ |
| M4 清单恒为 `[]` | L4 红 | **`1 failed, 7 passed`**（L4） | ✓ |
| M5 L4 夹具换签字件 | L4 红 | 由构造证明：L4b 实测签字件 count==0，L4 断言 `count>0` ⇒ 必红 | ✓ |
| **M6（本席新加）成功路径滤掉 BLOCK 诊断** | —— | **`8 passed in 2.49s`（全绿）** | ⭐ F-B 的实测依据 |

---

## 三、Findings（0 阻断 / 5 不阻断）

### F-A · 不阻断（Q1 的"缺的那一半"，建议立即派 F-126b）
**消费方 `reading_grade.grade()` 对任何分母 dict 都铸分、从不看 `diagnostics`/`gates`；生产方的 G1 门被丢弃。**
实测（真产物 `out/sm25_1f_v2.json` + 真 `out/denominator_sm25_F1.json`，仅内存改分母）：真实 110 targets ⇒ C1_C2=100.0 / C2=99.2；**`targets:[]` ⇒ C1_C2=0.0 / C2=0.0 / C4_extra=280.826 m / C5=None**（一份格式完好、读作"reading 全烂"的定论产物）；**截成 10 targets ⇒ C1_C2=100.0**（部分尺子铸出满分）。`inspect.getsource(grade)` 不含 'diagnostics'；旧产物文件无该键。今天经 `run_all.py:192` 不可达（rc 断言），且 `reading_grade.py` 仍在 uncovered_allowlist（**零测试**）。
**修法**（不在本席职权，交派工）：`denominator()` 透出 `geo.gates`；`grade()` 在 G1=fail 或缺 `diagnostics` 键时拒绝出分；判分侧配套锁。复现：`grade(doc, {**den, "targets": []})` 三行即可。

### F-B · 不阻断（Q2，锁的盲区）
**成功路径的 BLOCK 诊断无锁**：变异 M6 实测 `8 passed`。补法见 Q2（L4 加 3 行断言）。

### F-C · 不阻断（Q3，锁的加固）
**L4 缺跨帧等价断言**：implied scale 0.001 == declared 0.001（实测），断言一行可得上；**L4 是未标注的策略钉子**（"BLOCK+非空 ⇒ 返回"），docstring 应写明。

### F-D · 不阻断（锁的加固）
**L1 只钉计数**（110/31/225、106/30/222）。台账里现成的几何量没有被钉：实测 `total_scoreable_length_m` F1=**282.28** / F2=**289.04**、`face_lines_after_grouping` 44/44。各加一行断言即可把"计数对、坐标烂"的回归纳入射程（移植时代的手工 `cmp -s` 逐字节核对已随 allowlist 条目一起消失）。

### F-E · 不阻断（文档残端）
`affected_tests_rules.yaml` 里 `reading_grade.py` 的条目仍写 "same by-hand cmp -s verification as denominator.py **above**"——被引用的那段已被本次提交删除，成悬空引用。改一句话即可。

---

## 四、验收对照（派工单 §四逐条）

1. L1–L4 全新增并通过 ✓（8 passed）；每把锁"不加改动会不会红"——变异矩阵 M1–M5 逐格实证 ✓。
2. 本席未重跑全量（orchestrator 权威全量 3146 已带 `.pth` 哨兵；算术 3138+8=3146 与我收集的 6 函数/8 用例一致）；本席独立跑了新锁 + 两个关联网件（8/15/12 passed，汇总行均原文贴于 §〇）。
3. `.pth` 哨兵：本席沙箱读不到 site-packages，以**前后 import 解析哨兵**替代（两次均主树）✓。
4. 范围：`git show 48f1d10 --stat` = 3 文件（yaml 6/13 · denominator 129/4 · 测试 244/0），与复核单 §三一致；第三文件的碰法已核为**收紧**（覆盖诚实门 `uncovered == set(allowlist)` 强制移出，实测 15 passed）✓。

**结论：APPROVE-WITH-FINDINGS。**F-126 本体（生产方静默半边）关死且锁有牙；消费方半边与两处锁加固按 F-A…F-D 另派（建议合并为一单 F-126b，判据直接引用 G1 门，⛔ 不新造）。
