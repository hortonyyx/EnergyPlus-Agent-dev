# 派工单 · **F-156**：边界环的角点改成「相邻支撑线求交」（**授权重做基线**）

- **日期**：2026-09-01 · **派工方**：orchestrator · **施工方**：**Claude 家族施工席**（2026-09-01 用户拍板派出）· **审**：**GLM 或 GPT 家族**（跨家族，⛔ 不得 Claude）
- **基线**：**`636ce56`** · **权威全量**：**3601 passed / 13 xfailed / 0 failed**（2026-09-01 主控跑，11m13s、`-n auto`、exit 0；`.pth` 哨兵前后同为 `58f547fa…` 且指向主树）<br>⚠️ **原单写的 `58bb59f` / 3519 已过期**（模块 5/6 返工 + ②-1d 返工 + NF-1 已落树）
- **前置**：[F-155 判别实验](2026-09-01_f155_ring_from_supportline_intersection_probe.md) 已跑通并经
  [主控独立核验](../verdict/2026-09-01_f155_ring_probe_orchestrator_verification.md)。
- ⭐ **本单是实现单，⛔ 不要再做一遍实验。**

---

## 一、承重前提（**主控亲手复跑的**，⛔ 请自己复核，不符就停下上报）

`AI_agent/logs/experiments/2026-09-01_f155_ring_from_intersection/probe.py` 可直接复跑：
```
TARGET plan-F1  valid=True  vertices=24  area=88.265600  expected=88.27  delta=-0.004400  interval_misses=0
TARGET plan-F2  valid=True  vertices=16  area=70.339200  expected=70.34  delta=-0.000800  interval_misses=0
HEALTHY count=25  all_baseline_edges_4=True  all_rebuilt_vertices_4=True  all_valid=True  all_interval_misses_0=True
MISALIGNED_0P1MM plan-F1 cavity:04e1293098b1a95a  alive=True  vertices=8  valid=True
```
⭐ **两条已确立的结论**：
1. **一次换表示治好了 F-153 判定的「两个不同的病」** —— 28.68 那个（病因是 0.1 mm 端点错位）**也活了**
   ⇒ ⛔ **F-153「两个病别当一个修」的结论已被推翻**（它只在**旧表示下**成立）。
2. **`interval_misses=0` + 对称差 0.000000 ⇒ 答案本来就在事实层里** ——
   腔多边形一直是对的，是 `derive_boundary_edges` 从正确源头造出了自交的环。
   ⇒ **不是补数据，是换角点算法。**

## 二、任务

1. **把 `derive_boundary_edges` 的角点改成【相邻支撑线求交】** —— 与 gt 侧 `s7_expand_zones`
   同一机制（「rebuild the zone polygon from offset support-line corners」）。
   ⭐ 探针的 `intersection_ring()` / `facts_backed_supports()` / `merge_cyclic_collinear()`
   可作**形态参考**，⛔ 但**它是探索档探针**：要用就自己重新实现并补锁，⛔ 不许整段搬。
2. ⭐⭐⭐ **盖不满就响亮失败**：任何一段边界区间在事实层墙带里**找不到支撑线**或**盖不满**
   ⇒ **响亮失败并点名**，⛔ **不许静默补线、不许取最近的线**。
3. **重做 sm25 的 staging 基线**（本单**授权**，见 §三禁令的例外）——
   ⚠️ **理由必须讲清**：`boundary_edges` 是派生值且进哈希 ⇒ **改算法必然改哈希**
   （题错 #54 的教训：不是「加字段才要重做」）。
4. **留账**：在代码里写清**为什么角点由求交算而不是由端点接** ——
   ⛔ 别在 `.py` 字符串常量里写带仓库根前缀的生产文件路径（F-152）。

## 三、⛔ 禁令
1. ⛔ **不许静默补线 / 取最近线 / 加任何距离容差**去让区间盖满（见任务 2）。
2. ⛔ **不许手改 `gt_staging/` 下任何 JSON** —— 只能由生成器重写；⛔ 不许动 `gt_sources/`。
3. ⛔ **不许签任何 revision**（5 条保持 `unsigned`）。
4. ⛔ 不许动 `src/agent/correction/` 与 `src/agent/reading/`。
5. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。跑测 **`-n 4`**。

