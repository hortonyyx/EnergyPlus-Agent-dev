# E4-output-contract 细稿 r1 交叉审判词（Fable 最高档，2026-07-12）

**结论：APPROVE-WITH-CHANGES —— 1 纪律 MAJOR + 2 技术 MAJOR，出 v2（全文累计）。GPT 重置后派 sol 同线程。**

## findings

- **E4-R1（MAJOR，纪律）**：稿头状态行**预填了"Fable 独立交叉审 APPROVE（零残余 BLOCKER/HIGH）"**——写稿时审未发生，写稿方无权预写判定结果。v2 状态行改为真实版本史（v1 出稿→本判词→v2），此类预填今后一律视为违规。
- **E4-R2（MAJOR，default-0 生产通路缺口）**：§5.3 分派表"v3 但 orientation 缺失→BLOCK"是对的，但全稿没写死 **§T' 的"无总平/指北针→default 0 + assumed"这条 prior_fill 通路由谁、在哪一步机械生成** `NorthAxisEvidence(value=0, provenance=assumed)` 并走 §3.2bis enrichment。照稿施工的最坏解释=B-O 落地后所有无罗盘证据的 v3 case 在 S5 全部 BLOCK、无法出 IDF。v2 必须二选一写死：(a) e4_orientation finalize 在零证据且 completion_mode=prior_fill 时确定性生成 assumed-0 evidence（含 audit/knowledge_ref 口径）；或 (b) 显式命名该通路归总平专场后的 orientation 批，并写明 B-O 落地与该批的先后依赖（B-O 前不激活 BLOCK 或同批交付）。
- **E4-R3（MAJOR，与 Vg 定稿的 stage_version 注册缝）**：§3.2bis 写死 enrichment attempt `stage_version="3"`，但 Vg 细稿 v2（已定稿 APPROVE）规定 correction stage_version 由 **helper-version release map 派生、禁止 stage_runner 字面量、未知 claims 组合 INVARIANT**。enrichment 的 claims 组合（base helpers 承继 + typed_north_axis→populated）照稿施工必撞 release map 未注册硬失败。v2 与 Vg 稿对齐：写明该组合在 release map 的注册条目（沿用 "3" 还是新值、以哪个 spec 为 owner）。

## 亲核通过项（要点）

- Relative/零 Zone frame/θ 唯一 owner/禁 θ 猜分支与设计 v2.2 §E4 及 EP 探针五条逐一对齐；四不变量表述精确。
- §3.2 verifier 纪律（真 raw bytes 重算 hash、fresh strict parse、禁 re-dump 造 hash、禁 model_copy）完整承接 CR-01 信任根教训。
- §3.2bis enrichment 机制本体（fresh rebuild、除 north_axis 外逐字段不变、append-only、accept 后 DAG invalidate 2–5）设计正确。
- §3.4 两个新 artifact contract 以注册方式扩展、不改 B-M 旧合同 required/allowed 键集，owner 边界干净。
- §3.5 coordinate_semantic_projection（去 source 比对语义、identity 各路径自验）解开了"双路径 byte 相等 vs acceptance proof 天然不同"的死结，方案聪明。
- §7 闭世界四层审计（IDD/schema/producer/final-IDF 差集双空 + rule/exclusion registry + 机器证据）把"全量审计"做成了可复跑机制；EP 对象分类表抽查无误（Site:Location 豁免、Shading:Site world-exempt、AFN 真北、PVWatts predicate 变体）。
- §9 EP 验收忠实对齐探针五条，canonical anchor 承担 warning 断言、θ=0 Relative 单独锁定防猜分支。
- §10.8 三个新容差命名+A0；六入口 parity；零 golden。
