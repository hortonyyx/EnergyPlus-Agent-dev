# 预扫原始输出（`probe_arity.py` 的 stdout，2026-08-14）

```text
# artifacts found: 21

case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline
    objects=138  flagged=19
      ZONEHVAC:EQUIPMENTCONNECTIONS: 19  [missing_required] authored=7 idd=8 missing=['Zone Air Node Name']
case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e
    objects=64  flagged=14
      PEOPLE: 14  [missing_required] authored=8 idd=29 missing=['Activity Level Schedule Name']
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading
    objects=50  flagged=14
      PEOPLE: 14  [missing_required] authored=8 idd=29 missing=['Activity Level Schedule Name']
case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading
    objects=66  flagged=14
      PEOPLE: 14  [missing_required] authored=7 idd=29 missing=['Activity Level Schedule Name']
case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r1
    objects=79  flagged=42
      PEOPLE: 14  [missing_required] authored=8 idd=29 missing=['Activity Level Schedule Name']
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=5 idd=12 missing=['Control Type Schedule Name']
      ZONEHVAC:IDEALLOADSAIRSYSTEM: 14  [missing_required] authored=23 idd=28 missing=['Zone Supply Air Node Name']
case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r2
    objects=64  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e
    objects=106  flagged=14
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=7 idd=12 missing=['Control Type Schedule Name']
case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped
    objects=64  flagged=14
      PEOPLE: 14  [missing_required] authored=9 idd=29 missing=['Activity Level Schedule Name']
case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest
    objects=65  flagged=0
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
case_tests/e2e_tests/sm21_anchor/run_2026-08-07_f13_e2e_verify
    objects=54  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify
    objects=80  flagged=14
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=7 idd=12 missing=['Control Type Schedule Name']
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e
    objects=52  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_accept_B
    objects=64  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_accept_C
    objects=92  flagged=14
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=4 idd=12 missing=['Control 1 Name']
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_batchI_accept_01
    objects=66  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_batchI_accept_02
    objects=64  flagged=14
      ZONEHVAC:IDEALLOADSAIRSYSTEM: 14  [missing_required] authored=14 idd=28 missing=['Zone Supply Air Node Name']
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_oneshot_acceptance
    objects=106  flagged=28
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=7 idd=12 missing=['Control Type Schedule Name']
      ZONEHVAC:IDEALLOADSAIRSYSTEM: 14  [missing_required] authored=2 idd=28 missing=['Zone Supply Air Node Name']
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_post_blocker1_e2e
    objects=109  flagged=14
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=5 idd=12 missing=['Control Type Schedule Name']
case_tests/e2e_tests/sm21_anchor/run_2026-08-13_surface400_accept_01
    objects=106  flagged=28
      ZONECONTROL:THERMOSTAT: 14  [missing_required] authored=7 idd=12 missing=['Control Type Schedule Name']
      ZONEHVAC:IDEALLOADSAIRSYSTEM: 14  [missing_required] authored=2 idd=28 missing=['Zone Supply Air Node Name']
case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading
    objects=99  flagged=22
      ZONECONTROL:THERMOSTAT: 11  [missing_required] authored=2 idd=12 missing=['Control Type Schedule Name', 'Control 1 Object Type', 'Control 1 Name']
      ZONEHVAC:EQUIPMENTLIST: 11  [missing_required] authored=5 idd=110 missing=['Zone Equipment 1 Heating or No-Load Sequence']
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
this node -IDEALLOADSAIRSYSTEM-is not present in base dictionary
case_tests/e2e_tests/smalloffice_23
    objects=35  flagged=9
      PEOPLE: 9  [missing_required] authored=5 idd=29 missing=['Activity Level Schedule Name']

# ---- summary ----
   19 /   138   case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline
   14 /    64   case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e
   14 /    50   case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading
   14 /    66   case_tests/e2e_tests/sm21_anchor/run_2026-06-23_gpt54mini_reading
   42 /    79   case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r1
    0 /    64   case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r2
   14 /   106   case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e
   14 /    64   case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped
    0 /    65   case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest
    0 /    54   case_tests/e2e_tests/sm21_anchor/run_2026-08-07_f13_e2e_verify
   14 /    80   case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify
    0 /    52   case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e
    0 /    64   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_accept_B
   14 /    92   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_accept_C
    0 /    66   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_batchI_accept_01
   14 /    64   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_batchI_accept_02
   28 /   106   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_oneshot_acceptance
   14 /   109   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_post_blocker1_e2e
   28 /   106   case_tests/e2e_tests/sm21_anchor/run_2026-08-13_surface400_accept_01
   22 /    99   case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading
    9 /    35   case_tests/e2e_tests/smalloffice_23
```
