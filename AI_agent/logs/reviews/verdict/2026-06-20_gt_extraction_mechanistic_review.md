# Review — gt 产出方式是否"机制性固化无障碍"（Codex 通查 + 硬化）

- **Date**: 2026-06-20
- **Reviewer**: Codex (默认模型，ChatGPT 账户)，via MCP（文件内联）
- **Author**: Opus 4.8
- **触发**: 用户确认 sm21 gt 通过为标准 gt 后，要求 Codex 通查"产出方式是否固化无障碍 + 两 bug 是否机制性解决"

## Codex 判定
**未完全"机制性解决"**：对**这张已知 DXF**（同布局/层名/块名/图名/两层/走廊拓扑）稳；但作为"天正 exploded DXF"
这一类**还不无障碍**。**BUG A**（两 renderer 不一致）已大体结构性解决（gt 带逐窗几何 + 门一等公民）。
**BUG B 只半修**：立面 sill/head 用了 bbox，但**平面窗宽/位仍用 xscale/insert** = 同一反模式没根治。

## 据此实施的硬化（commit 见下，274 测绿）
1. **[Codex must-do #1] 平面窗宽/中心改用 `bbox.extents` 沿立面轴**（根治 BUG B 那一类 scale/insert≠绘制尺寸）；
   门仍用 insert+xscale（$DorLib2D$ bbox 含开启弧会高估，xscale=标称叶宽）。**实测窗宽与 xscale 完全一致(2.4/1.2/3.6)**，对窗无损、消除假设。
2. **[#2] 立面窗按 `floor_z` 区间分层**（`_floor_of_sill` 不再硬编码 sill<3.0，泛化多层）。
3. **[#3/#4] `_self_check` 加拓扑+计数硬断言**：4 立面齐 / 每层有 zone / zones 铺满 footprint / 角色无 'room' 兜底
   (= _ROLES 计数对不上则响) / 每窗 count==len(openings) 且逐 opening 有合法 sill/head / 每门有位置。
4. **build 失败要响**：`--write` 时 `_self_check` 有问题**拒写 gt.json**（绝不晋升坏 gt）。
5. **[#5] BUG A 机制守护**：测试断言两 renderer 所需数据齐全（每 opening 有 x/width/sill/head、每门有位置）+
   `_self_check` 能逮坏（删 sill 必报）+ floor 区间分类。新增 3 测。

## 留作未来多 case 泛化（非本张 DXF 障碍，已记）
- 门叶宽/位仍 xscale/insert（bbox 因开启弧不安全，需按图层/图元剔除弧后再 bbox）。
- 立面↔平面 nearest-x 匹配假设两图同向同原点（镜像立面需校朝向单调性）。
- 魔数 8000/9000/300/400 是本图容差，泛化时应对 title/footprint/extent 自校 + 诊断输出。
- 两 renderer 仍是两份代码读同一 gt；schema 完整性 + 一致性测试已守，彻底归一需共享几何归一层（未做）。

## 结论
对**当前这种形式的天正 exploded DXF**，产出方式现已**固化、自校验、失败要响**；用户报的两 bug 的**机制类**
（render 用立面级/无门位 + scale/insert≠绘制尺寸）已根治到平面窗+立面+schema+断言层。门叶/匹配/魔数的泛化硬化
留作多 case 时做。sm21 gt 不变（值全对），274 测绿。
