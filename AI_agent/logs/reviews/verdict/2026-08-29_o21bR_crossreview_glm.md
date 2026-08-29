# ②-1b-R 返工复审裁决书（GLM · 与上一轮同一席位）

- **日期**：2026-08-29 · **审阅方**：GLM 家族（glm-5.3，= 上一轮判 REWORK 的同一席位）· **请求书**：[`../request/2026-08-29_o21bR_crossreview_glm.md`](../request/2026-08-29_o21bR_crossreview_glm.md)
- **送审对象**：`201f47f`（主）+ `f140708`（补记）；**返工前基线** `596258c`。审的是 `git diff 596258c..f140708`；当前 HEAD `23fd454` 与 `f140708` 的 src/tests **逐位一致**（仅差文档，已核），故全部探针在当前树上跑、旧侧在 `git archive 596258c` 的 /tmp 副本跑。
- **方法**：所有 RESULTS 独立重跑、关键探针**双跑**逐位复现；旧树探针经 `PYTHONPATH=/tmp/o21b_old` 隔离并打印 `gt_revisions.__file__` 自证未串台；neuter/变异（R3 塞哈希、GROUP_QUANT 改值）只在 /tmp 副本做；引用行号全部回文件 `grep -n` 核过；未动主树任何文件（本裁决书除外）、未 git commit、未碰 site-packages。

---

## 裁决：**APPROVE-WITH-FINDINGS（阻断 0 条）**

四件返工全部兑现且实测成立；上一轮唯一阻断（B-1/F-137）的门已落地、方向正确（复刻生产者 D3 定义而非自造公式）、真实数据 107 堵墙零假阳；R1 返工途中的假阳性修复本身经受住了我的公式同式审查与变异实验。三条验收全过。新找到**第 7 种同形输入两条**（换图层伪装 translate 为主），与上一轮 F-139 同型同档——按同一把裁尺判不阻断，登记并由下一次动 `gt_revisions.py` 的单顺手带上。

读数复核先行：**全仓独立复现 `3305 passed / 13 xfailed / 0 failed`**（`python -m pytest -p no:cacheprovider -q -n 6`，834.38s，exit 0），与主控权威门、施工方第三次读数**三方逐位同数**；`.pth` 哨兵跑前跑后同为 `58f547fa9433…`（内容指主树）；工作树跑前跑后皆空。新增 13 条逐文件数对：`test_as_measured_facts_layer.py` 43→47（+4）、`test_gt_revisions_and_as_signed.py` 23→31（+8）、`test_tarch_converter_reproducibility.py` 13→14（+1），`4+8+1=13=3305−3292` 精确闭合。⚠️ 如实记录：全量窗口内我并行跑了三个受影响测试文件的子集（98 passed / 34s，纯内存测试不写树）与若干只读探针，全量汇总行完整给出 ⇒ 读数有效。

---

## 一、阻断（0 条）

无。

---

## 二、不阻断 findings

### F-1 ·【⭐ 本轮新找到的第 7 种同形输入·主】换图层（`layer`）伪装成合法 translate——R2 只堵了 axis，同一半句处方里的 layer 没堵

**复现**（`python3 /tmp/probe_7th.py /workspaces/EnergyPlus-Agent-dev`，双跑同读数）：before 的 handle `1A1` = `layer="WALL", axis="y", const=1000`；after 同 handle = `layer="AXIS-GRID", axis="y", const=990`：

```
[A 换图层] rev-1a1 | check=face_line_field_changed | candidate=kind='translate' field='const' delta_0p1mm=-10
        detail 提到 layer: False | detail 提到 axis: False
```

**定性**：与 F-139 完全同型——「这根本不是同一条墙线」的语义信号（图层换了：墙线变成了轴线/网格线）在候选里完全不可见，数值比较照常进行，人签字后 as_signed 里一条 WALL 图层的线被按 AXIS-GRID 线的坐标平移。R2 自己的代码注释写明「comparing const/along_min/along_max **across different axes** is not merely 'no candidate', it is comparing the wrong quantities」——layer 跨图层比较是同一句话的另一半。上一轮我方 N-6 的原始处方是「比 `axis`（**与 `layer`**）」，返工单（§二 R2）只转录了 axis ⇒ **施工方按单完成，layer 是处方半句未入单**，不算返工失败；按 F-139 上一轮同档（真实触发件未现、形态已在）判不阻断。
**修法 3 行**：`detect_translate_candidates` 的比较集从 `axis` 扩为 `(axis, layer)`，check 名如 `face_line_identity_changed`。下一次动 `gt_revisions.py`（含 F-2/F-4 的单）顺手带上。