## 四、⚠️⚠️ **跨单耦合（第三格对撞，派工方已查出，⛔ 别忽略）**

**②-1d 第二轮返工**（[单子](2026-09-01_o21d_rework2_exclusion_gap.md)）正在把那 **3 个 exclusion
登记成「已知缺陷」**。⭐ **本单会让其中至少 2 个（很可能 3 个）不再是 exclusion。**

⭐⭐ **2026-09-01 收工前更新：已实测，它【是】名单式** ——
`tests/test_o21d_exclusion_gap.py:89` 的 `test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger`
逐个断言那三个腔的登记面积。**主控已判为派工方题错 #58**（判据钉住了缺陷本身的存在），
改法写在 [②-1d 单 §九](2026-09-01_o21d_rework2_exclusion_gap.md)：拆成**规则 + 读数**两半。
⇒ ⭐ **本单施工时那条锁应当已经改好**；若还没改，**停下上报**，⛔ 别自己去改别人的单。

⇒ **两条硬要求**：
1. ⛔ **若 ②-1d 的锁把「恰好这 3 个」钉死了**，本单会让它红 ⇒ **停下上报**，由主控裁定谁改。
2. ⭐ 正确的形态应该是：②-1d 的锁量的是「**面积过阈值而进 exclusion 的必须有显式登记**」这条**规则**，
   ⛔ 不是「**这 3 个**必须在里面」这个**名单**。若你发现它写成了名单，**报出来**（那是 ②-1d 的返工点，不是你的）。

## 五、验收表（⭐ 已按**三格**对撞 · ⛔⛔ **判据一律不许用边数/loss 条数**）

> ⚠️ **题错 #57 的教训写死在这里**：上一轮把「边数变了」当成「环成立」，
> 结果 88/91 条边全部达标而环自交。**本单的判据是【环 valid + 面积对账】。**

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | ⭐⭐⭐ **两个走廊腔 + 28.68 那个：环 `is_valid=True`，且面积与 88.27 / 70.34 / 28.68 对得上**（给出 delta）| ⛔ 与「用边数当判据」对撞：**只报条数不算交付** |
| 2 | ⭐⭐⭐ **25 个健康腔逐个不变**：仍 4 顶点、**面积逐位相同**、仍 valid | ⛔ 与「治好两个弄坏二十五个」对撞 |
| 3 | ⭐⭐⭐ **`interval_misses` 全部为 0**；且**造一份盖不满的合成夹具 ⇒ 必须响亮失败**（⛔ 不许静默） | ⛔ 与禁令 1 对撞：**若你补了线，这条必然不通过** |
| 4 | ⭐⭐ **相邻支撑不垂直必须失败**：造一份夹具让两条相邻支撑平行 ⇒ 响亮失败 | ⛔ 防「求交求出个无穷远点还继续走」 |
| 5 | ⭐⭐⭐ **新旧哈希都给出来**，`revisions.json` 与 `as_signed.json` **都指向新值**、三者自洽 | ⭐ 第三格：本条**故意要求哈希变**（授权重做基线）|
| 6 | ⭐⭐⭐ **重生成机械可复现**：同一份 DXF + request 跑两次 ⇒ 三件套**逐字节相同** | ⛔ 与禁令 2 对撞 |
| 7 | 台账 5 条 revision **内容与 verdict 逐字未变**（diff 证明只有那一个哈希字段变）| 与禁令 3 对撞 |
| 8 | ⭐⭐⭐ **被读数钉死的既有断言**（`paired_edges == 100` · 那张排除清单 · `{exterior:32, interzone:68}` 等）：<br>**允许改期望数值**，但 ⛔ **每一处差异必须逐条有出处**（哪个腔从排除变配对、因此这个数从 X 变 Y）；<br>⛔ **不许改断言的结构或语义**；⭐⭐ **每条被改过期望值的锁，都要当场证明它还能红**（施加它当初针对的那个变异）| ⛔ 与「改到绿为止」对撞 |
| 9 | ⭐ **②-1d 耦合已核**（§四）：报出 ②-1d 的锁是「规则式」还是「名单式」 | 与 §四 对撞 |
| 10 | `pytest -n 4 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py`（+ ②-1d 落地后加上它的新文件）**全绿** | — |
| 11 | 列全改动路径（⛔ 不提交）| 与禁令 5 一致 |

