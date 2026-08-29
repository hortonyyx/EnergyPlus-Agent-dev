# 跨家族复核裁决 · ②-1a-R 返工：事实层 `walls` 改从面线配对

- **日期**：2026-08-29 · **复核方**：GLM 跨家族 · **被审**：`5357db3..59a0e96`（施工 `af7c64d` + 读数 `59a0e96`）
- **开工自检**：HEAD=`05a5921` ✓ · 树干净 ✓ · `grep -c "gt 铁律" AI_agent/CLAUDE.md`=2 ✓ · 请求书逐字读完 ✓
- **纪律执行**：⛔ 无 `pip install -e .`、⛔ 无写 `site-packages`、⛔ 未改主树任何源码/测试（全部 neuter 在 `/tmp/o21a_review/neuter/` 的 `git archive af7c64d` 副本上做，做完已删）；探针全部 `PYTHONPATH` 强制 + `CODE_FROM` 自证（两侧各自断言加载路径在预期树内，不满足即 raise）。

## 裁决：**APPROVE-WITH-FINDINGS**（0 阻断 · 5 不阻断）

---

## 一、我独立跑的读数原文（⛔ 均为本席位自己产出，非转抄）

### 1.1 denominator() 行为等价（§二.1 最高风险处）

方法：`git archive 9977c26` 解到 `/tmp/o21a_review/old`（⛔ 未动主树、未建 worktree），
两侧各跑 `denominator()` 于四个视图（签字/as-received × F1/F2，输入数据在
`9977c26..af7c64d` 区间零变化——`git diff 9977c26..af7c64d --stat -- case_tests/ src/configs/`
为空，两侧用的字节级相同输入），dump 全返回值 JSON 后递归逐字段对比。

```
CODE_FROM（两侧各自自证，探针断言失败即 raise）：
  old: /tmp/o21a_review/old/src/agent/judge/as_drawn/denominator.py (+ tarch_normalize / as_measured 同树)
  new: /workspaces/EnergyPlus-Agent-dev/src/agent/judge/as_drawn/denominator.py (+ 同)

DONE signed_F1: 110 targets / signed_F2: 106 / arec_F1: 108 / arec_F2: 106   ← 两侧相同

递归对比（含 ledger/counts/targets/allowed_not_required/opening_ledger/diagnostics 全部键）：
== arec_F1:    raw-diff paths=172  after-stripping-new-keys=0
== arec_F2:    raw-diff paths=166  after-stripping-new-keys=0
== signed_F1:  raw-diff paths=175  after-stripping-new-keys=0
== signed_F2:  raw-diff paths=166  after-stripping-new-keys=0
TOTAL raw-diff=679  residual-after-strip=0
VERDICT: EQUIVALENT (only the two documented new keys differ)

raw 差异的构成（全部、且恰好全部）是两个文档声明的新增键：
  ONLY_IN_NEW:handles  (=targets 条数 108/106/110/106)  +  ONLY_IN_NEW:handle (=allowed 条数 64/60/65/60)
无一处 VALUE/LEN/TYPE/ONLY_IN_OLD 差异。
```

⇒ **判分分母的生产者在四个视图上行为等价，声称属实。**

### 1.2 四组厚度直方图（新树 `af7c64d`，我独立算）

```
NEW signed plan-F1: walls=55 thickness_mm={120: 28, 240: 27}
NEW signed plan-F2: walls=53 thickness_mm={120: 28, 240: 25}
NEW arec   plan-F1: walls=54 thickness_mm={120: 27, 240: 27}
NEW arec   plan-F2: walls=53 thickness_mm={120: 28, 240: 25}
```

### 1.3 返工审三条（我独立复现，含一份请求书没要求的对照）

```
① OLD(9977c26) signed plan-F1: walls=45 {100:1,120:5,240:7,296:1,300:16,304:1,356:1,360:11,364:1,500:1}
   OLD(9977c26) signed plan-F2: walls=39 {100:2,120:4,240:5,260:1,300:16,360:11}
   OLD(9977c26) arec   plan-F1: walls=44 {100:1,120:4,240:7,296:1,300:16,303:1,356:1,360:11,364:1,500:1}
   OLD(9977c26) arec   plan-F2: walls=39 {100:2,120:4,240:5,260:1,300:16,360:11}
   ← ①签字 F1 与请求书期望直方图逐字相同；与施工记录 §一.1 四组逐数相同
② NEW 四组见 §1.2 —— 幽灵值（100/260/296/300/303/304/356/360/364/500）一个都没有
③ NEW sm24 (source.dxf, sha256=92885d52340af72e24cd6396e893924f581b72983f5f1643076972d2aade245d):
   plan-F1: walls=35 thickness_mm={120: 17, 240: 18}   openings=21 carriers_len_hist={2:21} 同face_pair=21/21
   ⭐ 对照（请求书没要求、我补的）：OLD(9977c26) sm24 source.dxf:
   plan-F1: walls=26 thickness_mm={120:7, 160:2, 240:4, 300:9, 360:4}
   ← 老代码在第二栋楼上【同时】产幽灵（160/300/360 都不是 sm24 真有的）且丢 9 堵真墙（26<35）
   ⇒ 缺陷类（非单例）被新判据两病同治，第三条不靠合成夹具也成立
```

