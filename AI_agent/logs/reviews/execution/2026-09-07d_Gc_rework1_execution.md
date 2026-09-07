# G-c 返工1交件 · GPT-6 Astra 施工

工程档。施工提交 HEAD `f0437dbaa089386027fd2d965d9a6671f9b090c1`，分支 `wt/09.07d_gc_rework`，工作目录 `/tmp/gc_rework_astra`。
复核仍由用户指定的 GLM 跨家族席位负责；本件是施工交件。

T1–T4均已分段提交；另有一段自审补强房间完整性的提交。最初六条失败均已消除；T4枚举另发现并修复三处仍绿但缺少相应反例的测试。生产源码在本次返工中修改为零；没有删测试、加skip/xfail或变更参数化。最终全量 **4009 passed / 0 failed / 2 skipped / 13 xfailed**。

## 自检与纪律

首次开工：
```sh
$ git log --oneline -1
f2188df5 09.07_Gc_locks_staging: 台账清零后，四条靠「台账里有记录」立着的锁改用自造存货
$ python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"
/tmp/gc_rework_astra/src/agent/judge/tarch_normalize.py
```
接续开工：
```sh
$ git log --oneline -1
fd5c3388 09.07_Gc_locks_staging: 台账清零后，四条靠「台账里有记录」立着的锁改用自造存货
$ git status --short
$ python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"
/tmp/gc_rework_astra/src/agent/judge/tarch_normalize.py
```
完整读取主树绝对路径下派工单（含勘误）、原派工单、两份中断状态档及拆钉GLM裁决。未执行安装、site-packages写入、git config、reset、force push、hook跳过或git add -A。每次只add明确路径，提交前查看cached numstat。主树只写本交件；未访问另一个施工席位的工作树。

## T0 · 已完成的rebase及补齐基线

首次调用及原始结果：
```sh
$ git rebase fde2f24c
Rebasing (1/8)
Rebasing (2/8)
Rebasing (3/8)
Rebasing (4/8)
Rebasing (5/8)
Rebasing (6/8)
Rebasing (7/8)
Rebasing (8/8)
Successfully rebased and updated refs/heads/wt/09.07d_gc_rework.
```
这一步在额度中断前已完成；接续后没有重做rebase。首次T0全量确实启动，但留存日志停在96%后，没有汇总行，不能把它冒充完成读数。接续消息明确主控重跑五文件得到同样六条失败。本席随后补做了全量快照回放：生产源码与fd5c3388逐字节无差异，只临时恢复本工作树中已改测试的fd5c3388版本，备份后用finally恢复所有施工版本。不是重新rebase，也没有修改主树代码。


