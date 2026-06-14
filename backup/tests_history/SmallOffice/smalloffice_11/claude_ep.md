# SmallOffice_11 — EnergyPlus IDF Planning Document

## Building Summary

| Property | Value |
|---|---|
| Test Name | SmallOffice_11 |
| Location | Shenzhen |
| Building Type | Office |
| Total Floor Area | 240 m² |
| Per-Floor Area | 120 m² |
| Number of Floors | 2 |
| Zones per Floor | 9 |
| Total Zones | 18 |
| Floor Height | 3.6 m |
| Building Dimensions | 10 m (E-W) × 12 m (N-S) |

## Building Geometry

From top-view pixel analysis:
- Left column: x=0–4 m (4 m wide)
- Central corridor: x=4–6 m (2 m wide, runs full N-S length)
- Right column: x=6–10 m (4 m wide)
- 4 rows of equal depth: 3 m each → total depth = 12 m

Coordinate system:
- x: West→East (0=west wall, 10=east wall)
- y: South→North (0=south wall, 12=north wall)
- z: ground up (Floor 1: z=0–3.6 m, Floor 2: z=3.6–7.2 m)

## Floor Plan — Per Floor

```
      0m     4m   6m     10m
 12m  +-------+---+-------+  12m  (North)
      |       |   |       |
      | ZNW   | C | ZNE   |
      | (NW)  | O | (NE)  |
  9m  +-------+ R +-------+   9m
      |       | R |       |
      | ZW2   | I | ZE2   |
      |       | D |       |
  6m  +-------+ O +-------+   6m
      |       | R |       |
      | ZW3   |   | ZE3   |
      |       |   |       |
  3m  +-------+   +-------+   3m
      |       |   |       |
      | ZSW   |   | ZSE   |
      |       |   |       |
  0m  +-------+---+-------+   0m  (South)
      0m     4m   6m     10m
```

**Naming:**
- Floor 1 (ground): Zone_F1_NW, Zone_F1_W2, Zone_F1_W3, Zone_F1_SW, Corridor_F1, Zone_F1_NE, Zone_F1_E2, Zone_F1_E3, Zone_F1_SE
- Floor 2 (upper): Zone_F2_NW, Zone_F2_W2, Zone_F2_W3, Zone_F2_SW, Corridor_F2, Zone_F2_NE, Zone_F2_E2, Zone_F2_E3, Zone_F2_SE

## Zone Coordinates Table

### Floor 1 (z = 0 m → ceiling at 3.6 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=0) |
|---|---|---|---|---|
| Zone_F1_NW | 0–4 | 9–12 | 12 | (0,9), (4,9), (4,12), (0,12) |
| Zone_F1_W2 | 0–4 | 6–9  | 12 | (0,6), (4,6), (4,9), (0,9) |
| Zone_F1_W3 | 0–4 | 3–6  | 12 | (0,3), (4,3), (4,6), (0,6) |
| Zone_F1_SW | 0–4 | 0–3  | 12 | (0,0), (4,0), (4,3), (0,3) |
| Corridor_F1 | 4–6 | 0–12 | 24 | (4,0), (6,0), (6,12), (4,12) |
| Zone_F1_NE | 6–10 | 9–12 | 12 | (6,9), (10,9), (10,12), (6,12) |
| Zone_F1_E2 | 6–10 | 6–9  | 12 | (6,6), (10,6), (10,9), (6,9) |
| Zone_F1_E3 | 6–10 | 3–6  | 12 | (6,3), (10,3), (10,6), (6,6) |
| Zone_F1_SE | 6–10 | 0–3  | 12 | (6,0), (10,0), (10,3), (6,3) |

### Floor 2 (z = 3.6 m → ceiling at 7.2 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=3.6) |
|---|---|---|---|---|
| Zone_F2_NW | 0–4 | 9–12 | 12 | (0,9,3.6), (4,9,3.6), (4,12,3.6), (0,12,3.6) |
| Zone_F2_W2 | 0–4 | 6–9  | 12 | (0,6,3.6), (4,6,3.6), (4,9,3.6), (0,9,3.6) |
| Zone_F2_W3 | 0–4 | 3–6  | 12 | (0,3,3.6), (4,3,3.6), (4,6,3.6), (0,6,3.6) |
| Zone_F2_SW | 0–4 | 0–3  | 12 | (0,0,3.6), (4,0,3.6), (4,3,3.6), (0,3,3.6) |
| Corridor_F2 | 4–6 | 0–12 | 24 | (4,0,3.6), (6,0,3.6), (6,12,3.6), (4,12,3.6) |
| Zone_F2_NE | 6–10 | 9–12 | 12 | (6,9,3.6), (10,9,3.6), (10,12,3.6), (6,12,3.6) |
| Zone_F2_E2 | 6–10 | 6–9  | 12 | (6,6,3.6), (10,6,3.6), (10,9,3.6), (6,9,3.6) |
| Zone_F2_E3 | 6–10 | 3–6  | 12 | (6,3,3.6), (10,3,3.6), (10,6,3.6), (6,6,3.6) |
| Zone_F2_SE | 6–10 | 0–3  | 12 | (6,0,3.6), (10,0,3.6), (10,3,3.6), (6,3,3.6) |

## Zone Adjacency Matrix — Floor 1

| | F1_NW | F1_W2 | F1_W3 | F1_SW | Corr_F1 | F1_NE | F1_E2 | F1_E3 | F1_SE |
|---|---|---|---|---|---|---|---|---|---|
| F1_NW  | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| F1_W2  | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| F1_W3  | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| F1_SW  | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| Corr_F1| 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 |
| F1_NE  | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| F1_E2  | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 0 |
| F1_E3  | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 |
| F1_SE  | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 |

*(Same adjacency matrix applies to Floor 2)*

## Windows

From the side view (east face): all 4 east-column rooms per floor have east-facing windows.
From the front view (south face): south-facing rooms (SW, SE) per floor have south-facing windows.
Also inferred: west-column rooms have west-facing windows (building is symmetric).
North-facing rooms (NW, NE) have north-facing windows.

Window sizing: 30% WWR (window-to-wall ratio) applied to all exterior walls with windows.
- Each office zone exterior wall: 4 m wide × 3.6 m tall → area = 14.4 m²
- Window per wall: 14.4 × 0.30 = 4.32 m² → 2.0 m wide × 2.16 m tall (sill at 0.9 m)

Corridor has no windows.

## Materials & Constructions

### Exterior Wall
- Concrete block (200 mm), insulation (50 mm), gypsum board (12.5 mm)
- Construction: Ext_Wall

### Interior Wall (between zones)
- Gypsum board (12.5 mm) + air gap + gypsum board (12.5 mm)
- Construction: Int_Wall

### Roof
- Concrete slab (150 mm), insulation (75 mm), membrane
- Construction: Roof

### Floor (Ground slab)
- Concrete slab (200 mm)
- Construction: Ground_Floor

### Ceiling/Floor (between stories)
- Concrete slab (150 mm)
- Construction: Int_Floor

### Glazing
- Double-pane (6 mm glass + 13 mm air + 6 mm glass)
- Construction: Ext_Window
