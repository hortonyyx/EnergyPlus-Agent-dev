# 返工单 r1 · 硬隔离脚手架批（主控轻门发现）

> 主控 Opus 5 · 2026-07-31 · 承 [派工单](2026-07-31_isolation_scaffold_construction_dispatch.md)
> 施工方 GLM-5.2 已在 S2 的 review-ask 中**主动登记**本条边界、未自行加宽 —— 处置正确，本单是主控的裁定，不是对施工的问责。

## R1-1 · S2b 的路径判定用「整串形状」，令 F-4 的修法在真实产物上仍会触发（MAJOR）

**施工方登记的原话**：`_looks_like_path` 对「整串」判定，故 content 整串不含 `/` 时才免扫；
整串里恰好含 `/` 时仍会被当路径扫到 `grade` 等。施工方判断「现实 reading 产物整串含 `/` 罕见」。

**主控实测推翻该乐观估计**（探针见下）：

| content | 结果 |
|---|---|
| `Found ~18 candidates; the grade line sits at z=0.` | **ALLOW** ← 07-30 原始案例已修好 |
| `Windows on 2026/07/31: grade line at z=0, span 1.2 m.` | **DENY: forbidden token: grade** |
| `North facade: sill 0.9 m, head 2.4 m (ratio 3/4).` | ALLOW |

精确的残留条件 = **content 里同时出现任意一个 `/` 与任意一个禁词**。
`reading_summary.md` 是整篇 markdown 作为一个字符串传入，**一个日期 `2026/07/31` 就足以触发**；
`m/s`、`N/A`、提到任何路径同理。⇒ 该缺口在复验轮上大概率复发，且复发形态与 F-4 完全一致
（必交产物写不出来 → 被误读成「模型不会写总结」）。

**裁定（修到根因，不是再加豁免词）**：
`content` 角色的参数 —— `content` / `new_string` / `old_string`（以及同类文本体参数）——
**整个排除出路径形状扫描**，一个字符都不扫。

理由：S2a 已经按**真实 `file_path`** 做了写保护（`_write_target` + `_check_write_target`），
写到哪里由参数角色决定、与文本内容无关 ⇒ **扫 content 的增量安全价值为零**，
而误伤代价已两次活体证实。判定应当**按参数角色**，不是按字符串长相 —— 这才是派工单
§3-S2b「路径类禁词只作用于被识别为路径的参数」的原意；「整串 `_looks_like_path`」是我骨架写窄了。

**必须新增的锁**：
1. 上表第 2 行（日期 + `grade line`）⇒ **ALLOW**。
2. 写保护不受影响的负锁：`Write` 到 `tools/run_cv_probe.py`，且 content 是纯净散文 ⇒ 仍 **DENY**
   （证明放松的是内容扫描、不是写保护）。
3. `Bash` 的 `command` 仍走原严格全串检查 ⇒ 含 `case_tests` 的命令仍 DENY。

## 探针（可复现）

```bash
mkdir -p /tmp/gp/out && cp src/agent/execution/isolation_templates/guard.py /tmp/gp/ && cd /tmp/gp
python - "Windows on 2026/07/31: grade line at z=0, span 1.2 m." <<'PY'
import json,subprocess,sys
payload={"tool_name":"Write","tool_input":{"file_path":"out/reading_summary.md","content":sys.argv[1]}}
r=subprocess.run(["python","guard.py"],input=json.dumps(payload),capture_output=True,text=True)
print(("DENY: "+r.stderr.strip()) if r.returncode==2 else "ALLOW")
PY
```
