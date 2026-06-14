# smalloffice_13 — EnergyPlus Model Design

## Building Information

| Field | Value |
|---|---|
| TestName | smalloffice_13 |
| Location | Shenzhen |
| Floor Area | 240 m² (15 × 8 × 2 floors) |
| Building Type | Office |
| Number of floors | 2 |
| Number of zones per floor | 7 |
| Total zones | 14 |
| Floor height | 3.60 m (both floors) |
| Total building height | 7.20 m |

Provided facade files: South_view.png, North_view.png, East_view.png, West_view.png.
East / West elevations contain **no blue rectangles → blank on every floor** (no fenestration on those facades).

---

## Dimension Extraction

### Top view
- Overall: **15.00 m (x)** × **8.00 m (y)**
- x-segments (left→right): `5.00 | 5.00 | 5.00`     (sum = 15.00 ✓)
- y-segments (bottom→top): `3.00 | 2.00 | 3.00`     (sum = 8.00 ✓)
- Cumulative x-boundaries: `[0.00, 5.00, 10.00, 15.00]`
- Cumulative y-boundaries: `[0.00, 3.00, 5.00, 8.00]`
- Corridor strip: `y ∈ [3.00, 5.00]` is a **full-width corridor** (single zone spanning x = 0–15).
- Room strips: south strip `y ∈ [0, 3]` (3 rooms), north strip `y ∈ [5, 8]` (3 rooms).

### South facade (y = 0) — file: South_view.png
- Floor heights (top→bottom): `3.60 | 3.60`           (sum = 7.20 ✓)
- Per-floor sub-heights (top→bottom): `top_gap 0.80 | win_h 1.80 | sill_h 1.00`   (sum = 3.60 ✓)
- Window x-segments (bottom chain): `1.40 | 2.40 | 2.50 | 2.40 | 2.50 | 2.40 | 1.40`   (sum = 15.00 ✓)
- Window x-ranges: `[1.40, 3.80]`, `[6.30, 8.70]`, `[11.20, 13.60]`
- Absolute z-ranges:
  - F1 (z_floor = 0.00): sill_z = 1.00, head_z = 2.80
  - F2 (z_floor = 3.60): sill_z = 4.60, head_z = 6.40
- Three windows per floor, each aligned with one south-strip room (S1 / S2 / S3).

### North facade (y = 8) — file: North_view.png
- Floor heights (top→bottom): `3.60 | 3.60`           (sum = 7.20 ✓; matches South chain)
- Per-floor sub-heights (top→bottom): `top_gap 0.80 | win_h 1.80 | sill_h 1.00`   (sum = 3.60 ✓)
- Window x-segments (bottom chain): `1.40 | 2.40 | 2.50 | 2.40 | 2.50 | 2.40 | 1.40`   (sum = 15.00 ✓)
- Window x-ranges: `[1.40, 3.80]`, `[6.30, 8.70]`, `[11.20, 13.60]`
- Absolute z-ranges (same as South facade):
  - F1: sill_z = 1.00, head_z = 2.80
  - F2: sill_z = 4.60, head_z = 6.40
- Three windows per floor, each aligned with one north-strip room (N1 / N2 / N3).

### East facade (x = 15) — file: East_view.png → **no blue rectangles → blank on every floor**
- Floor heights chain on left: `3.60 | 3.60`          (sum = 7.20 ✓; matches South)
- No window sub-height or horizontal chain is drawn.
- No fenestration surfaces emitted for this facade.

### West facade (x = 0) — file: West_view.png → **no blue rectangles → blank on every floor**
- Floor heights chain on left: `3.60 | 3.60`          (sum = 7.20 ✓; matches South)
- No window sub-height or horizontal chain is drawn.
- No fenestration surfaces emitted for this facade.

---

## Floor Plan Diagram

Identical layout on Floor 1 and Floor 2 (Floor 2 simply has z = 3.60).

```
        0m           5m          10m          15m
8m     +------------+------------+------------+ 8m
       | Zone_F?_N1 | Zone_F?_N2 | Zone_F?_N3 |
5m     +------------+------------+------------+ 5m
       |                Zone_F?_C               |
3m     +------------+------------+------------+ 3m
       | Zone_F?_S1 | Zone_F?_S2 | Zone_F?_S3 |
0m     +------------+------------+------------+ 0m
        0m           5m          10m          15m
```

`F?` ∈ {F1, F2}.

---

## Zone Adjacency Matrix (per floor — same topology on F1 and F2)

|          | S1 | S2 | S3 | C  | N1 | N2 | N3 |
|----------|----|----|----|----|----|----|----|
| **S1**   | 0  | 1  | 0  | 1  | 0  | 0  | 0  |
| **S2**   | 1  | 0  | 1  | 1  | 0  | 0  | 0  |
| **S3**   | 0  | 1  | 0  | 1  | 0  | 0  | 0  |
| **C**    | 1  | 1  | 1  | 0  | 1  | 1  | 1  |
| **N1**   | 0  | 0  | 0  | 1  | 0  | 1  | 0  |
| **N2**   | 0  | 0  | 0  | 1  | 1  | 0  | 1  |
| **N3**   | 0  | 0  | 0  | 1  | 0  | 1  | 0  |

Inter-floor adjacency: each F1 zone shares its ceiling with the corresponding F2 zone below; these are the only cross-floor adjacencies.

---

## Zone Coordinates Table