### 1.4 消费对账（我独立重算三桶，⛔ 不用 validator 自证）

```
== signed_F1   collected=225 (skew=0 degen=0) stored=225  funnel_ok=True
   buckets: paired=160 capped=65 loose=0  sum=225 stored=225  partition_ok=True
   fourth-fate: silent_drop=0  never_mentioned_by_D1D5=0
== signed_F2   collected=222 (0/0) stored=222  funnel_ok=True   162+60+0=222 partition_ok=True  0/0
== arec_F1     collected=223 (skew=1 degen=0) stored=222 funnel_ok=True   158+64+0=222 partition_ok=True  0/0
== arec_F2     collected=222 (0/0) stored=222  funnel_ok=True   162+60+0=222 partition_ok=True  0/0
```

两层漏斗都平：P1 收集线 → {非正交(itemised)/退化(计数)/存储 face_lines}；
存储 face_lines → {被墙引用/jamb cap 排除/落单} 三桶互斥且穷尽。
「第四归宿」探针（`if h in known` 过滤静默丢弃 + D1-D5 从未提及）两向均为 0。

### 1.5 split_const 偏差（§二.3 要我量的数）

```
signed_F1: deviation(|member_const − group_const|, 0.1mm 单位) hist={-4:2, -1:2, 0:156}  max=0.4mm
arec_F1:   hist={-4:2, 0:156}   max=0.4mm        signed_F2 / arec_F2: 全 0
独立重数 split 组数 = 文档自报 = 测试锁：signed F1=4 · arec F1=2 · F2 两视图=0
关键形态：signed F1 的 4 条偏差【同一堵墙的两个面同偏】(-1/-1 与 -4/-4) ⇒ thickness 不受影响
```

### 1.6 全量与哨兵

```
命令：python -m pytest -n 6        （⛔ 无 -m、⛔ 非 -n auto；HEAD=05a5921 跑前=跑后）

========= 3253 passed, 13 xfailed, 212 warnings in 1187.13s (0:19:47) ==========
（0 failed；与施工方声称 3253 passed / 13 xfailed / 0 failed 逐位一致；算术 3244+9=3253 ✓）

.pth 哨兵（跑前 / 跑后 / 复核收尾再记，三次全同）：
5198f6f9bf773d07373faa57a16e9564  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
a47a5925858b447ef52e3461fd6543e8  /opt/venv/lib/python3.12/site-packages/_virtualenv.pth
c767f0a08a993aec12f4a381d492dca2  /opt/venv/lib/python3.12/site-packages/sphinxcontrib_jsmath-1.0.1-py3.7-nspkg.pth

签字哈希独立重算：sm25 request d738d0ac230f21ae…(stored==recomputed ✓)
                sm24 request ae0fec087ef2a048…(stored==recomputed ✓)
全量跑完主树 git status --porcelain 仍为空、HEAD 仍 05a5921。
```

---

## 二、请求书 §二 六处逐一

1. **⭐⭐⭐ 提取行为等价** —— **属实**（§1.1）。残差 0，raw 差异恰为两个声明的新增键。
   探针两侧 `CODE_FROM` 自证 + 加载路径断言；旧侧 `git archive` 隔离，无串台。
2. **⭐⭐ 消费对账第四归宿** —— **未找到**（§1.4）。两层漏斗四视图全平；三桶互斥穷尽。
   唯一理论上可静默消失的位置是 `if h in known` 过滤与 D1-D5 未提及，两向实测 0；
   且 validator 的 `consumption_ledger_broken` 分支被测试用数据变异证明有牙。
   ⚠️ 附带观察（不阻断）：`loose` 桶在全部夹具上恒空 —— 见 §五.3。
3. **⭐⭐ `face_lo/face_hi` 存 1mm 组坐标** —— **裁定：不构成违反**。理由：
   ① 用户口径管的是【存储类型】（0.1mm 整数、禁浮点），`face_lo/face_hi` 是 int，合规；
   ② 值的语义是「生产者对哪几条笔画构成一条面线的回答」（D3 组坐标），不是某条笔画的坐标——
   墙由两条面线配对而成，本来就没有单一笔画坐标可存；
   ③ 0.1mm 精确值没有丢：笔画原样在 `face_lines`、墙按 handle 引用，分歧逐条点名
   （`face_groups_with_a_split_const`，实测偏差 ≤0.4mm、同墙双面同偏、thickness 无实害）。
   ⚠️ 但有一个「下一栋楼」形态要挂账（§五.1）：若将来某组偏差只打在墙的【一个】面上，
   thickness 会出 0.1mm 级非模数值——今天有厚度直方图锁兜底（值集变脏即红）。