```sh
$ python /tmp/gc_rework1_evidence/replay_baseline.py
BASELINE TEST SNAPSHOT fd5c3388; production delta 0; restored files: ['tests/deferred_projection_ledger.py', 'tests/test_a11_gt_1mm_ingest_resolution.py', 'tests/test_answer_compiler_profiles.py', 'tests/test_as_drawn_denominator_f126.py', 'tests/test_as_measured_facts_layer.py', 'tests/test_boundary_condition_facts.py', 'tests/test_f156_ring_from_intersection.py', 'tests/test_o21d_exclusion_gap.py']
/tmp/gc_rework_astra/src/agent/judge/tarch_normalize.py
bringing up nodes...
bringing up nodes...

........................................................................ [  1%]
........................................................................ [  3%]
........................................................................ [  5%]
........................................................................ [  7%]
...............................F........................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
........................................................................ [ 17%]
........................................................................ [ 19%]
..................................................F..................... [ 21%]
........................................................................ [ 23%]
.......F................................................................ [ 25%]
........................................................................ [ 26%]
........................................................................ [ 28%]
........................................................................ [ 30%]
......................................................F................. [ 32%]
........................................................................ [ 33%]
........................................................................ [ 35%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 41%]
........................................................................ [ 42%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 48%]
........................................................................ [ 50%]
........................................................................ [ 51%]
........................................................................ [ 53%]
........................................................................ [ 55%]
........................................................................ [ 57%]
........................................................................ [ 59%]
........................................................................ [ 60%]
..........................................................s............. [ 62%]
........................................................................ [ 64%]
........................................................................ [ 66%]
........................................................................ [ 67%]
......x................................................................. [ 69%]
........................................................................ [ 71%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 76%]
........................................................................ [ 78%]
........................................................................ [ 80%]
........................................................................ [ 82%]
........................................................................ [ 84%]
........................xx................x............................. [ 85%]
.....................................F.................................. [ 87%]
........................................................................ [ 89%]
...............F..................x..................................... [ 91%]
........................................................................ [ 93%]
......................................................................xx [ 94%]
x...........x..x...x....x.....x......................................... [ 96%]
...............................s........................................ [ 98%]
................................................................         [100%]
=================================== FAILURES ===================================
_________ test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches _________
[gw3] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches():
        """F-156 narrows this: every paired row still agrees, and every converter
        zone is still accounted for, but the audit as a whole no longer passes.
    
        The two corridor cavities now HAVE rings, so they are compared instead of
        excluded -- and the comparison reports the answer-side
        ``outer_skin``<->``wall_axis`` basis switch that F-157 owns.  ⛔ That is not
        tolerated silently: it is named, with the residual in units².  ⛔ ⭐ What
        this batch does require is the zero-threshold half: NO cavity that is
        genuinely the same room as its zone may show ANY residual.
        """
        _measured, _ledger, signed, _request, report = _real_inputs()
        audit = reconcile_boundary_basis(signed, report)
        assert audit.paired_edges == 108
        assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 29)
        assert audit.mismatches == []
        # ⭐⭐⭐ Zero threshold: every cavity that is NOT reported as a
        # projected-ring difference has a residual of exactly nothing -- there is no
        # "small enough" band anywhere in this assertion.
        # A-11 (1 mm ingest snap): 100 -> 108 paired edges and 2 -> 4 deferred
        # cavities.  The snap closes the old 286.8 m2 endcap-loss cavity into two
        # REAL rooms, whose projected rings then surface the F-153 form B endcap
        # geometry difference for the first time (named ``..._is_not_the_
        # converter_zone`` rows, symdiff 1182000 units2 -- a real geometric
        # difference, ⛔ not representation noise: the reconciliation now compares
        # BOTH sides on the same 1 mm grid, so a 0.1 mm band can no longer hide
        # here).  Plus the two pre-existing ``..._unavailable`` parallel cavities
        # F-157 already owed.
        deferred = _deferred_cavities(audit)
>       assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT
E       AssertionError: assert 2 == 4
E        +  where 2 = len({('plan-F1', 'cavity:8bd127719198fd63'), ('plan-F2', 'cavity:495501ce9b36f0f3')})

tests/test_boundary_condition_facts.py:150: AssertionError
_______________ test_the_scan_goes_red_when_the_snap_is_removed ________________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

plain_as_received = AsMeasuredV1(schema_version=1, case='sm25-L_anchor', source_dxf_label='sm25-L_t3_as_received.dxf', source_dxf_sha256='...ning dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': True}]))])

    def test_the_scan_goes_red_when_the_snap_is_removed(plain_as_received):
        """Shut the one door (the plain fixture already did) and the exit scan
        MUST report -- pinned to the dispatch's own measured baseline."""
        violations = scan_ingest_resolution_violations(
            plain_as_received.model_dump(mode="json"))
        assert violations, "a criterion that cannot go red is not a criterion"
        buckets = Counter(_bucket_of(v.rsplit(" = ", 1)[0]) for v in violations)
        for bucket, expected in BUCKETS.items():
>           assert buckets[bucket] == expected, \
                f"{bucket}: {buckets[bucket]} != dispatch baseline {expected}"
E           AssertionError: face_lines: 48 != dispatch baseline 46
E           assert 48 == 46

tests/test_a11_gt_1mm_ingest_resolution.py:220: AssertionError
__________________ test_external_quantities_are_bit_identical __________________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

snapped_as_received = AsMeasuredV1(schema_version=1, case='sm25-L_anchor', source_dxf_label='sm25-L_t3_as_received.dxf', source_dxf_sha256='...ning dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': True}]))])
plain_as_received = AsMeasuredV1(schema_version=1, case='sm25-L_anchor', source_dxf_label='sm25-L_t3_as_received.dxf', source_dxf_sha256='...ning dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': True}]))])

    def test_external_quantities_are_bit_identical(snapped_as_received,
                                                   plain_as_received):
        """Everything the snap does NOT own, compared bit-for-bit between the
        plain and snapped builds of the same drawing:
    
          * the converter's VERBATIM subtrees (diagnostics / gates /
            jamb_cap_bands) -- including their deepest ``context`` integers;
          * every converter readout count;
          * the RAW pre-snap observations (``before_p0`` / ``before_p1``) and
            the length observation ``minor_leg_units``;
          * identity strings (handles, layers, axes, view ids).
    
        ⚠️ The boundary-derived subtrees (``boundary_edges`` /
        ``boundary_ring_losses``) are excluded from this bit-identity lock on
        purpose: they are FUNCTIONS of the coordinates (on this fixture the snap
        legitimately turns one lost cavity into a closed ring -- edges 83 -> 91,
        losses 1 -> 0 -- so their enumerations and witness values move with the
        geometry).  Their COORDINATES are still exit-scanned as hard as
        everything else; this test is about inputs the snap must not touch, and
        those live outside the boundary subtrees."""
        snapped = snapped_as_received.model_dump(mode="json")
        plain = plain_as_received.model_dump(mode="json")
    
        def external_leaves(payload) -> Counter:
            return Counter(
                (".".join(path), value)
                for path, value in _iter_int_leaves(payload)
                if any(_path_matches(path, pattern)
                       for pattern in INGEST_NON_COORDINATE_PATHS)
                and "boundary_edges" not in path
                and "boundary_ring_losses" not in path)
    
        assert external_leaves(snapped) == external_leaves(plain), \
            "an exempt quantity outside the boundary derivation moved"
    
        for snapped_view, plain_view in zip(snapped["views"], plain["views"]):
>           assert [(f["id"], f["layer"], f["axis"])
                    for f in snapped_view["face_lines"]] == \
                   [(f["id"], f["layer"], f["axis"])
                    for f in plain_view["face_lines"]], "identity strings moved"
E           AssertionError: identity strings moved
E           assert [('1379', 'WA...L', 'x'), ...] == [('1379', 'WA...L', 'x'), ...]
E             
E             At index 45 diff: ('13AE', 'WALL', 'x') != ('1414', 'WALL', 'x')
E             Use -v to get more diff

tests/test_a11_gt_1mm_ingest_resolution.py:295: AssertionError
_________ test_projected_ring_identity_holds_with_no_tolerance_at_all __________
[gw3] linux -- Python 3.12.13 /opt/venv/bin/python

facts = AsSignedV1(schema_version=1, case='sm25-L_anchor', source_dxf_label='sm25-L_t3_as_received.dxf', source_dxf_sha256='4a...ning dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': True}]))])
report = ConversionReportV1(report_version=1, status='PASS', case='sm25-L_anchor', source_dxf_sha256='1251f65153829c9c4502e401b...e_handles': ['1609'], 'structural_source_handles': ['316', '317', '319', '31B']}], review_bundle_inventory_sha256=None)

    def test_projected_ring_identity_holds_with_no_tolerance_at_all(facts, report):
        """Every cavity that reaches the per-edge comparison lands on its zone
        EXACTLY.  ⛔ Read the assertion: it is "residual of exactly nothing for
        everyone outside the ONE declared ledger", not ``< something``.  The
        clear-span ring and the zone are on different bases and differ by 1.0-3.5
        m² before projection, so a threshold here could only have been read off
        the data it is judging.
    
        A-11 (1 mm ingest snap) moved BOTH sides of the comparison onto the same
        1 mm grid: the old 286.8 m² endcap-loss cavity closed into two real rooms
        (pairings 25 -> 27, paired edges 100 -> 108), whose rings surface the
        F-153 form B endcap difference for the first time.  Those two cavities —
        and only those, plus F-157's two — sit in the ONE deferred ledger declared
        in ``tests/deferred_projection_ledger.py``.  The count is pinned:
        one MORE unexplained projected-ring failure reddens here, so this is not
        an amnesty and not a threshold."""
        audit = reconcile_boundary_basis(facts, report)
        deferred = deferred_cavities(audit)
>       assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT  # 2 F-157 + 2 F-153 form B
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AssertionError: assert 2 == 4
E        +  where 2 = len({('plan-F1', 'cavity:8bd127719198fd63'), ('plan-F2', 'cavity:495501ce9b36f0f3')})

tests/test_f156_ring_from_intersection.py:112: AssertionError
_ test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na _
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na():
        _measured, ledger, signed = read_facts_for_compilation("sm25-L_anchor")
        request = TarchConversionRequestV1.model_validate_json(
            (SM25_SOURCE / "request_as_measured.json").read_text())
        answer = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
            signed, ledger, request)
>       assert {record.component_id for record in answer.unresolved_revisions} >= {
            "rev-13ad", "rev-13ae", "rev-13af"}
E       AssertionError: assert set() >= {'rev-13ad', ...', 'rev-13af'}
E         
E         Extra items in the right set:
E         'rev-13ad'
E         'rev-13af'
E         'rev-13ae'

tests/test_answer_compiler_profiles.py:62: AssertionError
____________ test_l4_discarded_non_orthogonal_segments_are_itemised ____________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

anchor_present = None
tmp_path = PosixPath('/tmp/pytest-of-root/pytest-21086/popen-gw0/test_l4_discarded_non_orthogon0')

    def test_l4_discarded_non_orthogonal_segments_are_itemised(anchor_present, tmp_path):
        """⛔ The fixture must HOLD the inventory, or the lock has no teeth.
    
        Signed drawing: ``excluded_non_orthogonal == 0`` (measured) -- against it,
        ``len(items) == count`` is ``0 == 0`` and passes on code that never builds
        the list.  So this uses the re-signed as-received drawing, measured to carry
        exactly one discarded stroke, and asserts NON-EMPTINESS first.
    
        ⭐ F-C (F-126 cross-review, 2026-08-29): this test is ALSO the pin -- until
        now unlabelled -- on the POLICY that ``denominator()`` RETURNS when BLOCK
        diagnostics ride alongside a NON-empty denominator.  ⚠️ ②-1b-S UPDATE
        (2026-08-29): it used to feed the fixture measured to produce 108 targets
        together with ``tarch_wall_nonorthogonal`` x2 + ``tarch_wall_free_end`` x1
        (all BLOCK) -- dispatch ②-1b-S R1 changed the S1 non-orthogonal action
        from unconditional drop to "snap the short leg to zero when within the
        (⛔⛔ placeholder, pending sign-off) admission threshold", and this
        fixture's two ``tarch_wall_nonorthogonal`` strokes (13AD/13AE, minor leg
        ~5.81 mm) are now admitted via snap -- ``geo.wall_lines`` no longer omits
        them and the S1-level ``tarch_wall_nonorthogonal`` BLOCK no longer fires
        for this fixture at all.  Only ``tarch_wall_free_end`` (a S4/G5 BLOCK,
        unrelated mechanism, unaffected by R1) remains.  The POLICY this test pins
        (BLOCK-alongside-non-empty-denominator still returns normally) still
        applies -- it is exercised on one fewer BLOCK code now, not on zero.
        Read literally, "any BLOCK => fail loudly" (the F-126 dispatch's R2) would
        make THIS fixture raise and this test go red -- deliberately: the scope
        note in ``denominator.py`` owns the distinction (F-126 fixed the silence,
        not the policy), and changing the policy should have to come through
        here, in the open.
    
        ⭐ F-B (same review): the BLOCK codes must SURVIVE the success path.  A
        "successful run doesn't need its BLOCK diagnostics" trim (keep INFO only)
        passes every other lock in this file: L3's success-path assertions run on
        the SIGNED drawing, whose diagnostics are all INFO, so filtering them
        changes nothing there.  Only this fixture holds BLOCK-on-success inventory.
        """
        request_path = _resigned_request(tmp_path, AS_RECEIVED_DXF)
        result = denominator(AS_RECEIVED_DXF, request_path, "plan-F1")
    
        # ⭐ F-B: the (now single) BLOCK code measured on this fixture still rides
        # out in ``diagnostics`` -- exactly this set, so a trim to INFO-only, a
        # rename, or a swallowed code all fail here.
>       assert {d["code"] for d in result["diagnostics"] if d["severity"] == "BLOCK"} == {
            "tarch_wall_free_end"}
E       AssertionError: assert set() == {'tarch_wall_free_end'}
E         
E         Extra items in the right set:
E         'tarch_wall_free_end'
E         Use -v to get more diff

tests/test_as_drawn_denominator_f126.py:260: AssertionError
=============================== warnings summary ===============================
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D2_missing_facade_renders_explicit_placeholder_not_omission
tests/test_batch_d_typed_grade.py::test_L_D2_missing_facade_renders_explicit_placeholder_not_omission
  /tmp/gc_rework_astra/tests/test_batch_d_typed_grade.py:44: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    for px in region.getdata():

tests/test_batch_d_typed_grade.py: 18 warnings
  /tmp/gc_rework_astra/tests/test_batch_d_typed_grade.py:53: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    for px in region.getdata():

tests/test_batch_d_typed_grade.py::test_L_D1_does_not_read_product_mirror_or_local_x_declarations
tests/test_batch_d_typed_grade.py::test_L_D1_does_not_read_product_mirror_or_local_x_declarations
  /tmp/gc_rework_astra/tests/test_batch_d_typed_grade.py:161: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    assert list(image_a.getdata()) == list(image_b.getdata())

tests/test_c2_b2_v3.py::test_f3_tampered_v3_and_feature_state_fail_closed
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `Floor` - serialized value may not be as expected [field_name='floors', input_value={'id': 'f1'}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_f9_route2_s2_authoritative_projector.py::test_real_integrated_entry_clean_run_shows_pass
  /tmp/gc_rework_astra/src/agent/pipeline.py:2546: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw1/test_real_integrated_entry_cle0/run_x; using flow defaults
    run_cfg = load_run_config(run_config_dir)

tests/test_f9_route2_s2_authoritative_projector.py::test_real_integrated_entry_neuter_projector_flips_to_fail
  /tmp/gc_rework_astra/src/agent/pipeline.py:2546: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw1/test_real_integrated_entry_neu0/run_x; using flow defaults
    run_cfg = load_run_config(run_config_dir)

tests/test_gt_from_dxf.py: 10 warnings
tests/test_gt_overlay.py: 6 warnings
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_from_dxf.py::test_plan_only_z_and_u_hidden_depth_are_preserved
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_from_dxf.py::test_elevation_multi_view_z_disagreement_fails_closed
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_overlay_affine_hash_watermark_and_atomic_output
tests/test_gt_overlay.py::test_v3_overlay_rejects_raster_hash_mismatch_and_sanitized_collision
tests/test_gt_overlay.py::test_v3_overlay_rejects_document_manifest_binding_mismatch
tests/test_gt_overlay.py::test_v3_elevation_overlay_uses_declared_floor_z_and_affine
tests/test_gt_overlay.py::test_v3_overlay_rejects_competing_binding_empty_view_id_and_singular_affine
tests/test_gt_overlay.py::test_v3_review_annotations_are_review_only_and_never_guess
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster', 'so...'m11': 0.1, 'm12': 0.0}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_elevation_overlay_uses_declared_floor_z_and_affine
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster', 'so...space': 'source_metre'}}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'elev-raster', 'so...'m11': 0.1, 'm12': 0.0}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_overlay_rejects_competing_binding_empty_view_id_and_singular_affine
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster', 'so...space': 'source_metre'}}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster-2', '...space': 'source_metre'}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_plan_opening_bars_sit_on_wall_band_real_sm24
tests/test_gt_overlay.py::test_v3_plan_opening_bar_keeps_outer_skin_position_when_wall_thickness_is_none
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': '1F'...'ceiling_height_m': 4.5}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': 0.24}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': 0.24}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'raster_plan_F1', ...space': 'source_metre'}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_uses0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_uses0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py: 13 warnings
tests/test_provenance_baseline.py: 2 warnings
tests/test_reading_mode.py: 1 warning
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'conclusion'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py: 14 warnings
tests/test_provenance_baseline.py: 2 warnings
tests/test_reading_mode.py: 1 warning
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'focus'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py: 13 warnings
tests/test_provenance_baseline.py: 2 warnings
tests/test_reading_mode.py: 1 warning
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'diagnosis'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py: 13 warnings
tests/test_provenance_baseline.py: 2 warnings
tests/test_reading_mode.py: 1 warning
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'recommendations'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_regression_tier_surfaces_blocking_check_row
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_regr0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_regression_tier_surfaces_blocking_check_row
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_regr0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_marker_me0/sm21_anchor/run_2026-06-20_gpt54_reading; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_marker_me0/sm21_anchor/run_2026-06-20_gpt54_reading/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_marks_unfrozen_run_legacy
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_mark0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_marks_unfrozen_run_legacy
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_mark0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_context_tamper_does_not_change_blocking
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_cont0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_context_tamper_does_not_change_blocking
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_R1_5_record_baseline_cont0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_missing_a0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_missing_a0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_duplicate0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_duplicate0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_on_anchor
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_on_anchor0/sm20_anchor/run_2026-06-15_baseline; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_on_anchor
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_on_anchor0/sm20_anchor/run_2026-06-15_baseline/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'F1'...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_nested_ag0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_nested_ag0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_provenance_baseline.py::test_record_baseline_writes_provenance_and_report_summary
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw4/test_record_baseline_writes_pr0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_provenance_baseline.py::test_record_baseline_writes_provenance_and_report_summary
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw4/test_record_baseline_writes_pr0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_provenance_baseline.py::test_record_baseline_git_failure_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw4/test_record_baseline_git_failu0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_provenance_baseline.py::test_record_baseline_git_failure_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw4/test_record_baseline_git_failu0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_report_lists_eyeball_items
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_report_li0/sm21_anchor/run_2026-06-20_gpt54_reading; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_report_lists_eyeball_items
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_report_li0/sm21_anchor/run_2026-06-20_gpt54_reading/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_agent_marker_like_text_in0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw3/test_agent_marker_like_text_in0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_stale_rec0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw3/test_record_baseline_stale_rec0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_state_aware_report_suppresses_dead_viewer
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_state_awa0/sm21_anchor/run_2026-06-20_sonnet_reading; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_state_aware_report_suppresses_dead_viewer
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_state_awa0/sm21_anchor/run_2026-06-20_sonnet_reading/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_missing_corrections_sidecar_does_not_change_gates
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_missing_c0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_missing_corrections_sidecar_does_not_change_gates
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_missing_c0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_correctio0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_correctio0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_malformed_corrections_sidecar_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_malformed0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_malformed_corrections_sidecar_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21086/popen-gw2/test_record_baseline_malformed0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_run_stage_flow.py::test_cmd_run_judge_off_still_writes_correction_renders
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_cmd_run_judge_off_still_w0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_resample_invalidates_downstream_before_force_run
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2756: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_cmd_resample_invalidates_0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_human_review_checkpoint_and_approve_resume
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_human_review_checkpo0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_human_review_checkpoint_and_approve_resume
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2756: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_human_review_checkpo0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_human_review_checkpoint_and_approve_resume
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_human_review_checkpo0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_first_pass_packet_has_gt_evidence_before_manifest_save
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_first_pass_packet_ha0/sm21_anchor/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_judge_block_auto_invalidates_and_force_resamples
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_judge_block_auto_inv0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_terminal_stop_returns_20
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_terminal_stop_return0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_geometry_auto_records_auto_policy
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_flow_geometry_auto_record0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_run_refuses_persisted_v1_run
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_cmd_run_refuses_persisted0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_flow_refuses_persisted_v1_run
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_cmd_flow_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_resample_refuses_persisted_v1_before_any_write
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2756: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_cmd_resample_refuses_pers0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_new_run_flow_smoke_produces_v2_base_v2_records
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_new_run_flow_smoke_produc0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_v1_run_resumable_after_explicit_migration
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21086/popen-gw3/test_v1_run_resumable_after_ex0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_render_grade.py: 16 warnings
  /tmp/gc_rework_astra/tests/test_render_grade.py:238: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    return sum(1 for px in view.getdata() if px == color)

tests/test_render_grade.py::test_render_grade_draws_no_data_for_missing_score_floor
tests/test_render_grade.py::test_render_grade_missing_facade_key_is_no_data
  /tmp/gc_rework_astra/tests/test_render_grade.py:243: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    return sum(1 for px in view.getdata() if all(abs(int(px[i]) - color[i]) <= tol for i in range(3)))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
=========================== short test summary info ============================
FAILED tests/test_boundary_condition_facts.py::test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches
FAILED tests/test_a11_gt_1mm_ingest_resolution.py::test_the_scan_goes_red_when_the_snap_is_removed
FAILED tests/test_a11_gt_1mm_ingest_resolution.py::test_external_quantities_are_bit_identical
FAILED tests/test_f156_ring_from_intersection.py::test_projected_ring_identity_holds_with_no_tolerance_at_all
FAILED tests/test_answer_compiler_profiles.py::test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na
FAILED tests/test_as_drawn_denominator_f126.py::test_l4_discarded_non_orthogonal_segments_are_itemised
6 failed, 4003 passed, 2 skipped, 13 xfailed, 211 warnings in 464.41s (0:07:44)
/tmp/gc_rework_astra/src/agent/judge/tarch_normalize.py
BASELINE pytest exit: 1
RESTORED committed test bytes: 8
STATUS
```


