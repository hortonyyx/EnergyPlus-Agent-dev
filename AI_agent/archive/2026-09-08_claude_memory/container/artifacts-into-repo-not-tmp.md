---
name: artifacts-into-repo-not-tmp
description: 用户反馈：实验产物/渲染图直接落仓库目录，别放 /tmp（用户看不到）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8a9dd69b-c527-4741-8afa-20d239d8a045
---

用户 2026-06-25 明确："别放 tmp 我看不到，直接落出来"。

**Why**：用户在 VS Code 工作区里看仓库文件；`/tmp` 在容器内、用户的编辑器看不到，且易失（重启清空）。我之前把渲染图/readings/掩膜都生成在 `/tmp/sonnet_ab/`、`/tmp/old_scaffold/`，只把少数 montage 拷进 logs，用户要看时全在 /tmp。

**How to apply**：跑实验/渲图/存中间产物时**直接写进仓库内可见路径**（如 `AI_agent/logs/review/<date>_<topic>/`），不要先落 `/tmp` 再补拷。隔离工作区若必须用 /tmp（如盲读子代理的隔离区，见 [[contamination-hard-isolation-requirement]]），产物一产出就同步落仓库。SendUserFile 发图之外，也要保证文件在仓库里供用户自行翻看。呼应 [[run-provenance-recording-requirement]] 的留痕纪律。
