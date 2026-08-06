# orchestrator 轻门 · F-13 顶点排序器「停止挪起笔点」

- **日期**：2026-08-06 · **裁决人**：orchestrator（Opus 5，独立执行，未参与施工）
- **被审对象**：F-13 施工席产出（`src/validator/data_model.py` + `tests/test_f13_retire_start_vertex_rotation.py`）
  · 现保全于分支 **`f13-wip-2026-08-06` @ `bc4f9d4`**（⛔ 标记 NOT_FOR_MERGE）
- **派工单**：[`request/2026-08-06_f13_retire_start_vertex_rotation_dispatch_claude.md`](../request/2026-08-06_f13_retire_start_vertex_rotation_dispatch_claude.md)

## 裁决：**⛔ 否决（REJECT）** —— 修法引入静默物理错误

> **全仓 2243 passed / 10 xfailed / 0 failed（零回归）· Pre-EnergyPlus 门 104 issue → 0
> · 端到端首次跑到 `EnergyPlus Completed Successfully, 0 severe, 6 warnings`
> · `VERTEX_WINDING_REVERSED` 全程 = 0。**
> **这些全部为真，且掩盖不了下面这条：那次跑出来的数值不可信。**

---

## 1. 病灶

IDF 声明 `GlobalGeometryRules → UpperLeftCorner, Counterclockwise`。
**EnergyPlus 信任这句声明**去推每个面的 `~Width` / `~Height`（进而喂外表面对流计算）。
**被 F-13 砍掉的「挪起笔点」正是在让这句声明成为真的。** 砍掉之后声明变成谎话。

---

## 2. 实证（全部本地 EnergyPlus + 只读脚本，**零 LLM 成本**）

**⭐ 解析器自校验**：对账脚本 `wh_audit2.py` 内置「逐面面积与 EnergyPlus 报告值一致」检查，
**三次实验均 115/115 通过** —— 只有自校验通过才采信结果。
（**首版脚本有解析 bug**：`FenestrationSurface:Detailed` 的 `Multiplier`/`Number of Vertices`
等前置数字字段被「取末尾连续数字」的启发式吞进顶点，窗被算成 7.30m 宽。
⇒ **教训：对账脚本本身必须先有自校验，否则它只是另一个没被验证的断言。**）

| IDF | 声明 | 垂直面(墙+窗) 判对 / 判错 |
|---|---|---|
| **07-02 老件**（排序器在，强制左上角起笔） | `UpperLeftCorner` | **79 / 0** ✅ |
| **F-13 之后**（今天） | `UpperLeftCorner`（原样未动） | **3 / 76** 🔴 |
| F-13 数据 + **只改声明这一个词** | `LowerLeftCorner` | 79 / 0 |

判据：垂直面真实高 = z 跨度、真实宽 = 水平跨度，与 eio 的 `~Width`/`~Height` 对账（容差 0.02m）。
样例：`Z01_W1` 实为 4.40m 宽 × 3.00m 高，F-13 之后 EnergyPlus 认为 **3.00 宽 × 4.40 高**。

**另一独立证据**：同一份 IDF **只改这一个词**重跑，
**csv 有 36% 数据格不同、最大相对差 100%**（某区负荷一边 0、一边 5495 J）
⇒ **该字段不是注释，真的进物理计算。**

### ⛔ 中途一个假设已被证伪
曾假设「EnergyPlus 会自己按声明去找那个角 ⇒ 属声明配对（UpperLeftCorner↔Counterclockwise）的**老**缺陷」。
**被 07-02 老件的 79/0 直接证伪** —— 同样的声明、同样的 EnergyPlus 版本，老数据全对。
⇒ **EnergyPlus 不重排，它信任声明。这是 F-13 引入的，不是老缺陷。**

---

## 3. ⛔ orchestrator 认错（本轮第二次框架性出错）

派工单 §2 由我写死：「那段代码做两件事……**(b) 顺手把起笔点挪到它自己认定的"标准角"—— 多余**」。
**这句是错的。** 它不多余，是在兑现 IDF 对外契约。
**用户基于这个错框架做出的那次拍板（「先砍掉多余的那半 + 给另半加计数」）随之作废。**

**⇒ 新增自检（写进 [[stop-and-report-catches-dispatcher-errors]] 同族纪律）：
删除一段「看起来多余」的规范化之前，先找出它在为哪一份对外契约服务。**
本例中那份契约就写在产物自己的头部（`GlobalGeometryRules`），**查一眼就能看到，我没查。**

**⚠️ 施工席无责**：它严格照单施工，锁与 neuter 都做对了（见 §4），错在派工单的前提。

---

## 4. 施工质量本身（与裁决分开评价）

- **实现好**：Newell 法从顶点顺序本身导出法向（与外部参考无关）· 反转保起笔点
  `[A,B,C,D]→[A,D,C,B]` · 退化面（近零面积）不猜直接放过 · 废弃函数留着只加注释（最小手术）。
- **锁与 neuter**：4 条锁 + neuter 自验（换回缺陷本体，逐字节复原）。
- **⇒ 「绕向计数器 / 日志 / Newell 判定」这部分是好的、可留用**；要撤的只是「停止挪起笔点」那半。

---

## 5. 修法（**待用户重新拍板**）

- **路线①（推荐）**：让**内核直接产出「左上角起笔、逆时针」的顶点**
  ⇒ 排序器变恒等 · 严格漂移门自然归零 · IDF 声明为真 · EnergyPlus 宽高正确。
  **一个动作同时解决三件事。** 绕向计数器保留（上游若产出绕向反的仍会被记下）。
- **路线②**：回滚 F-13，改成让**快照存「排序后」的顺序**。
  代价：快照不再是「内核自己算的几何」，且绕向错误在上游即被抹平、门永远看不见。

---

## 6. 本轮登记的其它未排期项

1. **F-14 候选**：`tests/test_zone_agent.py` 无任何 mock（`tests/` 下无 `conftest.py`）、单跑 13.5s
   ⇒ **真调付费 API**。全仓绿额外依赖 API 可用性与凭据，**每跑一次全仓都在烧钱**，且是天然 flaky 源
   （已实际造成一次基线红）。机械扫描确认**同类只此一条**。
2. **接地面无地温输入**：`.err` 报 `Surfaces with interface to Ground found but no "Ground Temperatures" were input`
   ⇒ EnergyPlus 用默认 18℃，影响结果准确度。
3. **World 坐标系下非零 North Axis 被 EnergyPlus 忽略**（`.err` 明示）。今天是 `world_legacy`、North Axis=0 无碍，
   但项目的 `relative_north_axis` 模式将来会撞上。
4. **环检测计数缺口**：老排序器还顺带把**乱序顶点按质心角度排回一个环**（自交「蝴蝶结」会被悄悄修好）。
   F-13 一并移除了这层安全网。⇒ 按「先仪表化」思路应补一个**检测计数**（不修、不 raise）。
   **⚠️ 这条同样是我派工单漏写的第三件事。**
