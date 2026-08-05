# F-2c 边界冲突 · orchestrator 裁定（**派工方的题出错了，这次是我**）

- **日期**：2026-08-05
- **上报方**：GLM-5.2（`AI_agent/logs/reviews/execution/2026-08-05_f2c_glm_boundary_report.md`）
- **裁定**：**选项 A，但换个落点** —— 见 §2

## 1. 先认错：派工单 §2 那句是我写错的

我写「复用 `identify_reading_contract`，⛔ 不许新写形状判定」时，**没有核它住在哪个包**。
它在 `src/agent/judge/reading_typed_adapter.py` —— judge 模块；而 B5 A6 硬边界
（`test_c2_b5_source_routing.py:213` + `test_c2_b5_parent_and_verts.py:1162` + 模块 docstring）
明令 `src/agent/correction/` 不得出现 `src.agent.judge`。**照我的单子做，必然撞墙。**
施工席停下上报是对的，**本轮第三次「派工方的题错了」**。

## 2. 裁定：选 A，落点改到 `src/agent/reading/`（不是 `execution/`）

**理由**：被搬的东西是「**识图产物的契约形状**」，它的语义归属是 **reading 契约**，不是编排（execution）。
而且这条依赖边**本来就存在、且合法**：
- `src/agent/correction/window_sources.py:23` 已经 `from src.agent.reading import parse_reading_view`；
- `src/agent/correction/envelope.py:23-24` 也已依赖 `src.agent.reading`；
- `identify_reading_contract` 自身**零 judge 依赖**（只用 `Literal` + dataclass + `ReadingView`）。

**具体**：
1. 把 `identify_reading_contract` + `ReadingContractDecision` + `READING_PRODUCT_CONTRACT`
   + `READING_CONTRACT_DETECTOR_VERSION` 搬到 `src/agent/reading/contract.py`（新文件）并从包导出；
2. `src/agent/judge/reading_typed_adapter.py` 改为**从新位置 import 后 re-export**，
   judge 侧调用点**一字不改、语义零变化**；
3. `window_sources.py` 从 `src.agent.reading` import ⇒ **B5 A6 两条守卫恢复绿，且守卫本身一个字不许改**。

**⛔ 明确否决 B 与 C**：
- **B（就地复刻一个薄形状判定）**= 第二把尺子。本项目已多次栽在这上面（判卷双尺 / 词表双份），不许。
- **C（把 B5 A6 守卫从字符串扫描收窄成 AST）**= 放宽守卫来迁就一次改动，方向错。**守卫一个字不动。**

## 3. 追加一把锁（防止「搬完之后又长出第二个」）

断言**全仓只有一个探测器**：judge 侧那个符号**就是** reading 侧那个对象
（`reading_typed_adapter.identify_reading_contract is reading.contract.identify_reading_contract`），
以及 `grep` 全仓 `def identify_reading_contract` 恰好一处。
⇒ 以后谁再复刻一份，这条锁必红。

## 4. 已完成的部分照收

F-2c-1（merge 写扁平镜像）+ 三把锁 + 四格 neuter **照单收下**，尤其那把
**自己 neuter 出来的假锁**（`StageRunner.record` 后漏 `manifest.save` ⇒ `verify` 在 `accepted is None` 提前退出、
根本没走到比较）——这正是「锁必须落在真实入口」的又一个实例，**写得好**。

## 5. 本轮之后的顺序（**变更**）

1. **⭐ 先做 F-5**（`2026-08-05_f5_window_source_field_names_dispatch.md`）——
   **BLOCKER**：`window_sources.py` 读 `x_range` 而契约是 `x_range_m` ⇒ 任何带窗的合规产物都过不了 1_correction，
   它正挡着用户的主线目标。**这一条最优先。**
2. 按本裁定收口 F-2c；
3. 最后 r4（产品库恢复 review 环）。
