# ②-1b-S 跨家族审裁决书（GLM · = 提出「丙」方案的同一席位）

- **日期**：2026-08-29 · **审阅方**：GLM 家族（glm-5.3）· **请求书**：[`../request/2026-08-29_o21bS_crossreview_glm.md`](../request/2026-08-29_o21bS_crossreview_glm.md)
- **送审对象**：`22202c1`，基线 `947d0c2`，一律以 `git diff 947d0c2..22202c1` 为准（14 文件 / +1290 −91，已核对）。
  当前 HEAD `ed2e3d4` 相对送审对象**只差 3 个文档文件、src/tests 零改动**（`git diff 22202c1..ed2e3d4 -- src/ tests/ | wc -l` = 0），故全部探针在当前树上跑、旧侧在 `git archive 947d0c2` 的 `/tmp/o21bS_old` 副本跑（`PYTHONPATH` 隔离 + `__file__` 自证未串台）。
- **方法**：所有 RESULTS 独立重跑；每道新门独立构造红侧输入验证有牙（不是只看测试绿）；引用行号全部回文件 `grep -n` 核过；neuter/合成 DXF 只在 `/tmp` 做；未动主树任何文件（本裁决书除外）、未 git commit、未 `pip install -e .`。
- **A1 负样本的构造方式**：拿真实 as-received DXF 的 `/tmp` 副本，往 **WALL 层**画真斜线（改两重哈希后走 `build_as_measured` 完整端到端，非单元级模拟）。

---

## 裁决：**APPROVE-WITH-FINDINGS（阻断 0 条）**

丙方案的机制件全部按单兑现且实测成立：吸附代替丢弃、决策 itemize、守恒式自证有牙、F-D 处置诚实、R5 三件各有变异方向证明。**请求书点名的「不该吸却被吸」负样本本席已构造出来并端到端落地为一条虚构正交墙**（F-1，本裁决书头号 finding）——但它证明的是**绝对距离阈值这个形状的固有风险**，不是本单实现的缺陷：实现忠实执行了派工单、阈值已按单停下待签、在现有全部语料上零实害。它应当作为**用户签字 `AXIS_SNAP_MAX_DEVIATION_M` 时的必读证据**（§五），不构成返工理由。

读数复核先行：**全仓独立复现 `3323 passed / 13 xfailed / 0 failed`**（`python -m pytest -p no:cacheprovider -q -n 6`，958.53s，exit 0），与主控权威门**逐位同数**；`.pth` 哨兵跑前跑后同为 `58f547fa9433…`；工作树跑前跑后皆空；HEAD 未动。主控实测四行全部独立复现同数：as-received F1 `face_lines=224 · walls=55 · axis_snapped=['13AD','13AE'] · s1_discarded=[] · 13AF 在 non_orthogonal_lines · thickness={1200:28, 2400:27} 与签字件逐位一致`；F2 两侧 `222/53`。

---

## 一、阻断（0 条）

无。

---

## 二、不阻断 findings

### F-1 ·【⭐⭐ 头号 · = 请求书 A1 要的负样本】「不该吸却被吸」**端到端成立**：一堵真的斜墙被掰成一条图上不存在的正交墙（walls 55→56）

**构造**（`/tmp/negsample_diagonal.dxf`：真实 as-received DXF 副本的 WALL 层加三条线，request 副本重算 `source_dxf_sha256` + `request_sha256` 后走完整 `build_as_measured`）：

1. **N1 · 一堵真斜墙的两个面**：两条平行斜线，各长 800mm、歪 5.5mm（**0.39°**），名义间距 120mm；
2. **N2 · 一条短而明显斜的线**：60mm 长、歪 5mm（**4.76°**，图上肉眼明显斜）；
3. **N3 · 45° 对照**（500×500mm）。

**实测**：

```
face_lines 224 → 227   walls 55 → 56   openings 31 → 31
axis_snapped = ['13AD','13AE','194E','194F','1950']   ← N1 两条 + N2 全被吸
s1_discarded = ['1951']                                ← N3 45° 正确拒绝
NEW-WALL w_x_256690_257890_316690_324690 lo=['194F'] hi=['194E'] thick=1200   ← 虚构墙
thickness {1200:28,…} → {1200:29,…}   ← 120mm 墙多出一堵，图上不存在
NEW-FACELINE 1950 axis=x const=247889 along 324690→325290               ← 4.76° 短线被掰正进面线层
```

