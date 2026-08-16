# 07-07 复现跑 F1 · 判卷原始输出

⛔ 诊断跑，不计正式成绩（CLAUDE.md §1.5 #7 dev 期开发者职能）。
判卷时序：全部六张图跑完 + transcript 泄题面审计通过之后才判。

```
# reading↔gt score — case sm21_anchor  (wall_tol=0.3m, win_tol=0.4m)

## 1f_view  (Floor 1)
  walls   1/4 hit   (max offset 0.0 m)
    vert x : WallSegment(orientation='v', coord=5.0, start=0.0, end=3.0)→MISS, WallSegment(orientation='v', coord=10.0, start=0.0, end=3.0)→MISS  | EXTRA [WallMatch(orientation='v', status='extra', truth=None, read=WallSegment(orientation='v', coord=3.44, start=0.0, end=3.0), delta=None, lateral_drift=False, extent_drift=False, extent_start_drift=False, extent_end_drift=False, pieces=[LinearPiece(kind='extra', span=(0.0, 3.0), within_tol=False), LinearPiece(kind='extra', span=(5.5, 8.0), within_tol=False)], truth_intervals=[], read_intervals=[WallSegment(orientation='v', coord=3.44, start=0.0, end=3.0), WallSegment(orientation='v', coord=3.44, start=5.5, end=8.0)]), WallMatch(orientation='v', status='extra', truth=None, read=WallSegment(orientation='v', coord=8.74, start=0.0, end=3.0), delta=None, lateral_drift=False, extent_drift=False, extent_start_drift=False, extent_end_drift=False, pieces=[LinearPiece(kind='extra', span=(0.0, 3.0), within_tol=False), LinearPiece(kind='extra', span=(5.5, 8.0), within_tol=False)], truth_intervals=[], read_intervals=[WallSegment(orientation='v', coord=8.74, start=0.0, end=3.0), WallSegment(orientation='v', coord=8.74, start=5.5, end=8.0)]), WallMatch(orientation='v', status='extra', truth=None, read=WallSegment(orientation='v', coord=13.4, start=0.0, end=3.0), delta=None, lateral_drift=False, extent_drift=False, extent_start_drift=False, extent_end_drift=False, pieces=[LinearPiece(kind='extra', span=(0.0, 3.0), within_tol=False), LinearPiece(kind='extra', span=(5.5, 8.0), within_tol=False)], truth_intervals=[], read_intervals=[WallSegment(orientation='v', coord=13.4, start=0.0, end=3.0), WallSegment(orientation='v', coord=13.4, start=5.5, end=8.0)])]
    horiz y: WallSegment(orientation='h', coord=3.0, start=0.0, end=15.0)→WallSegment(orientation='h', coord=3.0, start=0.0, end=15.0)(Δ+0.0), WallSegment(orientation='h', coord=5.0, start=0.0, end=15.0)→MISS  | EXTRA [WallMatch(orientation='h', status='extra', truth=None, read=WallSegment(orientation='h', coord=5.5, start=0.0, end=15.0), delta=None, lateral_drift=False, extent_drift=False, extent_start_drift=False, extent_end_drift=False, pieces=[LinearPiece(kind='extra', span=(0.0, 15.0), within_tol=False)], truth_intervals=[], read_intervals=[WallSegment(orientation='h', coord=5.5, start=0.0, end=15.0)])]
  windows 0/3 hit
    N: 1.24-3.64:MISS
    S: 3.44-4.64:MISS
    E: 3.4-4.6:MISS

## 2f_view  (Floor 2)
  walls   1/5 hit   (max offset 0.0 m)
    vert x : WallSegment(orientation='v', coord=3.75, start=0.0, end=3.0)→MISS, WallSegment(orientation='v', coord=7.5, start=0.0, end=3.0)→WallSegment(orientation='v', coord=7.5, start=0.0, end=3.0)(Δ+0.0), WallSegment(orientation='v', coord=11.25, start=0.0, end=3.0)→MISS
    horiz y: WallSegment(orientation='h', coord=3.0, start=0.0, end=15.0)→WallSegment(orientation='h', coord=3.0, start=0.0, end=15.0)(Δ+0.0), WallSegment(orientation='h', coord=5.0, start=0.0, end=15.0)→MISS  | EXTRA [WallMatch(orientation='h', status='extra', truth=None, read=WallSegment(orientation='h', coord=4.2, start=0.0, end=15.0), delta=None, lateral_drift=False, extent_drift=False, extent_start_drift=False, extent_end_drift=False, pieces=[LinearPiece(kind='extra', span=(0.0, 15.0), within_tol=False)], truth_intervals=[], read_intervals=[WallSegment(orientation='h', coord=4.2, start=0.0, end=15.0)])]
  windows 0/4 hit
    N: 1.95-5.55:MISS
    S: 2.19-3.39:MISS
    E: 3.4-4.6:MISS
    W: 3.4-4.6:MISS

=== TOTAL: walls 2/9, windows 0/7 ===
```
