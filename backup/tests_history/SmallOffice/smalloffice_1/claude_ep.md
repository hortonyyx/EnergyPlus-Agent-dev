# SmallOffice_1 Building EnergyPlus Model

## Building Information
- **Test Name**: SmallOffice_0
- **Building Location**: Shenzhen
- **Building Type**: Office
- **Number of Floors**: 3
- **Number of Thermal Zones per Floor**: 15
- **Total Number of Thermal Zones**: 45

## Zone Matrix Charts

### Floor 1 Zone Adjacency Matrix

| Zone | Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 | Z9 | Z10 | Z11 | Z12 | Z13 | Z14 | Z15 |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|
| Z1   | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z2   | 1  | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z3   | 0  | 1  | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z4   | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z5   | 0  | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z6   | 0  | 0  | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z7   | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 1  | 0  | 0   | 0   | 0   | 0   | 0   | 0   |
| Z8   | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 1  | 1   | 0   | 0   | 0   | 0   | 0   |
| Z9   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 1   | 0   | 0   | 0   | 0   | 0   |
| Z10  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 1  | 0   | 1   | 0   | 0   | 0   | 0   |
| Z11  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1   | 0   | 1   | 0   | 0   | 0   |
| Z12  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 1   | 0   | 1   | 0   | 0   |
| Z13  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 1   | 0   | 1   | 0   |
| Z14  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1   | 0   | 1   |
| Z15  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 1   | 0   |

**Zone Layout for Floor 1:**
- Z1-Z7: West side office zones (7 zones)
- Z8: West corridor zone
- Z9-Z15: East side office zones (7 zones)

### Floor 2 Zone Adjacency Matrix
(Same as Floor 1)

### Floor 3 Zone Adjacency Matrix
(Same as Floor 1)

## Building Floor Plan Diagrams

### Floor 1 Plan (0m - 21m in Y direction, 0m - 10m in X direction)

```
     0m        5m         10m
0m   +----------+----------+ 0m
     | Zone1    | Zone9    |
     | (NW)     | (NE)     |
3m   +----------+----------+ 3m
     | Zone2    | Zone10   |
     | (W)      | (E)      |
6m   +----------+----------+ 6m
     | Zone3    | Zone11   |
     | (W)      | (E)      |
9m   +----------+----------+ 9m
     | Zone4    | Zone12   |
     | (W)      | (E)      |
12m  +----------+----------+ 12m
     | Zone5    | Zone13   |
     | (W)      | (E)      |
15m  +----------+----------+ 15m
     | Zone6    | Zone14   |
     | (W)      | (E)      |
18m  +----------+----------+ 18m
     | Zone7    | Zone15   |
     | (SW)     | (SE)     |
21m  +----------+----------+ 21m
     | Zone8    |          |
     | (Corridor)|         |
24m  +----------+----------+ 24m
     0m        5m         10m
```

### Floor 2 Plan (Same layout as Floor 1, Z elevation: 3m)

### Floor 3 Plan (Same layout as Floor 1, Z elevation: 6m)

## Zone Dimensions

Each office zone:
- Width (X): 5m
- Depth (Y): 3m
- Height: 3m
- Floor Area: 15 m²

Corridor zone (Zone8):
- Width (X): 5m
- Depth (Y): 3m
- Height: 3m
- Floor Area: 15 m²

## Window Information

Based on the side view image:
- Each floor has 7 windows per side
- Windows are located on the east and west facades
- Window dimensions: approximately 1.5m wide x 1.5m high

## Location Information

- **City**: Shenzhen, China
- **Latitude**: 22.54°N
- **Longitude**: 114.06°E
- **Time Zone**: UTC+8
- **Elevation**: 10m
