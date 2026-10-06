# sm25 门窗位置逐项对比

评价口径：沿墙端点与垂墙误差分别使用冻结原图清单中的容差；未匹配项单列。

## 2026-10-05

汇总：位置 22/61，匹配 58，宿主 55，门连接 28。

| 层 | 参照 → 实际 | 类别 | 墙/立面 | 参照 span / cross (m) | 实际 span / cross (m) | 端点误差 / 垂墙误差 (m) | 依据 | 首次声明 |
|---|---|---|---|---|---|---|---|---|
| F1 | DN1 → F1:D_r1 | door | interior:NW1<->C | [3.86, 4.639] / 16.054 | [3.791, 4.64] / 16.166 | 0.069 / 0.112 | image_measurement_or_estimate | draft_001 [458.0, 487.3]→[497.2, 487.3] |
| F1 | DN2 → F1:D_r2 | door | interior:NW2<->C | [5.374, 6.153] / 16.054 | [5.362, 6.261] / 16.166 | 0.108 / 0.112 | image_measurement_or_estimate | draft_001 [530.5, 487.3]→[572.0, 487.3] |
| F1 | DE1 → F1:D_o1 | door | interior:E1<->C | [18.378, 19.135] / 11.073 | [18.234, 19.137] / 11.185 | 0.145 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 349.9]→[799.3, 391.7] |
| F1 | DE2 → F1:D_o2 | door | interior:E2<->C | [16.843, 17.622] / 11.073 | [16.884, 17.788] / 11.185 | 0.166 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 412.3]→[799.3, 454.1] |
| F1 | DE3 → F1:D_o3 | door | interior:E3<->C | [14.378, 15.135] / 11.073 | [14.149, 15.053] / 11.185 | 0.229 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 538.8]→[799.3, 580.6] |
| F1 | DE4 → F1:D_o4 | door | interior:E4<->C | [12.843, 13.622] / 11.073 | [12.543, 13.446] / 11.185 | 0.301 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 613.1]→[799.3, 654.9] |
| F1 | DE5 → F1:D_o5 | door | interior:E5<->C | [10.378, 11.157] / 11.073 | [10.378, 11.28] / 11.185 | 0.123 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 713.3]→[799.3, 755.0] |
| F1 | DE6 → F1:D_o6 | door | interior:E6<->C | [8.843, 9.622] / 11.073 | [8.705, 9.602] / 11.185 | 0.138 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 790.9]→[799.3, 832.4] |
| F1 | DE7 → F1:D_o7 | door | interior:E7<->C | [6.854, 7.632] / 11.073 | [6.532, 7.436] / 11.185 | 0.322 / 0.112 | image_measurement_or_estimate | draft_001 [799.3, 891.1]→[799.3, 932.9] |
| F1 | DW1 → F1:D_m1 | door | interior:W1<->C | [10.378, 11.157] / 8.953 | [10.121, 10.966] / 8.759 | 0.257 / 0.195 | declared_value_basis_not_explicit | draft_001 [687.3, 727.8]→[687.3, 766.9] |
| F1 | DW2 → F1:D_m2 | door | interior:W2<->C | [8.865, 9.622] / 8.953 | [8.614, 9.375] / 8.759 | 0.251 / 0.195 | declared_value_basis_not_explicit | draft_001 [687.3, 801.4]→[687.3, 836.6] |
| F1 | DS1 → F1:D_mr1 | door | interior:S1<->C | [11.062, 12.641] / 3.935 | [11.012, 12.667] / 3.764 | 0.050 / 0.171 | declared_value_basis_not_explicit | draft_001 [791.3, 1060.9]→[867.7, 1060.9] |
| F1 | DS2 → F1:D_mr2 | door | interior:S2<->C | [13.376, 14.955] / 3.935 | [13.297, 14.898] / 3.764 | 0.079 / 0.171 | declared_value_basis_not_explicit | draft_001 [896.8, 1060.9]→[970.7, 1060.9] |
| F2 | WE2 → F2:W_e2 | window | East | [12.737, 13.653] / 14.889 | [12.68, 13.492] / 15.002 | 0.161 / 0.113 | deterministic_correction_of_prior_declaration | draft_001 [988.9, 419.5]→[988.9, 461.3] |
| F2 | WE3 → F2:W_e3 | window | East | [10.338, 11.254] / 14.889 | [10.761, 11.573] / 15.002 | 0.423 / 0.113 | deterministic_correction_of_prior_declaration | draft_001 [988.9, 529.9]→[988.9, 571.7] |
| F2 | WE4 → F2:W_e4 | window | East | [8.724, 9.64] / 14.889 | [8.829, 9.655] / 15.002 | 0.105 / 0.113 | deterministic_correction_of_prior_declaration | draft_001 [988.9, 605.1]→[988.9, 646.9] |
| F2 | WE5 → F2:W_e5 | window | East | [6.718, 7.634] / 14.889 | [6.944, 7.762] / 15.002 | 0.227 / 0.113 | deterministic_correction_of_prior_declaration | draft_001 [988.9, 715.5]→[988.9, 757.3] |
| F2 | WS1 → F2:W_s1 | window | South | [6.915, 8.748] / 0.120 | [6.937, 8.737] / -0.087 | 0.022 / 0.207 | deterministic_correction_of_prior_declaration | draft_001 [681.8, 1235]→[866.5, 1235] |
| F2 | WS2 → F2:W_s2 | window | South | [9.446, 11.257] / 0.120 | [9.455, 11.259] / -0.087 | 0.009 / 0.207 | deterministic_correction_of_prior_declaration | draft_001 [899.8, 1235]→[1084.5, 1235] |
| F2 | WS3 → F2:W_s3 | window | South | [14.747, 16.558] / 0.120 | [14.76, 16.564] / -0.087 | 0.013 / 0.207 | deterministic_correction_of_prior_declaration | draft_003 [917.6, 1256.4]→[1000.3, 1256.4] |
| F2 | WS4 → F2:W_s4 | window | South | [17.256, 19.088] / 0.120 | [17.288, 19.092] / -0.087 | 0.033 / 0.207 | deterministic_correction_of_prior_declaration | draft_003 [1033.5, 1256.4]→[1116.2, 1256.4] |
| F2 | WS5 → F2:W_s5 | window | South | [21.291, 23.102] / 0.120 | [21.322, 23.126] / -0.087 | 0.031 / 0.207 | deterministic_correction_of_prior_declaration | draft_003 [1218.4, 1256.4]→[1301.1, 1256.4] |
| F2 | DN_NW1 → F2:D_g1 | door | interior:NW1<->C | [3.839, 4.647] / 16.052 | [3.883, 4.581] / 16.164 | 0.065 / 0.111 | image_measurement_or_estimate | draft_005 [419, 516.9]→[451, 516.9] |
| F2 | DN_NW2 → F2:D_g2 | door | interior:NW2<->C | [5.345, 6.174] / 16.052 | [5.432, 6.13] / 16.164 | 0.087 / 0.111 | image_measurement_or_estimate | draft_005 [490, 516.9]→[522, 516.9] |
| F2 | DN_NE → F2:D_mgr | door | interior:NE<->C | [10.1, 10.908] / 16.052 | [10.166, 10.864] / 16.164 | 0.065 / 0.111 | image_measurement_or_estimate | draft_003 [691.3, 485.6]→[691.3, 522.5] |
| F2 | DE1 → F2:D_c1 | door | interior:E1<->C | [14.351, 15.158] / 11.049 | [14.417, 15.115] / 11.187 | 0.065 / 0.137 | image_measurement_or_estimate | draft_003 [753.8, 567.8]→[753.8, 604.7] |
| F2 | DE2 → F2:D_c2 | door | interior:E2<->C | [12.824, 13.631] / 11.049 | [12.868, 13.566] / 11.187 | 0.065 / 0.137 | image_measurement_or_estimate | draft_003 [753.8, 639.4]→[753.8, 676.3] |
| F2 | DE3 → F2:D_c3 | door | interior:E3<->C | [10.338, 11.167] / 11.049 | [10.425, 11.123] / 11.187 | 0.087 / 0.137 | image_measurement_or_estimate | draft_003 [753.8, 727.4]→[753.8, 764.3] |
| F2 | DE4 → F2:D_c4 | door | interior:E4<->C | [8.833, 9.64] / 11.049 | [8.829, 9.655] / 11.187 | 0.015 / 0.137 | declared_value_basis_not_explicit | draft_003 [753.8, 815.3]→[753.8, 853.2] |
| F2 | DE5 → F2:D_c5 | door | interior:E5<->C | [6.827, 7.634] / 11.049 | [6.87, 7.568] / 11.187 | 0.065 / 0.137 | image_measurement_or_estimate | draft_003 [753.8, 902.1]→[753.8, 939.6] |
| F2 | DW → F2:D_mup | door | interior:W<->C | [12.083, 13.697] / 8.944 | [12.174, 13.684] / 8.763 | 0.092 / 0.181 | image_measurement_or_estimate | draft_003 [642.7, 630.6]→[642.7, 699.8] |
| F2 | DS1 → F2:D_b1 | door | interior:S1<->C | [7.919, 8.748] / 3.937 | [7.947, 8.767] / 3.740 | 0.028 / 0.196 | declared_value_basis_not_explicit | draft_003 [605.3, 1086.5]→[642.9, 1086.5] |
| F2 | DS2 → F2:D_b2 | door | interior:S2<->C | [9.446, 10.253] / 3.937 | [9.487, 10.312] / 3.740 | 0.059 / 0.196 | declared_value_basis_not_explicit | draft_003 [675.9, 1086.5]→[713.7, 1086.5] |
| F2 | DS3 → F2:D_b3 | door | interior:S3<->C | [15.75, 16.558] / 3.937 | [15.794, 16.492] / 3.740 | 0.065 / 0.196 | image_measurement_or_estimate | draft_003 [970.6, 1086.5]→[1009.3, 1086.5] |
| F2 | DS4 → F2:D_b4 | door | interior:S4<->C | [17.256, 18.085] / 3.937 | [17.256, 18.08] / 3.740 | 0.004 / 0.196 | image_measurement_or_estimate | draft_003 [1032.0, 1086.5]→[1069.8, 1086.5] |
| F2 | DS5 → F2:D_b5 | door | interior:S5<->C | [21.291, 22.12] / 3.937 | [21.379, 22.077] / 3.740 | 0.087 / 0.196 | image_measurement_or_estimate | draft_003 [1244.6, 1086.5]→[1284.2, 1086.5] |