4. **⭐ 复数承载墙** —— **数据完全支持，裁定正确**（§1.3/§1.4）：四视图 + sm24 共
   31/30/31/30/21 个洞口，全部恰好 2 carriers、0 个不同 face-pair、0 个 3 堵或 0 堵，
   且洞口几何上恰好夹在两段 run 之间（`run1.along_max ≤ op.along_min 且 op.along_max ≤ run2.along_min`
   全部成立）。D4 不跨洞口合并 ⇒ 「洞口在哪一段 run 里」确实无答案，硬选一段 = 往记录里写
   假话。复数是诚实形状。测试已锁 `len==2 + 同 face-pair + face-pair==洞口自身`(sm25) 与
   直方图+双面墨(sm24)。
5. **⭐ 返工审三条** —— **三条独立复现全过**（§1.3），且我补的老树 sm24 对照把
   「缺陷类修复」从推断变成了实测（幽灵+丢墙双病同治）。
6. **⭐ 反空转** —— **过**（§四：三个方向的变异全红，厚度断言不是恒真）。

## 三、请求书 §三 三条的独立判断

### #46 「sm24 会 BLOCK（F-132）」是题错 —— **确认**

我实测 `build_as_measured(sm24/source.dxf, request.json)` 直接跑通（35 堵干净直方图，
§1.3③）。身份门按**字节**哈希：source.dxf `92885d52…` 与 request 声明匹配
（盘上文件名 `source.dxf` ≠ request 里的 label `sm24_source.dxf`，但门不比名字）。
真 BLOCK 的是 `normalized.dxf`（另一份文件，`8416e908…` 不匹配）。
⇒ 返工审第三条因此拿到一栋与本单零关联的真楼，请求书判断正确。
**F-132 登记措辞**：登记说的是另一条门（gt 晋升件 `implementation_drift`、零测试触达）——
`tests/test_gt_promotion_path.py` 当前 72 passed 与它不矛盾（因为它说的就是没有锁在跑）。
**建议不改正文、补一句括注**：「不影响 as_measured 路径（其门按输入字节哈希）」——
这次误读的入口正是把两条门混为一条。

### #47 复数承载墙是施工方替派工方做的裁定 —— **裁定内容正确、程序合规**

内容上见 §二.4（数据 121/121 个洞口无一例外）。程序上：返工单没预见 carrier 会因此全灭，
施工方先量结构、按实测改 schema、把裁断原样写进施工记录请求复核——这正是「替口径裁断必须
交复核」的合规形态，且给出了完整读数（接触 {2:N}、严格重叠 {0:N}、face-pair {1:N}）。
我独立复测逐数相同。**采纳，登记为 #47 合理。**

### ⭐⭐⭐ 施工方驳回派工方 §五 理由 —— **驳回成立；替代理由站得住；准入条件按 §五.2 写才有牙**

1. **「gt 侧安全因为 DXF 输入确定」确实不充分**：这是「确定性输入 ⇒ 推导正确」的推理，
   ②-1a 自己就是反例——同一份确定性 DXF、确定性代码，产出 33 条虚构墙。若该理由成立，
   它同样会为 ②-1a 辩护。**输入确定只保证可复现，不保证正确。** 派工方理由的第二半
   （可被厚度直方图外部校验）才是承重件，但它被写成了附带性质。
2. **「外部可证伪」三件套不是口号，各有我实测的牙**：厚度断言（neuter-3 爆 36 个荒谬值⇒红）、
   消费台账（neuter-1 触发 `in_two_buckets` 红；测试另有 `consumption_ledger_broken` 方向）、
   第二栋楼（sm24 真输入、老树 26 堵两病、新树 35 堵干净）。
3. **「性质不是定理」的自省正确**：三件套靠人维持，删锁的人不会收到报警——所以要把
   「可证伪」从现状描述升格为准入条件。施工方的建议方向正确。
4. **与指南 §一「配对归模型」不冲突的承重理由**：那条口径禁的机制是「代码按声明厚度筛配对」
   （sm24 曾因此丢整批 120 隔墙），且它管的是 reading 的「认」。gt 侧必须有配对（否则
   reading 的配对无从判分）；实测新配对零厚度阈值 + sm24 的 17 堵 120 隔墙一堵没丢——
   被禁机制没有出现在 gt 配对里。**结论：不冲突，但承重理由是「可证伪 + 无被禁机制」，
   不是「输入确定」。**