### Floor 1 (z = 0.00 m → ceiling at 3.60 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=0) |
|---|---|---|---|---|
| Zone_F1_S1 | 0–5   | 0–3 | 15 | (0,0,0), (5,0,0), (5,3,0), (0,3,0) |
| Zone_F1_S2 | 5–10  | 0–3 | 15 | (5,0,0), (10,0,0), (10,3,0), (5,3,0) |
| Zone_F1_S3 | 10–15 | 0–3 | 15 | (10,0,0), (15,0,0), (15,3,0), (10,3,0) |
| Zone_F1_C  | 0–15  | 3–5 | 30 | (0,3,0), (15,3,0), (15,5,0), (0,5,0) |
| Zone_F1_N1 | 0–5   | 5–8 | 15 | (0,5,0), (5,5,0), (5,8,0), (0,8,0) |
| Zone_F1_N2 | 5–10  | 5–8 | 15 | (5,5,0), (10,5,0), (10,8,0), (5,8,0) |
| Zone_F1_N3 | 10–15 | 5–8 | 15 | (10,5,0), (15,5,0), (15,8,0), (10,8,0) |

Floor 1 area sum = 15 × 6 + 30 = 120 m² ✓ (matches 15 × 8).

### Floor 2 (z = 3.60 m → ceiling at 7.20 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=3.60) |
|---|---|---|---|---|
| Zone_F2_S1 | 0–5   | 0–3 | 15 | (0,0,3.60), (5,0,3.60), (5,3,3.60), (0,3,3.60) |
| Zone_F2_S2 | 5–10  | 0–3 | 15 | (5,0,3.60), (10,0,3.60), (10,3,3.60), (5,3,3.60) |
| Zone_F2_S3 | 10–15 | 0–3 | 15 | (10,0,3.60), (15,0,3.60), (15,3,3.60), (10,3,3.60) |
| Zone_F2_C  | 0–15  | 3–5 | 30 | (0,3,3.60), (15,3,3.60), (15,5,3.60), (0,5,3.60) |
| Zone_F2_N1 | 0–5   | 5–8 | 15 | (0,5,3.60), (5,5,3.60), (5,8,3.60), (0,8,3.60) |
| Zone_F2_N2 | 5–10  | 5–8 | 15 | (5,5,3.60), (10,5,3.60), (10,8,3.60), (5,8,3.60) |
| Zone_F2_N3 | 10–15 | 5–8 | 15 | (10,5,3.60), (15,5,3.60), (15,8,3.60), (10,8,3.60) |

Floor 2 area sum = 120 m² ✓.

All zones follow the `[SW, SE, NE, NW]` CCW ordering → §M7 Wall mapping applies directly:
Wall_1 = South (y = y_min), Wall_2 = East (x = x_max), Wall_3 = North (y = y_max), Wall_4 = West (x = x_min).

---

## Fenestration Table

East and West facades are blank on every floor (elevation images contain no blue rectangles).
Only South and North facades carry fenestration.

South and North windows are centered on the three south-strip / north-strip rooms; each room has at most one exterior window.

| Window ID          | Parent Zone  | Facade | Plane    | x-range (m)    | y (m) | z-range (m)  | Width × Height | Parent Wall        |
|--------------------|--------------|--------|----------|----------------|-------|--------------|----------------|--------------------|
| Win_F1_S1_South    | Zone_F1_S1   | South  | y = 0    | 1.40 – 3.80    | 0     | 1.00 – 2.80  | 2.40 × 1.80    | Zone_F1_S1_Wall_1  |
| Win_F1_S2_South    | Zone_F1_S2   | South  | y = 0    | 6.30 – 8.70    | 0     | 1.00 – 2.80  | 2.40 × 1.80    | Zone_F1_S2_Wall_1  |
| Win_F1_S3_South    | Zone_F1_S3   | South  | y = 0    | 11.20 – 13.60  | 0     | 1.00 – 2.80  | 2.40 × 1.80    | Zone_F1_S3_Wall_1  |
| Win_F1_N1_North    | Zone_F1_N1   | North  | y = 8    | 1.40 – 3.80    | 8     | 1.00 – 2.80  | 2.40 × 1.80    | Zone_F1_N1_Wall_3  |
| Win_F1_N2_North    | Zone_F1_N2   | North  | y = 8    | 6.30 – 8.70    | 8     | 1.00 – 2.80  | 2.40 × 1.80    | Zone_F1_N2_Wall_3  |
| Win_F1_N3_North    | Zone_F1_N3   | North  | y = 8    | 11.20 – 13.60  | 8     | 1.00 – 2.80  | 2.40 × 1.80    | Zone_F1_N3_Wall_3  |
| Win_F2_S1_South    | Zone_F2_S1   | South  | y = 0    | 1.40 – 3.80    | 0     | 4.60 – 6.40  | 2.40 × 1.80    | Zone_F2_S1_Wall_1  |
| Win_F2_S2_South    | Zone_F2_S2   | South  | y = 0    | 6.30 – 8.70    | 0     | 4.60 – 6.40  | 2.40 × 1.80    | Zone_F2_S2_Wall_1  |
| Win_F2_S3_South    | Zone_F2_S3   | South  | y = 0    | 11.20 – 13.60  | 0     | 4.60 – 6.40  | 2.40 × 1.80    | Zone_F2_S3_Wall_1  |
| Win_F2_N1_North    | Zone_F2_N1   | North  | y = 8    | 1.40 – 3.80    | 8     | 4.60 – 6.40  | 2.40 × 1.80    | Zone_F2_N1_Wall_3  |
| Win_F2_N2_North    | Zone_F2_N2   | North  | y = 8    | 6.30 – 8.70    | 8     | 4.60 – 6.40  | 2.40 × 1.80    | Zone_F2_N2_Wall_3  |
| Win_F2_N3_North    | Zone_F2_N3   | North  | y = 8    | 11.20 – 13.60  | 8     | 4.60 – 6.40  | 2.40 × 1.80    | Zone_F2_N3_Wall_3  |

Total = 12 fenestration surfaces.
