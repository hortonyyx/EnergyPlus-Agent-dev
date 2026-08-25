# 跨家族复核请求 · 楼层 id 映射层（F-90）

- **日期**：2026-08-25　**对方**：⭐ **GPT 家族**（用户 08-25：「审走 GPT」）
- **档位**：工程档（碰 `src/agent/judge/`）⇒ **审恒升一档**；⛔ **谁写谁不批**
- **被审 commit**：**`3f6731f`**（主树）· 施工报告 →
  [`../execution/2026-08-25_f90_floor_id_mapping_construction_report.md`](../execution/2026-08-25_f90_floor_id_mapping_construction_report.md)
- **原始需求** → [`2026-08-25_f90_floor_id_mapping_dispatch.md`](2026-08-25_f90_floor_id_mapping_dispatch.md)

⚠️ **本 commit 已随分支合入 main**（用户 08-25 令）。⇒ **本轮是「已合入后的补审」**：
若你判 REJECT，处置是**在 main 上另开修复单**，⛔ 不是回退历史。

## 一、⭐ 请重点攻的五条

1. ⭐⭐⭐ **「同根因 5 处」这个判断成立吗？**
   施工席位声称派工单点名的 1 处之外还有 4 处，其中**第 4 处**
   （`opening_claim_score._assign_openings_for_source` 的窗-gt 开口匹配）不修的话
   **不崩、但让满分产物静默判成全部 miss**。
   ⭐ 请独立验证：**把第 4 处的修复单独摘掉**（其余四处保留），一份本该满分的产物是不是真的会被静默判零？
   ⛔ 若摘掉后并不会静默全错，则「5 处」这个论断被夸大，请点明。
2. ⭐⭐ **那十个判据的读数公允吗？**
   施工用的是**自造的干净 fixture**（product 楼层 `"f1"` vs gt `"F1"`），
   其中 `boundary_complete` 是 **fail 32/32**、其余九条全 `not_applicable`。
   ⭐ 请判断：**一个只有一条判据 eligible、且那条还全 fail 的读数，能不能算「真的判出分」**？
   还是它同样可能是另一种形式的「没判」？⛔ 这条是 orchestrator 自己最不确定的地方。
3. **四个边界的响亮失败是真的吗？** 逐个构造反例，验证它们**确实抛错**而不是取默认值：
   `window_host_claim_missing_source_ids` · `window_host_claim_ambiguous_source` ·
   `window_host_source_not_a_registered_plan_input` · `floor_id_maps_to_multiple_plan_inputs`。
4. **「立面不需要处理」这个结论成立吗？**
   席位称立面走几何/指纹推导、**从不比较 `window.floor_id` 字符串**。请独立复核 —— 若它其实也比了，
   那 F-89 与本单的边界就划错了。
5. ⭐ **F-99 的归因对不对？**
   席位说修完 5 处后 sm25 R0 **仍判不出分**，卡在**另一个独立缺陷**：
   产物 facade span 与 gt 分段边界在 L 形内角处差 **约 0.12 m**，16 段里 8 段不归位。
   ⭐ 请验证：**这个 0.12 m 确实与楼层 id 无关吗**？还是它其实是本单没修干净的残留？
   （orchestrator 注：0.12 m = 半个 240 墙厚，与本日查明的「gt 外包 vs correction 中线」基准差同量级。）

## 二、验收判据

1. **全量绿**：`python -m pytest -n auto`，基线 = 合入 D-1 后的主线。⭐ 请自己跑。
   ⚠️ 已知环境坑：`tests/test_zone_agent.py` 需要 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY`，
   无凭据环境会红 —— **那是环境问题，⛔ 不是本 commit 的回归**（上一轮 GPT 已踩过）。
2. **范围**：diff 应只含 `src/agent/judge/opening_claim_score.py` · `score_service.py` + 两个测试。
   ⛔ 碰 pipeline 内核 / 交接契约 / `src/validator/` / gt ⇒ 记为越权。
3. **锁能变红**：施工提供了红/绿两段，请复验，并判断**变红方向对不对**。

## 三、⚠️ 必答

跨家族「停下上报」累计 **28 次全是派工方（orchestrator）题错**（本单席位已上报 2 条，其中第 2 条
——「修好 F-90 就能让 sm25 判出分」这个前提不成立——已登记为 **F-99**）。
⇒ **这 2 条你认同吗？还有第 3 条吗？**

⭐ 另请特别评估：**派工单要求「必须真的判出分、不是不再抛异常」，而施工用自造 fixture 达成、
真实 case 上并未达成**。**这算满足了那条验收判据，还是绕过了它？** 请直说。

## 四、产出

先给 **APPROVE / REJECT / APPROVE-WITH-FINDINGS** 一句话结论，再逐条列证据（指到文件行或命令输出）。
⛔ 只审：不改文件、不提交、不 push。用完的临时目录请自己清理。
