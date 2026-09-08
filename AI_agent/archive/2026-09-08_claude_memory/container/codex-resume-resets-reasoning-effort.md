---
name: codex-resume-resets-reasoning-effort
description: codex 的 reasoning effort 默认值靠不住（resume 会静默降到 low；⭐ 全新启动也会——默认值是按模型来的），必须显式钉+回读横幅
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 53d05c89-0efb-4c2a-8620-6fd4187f91c0
  modified: 2026-09-06T12:59:52.886Z
---

`codex exec resume <SESSION_ID>` **不继承原会话的 reasoning effort**，静默降到 `low`。
2026-09-05 续 astra 的 A-6 会话时实测：原会话是 `xhigh`，resume 起来日志写 `reasoning effort: low`。

**Why:** 续会话恰恰是用来补「要动脑的那一段」的（自设同形输入、逐句强制对账），低档直接掉质量；
而且它**不报错**，只在启动横幅里印一行，不盯就过去了。这是「观测量的缺席把多种原因压成同一个空白」
的一个实例 —— 你以为在用 xhigh，其实没有任何东西告诉你不是。

⭐⭐⭐ **2026-09-06 扩写：不止 resume —— 全新启动同样靠不住，因为默认值是【按模型】的。**
当天派 E-a′ 给 `gpt-6-astra`，用 `scripts/seat_gpt.sh`（**没传 effort**）**全新**起一个席位，
横幅是 `reasoning effort: low`；而历史 GPT 席位日志（`gpt_o21d` / `gpt_f156v3` / `gpt_m4_v3`，都是 gpt-5.x）
横幅**全是 `high`**。⇒ ⛔ **不是启动器一直坏、也不是 resume 专属** —— **同一个脚本、同一条命令，换个模型默认档就变了**。
⭐ 判别签名 = **同脚本历史日志 vs 本次日志的横幅不同**；只看本次会误判成「一直如此」。
已修：`seat_gpt.sh` 显式传 `-c model_reasoning_effort=${CODEX_EFFORT:-xhigh}` **并回读横幅比对**
（asked ≠ got 就响亮报错）—— ⭐ **要一个档 ≠ 拿到那个档，必须回读**。

**How to apply:**
- ⭐ **全新起席位也要显式钉 effort**，⛔ 别信默认；起完**回读横幅**核 `model:` / `reasoning effort:` / `session id:`。
- 续会话一律显式钉：`codex exec --sandbox danger-full-access --skip-git-repo-check -m <model> -c model_reasoning_effort="xhigh" resume <SESSION_ID> -`
- ⛔ **选项必须放在 `resume` 子命令之前**；写成 `codex exec resume <id> --sandbox ...` 会报
  「to pass '--sandbox' as a value, use '-- --sandbox'」，因为选项被当成 prompt 位置参数。
- 起来后**读启动横幅**核 `model:` / `reasoning effort:` / `session id:` 三行，⛔ 别假设。
- session id 在席位工作目录的 `.seat/seat.log` 里能翻到。

配套：[[gpt6-astra-takes-large-blocks]] · [[seat-quota-failure-leaves-silent-orphans]]
