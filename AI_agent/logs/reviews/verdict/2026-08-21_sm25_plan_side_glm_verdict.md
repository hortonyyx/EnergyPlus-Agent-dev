# 交叉审阅裁决 · sm25 平面侧三修 + 跨层轮廓比较（GLM 审 GPT 施工）

- **日期**：2026-08-21 · **审阅席**：GLM `glm-5.3` · **施工席**：GPT `gpt-5.6-sol` · **审阅对象**：提交 `6589943`
- **依据**：原始请求书 · `git diff 6589943^..6589943` · 本席自跑测试/探针输出（施工席与主控自述一律未采信）
- **判定**：**REWORK**（1 MAJOR 违反唯一硬回归红线 + 1 MAJOR 点名隐患成立；无 BLOCKER——三修本身全部有效，七把锁全部真实）

---

## 〇、一句话结论

三处修法本身我逐把 neuter 验过、全部真实有效，容差零放水，§2.2 的「自证循环」担忧**不成立**（断言单元级可红、输入层无静默窗口）；但本提交**附带了一处请求书未声明的行为变化**（`covers` 判据），它加上 face-pair 的证据归因抢占，共同造成 **sm24 重建产物 76 处字段漂移**——「sm24 逐字段不变（L1）唯一硬回归红线」在字段层面被破坏（几何内容零漂移）。现有 2946 把锁**全部漏抓**这个漂移，因为没有任何锁做跨版本产物比对。

---

## 一、§2.2 专门结论（请求书标注 BLOCKER 级检查项）

**结论：不构成 BLOCKER。断言能真的红；「墙带说 240、几何上那儿没有面」在输入层无静默窗口。但必须如实记录一个事实：这条「独立几何断言」在活链路上结构性恒真，真正的防线是 S4/G8 等其它层。**

三层证据：

1. **单元级可红（neuter N4 实证）**：把 `_face_pair_exit_is_supported` 摘成恒 `True`，
   `test_face_pair_binds_t_junction_to_240_and_geometry_assertion_is_live` 后半（挪 146E 后
   `assert not ...`）立刻红，且**零连带**（62 绿）。断言不是装饰性回声。

2. **活链结构性恒真（诚实记录，非缺陷定性）**：binding 由 `_face_pair_binding_for_edge`
   从 `face_pairs`（同一份 `wall_lines` 构建）产生，断言用**同一份不可变 `wall_lines`** 按
   handle 重读。同数据下 `predicted_far = near_coord + normal·t` 与 `far_coord` 必然一致
   （t 就取自这两条线）。N4 neuter 零连带恰恰证明：正常数据下这条断言不改变任何行为。
   它防的是 pair 构建/binding 的**簿记 bug**（记录与源不一致），不是输入几何分歧——
   原设计「射线观测 vs 墙带证据、两者不符报 unevidenced」的那种独立性，在 face-pair
   路径上确实不存在（射线值被静默替换、无对比断言）。

3. **输入层无静默窗口（活链实验，本席独立跑）**：把对面面线 146E 在 **/tmp 拷贝**上挪开
   （0.1 / 0.5 / 1.5 / 60 mm 四档，anchor 原件未动），重跑真实 F2 转换，四档**全部**：
   `tarch_wall_free_end`（BLOCK，dangle）+ G4/G5/G8/G9 红。「pair 说 240 但那儿没有面」
   在真实图上**无法静默产生**——挪任何 ≥0.1mm 的量先断拓扑；即使拓扑不断（合成情形），
   donor 借值与射线实测的分歧会由 G8 独立重建门暴露（N1 neuter 下 sm24 exit-gate 断言
   G8 symmetric_diff==0 变红即其分辨力实证）。厚度值每轮从两条真实源线实测（N1 neuter
   证明值不来自 request 区间），源动值必动，无烤死值。

⇒ 两条 BLOCKER 判据（「断言不能真的报红」「分歧永远不可能现形」）**均不成立**。遗留事项见 F3。

---

## 二、neuter 结果表（§2.1 七把锁，全部本席自做；自证前提：未扰动 7/7 绿，实测 15.4s）

| # | 锁 | neuter（摘掉的生产行为） | 目标红 | 连带红（全部同特性） | 还原自证 |
|---|---|---|---|---|---|
| N1 | face-pair 正例 240 来自线距 | `thickness_native=(t_min+t_max)/2` | ✅ `reads_real_240` 红 | `binds_t_junction`+`sm25_f2`+sm24×6（见 F1/F2 机制） | md5 OK |
| N2 | 跨度重叠守卫 | 删除 `hi-lo<=tau` 分支 | ✅ `requires_positive_along_wall_overlap` 红 | 同 N1 模式（9 红） | md5 OK |
| N3 | T 接头 240 绑定 | `_face_pair_binding_for_edge` 恒 None | ✅ `binds_t_junction` 红 | 仅 `sm25_f2`；**sm24 全绿**（F2 的反证） | md5 OK |
| N4 | 挪 146E 出口断言必红 | `_face_pair_exit_is_supported` 恒 True | ✅ 同测试后半红 | **零连带**（§2.2 证据） | md5 OK |
| N5 | 真实 sm25 F2 目标边 240 | `run_p2_conversion` 不传 `wall_line_layers` | ✅ `sm25_f2` 红 | 零连带 | md5 OK |
| N6 | 非凸凹口外窗判外 | `min(distances)`→`distances[0]`（回退单面） | ✅ `nonconvex...locally` 红 | `sm24_exit_gate_openings_21`×1（同分类逻辑） | md5 OK |
| N7 | 跨层轮廓 500mm 必红 | 距离比较删除（保留顶点数检查） | ✅ `must_red_for_one_vertex_shifted_500_mm` 红 | 零连带 | md5 OK |

