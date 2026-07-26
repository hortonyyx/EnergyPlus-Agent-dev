# gt/ — 评测参考答案（judge② 专用，绝不给 gate① / 执行器）

> **逐 case 管理**：一个 case 的全部 gt 内容放一个文件夹 `gt/<case>/`，**评测标准答案** =
> `gt/<case>/gt.json`（真实区划布局 / 每立面窗数 / 尺寸真值）。由人读**原始图纸**或从权威 CAD
> 抽取得出（**不从管线产物倒推**，否则是自证）。放在 `test_baseline/` 下而非 case 目录内，避免干扰被测 case。

## 目录结构（逐 case bundle）

```
gt/
  README.md
  <case>/
    gt.json          # 评测答案（judge/人 读，gate①/执行器绝不读）
    source.dxf       # 来源 CAD（天正图形导出后的纯几何；judge/人 用；绝不放 case_data/）
    renders/         # gt 渲染件（人肉视核验，可由 gt.json+工具重生成）
      gt_plan.png
      gt_elev.png
```

`source.dxf` 与 `gt.json` 同属**答案级数据**、同放 judge-only 的 gt 根下——`load_gt` 只按 case 读
`gt/<case>/gt.json` 这一个文件（**不 rglob**），DXF 安放其侧不会被误读；纪律真正要守的是**它绝不进
`case_data/`**（执行器可读=识图作弊），由 `tests/test_gt_discipline.py` 机械守。

## v3 答案与受控转正（2026-07-26 起）

v2 手录答案（`sm21_anchor`）与 v3 转换器答案（`sm24_anchor`，首个）并存。**v3 答案不由人手写、也不许手工拼装**，只能走这条受控通道：

```
天正 DXF（gt_sources/<case>/）
  → build_review_bundle   候选包（gt.json + renders/ + 审计表 + review_index.json），status=BLOCKED（近阈值门 G6 + 人核门 G10 未清）
  → gt_review_sign.py     人看图后签名 → review_ack.json（绑 源图 / request / 清单 三个 hash）
  → gt_review_rerun.py    带签名重跑 → 十门全绿 status=PASS（重跑产物必须与签字时逐字节相同，否则清单校验当场拒绝）
  → gt_promote.py         受控写入本目录：翻 human_verified + 重算 content_sha256 + 原子落盘 + 写后重读自校
```

- **写入口只此一条**：`write_gt_v3_candidate` **拒绝**写受保护根且只肯写 `candidate`；`load_gt_document` **只认** `human_verified`。中间这段除 `promote_gt_v3` 外无路可走。
- **转正只许动三处**：`verification.status` / `reviewer_id` / `reviewed_on`（+ 派生的 `content_sha256`）。几何、洞口、区、墙厚一律不得被 promote 触碰（有语义不变式门 + 变异矩阵锁）。
- **v3 目录多一层 `review/`**：签名证据（`review_index.json` / `review_ack.json` / 审计表 / 用途注记 / 十门全绿的转换报告）与答案同库，**这样这份签名将来可被重新验证**——拿落盘的这批文件重算 hash 对签名即可。
- **v3 的源 DXF 放 `case_tests/test_baseline/gt_sources/<case>/`**（不放本目录；上文「目录结构」里 `source.dxf` 与 `gt/<case>/` 同放是 v2 时代的安排）。
- **可复现的准确口径 = 同代码 + 同输入 ⇒ 同字节**：答案的 `generator.*_sha256` 绑定九个源码文件的字节，故涉及那些文件的改动会改变答案指纹。签名的可验证性因此走「拿落盘文件重算」，而不是「从源图重新推导」。

## 铁律（谁能看）

| 角色 | 看 gt? | 为什么 |
|---|---|---|
| **执行器**（1_correction / 4_mep 等 LLM 段）| ❌ 绝不 | 看了=照抄答案，误差预算崩，没法衡量该段质量 |
| **gate① 确定性校验** | ❌ 绝不 | gate① **随产品上线**，上线版**没有评测答案**；若依赖 gt，dev(有)/prod(无) 行为不一致 |
| **gate② judge（主 Agent）** | ✅ 唯一 | judge 是 dev 期脚手架，上线撤/迁小模型，本就不进 prod |
| **人（肉视）** | ✅ | 对照 gt 核渲染件（见下「渲染核验」）|

