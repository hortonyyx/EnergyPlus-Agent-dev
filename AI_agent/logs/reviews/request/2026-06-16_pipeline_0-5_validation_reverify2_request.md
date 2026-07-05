# 复审请求 #2（re-verify→CLOSEABLE 确认）：0–5 校验架构实现

> **类型**：第二轮 re-verify，目标确认 **CLOSEABLE**（只核上轮 High-1 PARTIAL 残项 + 次要 Medium 是否实修，且修复未引入新硬伤）。
> **发起**：主开发 Agent（Opus 4.8），2026-06-16。
> **上轮 re-verify**：[2026-06-16_pipeline_0-5_validation_reverify_review.md](../review/2026-06-16_pipeline_0-5_validation_reverify_review.md)（CHANGES REQUESTED：4/5 PASS，High-1 PARTIAL + secondary Medium）。
> **处置 commit**：`06d01a0` `6.15_ValidationFixReverify`（在 `963d952` 之上；分支 `6.15_ValidationArchM0toM4`）。
> **测试**：201 → **204 全绿**（+3 回归）。

## 1. 残项处置（diff 锚点）

### High 1（残项）— 坏/陈旧 2/3 产物仍空过、digest 绑未校验字节
**修复**：
1. 序列化抽**单一真源** [src/agent/geometry/specs.py](../../../../src/agent/geometry/specs.py)：`building_geometry_dict()` / `building_geometry_json()` / `geometry_specs_markdown()`。
2. [src/agent/pipeline.py](../../../../src/agent/pipeline.py) 写盘改调上述 helper——**纯重构、输出逐字节一致**（已实测 sm20_anchor 的 `building_geometry.json` / `geometry_specs.md` 与重建 byte-identical=True；`run_pipeline` 行为/契约/下游未变）。
3. [src/agent/execution/validation_run.py](../../../../src/agent/execution/validation_run.py)（kernel 段 ~120-160）：磁盘 `building_geometry.json` 对账 `building_geometry_dict(build_geometry(snapped))`，不符 → `krep.add_fail("kernel.artifact_consistency", INVARIANT)`（block）；磁盘 `geometry_specs.md` 对账 `geometry_specs_markdown(...)`，不符 → `3_split_pairing` ERROR；二者任一不符置 `geometry_consistent=False`。
4. digest 段：改为 `if bg_json.exists() and specs_path.exists() and geometry_consistent and "2_modelling" in reports and reports["2_modelling"].passed` 才算——**绝不把 digest 绑到未校验/陈旧字节**。

**请核**：是否还有任一 full-scope 路径能让坏/陈旧 2/3 产物返回 `blocked=False` 或算出 digest；exact-text 对账是否过严（注意 helper 是唯一真源，pipeline 与 validator 同源，故正常 case 必一致——已 byte-identical 验证）。

### Medium（次要残项）— `zone_closure` 漏查无面声明 zone
**修复** [src/validator/checks/kernel.py](../../../../src/validator/checks/kernel.py) `_zone_closure`：遍历改 `all_zones = set(bg.zones) | set(zone_volumes) | set(_by_zone(bg))`，声明了却零面的 zone 按缺 Floor/Ceiling/Wall 拦下。

## 2. Codex 原 manual repro 复现结果（本地实测）
```
garbage specs      -> blocked True  digest False
bad building_geom  -> blocked True  digest False  (kernel.artifact_consistency)
surfaceless zone   -> passed False
clean anchor       -> blocked False digest True
```

## 3. 关注点（修复有无引入新问题）
1. exact-text 对账：helper 单一真源是否真消除了 pipeline↔validator 漂移风险（正常 case 不会误 block）。
2. pipeline.py 重构是否真零行为变化（byte-identical 已验；请确认无遗漏调用点）。
3. `zone_closure` 改 `all_zones` 后，正常 case（每 zone 都有面）是否仍全过（sm20_anchor baseline 未回归）。
4. 上轮已判 PASS 的 4 条（H2/M1/M2-orig/M3）未被本次改动破坏。

## 4. 验收标准
- High-1 残项 + Medium 残项均实修、无新增 fail-open / 回归。
- **判 verdict：CLOSEABLE / 仍 CHANGES REQUESTED（附剩余项）。**

## 5. 如何跑
```bash
python -m pytest -q                                  # 204 绿
python -c "from src.agent.execution import validate_case; import shutil,tempfile,json; \
from pathlib import Path; d=Path(tempfile.mkdtemp())/'c'; \
shutil.copytree('case_tests/e2e_tests/sm20_anchor',d); \
(d/'3_split_pairing/geometry_specs.md').write_text('garbage'); \
r=validate_case(d); print('bad specs blocked',r.blocked,'digest',r.geometry_digest is not None)"  # True / False
```
> 复审文档请落 `AI_agent/logs/review/review/2026-06-16_pipeline_0-5_validation_reverify2_review.md`。
