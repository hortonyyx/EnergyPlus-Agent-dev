---
name: gt-standard-artifact-checklist
description: 2026-07-27 用户拍板——以后每份 gt 产物对齐同一标准清单、缺件即红；含 v3 判卷侧车与签名清单口径打架的收口
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d35be1c2-4f94-44e3-8b3a-684b58b6a0f0
  modified: 2026-07-27T07:38:56.658Z
---

**2026-07-27 用户拍板**：**以后每做一份 gt，产物一律对齐同一份标准清单**（`gt.json` / `renders/` / `review/` 签名证据 / **`score_inputs/view_bindings.json`**），**缺件即红**（机械校验，不靠人记）；并补 **provision bridge**（现无把判卷侧车从答案包搬进 run 的代码，`new_case_guide §0.3` 明写「必须人工或由显式脚本」拷成 `<run>/_run/judge_score_bindings.json`）。

**Why**：sm24 端到端开跑当场撞上「v3 case 判卷必须有 judge 侧车、而答案包没有」——**v3 判卷层此前从未在任何真实 case 上跑过**（sm21 走 legacy 路径不需要）。缺件在 regression 档是 fail-closed 硬停（`run_stage.py:1380`），设计正确但无人提前备件。

**How to apply**：做新 gt 时按清单逐项备齐再收工；跑 v3 case 前先查侧车在不在。侧车**可随答案包入库、每 run 复用**（同一 case 的 `provision_view_manifest` 两次产出逐字节相同，实测 sm24 `content_sha256=459513f1…`）；其手性须用**图纸自带尺寸链**独立核（不可拿产物自证）。

**⚠️ 待收口的规矩打架（R-6）**：`new_case_guide §0.3` 要求侧车放 `gt/<case>/score_inputs/`，而受控转正通道要求受保护目录内文件 ⊆ 签名清单 ⇒ 主控 07-27 造的 `view_bindings.json` 既未入 git 又不在 07-26 签名清单内、mtime 晚于人签，**是同族「关键输入不在 git 里」的第四次复发**。处置 = 文件入版本控制（无条件，已办）+ 清单口径归本批统一定。关联 [[no-stray-files-in-repo-root]]、[[judge-identity-and-metric-design]]。