## 渲染核验（人肉视用，别核裸坐标）

`<case>.json` 是裸坐标，对照原图核很费眼。用渲染工具把 gt 还原成**带尺寸标注的平面图+立面图**，
人对照原始 `*_view.png` 核**布局意图**（区划/计数/窗位/层高），不核 mm：

```
python scripts/tool_scripts/render_gt.py <case>        # 例: sm21_anchor
# → gt/<case>/renders/gt_plan.png  (逐层: 区块按 role 填色+标注、footprint+分带尺寸链、立面窗/门)
# → gt/<case>/renders/gt_elev.png  (逐立面: 楼层带+窗按 [sill,head] z 框出+计数、门、z 尺寸链)
```

窗的**计数 + sill/head 精确**(gt 真值)；窗在立面内的 **x 位置是示意**(均布，gt 不定 x，图上注明
`x schematic`)；区块 `rect_m` 是清空间 bbox(±墙厚)。`renders/` 可由 gt 随时重生成。
该工具是**人/judge 侧可视化**——读 gt 合规(铁律只禁 gate①/执行器)，有 `tests/test_gt_render.py` 守。

> 「judge 经验固化成确定性 check」= 把对答案的判断重写成**不靠答案、只靠输入就能查的不变量**
> （例：不是「区划对不对 gt」，而是「cells 是否铺满 footprint 无洞无叠」）——**不是**让 gate 读 gt。

## 精确坐标谁判？——不是 gt、不是 judge，是**确定性层**

gt 的 `rect_m` 是**布局意图（清空间 bbox ±墙厚）**，**故意不精确**。精确坐标有**容差带**（一段范围都算
对），**既不归 gt 也不归 judge**：
- **确定性核**把冗余坐标**坍缩成规范值**（吸 50mm 栅格 / 补缝 / z-stack 吸附）；
- **gate① kernel** 用**带容差不变量**判过不过（coverage 无洞无叠 / 闭合 / 最小边 / 互逆面积 / z 连续）；
- **gate① 交叉核对**软 flag 坐标 vs 尺寸链。

→ **judge 只判布局/计数/窗位（定性、对 gt）；精确坐标 mm 级由确定性判，judge 与 gt 都不卡。**

代码上：只有 [`src/agent/judge/gt.py`](../../../src/agent/judge/gt.py) `load_gt()` 读本目录；
`src/validator/checks/*`（gate①）与 `src/agent/pipeline.py`（执行器）**不得 import 它**
（有测试 `tests/test_gt_discipline.py` 机械守住）。

## schema

```jsonc
{
  "case": "<case>",
  "footprint": { "W_m": 15.0, "D_m": 8.0 },          // 总外包 (每层一致)
  "floors": [
    { "name": "Floor 1", "z_floor": 0.0, "ceiling_height": 3.0, "zone_count": 7,
      "zones": [
        { "id": "N1", "role": "office", "rect_m": [x0, y0, x1, y1], "note": "..." }
        // rect_m = 清空间 bbox（±墙厚，gt 只判布局意图、非精确 mm；精确坐标 correction 定）
      ] }
  ],
  "windows": [
    { "facade": "North", "floor": "Floor 1", "count": 3, "sill_m": 1.0, "head_m": 2.6 }
  ],
  "doors": [ { "facade": "South", "floor": "Floor 1", "note": "主入口" } ],
  "dimensions_truth": { ... },                        // 可选: 真实尺寸值，给 J0 查抄录
  "notes": "..."
}
```

## judge 怎么用

J1（1_correction）载入 gt → 把校正出的 cells/窗 与 `floors[].zones` / `windows[].count` **逐项直接比**，
verdict 写明差异，并据此生成 🔍 肉视清单（「gt 说该这样、产物那样，核一眼」）。J0 可用
`dimensions_truth` 查「数字抄录」。
