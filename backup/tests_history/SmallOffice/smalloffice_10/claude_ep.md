# SmallOffice_10 Building Analysis

## Building Information
- **Location**: Shenzhen (22.55°N, 114.10°E, Elevation: 4m, UTC+8)
- **Floor Area**: 240m² per floor
- **Building Type**: Office
- **Number of Floors**: 2
- **Zones per Floor**: 15
- **Total Thermal Zones**: 30

---

## Floor Plan Layout Analysis

Based on the top view image, the building has an **H-shape** layout:
- **Left (West) Wing**: 5 rooms arranged N-S in a single column (4m × 4m each)
- **Bridge (Middle)**: 5 rooms connecting the two wings E-W at the mid-level
- **Right (East) Wing**: 5 rooms arranged N-S in a single column (4m × 4m each)

**Area check:** (5+5+5) × (4×4) = 15 × 16 = 240 m² ✓
**Zone count:** 5 + 5 + 5 = 15 zones/floor ✓

**Room dimensions:** 4m (E-W) × 4m (N-S), ceiling height = 3.5m

**Building footprint:**
- E-W width: 4m (left wing) + 20m (bridge section) + 4m (right wing) = 28m
- N-S depth: 20m (5 rooms × 4m each)
- Bridge height (N-S): 4m, positioned at y=8m to y=12m (rows 3 of 5)

---

## Floor Plan Diagram (per floor)

```
     0m   4m   8m   12m  16m  20m  24m  28m
     |    |    |    |    |    |    |    |
0m   +----+                        +----+
     | WN1|                        | EN1|
4m   +----+                        +----+
     | WN2|                        | EN2|
8m   +----+----+----+----+----+----+----+
     | WM | B1 | B2 | B3 | B4 | B5 | EM |
12m  +----+----+----+----+----+----+----+
     | WS1|                        | ES1|
16m  +----+                        +----+
     | WS2|                        | ES2|
20m  +----+                        +----+
```

**Zone Key (per floor):**
| ID   | Name               | Position (x,y)      | Area  |
|------|--------------------|---------------------|-------|
| WN1  | West_North_1       | x=[0,4], y=[0,4]   | 16 m² |
| WN2  | West_North_2       | x=[0,4], y=[4,8]   | 16 m² |
| WM   | West_Mid           | x=[0,4], y=[8,12]  | 16 m² |
| WS1  | West_South_1       | x=[0,4], y=[12,16] | 16 m² |
| WS2  | West_South_2       | x=[0,4], y=[16,20] | 16 m² |
| B1   | Bridge_1           | x=[4,8], y=[8,12]  | 16 m² |
| B2   | Bridge_2           | x=[8,12], y=[8,12] | 16 m² |
| B3   | Bridge_Corridor    | x=[12,16], y=[8,12]| 16 m² |
| B4   | Bridge_4           | x=[16,20], y=[8,12]| 16 m² |
| B5   | Bridge_5           | x=[20,24], y=[8,12]| 16 m² |
| EN1  | East_North_1       | x=[24,28], y=[0,4] | 16 m² |
| EN2  | East_North_2       | x=[24,28], y=[4,8] | 16 m² |
| EM   | East_Mid           | x=[24,28], y=[8,12]| 16 m² |
| ES1  | East_South_1       | x=[24,28], y=[12,16]| 16 m²|
| ES2  | East_South_2       | x=[24,28], y=[16,20]| 16 m²|

---

## Zone Adjacency Matrix (per floor — same for Floor 1 and Floor 2)

| Zone | WN1 | WN2 | WM  | WS1 | WS2 | B1  | B2  | B3  | B4  | B5  | EN1 | EN2 | EM  | ES1 | ES2 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| WN1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| WN2  |  1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| WM   |  0  |  1  |  0  |  1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| WS1  |  0  |  0  |  1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| WS2  |  0  |  0  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| B1   |  0  |  0  |  1  |  0  |  0  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| B2   |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |
| B3   |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |  0  |
| B4   |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  1  |  0  |  0  |  0  |  0  |  0  |
| B5   |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  0  |  0  |  1  |  0  |  0  |
| EN1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  0  |  0  |
| EN2  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  1  |  0  |  0  |
| EM   |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  1  |  0  |  1  |  0  |
| ES1  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |  1  |
| ES2  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  0  |  1  |  0  |

*Note: Inter-floor adjacency (ceiling/floor between Floor 1 and Floor 2) handled via surface boundary conditions.*

---

## Zone Coordinates

### Floor 1 (z_origin = 0.0m)

| Zone Name            | x_origin | y_origin | z_origin | floor_vertices (local CCW)                                          |
|----------------------|----------|----------|----------|----------------------------------------------------------------------|
| F1_West_North_1      | 0        | 0        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_West_North_2      | 0        | 4        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_West_Mid          | 0        | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_West_South_1      | 0        | 12       | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_West_South_2      | 0        | 16       | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_Bridge_1          | 4        | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_Bridge_2          | 8        | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_Bridge_Corridor   | 12       | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_Bridge_4          | 16       | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_Bridge_5          | 20       | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_East_North_1      | 24       | 0        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_East_North_2      | 24       | 4        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_East_Mid          | 24       | 8        | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_East_South_1      | 24       | 12       | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |
| F1_East_South_2      | 24       | 16       | 0        | (0,0,0),(4,0,0),(4,4,0),(0,4,0)                                    |

### Floor 2 (z_origin = 3.5m) — same x,y coordinates, z_origin = 3.5

---

## Window Analysis

### Exterior-facing walls (true exterior exposure):
- **West wing** — West face (x=0): all 5 zones on each floor → windows on West wall
- **East wing** — East face (x=28): all 5 zones on each floor → windows on East wall
- **West wing WN1 / East wing EN1** — North face (y=0): north-most rooms → windows on North wall
- **West wing WS2 / East wing ES2** — South face (y=20): south-most rooms → windows on South wall
- **Bridge B1-B5** — North face (y=8) and South face (y=12): face internal courtyards → windows on N and S walls

### Window dimensions: 1.5m wide × 1.2m tall, sill height = 0.9m

---

## IDF Creation Plan

1. `create_location` — Shenzhen (22.55°N, 114.10°E)
2. `create_building` — SmallOffice, terrain = Suburbs
3. `create_zone` × 30 — 15 per floor, 2 floors
4. `create_standard_material` + `create_no_mass_material` — wall, floor, roof materials
5. `create_glazing_material` — window glass
6. `create_construction` × 4 — exterior wall, interior wall, roof/floor slab, window
7. Update surface boundary conditions for all zones
8. `create_fenestration_surface` — windows on exterior walls
9. `create_schedule_type_limits` + `create_schedule_compact` — occupancy, HVAC schedules
10. `create_hvac_thermostat` + `create_hvac_ideal_loads_system` — per zone
11. `create_people` + `create_light` — per zone
12. `validate_config` + `export_yaml`
