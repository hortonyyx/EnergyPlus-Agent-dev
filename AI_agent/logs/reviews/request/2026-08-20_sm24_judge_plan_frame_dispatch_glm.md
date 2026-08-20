# 派工单 · sm24 验收准入门：v3 判卷对 null `scale_origin` 的静默零分

- **日期**：2026-08-20
- **派工方**：orchestrator（claude-opus-5）
- **执行席**：GLM（`glm-5.3`，`scripts/glm_code.sh`）
- **档位**：**工程档**（碰判卷 ⇒ gate① + 全量绿 + 换人审；作者不得是 orchestrator，见 CLAUDE.md §0.2 / §0.4#3）
- **审阅方**：orchestrator 只看「原始需求 + `git diff` + 测试输出」，⛔ 不看长篇自述（§5#8）
- **为什么此刻做**：它是本批四格验收里 sm24 两格的**唯一准入门**。sm21 两格不受影响，正在并行跑。

---

## 一、背景（够独立读，不用翻别的文件）

本项目第一目标 = 在当前代码基座上重新拿到一次 2026-07-07 那个水平的识图（reading）成绩。
本批验收 = 两个模型（`gpt-5.4-mini` / `claude-sonnet-5`）× 两个 case（`sm21_anchor` / `sm24_anchor`）共四格。

判卷分两条路：
- `sm21_anchor` 的标准答案是 **gt schema v2** ⇒ 走 legacy 判卷路 ⇒ **不受本单影响**。
- `sm24_anchor` 的标准答案是 **gt schema v3** ⇒ 走 typed 判卷路 `src/agent/judge/reading_typed_adapter.py` ⇒ **卡在这里**。

## 二、现象与定位（我已核过的部分）

`src/agent/judge/reading_typed_adapter.py:430-460`：平面视图（`image_kind == "plan"`）如果
`scale_origin` 不是一个含有限 `world_x_m` / `world_y_m` 的 dict，整条 plan 通道
（`plan_segments` + `plan_openings`）直接返回：

```
status = not_applicable
reason = "plan_frame_unavailable"
cause_class = "product_content"
denominator_disposition = "retain_as_miss"     ← 计入分母、按 miss 计
```

**不抛异常、不看 `run_profile`、不产生任何与「画得稀烂」可区分的信号。**

**为什么这是缺陷而不是设计**：2026-08-17 已把读图器侧「必须填 `scale_origin`」放宽为 **SHOULD**
⇒ **留 null 是合法产出**。于是一份**逐笔画都对**的 reading 可以被合法地判成结构性零分，
且分数长相与「彻底画错」完全一致。

**gate① 侧有对应检查但挡不住**：`src/validator/checks/reading.py:1004`
（`reading.plan_scale_origin_usable`）只在 `golden` / `regression` 两档 BLOCK，
`exploratory` / `dev` 只提醒；而 `run_stage.py:3128` 的 `--run-profile` 默认值 = `exploratory`。
（以上三条我逐行核过。）

## 三、⚠️ 请优先评估的 option 0 —— 很可能根本不用你改代码

既然 gate① 已经有这条检查、只是档位太松，那么 **sm24 那两格改用更严的 `--run-profile` 跑**
就能把「静默零分」换成「入口处响亮拦下 + 返工一轮」——**零代码改动**。

**⇒ 请先回答这一条**：sm24 的 reading-only 验收跑改用 `--run-profile regression`（或别的合适档位），
是否足以关掉本缺陷对本批的影响？如果足够，**就不要动判卷代码**——按项目治理口径
（CLAUDE.md §0.1「不做这件事，下一次跑测能不能跑起来、结果能不能读？」），能跑能读即止。

请一并说明该档位会**顺带**收紧哪些别的门、会不会让这一批跑不动（这是我没核的部分）。

## 四、⚠️ 我的前提（当成**可能是错的**前提写，请优先证伪）

1. 我判断这是「判卷端契约」与「指令端契约」不一致，修法**如果**要改代码应落在判卷端。
   **但也可能应落在指令端**（把 SHOULD 收回 MUST）或**代码端**（世界原点由代码从产物推导）——
   这两条分别归「标定出模专项」与 `dimension_basis` 专项，本批不动。
   **如果你认为判卷端不该动，直接说，我改派。**
2. 我判断**不能**简单把 `denominator_disposition` 改成 `filter`：
   `src/agent/judge/score_schema.py:695-706` 的 validator 由 `cause_class` 强制推导 disposition
   （`trusted_input` ⇒ `filter`，其余 ⇒ `retain_as_miss`）；且 `filter` = 把 plan 通道**移出分母**
   ⇒ 读图器只要不填原点就能让整条通道「不计分」，**比现在更坏**。**能证伪就证伪。**
3. 我判断真正要修的**不是分数算法**，而是「这个零分**不可区分**」+「验收档位下**不 fail-closed**」。
4. **我没核的**：`exploratory` 档位下 typed 判卷的完整行为路径；以及切到更严档位的连带影响（见 option 0）。

## 五、要你交付（如果 option 0 不成立才做后三项）

1. **一份 ≤1 页定案说明**：选了哪条路、为什么、被否掉的选项各是什么理由。⛔ 不要长篇过程叙述。
2. **代码改动**（只在 option 0 不成立时）。
3. **锁**（至少两把，且**只锁契约与判定，不给脚手架加锁**）：
   - (a) 一份「笔画全对、但 `scale_origin` 为 null」的夹具，**先断言修改前确实是静默零分**，再断言修改后不是
     （回归用例必须自证前提：不先证明旧行为，锁就证明不了它抓的是这件事）；
   - (b) **neuter 验证**：把你的改动摘掉，该锁必须变红，且只红它、零连带。把 neuter 的实测结果写进定案说明。
4. **全仓 `python -m pytest -n auto`**：当前基线 **2835 绿 + 14 strict xfail**，交付时必须仍然如此。

## 六、⛔ 硬边界

- ⛔ 不许碰 `case_tests/test_baseline/gt/**`（gt 铁律，动它等于全部历史成绩作废）。
- ⛔ 不许碰 `skills/intake_pipeline/0_reading/**`（读图器的输入，本批冻结——正在用它跑验收）。
- ⛔ 不许改 gate① 那条 `reading.plan_scale_origin_usable` 的**档位口径**（2026-07-31 定，另有依据），
  除非你在定案说明里论证为什么必须一起动。
- ⛔ 不许 `git commit` / `git add`（由 orchestrator 统一提交）。
- ⛔ 不许改 `AI_agent/` 下任何管理文档。
- ⛔ 不许顺手修别的缺陷（撞见了写进定案说明的「顺带发现」一节，不要动手）。

## 七、⚠️ 停下上报

**发现我上面任何一条前提是错的 ⇒ 停下来说，不要顺着错前提做完。**
本仓历史上 12/12 次「停下上报」最后都证明是派工方的题出错了，不是执行方偷懒。
尤其第四节第 4 条那两处我明确没核。
