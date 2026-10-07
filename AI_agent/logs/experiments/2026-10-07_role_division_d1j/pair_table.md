# 全部真实立面交付逐项对位

最终源稿；无源稿的 run4/27B 使用仅供评测的参照 fixture。完整误差、旧冲突及高度差见 matching.json。

| 运行 / 交付 | 对位基准 | 改前 | 改后 | 新增 |
|---|---|---:|---:|---:|
| sm24_run3 / elev_W | candidate_18 | 5 | 5 | 0 |
| sm24_run3 / elev_E | candidate_18 | 4 | 4 | 0 |
| sm24_run3 / elev_N | candidate_18 | 2 | 2 | 0 |
| sm24_run3 / elev_S | candidate_18 | 3 | 3 | 0 |
| sm24_run4 / elev_south | evaluation_reference_only | 0 | 0 | 0 |
| sm24_run4 / elev_east | evaluation_reference_only | 4 | 4 | 0 |
| sm24_run4 / elev_north | evaluation_reference_only | 2 | 2 | 0 |
| sm24_run5 / elev_west | candidate_05 | 4 | 4 | 0 |
| sm24_run5 / elev_south | candidate_05 | 3 | 3 | 0 |
| sm24_run5 / elev_east | candidate_05 | 0 | 0 | 0 |
| sm24_run5 / elev_north | candidate_05 | 2 | 2 | 0 |
| sm24_run5 / elev_east_r2 | candidate_05 | 4 | 4 | 0 |
| sm24_run5 / elev_west_r2 | candidate_05 | 5 | 5 | 0 |
| sm24_run6 / elev_north_v1 | candidate_05 | 2 | 2 | 0 |
| sm24_run6 / elev_south_v2 | candidate_05 | 3 | 3 | 0 |
| sm24_run6 / elev_west_v1 | candidate_05 | 0 | 0 | 0 |
| sm24_run6 / elev_east_v1 | candidate_05 | 4 | 4 | 0 |
| sm24_run7 / elev_west | candidate_04 | 5 | 5 | 0 |
| sm24_run7 / elev_south | candidate_04 | 3 | 3 | 0 |
| sm24_run7 / elev_east | candidate_04 | 2 | 4 | 2 |
| sm24_run7 / elev_north | candidate_04 | 2 | 2 | 0 |
| sm24_run7 / elev_east_r2 | candidate_04 | 4 | 4 | 0 |
| sm21_run1 / elev_west | candidate_04 | 2 | 2 | 0 |
| sm21_run1 / elev_south | candidate_04 | 8 | 8 | 0 |
| sm21_run1 / elev_east | candidate_04 | 2 | 2 | 0 |
| sm21_run1 / elev_north | candidate_04 | 5 | 5 | 0 |
| sm25_run1 / elev_west | candidate_07 | 6 | 6 | 0 |
| sm25_run1 / elev_south | candidate_07 | 7 | 7 | 0 |
| sm25_run1 / elev_east | candidate_07 | 13 | 13 | 0 |
| sm25_run1 / elev_north | candidate_07 | 8 | 8 | 0 |
| qwen27b_r1 / sm24-west | evaluation_reference_only | 5 | 5 | 0 |
| qwen27b_r1 / sm24-east | evaluation_reference_only | 4 | 4 | 0 |
| qwen27b_r1 / sm24-north | evaluation_reference_only | 2 | 2 | 0 |
| qwen27b_r1 / sm24-south | evaluation_reference_only | 3 | 3 | 0 |

每个已对上对象（新增标为 +；原有不符项保留显示）：

