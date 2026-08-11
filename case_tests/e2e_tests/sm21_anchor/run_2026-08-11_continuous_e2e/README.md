# run_2026-08-11_continuous_e2e — 这个 run 是测什么的

> **性质 = 非正式工程验证跑，⛔ 不是成绩跑**（用户 2026-08-10 定：「这种非正式的都不用记，
> 写明是测什么就行了」）⇒ ⛔ 不走 `flow --record`，无 `baseline.json`、无 `report/REPORT.md`。
> 识图本轮一次没跑 ⇒ **本 run 不产生任何识图成绩**。

## 测什么：一条上一个 run 拿不到的证据

`run_2026-08-09_f18_e2e_verify` 虽然走完了全链，但它是**分三次、跨两天**推完的，
其中 **1_correction 跑在 08-09 的老代码上**，而 F-19（`d103c3e`）与 F-20（`3303eee`→`217d71f`）
两个修法在那之后才落库 ⇒ **「今天的代码从头连续跑一遍还通不通」从未被验证过。**

**本 run = 一次 `flow` 调用，`--from auto --to 5_intakeoutput --with-ep`，中途不停、不修、不续跑。**

与上一个 run 的**唯一变量 = 代码基线前移 + 一次性连续执行**（识图输入逐字节相同，`diff -rq` 校验过）。

## 结果：✅ 一次调用走完全链

真实退出码 **0**（⚠️ 以命令自身的 `.rc` 文件为准，不看后台通知）。单次调用内依次：

```
[0_reading] pass → [1_correction] pass → [2_modelling] pass
→ [3_split_pairing] awaiting_geometry_approval → (auto) → pass
→ [4_mep] pass → [5_intakeoutput] pass → EP complete
```

**EnergyPlus Completed Successfully — 4 Warning; 0 Severe Errors**（5.51 秒）。

`validate_case` 全量 **176 项、`blocked: False`**；非 PASS 7 条与上一个 run **完全同一批**
（0_reading 六张图各一条 `dimension_chain_closure` + 1_correction 一条 `evidence_debt_coverage`），
**均属识图产物自带、非本轮引入**。

## ⭐ 几何验收：digest 不同，但几何逐位相同

run_config 里写死的验收条件是「geometry digest 必须等于用户 2026-08-10 当面确认过的
`3409f90b…`，不同则不得声称已确认」。**实测 digest = `f05e8187…`，不同。**
按条件停下核查，结论如下：

| 比什么 | 结果 |
|---|---|
| **全部顶点坐标**（`geometry_specs.md` 提取 **460** 个三元组，逐个逐位同顺序比） | **★ 完全相同** |
| 分区边界 | 完全相同（`x[0,7.5] / y[5,8] / z_floor=3.0 / ceiling_height=3.6` 等逐项一致）|
| 唯一差异 | **两个房间的角色标签与名字**：`Meeting` → `Conference`（`Z08_F2_Meeting_NW` → `Z08_F2_Conference_NW`，NE 同）|

⇒ **几何未变，用户的视觉确认合法迁移到本 run。**

**⭐ 由此换来的判据（本轮实犯，写给后来人）**：
**⛔ 不能用 `geometry_checkpoint_digest` 判断「两次跑的几何是不是同一个」** ——
该 digest 是 `hash_obj(kernel_check_report)`（`approval.py:37-54`），
而内核报告里**嵌着房间名**，⇒ **1_correction 的 LLM 换个房间叫法就会让 digest 变**，几何一位没动。
判几何是否相同**必须比顶点**。
（这与 F-20 设计审时 sol 抓到的「往内核报告加任何一行都会让所有历史批准失效」是同一个事实的另一面。）

## 登记：1_correction / 4_mep 是随机档，两次跑不同

本 run 与上一个 run 的差异**全部落在两个 LLM 段**，几何内核零差异：

1. **房间角色**：`meeting` → `conference`（同一批房间、同一坐标）。
   ⚠️ 角色进下游会影响人员/照明/设备负荷 ⇒ **两个 run 的能耗结果不可直接对比**。
2. **EP 警告 18 → 4**：唯一差别是 `GetInternalHeatGains: People` ——
   旧 run 每区一条共 14 条，本 run **一条没有**；其余 4 条两 run 完全相同
   （无 Timestep 对象 / 无设计日 / 天气文件位置覆盖 IDF Location /
   **接地面无地温输入** ← 已登记债，EP 用默认 18 ℃）。
   ⇒ 4_mep 这一抽产出的 People 对象比上一抽干净，**属随机档波动，不是修法效果**。

## 登记：`0_reading` 出现两个 attempt，但识图**没有**被重跑

`attempts/001` 与 `002` 的 `output.json` / `checks.json` / `grade.png` / `render_manifest.json` /
`renders/` **全部逐字节相同**；`score_vs_gt.json` 唯一差异是 `attempt` 序号字段本身
⇒ **判卷确定性、识图模型未被调用**。`--from auto` 不静默跳 0_reading，会重跑该段的门与判卷并
归档为新 attempt，属设计行为。

## 输入

- `0_reading/` = `run_2026-08-09_f18_e2e_verify/0_reading` **逐字节复制**（`diff -rq` 校验一致）。
  溯源链：`run_2026-07-07_haiku_cv_retest` → 08-08 f16 → 08-09 f17 → 08-09 f18 → 本 run。
- ⛔ 该识图产物是在「停下等人审阅」的循环里拿到的，**非无监督基线**（CLAUDE.md §1.5#7 违规点①）
  ⇒ 记账门要求的 lane 无可诚实声明，这也是本 run 不走官方记账的原因之一。

## 基点

`b6a3458`，全仓 2361 passed / 10 xfailed / 0 failed。
关键源码指纹见 `run_config.yaml` 的 `provenance.key_source_fingerprints`。
