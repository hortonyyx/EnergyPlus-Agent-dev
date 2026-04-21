# SmallOffice_2 Zone Analysis

## Building Information
- **Test Name:** SmallOffice_0
- **Location:** Shenzhen
- **Building Type:** Office
- **Number of Floors:** 6
- **Thermal Zones per Floor:** 13 (12 offices + 1 corridor)
- **Total Thermal Zones:** 78

## Floor Plan Diagram (All Floors Same Layout)

```
     0m        5m         10m       15m
0m   +----------+----------+----------+ 0m
     | Office1  | Corridor | Office2  |
     | (NW)     | (C)      | (NE)     |
5m   +----------+----------+----------+ 5m
     | Office3  | Corridor | Office4  |
     | (W-N)    | (C)      | (E-N)    |
10m  +----------+----------+----------+ 10m
     | Office5  | Corridor | Office6  |
     | (W-M1)   | (C)      | (E-M1)   |
15m  +----------+----------+----------+ 15m
     | Office7  | Corridor | Office8  |
     | (W-M2)   | (C)      | (E-M2)   |
20m  +----------+----------+----------+ 20m
     | Office9  | Corridor | Office10 |
     | (W-M3)   | (C)      | (E-M3)   |
25m  +----------+----------+----------+ 25m
     | Office11 | Corridor | Office12 |
     | (SW)     | (C)      | (SE)     |
30m  +----------+----------+----------+ 30m
     0m        5m         10m       15m
```

## Zone Adjacency Matrix (Per Floor)

| Zone | O1 | O2 | O3 | O4 | O5 | O6 | O7 | O8 | O9 | O10 | O11 | O12 | Corridor |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|----------|
| O1   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O2   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O3   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O4   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O5   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O6   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O7   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O8   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O9   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O10  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O11  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| O12  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1        |
| Corridor | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |

## Zone Dimensions

### Zone Sizes
- **Office Zones**: 5m × 5m = 25m² each
- **Corridor Zone**: 5m × 30m = 150m²
- **Floor Area per Floor**: 12 × 25 + 150 = 450m²
- **Ceiling Height**: 3m per floor

### Floor Z-Origins
- **Floor 1**: z_origin = 0m
- **Floor 2**: z_origin = 3m
- **Floor 3**: z_origin = 6m
- **Floor 4**: z_origin = 9m
- **Floor 5**: z_origin = 12m
- **Floor 6**: z_origin = 15m

### Zone Naming Convention
- **Floor 1**: F1_Office1, F1_Office2, ..., F1_Office12, F1_Corridor
- **Floor 2**: F2_Office1, F2_Office2, ..., F2_Office12, F2_Corridor
- **Floor 3**: F3_Office1, F3_Office2, ..., F3_Office12, F3_Corridor
- **Floor 4**: F4_Office1, F4_Office2, ..., F4_Office12, F4_Corridor
- **Floor 5**: F5_Office1, F5_Office2, ..., F5_Office12, F5_Corridor
- **Floor 6**: F6_Office1, F6_Office2, ..., F6_Office12, F6_Corridor

### Zone Coordinates (x_origin, y_origin)
| Zone | x (m) | y (m) |
|------|-------|-------|
| Office1 (NW) | 0 | 0 |
| Office2 (NE) | 10 | 0 |
| Office3 (W-N) | 0 | 5 |
| Office4 (E-N) | 10 | 5 |
| Office5 (W-M1) | 0 | 10 |
| Office6 (E-M1) | 10 | 10 |
| Office7 (W-M2) | 0 | 15 |
| Office8 (E-M2) | 10 | 15 |
| Office9 (W-M3) | 0 | 20 |
| Office10 (E-M3) | 10 | 20 |
| Office11 (SW) | 0 | 25 |
| Office12 (SE) | 10 | 25 |
| Corridor | 5 | 0 |

## Window Information (from side view)
- Windows on East and West facades
- Each office has one window
- Window size: approximately 1.5m × 1.5m
- Window position: centered on exterior wall
- 6 floors × 12 offices = 72 windows total

## Site Information
- **Location**: Shenzhen, China
- **Latitude**: 22.54°N
- **Longitude**: 114.05°E
- **Time Zone**: UTC+8
- **Elevation**: 10m
