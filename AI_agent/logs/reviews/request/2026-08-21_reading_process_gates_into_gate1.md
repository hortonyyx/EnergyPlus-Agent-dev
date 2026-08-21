# 派工单 · 把四道 reading 过程门接进 gate①

> **状态**：⏸ **待用户拍板后派发**（碰 `src/validator/` ⇒ §5#8 须派工 + 换人审；orchestrator 只出方案）。
> **档位**：工程档（改校验器 ⇒ gate① + 全量绿 + 同族自审；⛔ 不是探索档）。
> **背景全档** → [`../../experiments/2026-08-21_historical_reading_dissection/README.md`](../../experiments/2026-08-21_historical_reading_dissection/README.md)

---

## 一、要做什么

把 `scripts/tool_scripts/reading_process_metrics.py` 里已经验证过分辨力的**四道硬门**，
接进 `src/validator/checks/reading.py` 的 `check_reading_view` / `check_reading_stage`。

| 门 | 判据 | 当前实测命中 |
|---|---|---|
| `reading.zero_product_plan` | 平面视图一扇窗都没有 | 07-05 · F1 · J3 |
| `reading.implausible_opening_width` | 平面洞口窄于 **0.60 m** | A2(0.24) · D1(0.40) · J3(0.20) · T1(0.52) |
| `reading.opening_polarity` | 同一面墙上「洞口之间的空档」CV < 0.05 而「洞口本身」CV > 0.20 ⇒ 疑似把墙垛当洞口 | T1 东墙（F-69）· A2 两面墙 |
| `reading.chain_placement_closure` | 一条链**摆到图上的跨度**必须等于它声称的总长（容差 0.02 m）| 07-08(0.24) · F1(3.80) · G1(4 条) |

⛔ **证据密度（转录标注数 ÷ 笔画数）不在本单内** —— 它 14/14 分得开，但样本 13 个是同一栋楼、
边界只差 0.23，**尚未取得门资格**，现为 provisional。

## 二、为什么这四道值得接

1. **`chain_placement_closure` 补的是现有门的结构性盲点**。
   `_chain_closure`（`reading.py:1069`）查「Σ段值 == 总长」。实证：07-07 与 07-08 对 sm21 顶链的
   转录**逐字相同**（段和 14.76 / 总长 15.00），差别只在把 0.24 m 残量**放进两条 120 mm 无标注隔墙带**
   还是**丢在链尾**。前者收在 15.00、后者收在 14.76，导致 07-08 每个窗依次偏 −0.12/−0.24、丢一扇窗。
   **现有门从结构上分不开这两者。**
2. 其余三道抓的都是**已经真咬过人的坑**（§0.4#4 允许加锁的那一类），且都不依赖 gt。
3. 四道全部**不依赖模型智力**：判据由代码算，模型只需照常产出。

## 三、施工要求

1. **判据实现直接复用 / 迁移** `reading_process_metrics.py` 里的 `_polarity_findings`、
   `_opening_width`、`_chain_placement_findings`，⛔ 不要重写一套并行实现
   （两份实现必然漂移；同族 [[free-correctness-evaporates-when-representation-changes]]）。
   建议把这三个纯函数上移到 `src/agent/reading/` 下的一个模块，脚本与校验器**同源引用**。
2. **档位分级**：探索档 = FLAG（记录不阻断）；golden / regression = BLOCK。
   与本仓既有 `run_profile` 惯例一致。
3. **阈值必须是具名常量 + 注释写明来历**，⛔ 不许内联字面量。
   `MIN_PLAUSIBLE_OPENING_M = 0.60` 是**声明的领域下限**（好夹具最窄 1.19 m、全仓 gt 最窄 0.90 m），
   不是拟合值 —— 注释里要这么写（[[silent-default-threshold-behind-otherwise-conclusions]]）。
4. **每道门配 neuter 实测**：摘掉该门 ⇒ 对应夹具必须变红；⛔ 只跑「加了之后是绿的」不算数。
5. **回归判据（硬性）**：
   ```
   python scripts/tool_scripts/reading_process_metrics.py --fixtures   # 必须 exit 0
   ```
   即：**好夹具只许红它 `known_defects` 里已登记的缺陷，且至少一份坏夹具变红**。
   ⚠️ 07-08 声明了 `CHAIN-PLACEMENT` —— 它**应该**被这道门红，这是正确行为不是回归。
6. ⛔ **不许改任何夹具的 `label` 或 `known_defects` 去让门变绿。** 若某道门红了一份好夹具，
   停下上报，⛔ 不要自行调阈值。

## 四、⛔ 明确不做

- 不动 `_chain_closure`（值闭合门）—— 新门是**补充**不是替换，两者查的不是一回事。
- 不加「证据密度」门（见 §一）。
- 不为 B1 / E1 / G1 那三份抓不住的坏夹具**猜**新门 —— 已登记为覆盖缺口，等新证据。

## 五、验收

- 全仓并行全量绿（当前基线 **2978 + 31 新锁**，14 strict xfail）。
- `--fixtures` exit 0。
- 每道门的 neuter 记录随 diff 提交。
- 跨家族审（施工非 Claude 家族 ⇒ 审用 Claude；反之亦然），审阅只看原始需求 + diff + 测试输出。