回放的失败集合逐条为派工单的三类六条：answer profiles / denominator L4 / external quantities 属A；scan baseline属C；projected-ring identity和real-sm25 boundary pairs属B。B仍先红在总数行2≠4；不是per-code断言直接指名，已遵循勘误后的归因路径。

## T1 · F-153 form B退休

`633bdc81`：F153分项钉2→0；派生总数表达式不动；F157分项钉不动。裁决正文写清阶梯由中点改为接头锚端，并传播共端点移动，接头闭合后投影环逐位重合。两个消费者的当前叙述同步。o21d只改过时叙述，未动断言；其producer-written loss库存在A11时已归零，空循环依约保留，反例仍由构造loss的测试提供。

归因命令：
```sh
python - <<'PYCODE'
from tests.test_boundary_condition_facts import _real_inputs
from src.agent.judge.answer_compiler import reconcile_boundary_basis
from tests.deferred_projection_ledger import F153_FORM_B_CODE,F157_UNAVAILABLE_CODE,deferred_cavities_by_code
_,_,signed,_,report=_real_inputs()
a=reconcile_boundary_basis(signed,report)
for c in (F153_FORM_B_CODE,F157_UNAVAILABLE_CODE):
    print(c,sorted(deferred_cavities_by_code(a,c)))
print('paired zones',len(a.pairings),'paired edges',a.paired_edges,'mismatches',a.mismatches)
print('boundary_ring_losses',sum(len(v.boundary_ring_losses) for v in signed.views))
PYCODE
```
原始输出（不含后续查看schema的额外pairing对象打印）：


```sh
$ 上述归因命令
facts_projected_ring_is_not_the_converter_zone []
facts_projected_ring_unavailable [('plan-F1', 'cavity:8bd127719198fd63'), ('plan-F2', 'cavity:495501ce9b36f0f3')]
paired zones 27 paired edges 108 mismatches []
boundary_ring_losses 0
```


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider tests/test_f156_ring_from_intersection.py tests/test_boundary_condition_facts.py tests/test_o21d_exclusion_gap.py
bringing up nodes...
bringing up nodes...

...........................................                              [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
43 passed in 4.06s
```


## T2 · 三条反例重建

`035fc237`：

1. **answer profiles**：真实台账为零，测试在真实13AD/13AE/13AF上构造unsigned候选，并通过真实derive/compile。正确输出必须列出三条NA记录，仅使clean answer中依赖这些faces的房间失效，并保留所有无关房间的完整payload。真实clean输出为13+14个projectable房间，构造后为9+14；不能沿用旧25这一库存数。每个projectable房间仍逐顶点对照签字GT。自审补强后，所有房间身份与数量来自request，projectable集合来自独立边界审计的pairings；避免将“剩下的都正确”当作完整。
2. **denominator L4**：临时DXF加入偏移0.6q、端点分别在0.2q/0.8q的孤立笔画。档0不旋转，但q量化跨格后仍是非正交笔画，进入D1列明路径，同时产生free-end BLOCK与G5=False。真正45度斜线在S1已drop，不能拿来代替这个D1反例。保留非空target、精确BLOCK code集合、handle、列表/计数、两坐标框架及长度关系，并对丢列表/丢BLOCK/坏长度/错handle逐一实测。
3. **external quantities**：实测F1列表位置改变4处，F2改变0处，两个视图的(id,layer,axis)多重集合均相同。故不是身份串改变，而是坐标排序改变。用(view,id,layer,axis)多重集合比较，保留重复次数；外部整数叶比较未删除。增加改id/改layer/改axis/丢行/重复行/改view六种反例，以及仅重排的绿对照。

“不加改动，本来红不红”：原真实夹具在T0里三条都红，但库存已不再表达各自原来的负向行为。重建后正确代码可再次对unsigned、漏列明和身份损坏给出真实红；下列三条临时测试不捕获异常，明确排除“只写它会红”。临时测试文件未进入正式收集，正式测试保留raises等反例断言。


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider tests/test_answer_compiler_profiles.py tests/test_as_drawn_denominator_f126.py tests/test_a11_gt_1mm_ingest_resolution.py -k 'not test_the_scan_goes_red_when_the_snap_is_removed'
bringing up nodes...
bringing up nodes...

..........................                                               [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
26 passed in 5.99s
```


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider /tmp/gc_rework1_evidence/test_T2_red.py
bringing up nodes...
bringing up nodes...

FFF                                                                      [100%]
=================================== FAILURES ===================================
_________________________ test_unsigned_sample_is_red __________________________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_unsigned_sample_is_red():
        measured, ledger, _ = read_facts_for_compilation('sm25-L_anchor')
        candidate = ledger.model_copy(update={'revisions': [
            _synthetic_unsigned_record(measured, handle=h) for h in ('13AD', '13AE', '13AF')]})
        request = TarchConversionRequestV1.model_validate_json((SM25_SOURCE / 'request_as_measured.json').read_text())
        answer = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
            derive_as_signed(measured, candidate), candidate, request)
