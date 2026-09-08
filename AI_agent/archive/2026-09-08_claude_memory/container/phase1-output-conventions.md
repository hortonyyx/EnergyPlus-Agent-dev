---
name: phase1-output-conventions
description: 两步法 phase1 产物交付约定 —— 渲 SVG(人工校验)+ PNG(多模态模型可回读自检)+ 每图拷一份原图进输出目录作参考
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2e86f2f6-b17b-4225-87a8-78f3d629ee3a
---

两步法 phase1 跑完后的产物交付约定(2026-05-28 用户拍板,**当日晚更新:PNG 重新纳入交付**):

1. **同时渲 SVG + PNG**。SVG=人工校验正式产物(可缩放、浏览器看得清);PNG=**让多模态模型(Claude/其他)能回读做视觉校验**——这是用户 2026-05-28 sm21 复盘后的明确要求(原"不必 PNG"已推翻)。命令:`render_vector_to_svg.py --dir <case>/phase1_vector` + `render_vector_to_png.py --dir <case>/phase1_vector`(后者 PIL,产 `<view>_render.png`)。
   - 注意:Claude 用 Read 看不了 SVG(只返 XML),但**能看 PNG**——所以 PNG 让助手/其他模型也能参与视觉校验(对刚做的 sm21 phase2 三模型诊断这类排查很有用),不再只靠人工。
2. **每图把原图也拷一份进输出目录作参考**。约定命名:`<case>/phase1_vector/<view>_source.png`(原图)、`<view>.svg`(重绘)、`<view>_render.png`(重绘 PNG)、`<view>.json`(矢量)并列,人工/模型逐图 side-by-side。

**Why**:SVG 人看、PNG 机看(多模态回读自检)。与 `test_data/phase1_generalization/` 布局(testN.jpg 原图 + svg + _render.png)一脉相承。

**How to apply**:phase1 子代理/会话产出 JSON + summary 后,助手收尾时:① `render_vector_to_svg.py --dir`;② `render_vector_to_png.py --dir`;③ 拷 N 张原图为 `_source.png`。待落进 [new_case_guide_twostep.md](AI_agent/guides/new_case_guide_twostep.md) Step 4a 校验环节(目前只提了 SVG)。相关流程见 [[twostep-poc-v2-status]]、[[recognition-modeling-capability]]。
