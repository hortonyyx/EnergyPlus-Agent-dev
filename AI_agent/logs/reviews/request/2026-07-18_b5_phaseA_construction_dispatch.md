# B5 Phase A 施工派工单（terra 施工 → Opus 子代理审 → 主控轻门）
2026-07-18 · Opus 主控 · C2 收官关键路径 · B5 施工第 1 批（共 4 Phase：A→B→C→D）

## 0. 分工 & 流程（用户 07-18 拍额度侧=terra 施工）
- 施工：**terra**（GPT 侧）。
- 施工审：**Opus 子代理**升一档（独立上下文、活体探针）。
- 主控轻门：Opus 独立全量 pytest + 亲核 diff/探针。
- 谁写谁不批（terra 写 → Opus 审，跨厂商）。

## 1. 本批范围 = B5 **Phase A** only（§14 Phase A，gates B5-A1..A7）
**绑定施工合同**（自读全文、施工-ready、累计式自包含）：`AI_agent/proposals/c2_b5_detail_spec.md`（v3 定稿，1612 行）。

Phase A 施工项（§14 Phase A 原文）：
- 三 tolerance + A0 登记（§11）；
- source locator/catalog、strict resolver input、ring-free direction facts、**Va 13 字段型 import 固定**（§4.1/§4.2/§4.3；认准 `facade_applicability.py` 的 `ElevationViewBindingV1`）；
- **production current-ring binding helper** + B-M floor-order 合同（§4.5 + §11/§12.2）；
- resolution/conflict/audit/artifact wire 与 hash（§5.2/§5.3/§9.2 的 Phase-A 地基部分）；
- draw contract 拒 producer refs/resolver audit（§4.4）。

**不越界**：纯 resolver 主链（§6）、parent/line/build（§8）、validator/specs/judge 四同步（§10）、E4 rebind/legacy 封口（§9.4/§3.3）归 Phase B/C/D——Phase A 只落 wire/类型/config/helper/hash 地基 + 其拒例测试。

## 2. 测试（§14 gate B5-A1..A7 + §13 对应行）
逐 gate 落齐：`B5-A1-source-identity` / `A2-wire-strict` / `A3-config-a0` / `A4-va-type-import` / `A5-hash-vectors` / `A6-current-ring-binding-parity` / `A7-draw-link-rejections`。
- **hash 冻结向量（A5）= 手写字面量、禁调 production helper**（禁自指假绿，spec 已钉）。
- **draw/link 拒例 SRC-C1..C10（§13.1，A7）= 逐条独立测试，不许合并成一次调用只断总失败**。
- BIND 组里属 Phase A 的 ring-free direction fact 篡改拒例（A6/A4）。

## 3. 纪律（施工审必打，先做到位）
- **shipped-untested = 连续 8 批头号 MAJOR**：所有安全拒绝分支必须有独立测试锁、负轴不缺；缺一条即视为未交付（§14 明文：不得用现有总绿数代替）。
- **禁自指假绿**：冻结向量手写字面量、不取 production helper 输出。
- **禁 fail-open**：无 broad-except 吞、无 proxy 放行、无自报字段冒充证据。
- **诚实部分交付 > 藏假绿**（B4b Phase B 教训）：做不完就如实报未完成全链，别用伪实现占位充数。
- **v1/v2 legacy 行为不变**：Phase A 加新 wire，不得引入 legacy 回归（legacy 封口在 Phase D）。

## 4. 全量测试归属
**terra 只跑 Phase A targeted tests**（codex 环境 ~30s 杀长进程，全量自验不可得）；**全量 pytest = 主控轻门唯一权威**，terra 不得以自跑总绿数作交付证据。

## 5. 交付回报
产出后回：改了哪些文件（§12.1 新增 / §12.2 修改对照）+ 七 gate 各自测试落点 + targeted tests 结果 + **诚实标注哪些做完 / 未完 / 存疑**。
