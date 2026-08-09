# Sonnet 强/弱 prompt A/B — reading 坐标精度（plan N1e）— 2026-06-25

## 目的
测 N1e 假设：把识图退化的指令层（`fa04ef6` 软化坐标精度责任、`06-16` 启动 prompt 缩水）**恢复回强 prompt**，
能否压下 Sonnet 在 sm21 上的坐标错（cited 基线：1f 竖墙偏 0.36m、窗大量错位）。

## 设计（单变量）
- 唯一变量 = **启动 prompt 强弱**；skill 文件 4 跑完全一致（HEAD `b5e3928`，skill md5 已记 `scores.txt` 旁）。
- **弱臂** = 当前 `new_case_guide.md` 附录 A 逐字（`prompt_weak.md`）。
- **强臂**（`prompt_strong.md`，按用户裁定**保 image-local、不含四立面世界映射表**）单变量加回：
  ① 坐标必须读准·**别指望 correction 回溯**硬线；② 尺寸链**算式入 `note`**（逼显式加法、可审）；
  ③ testdata 面积 240m²/2层≈120m² **sanity 锚定**。
- 执行 = 4 个冷启隔离 Sonnet 子代理（2 弱 / 2 强），物理目录隔离（只喂 images+skill+testdata、禁读 gt/其它 reading）。
- 测量 = `score_reading_vs_gt` 按 gt 坐标逐元素对账。
- **截断后已补全（2026-06-25）**：strong_1/strong_2 撞 session limit 后由各自独立的新隔离子代理补完剩余图（单补、保样本独立），4 臂均全 6 图。n 仍为 2/臂。

## ⚠️ 过程中抓到的 scorer bug（本轮真正价值）
首轮 strong 5/7 窗 vs weak 0/7 窗，差距可疑。核实发现：**两臂窗 x 读的完全一样且都命中 gt**
（weak `geometry.kind=rect, x_range_m:[1.24,3.64]` vs strong `kind=line, p1/p2`）。
`score_reading_vs_gt.extract_reading_{walls,windows}` **只解析 `p1/p2`(line)、不认 `rect`/`x_range_m`**
——而 `x_range_m` 是 reading schema 合法形状 → rect 形窗此前**全被静默算 0**，污染权威 reading 评测。
**已修**：新增 `_as_segment()` geometry 规范化（line + rect 都认，rect 取长轴中线），墙窗抽取共用；
回归测试 `test_rect_geometry_scores_like_equivalent_line`；全测 341→342。
**教训现场**：差点把 scorer bug 当"强 prompt 修好了窗"——印证 [[judge-gt-authoritative-images-auxiliary]]
未验证测量不得当结论。

## 结果（scorer 修复后，1f 四臂完全可比）
| 臂 | 1f 墙 命中/多余 | 1f 窗(共7) | 1f 竖墙偏移 |
|---|---|---|---|
| weak_1 | 3/4, +4 | 4 | −0.06/−0.06 |
| weak_2 | 4/4, +2 | **6** | −0.06/−0.18 |
| strong_1 | 4/4, +1 | 5 | −0.06/−0.18 |
| strong_2 | 4/4, +1 | 5 | −0.06/−0.18 |

**全 6 图完整 totals（strong 补全后）：**
| 臂 | 墙 | 窗 |
|---|---|---|
| weak_1 | 7/9 | 4/15 |
| weak_2 | **9/9** | **11/15** |
| strong_1 | 9/9 | 7/15 |
| strong_2 | 8/9 | 11/15 |

2f 窗 hit：weak_1 0/8 · weak_2 5/8 · strong_1 2/8 · strong_2 6/8 —— **方差巨大**。weak_2(9/9,11/15) 与 strong 持平/更好；窗 4–11 跨度内**方差 > 臂间差**。

## 结论
**强 prompt 没有清晰的坐标精度优势。**
1. **坐标偏移没改善**：1f 竖墙偏移四臂一致（0.06–0.18m）；cited 的 **0.36m 谁都没复现**；strong_1 的 2f 竖墙
   反而偏 0.15（weak_2 精确 0）。强 prompt 的"坐标硬线 + 尺寸链算式"没把偏移压下去。
2. **窗没改善**：单 run 最好的是 **weak_2（1f 6/7、全 11/15）**，是弱臂。2f 窗 hit 0/5/2 由 run 间方差主导。
3. **唯一一致信号**：强臂**墙过度分割略少**（多余墙 1 vs 弱 2–4）——但 weak_2 也只多 2，n=2 不显著。
4. **run 间方差 > prompt 臂差** —— 与 N1d「受控隔离下 Sonnet 戏剧性缺陷不复现」同结论。指令层退化是
   "坐标 vs gt 变差的合理机制"但**本实验未证其为 Sonnet 坐标错的成因**（呼应退化调查的诚实标注）。

## 启示（下一步候选，非本轮执行）
- prompt 强度不是杠杆 → 真 lever 仍在 N1d 末尾那组：**杂物/尺寸链 tick 掩膜 / 局部放大裁图 / 加 reread 预算 / 换强模型**（Opus sm24/sm21_pre 一次干净）。
- 强臂截断（session limit）→ 若要补 n，重跑 strong_1/strong_2 至全 6 图；但当前信号已足够说"无清晰优势"。
- scorer 还可补：综合 zone_f1/WWR + 嵌 record_baseline（plan N4 残留）。
