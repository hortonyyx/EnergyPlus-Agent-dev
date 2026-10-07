# Q2-E 离线重放

本报告由 `replay.py` 只读历史产物生成；0 次 work model／外部模型请求。参照仅用于评价，未进入生产对齐与平立面匹配。

共清点 48 份真实立面提交，48 个不同提交文件哈希；按每次运行每个立面取最后一次提交后为 43 份。

## 指定运行覆盖

| 运行 | 提交数 | 末次立面 | 末次开口 | 覆盖 | 缺失 |
|---|---:|---:|---:|---|---|
| role_debug/sm24_run3 | 4 | 4 | 14 | complete | — |
| role_debug/sm24_run4 | 3 | 3 | 9 | incomplete | West |
| role_debug/sm24_run5 | 6 | 4 | 14 | complete | — |
| role_debug/sm24_run6 | 4 | 4 | 14 | complete | — |
| role_debug/sm24_run7 | 5 | 4 | 14 | complete | — |
| role_debug/sm21_run1 | 4 | 4 | 17 | complete | — |
| role_debug/sm25_run1 | 4 | 4 | 34 | complete | — |
| cmp3/sm24_role | 4 | 4 | 14 | complete | — |
| cmp3/sm21_role | 5 | 4 | 17 | complete | — |
| cmp3/sm25_role | 5 | 4 | 34 | complete | — |
| reader_model_probe/qwen27b_r1 | 4 | 4 | 14 | complete | — |

## 对参照的 5／10／30 cm 分档（全部提交，含重复/返工）

| 状态 | 指标 | ≤5 cm | 5–10 cm | 10–30 cm | >30 cm | 不可用 |
|---|---|---:|---:|---:|---:|---:|
| 对齐前 | 沿墙端点位置 | 172 | 4 | 8 | 9 | 0 |
| 对齐前 | 宽度 | 190 | 0 | 1 | 2 | 0 |
| 对齐前 | 窗台/门槛 | 193 | 0 | 0 | 0 | 0 |
| 对齐前 | 窗顶/门顶 | 191 | 0 | 0 | 2 | 0 |
| 对齐后 | 沿墙端点位置 | 172 | 4 | 8 | 9 | 0 |
| 对齐后 | 宽度 | 190 | 0 | 1 | 2 | 0 |
| 对齐后 | 窗台/门槛 | 193 | 0 | 0 | 0 | 0 |
| 对齐后 | 窗顶/门顶 | 191 | 0 | 0 | 2 | 0 |

按每次运行每个立面只保留最后一次提交的同口径统计也保存在 `evidence_replay.json.reference_tiers_latest_per_facade`，用于避免返工重复计权。

读图侧共有 218 个开口槽位，参照侧也有 218 个；其中只有 193 对具备同 facade/floor/kind 且逐序可接受的身份，所以尺寸档位分母是 193，不是 218。
未评分的读图侧 25 扇和参照侧 25 扇中，22+22 扇来自楼层标签不一致（`GF`/`PLAN.F*` 对 `F*`）；3+3 扇来自位置或次序冲突。它们保留在清单中，但不强配、不计入误差档位；这些数量按 48 份提交统计，含重复/返工。
候选墨线中，水平边有 419 条原位确认、0 条候选移动；竖向边有 324 条原位确认、0 条候选移动、80 条因缺少合格标定而不搜索。另有水平 17 条、竖向 32 条因候选墨线不唯一而不采纳。候选移动边合计 0，按证据策略实际采纳移动边 0、采纳字段 0；保留值与唯一墨线超过阈值的不一致 10 项。识别出 2 个门槛接触已保存 floor/ground 观测，其中 2 个明确以 `retained_floor_contact` 保留原 sill。
相对参照的档位变化：位置 0 改善/193 不变/0 变差；宽度 0 改善/193 不变/0 变差；窗台/门槛 0 改善/193 不变/0 变差；窗顶/门顶 0 改善/193 不变/0 变差。

## A 实际数值变化与四指标回归闸

48 份提交中有 0 扇有效数值发生变化，其中参照可配对 0 扇、不可配对 0 扇；逐项精确误差回归为 0。对所有可配对变化扇，位置、宽度、窗台/门槛、窗顶/门顶四项均要求 after ≤ before；任一项变差会使重放直接失败。

| 运行/立面/层/对象 | 提交 SHA | 依据 | 采纳字段 | 数值变化 | 参照状态 | 位置前→后 | 宽度前→后 | sill 前→后 | head 前→后 |
|---|---|---|---|---|---|---:|---:|---:|---:|
| 无：218 个历史开口的 effective values 均与 reader values 相同 | — | — | — | — | — | — | — | — | — |

### 保留值与唯一墨线不一致（独立于 B 数值分档）

共 10 个提交内开口记录（按 submission SHA + opening id）、10 个字段；按字段 {"width_m": 10}，按依据类型 {"annotation_and_pixels": 10}。这些项进入复核，但不改原 reader 数值，也不改 B 的 ≤10/10–30/>30 桶。

