# 跨家族复核请求 · 立面判卷绑定（2026-08-22）

**复核席位**：GPT 家族（gpt-5.6-sol）· **施工席位**：GLM（glm-5.3）· **主控**：Claude（不参与施工）
⛔ **只看原始需求 + diff + 测试输出**，不看施工方的长篇自述。

- 原始需求（派工单）：[`request/2026-08-22_elevation_score_bindings_dispatch.md`](2026-08-22_elevation_score_bindings_dispatch.md)
- 施工方执行日志：[`execution/2026-08-22_elevation_bindings_glm_execution.md`](../execution/2026-08-22_elevation_bindings_glm_execution.md)
- diff：工作树未提交改动 —— `git diff` + 新增 `tests/test_elevation_score_bindings.py`
- 施工前全量基线：**2996 passed / 13 xfailed**（提交 `c116322`）

---

## 一、要判什么

判卷此前**无法为立面产出绑定**，因此一份完整的六图识图产物根本判不了分。
本批要让它能产出，并让立面频道真的参与计分。

## 二、施工方声称的结果（**请独立复现，不要转述**）

1. sm24 立面判分通过：`window_elevation_geometry 44/44 pass`，elevation 频道 `applicable`
2. 生成器重产的绑定与手工「已知好」参照 **5/5 逐字段一致**
3. 三把新门都在真实入口/真实夹具上响过（方向反转拒收 · 镜像门好绿坏红 · neuter 摘接线）
4. 全量 **3006 passed / 13 xfailed**
5. sm25 因结构阻塞未通过 —— 施工方按纪律**停下上报**，未绕过

## 三、⭐ 请重点证伪的六条

1. **镜像门是不是一道真门？** 它必须在真实夹具上红过。请独立构造一份**不该红**的产物确认它沉默，
   再确认坏夹具确实红。⚠️ 本项目有过「新门在夹具上一次没响、当场删掉」的先例。
2. **neuter 摘的是接线还是机制？** ⚠️ 主控本轮栽过一次：第一版锁只测 helper，**摘掉接线仍全绿**。
   请对每把锁独立做一次「只摘接线」的 neuter。
3. **`along_origin` 的取法**：施工方用「跨层并集」，而 Va 在
   `facade_applicability.py:462-465` 用**逐层** extent 端点做严格相等比较。
   这两者在单层 case 上恰好一致 —— **请判断这是不是巧合**，以及多层 case 上是否会出别的错。
4. **`mirrored=False` 的依据是否成立**：`normalize_mirror_flag` 对 `"unknown"` 主动拒绝猜，
   所以这必须是有据选择。证据脚本：
   `python AI_agent/logs/experiments/2026-08-22_elevation_mirror_convention/verify_mirror_convention.py`
5. **过渡旗标 `--elevation-fingerprint-union-pending-s1` 是否安全**：它让绑定文件能产出但过不了 Va。
   请判断它会不会让某条路径**静默**产出一份不可用的绑定（本项目对「静默降级」极敏感：F-64/F-68/F-75 同族）。
6. **`affected_tests_rules.yaml` 删掉了一行豁免** —— 请确认删得对，不是为了让某条锁不报。

## 四、必须实测的三件（⛔ 不接受「读代码看起来对」）

1. **端到端**：sm24 立面判分复现（`kind`、`channel_applicability`、`window_elevation_geometry`）
2. **全量**：主树独立跑 `python -m pytest -q -n auto`，与 3006/13 对账
3. **neuter**：见 §三.2

## 五、⚠️ 主控自曝：本轮我出的题错过一条

派工单 P7 我写「judge 侧对 gt 的绑定校验不比对指纹」——**字面为真但以偏概全**，
我只查了 `validate_score_view_bindings_against_gt` 一处接缝就当成判卷全链如此，
实际 Va 侧逐 opening 有另一道严格相等校验。施工方停下上报抓住了它。
**请同样把派工单其余七条前提当作【可能错的】来看**，发现问题直接写进裁决。

## 六、裁决

写入 `AI_agent/logs/reviews/verdict/2026-08-22_elevation_score_bindings_gpt_verdict.md`：
`APPROVE / REWORK / BLOCK` + 逐条（BLOCKER / MAJOR / MINOR），每条附**实测命令与输出**。
⛔ 无实测输出的条目按 MINOR 计。
⛔ 不要修改 `src/` `scripts/` `tests/` 下的文件（neuter 请改完立即改回，并在裁决里写明改了什么）。
