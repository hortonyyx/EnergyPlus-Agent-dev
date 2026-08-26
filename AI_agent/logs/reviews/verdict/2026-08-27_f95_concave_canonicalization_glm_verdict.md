# 跨家族复核裁决 · F-95 顶点规范化收窄为「有序简单环」

- **日期**：2026-08-27　**复核席位**：GLM 家族（`glm-5.3`，worktree `/tmp/ep_f95_review` @ `ed0ba09`）
- **被审 commit**：`5b7a3a8`（施工 = GPT 家族 `gpt-5.6-sol`）
- **开工自检**：HEAD = `ed0ba09` ✅ · `AI_agent/CLAUDE.md` = 447 行 ✅
- **前置核查**：`5b7a3a8` 是 `ed0ba09` 的祖先，两 commit 之间 6 个提交只动管理文档，
  被审 5 个代码/测试文件在两 commit 间**逐字节一致** ⇒ 本 worktree 上的一切实测针对的就是被审代码本体。

## 总判：**APPROVE**

新实现正确、锁有分辨力且变红方向全部正确、契约收窄经行为验证未踩到任何真实调用方、
两条既有输出契约有独立证明、F-13 四把锁断言零改动（机械核实为纯改名）。
我自己跑的全量与本 worktree 基线逐字一致。阻断项：**0**。不阻断 findings：4 条（见下）。

---

## 一、五条验收判据逐条读数

### A1 独立全量 ✅

```
python -m pytest -q -n auto   （/tmp/ep_f95_review，干净树）
3035 passed, 13 xfailed, 211 warnings in 560.68s（9:20）   exit 0
```

与 orchestrator 参考基线（**3035 passed / 13 xfailed / 0 failed**，同 commit 主树）逐字一致。
`test_zone_agent` 缺凭据的已知环境红在本 worktree **未出现**（0 failed）——施工自述的
「3034 passed + 1 红」是其自己环境的凭据差，非代码差。

### A2 摘掉修复 ⇒ 定向变红 ✅

`git checkout 5b7a3a8^ -- src/validator/data_model.py`（复原极角排序）后全量：

```
4 failed, 3031 passed, 13 xfailed, 211 warnings in 520.22s (0:08:40)
—— 4 failed 全部在 tests/test_f95_concave_canonicalization.py（4 把保形锁），零外溢
```

（3031 + 4 = 3035，与干净树自洽。跑毕 `git checkout HEAD --` 复原，
`git diff 5b7a3a8 -- src/validator/data_model.py` = 0 行核实复原到位；
复原树上 F-13×8 + F-95×6 定向复跑 = **14 passed**。）

新锁单独跑：**4 failed / 2 passed**（7.55s），红的四把与方向：

| 锁 | 变异读数 | 方向 |
|---|---|---|
| 共享函数 U 保形 | `assert 70.0 == 76.0`（面积对不上，边集 CHANGED） | ✅ 直接命中形状损坏 |
| kernel 真实路径 Floor/Roof | `assert 65.0 == 76.0` | ✅ 命中生产路径；且同一 U 顶点集不同起点得 70/65 两个不同坏形，坐实旧 `cmp_to_key` 比较器非全序 |
| bowtie 响亮拒绝 | `DID NOT RAISE`（旧实现静默接受） | ✅ 命中收窄后的合同 |
| 双绕向/不同起点收敛 | 三份 canonical 输出不相等 | ✅ 旧实现对起点/绕向不稳定 |

变异下另跑六形矩阵工具：`sm25_corridor_14v in=97.731 out=226.457 CORRUPTED`——
F-95 头条数字原样复现；新实现下同夹具 `97.731 → 97.731` OK。

### A3 「4 failed / 2 passed」的那 2 格 ✅（不是真盲区，不触发 REWORK）

**实测**：变异下仍绿的两格是

1. `test_winding_contract_is_independently_observable_on_concave_ring`（绕向与 normal 一致）
2. `test_upper_left_contract_is_independently_observable_on_concave_ring`（起点 = UpperLeftCorner）

定性：**这两格本来就不该红**。它们锁的是**既有 IDF 输出契约**（原派工单判据 4 点名
「两条既有契约不许破」并要求各给独立实测证明的那两条），不是 F-95 的判别器。
旧实现的算法性质（极角排序以 normal 定符号 ⇒ 绕向必然随 normal；排序后再取 top-left
起点）决定了它在这两条上**本来就是对的**——4 把 F-95 判别锁（形状/路径/拒绝/收敛）
在变异下 **4/4 全红**。即：新锁对「形状被毁」这一缺陷类的分辨力没有缺口；
施工自述把它们如实归类为「非 F-95 discriminator」，与我的读法一致。
请求单预设的另一支「真盲区 ⇒ 应 REWORK」不成立。

### A4 收窄契约的行为验证 ✅（无真实路径被拒掉）

把 orchestrator 的 grep 级核查升级为行为验证，三路证据：

**(a) 调用点普查（复核 orchestrator 的「四处」）**：全仓 `grep` 复核，`src/` 内真调用恰好 4 处，
与请求单所列**同行号**：`build.py:79`（面）/ `build.py:85`（窗）/ `kernel.py:399`（窗宿主 fresh 重算）/
`data_model.py:1374`（gate① `validate_points_sorting` 的委托）。无第五处。

