# 派工单 · **F-153 第三轮**：按用户拍板的**甲案**把丢失清单固化进事实层

- **日期**：2026-08-31 · **派工方**：orchestrator · **施工方**：**GPT 家族**（你写了前两轮，本轮延续）· **审**：**GLM 家族**
- **基线**：**`31f873d`** · 前两轮全档 → [执行档](../execution/2026-08-30_f153_boundary_ring_loss_execution.md) ·
  [主控实验档](../../experiments/2026-08-30_f153_orchestrator_repro/README.md) ·
  [本单前两轮](2026-08-30_f153_boundary_ring_loss_dispatch.md)

---

## 〇、⛔⛔ 本轮最要紧的一句：**上一轮我给你的裁决被用户推翻了**

上一轮派工单 **§八** 我裁「loss readout 改成**纯派生**、⛔ 不做存储字段」。
**用户 2026-08-31 拍板：走【甲案】—— 要固化进签字过的事实层。**
⇒ ⛔ **§八 作废**。你上一轮交的纯派生实现是**中间态、不是终态**，本轮要改回去。

⭐ **你上上一轮那版 WIP 的形状是对的**（`boundary_ring_losses` 挂在 `AsMeasuredViewV1` 上
+ view 级唯一性/互斥校验）——它在 `31f873d` 的历史里，**可以复用形状，但请自己重新论证 + 补锁**。

⭐ **用户明确知道并接受了代价**（我用白话讲过、他复述后选的甲）：
底稿指纹会变 · sm25 基线要重做 · **以后每加一个字段都要重做一次**。
⇒ ⛔ **别再劝回乙案**，也⛔ 别自作主张只做一半。

---

## 一、本轮任务项

### 任务 1 · 把 loss readout 变回**存储字段**
`boundary_ring_losses` 挂回 `AsMeasuredViewV1`，进 `canonical_bytes()`，
带上你上一轮加的两个上游线索字段（`nearest_same_axis_wall_face_const` /
`span_to_nearest_same_axis_wall_face_delta`）。
⭐ **保留**你上一轮已经做对的两件：**形态 A 的几何交点切分**（收窄版）· **形态 B 只报不修**。

### 任务 2 · ⭐⭐⭐ **重做 sm25 的 staging 基线**（⛔ 本轮解除禁令 7，**只解除这一件事**）
`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/` 三件套要重生成：
`as_measured.json`（内容变、哈希从 `839d67a2…` 变）· `revisions.json`（`as_measured_content_sha256` 跟着换）·
`as_signed.json`（重新派生）。
⭐ 入口 = `gt_facts_staging.write_facts_candidate(case, as_measured, ...)`（`gt_facts_staging.py:251`）。
⚠️ **⛔ 不许手改 JSON** —— 必须**从 DXF + request 重跑生成**，否则就是手搓答案。
⚠️ **⛔ 台账里那 5 条 revision 的内容与 verdict 一个字都不许动**（它们全是 `unsigned`，本轮不签任何字）——
本轮只换它指向的那个哈希。

### 任务 3 · ⭐ **同批把 sm24 也过一遍**
你上一轮实测 sm24 有 **2 个过阈值 cavity 被丢（23.1672 / 30.8464 m²，均 `owner_count=0`）**。
⇒ sm24 若有 staging 基线，**一并重做**；若没有（像 sm21 那样缺签字 request），**如实报结构性 N/A**，
⛔ 别造一份 request 来凑。

### 任务 4 · **留一条给后来人的账**
在 `as_measured.py` 里写清（docstring 即可）：**这个字段是纯派生值，之所以仍然存盘，
是因为「底稿必须自己承认自己的缺口」**——⛔ 不要让后来人以为「凡派生值都该存」。

---

## 二、⛔ 禁令

1. ⛔ **不许手改 `gt_staging/` 下任何 JSON** —— 只能由生成器重写（任务 2）。
2. ⛔ **不许动 `gt_sources/`**（DXF 与 request 是输入，不是产物）。
3. ⛔ **不许签任何 revision**（5 条保持 `unsigned`）。
4. ⛔ **不许动 `answer_compiler.py`** —— 那是 ②-1d 的面。
5. ⛔ **不许在 `_boundary_owners` 上做容差匹配**（形态 B 的病灶不在这层，见上一轮 §九）。
6. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。

