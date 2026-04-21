# SmallOffice_12 — EnergyPlus IDF Planning Document

## Building Summary

| Property | Value |
|---|---|
| Test Name | SmallOffice_12 |
| Location | Shenzhen |
| Building Type | Office |
| Total Floor Area | 1368 m² |
| Per-Floor Area | 456 m² |
| Number of Floors | 3 |
| Zones per Floor | 15 |
| Total Zones | 45 |
| Floor Height | 3.6 m |

## Building Geometry

From top-view analysis:
- Left column: 7 rooms (Zone1_L1 to Zone7_L7 on Floor 1), top room is larger
- Central corridor: runs full N-S length
- Right column: 7 rooms (Zone8_R1 to Zone14_R7 on Floor 1), top room is larger
- 7 rows total

Coordinate system:
- x: West→East (0=west wall, 14=east wall)
- y: South→North (0=south wall, 24=north wall)
- z: ground up (Floor 1: z=0–3.6 m, Floor 2: z=3.6–7.2 m, Floor 3: z=7.2–10.8 m)

## Floor Plan — Per Floor

```
        0m         4m    6m          14m
  24m   +----------+-----+------------+  24m  (North)
        |          |     |            |
        | Zone1_L1 |     |  Zone8_R1  |
        |          |     |            |
  20m   +----------+     +------------+  20m
        |          |     |            |
        | Zone2_L2 |     |  Zone9_R2  |
        |          |     |            |
  16.5m +----------+ C   +------------+  16.5m
        |          | O   |            |
        | Zone3_L3 | R   | Zone10_R3  |
        |          | R   |            |
  13m   +----------+ I   +------------+  13m
        |          | D   |            |
        | Zone4_L4 | O   | Zone11_R4  |
        |          | R   |            |
  9.5m  +----------+     +------------+  9.5m
        |          |     |            |
        | Zone5_L5 |     | Zone12_R5  |
        |          |     |            |
  6m    +----------+     +------------+  6m
        |          |     |            |
        | Zone6_L6 |     | Zone13_R6  |
        |          |     |            |
  2.5m  +----------+     +------------+  2.5m
        |          |     |            |
        | Zone7_L7 |     | Zone14_R7  |
        |          |     |            |
  0m    +----------+-----+------------+  0m  (South)
        0m         4m    6m          14m
```

**Naming Convention:**
- Floor 1 (ground): Zone_F1_L1, Zone_F1_L2, ..., Zone_F1_L7, Corridor_F1, Zone_F1_R1, ..., Zone_F1_R7
- Floor 2 (middle): Zone_F2_L1, Zone_F2_L2, ..., Zone_F2_L7, Corridor_F2, Zone_F2_R1, ..., Zone_F2_R7
- Floor 3 (top): Zone_F3_L1, Zone_F3_L2, ..., Zone_F3_L7, Corridor_F3, Zone_F3_R1, ..., Zone_F3_R7

## Zone Coordinates Table

### Floor 1 (z = 0 m → ceiling at 3.6 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=0) |
|---|---|---|---|---|
| Zone_F1_L1 | 0–4 | 20–24 | 16 | (0,20), (4,20), (4,24), (0,24) |
| Zone_F1_L2 | 0–4 | 16.5–20 | 14 | (0,16.5), (4,16.5), (4,20), (0,20) |
| Zone_F1_L3 | 0–4 | 13–16.5 | 14 | (0,13), (4,13), (4,16.5), (0,16.5) |
| Zone_F1_L4 | 0–4 | 9.5–13 | 14 | (0,9.5), (4,9.5), (4,13), (0,13) |
| Zone_F1_L5 | 0–4 | 6–9.5 | 14 | (0,6), (4,6), (4,9.5), (0,9.5) |
| Zone_F1_L6 | 0–4 | 2.5–6 | 14 | (0,2.5), (4,2.5), (4,6), (0,6) |
| Zone_F1_L7 | 0–4 | 0–2.5 | 10 | (0,0), (4,0), (4,2.5), (0,2.5) |
| Corridor_F1 | 4–6 | 0–24 | 48 | (4,0), (6,0), (6,24), (4,24) |
| Zone_F1_R1 | 6–14 | 20–24 | 32 | (6,20), (14,20), (14,24), (6,24) |
| Zone_F1_R2 | 6–14 | 16.5–20 | 28 | (6,16.5), (14,16.5), (14,20), (6,20) |
| Zone_F1_R3 | 6–14 | 13–16.5 | 28 | (6,13), (14,13), (14,16.5), (6,16.5) |
| Zone_F1_R4 | 6–14 | 9.5–13 | 28 | (6,9.5), (14,9.5), (14,13), (6,13) |
| Zone_F1_R5 | 6–14 | 6–9.5 | 28 | (6,6), (14,6), (14,9.5), (6,9.5) |
| Zone_F1_R6 | 6–14 | 2.5–6 | 28 | (6,2.5), (14,2.5), (14,6), (6,6) |
| Zone_F1_R7 | 6–14 | 0–2.5 | 20 | (6,0), (14,0), (14,2.5), (6,2.5) |

**Floor 1 Total Area:** 16+14×5+10 + 48 + 32+28×5+20 = 96 + 48 + 192 = 336 m²