## 六、停下上报（分层）
**必停**：§一 读数复跑不出来 · 有区间盖不满而你找不到不补线的解法 ·
②-1d 的锁是名单式（§四）· 除验收 8 授权外还有别的既有锁变红 · 任务项与禁令自相矛盾。
**只记不停**：面积末位 · 顶点数 · 错误码取名 · 环序的取法（腔提供顺序是合法的，见下）。

⭐ **关于「环序从哪来」**：F-155 施工方自报「顺序仍取自 cavity component，未证明能仅凭无序 supports 恢复」。
**主控判断（供你复核，⛔ 不是定论）**：腔多边形本身就是事实层产物，拿它定顺序**不是外部信息**；
`boundary_edges` 存在的理由是**逐边语义**（`boundary_condition` / basis），**不是形状**。
⇒ **允许用腔定序**；⛔ 但若你发现这样会引入循环依赖或别的问题，**报出来**。

⭐⭐⭐ **累计 57 次停报，57 次都是派工方的题错 —— 放心停。**

## 七、交付
代码（⛔ 不提交）+ 执行档 `AI_agent/logs/reviews/execution/<日期>_f156_ring_intersection_execution.md`，
逐条给命令+读数、**你自己认为最薄弱的一处**、希望复核方重点打哪里。

---

## 十、⛔⛔ 本轮三席同飞 —— 并发条款（2026-09-01 补，⛔ 开工前必读）

**同时在飞的另两席**（写面与你**不相交**，已由主控核过）：
- **GLM 席** = 模块 4 返工，写面 = `src/agent/correction/wall_compiler.py` + `tests/test_o22m4_wall_compiler.py`
- **GPT 席** = 模块 5/6 返工件复审（**只读** + 只写自己那份裁决 md）

⇒ **四条硬纪律**：

1. ⛔⛔ **不许跑全量**（`pytest` 不带路径）—— 别的席位正在写树，全量必假红，
   而且你自己的写树也会让它们假红。**只跑受影响子集**，路径显式列出。
2. ⛔ **并行时一律 `-n 6`**，⛔ 不用 `-n auto`（同机三路 `-n auto` 实测把全量跑崩：
   `load average 17.44 / 16 核`、worker `OSError: cannot send`、**无 summary 行**）。
3. ⭐⭐⭐ **撞到不属于你写面的红 ⇒ 先 `git status --porcelain` 看是不是别的席位在飞，
   然后【停下上报】** —— ⛔ 不许自行修、⛔ 不许写进你的 RESULTS 当作回归。
   （已实犯过三次：纯 md 提交造出的假红被记成回归。）
4. ⛔ **绝对不许跑 `pip install -e .` / 任何写 `site-packages` 的命令** —— venv 全机器共享。
   import 有问题一律走 `python -m` / pytest 入口。
   **交件前重读一次哨兵**：`sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth`
   应为 `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`，**变了即停下上报**。

**你的写面（⛔ 越界即违规）**：`src/agent/judge/as_measured.py` · sm25 staging 基线三件套 ·
`tests/test_as_measured_facts_layer.py` / `test_gt_facts_staging_sm25.py` / `test_boundary_condition_facts.py` /
`test_denominator_from_facts.py` · 你自己的执行档 `AI_agent/logs/reviews/execution/`。
⛔ **不许碰** `src/agent/correction/wall_compiler.py`、`decision_schema.py`、`decision_executor.py` 及其测试。