**定性**：这就是「把一条真的斜线掰成一堵图上不存在的正交墙」——本项目 33 条虚构墙病根形状的完整复刻，且**两条平行短斜线各自吸到中点后恰好保持 120mm 间距、顺利配对成墙**（中点方案反而帮了倒忙）。它与 33 条虚构墙那次的本质区别：每条吸附都有 `tarch_wall_axis_snapped`（INFO）itemize + ledger 锁 + 阈值显式标注待签——**不是静默虚构，是显式记录的、等人签字的决策面**。当前语料（3 份图、非正交线仅 13AD/13AE 两条）上零实害；但签字材料必须写明：**签多大，多大以内的斜线就会这样进答案**。
**配套数字**（绝对距离阈值的角度含义随线长漂移 **128 倍**）：

| 线长 | 6mm 占位下最大可吸角度 | 10mm 建议下 |
|---|---|---|
| 3640mm（=13AD 的长度） | 0.09°（≈ 真实手抖 0.0914°，合理） | 0.16° |
| 120mm（本语料最短墙头之一，13AF 即此长） | 2.87° | **4.78°** |
| 60mm | 5.74° | **9.59°** |
| 30mm | 11.54° | **19.47°** |

单元级实证（`tests/test_tarch_converter_p1_geometry.py::_collect_with_snap_threshold` 借用）：`dy=9mm` 线在 6mm 占位下拒绝、10mm 建议值下被吸；`60mm 线歪 9.5mm(9.5°)` 在 10mm 下被吸进 wall_lines。

### F-2 ·【= A5】验收 1「222→225」与验收 6「sm25 变 drift」两条题错**确系结构性不可能**，施工方的判断成立——且不存在「双方都没想到的正路」

- **① 225 上限是 224**：实测 13AF 原生 `dx=0.1915mm dy=119.9998mm`，`dx < tau_axis(1mm)` ⇒ **根本不进「两腿都超」的 S1 分支**（`tarch_normalize.py:493`），吸附机制对它不存在。量化后 `p0=(-25228.9, 38279.5) p1=(-25229.1, 38159.5)`，**x、y 两轴格点都不齐** ⇒ 落 `_face_line_records` 的 `non_orthogonal_lines` 桶（as_measured 侧的量化后判定）。要收它必须动那个桶——请求书 §四 已显式划出范围。⇒ 在派工单范围内 224 就是上限。
- **② sm25 恒 `reproduced`**：四条 fatal 指纹通道逐一核过——`converter_sha256` 被豁免判死（`gt_raw_layer.py:464` `recorded in KNOWN_PRE_F_D` ⇒ 返回 recorded ⇒ `recorded==recorded` 恒真）；`judge_config_sha256`/`vg_config_sha256` 对比当前配置（本单未碰，且碰配置 = 另一个签字面）；`vg_implementation_sha256` 闭包 = correction 四模块（`gt_schema.py:748`，实测 sm25 signed==current，本单未碰）。实测本单闭包改动（真实翻转了 widened 指纹）下 sm25 仍 `reproduced / drifted=()`、sm24 `implementation_drift / drifted=('converter_sha256','vg_implementation_sha256')`（后者含 correction 四模块的历史漂移，非本单引入）。**唯一能让 sm25 报 drift 的「做法」是故意改 judge_gt.yaml 或 correction 模块制造假漂移**——与「不许往豁免集合塞值糊过去」同型的糊弄，不是路。⇒ 判断成立。
- **验收 1/6 判 ⚠️ 部分达成是正确读数**，两处停下上报的处置（如实报告差异而非凑数）正确。⚠️ 顺带给主控提一句：as-received F1 的 224 vs 签字件 225 的差（13AF）是**结构性永久差**，重签前每次对账都会出现，别再当回归追。

### F-3 ·【证据形式】验收 2「plan-F2 逐位不变」的施工方证据形式上无牙——本席用新旧树对照补证，结论成立

施工方引用的 `f2_a == f2_s` 比较的是 **as-received F2 vs signed F2 在同一份新代码下**的相等——而 F2 两侧本来就相同，吸附开不开它都绿（门在夹具无存货的方向上无牙，请求书 A1 预警的同型）。真正能证明「吸附没动 F2」的是**基线代码跑的 F2 vs 新代码跑的 F2**：本席用 `git archive 947d0c2` 副本对照实测，**唯一差异 = 新增空字段 `"axis_snapped_lines": []`**（逐字段递归 diff，几何零变化）。验收 2 实质通过，但通过的证据是本席的对照，不是施工方那条测试。