**(b) 输入空间审计（每个调用点的环从哪来）**：
- 墙环 = 单条边界段的竖直矩形（`_wall_verts`）；退化段（p1==p2）⇒ Newell 法向 = 0 ⇒
  被 `_canonicalize_bg_vertices` **既有的** `norm < 1e-9` 跳过（该守卫本 commit 未动）。
- Floor/Ceiling/Roof 环 = shapely `intersection/difference` 的合法多边形产物
  （`_ring_verts` 已剥闭合点；`piece.area < _AREA_MIN=0.05` 的碎片直接丢弃）。
- 窗环 = 宿主墙面矩形；零宽窗 ⇒ Newell=0 ⇒ 同一既有守卫跳过；v3 路径另有
  `_validate_window_line_inputs` 的区间守卫。
- cell 级垃圾（bowtie/重复顶点/闭合环/超短边）在**上游** `cell_polygon()`
  （`src/agent/correction/cell_geometry.py`，本 commit 未碰）就被具名 ValueError 拒掉，
  根本到不了 canonicalizer——**这一行为修前修后逐字相同**（实测见下表）。

**(c) 真实入口前后对照电池**（`build_geometry` 真入口，13 个合法对抗配置
+ 4 个垃圾输入，旧实现/新实现各跑一遍，**逐格一致**）：

| 配置 | 旧实现 | 新实现 |
|---|---|---|
| L / U / Z / 梳形 / 共线中间点（各 1 层） | OK | OK |
| **跨层错位碎片**（2F 相对 1F 偏 0.5/0.3/0.1/0.06/0.03/0.01 m——F-96 发生器） | OK（产出 w 宽 Roof/Floor 薄条） | OK（同样产出、全部接受、无重复顶点环） |
| 同层部分共边 / 仅共一角 | OK | OK |
| cell 级 bowtie / 重复顶点 / 闭合环 / 近零面积 | 上游拒（4 种具名错误） | **同样上游拒，同错同因** |

**结论：没有任何原本能跑通的路变成崩溃。** F-96 的跨层碎片（薄但简单）修前修后都流过；
退环（重合点/零面积）在内核层从来是被 Newell 守卫**跳过**而非「悄悄修好」，共线三点
修前修后**都接受**（实测，见 §3.3）。行为差只出现在**手喂非简单环**的一格：
旧 = 静默产出坏环（bowtie 被排成某个自交环进 IDF），新 = 具名响亮拒绝——这正是本单要的收窄。

### A5 F-13 四把锁逐行核 ✅（断言零削弱）

机械核实：对该文件 diff 的全部 +/- 行做过滤，
**每一条改动行都只含 `scrambled`→`ordered_different_start` 的改名，无任何其他字符变化**
（`grep -vE 'ordered_different_start|scrambled'` 后增删行为零）。四把锁本体
（lock1 真实入口恒等锁 / lock2×4 形状 / change-counter / neuter）断言一个未动，
随全量绿。自述「只把变量名改了，断言一个没动」与 diff 逐字相符。

---

## 二、§三四处重点的实测结论

### §3.1 「4 failed / 2 passed」的 2 格 → 见 A3。**不是真盲区；是既有契约锁，旧实现在其上本就正确。**

### §3.2 收窄是否踩到真实调用方 → 见 A4。**未踩到；证据为行为级（真入口前后对照电池 + 四调用点输入空间审计），不再是 grep 级。**

### §3.3 非简单环判定会不会误拒 → **误拒余量实测 = 0 宽度**（只在「数学上真退化」的精确边界上拒）

先答「数值容差是多少」：重复顶点判定用 `np.unique` **精确相等，无容差**；
简单性判定委托 GEOS 鲁棒谓词（无可调 epsilon）；`area == 0.0` 精确。实测带余量：

| 输入（合法正交环方向） | 读数 |
|---|---|
| 两角点相距 1e-3 / 1e-9 / 1e-15 / **5e-324**（最小非规约数）/ 1 ulp | **全部 ACCEPT** |
| 精确相等（真重合） | REJECT（刀口） |
| 拐角共线中间点（精确共线 + 1e-9/1e-6 偏出） | **全部 ACCEPT**（共线三点不误拒） |
| 合法 U 环平移 +1e3 / +1e6 / +1e7 | ACCEPT，顶点集保持 |
| 竖直墙环（丢轴投影路径）近重合角点 | ACCEPT |
| T 形接触（顶点落在非邻边内部——真非简单） | REJECT（正确拒绝） |
| GEOS 判 valid 但含精确重复点的环 | REJECT（`np.unique` 先于 shapely 触发）——见 finding N2 |

**不存在「浮点末位重合的合法环被判自交」的带状误拒区**：从 1 ulp 到最小非规约数全接受，
拒绝只在精确重合这一数学退化点上发生。同族教训（重算门偏 1.480 px 误判诚实产物）的形态
在本实现里**结构上不存在**——因为这里没有「重算一个带容差的量与自报值比对」，只有
「精确退化判定」。投影丢弃轴亦核过：`argmax|normal|` 轴与环平面内积 ≥ 1/√3 > 0，
对任意平面环是单射投影，不会制造伪自交。

