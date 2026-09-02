# 探针 · 投影桥「中轴平面剖分」在真实 sm25 上到底切不切得出房间

- **日期**：2026-09-02 · **做的人**：orchestrator（主控）· **档位**：**探索档**
- **⛔ 铁律**：本探针的产物**永远不作成绩**（CLAUDE.md §0.2）。它验的是**算法**，不是任何一次跑测。
- **手法**：[[feed-the-answer-in-to-test-the-code-alone]] —— 把**答案**（`as_measured` 事实层的墙与洞口）
  当**输入**喂进候选算法，单测算法自己。⛔ 信任根没有被伪造：骨架取答案、结论只讲算法。
- **服务于**：[proposals/correction_projection_bridge.md](../../../proposals/correction_projection_bridge.md) 的 **W1**
  （「把中线延伸到相邻中线的交点」这一步没有签字的规则）

## 输入

`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json`
（`units_per_metre = 10000` ⇒ 1 unit = 0.1 mm；`plan-F1` 55 墙 / 31 洞口，`plan-F2` 53 墙 / 30 洞口）
出现过的墙厚只有两个值：**120 mm 与 240 mm**。

## 四次测量（逐次都是被上一次的读数逼出来的）

| # | 做法 | 读数 |
|---|---|---|
| **1** | 中线 = 两面线中点，沿墙区间**原样**，`polygonize` | ⛔ **F1 / F2 各 0 个有界面** —— 不是"差一点"，是一个房间都没有 |
| **2** | 同上 + 两端各延伸一个**常数** | 0–300 mm 全是 **0 个**；600 mm 才 7 个；1200 mm 才 15 个 ⇒ **没有平台，只有单调增长**。而墙厚才 240 mm ⇒ 600 mm 的延伸已经是**凭空造墙** |
| **3** | 把**洞口**也当中线的延续加进去（判分侧 `_wall_region` 正是这么补缺口的）+ 常数延伸 | **119 mm → 0 个面 · 120 mm → 13 个 · 121 mm → 14 个** ⇒ ⭐⭐⭐ **±1 mm 就换答案，且多延伸会造出多余的面** = W1 被量成了数 |
| **4** | ⭐ **零参数规则**：端点若落在某堵**垂直墙的墙带**内（判据 = **那堵墙自报的半厚**，⛔ 不是我设的数），就延伸到它的**中线**上 | **F1 13 间 · F2 15 间**（共 **28**）· 两层总面积都 **279.26 m²** · 最小房间 **7.18 m²** · **零个 <1 m² 的碎片** · F1 端点延伸 47 次 / F2 46 次 |

⭐ **为什么 120 mm 是那个魔数**：它 = **240 mm 墙厚的一半**。中线止于垂直墙的**面**，
要够到那堵墙的**中线**恰好差它的 `t/2`。⇒ 这个量**本来就在事实里**，
⛔ 不该由派工方去"调"（[[gate-teeth-direction-follows-fixture-inventory]] 的正解形态：**让被测对象自己提供尺子**）。
⭐ 也因此「延伸自己厚度的一半」是**错的**（实测：F1/F2 各只剩 **1** 个面 = 整个外轮廓）——
120 厚的隔墙撞上 240 厚的主墙时，要的是**对方**的半厚。

## ⛔ 一个必须查清的开放问题（⛔ 别当验证通过）

| 那条路 | 数出来几个 |
|---|---|
| **本探针（中轴剖分）** | **28** 个房间，**零丢失** |
| **判分侧（腔）** | 25 健康腔 + 2 走廊腔 = 27 个环，**外加 F-153 登记的 3 个丢失** = **30** |

**28 ≠ 30。** 差的 2 个是什么，本探针**没有查**。
⛔ **不许把「数目相近」当成对上了** —— 那正是 [[proxy-mistaken-for-the-thing]]：
「条数达标」证明不了「每个房间都对」。
⇒ **B1 派工单必须把这条写成阻塞验收项**：**逐个把 28 个面与 30 个腔配上账**，
差额要么指名理由（如两个腔在中轴口径下本就是同一个房间），要么就是本算法的缺陷。

