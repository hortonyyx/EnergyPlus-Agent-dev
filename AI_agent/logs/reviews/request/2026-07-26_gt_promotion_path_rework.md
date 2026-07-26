# 返工单：GT 转正通道 r1（主控轻门，2026-07-26）

- 施工方：terra（续同一线程，返工轮免重拍）
- 主控轻门：Opus 5 — 独立全量复跑 + 亲核全部新增/改动代码 + 亲核测试真绑性
- 基线：本批交付 1617 passed / 10 xfailed / 0 failed（施工方报数），主控独立复跑结果见 §0
- 判定：**REWORK**（2 MAJOR / 4 MINOR / 2 项施工方已诚实披露的未竟）

> 施工方**主动停手上报**契约外差异（`sources[0].content_sha256`）与**诚实披露** R3-7/R4-14 未竟，均为正面样板，本单不因此扣分；退回针对的是"门写了但没绑"这一类。

---

## 0. 主控独立复跑

见本单末尾「复跑结果」节（轻门当场填写）。

## 1. MAJOR-1 — 一道声称的门是恒真的（假门）

**位置**：`src/agent/judge/gt_promotion.py:96-97`

```python
data = canonical_gt_v3_bytes(promoted)
if data != canonical_gt_v3_bytes(promoted):  # protects the write/self-check invariant from future drift
    raise ValueError("promotion_canonical_write_drift")
```

**问题**：`canonical_gt_v3_bytes` 是纯函数，对同一个 `promoted` 对象调用两次必然相等 ⇒ 该分支**永不可达**，注释声称的"防未来漂移"保护**不存在**。真正的写入自校已经由第 110 行 `(destination / "gt.json").read_bytes() != data` 承担。

**为何算 MAJOR 而非 NIT**：它不产生错误行为，但它在最高信任资产的写入路径上**伪装成一道门**。本项目已多次因"声称存在、实际恒真"的门吃亏（G8 恒等式假绿是同一模式）。审阅方与未来读者会据注释认为此处有保护。

**出口**：删掉这两行（推荐，第 110 行已是真检查）；或改成真正能失败的检查（例如对**重读回来的字节**再规范化一次比对），并补一条 neuter 证明它可以变红。**不接受**保留恒真分支。

## 2. MAJOR-2 — 语义不变式的锁是自指的（false-lock）

**位置**：`tests/test_gt_promotion_path.py:186` `test_r4_3_neutered_semantic_invariant_turns_red`

**问题**：该用例直接调用 `promotion._assert_promotion_semantics(candidate, verified)` 喂坏输入验其抛错，**完全不经过 `promote_gt_v3` 生产路径**。

**可证伪的具体后果**：把 `gt_promotion.py:94` 的 `_assert_promotion_semantics(candidate, promoted)` **整行删除**，
- `test_r4_3` 仍绿（它不调用 `promote_gt_v3`）；
- `test_r4_2` 也仍绿（promote 本来就不改几何，删掉守卫不改变结果）。

⇒ 守卫被摘掉**无任何测试变红** = false-lock。而它保的正是本批最重要的不变式：**转正不得偷改几何**（细稿 §5.3 末）。

**出口**：改成经生产路径的真变异。至少两条：
1. `monkeypatch` `promotion._verified_document` 令其返回一个**几何被改**的文档 → 断言 `promote_gt_v3` 抛 `promotion_semantic_invariant_failed`，且目标目录**未被创建**；
2. 一条等价于"删掉第 94 行守卫调用即变红"的证明（fresh-process 源码变异，或把 `_assert_promotion_semantics` monkeypatch 成 no-op 后断言上一条用例变红）。
保留现有的直调守卫用例无妨，但它**不计入** R4-3。

## 3. 施工方已披露的未竟 —— 本轮必须补完

- **R3-7**：签署工具每条前置的逐条 fresh-process neuter 表（每条前置 neuter 后**只**红对应用例）。
- **R4-14**：promote 每条前置同上。
- **R4-15**：sm21 资产独立逐字节 snapshot（`case_tests/test_baseline/gt/sm21_anchor/**` 在整批测试运行前后 hash 相同）。现状"全仓绿即算"不足以证明**没被写过又被写回**。

> 这三项是本批**验收纪律的命脉**。上两批（转换器 P0-P2、返工轮）都栽在"九门大面积 false-lock"上，MAJOR-2 说明同一模式在本批已经复现了一次。

## 4. MINOR（本轮一并处理，或明确说明为何不处理）

- **MINOR-1**：`gt_promotion.py:28` `_approved_target_root` 把**整个系统临时目录**当作合法答案根白名单。真实受保护根策略未被放宽（其它路径 raise），但"任意 /tmp 路径都能产出一份看起来已转正的答案"是不必要的松口。建议改为显式测试注入（例如仅接受调用方显式传入的、且带测试标记的根），而不是靠路径前缀。
- **MINOR-2**：`tarch_review_bundle.validate_review_index` 只校验 index **列出的**文件存在且字节相符，**不检测包内存在未列入 index 的额外文件**。人核看到的是目录里的图，promote 校验的是清单里的图，两者可能不是同一集合。建议加一条双向完整性检查（或明确写文档说明为何单向足够）。
- **MINOR-3**：`tarch_normalize._save_converter_augmented_dxf` **复刻了 ezdxf `write()` 的内部流程**（`commit_pending_changes` → `add_required_classes` → `update_all` → `export_sections`）。ezdxf 升级若改动该流程，本函数会**静默偏离**库行为。建议：加一条与库默认保存路径的等价性锁（例如同一 doc 两条路径产出除被钉死字段外逐字节相同），或在依赖里钉住 ezdxf 版本并注明。
- **MINOR-4**：`sign_review_bundle` 的 `near_threshold_confirmed=bool(near_faces)` 记录的是"**有没有**近阈值面"，而非"**人确认了**"。当前行为等价（无面时无需确认），但字段语义应绑人的输入 `confirm_near_threshold`。
- **MINOR-5**：签字后的**强制重跑**（`rerun_signed_review_bundle`）没有命令行入口，主控执行链路 ③ 只能手写 python 调库。补一个 CLI（或并入 `gt_promote.py --rerun-first`）。

## 5. 不变的禁区

细稿 §6 全部照旧。特别重申：**不得**把任何东西写进 `case_tests/test_baseline/gt/`；对 sm24 的实际转正由主控亲自执行。

## 6. 复跑结果（主控轻门当场填写）

- 主控独立全量（实测，非采信施工方报数）：`1617 passed, 10 xfailed, 150 warnings in 591.15s` — **0 failed**，与施工方报数一致；相对基线 `1583 passed / 10 xfailed` = **+34 绿、xfailed 不变、零回归**。
- 禁区核查：`git status --short case_tests/` 为空 ⇒ sm21 资产与 `gt_sources/`、`case_data/` 未被触碰；`.gitignore` 未改；`case_tests/test_baseline/gt/` 未被写入。
- 亲核 diff 范围：`tarch_normalize.py`（WP-1 局部、纯函数、不动全局、不改读取路径）+ 4 个新文件 + 2 个新测试文件；未见越界改动，未碰 sm21/gt_sources/case_data/.gitignore。