## 四、我做的 neuter 与结果（全部在 /tmp `git archive af7c64d` 副本，做完已删）

| # | 变异 | 结果 |
|---|---|---|
| N1 | 墙源真·改回 `wall_bands`（9977c26 的 `_wall_records` 原样内联） | **schema 结构锁当场拦**：`AsMeasuredWallV1.cap_handles Extra inputs are not permitted`（4 视图全 ERROR）——「改回旧源」这个动作在新 schema 下建不成文档；比断言更硬 |
| N2 | 跳过 D2 剔除、把全部存储笔画直接喂配对器（返工单点名的陷阱形状） | **消费对账 validator 红**：`as_measured_face_line_in_two_buckets[wall+jamb_cap]`（65 条 jamb cap 被配进墙）——第二道防线真实有牙 |
| N3 | 配对「取最近」→「取最远」（保持成员消耗、账仍平、只改配对质量） | 走到 inventory 断言红（53≠55）；直方图独立计算 = **36 个非模数厚度（最大 20 m）⇒ THICKNESS GATE: RED** |
| S1 | neuter `_band_sort_key` + 反转 `wall_bands` 输入 | 字节改变（真牙）；真 key 下反转恒同（顺序无关性成立） |
| S2 | 检查 `_wall_sort_key` 全序性 | 54 堵墙严格全序（该缝在新方向真实承重） |

基线（未变异副本）`test_r2_measured_inventory` 4 passed 先行确认，非「本来就红」。

主树在全部 neuter 之后复检：`git status --porcelain` 为空（⛔ 未动主树一个字节）。

**neuter 结论：厚度断言不是恒真——三个方向（旧源结构锁 / 跳 D2 台账门 / 最近→最远厚度门）
各自在第一道对应防线红；「把配对改回 wall_bands」今天有【schema + 台账 + 直方图】三层等着它。**

## 五、我方没说到的地方

1. **【不阻断·挂账】组坐标偏差的「单面偏移」形态**：本图 4/2 条偏差全部同墙双面同偏，
   thickness 分毫未动。这是巧合不是结构保证——下一栋楼若只偏一面，会出 0.1mm 级非模数
   thickness。今天厚度直方图锁会红（有牙），但更稳的形态是把该锁从字面 `{120,240}` 推广为
   `set(hist) ⊆ set(request.wall_thickness_range_m 声明值)`——自动适用每栋楼，不用人手改常量。
2. **【不阻断】docstring 的 MEASURED 数字与自己的锁不符**：`AsMeasuredWallV1` 与
   `_split_const_groups` 两处 docstring 写「2 groups on signed plan-F1, **0 on the other
   three views**」，实测与测试锁都是 signed F1=**4**、arec F1=**2**、F2=0。锁是对的、散文错
   （施工记录 §二末尾同错）。修 = 两行数字；按 [[self-report-more-compliant-than-artifact]]
   的既定纪律点名——这次是「自述比锁粗心」，趋势反了但仍要修。
3. **【不阻断·观察】`loose` 桶全夹具恒空**：`face_lines_not_paired_into_a_wall` 在
   sm25 四视图、sm24、合成夹具上都是空。它不是门缺陷（pairing 大面积失败时 walls 先少、
   厚度直方图锁先红），但「pairable but unpaired」这个合法状态从未被任何夹具真实行使。
   建议合成夹具补一个「故意落单一条面线」的形态，让该桶至少被真实走过一次
   （[[two-kinds-of-latency-no-ruler-vs-never-reached]]：没跑到 ≠ 没问题）。
4. **【补充】准入条件的第四件套**：施工方三件套之外还有第四样现成的——**幽灵形状的回归锁**
   （`test_r1_the_old_wall_band_source...` 与 `...puts_the_ghost_walls_back` 把「band 源必须
   仍产 300mm 幽灵」锁死）。D2 将来被削弱时这两条先红。写准入条件时应把它一并列入。
5. **【确认】**区间 `5357db3..af7c64d` 与 `af7c64d..05a5921` 的边界我核过：前者是全部代码改动
   （3 文件），后者只补两份 md（源码与 9977c26 侧对比时用主树=af7c64d 等价，成立）。

## 六、阻断 / 不阻断清单

**阻断（0 条）**

**不阻断（5 条）**
1. docstring ×2 + 施工记录散文的 split_const 数字错（4/2 写成 2/0）—— 锁正确，改散文两行。
2. 「单面偏移」潜在形态挂账 + 建议直方图锁推广为「值集 ⊆ 声明集」参数化。
3. `loose` 桶零存货观察 —— 建议合成夹具补落单形态。
4. F-132 登记建议补括注「不影响 as_measured 路径」，防两条门再被混为一条。
5. 准入条件落地形态建议：按 §三.⭐⭐⭐ + §五.2/§五.4 写（测试函数名引用清单，非 prose）。
