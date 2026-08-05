# sm25 素材入仓 + GT 前置勘察（2026-08-04 夜 · orchestrator）

> 用户 08-04 晚：「跑完 sm21 之后你帮我先把 sm25 的素材整理好，包括 gt，
> testdata 你先帮我建好我明天来填值」。
> 本文 = 已做完的部分 + **明天要用户拍板/填值的部分** + **卡点（GT 不能今晚做完的真实原因）**。

---

## 1. ✅ 已做完：素材入仓 + 命名规范化

用户放的原始素材（两处，均未入库）：

| 原位置 | 内容 |
|---|---|
| `case_tests/e2e_tests/sm25-L_anchor/*.jpg` | 6 张图：`1f` `2f` `east` `north` `south` `west-view` |
| `case_tests/test_baseline/gt_sources/sm25_anchor/sm25-L_t3.dxf` | 天正导出 DXF |

已整理为标准 case 布局：

```
case_tests/e2e_tests/sm25-L_anchor/
  case_data/            ← 管线唯一读取处（只认 .png，view_manifest.py:868 硬性）
    1f_view.png  2f_view.png
    North_view.png  South_view.png  East_view.png  West_view.png
    testdata_prompt.json          ← 骨架已建，见 §3
  source_images/        ← 用户给的原始 jpg 原样留存（溯源，不参与管线）
case_tests/test_baseline/gt_sources/sm25-L_anchor/   ← 原 sm25_anchor，改名对齐 case id
    sm25-L_t3.dxf
```

- **JPG → PNG 是无损重编码**（像素不变，只换容器）；⛔ 没做任何降噪/反色/裁剪。
- **底色黑、尺寸线绿**与 sm24 语料一致（已比对 `sm24_anchor/case_data/1f_view.png`），**不需要极性归一化**。
- **case id 取 `sm25-L_anchor`**（= 用户自己建的 e2e 目录名，也是 plan/decision_log 里一直用的「sm25-L」）。
  gt_sources 那侧原名 `sm25_anchor` 与它对不上，**已改名对齐**（gt 路径按 case id 解析，两名并存会直接断链）。
  ⚠️ 如果你更想要 `sm25_anchor`，改回只是两个目录改名，尚无任何代码/记录引用。

**机械验收（orchestrator 已跑）**：`build_view_manifest` 出 6 条 entry，
2 plan + 4 elevation 分类正确、四个立面方向 `direction_source=user` 解析正确、
6 张全部 `dimensioned=declared_true`，`regression` 严格档 applicability 门**通过**。

---

## 2. 图纸与 DXF 勘察结论

### 2.1 DXF 结构（与 sm24 的画图约定一致 ✅）

`edge` 层 6 个视图框 + 框内图名（`0` 层 TEXT）：

| 框 handle | 图名 | 用途 |
|---|---|---|
| `37B` | `1f平面图` | 1F 平面 |
| `380` | `2f平面图` | 2F 平面 |
| `382` | `西立面` | West |
| `384` | `南立面` | South |
| `386` | `北立面` | North |
| `388` | `东立面` | East |

图元：`WALL` LINE 448 · `PUB_DIM` DIMENSION 295 · `WINDOW` INSERT 61 ·
`E_WINDOW` INSERT 21 + LWPOLYLINE 14 · `LVTRY` INSERT 27（门）。
**六个框内都有尺寸标注**（1F 76 / 2F 71 / 西 40 / 南 34 / 北 42 / 东 32 条 DIMENSION）
⇒ `dimensioned_views` 六张全填 true 是诚实的。

### 2.2 ⚠️ 与 sm24 的两处差别（都要用户知道）

1. **⛔ 没有房间名标注。** 07-21 记的画图约定是「房间名标注 **sm25 起**」，但这份 DXF 里
   除了 6 个图名之外**零文字**。⇒ GT 的区名/role（办公/会议/走廊）**无法从图上机读**，
   只能靠 `label_role_map` 人工给，或全部记成通用名。**明天要定：补标注重导，还是人工给 role。**
2. **⭐ 两层，且两层 footprint 相同、内部分隔不同。** 外框都是 25000×20000 的同一个 L/U 形，
   1F 与 2F 的内部房间划分不一样（2F 下部是 5 间办公、1F 下部是 2 间大会议）。
   ⇒ 对不变量 #6 是好消息：**仍在「共底面盒子」内**，没有退台/挑空。