### §3.4 F-13 四把锁 → 见 A5。**纯改名，断言零改动（机械核实，非目测）。**

---

## 三、Findings

### 阻断（0 条）

无。

### 不阻断（4 条）

- **N1（残余理论窗口，建议随 F-96 一起处理）**：四个调用点里唯一理论上能喂出
  「GEOS-valid 但含精确重复顶点」环的，是 shapely `intersection/difference` 产物自身带重复坐标。
  13 配置电池（含全部 F-96 碎片宽度）未触发；GEOS 节点吸附通常会合并重合节点。即便发生：
  旧实现的输出同样是带重复顶点的环直进 IDF（对 EP 而言一样坏，只是静默）。建议登记到
  F-96（跨层碎片）名下一起守卫，不单独开工。
- **N2（判据分层不一致，知悉即可）**：新实现的「非简单」外延与 GEOS 的 `is_valid` 外延
  在「精确重复顶点」一格**不相交**（GEOS 判 valid+simple，实现拒之）。这是**收窄合同的
  合理从严**（重复顶点环对 IDF 本就非法），但意味着「Shapely 说合法」不再蕴含「本函数接受」。
  已由 N1 说明真实路径不产此形态。
- **N3（分类学债，极小）**：`classify_ring_change` 的 `"resorted"` 类别在新合同下生产侧
  永不触发，docstring 已如实标注「保留为历史诊断类」。未来有人给 `GeometrySchema` 接
  非内核生产者时需重读此合同（现无此调用方，见 A4 普查）。
- **N4（环境差备忘）**：施工方 worktree 全量「3034+1 红（缺 API 凭据）」与本 worktree
  「3035/0 红」的差异为环境凭据差，非代码差；两个数都与其各自环境自洽。

---

## 四、orchestrator 题面的问题（按请求单 §六要求逐条）

1. **§3.2 的前提句与事实有出入（结论不受影响）**：题面把退化环的旧状态写成「被悄悄修好」。
   实测：重合点/超短边在 **cell 层**从来是被上游 `cell_polygon` **响亮拒绝**（非悄悄修好），
   在**面层**是被 Newell 守卫**跳过**（也非修好）；共线三点则修前修后**都原样接受**。
   即：这些形态从未走过 canonicalizer，「收窄」对它们的答案是「无路径变化」，
   而不是「从静默修复变成拒绝」。
2. **§3.3 预设了「数值容差」存在**：实测答案是**没有容差**——重复顶点判定是精确相等，
   简单性判定委托 GEOS 鲁棒谓词。因此「误拒余量」的正确量纲是「拒绝仅在精确退化点发生
   （零宽度带）」，而非某个 epsilon 数值。题面若先问「有没有容差」会更准。
3. **§3.1 的措辞「2 passed = 新锁抓不住的两格」是误导性框定**（题面自己也列了另一种可能，
   故不算错）：这两格锁的是既有输出合同，旧实现构造上就满足，**不存在「该抓而没抓」的破坏**。
   把它们计入「锁的分辨力分母」会低估分辨力（F-95 判别锁 4/4 全红）。
4. 其余核查过的题面事实（diff 范围 7 文件/+531−66、四处调用点及行号、sm25 97.731→226.457、
   自述含「4 failed / 2 passed」原句、范围清单抄自 `git show --stat` 的自首）**全部与实测相符**。
   主动作废「范围一致性」判据的处置得当——顺带信息性对照：diff 恰好落在原派工单允许清单内，
   禁碰清单零触碰。

---

## 五、附录：实测命令与原始读数

```
# A1 全量（干净树）
3035 passed, 13 xfailed, 211 warnings in 560.68s (0:09:20)   EXIT=0

# A2 变异全量（git checkout 5b7a3a8^ -- src/validator/data_model.py 后）
4 failed, 3031 passed, 13 xfailed, 211 warnings in 520.22s (0:08:40)
（4 failed = tests/test_f95_concave_canonicalization.py 的 4 把保形锁；零外溢；跑毕复原）

# 复原后定向复跑:  tests/test_f13_* + tests/test_f95_* → 14 passed in 10.77s

# 新锁单文件（变异下）:  4 failed, 2 passed in 7.55s
# 六形矩阵（新实现）:    all ordered simple rings preserved; non-simple ring rejected
#                        sm25_corridor_14v  in=97.731 out=97.731
# 六形矩阵（变异下）:    6 failure(s): U_two_reflex, comb_three_reflex, U_reverse_winding,
#                        U_different_start, sm25_corridor_14v, bowtie_non_simple_accepted
#                        sm25_corridor_14v  in=97.731 out=226.457 CORRUPTED
# gate① 入口喂 bowtie:   ValidationError wrapping
#                        canonicalize_ring_vertices.non_simple_ring … reason='Self-intersection[1 1]'
```

（探针脚本与过程文件已按约清理，worktree 交件时 `git status --porcelain` 除本裁决文件外为空。）
