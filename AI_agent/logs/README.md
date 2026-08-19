# logs/ —— 项目开发的过程痕迹（**非活文档**）

> **定位（硬纪律，2026-07-05 立）**：`logs/` 只放**项目开发过程中的痕迹**——交叉审阅、独立测试、执行日志、
> 审计、诊断。**不承载方案类活文档。**
>
> **判据一句话**：「这文档现在还是某个未完成 / 持续演进设计的**权威源**吗？」
> - **是** → 活文档，**不放这里**，归位到 `proposals/`（没动工的设想）/ `capability/`（能力主线）/
>   `architecture/`（当前稳定架构 + 子系统活规格）/ `reference/`（稳定参考）/ `guides/`（操作手册）。
> - 只是**某次开发步骤的快照**（request brief / Codex 裁决 / 执行日志 / audit / A-B / diagnosis）→ 放这里。
>
> **注**：做完的 proposal **不是**活文档——它是"提了 X→Codex 审→建好了"的冻结痕迹，留在 `reviews/request/`。
> 只有**还活着（open / 被前向引用为权威）**的才拎出去。

## 结构

```
logs/
  reviews/                        交叉审阅（Claude 出方案 → Codex 审 → Codex 执行 的轨迹，见 CLAUDE.md §5#8）
    request/                        我发给 Codex 的 ask：request brief / proposal / execution brief / 原型 reference
    verdict/                        Codex 的审阅裁决输出（*_review.md）
    execution/                      执行日志（*_execution_log.md）
  experiments/                    独立测试：A-B probe · 脚手架/迁移 audit · 模型对照 · reading run · 诊断 · 侦察
                                    （多为 `20xx-xx-xx_*/` 目录 bundle，被 .gitignore 的 `20*_*/` 规则整体忽略）
  worklog/                        **翻篇的日更与状态摘要归档**（2026-08-18 立；从 CLAUDE.md §2 / plan.md 搬出，逐字未改）
                                    ⛔ 非权威口径——与 CLAUDE.md / plan.md 冲突处以后者为准
  renders/                        判卷/demo 渲染图（`20*_*/` 子目录，gitignored 不入库）
  backup/                         历史备份
  downstream_agent_changes.md     **活记录**：本项目侧对下游 subagent 代码的 hotfix（唯一留在 logs 根的活文档，
                                    因它是"运行中的过程日志"而非方案）
```

## 命名约定

- `YYYY-MM-DD_<slug>_request.md` / `_proposal.md` / `_brief.md` → `reviews/request/`
- `YYYY-MM-DD_<slug>_review.md` → `reviews/verdict/`
- `YYYY-MM-DD_<slug>_execution_log.md` → `reviews/execution/`
- `YYYY-MM-DD_<slug>_diagnosis.md` / `_recon.md` / `_investigation.md` / audit bundle 目录 → `experiments/`

## gitignore 提醒

`experiments/` 与 `renders/` 下的 `20*_*/` 目录被 repo 根 `.gitignore:7` 的 `20*_*/` 规则忽略——
它们是本地过程产物，不入库。少数被前向引用的 audit findings（`experiments/*/…_findings.md`、`RECONCILED*.md`）
历史上被 `git add -f` 强制跟踪，移动时用 `git mv` 保持 tracked。
