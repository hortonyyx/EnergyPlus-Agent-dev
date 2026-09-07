# G-c rework1 T4 锁存货逐项对照

外延方法：先对tests全部Python源码检索13AD/13AE/13AF、rev-、axis_snapped_lines、non_orthogonal_lines、AXIS_SNAP_MAX_ANGLE_DEG、AXIS_SNAP_MAX_DEVIATION_M及10 mm；再用AST补找断言中faces/walls/targets/segments的len或数值比较。随后沿模块常量、fixture和helper展开：特别补入B1的face-handle定位、staging的unsigned helper、deferred ledger两个消费者，以及o21d的实时loss与构造loss两半。表内按完整测试函数名列出相关锁，参数化项仍保留在原函数。

结论中的“无需动；前任已…”指fd5c3388已有的重推，不能误读为旧口径无需修改。T4额外修复三处：after_p1豁免方向、facts成功路径BLOCK库存、每次仅删一条snap的反例。三个同形变异在T4前3 passed，T4后3 failed。

| 锁（tests/相对路径） | 它的存货 | 阶梯之后还在吗 | 结论 |
|---|---|---|---|
| `test_a11_gt_1mm_ingest_resolution.py::test_the_scan_goes_red_when_the_snap_is_removed` | 关闭入库吸附后的非网格坐标出现次数 | 改变：独立字段枚举为104；面线48并非条数 | 需重推；T3已完成 |
| `test_a11_gt_1mm_ingest_resolution.py::test_external_quantities_are_bit_identical` | 同图两种入库表示的身份及外部量 | 身份未变，F1排序位置变4处；新增6种身份损坏 | 需重建负样本；T2已完成 |
| `test_a11_gt_1mm_ingest_resolution.py::test_the_exemption_table_cannot_rot_onto_a_coordinate` | 坐标字段不能被豁免；原non_orthogonal路径不属schema且现在应为RAW | 旧路径无实体；用真实after_p1坐标替换，错误豁免旧绿新红 | 需重推；T4修复 |
| `test_a11_gt_1mm_ingest_resolution.py::test_identity_lock_document_level` | 真实faces按handle配对、网格坐标及暂存三件套 | 仍在；配对先验、移动上界与扫描对象非空 | 无需动；T3已澄清plain是当前阶梯反事实 |
| `test_a11_gt_1mm_ingest_resolution.py::test_max_coordinate_move_is_within_half_a_millimetre` | 真实faces按handle配对、网格坐标及暂存三件套 | 仍在；配对先验、移动上界与扫描对象非空 | 无需动；T3已澄清plain是当前阶梯反事实 |
| `test_a11_gt_1mm_ingest_resolution.py::test_snapped_documents_scan_green` | 真实faces按handle配对、网格坐标及暂存三件套 | 仍在；配对先验、移动上界与扫描对象非空 | 无需动；T3已澄清plain是当前阶梯反事实 |
| `test_a11_gt_1mm_ingest_resolution.py::test_sm24_snapped_scan_is_green` | 真实faces按handle配对、网格坐标及暂存三件套 | 仍在；配对先验、移动上界与扫描对象非空 | 无需动；T3已澄清plain是当前阶梯反事实 |
| `test_a11_gt_1mm_ingest_resolution.py::test_staged_trio_scans_green` | 真实faces按handle配对、网格坐标及暂存三件套 | 仍在；配对先验、移动上界与扫描对象非空 | 无需动；T3已澄清plain是当前阶梯反事实 |
| `test_a11_gt_1mm_ingest_resolution.py::test_the_declaration_point` | 单位声明、枚举网格值、半格两侧 | 构造值独立于CAD负样本 | 无需动 |
| `test_a11_gt_1mm_ingest_resolution.py::test_snap_is_the_identity_on_grid_values` | 单位声明、枚举网格值、半格两侧 | 构造值独立于CAD负样本 | 无需动 |
| `test_a11_gt_1mm_ingest_resolution.py::test_snap_bankers_rounding_and_bounds` | 单位声明、枚举网格值、半格两侧 | 构造值独立于CAD负样本 | 无需动 |
| `test_answer_compiler_profiles.py::test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na` | 原rev-13ad/ae/af及受影响房间 | 真实台账消失；在真实faces上重建三条unsigned；request名单和独立pairings钉完整性，clean边依赖推导受影响集合 | 需重建负样本；T2已完成 |
| `test_answer_compiler_profiles.py::test_1a_fully_signed_synthetic_ledger_reproduces_the_known_target_bit_for_bit` | synthetic_signed_facts的房间、签字action、退化support反例 | 合成库存独立构造，不读取已清空真实台账 | 无需动 |
| `test_answer_compiler_profiles.py::test_6a_axis_profile_deduplicates_a_collapsed_step_and_counterfactual_is_red` | synthetic_signed_facts的房间、签字action、退化support反例 | 合成库存独立构造，不读取已清空真实台账 | 无需动 |
| `test_answer_compiler_profiles.py::test_6b_one_wall_support_cannot_switch_basis_mid_span` | synthetic_signed_facts的房间、签字action、退化support反例 | 合成库存独立构造，不读取已清空真实台账 | 无需动 |
| `test_answer_compiler_profiles.py::test_6c_vertices_are_support_line_intersections_not_wall_endpoints` | synthetic_signed_facts的房间、签字action、退化support反例 | 合成库存独立构造，不读取已清空真实台账 | 无需动 |
| `test_answer_compiler_profiles.py::test_profiles_have_the_three_metamorphic_relations_in_both_directions` | synthetic_signed_facts的房间、签字action、退化support反例 | 合成库存独立构造，不读取已清空真实台账 | 无需动 |
| `test_answer_compiler_profiles.py::test_clear_span_is_a_derived_table_not_a_profile` | synthetic_signed_facts的房间、签字action、退化support反例 | 合成库存独立构造，不读取已清空真实台账 | 无需动 |
| `test_as_drawn_denominator_f126.py::test_l4_discarded_non_orthogonal_segments_are_itemised` | D1仍收到的非正交笔画与成功路径BLOCK | 13AF/自由端消失；临时图跨q格笔画重建D1记录与G5红 | 需重建负样本；T2已完成 |
| `test_as_drawn_denominator_f126.py::test_l1_signed_drawing_still_yields_the_same_denominator` | signed图两个视图的targets/开口/长度及非正交零库存 | signed图未改变；前者钉数与长度、后者是正样本对照 | 无需动 |
| `test_as_drawn_denominator_f126.py::test_l4b_signed_drawing_has_no_non_orthogonal_inventory` | signed图两个视图的targets/开口/长度及非正交零库存 | signed图未改变；前者钉数与长度、后者是正样本对照 | 无需动 |
| `test_as_drawn_denominator_f126.py::test_l2_blocked_input_raises_and_names_the_blocking_code` | 源哈希错配或空几何等显式反例 | 仍在，与阶梯接头无关 | 无需动 |
| `test_as_drawn_denominator_f126.py::test_l2b_the_two_ways_of_being_empty_do_not_share_one_exit` | 源哈希错配或空几何等显式反例 | 仍在，与阶梯接头无关 | 无需动 |
| `test_as_drawn_denominator_f126.py::test_l3_diagnostics_ride_out_on_both_paths` | 源哈希错配或空几何等显式反例 | 仍在，与阶梯接头无关 | 无需动 |
| `test_as_drawn_denominator_consistency_readout.py::test_l6_gates_discriminate_on_the_blocked_geometry` | 原as-received的G1/G5/BLOCK/dangles | 真实负样本消失；前任已用45度笔画与孤立正交笔画分别构造 | 无需动；前任已重建，194条定向跑含本文件 |
| `test_as_drawn_denominator_consistency_readout.py::test_l7b_block_diagnostics_are_localisable_and_fields_always_present` | 原as-received的G1/G5/BLOCK/dangles | 真实负样本消失；前任已用45度笔画与孤立正交笔画分别构造 | 无需动；前任已重建，194条定向跑含本文件 |
| `test_as_drawn_denominator_consistency_readout.py::test_l8_s4_closure_counts_ride_out` | 原as-received的G1/G5/BLOCK/dangles | 真实负样本消失；前任已用45度笔画与孤立正交笔画分别构造 | 无需动；前任已重建，194条定向跑含本文件 |
| `test_as_drawn_denominator_consistency_readout.py::test_l5_gates_ride_out_on_the_signed_drawing` | signed正样本、源哈希错配、13DC退化线、无定位合成诊断 | 均仍在；13DC不是此次三条歪线 | 无需动 |
| `test_as_drawn_denominator_consistency_readout.py::test_l6b_gates_ride_out_on_the_exception_too` | signed正样本、源哈希错配、13DC退化线、无定位合成诊断 | 均仍在；13DC不是此次三条歪线 | 无需动 |
| `test_as_drawn_denominator_consistency_readout.py::test_l7_diagnostics_carry_localisation_not_just_context` | signed正样本、源哈希错配、13DC退化线、无定位合成诊断 | 均仍在；13DC不是此次三条歪线 | 无需动 |
| `test_as_drawn_denominator_consistency_readout.py::test_l7c_unlocalisable_is_stated_not_silent` | signed正样本、源哈希错配、13DC退化线、无定位合成诊断 | 均仍在；13DC不是此次三条歪线 | 无需动 |
| `test_as_measured_facts_layer.py::test_r2_measured_inventory` | 四个图/视图的faces、walls、开口、厚度、S4、cap存货 | as-received F1已与signed F1收敛；EXPECTED附逐项来源 | 无需动；前任已重推 |
| `test_as_measured_facts_layer.py::test_r2_the_as_received_drawing_differs_from_the_signed_one_as_f129_measured` | 曾经几何不相同；现在要辨识是否经过吸附 | 几何相同，真实三条snap审计仍在，signed为空 | 无需动；前任已重推 |
| `test_as_measured_facts_layer.py::test_r4_the_wider_s1_identity_is_real_on_as_received_plan_f1` | all handles、13DC和三条snap的账实闭合 | 226=225+1，三条snap为13AD/AE/AF，真实数据仍在 | 无需动；前任已重推 |
| `test_as_measured_facts_layer.py::test_o21bs_the_real_snap_list_has_exactly_the_three_known_handles` | all handles、13DC和三条snap的账实闭合 | 226=225+1，三条snap为13AD/AE/AF，真实数据仍在 | 无需动；前任已重推 |
| `test_as_measured_facts_layer.py::test_o21bs_deleting_a_snap_entry_turns_the_ledger_red` | 单条snap记录消失 | 列表从2增至3后[:1]实际删2；单删方向失去反例 | 需重建负样本；T4逐条删除，每次只删一条 |
| `test_as_measured_facts_layer.py::test_r2_readouts_are_the_converters_own_numbers` | 成功构建中的BLOCK及失败gate透传 | 真实BLOCK消失；旧锁对删BLOCK变异绿；临时孤立线重建 | 需重建负样本；T4修复，旧绿新红 |
| `test_as_measured_facts_layer.py::test_f148_snap_list_angle_is_required_and_bound_to_its_diagnostic` | 真实snap行上的删角度/改角度/假handle/重复归类 | 仍有三条可选，变异均直接构造 | 无需动；更正过时13AF描述 |
| `test_as_measured_facts_layer.py::test_o21bs_a_snapped_handle_must_be_a_real_face_line` | 真实snap行上的删角度/改角度/假handle/重复归类 | 仍有三条可选，变异均直接构造 | 无需动；更正过时13AF描述 |
| `test_as_measured_facts_layer.py::test_o21bs_a_handle_cannot_be_both_snapped_and_s1_discarded` | 真实snap行上的删角度/改角度/假handle/重复归类 | 仍有三条可选，变异均直接构造 | 无需动；更正过时13AF描述 |
| `test_as_measured_facts_layer.py::test_r2_a_band_whose_second_face_was_never_drawn_is_named_not_dropped` | 真实missing-face bands、boundary edges、开口及owner关系 | 仍有非空存货；179边和每开口owner形态被断言 | 无需动 |
| `test_as_measured_facts_layer.py::test_r2_projection_fields_are_absent_but_boundary_condition_is_first_class` | 真实missing-face bands、boundary edges、开口及owner关系 | 仍有非空存货；179边和每开口owner形态被断言 | 无需动 |
| `test_as_measured_facts_layer.py::test_r2_every_opening_names_its_carrier_wall` | 真实missing-face bands、boundary edges、开口及owner关系 | 仍有非空存货；179边和每开口owner形态被断言 | 无需动 |
| `test_as_measured_facts_layer.py::test_r2_the_ledger_identity_has_teeth` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r2_a_dangling_reference_is_refused` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r4_removing_13dc_from_the_itemized_list_turns_the_identity_red` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r4_removing_13dc_and_its_count_together_breaks_the_primary_identity` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r1_pairing_every_collected_face_line_puts_the_ghost_walls_back` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r1_a_wall_cannot_be_built_without_ink_on_both_faces` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r1_the_face_line_consumption_ledger_has_teeth` | 主动删除face/13DC、伪引用、错误墙配对的反例 | 真实faces/walls/13DC仍在；错误配对由测试重新构造 | 无需动；前任已更新225条faces的前提 |
| `test_as_measured_facts_layer.py::test_r2_every_wall_thickness_recomputes_from_its_two_stored_faces` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_r2_every_reference_resolves` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_r1_the_wall_axis_and_its_face_lines_agree_after_the_one_flip` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_r3_upstream_iteration_order_cannot_move_the_digest` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_r3_each_ordering_seam_is_load_bearing` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_r3_the_builder_leaves_every_list_in_a_total_order` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_r3_the_wall_sort_key_is_what_makes_walls_totally_ordered` | 非空几何表的关系与顺序；主动逆序/废除排序seam | 仍在；与T2列表位置不是身份的修正互补 | 无需动 |
| `test_as_measured_facts_layer.py::test_gc_a11d3_a_non_orthogonal_row_keeps_its_sub_millimetre_evidence` | 原13AF的RAW非正交端点 | 真实行消失；前任用_StubGeo及注入行补回，并移除豁免反测 | 无需动；前任已重建 |
| `test_as_measured_facts_layer.py::test_gc_a11d3_the_exit_scan_exempts_that_row_and_would_flag_it_otherwise` | 原13AF的RAW非正交端点 | 真实行消失；前任用_StubGeo及注入行补回，并移除豁免反测 | 无需动；前任已重建 |
| `test_as_measured_facts_layer.py::test_gc_the_arbitration_row_validates_and_carries_what_a_signer_needs` | 档2/档3具名诊断及仲裁行 | 语料本来没有；前任合成行与诊断提供两侧样本 | 无需动 |
| `test_as_measured_facts_layer.py::test_gc_deleting_an_arbitration_row_turns_the_ledger_red` | 档2/档3具名诊断及仲裁行 | 语料本来没有；前任合成行与诊断提供两侧样本 | 无需动 |
| `test_as_measured_facts_layer.py::test_gc_an_arbitration_row_cannot_disagree_with_its_diagnostic` | 档2/档3具名诊断及仲裁行 | 语料本来没有；前任合成行与诊断提供两侧样本 | 无需动 |
| `test_as_measured_facts_layer.py::test_gc_tier3_does_not_enter_the_arbitration_ledger` | 档2/档3具名诊断及仲裁行 | 语料本来没有；前任合成行与诊断提供两侧样本 | 无需动 |
| `test_gt_facts_staging_sm25.py::test_6_the_worklist_is_empty_because_the_detector_finds_nothing` | 真实待签台账及检测器是否活着 | 台账为空；前任另移动13AD并对齐wall后验证检测器仍出候选 | 无需动；前任已重建 |
| `test_gt_facts_staging_sm25.py::test_3_signing_a_const_candidate_is_refused_by_the_wall_face_gate` | 从真实rev记录取样再签字/损坏 | 真实记录消失；前任_synthetic_unsigned_record补回并走真实读写门 | 无需动；前任已重建 |
| `test_gt_facts_staging_sm25.py::test_3_hand_tampering_a_revisions_action_moves_as_signed_and_its_hash` | 从真实rev记录取样再签字/损坏 | 真实记录消失；前任_synthetic_unsigned_record补回并走真实读写门 | 无需动；前任已重建 |
| `test_gt_facts_staging_sm25.py::test_r2_on_disk_revisions_schema_break_is_caught_before_verify_even_runs` | 从真实rev记录取样再签字/损坏 | 真实记录消失；前任_synthetic_unsigned_record补回并走真实读写门 | 无需动；前任已重建 |
| `test_gt_facts_staging_sm25.py::test_1_as_measured_matches_the_as_received_build_bit_for_bit` | 三件套、几何值和内容哈希 | 仍在；字节由同树重建，错误样本显式改字段/哈希 | 无需动 |
| `test_gt_facts_staging_sm25.py::test_3_the_staged_trio_reproduces_bit_for_bit` | 三件套、几何值和内容哈希 | 仍在；字节由同树重建，错误样本显式改字段/哈希 | 无需动 |
| `test_gt_facts_staging_sm25.py::test_3_a_hand_tampered_integer_in_the_staged_as_signed_is_caught` | 三件套、几何值和内容哈希 | 仍在；字节由同树重建，错误样本显式改字段/哈希 | 无需动 |
| `test_gt_facts_staging_sm25.py::test_r2_on_disk_as_signed_tamper_is_caught_through_the_real_read_path` | 三件套、几何值和内容哈希 | 仍在；字节由同树重建，错误样本显式改字段/哈希 | 无需动 |
| `test_gt_facts_staging_sm25.py::test_r2_on_disk_as_measured_hash_break_is_caught` | 三件套、几何值和内容哈希 | 仍在；字节由同树重建，错误样本显式改字段/哈希 | 无需动 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock1_tier1_admits_and_itemises_with_the_derived_ceiling` | 3 mm out over a 2000 mm run = 0.086°: inside the 5° envelope and inside | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock2_over_cap_is_still_refused_and_is_named_arbitration` | 20 mm out over 2000 mm = 0.573°: the ANGLE says yes (0.573 < 5), so the | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock3_cap_is_derived_per_request_not_baked_in` | _lock3_cap_is_derived_per_request_not_baked_in | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock4_real_tremor_all_three_strokes_are_tier1_and_auditable` | _lock4_real_tremor_all_three_strokes_are_tier1_and_auditable | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock4b_the_anchor_rule_closes_the_joints_the_midpoint_split` | ⭐⭐ THE VARIABILITY PROOF for lock 4, and the acceptance G-c-1 asks for: | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock5_the_deviation_ceiling_still_has_teeth_now_as_cap` | 2000 mm run, 8 mm out = 0.229°.  The ENVELOPE says yes either way, so | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock5b_the_retired_10mm_ceiling_is_not_silently_still_in_force` | ⭐ The other half of lock 5's retirement: prove the 10 mm number is not | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock6_on_a_short_stroke_only_the_angle_can_refuse` | 60 mm long.  5.00 mm out = 4.764° (inside) and 5.30 mm out = 5.046° | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock7_forty_five_degrees_is_tier3_and_never_reaches_a_human` | _lock7_forty_five_degrees_is_tier3_and_never_reaches_a_human | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock8_five_degrees_still_admits_the_0p39deg_slanted_wall_KNOWN_RISK` | ⛔⛔ THIS TEST PINS A COST, ⛔ NOT A CORRECTNESS CLAIM. | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock9_moving_only_the_angle_envelope_flips_a_case` | Same 60 mm / 5 mm stroke as lock 6.  ⛔ The request's declared thickness | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock10_the_envelope_and_the_cap_are_not_redundant` | Two strokes, each refused by exactly one of the two limits, ⛔ with the | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock11_the_snap_alone_never_moves_an_along_axis_endpoint` | _lock11_the_snap_alone_never_moves_an_along_axis_endpoint | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_lock11b_an_along_axis_endpoint_DOES_follow_a_relocated_node` | ⭐⭐ The exception, on a fixture that reproduces the corpus' west corner | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier0_boundary_at_q_noise_is_not_recorded_at_all` | ⭐ Both sides of ``q`` = 0.1 mm.  ⛔ Under it there must be NO record of | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier1_boundary_is_cap_on_a_long_stroke` | ⭐ Both sides of the tier-1 ceiling where CAP binds.  2000 mm run, | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier1_boundary_is_the_angle_on_a_short_stroke` | ⭐ Both sides of the tier-1 ceiling where the ANGLE binds instead -- | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier2a_long_stroke_inside_the_envelope_but_over_cap` | ⭐⭐ THE RISK FACE OF THE 5° CHANGE, and the格 the dispatch calls out: | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier2b_both_ends_anchored_is_a_suspected_real_slant` | ⭐⭐ The other tier-2 door, and the one the anchor rule opens: a skew | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier2c_unanchored_and_visibly_different_goes_to_a_human` | ⭐⭐ The zero-threshold observability rule, BOTH sides. | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc6_tier3_boundary_is_the_signed_five_degrees` | ⭐ Both sides of the user-signed envelope, on a stroke short enough that | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_ladder_limit_table_matches_the_shape_the_user_asked_for` | ⭐ "长度越长容差应该越大一些" AND "长线上小角度已经很显眼" are BOTH true, | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_ladder_limit_first_limb_is_subsumed_by_the_angle_envelope` | ⚠️ A MEASURED PROPERTY, recorded so nobody reads more into | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_ingest_grid_is_tau_node_not_a_fourth_threshold` | ⭐⭐⭐ THE "no fourth threshold" LOCK.  The observability rule rounds its | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_gc_the_ladder_holds_exactly_three_numbers` | ⛔ The unit's hard constraint, made executable: ``q`` (derived), ``CAP`` | 真实三条歪线或显式构造的q/CAP/角度/锚端两侧样本仍在 | 无需动；前任已重推/补齐，定向跑通过 |
| `test_tarch_converter_p1_geometry.py::test_sm24_exit_gate_openings_21_and_topology_clean` | sm24几何基线、45度斜线、孤立直线、合成闭合房间 | 独立于被修复sm25三条笔画；反例仍显式构造 | 无需动 |
| `test_tarch_converter_p1_geometry.py::test_sm24_deterministic` | sm24几何基线、45度斜线、孤立直线、合成闭合房间 | 独立于被修复sm25三条笔画；反例仍显式构造 | 无需动 |
| `test_tarch_converter_p1_geometry.py::test_s1_wall_nonorthogonal_rejected` | sm24几何基线、45度斜线、孤立直线、合成闭合房间 | 独立于被修复sm25三条笔画；反例仍显式构造 | 无需动 |
| `test_tarch_converter_p1_geometry.py::test_s4_wall_free_end_dangle` | sm24几何基线、45度斜线、孤立直线、合成闭合房间 | 独立于被修复sm25三条笔画；反例仍显式构造 | 无需动 |
| `test_tarch_converter_p1_geometry.py::test_synthetic_green_one_window_closes` | sm24几何基线、45度斜线、孤立直线、合成闭合房间 | 独立于被修复sm25三条笔画；反例仍显式构造 | 无需动 |
| `test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all` | F153B/F157分原因集合与逐位环差 | F153B退休，F157原两个cavity不变 | 需重推；T1只改F153B钉及叙述 |
| `test_f156_ring_from_intersection.py::test_moving_one_converter_edge_by_one_millimetre_reddens` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_cavity_that_covers_two_zones_fails_loudly_instead_of_taking_one` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_endcap_admissibility_rule_has_teeth_on_a_one_unit_move` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_removing_the_endcap_rule_admits_the_ring_the_rule_refuses` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_every_edge_sits_on_a_measured_face_of_its_own_wall_band` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_letting_endcaps_become_edges_breaks_that_invariant` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_adjacent_support_lines_of_every_stored_ring_are_perpendicular` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_a_parallel_junction_is_a_named_loss_not_a_silent_ring` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_every_ring_turns_exactly_on_its_support_line_intersections` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_odd_interzone_thickness_is_declined_loudly_not_silently_truncated` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_f156_ring_from_intersection.py::test_chaining_span_end_points_breaks_the_corner_rule` | 从真实已闭合环选择support/endcap，主动移位/改厚度/改变连接规则 | 环仍非空，构造后有非空变化/具名loss的断言 | 无需动 |
| `test_boundary_condition_facts.py::test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches` | 按cause的deferred计数、配对边和未解释残差 | F153B归零；F157仍在，配对集合与计数未变 | 需重推；T1已完成 |
| `test_boundary_condition_facts.py::test_r4_clear_every_converter_judgment_readout_and_renamed_carrier_has_teeth` | 清除所有converter派生判断后的几何来源与伪carrier | 主动构造，不依赖原台账或非正交计数 | 无需动 |
| `test_o21d_exclusion_gap.py::test_deregistering_each_live_loss_clears_exactly_its_own_red` | producer-written ring losses实时读数 | A11已为0；明确允许空循环，非G-c新增缺口 | 无需动断言；T1仅更新过时叙述 |
| `test_o21d_exclusion_gap.py::test_reading_the_ledger_the_gate_consumes_is_the_ledger_the_facts_layer_stores` | producer-written ring losses实时读数 | A11已为0；明确允许空循环，非G-c新增缺口 | 无需动断言；T1仅更新过时叙述 |
| `test_o21d_exclusion_gap.py::test_honest_substrate_branch_reds_are_exactly_the_known_defect` | producer-written ring losses实时读数 | A11已为0；明确允许空循环，非G-c新增缺口 | 无需动断言；T1仅更新过时叙述 |
| `test_o21d_exclusion_gap.py::test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion` | 从真实已配对房间剥环并构造loss | 非空房间及合成loss仍在；保证fail-loud方向 | 无需动 |
| `test_o21d_exclusion_gap.py::test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion` | 从真实已配对房间剥环并构造loss | 非空房间及合成loss仍在；保证fail-loud方向 | 无需动 |
| `test_o21d_exclusion_gap.py::test_flooding_the_loss_ledger_is_fail_loud_per_loss` | 从真实已配对房间剥环并构造loss | 非空房间及合成loss仍在；保证fail-loud方向 | 无需动 |
| `test_b1_projection_bridge_fixtures.py::test_fixture1_remainder_one_unit_both_versions_cut_14` | 13AE/13AD定位墙，主动加入端点余数/删墙/删开口 | 墙id随坐标改变；helper以face handles定位且assert命中唯一，故存货仍在 | 无需动 |
| `test_b1_projection_bridge_fixtures.py::test_fixture1_red_before_tolerance_zero_is_a_loud_zero_face_layer` | 13AE/13AD定位墙，主动加入端点余数/删墙/删开口 | 墙id随坐标改变；helper以face handles定位且assert命中唯一，故存货仍在 | 无需动 |
| `test_b1_projection_bridge_fixtures.py::test_fixture2_two_unit_remainder_still_red` | 13AE/13AD定位墙，主动加入端点余数/删墙/删开口 | 墙id随坐标改变；helper以face handles定位且assert命中唯一，故存货仍在 | 无需动 |
| `test_b1_projection_bridge_fixtures.py::test_fixture4_dropped_opening_two_redundant_channels` | 13AE/13AD定位墙，主动加入端点余数/删墙/删开口 | 墙id随坐标改变；helper以face handles定位且assert命中唯一，故存货仍在 | 无需动 |
| `test_b1_projection_bridge_fixtures.py::test_fixture5_removed_wall_red_at_reconciliation_only` | 13AE/13AD定位墙，主动加入端点余数/删墙/删开口 | 墙id随坐标改变；helper以face handles定位且assert命中唯一，故存货仍在 | 无需动 |
| `test_b1_projection_bridge_fixtures.py::test_4b_counts_equalised_attack_red_only_on_2_and_3` | 13AE/13AD定位墙，主动加入端点余数/删墙/删开口 | 墙id随坐标改变；helper以face handles定位且assert命中唯一，故存货仍在 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_a_handle_absent_on_one_side_gets_no_candidate_action` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_a_single_field_translate` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_axis_swap_with_numeric_coincidence_is_not_reported_as_translate` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_layer_swap_reproduces_pre_fix_without_the_layer_comparison` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_layer_swap_with_numeric_coincidence_is_not_reported_as_translate` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_multi_field_change_is_flagged_not_guessed` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_detect_translate_candidates_refuses_a_handle_reused_across_views` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_a_const_translate_desyncs_face_lo_is_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_b_same_shape_different_face_line_is_also_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_c_same_shape_different_field_along_min_is_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_d_same_shape_different_field_along_max_is_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_e_same_shape_negative_delta_is_also_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_f_zero_revisions_does_not_misfire` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f137_g_split_const_group_is_not_a_false_positive` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f140_a_group_centre_line_crossing_the_boundary_is_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f140_b_a_split_const_line_crosses_at_a_different_delta_than_the_centre_line` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f140_the_grouping_constant_tracks_the_live_module_attribute` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f142_a_translate_that_fully_closes_the_split_drops_the_entry` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_f142_an_in_group_translate_refreshes_the_split_const_registry` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_gate_a_hand_tampered_integer_in_as_signed_is_caught` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_gate_canonical_bytes_is_a_pure_function_of_the_document` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_gate_editing_a_revisions_action_moves_as_signed_and_its_hash` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_gate_reproduces_on_an_unmutated_trio` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_index_face_lines_pre_fix_shape_would_have_silently_shadowed_plan_f1` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_a_signed_drawing_error_revision_is_well_formed` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_as_designed_and_producer_defect_never_carry_an_action` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_candidate_action_is_visible_while_unsigned` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_drawing_error_requires_an_action` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_ledger_ids_must_be_unique` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_signed_verdict_requires_a_signature` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_translate_delta_zero_is_rejected` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_unsigned_cannot_carry_an_authoritative_action` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_unsupported_action_kind_is_rejected_and_named` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r1_verdict_null_is_rejected_by_the_type_itself` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r2_a_translate_that_breaks_along_min_max_fails_loudly` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r2_an_unsigned_record_cannot_influence_as_signed` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r2_as_designed_and_producer_defect_never_touch_geometry` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r2_ledger_bound_to_a_different_as_measured_is_refused` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r2_translate_moves_exactly_the_named_field` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |
| `test_gt_revisions_and_as_signed.py::test_r2_translate_target_not_found_is_refused_loudly` | _minimal_doc及_signed_revision等合成schema/action/候选 | 每条自行建记录/变异，不依赖sm25真实rev台账 | 无需动 |

排除对账（按命中语义，不是按是否变红排除）：

| 检索命中 | 存货与排除理由 |
|---|---|
| test_affected_tests_map::test_since_uses_committed_range_only | rev-parse是git命令，与revisions台账无关。 |
| test_deterministic_core::test_window_uses_fine_grid_not_structural | 10 mm是窗离散网格，不是已作废吸附偏移上限。 |
| test_f133_same_floor_step两条10mm测试 | 真实墙轴台阶的分组/记录样本，走校正核心；不是tarch吸附10mm门，均在194条定向跑内通过。 |
| test_j2_resolutions、test_elevation_grade、test_b3_elevation_leg | 10 mm指立面产品分辨率或mm/px，测量对象不同。 |
| B1 production_loader/acceptance其余墙计数 | 真实wall或显式smix样本，按数据声明的厚度、端点和owner构造；上述face-handle桥接仍有效。 |
| c2/b4、reading_typed、o22、gt_render/gt_from_dxf、j_grade等AST墙/面计数命中 | 读图/校正/证据适配器的typed构造夹具或冻结run产物，不以此次as-received三条笔画的拒绝作为负样本。其宽泛“wall”计数保留原口径，由最终全量检查。 |

可能遗漏的类别：动态拼出的字段名、通过多层helper/插件间接读取库存且源码不含上述词的断言，以及不在tests收集范围的离线科研脚本。本文没有声称把这些也穷尽。计数相同但实际对象替换，是计数锁的固有盲区；本次对F157核了两个cavity id，对身份锁改用含重复次数的实体身份，对扫描锁核了路径/值多重集合。没有用全量绿替代上述外延说明。