| 运行/立面/层/对象 | 提交 SHA | 字段 | 依据 | reader | ink | 差值 | 阈值 |
|---|---|---|---|---|---|---:|---:|
| role_debug/sm24_run4/East/F1/W1 | 1f5641df4cd5 | width_m | annotation_and_pixels | 4.8 | 4.682622268470343 | 0.117378 m | 0.050000 m |
| role_debug/sm24_run5/West/F1/W2 | 30caa92584a7 | width_m | annotation_and_pixels | 1.5 | 1.2057112638815441 | 0.294289 m | 0.050000 m |
| role_debug/sm24_run5/East/F1/D1 | 3ef1e13797ee | width_m | annotation_and_pixels | 1.6 | 1.673728813559322 | 0.073729 m | 0.050000 m |
| role_debug/sm24_run5/East/F1/D1 | 4768abf58f38 | width_m | annotation_and_pixels | 1.6 | 1.673728813559322 | 0.073729 m | 0.050000 m |
| role_debug/sm24_run7/East/F1/E-W1 | 0eb959ab81d7 | width_m | annotation_and_pixels | 4.8 | 4.931954273271638 | 0.131954 m | 0.050000 m |
| role_debug/sm21_run1/North/F1/W1 | 55ee21a82e71 | width_m | annotation_and_pixels | 2.4 | 2.2151162790697674 | 0.184884 m | 0.050000 m |
| role_debug/sm21_run1/North/F1/W3 | 55ee21a82e71 | width_m | annotation_and_pixels | 2.4 | 2.2151162790697674 | 0.184884 m | 0.050000 m |
| role_debug/sm21_run1/North/F2/W4 | 55ee21a82e71 | width_m | annotation_and_pixels | 3.6 | 3.313953488372093 | 0.286047 m | 0.050000 m |
| role_debug/sm21_run1/North/F2/W5 | 55ee21a82e71 | width_m | annotation_and_pixels | 3.6 | 3.313953488372093 | 0.286047 m | 0.050000 m |
| cmp3/sm25_role/North/F1/NF1-W2 | ef4330ff808c | width_m | annotation_and_pixels | 0.6 | 0.7030827474310437 | 0.103083 m | 0.050000 m |

### reader 宽度与像素跨度内部冲突（独立于唯一墨线不一致）

最后一次立面提交的 B 对位中共有 159 扇非 pixels 开口的 reader width 与像素跨度存在大于 1e-7 m 的差异，均禁止直接 `use_elevation`；其中 6 扇超过 `max(5 cm, 2 px)`，须主动待裁决/重读，其余 153 扇只在选择 `use_elevation` 时要求重读。这不是 unique-ink 差异，也不并入 B 原位置三档；阈值只决定是否主动新增一条待裁决记录。全部逐扇记录保存在 `evidence_replay.json.width_span_conflict_audit.rows`；下表列主动冲突。

| 运行/立面/层/对象 | 依据 | reader width | pixel span width | 差值 | 阈值 | B 桶 |
|---|---|---:|---:|---:|---:|---|
| role_debug/sm24_run5/East/F1/D1 | annotation_and_pixels | 1.600000 | 1.673729 | 0.073729 | 0.050000 | >30cm |
| role_debug/sm24_run5/West/F1/W2 | annotation_and_pixels | 1.500000 | 1.205711 | 0.294289 | 0.050000 | <=10cm |
| role_debug/sm21_run1/North/F1/W1 | annotation_and_pixels | 2.400000 | 2.215116 | 0.184884 | 0.050000 | 10-30cm |
| role_debug/sm21_run1/North/F1/W3 | annotation_and_pixels | 2.400000 | 2.215116 | 0.184884 | 0.050000 | 10-30cm |
| role_debug/sm21_run1/North/F2/W4 | annotation_and_pixels | 3.600000 | 3.313953 | 0.286047 | 0.050000 | 10-30cm |
| role_debug/sm21_run1/North/F2/W5 | annotation_and_pixels | 3.600000 | 3.313953 | 0.286047 | 0.050000 | 10-30cm |

## 每次运行平立面差（最后一次立面提交）

| 运行 | ≤10 cm | 10–30 cm | >30 cm | 墨线不一致（扇/字段） | reader宽度-像素跨度冲突 | 未匹配/不可评 |
|---|---:|---:|---:|---:|---:|---:|
| role_debug/sm24_run3 | 14 | 0 | 0 | 0/0 | 0 | 0 |
| role_debug/sm24_run4 | — | — | — | — | — | no_delivery_selection |
| role_debug/sm24_run5 | 9 | 1 | 4 | 2/2 | 2 | 1 |
| role_debug/sm24_run6 | 8 | 0 | 0 | 0/0 | 0 | 8 |
| role_debug/sm24_run7 | 14 | 0 | 0 | 0/0 | 0 | 0 |
| role_debug/sm21_run1 | 13 | 4 | 0 | 4/4 | 4 | 0 |
| role_debug/sm25_run1 | 28 | 4 | 2 | 0/0 | 0 | 0 |
| cmp3/sm24_role | 14 | 0 | 0 | 0/0 | 0 | 0 |
| cmp3/sm21_role | 17 | 0 | 0 | 0/0 | 0 | 0 |
| cmp3/sm25_role | 31 | 3 | 0 | 0/0 | 0 | 0 |
| reader_model_probe/qwen27b_r1 | — | — | — | — | — | elevation_only_probe |