### F-2 ·【第 7 种·次】跨视图同名 handle 遮蔽——能绕过 R2 的换轴检查本身（上一轮 N-7 的具体化）

**复现**（同上脚本 B 段）：after 的 `plan-F1` 里 `1A1` **真的换轴了**（y→x, const=990），但 `plan-F2` 里又有一条同名 `1A1`（axis=y, const=1005）。`_index_face_lines_by_handle`（`gt_revisions.py:432-433`）跨视图后者覆盖前者 ⇒ detect 看见的是 F2 那条 ⇒ **axis 检查放行**，报出 `translate const +5`；而 `target.view_id` 取自 before = plan-F1 ⇒ 候选将被应用在**换轴了的那个视图**上——比错的线、打在对的视图，双重错位。

**定性**：根源是上一轮 N-7 已登记的索引结构（真实 sm25 F1∩F2 face_line 交集 = 0，今天不触发），不是 R2 的错——R2 在它看得见的范围内正确。并入 N-7 登记，随 N-7 的修法（索引遇重复 handle 直接 raise）一并解，不单独阻断。

### F-3 ·【= 请求书 N-a】探测下限「0.5 mm」不成立——真实灵敏度**位置依赖 0.1~0.9 mm**；红侧无测试钉住；GROUP_QUANT 复刻无锁（且实测是**静默**不是假红）

三段实测，逐条给数：

1. **主控读数逐位复现**（`/tmp/probe_f137.py` 打在 1379 上，const=0 恰在毫米格中心）：delta = 1/2/4 单位（0.1/0.2/0.4 mm）放过；5/9/10/20/50/100/500（0.5 mm 起）响亮 `as_signed_wall_face_lo_disagrees_with_its_face_lines`。
2. **⭐ 但换真实 split-const 面线 140E**（const=159396、其墙 `w_x_159400_160600_111200_147600` 的 face_lo=159400、合法偏离 −0.4 mm；`/tmp/probe_f137_140e.py`，双跑同读数）：
   ```
   向离开组中心方向：-0.2 mm 即红（-0.1 mm 因浮点边界恰好留在原格，绿）
   向组中心方向：  +0.1/+0.2/+0.3/+0.4/+0.5 mm 全绿，+0.9 mm 红
   ```
   ⇒ **同一条线上两个方向的灵敏度差 4 倍以上；同一张图上同样的 0.5 mm 位移，在 1379 上红、在 140E 上绿**。门的真实分辨率不是常数 0.5 mm，而是「该线当前 const 距毫米格边界的距离」，取值区间 [0.1, 0.9+] mm。`test_f137_g` docstring 里「by up to ~0.5 mm」以偏概全（那是组中心线的特例）。
3. **GROUP_QUANT 耦合是静默的，实测证实**（/tmp 副本 `denominator.GROUP_QUANT` 3→2、门仍用 `_GROUP_QUANT_DECIMALS=3`）：真实 sm25 零 revisions 派生 **SUCCESS——门没有发现刻度已经不一致**。机理：真实数据的 const 尾数 ≤0.4 mm，在毫米格与厘米格下归同一格；「假红」只会在尾数 ≥0.5 mm 的成员（下一栋楼才可能出现）上发生。施工方自述「改上游会静默移动下限」**准确**。
4. **测试钉住核查**：绿侧有钉（`test_f137_g`：0.4 mm split-const 零 revisions 通过）；红侧**无钉**——最近的 `test_f137_a` 用 delta=500（50 mm），离分辨率边界差 100 倍，没有任何测试钉「越过毫米格 ⇒ 红」。

