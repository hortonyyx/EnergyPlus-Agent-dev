---
name: no-stray-files-in-repo-root
description: 2026-07-26 用户硬规矩——未经授权不许在仓库根目录落文档/目录；过程痕迹一律归 AI_agent/logs/，根目录只留 README/main.py/pyproject/uv.lock + 既有目录
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4d3b4934-21a3-45a9-97a2-c67b2bdc0336
  modified: 2026-07-26T15:45:26.153Z
---

**2026-07-26 用户定（硬规矩）**：**不许在仓库根目录无授权落文档或新目录**。根目录只该有 `README.md` / `main.py` / `pyproject.toml` / `uv.lock` + 既有目录（`AI_agent/ backup/ case_tests/ data/ docker/ scripts/ skills/ src/ tests/ tests_scripts/`）。过程痕迹（派工单/执行日志/裁决书/实验产物）一律落 **`AI_agent/logs/`** 下对应子目录（纪律见 `AI_agent/logs/README.md`、索引见 CLAUDE.md §6）。

**Why**：用户当场发现根目录多出 `logs/` 与 `output/` 两个目录（自己没建、也没批准），要求归置并立规矩。根目录是用户每天看的门面，散落目录会让人分不清哪份是权威文档；且与 [[logs-reorg-process-only]] 定的「过程痕迹只在 AI_agent/logs」口径冲突。同型于 [[artifacts-into-repo-not-tmp]]（产物要落在用户看得见的正确位置），方向相反：**正确位置 ≠ 随便哪儿都行**。

**How to apply**：
- 自己写文件前先问「这属于 `AI_agent/logs/{request,verdict,execution,experiments}` 哪一格」；临时文件走 scratchpad，别落仓库根。
- 派工单里对执行档写死允许写入路径清单（本轮 GLM 就抓到施工方越界改 `AI_agent/guides/`）。
- **已清理（2026-07-26，`bb6d509` 之后）**：根 `logs/reviews/` 里 5 份 07-06 审轨 `git mv` 进 `AI_agent/logs/reviews/`（无引用破坏）；`output/logs/` 478 个**零字节**日志删除。
- **✅ 全清完毕（2026-07-26 同日续批·GLM 施工 / sol 审 APPROVE 零 finding / 主控轻门 1671 绿 **0 skipped**）**：根 `logs/` 与 `output/` **都已不存在**；测试真正依赖的 6 个 JSON（约 80KB）入库为 `tests/fixtures/sm24_review/`（`source.dxf` 不搬——与已入库 `gt_sources/sm24_anchor/source.dxf` md5 相同）；15M 派生件直接删（逐字节可重生成 + 签名证据已随转正入库）。
- **这批攒下的可复用套路**：
  1. **动手前先量「到底哪几个字节是必须保的」**：看着 15M，实际只有 80KB 是活输入、739KB 的 DXF 还与已入库副本 md5 相同 ⇒ 大部分"不敢删"其实是没量过。
  2. **夹具落点不能日期命名**（`.gitignore:7` 的 `20*_*/` 吞掉一切 `20xx_xxx/`；`AI_agent/logs/experiments` 下那 39 个跟踪文件是当年 `git add -f` 硬塞的，**别效法**）；验收必须 `git check-ignore` 每个夹具文件都无输出。
  3. **搬夹具的命脉验收 = 「把夹具改名，相关用例必须硬红不许 skip」**（本批实测 29 failed + 50 errors + **0 skipped**）；全仓读数要看 **0 skipped**，不然就是"绿着空跑"。
  4. **派工单前提可能是错的**：本批要求删 `.gitignore` 的 `output/` 行，实测它是**全局**规则、删后 16 个既有 e2e output 目录冒成未跟踪噪音 ⇒ 主控裁定保留。**GLM 停下上报而非硬做/偷改 = 样板行为**，值得在派工单里明写「发现前提错就停下上报」。
- **📌 残留债**：① `convert_idf` / `run_agent` 仍以 `output/` 为默认输出（`output/idf/`、`output_dir=Path("output")`）⇒ 显式跑这两个命令时根 `output/` 会重现；要永久干净得改默认值。② `test_gt_overlay` 里 sm21 那几条 `skipif(_HAS)` 缺资产时是 5 skipped + exit 0 而非硬红（资产受跟踪故当前无害·主控与 sol 独立认定同一处"最脆"）⇒ 下次碰该文件改 assert。
