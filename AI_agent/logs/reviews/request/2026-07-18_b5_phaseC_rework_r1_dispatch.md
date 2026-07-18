# B5 Phase C 返工 r1 派工单（sol 施工 → Fable 复验）
2026-07-18 · Opus 主控 · 承 Fable r1 REWORK（0 BLOCKER / 2 MAJOR / 2 MINOR / 4 NIT）

## 结论：纯补测试锁，零算法改动
Fable 对抗审判 **REWORK**，但**算法层与信任根全部实证为真**（4/4 活体探针阳性：负轴 sort→红 / parent normal 门→红 / kernel verts 等值门→红 / judge contract 门→红；零 fail-open、零真 bug、LINE-7 延后正当）。唯一缺口 = 本批新增的两簇 spec 点名**安全拒绝分支全仓零测试锁**（缺锁=未交付，同 Phase B r1 标准）。**返工范围窄：只逐分支补独立拒例测试，不动任何算法/生产码。**

判词全文（逐分支修法清单在内）：`AI_agent/logs/reviews/verdict/2026-07-18_b5_phaseC_review_r1.md` —— **先读它的 MAJOR-1/2 两节**。

## 必做（MAJOR-1/2，逐分支独立锁，缺一条=仍未交付）

**MAJOR-1 四同步 promotion 拒绝门**：
- `validator/checks/kernel.py:_window_parent_binding`：① `c2_b5_v1` bg + `proof=None` → fail（**反「先接受 output 后补 sidecar」软接线门，最关键**）② legacy bg + proof 非 None → fail ③ unknown contract → fail ④ invalid proof artifact bytes → fail ⑤ unsupported proof type → fail。
- `correction/geometry_validator.py:check_window_host_resolution`：⑥ geom.conflicts 含 `window_host_conflict` → block（spec §10.1 点名条款）⑦ evidence wire 型错 → fail ⑧ artifact evidence 与传入 evidence 不一致 → fail。

**MAJOR-2 versioned serializer 与身份拒绝门**：
- `geometry/specs.py:_selected_contract`：⑨ 显式 contract 与 `bg.geometry_contract` 不符 → raise ⑩ `c2_b5_v1` 窗缺 source/segment/host 三身份 → raise（`building_geometry_dict` 与 `serialize_geometry` **各一处**，两条）。
- `geometry/build.py:build_geometry`：⑪ legacy + proof → raise「legacy build must not receive B5 window host proof」。
- `correction/window_host.py:WindowHostsArtifactV1._hash`：⑫ output 身份 / ⑬ claims·evidence window id 精确相等 / ⑭ 三 identity hash 一致 —— 三条 cross-check 各一锁。
- `judge/score_service.py:score_typed_attempt`：⑮ `b5_output_hash_mismatch` / ⑯ `b5_product_payload_differs_from_verified_output` 两分支。
- `geometry/modelling.py:attach_windows_v3`：⑰ 首个 source↔resolution 集合 totality reject 直接锁（不靠 build 层间接相邻）。

## 顺手清（NIT-1/NIT-2，都在已改文件内，trivial）
- **NIT-1**：LINE-6 补 t>1 上界越界拒例；LINE-8 补 wire normal `(0,0)` 变体拒例。
- **NIT-2**：`judge/score_schema.py:build_product_identity` 把 `getattr(record,"artifact_contract",None)` 改**直取属性**（该字段 required，default None 只掩盖漂移）。

## 延后 Phase D（本轮不动，已登记，别顺手做）
- **MINOR-1**：`build.py:_reverify_window_host_proof` 与 `geometry_validator.py:check_window_host_resolution` 两处裸构造 `VerifiedWindowResolverInputs` 伪 marker（空 bytes）违 §4.4 —— Phase D 用 recompute 专用窄输入型 / `reissue_for_recompute()` 收回。
- **MINOR-2**：v3 pipeline C↔D 硬断（`pipeline.py:materialize_kernel_geometry` / `check_kernel` 未传 proof，v3 走 run_pipeline 在 kernel 段 RuntimeError fail-closed）—— Phase D 派工单显式列 pipeline/check_kernel proof 接线。
- **NIT-3**（candidate output 序列化口径共享 helper）、**NIT-4**（带窗 legacy frozen-byte fixture，归 §13.7）。

## 纪律 & 回报
- 每分支**独立测试**，不得参数化成一次调用只断总失败；fixture 期望 record/hash/verts **手写字面量或冻结文件**，禁调用被测函数生成 expected 自比，禁 `x!=x` 伪检查。
- **别跑全仓 pytest**（沙箱杀长进程，全量归主控轻门）；跑 targeted（`python -m pytest tests/test_c2_b5_*.py -x -q`）确认新锁全绿。
- 回报：新增测试逐条对应 ①..⑰ + NIT-1/2 落点（文件:节点）+ targeted 结果 + 诚实标注是否全锁齐。