每把 neuter 后 `md5sum -c` 四个生产文件全部 OK + `git status` 与开工快照逐字节一致（零残留）。

---

## 三、逐条 finding

### F1 · MAJOR · `covers` 浮点误判 → sm24 六条纯外轮廓边被误发射 → 唯一硬回归红线（字段层）被破坏

**这是请求书未声明的第四处行为变化**（缺陷表只列三处；diff 里 `_append_plan_geometry` 的
GTV3_ZONE 发射条件从「仅 wall_axis」改为「outer_skin 且不被 `footprint.exterior.covers()`
覆盖」）。

**实跑证据链（全部本席自跑）**：

1. 跨版本 sm24 重建（同 fixture request + zone_roles，`build_review_bundle` 全链）：

   | 产物 | `6589943^`（改动前） | `6589943`（本提交） |
   |---|---|---|
   | gt.json `content_sha256` | `2ef32cf1…` | `e478f217…` ❌ |
   | gt.json 文件 sha | `b12a18e6…` | `178d5dca…` ❌ |
   | GTV3_ZONE 线数 | 19 | **25** ❌ |
   | 结构化 diff | —— | **76 处叶子字段不同**：8 个 zone 的 `source_refs` 条目数变（6→8、5→6、7→9…）+ 全部 zones/openings 的生成句柄漂移 + 3 处 generator 溯源 hash |

2. 几何内容**零漂移**：diff 中不包含任何 zone 环顶点、opening 矩形、footprint 变化；
   诊断集、门结果全同。变化的只有生成图元句柄/条目与溯源字段。

3. **根因是 `covers` 原语误判，不是设计必需**：sm24 六条被新发射的边全部是
   `distance(exterior, edge) == 0.000000000` 但 `covers == False`（本席在活转换内逐条打印）。
   sm24 是凸矩形，没有任何 re-entrant 延伸边；这六条是纯外轮廓边，被共线浮点误判成
   「未被覆盖」。

4. **修复可用且能完全消除漂移**（本席临时实验，已还原）：判据换
   `distance <= 1e-6` 后 sm24 重建与改动前**仅剩 3 处差异 = generator 的代码自身
   hash**（即 08-20 已登记的「溯源戳失配、内容一致」既定形态），GTV3_ZONE 回到 19 条。

5. **但简单换 distance 不可行**（同一实验证明）：sm25 F2 的 23 条 outer_skin 边
   distance 全部为 0（延伸段「接触即 0」，distance 分不出「纯躺轮廓」与「延伸出去」），
   严格判据下 sm25 **G9 红**。正确修法需要分段覆盖/端点归属级别的判定。这证实补发射
   行为本身对 sm25 是**必要的**，问题只在判据原语的浮点鲁棒性——在 sm24 上误伤。

**伤害面评估**：判卷语义不受影响（gt 消费者按几何/位置读，不按生成句柄）；已签字 sm24
gt 的历史成绩不依赖重建。但 08-20 登记「内容仍一致」的前提在 6589943 之后**不再成立**
（内容也不一致了，虽然仅句柄/溯源层）——该登记需主控更新，且将来任何用现行代码重建
sm24 bundle 的场合 hash 都对不上。

**处置建议**（主控拍板）：修 `covers` → 分段覆盖判定（恢复 sm24 字段零漂移 + 保 sm25 G9）；
或显式接受漂移并更新 08-20 登记 + 重签 sm24。

### F2 · MAJOR · face-pair 抢占 sm24 三条边的 cap/jamb 证据归因（§2.4 点名隐患成立）

**实跑证据**：跨版本 zone-edge 全量 dump（`run_p2_conversion`，同 request）：

- 改动前：38 条边证据全 `wall_cap_or_opening_jamb`（handles A95/A97/A99）
- 本提交：35 cap/jamb + **3 `wall_face_pair`**（c_04 一条、c_05 两条；AA0/AA1、AB3/AB1、A9A/A98）

