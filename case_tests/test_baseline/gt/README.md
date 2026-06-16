# gt/ — 评测参考答案（judge② 专用，绝不给 gate① / 执行器）

> 每个 case 一份 `<case>.json` = **评测标准答案**（真实区划布局 / 每立面窗数 / 尺寸真值），
> 由人读**原始图纸**独立得出（**不从管线产物倒推**，否则是自证）。放在 `test_baseline/` 下而非
> case 目录内，避免干扰被测 case。

## 铁律（谁能看）

| 角色 | 看 gt? | 为什么 |
|---|---|---|
| **执行器**（1_correction / 4_mep 等 LLM 段）| ❌ 绝不 | 看了=照抄答案，误差预算崩，没法衡量该段质量 |
| **gate① 确定性校验** | ❌ 绝不 | gate① **随产品上线**，上线版**没有评测答案**；若依赖 gt，dev(有)/prod(无) 行为不一致 |
| **gate② judge（主 Agent）** | ✅ 唯一 | judge 是 dev 期脚手架，上线撤/迁小模型，本就不进 prod |
| **人（肉视）** | ✅ | 对照 gt 核渲染件 |

> 「judge 经验固化成确定性 check」= 把对答案的判断重写成**不靠答案、只靠输入就能查的不变量**
> （例：不是「区划对不对 gt」，而是「cells 是否铺满 footprint 无洞无叠」）——**不是**让 gate 读 gt。

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