**裁定**（N-a 两问的答复）：**该做「命名+加锁」，不阻断**。理由：(a) 下限本身不是缺陷——它由「判据必须复刻生产者定义」直接决定：墙的 `face_lo` 只有毫米格分辨率（D3 量子化、split-const 已命名登记），任何一致性检查的下限必然等于格分辨率；格内移动时墙的组坐标**确实**没变，绿是对的；越格时 as_signed 里真的出现面线与墙组坐标不一致，红也是对的。(b) 公式同式经我独立审查成立：生产者 const 先 `round(仿射, QUANT=4)` 量化（`denominator.py:325/330`）再 `round(·, GROUP_QUANT)` 分组（`denominator.py:371`），门的 `_group_const_of` 从同一 0.1 mm 格点整数出发做同一 `round(·, 3)`——**同一格点浮点、同一 banker's round ⇒ 结构同式**，残余差异仅双重浮点边界巧合；107 堵墙零 revision 全过门（见 N-b）为实证。(c) 实质缺口是三条便宜的锁，**下一单 5 行内带上**：① 红侧分辨率钉子（组中心线 +5 单位 ⇒ 必须 raise；split-const 线 −2 单位 ⇒ 必须 raise）② 用一条断言把 `_GROUP_QUANT_DECIMALS == denominator.GROUP_QUANT` 钉住（或直接 import，是否引依赖由施工方跨单判断）③ `test_f137_g` docstring 的「~0.5 mm」改为机理表述「越出所在毫米格」。

### F-4 ·（小）格内 translate 后 `face_groups_with_a_split_const` 登记在 as_signed 里 stale

**复现**（纯内存）：签 140E `const −1 单位`（0.1 mm，格内，门绿、合法），derive 后 as_signed 里 140E `const=159395`，而 `converter_readouts.face_groups_with_a_split_const` 原样带过、仍写 `member_consts: [159396]`。诊断登记与实际面线失同步。低危（该登记是诊断字段非判据输入；「这个组有 split」的定性仍真，只是偏离量旧了）。修法：`derive_as_signed` 对被 translate 的 handle 重算该登记，或 docstring 声明「登记是 as_measured 时刻的快照」。随 F-1 的单带上。

### F-5 ·（顺带核实，非新 finding）R2 修复后真实五条清单逐位不变

`test_6_the_five_line_worklist_is_all_unsigned_with_two_well_formed_candidates`（基线 596258c 就存在、非本轮新加）从两份 dxf **重新计算**并断言 2 条 translate（13AC/160A）+ 3 条 None（13AD/13AE/13AF），当前 5 passed ⇒ 施工方「真实清单逐位不变」的自述有既有回归锁背书 + 我方独立跑绿。

---

## 三、三条验收逐条结论（⛔ 返工审三条，不是两条）

| | 结论 | 证据 |
|---|---|---|
| **① 旧 commit 复现** | ✅ 成立 | `git archive 596258c` 副本（`PYTHONPATH` 隔离 + `__file__` 自证）：F-137 探针 `1379 const+500` ⇒ derive **SUCCESS 无 raise**、墙仍 `face_lo=0/face_hi=2400/thickness=2400`（与上一轮裁决逐位同）；F-139 探针（上一轮 `/tmp/probe_axis_swap.py` 原脚本）⇒ 报 `translate const −10`、detail 无 axis、签字后进 as_signed 全链绿。均双跑 |
| **② 新 commit 不复现** | ✅ 成立 | 当前树（src/tests ≡ f140708）：F-137 同探针 ⇒ 响亮 `as_signed_wall_face_lo_disagrees_with_its_face_lines`；F-139 同构探针 ⇒ `face_line_axis_changed` + `candidate_action=None` + detail 点名 axis。施工方 6 变体抽核：`test_f137_b/c/d/e`（换面线/along_min/along_max/负号）以提交测试存在且绿（三文件子集 98 passed）；真实数据变体由我方 140E 探针（真实 sm25、另一堵墙、双向有牙）覆盖；`test_6` 五条清单不变 |
| **③ 换同形输入仍走不通** | ✅ 找到**第 7 种两条**（F-1 换图层·主 / F-2 跨视图遮蔽·次），均判不阻断（与 F-139 上一轮同档） | 见 §二 F-1/F-2。另排除三条候选路径：target 指向非面线实体 ⇒ `derive` 已有 `as_signed_translate_target_not_found` 响亮拦截（`gt_revisions.py:406-409`）；unpaired 面线大幅 translate ⇒ 语义上只有一份记录无「失同步」可言（非同形）；「签了不生效」通道不存在 |