**机制（N3 neuter 反证）**：sm24 这 3 条边原本走 **donor-collapse 借邻居 cap 证据**；新代码
里 face-pair binding 在 donor **之前**截胡（值恰好同 200）。N3（binding 恒 None）下 sm24
六个测试**全绿**——回到 donor+cap 路径、产物复原，证明 face-pair 对 sm24 非必要、纯归因替换。
该归因变化独立于 F1（distance 修复版 conversion_report 仍 61+3 vs 改动前 64）。

「自有证据优先于借来的证据」语义上说得通，但请求书 §2.4 原话「若抢占了，即使产物碰巧
一样也是隐患」——事实抢占成立，且 `proof_ids` 已流入 source_map 对外产物。施工/主控需
显式声明这是接受的归因变化，或让 cap/jamb 证明优先于 face-pair。

### F3 · MINOR · 「独立几何断言」的定位名不副实（见 §一）

`_face_pair_exit_is_supported` 是簿记一致性重读（防 pair 构建错乱），不是独立几何观测；
其 docstring「Independent re-read」中「Independent」易读成「独立于取值来源」。建议改注释/
报告措辞，明确「输入层分歧由 S4 拓扑门 + wall-region 覆盖检查 + G8 重建门承担」——这三层
是我实测抓到全部四档挪线实验的真正防线。不修也不影响正确性。

### F4 · MINOR · 唯一硬回归红线没有任何机械锁

「sm24 逐字段不变」只能靠跨版本产物比对验证（本席做法）；现有 2946 把锁全部比对
「同代码两次运行」或几何数值，对字段级漂移零覆盖——主控权威全量 2946 绿与漂移并存
即是证明。建议登记一把冻结 sm24 重建产物 hash 的跨版本锁（是否值得加锁按 §0.1 由
主控拍板，本席只登记缺口）。

### 正面结论（均带实跑证据）

- **修法 1（face-pair）有效**：值来自实测线距（N1）、跨度守卫真挡（N2）、T 接头绑对
  （N3）、真实 sm25 F2 边拿到 240 + G4/G7/G8/G9 全绿（N5 反向 + 正向测试）。
- **修法 2（非凸局部判定）有效**（N6）；双面探测对 interior 窗仍正确（两面都不贴皮才排除）。
- **修法 3（容差比较）零放水**（§四）。
- sm25 候选包 `gt.json` `content_sha256 = 785f8273…`、F1=14/F2=15 分区、31 窗 3 门，
  与仓库提交逐项一致（本席读文件核对）。
- `build_request.py` 改动（量化原点/zone_id 层前缀/沿墙比例 ULP 处置）与请求书③④一致，
  无生产影响；`affected_tests_rules.yaml` +1 为 CLI 如实登记；`gt_review_build.py` 为薄
  封装（41 行，不写 gt/ 目录）。

---

## 四、§2.3 容差比较四项验证（本席独立探针，`_ordered_rings_equal_within_tolerance`，tol=0.001）

| 检查 | 结果 |
|---|---|
| ① 顶点数不同 ⇒ 红 | ✅ False |
| ② 顺序不同（旋转起点）⇒ 红 | ✅ False |
| ②b 顺序不同（反转）⇒ 红 | ✅ False |
| ③ 单顶点偏 500 mm ⇒ 红 | ✅ False（整环平移 500mm 亦 False） |
| ④ 容差值一个没改 | ✅ `dxf_node_join_tolerance_m=0.001`（现有值）；`src/configs/` 本提交零改动 |
| 放行侧 | 单顶点偏 0.9mm（<1mm）✅ True；全同 ✅ True——不是恒 False 的空门 |

---

## 五、全仓对账（本席自跑）

`python -m pytest tests/ -q -n auto`（本席在主树自跑，2026-08-21）：

```
2946 passed, 14 xfailed, 212 warnings in 680.24s (0:11:20)
exit=0
```

- 与主控权威全量**逐位一致**（2946 passed / 14 xfailed / exit 0）。
- **xfail 数未变**（14 → 14，无新增 xfail、无 xfail 转 pass 的暗改）。

---

## 六、边界自证

- 全程未 `git add/commit/push/stash`；未改 `case_tests/test_baseline/gt/**` 与
  `sm25-L_anchor/*.dxf`（挪线实验全部在 `/tmp` 拷贝上）。
- **本席足迹 = 仅 `src/agent/judge/` 四个生产文件（neuter 用，全部还原）+ 本裁决书 + `/tmp/glm_review/`**。
  收工自证：四生产文件 `md5sum -c` 全 OK（与开工快照逐字节一致）。
- ⚠️ 收工时树上另有并行席位（主控）的进行中改动（`gt_review_build.py` 加 `--zone-roles`、
  `review_bundle/` 渲染与 `review_annotations.json`、`plan.md`、`render_gt_overlay.py`、
  `zone_roles_review_only.json`）——**非本席所写**，本席未触碰，留给该席位自行处置。
- 审阅用临时 worktree（`/tmp/glm_review/pre_tree` @ `6589943^`）仅用于旧代码产物重建，
  已 `git worktree remove` 清除。
