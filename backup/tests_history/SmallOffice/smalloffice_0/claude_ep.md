# SmallOffice_0 Zone Analysis

## Building Information
- **Test Name:** SmallOffice_0
- **Location:** Shenzhen
- **Floor Area:** 240m² (120m² per floor)
- **Building Type:** Office
- **Number of Floors:** 2
- **Thermal Zones per Floor:** 9 (8 offices + 1 corridor)
- **Total Thermal Zones:** 18

## Floor Plan Diagram - Floor 1

```
     0m        5m         10m       15m
0m   +----------+----------+----------+ 0m
     | Office1  | Corridor | Office2  |
     | (NW)     | (C)      | (NE)     |
3m   +----------+----------+----------+ 3m
     | Office3  | Corridor | Office4  |
     | (W-N)    | (C)      | (E-N)    |
6m   +----------+----------+----------+ 6m
     | Office5  | Corridor | Office6  |
     | (W-M)    | (C)      | (E-M)    |
9m   +----------+----------+----------+ 9m
     | Office7  | Corridor | Office8  |
     | (SW)     | (C)      | (SE)     |
12m  +----------+----------+----------+ 12m
     0m        5m         10m       15m
```

## Floor Plan Diagram - Floor 2

```
     0m        5m         10m       15m
0m   +----------+----------+----------+ 0m
     | Office9  | Corridor | Office10 |
     | (NW)     | (C)      | (NE)     |
3m   +----------+----------+----------+ 3m
     | Office11 | Corridor | Office12 |
     | (W-N)    | (C)      | (E-N)    |
6m   +----------+----------+----------+ 6m
     | Office13 | Corridor | Office14 |
     | (W-M)    | (C)      | (E-M)    |
9m   +----------+----------+----------+ 9m
     | Office15 | Corridor | Office16 |
     | (SW)     | (C)      | (SE)     |
12m  +----------+----------+----------+ 12m
     0m        5m         10m       15m
```

## Zone Adjacency Matrix - Floor 1

| Zone | F1_Office1 | F1_Office2 | F1_Office3 | F1_Office4 | F1_Office5 | F1_Office6 | F1_Office7 | F1_Office8 | F1_Corridor |
|------|------------|------------|------------|------------|------------|------------|------------|------------|-------------|
| F1_Office1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Office8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F1_Corridor | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |

## Zone Adjacency Matrix - Floor 2

| Zone | F2_Office9 | F2_Office10 | F2_Office11 | F2_Office12 | F2_Office13 | F2_Office14 | F2_Office15 | F2_Office16 | F2_Corridor |
|------|------------|-------------|-------------|-------------|-------------|-------------|-------------|-------------|-------------|
| F2_Office9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Office16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| F2_Corridor | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |

## Zone Dimensions

### Floor 1 Zones (z_origin = 0m, ceiling_height = 3m)
- **F1_Office1**: x=0, y=0, 5m×3m
- **F1_Office2**: x=10, y=0, 5m×3m
- **F1_Office3**: x=0, y=3, 5m×3m
- **F1_Office4**: x=10, y=3, 5m×3m
- **F1_Office5**: x=0, y=6, 5m×3m
- **F1_Office6**: x=10, y=6, 5m×3m
- **F1_Office7**: x=0, y=9, 5m×3m
- **F1_Office8**: x=10, y=9, 5m×3m
- **F1_Corridor**: x=5, y=0, 5m×12m

### Floor 2 Zones (z_origin = 3m, ceiling_height = 3m)
- **F2_Office9**: x=0, y=0, 5m×3m
- **F2_Office10**: x=10, y=0, 5m×3m
- **F2_Office11**: x=0, y=3, 5m×3m
- **F2_Office12**: x=10, y=3, 5m×3m
- **F2_Office13**: x=0, y=6, 5m×3m
- **F2_Office14**: x=10, y=6, 5m×3m
- **F2_Office15**: x=0, y=9, 5m×3m
- **F2_Office16**: x=10, y=9, 5m×3m
- **F2_Corridor**: x=5, y=0, 5m×12m

## Window Information (from side view)
- Windows visible on east and west facades
- Each office has one window
- Window size: approximately 1.5m × 1.5m
- Window position: centered on exterior wall
