# 补窗前的实测调查（2026-09-08，主控）

> **起因**：用户「先补窗，得跑出来一个完整的，别跑缺胳膊少腿的」＋「这部分 Claude 来修」。
> **前提**：`projection_bridge.py:920` 是一句硬写的 `windows=[]` ⇒ **新腿按设计产出一栋没有窗的楼**；
> 平面产物里 85/87 个洞口候选**只被用来切墙**（变成 `CutLineV1` 雕房间），一个都没变成窗。
> **树** = `/tmp/w1_windows_claude`（分支 `wt/09.08_windows`，⛔ 与 GLM 正在施工的树分开）。

## 1 · 两边各有对方没有的一半

| | 平面产物 `as_drawn_plan_v2` | 立面产物 `as_drawn_elevation_v0` |
|---|---|---|
| 沿面范围 | ✅ `opening_candidates[].span_m` | ✅ `openings[].x_range_m` |
| **高度（窗台/窗顶）** | ⛔ **没有** | ✅ **`z_range_m`** |
| **门/窗分类** | ✅ **`hypotheses.opening_types`**（`window`/`door`/`not_opening`）| ⛔ **没有**（`ledger.door_window_classified: false`）|
| 洞口总数 | 1f 85 · 2f 87（含大量内门）| east 13 · north 8 · south 7 · west 6 = **34** |

⇒ **必须配对**：立面给 z，平面给类型。⛔ 任一边单独都造不出一个合法的 `WindowV3`
（它要 `facade` + `span` + `z` + `floor_id`）。

## 2 ⭐⭐⭐ · 沿面坐标同源，**但每一面的朝向不同**（实测，唯一）

把每个立面洞口的 `x_range_m` 拿去平面的 window/door 候选里找最近的（判据：两端点误差和 < 100 mm）：

| 面 | 沿面全长 | **原样** | **镜像** |
|---|---|---|---|
| east | 20 m | **13/13** | 4/13 |
| north | 25 m | 0/8 | **8/8** |
| south | 25 m | **7/7** | 0/7 |
| west | 20 m | 3/6 | **6/6** |

⇒ **34 个立面洞口在正确朝向下全部匹配**，且每一面的朝向**唯一**（13vs4 · 0vs8 · 7vs0 · 3vs6，⛔ 没有模棱两可的）。
**East/South 原样，North/West 镜像** —— 从建筑外面看，+x 在南立面上是左→右、在北立面上是右→左，几何上本该如此。

### ⛔⛔ 主控自更正：**我先前判它「翻转被默认掉 ⇒ North/West 会装反」，那是错的**

第一版结论写的是：as_drawn 腿用 `_resolve_facade_flip_fields(None)` 的无声明默认值
⇒ North/West 的洞口会被静默放到墙的另一头，**补窗之前必须先修**。

**把默认值代进公式算一遍就翻了**：
- `_resolve_facade_flip_fields(None)` 返回 `(mirrored=False, local_x_positive="image_left_to_right")`
- 代进 `facade_convention.resolve_sign`：`effective_flip = False XOR False = False`
  ⇒ **`sign = FACADE_BASE_SIGN[family]`**

而 `facade_convention.py:37-39` 写死的就是：

```python
FACADE_BASE_SIGN = {"North": -1, "South": 1, "East": 1, "West": -1}
```

⇒ **默认值给出的正是我实测证明为正确的那组符号。⛔ 当前没有这个缺陷。**

⭐ **我犯的错**：把「这个值是默认来的」直接读成了「这个值是错的」，
⛔ 没有把默认值代进下游公式算一遍。**「默认」描述的是来源，不是正确性。**

**真实的残余风险弱得多**（登记，本轮不修）：
若将来某份立面产物**真的是镜像画的 / 右→左**，as_drawn 腿**不会察觉** ——
它不从产物读 `mirrored` / `local_x_positive`，只吃默认。
⇒ 属于 [[symmetric-evidence-cannot-prove-direction]] 的形态，但**是潜在限制、不是当前缺陷**。

### ⭐⭐⭐ 而这一查带来一个更好的结果：**约定和投影公式仓里早就有**

- `facade_convention.FACADE_BASE_SIGN` = 我实测的那四个符号，**逐个吻合**
- `window_sources.py:541` 的注释原话就叫它「**the North/West mirror sign**」
- `_advisory_elevation_world_frame` 的 docstring（:490-492）给出的公式原文是
  「`world = local` when `sign == +1`, or **`world = W - local` when `sign == -1`**」
  —— **与我实测用的镜像式逐字相同**

⇒ **两条【不同族】的推导互相印证**：我的是从真产物**实测**出来的，仓里的是**声明的表**。
⇒ **补窗不需要「先修翻转」这一步**，直接复用 `facade_convention`，⛔ 不自己发明规则。

## 3 · 匹配上的 34 个：31 window + 3 door，1f/2f 各 17

残差：**最大 53.6 mm，中位 18.4 mm**（标定量级，与足迹侧 14.4 mm 同量级）。

## 4 ⚠️ · 我第一版匹配器的两个缺陷（如实登记，⛔ 别照抄）

1. **只按沿面范围找最近 ⇒ 会串层**：1f/2f 的窗常常上下对齐，9/34 匹配到了另一层。
   ⇒ **楼层必须先由立面的 `z_range_m` 对 ladder 定**，再在该层内匹配。
2. **没约束到外墙 ⇒ 匹配到内墙线**（east 匹配到 `pos_m=14.755` 的内部线）。
   ⇒ 必须先定「这一面的外墙面线」，再在其上匹配。

⇒ 正确的匹配键 = **（楼层 by z）×（该面的外墙）×（沿面范围）**，⛔ 不是单看沿面范围。

