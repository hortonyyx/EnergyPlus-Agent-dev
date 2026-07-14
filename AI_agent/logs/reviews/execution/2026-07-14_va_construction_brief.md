# Va 批施工执行简报（2026-07-14）

## 改动映射（施工稿章节 → 文件 / 测试）

| 施工稿章节 | 落点 | 验证 |
|---|---|---|
| §2–§7（wire、纯核、interval、identity、direction、ledger） | `src/agent/correction/facade_applicability.py` | `tests/test_c2_va_applicability.py` |
| §10/§11（Va 专属、import-order、包级环禁令） | `tests/test_c2_va_applicability.py`；`correction/__init__.py` 未改 | Va 专属组的 strict/identity/direction/negative/property/import-order 断言 |
| §12（A0 合同登记） | `skills/intake_pipeline/1_correction/A0_contract.md` | 文档审阅 + Va 常量断言 |
| §0.3 已收录依赖门 | 无代码改动 | 静态机械断言；真实 v3 finalize/Vg 回归组 |

## 备份

修改既有 A0 文件前，已备份至
`backup/src_history/2026-07-14_va_construction/skills/intake_pipeline/1_correction/A0_contract.md`。
未修改既有 `tests/`、Vg、manifest、schema 或 `correction/__init__.py`。

## 验收与测试

| 分组 | 结果 |
|---|---:|
| §0.3 静态依赖门（claims/manifest/version/file） | passed |
| Va 专属 `tests/test_c2_va_applicability.py`（r1 返工后） | 46 passed |
| Va + Vg + B-M + claims + v3 finalize 定向组 | 272 passed（1 个既有 Pydantic serializer warning） |
| `git diff --check` | passed |

按派单纪律，未运行全量 pytest；该门由主控独立执行。

## 预期行为变化

新增 Va 纯内存 ledger：固定七 claim 输出；plan 正证据绕过 Vg；elevation 只经已绑定 local→world→target→该 target segment 的 Vg visible interval；partial existence 与其他 partial 状态分开；completeness 只生成 negative-evidence audit，不提升正向 applicability。输入身份、segment、frame、claim ledger 与 hash 漂移 fail-closed 为规定的结构化 error code。

## r1 返工（findings → 修复映射）

| r1 finding | 修复 |
|---|---|
| VA-C1 elevation negative family 恒真过滤 | `_relevant_negative` 现直接消费 `bindings[entry.input_id].resolved_building_direction`；新增 South opening + East completeness source 反例，断言 East 不进入 decision。 |
| VA-C2 §11 测试族缺口 | Va 测试从 14 增至 46：补 strict/identity、target closure、16 格 direction XOR、true_azimuth/unknown 正拒、binding cardinality、多 source union、negative 三 source 与多立面过滤、sm26 synthetic、judge/executor parity、B4b seam、purity/concurrency、integer partition oracle、零/一/多 relevant source；既有 Vg/B-M/B2 定向回归同跑。 |
| VA-C3 segment hash preimage 未冻结 | A0 §4.1 明记完整 `FacadeSegment.model_dump(mode="json")`、排序键、family rank、JSON 编码及 SHA-256 口径。 |
| VA-C5 item 15 测试名实不符 | touch 零覆盖与 adjacent merge / real-gap 不桥接拆为两个名称和断言一致的测试。 |

### §11 测试族状态

§11 #1–#30 均已有 Va 专属或既有依赖回归落点；#31 的全量 pytest/strict-xfail 权威门依派单仍由主控独立执行，施工侧确认零 golden 改动并完成定向组。无其他静默未竟。

## 未决·偏离事项

- 无代码范围偏离；未改 golden、运行编排、reader、gt、judge、scorer、render 或 B4b。
- 全量 pytest 未由施工者运行（派单明确主控独立权威门）。

## review-ask

请 Opus 执行审重点抽查：多立面 negative-only source 是否只保留 resolved family 相同的 binding，以及 A0 冻结的 segment-hash preimage 是否可由独立 adapter 逐字复现；true-azimuth/unknown 保持纯 binding 消费，不新增 sidecar I/O。

## r2 VA-C6 微补

- 仅修改 `tests/test_c2_va_applicability.py`（及本执行简报）；未动 Va 实现、A0、golden、gt 或 `correction/__init__.py`。
- 16 格 N/S/E/W × mirror × local-convention 改为手写冻结 sign/origin/两端 world 值；每格实际调用 `derive_opening_claim_applicability`，断言 mapped interval、visible coverage 与 status。
- 补 §11.7 local `x=0/x=2` 两端映射逐格断言；补 §11.10 的 wrong `world_axis`、wrong `along_origin`、`source_footprint_fingerprint` drift 三拒例，且每例先重算 frame hash 以避免仅命中 stale-hash 路径。
- Va 专属组：**49 passed**；全量 pytest 仍由主控独立权威门执行。

### r2 review-ask

请复审抽查方向矩阵的期望表未复用 production XOR 推导，且每行均通过公共 `derive_opening_claim_applicability` 而非只校验 binding 字段。VA-C7 为 B4b 挂账，本批未施工。