### F-4 ·【表述校准】「10mm 与 6mm 在现有语料上影响相同」为真但容易被读过头

正确部分：现有语料唯一正样本 5.8084/5.8087mm，两个阈值下吸附清单同为 `['13AD','13AE']`，逐位同。但两阈值**并非处处等价**：(6,10]mm 窗内的线行为翻转（F-1 的 `dy=9mm` 实测：6mm 拒 / 10mm 吸）。签字材料应表述为「现有语料上等价、边界外 4mm 窗行为不同」，⛔ 不写「影响相同」了事。

### F-5 ·【记账面】G2 守恒记账发生在吸附之后的坐标上——原始坐标只活在诊断 context 里，仍可审计，不阻断

`tarch_normalize.py:521-525` 的 `source_x/source_y` 记账用的是吸附后的 `sx/sy`，故一条歪 5.8mm 的线吸附后两 y 同值、量化同格，G2 的「不许合并相距 > tau_node 的坐标」检查**看不到吸附前的原始差**。可接受的理由：G2 的语义是「量化这一步不许合并」，吸附是显式 itemize 的另一机制（合并发生在量化之前、由 R3 的 ledger 守恒式管账），且原始坐标完整活在 `tarch_wall_axis_snapped` 的 `before_p0/p1`（已实测 13AD before=[52401,100659]→[88800,100601]）。一句话：不是绕过，是分了账——但这个分账关系值得一句 docstring（现无）。

### F-6 ·【A2 配套实测】中点选择在真实样本上完美，反向歪斜下墙厚 +minor 是吸附本身的代价（非中点特有）；偶格中点会再偏 0.05mm

- **实测 13AD/13AE**（真实手抖形状=两面同向同幅歪 5.81mm）：中点 `100630 / 99430`，间距 = **恰好 1200 单位 = 120.0mm 名义墙厚，逐位保持**；沿墙区间 `[52401, 88800]` 吸附前后逐位相同（长腿端点不动）；**openings 31→31、零条内容变化**（洞口位置独立从原图实测，不受吸附影响）——A2 三问全部独立核实通过。
- **变体计算**（`_snap_short_leg_to_axis` 直测）：**反向歪**（A 升 B 降各 5.8mm）下中点间距 = 125.8mm（**墙厚被吸厚 5.8mm**）；保 p0 反向歪同样 125.8mm；保 p0 只在「两面绘制方向一致且名义位都在 p0」时保持——**没有任何选择在反向歪下保持墙厚，中点是唯一不依赖 DXF 绘制方向的选择**。施工方「中点=唯一对称解」的论证成立，本席维持。
- 理论小项：两端点之和为奇（0.1mm 单位）时中点落两格之间，量化（banker's round）再偏 ≤0.05mm——13AD/13AE 实测无此形态，登记不阻断。
- 墙厚扰动上界（签字材料用）：中点吸附对墙厚的最大扰动 = **±minor_leg**（两面反向歪最坏）；6mm 阈值下最坏 ±6mm（120mm 墙的 5%），10mm 下 ±10mm（8.3%）。

### F-7 ·【顺带核实，非新 finding】其余各面

- **A3 三门独立构造红侧**：删吸附清单一条 ⇒ `as_measured_axis_snapped_ledger_broken` 红；清单 handle 悬空（合法格式 'FFFF'）⇒ `as_measured_axis_snapped_not_a_face_line` 红；同 handle 双记 ⇒ `as_measured_axis_snapped_also_discarded` 红。清单完整性 = 真实 as-received 恰 `['13AD','13AE']`（`test_o21bs_the_real_snap_list…` 亦绿）；「被吸过 vs 本来就正」在产物上分得开：signed F1 清单 `[]`、as-received F1 `['13AD','13AE']`，被吸面线本身在 face_lines 里无标记、区分信息全在清单（这正是 R2 的要求形态）。
- **R5 抽核 6 条全绿**（F-141 换层/跨视图、F-140 活耦合+红侧钉、F-142 刷新/清空），F-141 的变异方向测试（`test_detect_layer_swap_reproduces_pre_fix_without_the_layer_comparison`）以「重建 pre-fix 比较逻辑 + 断言该形状必产 translate 前提」的方式成立。
- **豁免集合零改动**：`git diff 947d0c2..22202c1` 中 `KNOWN_PRE_F_D` 相关 0 行；集合相等断言两条测试绿（有牙性 ②-1b-R 已证，本单未改 `gt_raw_layer.py`）。
- **验收 9**：diff 不含任何 `request*.json`；`compute_request_sha256` 对两份 request 重算 stored==computed 均 True。
- **gt_staging 三份 json**：字段级 diff = `converter_implementation_fingerprint` 1 处 + views 内条目（新增吸附清单 2 条 + face_lines+2/walls+1 及其排序移位），与执行记录自洽。
- 施工方阈值分布表（三份图穷举、非正交线全局仅 2 条）与「sm21 结构上不走转换器」本席从 `UNSIGNED_ANCHORS` 定义侧面采信。