## 5 · 由此定下的设计方向

**窗必须是确定性推导的，⛔ 不是模型画的** —— 与本项目的杠杆一致
（[[reading-lever-is-measurement-enforcement]]：读图器只写像素锚点，代码做唯一换算）。

1. 每份立面：**复用 `facade_convention.resolve_sign` + `project_affine_interval`**
   （⛔ 不自己发明规则；默认的 flip 字段在本批产物上已实测正确）
2. 洞口的 `z_range_m` → 对 ladder 定楼层（实测四面**零跨层**，干净）
3. 沿面范围 → 定位到该层该面的外墙面线上的洞口候选
4. 平面的 `opening_types` 给类型；立面的 `z_range_m` 给 `z=[sill, head]`
5. 组装 `WindowV3(id, floor_id, facade, span, z, room=含它的 cell)`

⛔ **尚未验的**（⚠️ 我是推的不是量的）：
- 3 个 door 要不要也进 `windows[]`（EnergyPlus 里外门也是 fenestration）—— 要看 legacy 腿怎么做
- `room`（cell id）怎么定：洞口在墙上，两侧各有一个 cell

---

## 6 · S1 之后的两条新实测（决定了 S2 的驱动方向）

### 6.1 平面的 window 候选**全在外墙上**，内墙 0 个

足迹外轮廓平面位置：x = [0.11, 5.12, 14.88, 24.88]，y = [0.12, 5.88, 14.12, 19.88]（Z 形八面）。
逐个候选查它所在面线（或其配对面）是否落在这八个位置上（容差 0.30 m，覆盖墙厚+吸附残差）：

| | window 候选 | **外墙上** | 内墙上 |
|---|---|---|---|
| 1f | 30 | **30** | 0 |
| 2f | 32 | **32** | 0 |

⇒ 「62 个平面 window vs 34 个立面洞口」的差额**不是内窗**。

### 6.2 ⭐⭐⭐ 一个物理窗在墙的**两个面**上各留一个缺口 —— 直接按候选造窗会**静默翻倍**

按「配对面上有 span 相符（<0.15 m）的另一个 window 候选」归并：

| | window 候选 | 成对 | 落单 | **物理窗数** |
|---|---|---|---|---|
| 1f | 30 | 14 组 | 2 | **16** |
| 2f | 32 | 15 组 | 2 | **17** |
| 合计 | 62 | 29 组 | 4 | **33** |

⇒ **62 个候选 = 33 个物理窗**（29 个两面都记了 + 4 个只记到一面）。
⚠️ 若 S2 直接按候选造窗，模型会拿到**两倍数量的窗**，而且**看上去完全合理、不报错** ——
同族 [[observation-named-as-fact-travels-as-fact]]：`opening_candidate` 是**面上的观测**，
⛔ 不是**物理窗**，名字不提醒你这件事。

### 6.3 ⇒ S2 的驱动方向：**从立面洞口驱动**，⛔ 不从平面候选驱动

理由是**契约硬的，不是偏好**：
- `WindowV3` 必须有 `z`；而 `sill`/`head` **只准立面声称**（`_claim_links` 的权限矩阵）
- ⇒ **平面上有、立面上没有的窗，造不出合法窗对象**

所以：立面洞口是驱动集（34 个），平面候选供 `host` 与门窗类型。
⛔ 平面有而立面无的那些，**必须作为记账的缺席**（登记，⛔ 不静默丢）。

⚠️ **尚未解释的余量**（⛔ 不预设）：平面 33 个物理窗 vs 立面 31 个 window 类型洞口。
S2 要逐个对上，差额必须有名字。

---

## 7 · 回应 J0 的朝向质疑（2026-09-08，主控实测）

GPT 席位在首次 judge-on 跑的 J0 裁决里写：
> 「North/West grade overlays also show a **horizontal registration offset** against source pixels;
> the reported 100 percent extent scores do not establish declaration-level orientation.」

⇒ 若这是**坐标层**的问题，North/West 的窗会整体错位 ⇒ 直接压在补窗的地基上，必须查。

**实测**（立面洞口投影到世界系后，与平面候选的端点偏移中位数）：

| 面 | `FACADE_BASE_SIGN` | n | lo 端偏移 | hi 端偏移 |
|---|---|---:|---:|---:|
| **East** | +1（不镜像）| 12 | **−13.8 mm** | −8.0 mm |
| South | +1（不镜像）| 7 | +3.7 mm | +1.9 mm |
| **North** | −1（镜像）| 8 | +10.7 mm | +8.8 mm |
| West | −1（镜像）| 4 | −3.4 mm | −4.2 mm |

⭐ **偏移最大的是 East（不镜像），最小的是 West（镜像）** ⇒ **偏移不随镜像变化**，
量级 ≤ 14 mm，与本档 §3 量到的跨图标定残差（中位 18.4 mm）同一档。

⇒ **坐标层的镜像相关偏移不成立**；镜像没有引入系统性错误。

⚠️ **划界（⛔ 不夸大本次测量）**：
- 本测量只覆盖**坐标层**。J0 说的是 **overlay（渲染叠图）**上的偏移 ——
  那属于席位同时发现的**渲染器仍读 legacy `strokes/dimensions`、产出 400×80 空图**那条，
  ⛔ 不是本条线的问题，也**未被本次测量覆盖**。
- 样本量小（4~12），「系统性」是粗判据（两端同向且 >5 mm）。
- ⛔ 本测量**不**证明「声明级朝向已确立」—— J0 那半句仍然成立：
  as_drawn 腿的 flip 取的是**默认值**，⛔ 产物没有声明它（本档 §2 的残余风险，登记未修）。