---

## 四、N-a / N-b / N-c 逐条裁定

### N-a · 门的下限与锁 —— **做「命名+加锁」，不阻断**（详 F-3）

要点重述：①「0.5 mm 下限」不成立，位置依赖 [0.1, 0.9+] mm，同一图上等量位移红绿不一致；② 门公式与生产者 D3 **结构同式**（同一 0.1 mm 格点浮点进同一 round），107 墙实证零假阳；③ 红侧无钉、GROUP_QUANT 复刻实测**静默**（非假红）；④ 三条锁（分辨率钉子 / 常量联动断言 / docstring 改机理表述）下一单带上。**「本来就该这样」的部分** = 格量子化分辨率本身（复刻生产者的必然后果）；**「加锁」的部分** = 把分辨率的两侧钉进测试、把常量联动变成可执行断言。

### N-b · along/thickness/carrier 上还有没有会被判红的合法偏差 —— **实测未发现**

- **生产者公式核对**（`as_measured.py:832-840` + `denominator.py:441-457`）：墙 `along_min/along_max = to_units(max(a.lo_m,b.lo_m)) / to_units(min(a.hi_m,b.hi_m))`，其中 a/b 的区间 = D3 组 merge 焊接后的**成员并集**；门的 `_group_along_extent` = 面线成员并集 + 同一 max/min 交叠公式 ⇒ **同式**。「同组多段因跨洞口/超 merge_m 分成多 target」的路径下，各 target 各配各墙、handles 各归各 ⇒ 门仍逐墙一致。
- **实证**（`/tmp/probe_nb_nc.py`）：真实 sm25 两视图 **107 堵墙**（F1 54 + F2 53）零 revision 逐墙过门，`const 吻合 54/53、thickness 吻合 54/53、along 吻合 54/53` —— 三个公式无一个假阳。
- **thickness**：生产者 `thickness = face_hi − face_lo` 本身是恒等式（`as_measured.py:839`），门复刻同式 ⇒ 无独立偏差面。
- **carrier_wall_ids / openings**：悬空引用已有门（`as_measured.py:446-448` `as_measured_dangling_carrier_ref`）；opening 的位置字段独立从原图实测（`_opening_records` 不从面线推导）⇒ 无「墙动洞口没动」的第二份记录；translate 不改墙 id ⇒ carrier 不会悬空。
- **R4 新恒等式**：只作用 converter_readouts 的 S1 记账（diagnostics 按 code **转运不重算**），S1 逐实体单次丢弃 ⇒ 无重复计数形态；真实两视图全绿。
- 格内 along 端点移动（不越交叠边界）门绿——这是**定义内容忍**（墙的 along 本来就是两面交叠），非缺陷；越过边界 ⇒ 红（施工方 +3000 实测、门公式保证）。

### N-c · 恒 0 的旧恒等式 —— **还在、仍全绿；判可接受**

实测：窄恒等式保留在 `_ledger_identity`（`as_measured.py:407-411`，宽恒等式 `as_measured.py:421-432` 插在它之后）且两视图全绿（F1 `223==222+1+0`、F2 `222==222+0+0`），`degenerate_in_wall_lines` 实测两视图均 **0**（恒 0 证实）。**可接受的理由**：(a) 它不是纯假绿——是「`geo.wall_lines` 内部分桶完整性」的**条件哨兵**（转换器若某天不再滤零长线，wall_lines 会出现零长段 ⇒ 它变红），R4 注释诚实声明「a real but always-empty check」；(b) 那个假绿面的**实质危害**（3 笔墨迹无声离开记录）已由宽恒等式 + itemized handles 关掉（`226==223+2+1`，13AD/13AE/13DC 逐笔点名在案）；(c) 两个新字段与恒 0 字段名字有区分度（`degenerate_line_handles`=S1 丢弃 vs `degenerate_in_wall_lines`=wall_lines 内部），无「两个名字一个东西」的混淆。`consumed_wall_handles` 确认已删（schema 无此字段 + `test_r4_consumed_wall_handles_field_is_gone`）。

---

## 五、§三 1-4 核对结论