⭐ **弱corroboration（⛔ 只能算线索）**：F-153 被吞掉的三个腔的**净空**面积是
88.27 / 28.68（F1）与 70.34（F2）；本探针在对应楼层切出的最大三个房间是
96.36 / 31.48（F1）与 77.03（F2）—— **中轴口径本就比净空大**，量级吻合。
⛔ 但这**不构成**「那三个房间被找回来了」的证明：没有逐个做位置对账。

## 复现

```bash
python - <<'PY'
import json
from shapely.ops import polygonize, unary_union
from shapely.geometry import LineString
d=json.load(open("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json"))
UPM=d["units_per_metre"]
def lines_of(view):
    out=[]
    for w in view["walls"]:
        out.append((w["axis"],(w["face_lo"]+w["face_hi"])/2.0,w["along_min"],w["along_max"],w["thickness"]/2.0))
    for o in view["openings"]:
        out.append((o["axis"],(o["cross_lo"]+o["cross_hi"])/2.0,o["along_min"],o["along_max"],(o["cross_hi"]-o["cross_lo"])/2.0))
    return out
for v in d["views"]:
    L=lines_of(v); segs=[]
    for ax,c,lo,hi,ht in L:
        nlo,nhi=lo,hi
        for ax2,c2,lo2,hi2,ht2 in L:
            if ax2==ax or not (lo2-ht <= c <= hi2+ht): continue
            if abs(lo-c2)<=ht2 and c2<nlo: nlo=c2
            if abs(hi-c2)<=ht2 and c2>nhi: nhi=c2
        segs.append(LineString([(nlo,c),(nhi,c)]) if ax=="x" else LineString([(c,nlo),(c,nhi)]))
    f=list(polygonize(unary_union(segs)))
    ar=sorted((x.area/UPM**2 for x in f),reverse=True)
    print(v["view_id"], len(f), round(sum(ar),2), [round(a,2) for a in ar])
PY
```

## 这个探针改变了设计稿的什么

1. **W1 从"薄弱点"变成"已给出规则"**：延伸不是常数，是**延到相邻中线**，判据用对方自报的半厚 ⇒ **零自由参数**。
2. **洞口必须参与切割**（⛔ 不只是"窗的来源"）：不把洞口当中线延续加进去，**一个房间都切不出来**。
   ⇒ 设计稿 §7.2 的批次表里，**B1 就得读洞口的沿墙区间**，⛔ 不能推到 B4。
3. 新增一条 B1 的阻塞验收：**28 vs 30 的逐个对账**。


---

## 第二轮（同日）：W2 与 W3

### W2 —— 少一堵墙，**静默丢一个房间，且可以毫无几何签名**

从 sm25 `plan-F1` 逐个删掉一堵内墙后重跑（基线 13 个房间 · 1 个真悬端）：

| 删掉的墙 | 房间数 | 真悬端数 |
|---|---|---|
| `w_x_38800_40000_149600_208800` | 12 | 3 |
| `w_x_99400_100600_111200_147600` | 12 | 1 |
| `w_x_197600_200000_2400_22400` | 12 | 1 |
| ⛔ `w_y_50000_52400_121599_140000` | **12** | **0** |

（"真悬端" 的判据 = 端点落在剖分区域**内部**、且没有任何别的线经过它。）

⇒ **最后一行是判决**：房间真的少了一个，**悬端检测零反应**。
⇒ 设计稿 §四 原写的「必需中线不可派生 ⇒ 整层响亮 NA」**几何层实现不了**，已作废改写。

### W3 —— 生产侧没有外部外轮廓

| 量的东西 | 读数 |
|---|---|
| 事实层外轮廓（gt 侧）| **290.00 m²** · F1 59 顶点 / F2 56 顶点 |
| 本算法派生的外轮廓 | **279.26 m²** · **顶点数逐层相同** |
| 差 | **10.7424 m²**，两层完全一致 ⇒ 外墙走中轴、整圈内缩 `t/2` 的**基准差** |
| `AsDrawnPlanV2` 里有没有外轮廓 | ⛔ **零命中**（`footprint`/`outline`/`boundary`）|

⇒ 桥自派生 footprint、gate① 的 `check_coverage` 又拿同一个 footprint 当分母
⇒ **B3 在新链上按构造恒真**。已写进设计稿，要求 B1 显式声明 + 补一道不自洽的门。