## 三、验收表（⭐ 已按**三格**对撞：①禁令 ②任务项 ③**已落库产物的既有承诺**）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | 三个 sm25 cavity + 两个 sm24 cavity **各自出现在落库 `as_measured.json` 的 `boundary_ring_losses` 里**，带面积、span、reason、上游线索 | 与任务 1/2/3 一致 |
| 2 | ⭐ **新旧哈希都给出来**：旧 `839d67a2…` → 新 `<x>`，且 `revisions.json` 与 `as_signed.json` **都指向新值**、三者自洽 | ⭐ 第三格对撞：**这条【故意要求哈希变】** —— 与上一轮「哈希不许变」正好相反，因为口径变了 |
| 3 | ⭐⭐⭐ **重生成是机械可复现的**：同一份 DXF + request 跑两次 ⇒ 三件套**逐字节相同** | ⛔ 与禁令 1 对撞：**若你手改过 JSON，这条必然不通过** |
| 4 | 台账 5 条 revision 的**内容与 verdict 逐字未变**（给 diff 证明只有那一个哈希字段变了） | 与禁令 3 对撞 |
| 5 | `pytest -n 6 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py` **全绿** | ⚠️ 这几个文件里有断言钉着旧哈希 ⇒ **允许你改那些【哈希常量】**，⛔ 但不许改任何**行为断言**；改了哪几行要逐行列出来 |
| 6 | 形态 A 的切分与形态 B 的「只报不修」**行为与上一轮一致**（给出对比读数） | 与任务 1「保留已做对的两件」一致 |
| 7 | 列全改动路径（⛔ 不提交） | 与禁令 6 一致 |

## 四、停下上报（分层）
**必停**：重生成出来的三件套**与旧的除新字段外还有别的差异**（那说明生成链不确定）· 既有**行为**断言变红 ·
sm24 的 staging 基线**不存在**且你判断不该造 · 任务项与禁令自相矛盾（**累计 51/51 全是我的题错**）。
**只记不停**：哈希常量所在的行号 · sm21 仍 N/A · 面积末位差异。

## 五、交付物
代码 + 重生成的三件套（⛔ 不提交）· 执行档追加「第三轮」一节（⛔ 不重写前两轮）。

---

# ⭐ 补充裁决（2026-08-31 · 回应施工方就任务 3 的强制停报）

## 六、⚠️ **停报成立，派工方题错 #52（累计 52，仍 52/52）**

**施工方报的**：`gt_staging/` 下**只有 sm25**，不存在 sm24 基线；而 sm24 的 `gt_sources/sm24_anchor/`
**确实有 `request.json` 与 `source.dxf`**，并非「像 sm21 那样缺 request」⇒ 任务 3 的二分法**盖不住它**。

**主控独立核实（⛔ 未转引）**：
```
ls case_tests/test_baseline/gt_staging/        ⇒ 只有 sm25-L_anchor
gt_sources/sm21_anchor/  ⇒ source.dxf                                   （确实缺 request）
gt_sources/sm24_anchor/  ⇒ request.json source.dxf normalized.dxf …     （⭐ 有 request）
gt_sources/sm25-L_anchor/⇒ request.json request_as_measured.json + 两份 DXF
```
⇒ **成立。**

⭐ **病族 = [[absence-conflates-causes-in-observables]]（「缺席」把多种原因压成同一个空白）**：
我写任务 3 时把「**没有 staging**」只想到**一种**原因（缺 request），
漏了**第二种**（**有 request、只是从来没建过**）。这正是我自己 08-30 刚犯过的「漏第三态」同形。
⚠️ 而三格对撞**拦不住这一类** —— 它不是矛盾，是我对外部事实的分类不全
⇒ 配套解只能是「**派工前先自己 `ls` 一遍**」（同题错 ⑮ 的处置）。

## 七、⭐ 裁决：**sm24 本单按【结构性 N/A】，⛔ 不在本单首次创建**

**决定（⛔ 不需要你再问，§四 该条停报就此豁免）**：

1. ✅ **sm24 不做**：本单是「**重做既有基线**」，**首次创建一份新 case 的事实层是另一种性质的动作**——
   它要回答的是「转换器在 sm24 上跑不跑得干净、诊断有哪些、要不要签修订」，
   那是**它自己的一张单、自己的验收**。塞进返工单里 = 范围蔓延，产出一份没人审得动的 diff。
2. ✅ **代价为零，这一点很重要**：F-153 的**代码**改动（存储字段 + loss 派生）**对任何 case 都生效**
   ⇒ sm24 一旦有了事实层，那 2 个 cavity（**23.1672 / 30.8464 m²**）**会自动被记进去**。
   ⇒ 现在不做，**不会让任何东西永久失守**。
3. ⭐ **但你仍要交一样东西**：把 sm24 那 2 个 cavity 的读数**写进执行档**（你上一轮已经量过），
   并注明「**待 sm24 事实层建立后自动落库**」——⛔ 别让它掉进缝里。
4. **验收表随之改**：原 **§三 验收 1** 里「两个 sm24 cavity 出现在落库 JSON 里」⇒ **改为**
   「sm24 的 2 个 cavity 读数出现在**执行档**里，并标注 N/A 原因 = **该 case 尚无事实层基线**」。

## 八、⭐ 另行登记（⛔ 不在本单）

**新单：首次创建 sm24 的 facts staging 基线**（原料齐备：`gt_sources/sm24_anchor/{source.dxf,request.json}`）。
已登记 plan.md，⛔ 本轮不派。

## 九、⛔ 其余一切不变
任务 1 / 任务 2 / 任务 4 照旧；禁令 1–6 照旧；验收 2–7 照旧。**请从这里继续。**