3. 层高：北立面标注 **每层 3600、总 7200**（两层）。

---

## 3. ✅ testdata 骨架已建（`case_data/testdata_prompt.json`）

已按机器可定的部分填好：路径 · 层数 2 · `dimensioned_views` 六张 · 结构对齐 sm21/sm24。
**留给你填的四个 `TODO_` 字段**（每个都写了 orchestrator 的建议值在字符串里）：

| 字段 | orchestrator 建议 | 为什么要你定 |
|---|---|---|
| `Building location` | Shenzhen（前例都是） | 气象文件绑定 |
| `Building type` | Office（家具看是办公） | 影响 4_mep 物理语义 |
| `Floor area` | 待转换器出 footprint 后机械核对 | 我不猜，等 GT |
| `thermal_zones`（逐层） | **1F 建议 14** / **2F 建议 15** | ⭐ 这是**判据**不是观察：它进 gate① 区数 tripwire。<br>我的数字是**看图数的**（1F：左上 2 办公 + 右列 7 小间 + 中部 2 + 下部 2 会议 + L 走廊 1；<br>2F：左上 2 + 右上 1 + 右列 5 + 中部 1 大会议 + 下部 5 + L 走廊 1），<br>**走廊按 sm24 那条「L 走廊算 1 热区」的口径**。转换器的腔体数出来后应与它对账。 |

---

## 4. ⛔ GT 今晚做不完的真实原因：转换器目前只处理**一个**平面

**这不是踩坑，是能力缺口，且是 sm24 收官时就登记过的债（`HC-04 多层静默 floors[0]`）。**

逐条实证（orchestrator 直接读代码核实）：

| 位置 | 现状 |
|---|---|
| `src/agent/judge/tarch_review_bundle.py:169` | `run_p2_conversion(..., request.plan_views[0], ...)` —— **只跑第 0 个平面** |
| `src/agent/judge/tarch_review_bundle.py:217` | 带签名重跑那条路 **同样只跑 `plan_views[0]`** |
| `src/agent/judge/tarch_normalize.py:2071` | `floor = request.floors[0]` —— manifest 只写第 0 层 |
| `src/agent/judge/tarch_normalize.py:1909` | 光栅标定按「文档里**唯一一条** `GTV3_FOOTPRINT` LWPOLYLINE」找 footprint ⇒ 两层两条即歧义 |
| `src/agent/judge/tarch_normalize.py:_build_source_map` | 签名 `(request, plan_view, ...)` —— 逐边 ancestry 也是单平面 |

**对照面**：GT v3 **提取器**本身是支持多平面的（`gt_extraction.py:701` 按 manifest 里的
plan view 逐个遍历）—— 缺口**集中在转换器（天正 DXF → 规范化 DXF + manifest）这一段**。

⇒ **sm25 GT = 一个「转换器多层化」批次**，不是今晚顺手能收的活。形状建议（明天派工时细化）：
1. `run_p2_conversion` 逐 plan view 跑一遍，产物合并进**一份** normalized DXF（GTV3_* 图层按层加 floor 后缀/属性）；
2. manifest 写 **2 个 PlanViewBinding + 2 个 floor**（z=0 / z=3.6，层高 3.6）；
3. footprint 查找从「全文档唯一一条」改成「按 view 绑定」；
4. 立面侧：`ElevationViewIntent.floor_datums` **已经是 list**，多层 datum 结构上支持，需实测；
5. 九门（G1–G10）逐层跑 + 汇总，`G6` 的房间数判据按**逐层**声明。

**⚠️ 排期含义**：sm25 GT 走完还要**真人签字**（G10，`gt_review_sign.py`，绑源图/request/清单三个 hash），
所以无论如何都要你明天在场。今晚我把**不依赖多层化的前置**全部做完了（素材 + testdata 骨架 + 勘察）。

---

## 5. 明天开工的第一件事（建议顺序）

1. 你填 §3 的四个 `TODO_` + 定 §2.2 的房间名/role 口径；
2. 派「转换器多层化」批次（施工 GLM / 审 Claude 侧子代理，或按当轮额度拍）；
3. 转换器出候选包 → 你看 overlay 签字（G10）→ 带签名重跑 → promote 落 `gt/sm25-L_anchor/`；
4. 之后才是跑 sm25 端到端 = C2 收官。