### Floor 2 (z = 3.6 m → ceiling at 7.2 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=3.6) |
|---|---|---|---|---|
| Zone_F2_L1 | 0–4 | 20–24 | 16 | (0,20,3.6), (4,20,3.6), (4,24,3.6), (0,24,3.6) |
| Zone_F2_L2 | 0–4 | 16.5–20 | 14 | (0,16.5,3.6), (4,16.5,3.6), (4,20,3.6), (0,20,3.6) |
| Zone_F2_L3 | 0–4 | 13–16.5 | 14 | (0,13,3.6), (4,13,3.6), (4,16.5,3.6), (0,16.5,3.6) |
| Zone_F2_L4 | 0–4 | 9.5–13 | 14 | (0,9.5,3.6), (4,9.5,3.6), (4,13,3.6), (0,13,3.6) |
| Zone_F2_L5 | 0–4 | 6–9.5 | 14 | (0,6,3.6), (4,6,3.6), (4,9.5,3.6), (0,9.5,3.6) |
| Zone_F2_L6 | 0–4 | 2.5–6 | 14 | (0,2.5,3.6), (4,2.5,3.6), (4,6,3.6), (0,6,3.6) |
| Zone_F2_L7 | 0–4 | 0–2.5 | 10 | (0,0,3.6), (4,0,3.6), (4,2.5,3.6), (0,2.5,3.6) |
| Corridor_F2 | 4–6 | 0–24 | 48 | (4,0,3.6), (6,0,3.6), (6,24,3.6), (4,24,3.6) |
| Zone_F2_R1 | 6–14 | 20–24 | 32 | (6,20,3.6), (14,20,3.6), (14,24,3.6), (6,24,3.6) |
| Zone_F2_R2 | 6–14 | 16.5–20 | 28 | (6,16.5,3.6), (14,16.5,3.6), (14,20,3.6), (6,20,3.6) |
| Zone_F2_R3 | 6–14 | 13–16.5 | 28 | (6,13,3.6), (14,13,3.6), (14,16.5,3.6), (6,16.5,3.6) |
| Zone_F2_R4 | 6–14 | 9.5–13 | 28 | (6,9.5,3.6), (14,9.5,3.6), (14,13,3.6), (6,13,3.6) |
| Zone_F2_R5 | 6–14 | 6–9.5 | 28 | (6,6,3.6), (14,6,3.6), (14,9.5,3.6), (6,9.5,3.6) |
| Zone_F2_R6 | 6–14 | 2.5–6 | 28 | (6,2.5,3.6), (14,2.5,3.6), (14,6,3.6), (6,6,3.6) |
| Zone_F2_R7 | 6–14 | 0–2.5 | 20 | (6,0,3.6), (14,0,3.6), (14,2.5,3.6), (6,2.5,3.6) |

### Floor 3 (z = 7.2 m → ceiling at 10.8 m)

| Zone | x-range (m) | y-range (m) | Area (m²) | Floor Vertices (CCW, Z=7.2) |
|---|---|---|---|---|
| Zone_F3_L1 | 0–4 | 20–24 | 16 | (0,20,7.2), (4,20,7.2), (4,24,7.2), (0,24,7.2) |
| Zone_F3_L2 | 0–4 | 16.5–20 | 14 | (0,16.5,7.2), (4,16.5,7.2), (4,20,7.2), (0,20,7.2) |
| Zone_F3_L3 | 0–4 | 13–16.5 | 14 | (0,13,7.2), (4,13,7.2), (4,16.5,7.2), (0,16.5,7.2) |
| Zone_F3_L4 | 0–4 | 9.5–13 | 14 | (0,9.5,7.2), (4,9.5,7.2), (4,13,7.2), (0,13,7.2) |
| Zone_F3_L5 | 0–4 | 6–9.5 | 14 | (0,6,7.2), (4,6,7.2), (4,9.5,7.2), (0,9.5,7.2) |
| Zone_F3_L6 | 0–4 | 2.5–6 | 14 | (0,2.5,7.2), (4,2.5,7.2), (4,6,7.2), (0,6,7.2) |
| Zone_F3_L7 | 0–4 | 0–2.5 | 10 | (0,0,7.2), (4,0,7.2), (4,2.5,7.2), (0,2.5,7.2) |
| Corridor_F3 | 4–6 | 0–24 | 48 | (4,0,7.2), (6,0,7.2), (6,24,7.2), (4,24,7.2) |
| Zone_F3_R1 | 6–14 | 20–24 | 32 | (6,20,7.2), (14,20,7.2), (14,24,7.2), (6,24,7.2) |
| Zone_F3_R2 | 6–14 | 16.5–20 | 28 | (6,16.5,7.2), (14,16.5,7.2), (14,20,7.2), (6,20,7.2) |
| Zone_F3_R3 | 6–14 | 13–16.5 | 28 | (6,13,7.2), (14,13,7.2), (14,16.5,7.2), (6,16.5,7.2) |
| Zone_F3_R4 | 6–14 | 9.5–13 | 28 | (6,9.5,7.2), (14,9.5,7.2), (14,13,7.2), (6,13,7.2) |
| Zone_F3_R5 | 6–14 | 6–9.5 | 28 | (6,6,7.2), (14,6,7.2), (14,9.5,7.2), (6,9.5,7.2) |
| Zone_F3_R6 | 6–14 | 2.5–6 | 28 | (6,2.5,7.2), (14,2.5,7.2), (14,6,7.2), (6,6,7.2) |
| Zone_F3_R7 | 6–14 | 0–2.5 | 20 | (6,0,7.2), (14,0,7.2), (14,2.5,7.2), (6,2.5,7.2) |

## Zone Adjacency Matrix — Floor 1

| | L1 | L2 | L3 | L4 | L5 | L6 | L7 | Corr | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L3 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L4 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L5 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L6 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L7 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Corr | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| R1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| R2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| R3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 |
| R4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| R5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| R6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 1 |
| R7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

*(Same adjacency matrix applies to Floor 2 and Floor 3)*

## Windows

From the side view (showing windows as blue squares):
- Left column rooms (L1-L7) have west-facing windows
- Right column rooms (R1-R7) have east-facing windows
- Corridor has no windows

Window sizing: ~30% WWR applied to all exterior walls with windows.

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
