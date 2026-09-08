---
name: elevation-plan-matching-goes-direct
description: 立面↔平面靠几何对应绑侧、脱离四立面与正南正北——⭐ 早已立项为 C2.1，规划稿在 proposals/
metadata:
  type: project
---

**⛔ 先记教训**：2026-09-08 用户问「咱后续立面要解锁直接匹配……这个你是知道的哇？」，
我答「**这条方向我原先没有，是你现在给我的**」。**错的。**
用户一句「这条不是登记在 C2.1 批次了吗，你查一下」翻出：**早已立项，且有正式规划稿**
`AI_agent/proposals/c2_1_facade_matching_plan.md`（127 行，2026-07-19 存档，
`decision_log.md:170` / `:189` 均有登记）。
⇒ 我只 grep 了 `plan.md`/`CLAUDE.md`/记忆目录，**没查 `proposals/`**。
同族 [[list-the-directory-before-writing-a-new-doc]]：**代价不是重复劳动，是我差点把已有架构重新发明一遍。**

## 稿里已经写死的（⛔ 别再重新发明）

| 稿中原文 | 管的是哪一半 |
|---|---|
| 接缝铁律：「匹配在**建筑帧坐标**下按几何绑侧，**true-north 无关**；旋转(C2.2)=全局单 θ 另一步」 | 脱离正南正北 |
| §126：「sm25-L 验的是『四标准**命名**立面、无匹配』—— C2.1 **唯一新轴 = 把「命名」换成「几何绑侧」**」 | 靠对应关系匹配 |
| §42 扩展点(铁律#6)：「匹配器接口取**「候选侧集合」为入参而非硬编码 4 cardinal**」 | 脱离四立面 |
| §41 Q1：C2.1 **域内**答案 = 恒四个 cardinal（U 形不增加可命名外侧）| 本批范围 |
| §95 C2.1-B：确定性打分器**纯函数**（特征阶梯 + **镜像分支** + **margin 阈值**）+ MatchedViewBinding sidecar | 引擎形态 |
| §118 风险1：镜像对称 → **必须 conflict 不许猜**，测试族含「刻意对称」负例 | 主险 |

⭐ **§42 那条正是「把 cardinal 收在一处、做成入参」的工程纪律** —— 稿子早写了。

## 我 2026-09-08 的实测能给这份稿添的东西（新增，非重复）

`logs/experiments/2026-09-08c_window_investigation`：34 个立面洞口 × 平面 `opening_types` 候选，
按沿面范围两端点误差和匹配，**四面各 100% 且 margin 明确**
（east 13/13 vs 镜像 4 · north 镜像 8/8 vs 0 · south 7/7 vs 0 · west 镜像 6/6 vs 3）。
⇒ **§95 要的那个「margin 阈值」在真产物上有读数了**；§118 的镜像风险在 sm25-L 上**不发生**（无平局）。
另：`facade_convention.FACADE_BASE_SIGN` 四个符号与实测**逐条吻合**。

**How to apply**：
- 涉及立面朝向/匹配的活，**先读 `proposals/c2_1_facade_matching_plan.md`**，⛔ 不要另起炉灶。
- 现在仍**不实现**（[[extensibility-is-not-generalization-now]]）；但按 §42：
  **四立面/基准符号只许出现在 `facade_convention` 一处**，⛔ 别处不许再抄 N/S/E/W 判断。
- ⭐ 找「这件事以前定过没有」时，`proposals/` 与 `decision_log.md` **和 plan.md 一样要查**。

配套：[[building-complexity-extensibility-principle]]（#6，点名的是非方形/退台/挑空/中庭，**不含朝向**）
· [[derive-facade-frame-unwired-ew-sign-trap]] · [[c2-full-unlock-sprint]]