| 运行 / 交付 | 图中 ID → 源 ID | 参照 ID | 身份核对 | 高度核对 | 新增 |
|---|---|---|---|---|---|
| sm24_run3 / elev_W | W1 → W5 | op_ae7 | 通过 | 通过 |  |
| sm24_run3 / elev_W | W2 → W6 | op_aed | 通过 | 通过 |  |
| sm24_run3 / elev_W | W3 → W7 | op_af0 | 通过 | 通过 |  |
| sm24_run3 / elev_W | W4 → W8 | op_af3 | 通过 | 通过 |  |
| sm24_run3 / elev_W | W5 → W9 | op_ae4 | 通过 | 通过 |  |
| sm24_run3 / elev_E | D1 → D2 | op_ac9 | 通过 | 通过 |  |
| sm24_run3 / elev_E | W1 → W4 | op_aff | 通过 | 通过 |  |
| sm24_run3 / elev_E | W2 → W3 | op_afc | 通过 | 通过 |  |
| sm24_run3 / elev_E | W3 → W2 | op_aea | 通过 | 通过 |  |
| sm24_run3 / elev_N | D1 → D1 | op_ac3 | 通过 | 通过 |  |
| sm24_run3 / elev_N | W1 → W1 | op_ae1 | 通过 | 通过 |  |
| sm24_run3 / elev_S | S-D1 → D3 | op_ade | 通过 | 通过 |  |
| sm24_run3 / elev_S | S-W1 → W10 | op_af6 | 通过 | 通过 |  |
| sm24_run3 / elev_S | S-W2 → W11 | op_af9 | 通过 | 通过 |  |
| sm24_run4 / elev_east | D1 → op_ac9 | op_ac9 | 通过 | 通过 |  |
| sm24_run4 / elev_east | W1 → op_aff | op_aff | 通过 | 通过 |  |
| sm24_run4 / elev_east | W2 → op_afc | op_afc | 通过 | 通过 |  |
| sm24_run4 / elev_east | W3 → op_aea | op_aea | 通过 | 通过 |  |
| sm24_run4 / elev_north | D1 → op_ac3 | op_ac3 | 通过 | 通过 |  |
| sm24_run4 / elev_north | W1 → op_ae1 | op_ae1 | 通过 | 通过 |  |
| sm24_run5 / elev_west | W1 → W_W1 | op_ae7 | 通过 | 通过 |  |
| sm24_run5 / elev_west | W3 → W_W3 | op_af0 | 通过 | 通过 |  |
| sm24_run5 / elev_west | W4 → W_W5 | op_af3 | 通过 | 通过 |  |
| sm24_run5 / elev_west | W5 → W_W6 | op_ae4 | 通过 | 通过 |  |
| sm24_run5 / elev_south | S-D1 → D_bot | op_ade | 通过 | 通过 |  |
| sm24_run5 / elev_south | S-W1 → W_N1 | op_af6 | 通过 | 通过 |  |
| sm24_run5 / elev_south | S-W2 → W_N2 | op_af9 | 通过 | 通过 |  |
| sm24_run5 / elev_north | D1 → D_entr | op_ac3 | 通过 | 通过 |  |
| sm24_run5 / elev_north | W1 → W_S1 | op_ae1 | 通过 | 通过 |  |
| sm24_run5 / elev_east_r2 | D1 → D_E1 | op_ac9 | 通过 | 通过 |  |
| sm24_run5 / elev_east_r2 | W1 → W_E3 | op_aff | 通过 | 通过 |  |
| sm24_run5 / elev_east_r2 | W2 → W_E2 | op_afc | 通过 | 通过 |  |
| sm24_run5 / elev_east_r2 | W3 → W_E1 | op_aea | 通过 | 通过 |  |
| sm24_run5 / elev_west_r2 | W1 → W_W1 | op_ae7 | 通过 | 通过 |  |
| sm24_run5 / elev_west_r2 | W2 → W_W2 | op_aed | 通过 | 通过 |  |
| sm24_run5 / elev_west_r2 | W3 → W_W3 | op_af0 | 通过 | 通过 |  |
| sm24_run5 / elev_west_r2 | W4 → W_W5 | op_af3 | 通过 | 通过 |  |
| sm24_run5 / elev_west_r2 | W5 → W_W6 | op_ae4 | 通过 | 通过 |  |
| sm24_run6 / elev_north_v1 | N_D1 → D1 | op_ac3 | 通过 | 通过 |  |
| sm24_run6 / elev_north_v1 | N_W1 → W_T1 | op_ae1 | 通过 | 通过 |  |
| sm24_run6 / elev_south_v2 | D1 → D2 | op_ade | 通过 | 通过 |  |
| sm24_run6 / elev_south_v2 | W1 → W_B0 | op_af6 | 通过 | 通过 |  |
| sm24_run6 / elev_south_v2 | W2 → W_B1 | op_af9 | 通过 | 通过 |  |
| sm24_run6 / elev_east_v1 | E_D1 → D3 | op_ac9 | 通过 | 通过 |  |
| sm24_run6 / elev_east_v1 | E_W1 → W_E3 | op_aff | 通过 | 通过 |  |
| sm24_run6 / elev_east_v1 | E_W2 → W_E2 | op_afc | 通过 | 通过 |  |
| sm24_run6 / elev_east_v1 | E_W3 → W_E1 | op_aea | 通过 | 通过 |  |
| sm24_run7 / elev_west | W1 → W-l1 | op_ae7 | 通过 | 通过 |  |
| sm24_run7 / elev_west | W2 → W-l2 | op_aed | 通过 | 通过 |  |
| sm24_run7 / elev_west | W3 → W-l3 | op_af0 | 通过 | 通过 |  |
| sm24_run7 / elev_west | W4 → W-l4 | op_af3 | 通过 | 通过 |  |
| sm24_run7 / elev_west | WG1 → W-l5 | op_ae4 | 通过 | 通过 |  |
| sm24_run7 / elev_south | S-D1 → D-south | op_ade | 通过 | 通过 |  |
| sm24_run7 / elev_south | S-W1 → W-b1 | op_af6 | 通过 | 通过 |  |
| sm24_run7 / elev_south | S-W2 → W-b2 | op_af9 | 通过 | 通过 |  |
| sm24_run7 / elev_east | E-D1 → D-entry-e | op_ac9 | 通过 | 通过 |  |
| sm24_run7 / elev_east | E-W1 → W-r3 | op_aff | 通过 | 通过 |  |
| sm24_run7 / elev_east | E-W2 → W-r2 | op_afc | 通过 | 通过 | + |
| sm24_run7 / elev_east | E-W3 → W-r1 | op_aea | 通过 | 通过 | + |
| sm24_run7 / elev_north | D1 → D-entry-n | op_ac3 | 通过 | 通过 |  |
| sm24_run7 / elev_north | W1 → W-top | op_ae1 | 通过 | 通过 |  |
| sm24_run7 / elev_east_r2 | E-D1 → D-entry-e | op_ac9 | 通过 | 通过 |  |
| sm24_run7 / elev_east_r2 | E-W1 → W-r3 | op_aff | 通过 | 通过 |  |
| sm24_run7 / elev_east_r2 | E-W2 → W-r2 | op_afc | 通过 | 通过 |  |
| sm24_run7 / elev_east_r2 | E-W3 → W-r1 | op_aea | 通过 | 通过 |  |
| sm21_run1 / elev_west | D1 → F1:D-W1 | door_0 | 通过 | 通过 |  |
| sm21_run1 / elev_west | W1 → F2:W-W1 | window_group_7_item_0 | 通过 | 通过 |  |
| sm21_run1 / elev_south | D1 → F1:D-S1 | door_1 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W1 → F1:W-S1 | window_group_2_item_0 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W2 → F1:W-S2 | window_group_2_item_1 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W3 → F1:W-S3 | window_group_2_item_2 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W4 → F2:W-S1 | window_group_3_item_0 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W5 → F2:W-S2 | window_group_3_item_1 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W6 → F2:W-S3 | window_group_3_item_2 | 通过 | 通过 |  |
| sm21_run1 / elev_south | W7 → F2:W-S4 | window_group_3_item_3 | 通过 | 通过 |  |
| sm21_run1 / elev_east | W_F1_E1 → F1:W-E1 | window_group_4_item_0 | 通过 | 通过 |  |
| sm21_run1 / elev_east | W_F2_E1 → F2:W-E1 | window_group_5_item_0 | 通过 | 通过 |  |
| sm21_run1 / elev_north | W1 → F1:W-N3 | window_group_0_item_2 | 通过 | 通过 |  |
| sm21_run1 / elev_north | W2 → F1:W-N2 | window_group_0_item_1 | 通过 | 通过 |  |
| sm21_run1 / elev_north | W3 → F1:W-N1 | window_group_0_item_0 | 通过 | 通过 |  |
| sm21_run1 / elev_north | W4 → F2:W-N2 | window_group_1_item_1 | 通过 | 通过 |  |
| sm21_run1 / elev_north | W5 → F2:W-N1 | window_group_1_item_0 | 通过 | 通过 |  |
| sm25_run1 / elev_west | D1 → F1:D1 | op_156b | 通过 | 通过 |  |
| sm25_run1 / elev_west | D2 → F1:D13 | op_156e | 通过 | 通过 |  |
| sm25_run1 / elev_west | W1 → F1:W4 | op_159d | 通过 | 通过 |  |
| sm25_run1 / elev_west | W2 → F1:W5 | op_15a0 | 通过 | 通过 |  |
| sm25_run1 / elev_west | W3 → F2:W_conf | op_15b8 | 通过 | 通过 |  |
| sm25_run1 / elev_west | W4 → F2:W_scorr_w | op_15d3 | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW1-1 → F1:W14 | op_15be | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW1-2 → F1:W15 | op_15c1 | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW2-1 → F2:W_s1 | op_15c4 | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW2-2 → F2:W_s2 | op_15c7 | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW2-3 → F2:W_s3 | op_15ca | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW2-4 → F2:W_s4 | op_15cd | 通过 | 通过 |  |
| sm25_run1 / elev_south | SW2-5 → F2:W_s5 | op_15d0 | 通过 | 通过 |  |
| sm25_run1 / elev_east | D1 → F1:D16 | op_1571 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W1 → F1:W12 | op_159a | 通过 | 通过 |  |
| sm25_run1 / elev_east | W2 → F1:W11 | op_1597 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W3 → F1:W10 | op_1594 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W4 → F1:W9 | op_1591 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W5 → F1:W8 | op_158e | 通过 | 通过 |  |
| sm25_run1 / elev_east | W6 → F1:W7 | op_158b | 通过 | 通过 |  |
| sm25_run1 / elev_east | W7 → F1:W6 | op_1588 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W8 → F2:W_off5 | op_15b5 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W9 → F2:W_off4 | op_15b2 | 通过 | 通过 |  |
| sm25_run1 / elev_east | W10 → F2:W_off3 | op_15af | 通过 | 通过 |  |
| sm25_run1 / elev_east | W11 → F2:W_off2 | op_15ac | 通过 | 通过 |  |
| sm25_run1 / elev_east | W12 → F2:W_off1 | op_15a9 | 通过 | 通过 |  |
| sm25_run1 / elev_north | BAND_F1 → F1:W13 | op_15d6 | 通过 | 通过 |  |
| sm25_run1 / elev_north | WN_F1 → F1:W3 | op_1585 | 通过 | 通过 |  |
| sm25_run1 / elev_north | WA_F1 → F1:W2 | op_1582 | 通过 | 通过 |  |
| sm25_run1 / elev_north | WB_F1 → F1:W1 | op_157f | 通过 | 通过 |  |
| sm25_run1 / elev_north | BAND_F2 → F2:W_ribbon | op_15d9 | 通过 | 通过 |  |
| sm25_run1 / elev_north | WN_F2 → F2:W_mgr | op_15bb | 通过 | 通过 |  |
| sm25_run1 / elev_north | WA_F2 → F2:W_m2 | op_15a6 | 通过 | 通过 |  |
| sm25_run1 / elev_north | WB_F2 → F2:W_m1 | op_15a3 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-west | W1 → op_ae7 | op_ae7 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-west | W2 → op_aed | op_aed | 通过 | 通过 |  |
| qwen27b_r1 / sm24-west | W3 → op_af0 | op_af0 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-west | W4 → op_af3 | op_af3 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-west | W5 → op_ae4 | op_ae4 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-east | D1 → op_ac9 | op_ac9 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-east | W1 → op_aff | op_aff | 通过 | 通过 |  |
| qwen27b_r1 / sm24-east | W2 → op_afc | op_afc | 通过 | 通过 |  |
| qwen27b_r1 / sm24-east | W3 → op_aea | op_aea | 通过 | 通过 |  |
| qwen27b_r1 / sm24-north | D1 → op_ac3 | op_ac3 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-north | W1 → op_ae1 | op_ae1 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-south | D1 → op_ade | op_ade | 通过 | 通过 |  |
| qwen27b_r1 / sm24-south | W1 → op_af6 | op_af6 | 通过 | 通过 |  |
| qwen27b_r1 / sm24-south | W2 → op_af9 | op_af9 | 通过 | 通过 |  |