>       _assert_no_unsigned_geometry(answer)

../gc_rework1_evidence/test_T2_red.py:18: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

answer = CompiledAnswerV1(case='sm25-L_anchor', profile='form_b_exterior_skin', compiler_version=2, dependency_closure_version=..._zones': 15, 'measured_cavities': 15, 'projected_zones': 14, 'na_zones': 1, 'openings': 30, 'na_openings': 0}, na=[])])

    def _assert_no_unsigned_geometry(answer):
>       assert answer.unresolved_revisions == [], "unsigned revisions remain"
E       AssertionError: unsigned revisions remain
E       assert [NaRecordV1(r...rom=['13AF'])] == []
E         
E         Left contains 3 more items, first extra item: NaRecordV1(rule='unsigned_revision', component_kind='revision', component_id='rev-13ad', reason_code='revision_has_no_signed_verdict', affected_metrics=['zone_geometry', 'reading_face_lines'], propagated_from=['13AD'])
E         Use -v to get more diff

tests/test_answer_compiler_profiles.py:113: AssertionError
_______________________ test_missing_itemisation_is_red ________________________
[gw1] linux -- Python 3.12.13 /opt/venv/bin/python

tmp_path = PosixPath('/tmp/pytest-of-root/pytest-21054/popen-gw1/test_missing_itemisation_is_re0')

    def test_missing_itemisation_is_red(tmp_path):
        dxf, request, handle = _l4_nonorthogonal_fixture(tmp_path)
        result = denominator(dxf, request, 'plan-F1')
        _assert_l4_itemisation(result, request, handle)
        assert next(g for g in result['gates'] if g['id'] == 'G5')['passed'] is False
        damaged = deepcopy(result)
        damaged['excluded_non_orthogonal_segments'] = []
>       _assert_l4_itemisation(damaged, request, handle)

../gc_rework1_evidence/test_T2_red.py:28: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

result = {'allowed_not_required': [{'axis': 'y', 'const_m': 12.1599, 'handle': '1370', 'hi_m': 5.24, ...}, {'axis': 'y', 'const..., 44333.600000000006]}, 'handles': ['151D'], ...}, ...], 'excluded_non_orthogonal_segments': [], 'floor_id': 'F1', ...}
request_path = PosixPath('/tmp/pytest-of-root/pytest-21054/popen-gw1/test_missing_itemisation_is_re0/resigned_request.json')
handle = '194E'

    def _assert_l4_itemisation(result, request_path, handle):
        assert result["targets"], "BLOCK must ride alongside a nonempty denominator"
        assert {d["code"] for d in result["diagnostics"] if d["severity"] == "BLOCK"} == {
            "tarch_wall_free_end"}
>       assert {item["handle"] for item in result["excluded_non_orthogonal_segments"]} == {handle}
E       AssertionError: assert set() == {'194E'}
E         
E         Extra items in the right set:
E         '194E'
E         Use -v to get more diff

tests/test_as_drawn_denominator_f126.py:265: AssertionError
_________________________ test_changed_identity_is_red _________________________
[gw2] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_changed_identity_is_red():
        snapped = snapped_as_received.__wrapped__().model_dump(mode='json')
        plain = plain_as_received.__wrapped__().model_dump(mode='json')
        _assert_external_quantities_identical(snapped, plain)
        snapped['views'][0]['face_lines'][0]['id'] = 'DEADFACE'
>       _assert_external_quantities_identical(snapped, plain)

../gc_rework1_evidence/test_T2_red.py:36: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

snapped = {'case': 'sm25-L_anchor', 'converter_implementation_fingerprint': '69a9915fae9aeeb2675fe3b2def610a98fe75c75ea44eb7b335... 'coordinate_unit': '0.1mm', 'request_sha256': 'ae272a73f6331e3ac5787019053b3c973da04fcc53ba9bbe42aa10597be26c5a', ...}
plain = {'case': 'sm25-L_anchor', 'converter_implementation_fingerprint': '69a9915fae9aeeb2675fe3b2def610a98fe75c75ea44eb7b335... 'coordinate_unit': '0.1mm', 'request_sha256': 'ae272a73f6331e3ac5787019053b3c973da04fcc53ba9bbe42aa10597be26c5a', ...}

    def _assert_external_quantities_identical(snapped, plain):
        """Compare identities by view/handle, retaining multiplicity, not position.
    
        G-c changes coordinates, and therefore the face sort order, in the two
        builds.  The identity tuple itself does not change.  Counter equality
        rejects dropped/duplicated faces as well as changed handle/layer/axis/view.
        """
        def identities(payload):
            return (Counter(view["view_id"] for view in payload["views"]),
                    Counter((view["view_id"], face["id"], face["layer"], face["axis"])
                            for view in payload["views"] for face in view["face_lines"]))
    
>       assert identities(snapped) == identities(plain), "identity strings moved"
E       AssertionError: identity strings moved
E       assert (Counter({'pl...L', 'y'): 1})) == (Counter({'pl...L', 'y'): 1}))
E         
E         At index 1 diff: Counter({('plan-F1', 'DEADFACE', 'WALL', 'x'): 1, ('plan-F1', '137E', 'WALL', 'x'): 1, ('plan-F1', '13BE', 'WALL', 'x'): 1, ('plan-F1', '13C3', 'WALL', 'x'): 1, ('plan-F1', '13BB', 'WALL', 'x'): 1, ('plan-F1', '137B', 'WALL', 'x'): 1, ('plan-F1', '137C', 'WALL', 'x'): 1, ('plan-F1', '13C0', 'WALL', 'x'): 1, ('plan-F1', '13C1', 'WALL', 'x'): 1, ('plan-F1', '13BA', 'WALL', 'x'): 1, ('plan-F1', '1380', 'WALL', 'x'): 1, ('plan-F1', '1383', 'WALL', 'x'): 1, ('plan-F1', '13C7', 'WALL', 'x'): 1, ('plan-F1', '13C6', 'WALL', 'x'): 1, ('plan-F1', '13B7', 'WALL', ...
E         
E         ...Full output truncated (2 lines hidden), use '-vv' to show

tests/test_a11_gt_1mm_ingest_resolution.py:323: AssertionError
=========================== short test summary info ============================
FAILED ../gc_rework1_evidence/test_T2_red.py::test_unsigned_sample_is_red - A...
FAILED ../gc_rework1_evidence/test_T2_red.py::test_missing_itemisation_is_red
FAILED ../gc_rework1_evidence/test_T2_red.py::test_changed_identity_is_red - ...
3 failed in 4.94s
```


## T3 · 坐标库存的独立推导

`b6664f22`：钉的是**当前图纸在当前阶梯下，关闭1 mm入库吸附后产生的非网格整数坐标出现次数**，不是历史派工单数字，也不是面线/墙条数。

可执行推导 `_unsnapped_coordinate_inventory` 显式遍历facts的几何字段，不调用扫描器、其整数walker或豁免matcher；扫描结果还要与推导的(path,value)多重集合完全相同，遗漏一个再重复计另一个不能相互抵消。

面线：F1为12个const、15个along_min、15个along_max；F2分别2/2/2，合计48。13AF的const=52400在网格上，跟随接头后的两个端点99401和100601各贡献一次。墙端点10、开口端点10。evidence为边界两种face const共4加split member_consts 4，合计8。derived为boundary端点/span 8、footprint-edge证据6、snap after端点6、footprint点8，合计28。因此48+10+10+8+28=104。

旧库存100→104不仅是face桶+2：walls为11→10，evidence为7→8，derived为26→28。构造器不是历史pre-A11代码，保留了当前阶梯及共端点传播；docstring已改正。


```sh
$ python - <<'PYCODE'
from collections import Counter
from tests.test_a11_gt_1mm_ingest_resolution import plain_as_received,_unsnapped_coordinate_inventory,_bucket_of
counts=Counter()
for item,n in _unsnapped_coordinate_inventory(plain_as_received.__wrapped__()).items():
    counts[item.rsplit(' = ',1)[0]]+=n
buckets=Counter()
for path,n in sorted(counts.items()):
    print(path,n)
    buckets[_bucket_of(path)]+=n
print('DERIVED BUCKETS',dict(buckets),'TOTAL',sum(buckets.values()))
PYCODE
views.*.boundary_edges.*.evidence.footprint_edge_points.*.* 6
views.*.boundary_edges.*.evidence.opposite_face_const 2
views.*.boundary_edges.*.evidence.raw_face_const 2
views.*.boundary_edges.*.p1.* 2
views.*.boundary_edges.*.p2.* 2
views.*.boundary_edges.*.span_hi 2
views.*.boundary_edges.*.span_lo 2
views.*.converter_readouts.axis_snapped_lines.*.after_p0.* 3
views.*.converter_readouts.axis_snapped_lines.*.after_p1.* 3
views.*.converter_readouts.face_groups_with_a_split_const.*.member_consts.* 4
views.*.face_lines.*.along_max 17
views.*.face_lines.*.along_min 17
views.*.face_lines.*.const 14
views.*.footprint.rings.*.points.*.* 8
views.*.openings.*.along_max 5
views.*.openings.*.along_min 5
views.*.walls.*.along_max 5
views.*.walls.*.along_min 5
DERIVED BUCKETS {'derived': 28, 'evidence': 8, 'face_lines': 48, 'openings': 10, 'walls': 10} TOTAL 104
```


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider tests/test_a11_gt_1mm_ingest_resolution.py
bringing up nodes...
bringing up nodes...

............                                                             [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
12 passed in 5.27s
```


## T4 · 逐项枚举及额外修复

`50ee08b0`：关键词检索、AST计数断言检索，再沿fixture/helper与声明点扩展。检索原始命令：
```sh
rg -n -i '13a[d-f]|rev-|axis_snapped_lines|non_orthogonal_lines|AXIS_SNAP_MAX_ANGLE_DEG|AXIS_SNAP_MAX_DEVIATION_M|10 ?mm' tests --glob '*.py'
```
AST补检规则：遍历tests的FunctionDef/test_*中的Assert，对含face_lines/wall_lines/walls/targets/segments且含len或数字比较的节点逐项列出；不能用测试是否红作为入选条件。

额外发现三处：

- A11豁免代表路径原先漏了converter_readouts，根本不属schema；G-c又已把非正交端点定义为RAW，不能继续把它说成应吸附坐标。保留该检查方向，换到真实post-snap after_p1，并证明错误豁免能被抓住。
- facts readouts的成功路径BLOCK库存清零，旧比较只比到了INFO。复用临时孤立线夹具，经真实P1和build_view比较，恢复BLOCK/G5失败的透传检查。
- snap列表由2增3后，原[:1]一次删2条，失去“缺1条”的反例。逐个handle新拷贝、每次只删一条，均触发相同schema错误。

同一组三个变异的旧绿/新红原文如下：


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider /tmp/gc_rework1_evidence/test_T4_sensitivity.py  # T4修改前
bringing up nodes...
bringing up nodes...

...                                                                      [100%]
3 passed in 4.12s
```


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider /tmp/gc_rework1_evidence/test_T4_sensitivity.py  # T4修改后
bringing up nodes...
bringing up nodes...

FFF                                                                      [100%]
=================================== FAILURES ===================================
_________________________ test_newly_exempted_after_p1 _________________________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x761a8fb7f890>

    def test_newly_exempted_after_p1(monkeypatch):
        monkeypatch.setitem(a11.INGEST_NON_COORDINATE_PATHS,
                           'views[*].converter_readouts.axis_snapped_lines[*].after_p1',
                           'deliberately wrong coordinate exemption')
>       a11.test_the_exemption_table_cannot_rot_onto_a_coordinate()

../gc_rework1_evidence/test_T4_sensitivity.py:10: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    def test_the_exemption_table_cannot_rot_onto_a_coordinate():
        """The exempt table is the A-11 "coordinate vs non-coordinate" boundary;
        these REPRESENTATIVE coordinate paths (one per producer family) must
        never be matched by any exemption pattern -- if one is, the exit scan
        has gone blind on real coordinates."""
        coordinate_paths = [
            ("views", "0", "face_lines", "3", "const"),
            ("views", "0", "face_lines", "3", "along_max"),
            ("views", "0", "walls", "2", "face_lo"),
            ("views", "0", "walls", "2", "along_min"),
            ("views", "0", "openings", "1", "cross_hi"),
            ("views", "0", "footprint", "rings", "0", "points", "*", "0"),
            ("views", "0", "boundary_edges", "5", "span_lo"),
            ("views", "0", "boundary_edges", "5", "p2", "1"),
            ("views", "0", "boundary_edges", "5", "evidence", "raw_face_const"),
            ("views", "0", "boundary_edges", "5", "evidence",
             "footprint_edge_points", "*", "1"),
            ("views", "0", "boundary_ring_losses", "0", "span", "const"),
            # G-c makes non_orthogonal endpoints RAW/exempt; the former path
            # also omitted converter_readouts and never named a schema field.
            # Keep the coordinate tooth on the real second POST-snap endpoint.
            ("views", "0", "converter_readouts", "axis_snapped_lines", "0",
             "after_p1", "0"),
            ("views", "0", "converter_readouts", "axis_snapped_lines", "0",
             "after_p0", "1"),
            ("views", "0", "converter_readouts",
             "face_groups_with_a_split_const", "0", "member_consts", "0"),
            ("views", "0", "converter_readouts",
             "unresolved_opening_carriers", "0", "cross_lo"),
        ]
        for path in coordinate_paths:
            for pattern in INGEST_NON_COORDINATE_PATHS:
>               assert not _path_matches(tuple(path), pattern), \
                    f"exemption {pattern!r} swallows coordinate path {'.'.join(path)!r}"
E               AssertionError: exemption 'views[*].converter_readouts.axis_snapped_lines[*].after_p1' swallows coordinate path 'views.0.converter_readouts.axis_snapped_lines.0.after_p1.0'
E               assert not True
E                +  where True = _path_matches(('views', '0', 'converter_readouts', 'axis_snapped_lines', '0', 'after_p1', ...), 'views[*].converter_readouts.axis_snapped_lines[*].after_p1')
E                +    where ('views', '0', 'converter_readouts', 'axis_snapped_lines', '0', 'after_p1', ...) = tuple(('views', '0', 'converter_readouts', 'axis_snapped_lines', '0', 'after_p1', ...))

tests/test_a11_gt_1mm_ingest_resolution.py:311: AssertionError
________________________ test_ignoring_one_missing_snap ________________________
[gw2] linux -- Python 3.12.13 /opt/venv/bin/python

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7a60e5b6c8f0>

    def test_ignoring_one_missing_snap(monkeypatch):
        doc = facts.as_received_doc.__wrapped__()
        original = facts.AsMeasuredV1.model_validate
        def misses_one(cls, raw, **kwargs):
            readouts = raw['views'][0]['converter_readouts']
            if len(readouts['axis_snapped_lines']) == 2:
                return doc
            return original(raw, **kwargs)
        monkeypatch.setattr(facts.AsMeasuredV1, 'model_validate', classmethod(misses_one))
>       facts.test_o21bs_deleting_a_snap_entry_turns_the_ledger_red(doc)

../gc_rework1_evidence/test_T4_sensitivity.py:34: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

as_received_doc = AsMeasuredV1(schema_version=1, case='sm25-L_anchor', source_dxf_label='sm25-L_t3_as_received.dxf', source_dxf_sha256='...ning dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': True}]))])

    def test_o21bs_deleting_a_snap_entry_turns_the_ledger_red(as_received_doc):
        """⭐⭐ Dispatch ②-1b-S R3's explicit self-proof requirement: "把吸附清单
        里任一条删掉 -> 恒等式必须红".  The face line itself (still 13AD, still a
        real orthogonal stroke) is untouched -- only its itemisation entry in
        ``axis_snapped_lines`` is removed, proving the CROSS-COUNT check (not
        just "the list is non-empty") is what has teeth here."""
        original = as_received_doc.model_dump(mode="json")
        view = next(v for v in original["views"] if v["view_id"] == "plan-F1")
        snapped = view["converter_readouts"]["axis_snapped_lines"]
        assert len(snapped) == 3, "premise: the fixture really holds 3 entries"
        for removed in snapped:
            raw = copy.deepcopy(original)
            target = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
            target["converter_readouts"]["axis_snapped_lines"] = [
                row for row in snapped if row["id"] != removed["id"]]
>           with pytest.raises(ValueError, match="as_measured_axis_snapped_ledger_broken"):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           Failed: DID NOT RAISE <class 'ValueError'>

tests/test_as_measured_facts_layer.py:692: Failed
__________________________ test_losing_block_readouts __________________________
[gw1] linux -- Python 3.12.13 /opt/venv/bin/python

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7b708479dd60>
tmp_path = PosixPath('/tmp/pytest-of-root/pytest-21057/popen-gw1/test_losing_block_readouts0')

    def test_losing_block_readouts(monkeypatch, tmp_path):
        original = facts.am._readout_records
        def without_blocks(geo):
            diagnostics, gates = original(geo)
            return [d for d in diagnostics if d['severity'] != 'BLOCK'], gates
        monkeypatch.setattr(facts.am, '_readout_records', without_blocks)
        doc = facts.as_received_doc.__wrapped__()
        fn = facts.test_r2_readouts_are_the_converters_own_numbers
        kwargs = {'tmp_path': tmp_path} if 'tmp_path' in inspect.signature(fn).parameters else {}
>       fn(doc, **kwargs)

../gc_rework1_evidence/test_T4_sensitivity.py:22: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_as_measured_facts_layer.py:753: in test_r2_readouts_are_the_converters_own_numbers
    _assert_converter_readouts_match(blocked_view.converter_readouts, blocked_geo)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

readouts = AsMeasuredConverterReadoutsV1(dangles=1, cuts=0, invalid=0, degenerate_line_count=1, degenerate_line_handles=['13DC'],...pening dual evidence', 'passed': True}, {'id': 'G5', 'name': 'topology closure + area conservation', 'passed': False}])
geo = P1PlanViewGeometry(view_id='plan-F1', floor_id='F1', quant_step_native=0.1, wall_lines=[('136B', -30229.0, 47973.60000...143B', '13B9', '143A', '13D9', '160F', '13CC', '13F7', '13D8', '139A', '13F4', '1427', '1384', '13EA', '1394', '1376'})

    def _assert_converter_readouts_match(readouts, geo):
        assert (readouts.dangles, readouts.cuts, readouts.invalid) == (
            geo.dangles, geo.cuts, geo.invalid)
        assert readouts.degenerate_line_count == geo.degenerate_line_count
        assert readouts.wall_lines_total == len(geo.wall_lines)
>       assert [d["code"] for d in readouts.diagnostics] == [
            str(getattr(d.code, "value", d.code)) for d in geo.diagnostics]
E       AssertionError: assert ['tarch_wall_...xcluded', ...] == ['tarch_wall_...xcluded', ...]
E         
E         At index 4 diff: 'tarch_interior_opening_excluded' != 'tarch_wall_free_end'
E         Right contains one more item: 'tarch_interior_opening_excluded'
E         Use -v to get more diff

tests/test_as_measured_facts_layer.py:761: AssertionError
=========================== short test summary info ============================
FAILED ../gc_rework1_evidence/test_T4_sensitivity.py::test_newly_exempted_after_p1
FAILED ../gc_rework1_evidence/test_T4_sensitivity.py::test_ignoring_one_missing_snap
FAILED ../gc_rework1_evidence/test_T4_sensitivity.py::test_losing_block_readouts
3 failed in 4.92s
```


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider tests/test_a11_gt_1mm_ingest_resolution.py tests/test_as_measured_facts_layer.py tests/test_tarch_converter_p1_geometry.py tests/test_gt_facts_staging_sm25.py tests/test_as_drawn_denominator_consistency_readout.py tests/test_gt_revisions_and_as_signed.py tests/test_f133_same_floor_step.py
bringing up nodes...
bringing up nodes...

........................................................................ [ 37%]
........................................................................ [ 74%]
..................................................                       [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
194 passed in 13.15s
```


### T4对照表全文

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


## 自审补强、gate①及最终全量

自审补强房间完整性后，request全名单和独立审计projectable集合共同约束输出；删房间或仅将一个合法房间改为NA都会红。没有新增测试函数、删除旧函数或改变参数化。下列8个xfailed均来自test_validation_run_baseline既有的严格_RERECORD_XFAIL标记（deterministic-naming golden re-record pending sm21 batch），本轮没有动它们。gate①几何/契约相关测试与转换器G1–G10反例及单门对应性检查均显式运行：


```sh
$ python -m pytest -q -n 6 -p no:cacheprovider tests/test_answer_compiler_profiles.py tests/test_geometry_kernel.py tests/test_validation_run_baseline.py tests/test_tarch_converter_gate_mutations.py
bringing up nodes...
bringing up nodes...

..................x..x.xx...x.....xx...x.................                [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
49 passed, 8 xfailed in 27.32s
```


```sh
$ git log --oneline -1
python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"
python -m pytest -q -n 6 -p no:cacheprovider
python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"
f0437dba 09.07_Gc_rework_T2_room_completeness
/tmp/gc_rework_astra/src/agent/judge/tarch_normalize.py
bringing up nodes...
bringing up nodes...

........................................................................ [  1%]
........................................................................ [  3%]
........................................................................ [  5%]
........................................................................ [  7%]
........................................................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
........................................................................ [ 17%]
........................................................................ [ 19%]
........................................................................ [ 21%]
........................................................................ [ 23%]
........................................................................ [ 25%]
........................................................................ [ 26%]
........................................................................ [ 28%]
........................................................................ [ 30%]
........................................................................ [ 32%]
........................................................................ [ 33%]
........................................................................ [ 35%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 41%]
........................................................................ [ 42%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 48%]
........................................................................ [ 50%]
........................................................................ [ 51%]
........................................................................ [ 53%]
........................................................................ [ 55%]
........................................................................ [ 57%]
........................................................................ [ 59%]
........................................................................ [ 60%]
..................................................s..................... [ 62%]
........................................................................ [ 64%]
........................................................................ [ 66%]
........................................................................ [ 67%]
........................................................................ [ 69%]
................................................................x....... [ 71%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 76%]
........................................................................ [ 78%]
........................................................................ [ 80%]
........................................................................ [ 82%]
...................xx..................x................................ [ 84%]
........................................................................ [ 85%]
........................................................................ [ 87%]
........................................................................ [ 89%]
................................................................x....... [ 91%]
........................................................................ [ 93%]
........................................................................ [ 94%]
......x.xx.xx.xx.x...................................................... [ 96%]
.............................s.......................................... [ 98%]
................................................................         [100%]
=============================== warnings summary ===============================
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D1_six_panels_render_with_titles_and_exact_canvas_size
tests/test_batch_d_typed_grade.py::test_L_D2_missing_facade_renders_explicit_placeholder_not_omission
tests/test_batch_d_typed_grade.py::test_L_D2_missing_facade_renders_explicit_placeholder_not_omission
  /tmp/gc_rework_astra/tests/test_batch_d_typed_grade.py:44: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    for px in region.getdata():

tests/test_batch_d_typed_grade.py: 18 warnings
  /tmp/gc_rework_astra/tests/test_batch_d_typed_grade.py:53: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    for px in region.getdata():

tests/test_batch_d_typed_grade.py::test_L_D1_does_not_read_product_mirror_or_local_x_declarations
tests/test_batch_d_typed_grade.py::test_L_D1_does_not_read_product_mirror_or_local_x_declarations
  /tmp/gc_rework_astra/tests/test_batch_d_typed_grade.py:161: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    assert list(image_a.getdata()) == list(image_b.getdata())

tests/test_c2_b2_v3.py::test_f3_tampered_v3_and_feature_state_fail_closed
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `Floor` - serialized value may not be as expected [field_name='floors', input_value={'id': 'f1'}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_f9_route2_s2_authoritative_projector.py::test_real_integrated_entry_clean_run_shows_pass
  /tmp/gc_rework_astra/src/agent/pipeline.py:2546: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw1/test_real_integrated_entry_cle0/run_x; using flow defaults
    run_cfg = load_run_config(run_config_dir)

tests/test_f9_route2_s2_authoritative_projector.py::test_real_integrated_entry_neuter_projector_flips_to_fail
  /tmp/gc_rework_astra/src/agent/pipeline.py:2546: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw1/test_real_integrated_entry_neu0/run_x; using flow defaults
    run_cfg = load_run_config(run_config_dir)

tests/test_gt_from_dxf.py: 10 warnings
tests/test_gt_overlay.py: 6 warnings
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_from_dxf.py::test_plan_only_z_and_u_hidden_depth_are_preserved
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_from_dxf.py::test_elevation_multi_view_z_disagreement_fails_closed
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_overlay_affine_hash_watermark_and_atomic_output
tests/test_gt_overlay.py::test_v3_overlay_rejects_raster_hash_mismatch_and_sanitized_collision
tests/test_gt_overlay.py::test_v3_overlay_rejects_document_manifest_binding_mismatch
tests/test_gt_overlay.py::test_v3_elevation_overlay_uses_declared_floor_z_and_affine
tests/test_gt_overlay.py::test_v3_overlay_rejects_competing_binding_empty_view_id_and_singular_affine
tests/test_gt_overlay.py::test_v3_review_annotations_are_review_only_and_never_guess
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster', 'so...'m11': 0.1, 'm12': 0.0}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_elevation_overlay_uses_declared_floor_z_and_affine
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster', 'so...space': 'source_metre'}}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'elev-raster', 'so...'m11': 0.1, 'm12': 0.0}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_overlay_rejects_competing_binding_empty_view_id_and_singular_affine
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'Flo...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `NorthAxisBindingV1` - serialized value may not be as expected [field_name='north_axis', input_value={'value_deg': 27.5, 'sour...ce_entity_handle': '30'}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster', 'so...space': 'source_metre'}}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'plan-raster-2', '...space': 'source_metre'}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_gt_overlay.py::test_v3_plan_opening_bars_sit_on_wall_band_real_sm24
tests/test_gt_overlay.py::test_v3_plan_opening_bar_keeps_outer_skin_position_when_wall_thickness_is_none
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': '1F'...'ceiling_height_m': 4.5}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': 0.24}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': 0.24}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'elevation', 'id...entity_index': None}]}]}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `RasterOverlayBindingV1` - serialized value may not be as expected [field_name='raster_overlays', input_value={'id': 'raster_plan_F1', ...space': 'source_metre'}}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_marker_me0/sm21_anchor/run_2026-06-20_gpt54_reading; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
tests/test_orchestrate_baseline.py::test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_marker_me0/sm21_anchor/run_2026-06-20_gpt54_reading/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py: 13 warnings
tests/test_reading_mode.py: 1 warning
tests/test_provenance_baseline.py: 2 warnings
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'conclusion'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py: 14 warnings
tests/test_reading_mode.py: 1 warning
tests/test_provenance_baseline.py: 2 warnings
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'focus'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py: 13 warnings
tests/test_reading_mode.py: 1 warning
tests/test_provenance_baseline.py: 2 warnings
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'diagnosis'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py: 13 warnings
tests/test_reading_mode.py: 1 warning
tests/test_provenance_baseline.py: 2 warnings
  /tmp/gc_rework_astra/scripts/tool_scripts/report_assembly.py:910: RuntimeWarning: REPORT.md missing AGENT region 'recommendations'; using placeholder
    sections.append(_wrap_region("AGENT", key, _agent_region(key, baseline, agent_regions)))

tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_missing_a0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
tests/test_orchestrate_baseline.py::test_record_baseline_missing_agent_region_gets_placeholder
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_missing_a0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract
  /opt/venv/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `FloorBindingV1` - serialized value may not be as expected [field_name='floors', input_value={'id': 'F1', 'name': 'F1'...'ceiling_height_m': 3.0}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `PlanViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    PydanticSerializationUnexpectedValue(Expected `ElevationViewBindingV1` - serialized value may not be as expected [field_name='views', input_value={'kind': 'plan', 'id': 'p...wall_thickness_m': None}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_duplicate0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_duplicate_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_duplicate0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_nested_ag0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
tests/test_orchestrate_baseline.py::test_record_baseline_nested_agent_marker_fails_before_write
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_nested_ag0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw4/test_agent_marker_like_text_in0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
tests/test_orchestrate_baseline.py::test_agent_marker_like_text_inside_gen_payload_is_ignored
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw4/test_agent_marker_like_text_in0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_stale_rec0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
tests/test_orchestrate_baseline.py::test_record_baseline_stale_recommendation_evidence_fails_with_agent_block
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw4/test_record_baseline_stale_rec0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_uses0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_uses0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_regression_tier_surfaces_blocking_check_row
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_regr0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_regression_tier_surfaces_blocking_check_row
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_regr0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_marks_unfrozen_run_legacy
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_mark0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_marks_unfrozen_run_legacy
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_mark0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_context_tamper_does_not_change_blocking
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_cont0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_R1_5_record_baseline_context_tamper_does_not_change_blocking
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_R1_5_record_baseline_cont0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_on_anchor
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_on_anchor0/sm20_anchor/run_2026-06-15_baseline; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_on_anchor
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_on_anchor0/sm20_anchor/run_2026-06-15_baseline/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_report_lists_eyeball_items
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_report_li0/sm21_anchor/run_2026-06-20_gpt54_reading; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_report_lists_eyeball_items
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_report_li0/sm21_anchor/run_2026-06-20_gpt54_reading/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_state_aware_report_suppresses_dead_viewer
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_state_awa0/sm21_anchor/run_2026-06-20_sonnet_reading; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_state_aware_report_suppresses_dead_viewer
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_state_awa0/sm21_anchor/run_2026-06-20_sonnet_reading/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_missing_corrections_sidecar_does_not_change_gates
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_missing_c0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_missing_corrections_sidecar_does_not_change_gates
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_missing_c0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_correctio0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
tests/test_orchestrate_baseline.py::test_record_baseline_correction_audit_summary_is_separate_from_flags
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_correctio0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_orchestrate_baseline.py::test_record_baseline_malformed_corrections_sidecar_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_malformed0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_orchestrate_baseline.py::test_record_baseline_malformed_corrections_sidecar_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw5/test_record_baseline_malformed0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_run_stage_flow.py::test_cmd_run_judge_off_still_writes_correction_renders
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_cmd_run_judge_off_still_w0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_resample_invalidates_downstream_before_force_run
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2756: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_cmd_resample_invalidates_0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_provenance_baseline.py::test_record_baseline_writes_provenance_and_report_summary
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw1/test_record_baseline_writes_pr0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_provenance_baseline.py::test_record_baseline_writes_provenance_and_report_summary
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw1/test_record_baseline_writes_pr0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_run_stage_flow.py::test_flow_human_review_checkpoint_and_approve_resume
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_human_review_checkpo0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_human_review_checkpoint_and_approve_resume
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2756: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_human_review_checkpo0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_human_review_checkpoint_and_approve_resume
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_human_review_checkpo0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_provenance_baseline.py::test_record_baseline_git_failure_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:201: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw1/test_record_baseline_git_failu0/synthetic_case/run_audit; using flow defaults
    run_cfg = load_run_config(run_dir)

tests/test_provenance_baseline.py::test_record_baseline_git_failure_is_best_effort
  /tmp/gc_rework_astra/scripts/tool_scripts/record_baseline.py:596: RuntimeWarning: /tmp/pytest-of-root/pytest-21112/popen-gw1/test_record_baseline_git_failu0/synthetic_case/run_audit/run_config.yaml missing; baseline.models will use llm.yaml fallbacks plus unknown placeholders
    "models": _models_from_llm_yaml(run_dir, orchestrator=orchestrator),

tests/test_run_stage_flow.py::test_flow_first_pass_packet_has_gt_evidence_before_manifest_save
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_first_pass_packet_ha0/sm21_anchor/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_judge_block_auto_invalidates_and_force_resamples
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_judge_block_auto_inv0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_terminal_stop_returns_20
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_terminal_stop_return0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_geometry_auto_records_auto_policy
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_flow_geometry_auto_record0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_run_refuses_persisted_v1_run
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_cmd_run_refuses_persisted0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_flow_refuses_persisted_v1_run
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_cmd_flow_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_resample_refuses_persisted_v1_before_any_write
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2756: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_cmd_resample_refuses_pers0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_new_run_flow_smoke_produces_v2_base_v2_records
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2909: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_new_run_flow_smoke_produc0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_v1_run_resumable_after_explicit_migration
  /tmp/gc_rework_astra/scripts/tool_scripts/run_stage.py:2682: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-21112/popen-gw5/test_v1_run_resumable_after_ex0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_render_grade.py: 16 warnings
  /tmp/gc_rework_astra/tests/test_render_grade.py:238: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    return sum(1 for px in view.getdata() if px == color)

tests/test_render_grade.py::test_render_grade_draws_no_data_for_missing_score_floor
tests/test_render_grade.py::test_render_grade_missing_facade_key_is_no_data
  /tmp/gc_rework_astra/tests/test_render_grade.py:243: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
    return sum(1 for px in view.getdata() if all(abs(int(px[i]) - color[i]) <= tol for i in range(3)))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
4009 passed, 2 skipped, 13 xfailed, 211 warnings in 463.05s (0:07:43)
/tmp/gc_rework_astra/src/agent/judge/tarch_normalize.py
```


全量逐位闭合：主线参照3989+2+13=4004；当前4009+2+13=4024，净增20。原G-c六红使4009个正常测试中只有4003通过；本次修复使这六条恢复，4003+6=4009。

新增20全部来自接手前已落库G-c：P1算法测试34个函数→48个（+14），facts层52→58（+6）。四个前任改动文件合计34个新名字、14个消失名字，其中14个全部有重推后的对应物，真正新增20；所有这些新增/移除名字均无参数化装饰器，共名函数的参数化装饰器未变。本次T1–T4及自审补强的函数名/装饰器完全不变（净增0）。具体名单及装饰器机械对账原文：


```sh
$ AST对照 git show fde2f24c:tests/<file> 与当前文件；输出新增/消失函数及装饰器
test_tarch_converter_p1_geometry.py old 34 new 48 added 25 removed 11
ADD test_gc6_tier0_boundary_at_q_noise_is_not_recorded_at_all decorators []
ADD test_gc6_tier1_boundary_is_cap_on_a_long_stroke decorators []
ADD test_gc6_tier1_boundary_is_the_angle_on_a_short_stroke decorators []
ADD test_gc6_tier2a_long_stroke_inside_the_envelope_but_over_cap decorators []
ADD test_gc6_tier2b_both_ends_anchored_is_a_suspected_real_slant decorators []
ADD test_gc6_tier2c_unanchored_and_visibly_different_goes_to_a_human decorators []
ADD test_gc6_tier3_boundary_is_the_signed_five_degrees decorators []
ADD test_gc_ingest_grid_is_tau_node_not_a_fourth_threshold decorators []
ADD test_gc_ladder_limit_first_limb_is_subsumed_by_the_angle_envelope decorators []
ADD test_gc_ladder_limit_table_matches_the_shape_the_user_asked_for decorators []
ADD test_gc_lock10_the_envelope_and_the_cap_are_not_redundant decorators []
ADD test_gc_lock11_the_snap_alone_never_moves_an_along_axis_endpoint decorators []
ADD test_gc_lock11b_an_along_axis_endpoint_DOES_follow_a_relocated_node decorators []
ADD test_gc_lock1_tier1_admits_and_itemises_with_the_derived_ceiling decorators []
ADD test_gc_lock2_over_cap_is_still_refused_and_is_named_arbitration decorators []
ADD test_gc_lock3_cap_is_derived_per_request_not_baked_in decorators []
ADD test_gc_lock4_real_tremor_all_three_strokes_are_tier1_and_auditable decorators []
ADD test_gc_lock4b_the_anchor_rule_closes_the_joints_the_midpoint_split decorators []
ADD test_gc_lock5_the_deviation_ceiling_still_has_teeth_now_as_cap decorators []
ADD test_gc_lock5b_the_retired_10mm_ceiling_is_not_silently_still_in_force decorators []
ADD test_gc_lock6_on_a_short_stroke_only_the_angle_can_refuse decorators []
ADD test_gc_lock7_forty_five_degrees_is_tier3_and_never_reaches_a_human decorators []
ADD test_gc_lock8_five_degrees_still_admits_the_0p39deg_slanted_wall_KNOWN_RISK decorators []
ADD test_gc_lock9_moving_only_the_angle_envelope_flips_a_case decorators []
ADD test_gc_the_ladder_holds_exactly_three_numbers decorators []
REMOVE test_axis_snap_admits_a_line_within_the_threshold_and_itemises_it decorators []
REMOVE test_axis_snap_along_axis_endpoints_survive_bit_for_bit_through_quantize decorators []
REMOVE test_axis_snap_still_refuses_a_genuine_diagonal_beyond_the_threshold decorators []
REMOVE test_axis_snap_threshold_is_a_real_parameter_not_hardcoded decorators []
REMOVE test_f147_acceptance_1_real_tremor_13ad_is_admitted_by_both_gates decorators []
REMOVE test_f147_acceptance_1b_the_signed_10mm_deviation_value_has_teeth decorators []
REMOVE test_f147_acceptance_2_short_slant_passes_the_mm_gate_and_the_angle_gate_stops_it decorators []
REMOVE test_f147_acceptance_3_forty_five_degrees_is_refused_by_both_gates decorators []
REMOVE test_f147_acceptance_5a_widening_only_the_angle_gate_flips_a_case decorators []
REMOVE test_f147_acceptance_5b_widening_only_the_deviation_gate_flips_a_different_case decorators []
REMOVE test_f147_signed_1deg_admits_the_0p39deg_slanted_wall_KNOWN_SIGNED_RISK decorators []
test_as_measured_facts_layer.py old 52 new 58 added 7 removed 1
ADD test_gc_a11d3_a_non_orthogonal_row_keeps_its_sub_millimetre_evidence decorators []
ADD test_gc_a11d3_the_exit_scan_exempts_that_row_and_would_flag_it_otherwise decorators []
ADD test_gc_an_arbitration_row_cannot_disagree_with_its_diagnostic decorators []
ADD test_gc_deleting_an_arbitration_row_turns_the_ledger_red decorators []
ADD test_gc_the_arbitration_row_validates_and_carries_what_a_signer_needs decorators []
ADD test_gc_tier3_does_not_enter_the_arbitration_ledger decorators []
ADD test_o21bs_the_real_snap_list_has_exactly_the_three_known_handles decorators []
REMOVE test_o21bs_the_real_snap_list_has_exactly_the_two_known_handles decorators []
test_as_drawn_denominator_consistency_readout.py old 7 new 7 added 0 removed 0
test_gt_facts_staging_sm25.py old 9 new 9 added 2 removed 2
ADD test_3_signing_a_const_candidate_is_refused_by_the_wall_face_gate decorators []
ADD test_6_the_worklist_is_empty_because_the_detector_finds_nothing decorators []
REMOVE test_3_signing_the_real_const_candidate_is_refused_by_the_wall_face_gate decorators []
REMOVE test_6_the_worklist_is_all_unsigned_and_matches_the_a11_shape decorators []
```


P1的11个改名对应：admit→lock1、over-deviation refusal→lock2、threshold parameter→lock3、真实13AD tremor→lock4、10mm tooth→lock5、短线角度拒绝→lock6、45度→lock7、0.39度风险→lock8、仅改角度→lock9、仅改偏移→lock10、along endpoints→lock11。P1新增14为lock4b/5b/11b、七条gc6阶梯边界、四条公式/网格/三参数自检。facts层改名1条是two_known_handles→three_known_handles，新增6条为两条A11-d3证据与四条仲裁台账检查。staging改名2条是候选台账变空、真实const候选改合成候选；数量不变。readout文件无函数增删。


```sh
$ 返工范围AST核对与生产源码差分
tests/deferred_projection_ledger.py test names/decorators unchanged 0 new root-prefixed production strings 0
tests/test_a11_gt_1mm_ingest_resolution.py test names/decorators unchanged 11 new root-prefixed production strings 0
tests/test_answer_compiler_profiles.py test names/decorators unchanged 7 new root-prefixed production strings 0
tests/test_as_drawn_denominator_f126.py test names/decorators unchanged 6 new root-prefixed production strings 0
tests/test_as_measured_facts_layer.py test names/decorators unchanged 58 new root-prefixed production strings 0
tests/test_boundary_condition_facts.py test names/decorators unchanged 13 new root-prefixed production strings 0
tests/test_f156_ring_from_intersection.py test names/decorators unchanged 12 new root-prefixed production strings 0
tests/test_o21d_exclusion_gap.py test names/decorators unchanged 17 new root-prefixed production strings 0
production source changed in rework: 0
inventory names resolve: 168
```


```sh
$ git log --oneline --numstat fd5c3388..HEAD
f0437dba 09.07_Gc_rework_T2_room_completeness
1	1	tests/gc_rework1_inventory.md
37	1	tests/test_answer_compiler_profiles.py
50ee08b0 09.07_Gc_rework_T4_enumerate_fixture_inventory
189	0	tests/gc_rework1_inventory.md
5	1	tests/test_a11_gt_1mm_ingest_resolution.py
47	57	tests/test_as_measured_facts_layer.py
b6664f22 09.07_Gc_rework_T3_derive_scan_inventory
84	32	tests/test_a11_gt_1mm_ingest_resolution.py
035fc237 09.07_Gc_rework_T2_rebuild_negative_stock
44	9	tests/test_a11_gt_1mm_ingest_resolution.py
61	15	tests/test_answer_compiler_profiles.py
67	68	tests/test_as_drawn_denominator_f126.py
633bdc81 09.07_Gc_rework_T1_retire_form_b
17	12	tests/deferred_projection_ledger.py
4	3	tests/test_boundary_condition_facts.py
4	4	tests/test_f156_ring_from_intersection.py
8	9	tests/test_o21d_exclusion_gap.py
```


```sh
$ git log --oneline fd5c3388..HEAD
f0437dba 09.07_Gc_rework_T2_room_completeness
50ee08b0 09.07_Gc_rework_T4_enumerate_fixture_inventory
b6664f22 09.07_Gc_rework_T3_derive_scan_inventory
035fc237 09.07_Gc_rework_T2_rebuild_negative_stock
633bdc81 09.07_Gc_rework_T1_retire_form_b
```


```sh
$ git diff --numstat fd5c3388..HEAD
17	12	tests/deferred_projection_ledger.py
189	0	tests/gc_rework1_inventory.md
133	42	tests/test_a11_gt_1mm_ingest_resolution.py
98	16	tests/test_answer_compiler_profiles.py
67	68	tests/test_as_drawn_denominator_f126.py
47	57	tests/test_as_measured_facts_layer.py
4	3	tests/test_boundary_condition_facts.py
4	4	tests/test_f156_ring_from_intersection.py
8	9	tests/test_o21d_exclusion_gap.py
```


## 外围勘误与最薄弱判断

- T1首红位于总数行而非per-code行，按派工单勘误执行，未当成承重方向错误。
- T2身份串本身没有变化，变化的是4处顺序；重新配对身份并重建反例即可保持修法方向。
- T3的48是坐标出现次数，13AF贡献两个端点；其余桶也改变，已逐字段推导。
- 原派工单提及的gt_revisions模块“13AF is skewed too far for the signed snap gates”历史叙述仍不正确：它曾是太直而未进入旧门。本单不改该生产模块，点名留给其拥有者处理。

本轮最薄弱的一处判断是T4外延：将宽泛wall计数命中中的冻结run、typed合成夹具及其他分辨率测试判为不依赖此次真实歪线拒绝库存。如果某个动态helper间接读了当前facts而源码没有显示这种依赖，仍可能漏掉另一把空转锁。表内给出入选/排除依据与可能漏掉的类别；全量绿不能替代这层判断。另明确L4的跨q格样本依赖当前档0与q量化的契约，未来若改这层几何规则，应重新构造该D1输入，而不是删掉列明断言。

## 复现脚本原文

以下脚本位于本席证据临时目录；在此全文嵌入，避免交件依赖临时目录的寿命。正式测试与168行对照已在分支提交。


### replay_baseline.py

```python
"""Replay the post-rebase test snapshot and restore the committed rework.

Only this worktree's changed Python test files are replaced.  Production
sources are byte-identical to the post-rebase snapshot and are never written.
Every replacement is backed up before any mutation, and finally restores it.
"""
import json
import subprocess
import sys
from pathlib import Path

repo = Path('/tmp/gc_rework_astra')
evidence = Path('/tmp/gc_rework1_evidence')
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo) == b''
source_delta = subprocess.check_output(['git', 'diff', '--name-only', 'fd5c3388', '--', 'src'], cwd=repo)
assert source_delta == b'', source_delta
changed = subprocess.check_output(['git', 'diff', '--name-only', 'fd5c3388', '--', 'tests'], cwd=repo, text=True).splitlines()
paths = [p for p in changed if p.endswith('.py')]
backup = evidence / 'committed_test_backups'
backup.mkdir(exist_ok=True)
saved = {name:(repo/name).read_bytes() for name in paths}
for name,data in saved.items():
    destination=backup/name
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(data)
(evidence/'replay_manifest.json').write_text(json.dumps(paths,indent=2))
print('BASELINE TEST SNAPSHOT fd5c3388; production delta 0; restored files:', paths, flush=True)
try:
    for name in paths:
        (repo/name).write_bytes(subprocess.check_output(['git','show',f'fd5c3388:{name}'],cwd=repo))
    subprocess.run([sys.executable,'-c','import src.agent.judge.tarch_normalize as m; print(m.__file__)'],cwd=repo,check=True)
    result = subprocess.run([sys.executable,'-m','pytest','-q','-n','6','-p','no:cacheprovider'],cwd=repo)
    subprocess.run([sys.executable,'-c','import src.agent.judge.tarch_normalize as m; print(m.__file__)'],cwd=repo,check=True)
    print('BASELINE pytest exit:',result.returncode,flush=True)
finally:
    for name,data in saved.items():
        (repo/name).write_bytes(data)
    print('RESTORED committed test bytes:',len(saved),flush=True)
    print('STATUS',subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True),flush=True)
```


### test_T2_red.py

```python
from copy import deepcopy
from src.agent.judge.answer_compiler import AnswerCompiler, OutputProfile, read_facts_for_compilation
from src.agent.judge.gt_revisions import derive_as_signed
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1
from tests.test_gt_facts_staging_sm25 import _synthetic_unsigned_record
from tests.test_answer_compiler_profiles import SM25_SOURCE, _assert_no_unsigned_geometry
from tests.test_as_drawn_denominator_f126 import _l4_nonorthogonal_fixture, _assert_l4_itemisation, denominator
from tests.test_a11_gt_1mm_ingest_resolution import snapped_as_received, plain_as_received, _assert_external_quantities_identical


def test_unsigned_sample_is_red():
    measured, ledger, _ = read_facts_for_compilation('sm25-L_anchor')
    candidate = ledger.model_copy(update={'revisions': [
        _synthetic_unsigned_record(measured, handle=h) for h in ('13AD', '13AE', '13AF')]})
    request = TarchConversionRequestV1.model_validate_json((SM25_SOURCE / 'request_as_measured.json').read_text())
    answer = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        derive_as_signed(measured, candidate), candidate, request)
    _assert_no_unsigned_geometry(answer)


def test_missing_itemisation_is_red(tmp_path):
    dxf, request, handle = _l4_nonorthogonal_fixture(tmp_path)
    result = denominator(dxf, request, 'plan-F1')
    _assert_l4_itemisation(result, request, handle)
    assert next(g for g in result['gates'] if g['id'] == 'G5')['passed'] is False
    damaged = deepcopy(result)
    damaged['excluded_non_orthogonal_segments'] = []
    _assert_l4_itemisation(damaged, request, handle)


def test_changed_identity_is_red():
    snapped = snapped_as_received.__wrapped__().model_dump(mode='json')
    plain = plain_as_received.__wrapped__().model_dump(mode='json')
    _assert_external_quantities_identical(snapped, plain)
    snapped['views'][0]['face_lines'][0]['id'] = 'DEADFACE'
    _assert_external_quantities_identical(snapped, plain)
```


### test_T4_sensitivity.py

```python
import inspect
from tests import test_a11_gt_1mm_ingest_resolution as a11
from tests import test_as_measured_facts_layer as facts


def test_newly_exempted_after_p1(monkeypatch):
    monkeypatch.setitem(a11.INGEST_NON_COORDINATE_PATHS,
                       'views[*].converter_readouts.axis_snapped_lines[*].after_p1',
                       'deliberately wrong coordinate exemption')
    a11.test_the_exemption_table_cannot_rot_onto_a_coordinate()


def test_losing_block_readouts(monkeypatch, tmp_path):
    original = facts.am._readout_records
    def without_blocks(geo):
        diagnostics, gates = original(geo)
        return [d for d in diagnostics if d['severity'] != 'BLOCK'], gates
    monkeypatch.setattr(facts.am, '_readout_records', without_blocks)
    doc = facts.as_received_doc.__wrapped__()
    fn = facts.test_r2_readouts_are_the_converters_own_numbers
    kwargs = {'tmp_path': tmp_path} if 'tmp_path' in inspect.signature(fn).parameters else {}
    fn(doc, **kwargs)


def test_ignoring_one_missing_snap(monkeypatch):
    doc = facts.as_received_doc.__wrapped__()
    original = facts.AsMeasuredV1.model_validate
    def misses_one(cls, raw, **kwargs):
        readouts = raw['views'][0]['converter_readouts']
        if len(readouts['axis_snapped_lines']) == 2:
            return doc
        return original(raw, **kwargs)
    monkeypatch.setattr(facts.AsMeasuredV1, 'model_validate', classmethod(misses_one))
    facts.test_o21bs_deleting_a_snap_entry_turns_the_ledger_red(doc)
```