B 的对象身份仍由最终 source 与立面通过生产 `match_elevation` 对位；独立平面量值改从 `role_floor_sources.json` 绑定且哈希复核通过的 accepted plan-reader trial 读取，再调用生产 `compare_opening_positions`。因此协调者采用立面或后续改 source，不会反写平面观察值。
逐个核对有交付选择的最终 source 外开口：共 173 扇；170 扇与 accepted trial 的 XY 一致，2 扇被协调者改位，1 扇仅存在于最终 source。

### 最终 source 相对 accepted plan trial 的 XY 差异

| 运行/立面/对象 | accepted trial span | final source span | 左右/宽最大变化 | 处理 |
|---|---:|---:|---:|---|
| role_debug/sm24_run6/South/W_B0 | — | 0.546448–2.049182 | — | accepted trial 无此开口，记 unavailable/需重读 |
| role_debug/sm25_run1/North/F2:W_ribbon | 15.008726–23.756545 | 15.293000–23.277000 | 0.763819 m | trial 作为独立平面量值 |
| role_debug/sm25_run1/West/F2:W_scorr_w | 4.422869–5.285868 | 4.444500–5.609600 | 0.323732 m | trial 作为独立平面量值 |

## sm25 分工位置待裁决（>10 cm）

| 立面/层/对象 | 平立面最大差（左右/宽） | 平面对参照 | 立面对参照 | 位置更近 | 宽度更近 |
|---|---:|---:|---:|---|---|
| East/F1/D1→F1:D_E_2leaf | 0.206 m | 0.195 m | 0.011 m | elevation | elevation |
| East/F2/W9→F2:W_E4 | 0.203 m | 0.197 m | 0.006 m | elevation | elevation |
| West/F1/W-D1→F1:D_SW_entr | 0.189 m | 0.206 m | 0.017 m | elevation | elevation |

## 口径与限制

- 历史开口 `bbox` 的实际格式是 `[left_px, top_px, right_px, bottom_px]`，它是证据裁剪框；独立水平粗框在 `x_px=[left,right]`。水平标定为 `x_calibration={pixel_start,pixel_end,world_start_m,world_end_m,world_axis}`，允许 world 方向反向。生产派生的竖向标定使用同四个数值键，图像 Y 增大时绝对 Z 必须减小。
- A 仅在 `evidence_type==pixels`、相关墨线唯一且边实际移动时替换对应 reader 字段；annotation、annotation_and_pixels、visual_estimate 均保留。原位 confirmed 只证明边，无权重算 reader 数值。`candidate_bbox_px` 记录墨线候选，`effective_bbox_px`/`aligned_bbox_px` 与 `aligned_values` 记录实际生效值。
- 门槛保护只适用于 door：同层已保存的 floor/ground 观测须为 annotation、annotation_and_pixels 或 pixels，且与原 sill 相距不超过 `min(1 px, 5 cm)`。历史常见 0.16/0.20 m 抬高门槛不会被机械当作地坪。
- 旧立面提交没有显式 `z_calibration`。重放直接调用生产 `derive_z_calibration`：只认图像证据的横向 level/eave/ground 带，用 bbox 中心与 `value_m` 取跨度最大的两带；其余带保留残差。48 份中 36 份成功、11 份缺两条合格水平带、1 份残差超 10 cm 被拒；半带不确定度超过 35 cm 也会拒绝。拒绝时保留原 sill/head，不拿不足证据强行吸附。
- 历史 `bbox` 是证据裁剪框，不当作开口框。水平粗框来自 `x_px`；竖向粗框仅由上述 Z 标定把提交的 sill/head 反算成像素。
- 对参照配对按 facade/floor/kind 的世界坐标顺序完成；漏项和多项留作未匹配，不强配。平立面对象身份与冲突直接调用生产 `match_elevation`。
- 平立面对比不把最终 delivery candidate 当作独立平面读数。最终 source 只用于对象身份；span 来自对应楼层哈希绑定的 accepted plan-reader trial。trial 缺对象时保留当前 source 对位与单侧冲突，记为 unavailable/需重读，不进入 ≤10 cm。
- B 的 ≤10/10–30/>30 桶只由 accepted plan-reader trial span 与立面像素 span 的端点/宽度差计算；墨线不一致和 reader width/pixel span 内部冲突是附加复核信号，不改桶。非 pixels 的 reader width 与像素跨度存在任何大于 1e-7 m 的差异时，禁止 `use_elevation`；超过 `max(5 cm, 2 px)` 才另记 pending 冲突。
- `role_debug/sm24_run4` 缺 West 成功提交：原 West reader 记录为 failed，重试仍为 running；plan reader 同时一份 failed、一份 running，根目录无 receipt 与全楼交付选择。因此只能重放 East/North/South，不能给平立面扇数。27B 摸底同样只有立面读图员产物。
- `evidence_inventory.json` 保留每份提交、原图及参照的路径与 SHA-256；未复制历史图片、事件日志或 BIM bytes。