---

## 三、A1–A5 逐条结论

| 攻击面 | 结论 | 处置 |
|---|---|---|
| **A1** 不该吸却被吸 | **找到了，端到端落地**（F-1）：0.39° 斜墙 → 虚构墙 walls 55→56；4.76° 短线进 face_lines；45° 正确拒绝。定性=阈值形状固有风险，非实现缺陷；现有语料零实害 | 归 §五签字材料必读；建议双门限 |
| **A2** 中点 vs 保端 | 施工方判断**成立**（本席独立核实三点 + 反向歪变体）：中点=唯一不依赖绘制方向的选择；真实样本墙厚逐位保持、沿墙区间逐位不动、洞口零变化。反向歪 ±minor 是吸附固有代价（F-6），随阈值一并给用户知情 | 维持；墙厚扰动上界写进签字材料 |
| **A3** 清单/守恒/可区分 | 三门独立构造红侧全响；清单完整；产物可区分（F-7） | 通过 |
| **A4** F-D 四项 | sm25 恒 `reproduced`（豁免=recorded==recorded，逻辑+实测双核）；sm24 正确 `implementation_drift`（converter_sha256=本单真实翻转）；豁免集合 diff 零改动；集合相等断言咬合 | 四项全部独立核实 |
| **A5** 两条题错 | **均结构性不可能，施工方判断正确且无第三条路**（F-2：13AF 不进 S1 分支属范围外机制；sm25 四条 fatal 通道唯一可动的已被豁免判死，制造假漂移=糊弄） | 验收 1/6 判「部分达成」是正确读数 |

---

## 四、裁决理由小结

本单是丙方案（本席上一轮提出）的施工。丙的三件配套——itemize、守恒式、先补锁——全部到位且有实测的牙；两处与验收字面不符的地方（225/drift）经本席独立核实均为派工方题错而非施工缺陷，施工方两处停下上报、如实报告差异的处置符合纪律。头号风险（不该吸却被吸）不在代码里、在**待签字的阈值形状里**：代码忠实执行任何签字值，签错形状（绝对距离单门）就会把 F-1 的演示变成未来某张图上的真实虚构墙。故 APPROVE-WITH-FINDINGS、0 阻断、阈值意见如下。

---

## 五、§三 阈值意见（⛔ 本席不拍板，供用户签字）

### ① 10mm 作为唯一绝对阈值：对长线成立、对短线不成立

- 成立的一面：正样本 5.81mm × 1.7 边际；10mm < 最小声明墙厚 120mm 的 1/12；现有语料 (6,10] 窗空载。
- 不成立的一面（F-1 实测）：绝对距离不随线长缩放，10mm 下 **120mm 短墙头可被吸至 4.8°、60mm 至 9.6°、30mm 至 19.5°**——图上明显斜的短线会被掰正，且两条平行短斜线会配对出完整虚构墙。本语料 120mm 级墙头真实存在（13AF 即 120mm），短不是假设。

### ② 别的标定路径（按本席推荐顺序）