1. **三份 json 变化**：✅ 属实。`revisions.json` 全文档字段级 diff **恰好 1 处**（`as_measured_content_sha256: d0fd263c… → e5a621a8…`），5 条真实记录（target/finding/candidate_action/verdict/action）**逐位不变**（`git show` 两版 json 递归对比）。`converter_implementation_fingerprint` 变化 = F-D 加宽指纹对**真实发生的闭包成员编辑**（`tarch_normalize.py` 删字段）的正确响应——机理成立，非意外。
2. **子集 +9 vs 全量 +13**：✅ 算术精确（+4/+8/+1=13）。「4 条 R4 自证是子集跑完后补写、未重跑子集」的过程性解释无法从单一 commit 独立复核，但与「8+1=9 在子集时已存在」自洽且全量逐位覆盖 ⇒ 采信为操作顺序疏漏，非映射缺陷。
3. **最终读数来自无干预那次**：✅ 采信。我方独立复现三方同数 3305/13/0 + 哨兵一致 + 树干净；两次作废事故施工方如实自报且未采信其结果，处置正确。
4. **R3 只改锁与措辞、豁免行为逐位未变**：✅ `gt_raw_layer.py` 的 diff 全部落在 `_expected_converter_sha256` 的 **docstring**（函数体行为行均为上下文行、无 +/−）。**锁的牙独立证实**：/tmp 副本往 `KNOWN_PRE_F_D_CONVERTER_SHA256` 塞 `"fab0fab0…"` ⇒ `test_f_d_d` 红（`AssertionError`，`test_tarch_converter_reproducibility.py:239` 的**集合整体相等**断言咬合）——上一轮同型塞法零红，边际效应从 0 条变红 1 条；git 对象溯源断言（`sha256(git show a40d56d:…) in 集合`）与 `test_f_d_d2` 自证在干净环境均绿。

---

## 六、附录：复现命令清单

| 项 | 命令/脚本 | 读数 |
|---|---|---|
| 全仓复现 | `python -m pytest -p no:cacheprovider -q -n 6` | `3305 passed, 13 xfailed, 0 failed`；`.pth` 哨兵前后同 `58f547fa…` |
| ① F-137 旧树 | `PYTHONPATH=/tmp/o21b_old python3 /tmp/probe_f137.py /tmp/o21b_old 500` | derive SUCCESS 无 raise，墙 0/2400/2400 不动 |
| ① F-139 旧树 | `PYTHONPATH=/tmp/o21b_old python3 /tmp/probe_axis_swap.py` | 报 `translate const −10`，签字后全链绿 |
| ② F-137 新树 | `PYTHONPATH=主树 python3 /tmp/probe_f137.py 主树 500` | `as_signed_wall_face_lo_disagrees…` raise |
| ② F-139 新树 | `python3 /tmp/probe_f139_new.py 主树` | `face_line_axis_changed` + `candidate_action=None` |
| ③ 第 7 种 | `python3 /tmp/probe_7th.py 主树` | A 换图层 ⇒ translate 候选零提示；B 遮蔽 ⇒ 换轴被绕过报 translate(+5) |
| N-a 灵敏度 | `python3 /tmp/probe_f137.py 主树 <1..500>`；`/tmp/probe_f137_140e.py 主树` | 1379: 1/2/4 绿 5 起红；140E: −0.2 红、+0.5 绿、±(0.1~0.9) 位置依赖 |
| N-a GROUP_QUANT 变异 | /tmp 副本 `GROUP_QUANT=2` + 零 revisions 派生 | SUCCESS ⇒ 静默证实 |
| N-b 同式实证 | `python3 /tmp/probe_nb_nc.py 主树` | 107 墙 const/thickness/along 全吻合 |
| N-c | 同上 | 窄恒等式 223==222+1+0 / 222==222+0+0 双绿；`degenerate_in_wall_lines=0` |
| R3 锁牙 | /tmp 副本塞 `fab0fab0…` 后 `pytest …::test_f_d_d…` | 1 failed（:239 集合相等断言） |
| revisions 单处变 | `git show 596258c:<json>` vs `<json>` 递归 diff | 恰 1 处（as_measured_content_sha256），5 条逐位不变 |
| F-4 stale | 纯内存探针（140E const−1 格内） | 登记仍写 159396、实际 159395 |

— GLM 跨家族审阅席位 · 2026-08-29