未匹配参照：['WC_N', 'WW', 'WN_C']。
未匹配实际：['F1:D_r3']。

## 2026-10-04

汇总：位置 48/61，匹配 61，宿主 58，门连接 28。

| 层 | 参照 → 实际 | 类别 | 墙/立面 | 参照 span / cross (m) | 实际 span / cross (m) | 端点误差 / 垂墙误差 (m) | 依据 | 首次声明 |
|---|---|---|---|---|---|---|---|---|
| F1 | DS1 → F1:D_L1 | door | interior:S1<->C | [11.062, 12.641] / 3.935 | [11.039, 12.619] / 4.043 | 0.023 / 0.108 | image_measurement_or_estimate | draft_001 [792, 1048]→[865, 1048] |
| F1 | DS2 → F1:D_L2 | door | interior:S2<->C | [13.376, 14.955] / 3.935 | [13.377, 14.957] / 4.043 | 0.002 / 0.108 | image_measurement_or_estimate | draft_001 [900, 1048]→[973, 1048] |
| F1 | DX_WN → F1:D_west | door | West | [14.551, 15.33] / 0.130 | [14.443, 15.308] / 0.000 | 0.108 / 0.130 | declared_value_basis_not_explicit | draft_001 [282, 567]→[282, 527] |
| F1 | DX_E → F1:D_east | door | East | [0.562, 2.141] / 24.881 | [1.557, 3.157] / 25.000 | 1.016 / 0.119 | image_measurement_or_estimate | draft_001 [1437, 1163]→[1437, 1089] |
| F2 | WW_C → F2:W2_WW | window | West | [4.253, 5.453] / 5.116 | [4.1, 5.365] / 4.996 | 0.153 / 0.120 | deterministic_correction_of_prior_declaration | draft_006 [470, 1070]→[470, 1012] |
| F2 | DN_NW1 → F2:D2_A | door | interior:NW1<->C | [3.839, 4.647] / 16.052 | [3.883, 4.581] / 16.140 | 0.065 / 0.087 | image_measurement_or_estimate | draft_006 [419, 518]→[451, 518] |
| F2 | DN_NW2 → F2:D2_B | door | interior:NW2<->C | [5.345, 6.174] / 16.052 | [5.432, 6.13] / 16.140 | 0.087 / 0.087 | image_measurement_or_estimate | draft_006 [490, 518]→[522, 518] |
| F2 | DN_NE → F2:D2_Loff | door | interior:NE<->C | [10.1, 10.908] / 16.052 | [10.1, 10.929] / 16.140 | 0.022 / 0.087 | image_measurement_or_estimate | draft_004 [704, 518]→[742, 518] |
| F2 | DS1 → F2:D2_o1 | door | interior:S1<->C | [7.919, 8.748] / 3.937 | [6.894, 8.704] / 4.035 | 1.025 / 0.098 | image_measurement_or_estimate | draft_004 [557, 1060]→[640, 1060] |
| F2 | DS2 → F2:D2_o2 | door | interior:S2<->C | [9.446, 10.253] / 3.937 | [9.424, 11.257] / 4.035 | 1.003 / 0.098 | image_measurement_or_estimate | draft_004 [673, 1060]→[757, 1060] |
| F2 | DS3 → F2:D2_o3 | door | interior:S3<->C | [15.75, 16.558] / 3.937 | [14.769, 16.536] / 4.035 | 0.982 / 0.098 | image_measurement_or_estimate | draft_004 [918, 1060]→[999, 1060] |
| F2 | DS4 → F2:D2_o4 | door | interior:S4<->C | [17.256, 18.085] / 3.937 | [17.256, 19.175] / 4.035 | 1.091 / 0.098 | image_measurement_or_estimate | draft_004 [1032, 1060]→[1120, 1060] |
| F2 | DS5 → F2:D2_o5 | door | interior:S5<->C | [21.291, 22.12] / 3.937 | [21.793, 23.604] / 4.035 | 1.483 / 0.098 | image_measurement_or_estimate | draft_004 [1240, 1060]→[1323, 1060] |

未匹配参照：无。
未匹配实际：['F1:D_core', 'F2:W2_AW']。

## 首稿即出现的差异

- 2026-10-04 F1 draft_001：位置 25/31，声明 30 个；漏配 ['DN1']，多配 []。
- 2026-10-04 F2 draft_004：位置 20/30，声明 30 个；漏配 ['DN_NW1', 'DN_NW2']，多配 ['D2_c2', 'D2_c3']。
- 2026-10-05 F1 draft_001：位置 11/31，声明 32 个；漏配 []，多配 ['D_r3']。
- 2026-10-05 F2 draft_003：位置 10/30，声明 28 个；漏配 ['WW', 'DN_NW1', 'DN_NW2']，多配 ['D_mgr']。

完整数值、source_refs、容差和首稿 basis 见 `analysis_evidence.json`。