1. ⭐ **双门限：绝对距离 AND 角度**（`minor ≤ D 且 atan2(minor, major) ≤ θ`）。在本席全部样本上分类正确的取值：**D=10mm、θ=0.25°**——放行 13AD/13AE（0.0914°，×2.7 边际），拦下 0.39° 缓斜墙演示与一切 4°+ 短线；绝对门继续兜住「短线手抖角度过敏」的角度短板，角度门兜住「长线缓斜」的绝对门短板。缺点：θ 的 0.25° 没有第二个数据点支撑（n=2），本质是**结构性防御而非数据标定**，须向用户如实说明。
2. **从声明墙厚模数推**：墙厚扰动上界 = minor（反向歪最坏，F-6），令「扰动 ≤ 最小声明墙厚 × 系数」：系数 1/20 → 6mm（=现占位）、1/12 → 10mm（=建议值）。优点是随未来建筑墙厚模数自动缩放（对齐不变量 #6）；缺点是只管墙厚扰动面、管不住长线缓斜墙。
3. **同族线一致性**（同一堵墙两面的歪应同向同幅）：拦得住「只有一面歪」的错吸，**拦不住两面同向同幅的真斜墙**（F-1 的 N1 恰同向同幅，会骗过它）——只配当辅助信号，不配当主判。
4. **纯角度/线长归一化**（单用）：120mm 线歪 2mm 就 0.95°，θ 取 0.25° 会拒绝真实手抖——单用对短线过敏，只能与绝对门联用（即路径 1）。
- 无论签哪个：**吸附清单在人签 revisions 时逐条过目**（R2 的 itemize 已把 before/after/短腿量全放盘上，成本一次目视）——这是最后一道也是最便宜的一道闸。

### ③ 占位期（6mm 待签）风险面

- 任何新图/重跑落在 (1, 6]mm 的线**自动吸、无人工过目**（清单只 itemize 不拦截）；sm24 重跑与 sm25 走查必须把 `axis_snapped_lines` 列为必查项（好在这两份图今天该清单为空，施工方分布表已穷举）。
- 阈值是模块常量（`tarch_normalize.py:130`），**改值即再翻闭包指纹** ⇒ sm24 再 drift、gt_staging 再生。建议**签字时点与下一次重签/走查合并**，避免两次翻转两次重跑。
- 阈值不进 `judge_gt.yaml` 的理由（该 schema 序列化形态烤进已签 gt.json 的 content hash，加字段即 `gt_hash_content_mismatch`）本席从施工方实验记录采信——将来若要进 yaml 必须走重签，这条约束应写进签字件。

---

## 六、附录：复现命令清单

| 项 | 命令/方法 | 读数 |
|---|---|---|
| 全仓独立复现 | `python -m pytest -p no:cacheprovider -q -n 6` | `3323 passed, 13 xfailed, 0 failed`，958.53s；哨兵前后同 `58f547fa…`；树前后皆空 |
| 主控四行复现 | `build_as_measured(as-received/request_as_measured.json)` 读 view 计数 | F1 224/55/`['13AD','13AE']`/13AF 在 non_ortho；F2 222/53；thickness 与签字件逐位一致 |
| F-1 负样本 | `/tmp/negsample_diagonal.dxf`（WALL 层 3 线）+ 重算双哈希的 request 副本 → `build_as_measured` | walls 55→56（`w_x_256690_257890_316690_324690`），face_lines 224→227，45° 对照被拒 |
| F-2 ① | ezdxf 读 13AF 原生端点 + `_quantize` 直算 | dx=0.1915<tau_axis 不进 S1；量化后两轴都不齐 → non_ortho 桶 |
| F-2 ② | `verify_raw_layer_reproduction` 两 case + `gt_schema.py:748` 闭包定义 | sm25 `reproduced`/`()`, sm24 `implementation_drift`/`('converter_sha256','vg_implementation_sha256')` |
| F-3 新旧树对照 | `git archive 947d0c2` → `/tmp/o21bS_old`（PYTHONPATH 隔离）跑 F2 vs 新树 F2 递归 diff | 唯一差异 `axis_snapped_lines: []` |
| F-4 单元实证 | `tests/…p1_geometry.py::_collect_with_snap_threshold(2000, 9, …)` | 6mm 拒 / 10mm 吸；60mm 歪 9.5° @10mm 吸 |
| F-6 | `_snap_short_leg_to_axis` 直测同向/反向歪 | 同向 120.0 保持；反向 125.8（+5.8） |
| A3 三门 | `AsMeasuredV1.model_validate` 对删条/悬空/双记的构造输入 | 三种构造输入各响亮红（`…ledger_broken` / `…not_a_face_line:['FFFF']` / `…also_discarded:['13AD']`） |
| R5 抽核 | pytest 6 条（F-141×2 / F-140×2 / F-142×2） | 6 passed |
| 豁免集合 | `git diff 947d0c2..22202c1 -- src/…/tarch_normalize.py \| grep -c KNOWN_PRE_F_D` | 0 |
| 验收 9 | `compute_request_sha256` 对两份 request 重算 | stored==computed 均 True |

— GLM 跨家族审阅席位 · 2026-08-29
