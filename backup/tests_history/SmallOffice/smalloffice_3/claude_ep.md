# SmallOffice_3 Building Analysis

## Building Overview
- **Test Name:** SmallOffice_0
- **Location:** Shenzhen
- **Floor Area:** 240m²
- **Building Type:** Office
- **Number of Floors:** 3
- **Thermal Zones per Floor:** 19
- **Total Thermal Zones:** 57

## Top View Analysis

The building has an L-shaped layout:
- **Vertical wing:** 7 rows of rooms with a central corridor
- **Horizontal wing:** Extends to the right from the bottom, with 2 rows of rooms

### Zone Layout (Per Floor)

```
         0m    2.5m   5m
    0m   +------+------+  0m
         | R1   | R2   |     Row 1 (North end)
    3m   +------+------+  3m
         | R3   | R4   |     Row 2
    6m   +------+------+  6m
         | R5   | R6   |     Row 3
    9m   +------+------+  9m
         | R7   | R8   |     Row 4
   12m   +------+------+ 12m
         | R9   | R10  |     Row 5
   15m   +------+------+ 15m
         | R11  | R12  |     Row 6
   18m   +------+------+ 18m
         | R13  | R14  |     Row 7 (corner)
   21m   +------+------+------+------+------+ 21m
         | R15  | R16  | R17  | R18  | R19  |     Horizontal wing
   24m   +------+------+------+------+------+ 24m
         0m    2.5m   5m    7.5m  10m   12.5m
```

**Zone Identification:**
- **R1-R14:** Vertical wing rooms (7 rows × 2 columns = 14 rooms)
- **R15-R19:** Horizontal wing rooms (5 rooms extending east)
- **Corridor:** The central spine running through the vertical wing serves as circulation

## Zone Matrix Chart (19 zones per floor)

| Zone | Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 | Z9 | Z10 | Z11 | Z12 | Z13 | Z14 | Z15 | Z16 | Z17 | Z18 | Z19 |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| Z1   | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z2   | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z3   | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z4   | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z5   | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z6   | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z7   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z8   | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z9   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z10  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z11  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z12  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   |
| Z13  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   |
| Z14  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1   | 0   | 1   | 0   | 0   | 0   | 0   |
| Z15  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 0   | 0   | 0   |
| Z16  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 0   | 0   |
| Z17  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 0   |
| Z18  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1   |
| Z19  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 1   | 0   |

**Legend:** 1 = adjacent zones, 0 = non-adjacent zones or the zone itself

## Building Floor Plan Diagram (Per Floor)

```
        0m       2.5m      5m
    0m  +---------+---------+ 0m
        | Zone1   | Zone2   |
        | (NW)    | (NE)    |
    3m  +---------+---------+ 3m
        | Zone3   | Zone4   |
        | (W)     | (E)     |
    6m  +---------+---------+ 6m
        | Zone5   | Zone6   |
        | (W)     | (E)     |
    9m  +---------+---------+ 9m
        | Zone7   | Zone8   |
        | (W)     | (E)     |
   12m  +---------+---------+ 12m
        | Zone9   | Zone10  |
        | (W)     | (E)     |
   15m  +---------+---------+ 15m
        | Zone11  | Zone12  |
        | (W)     | (E)     |
   18m  +---------+---------+ 18m
        | Zone13  | Zone14  |
        | (W)     | (E-Corner)|
   21m  +---------+---------+---------+---------+---------+ 21m
        | Zone15  | Zone16  | Zone17  | Zone18  | Zone19  |
        | (W)     | (W-C)   | (C)     | (E-C)   | (E)     |
   24m  +---------+---------+---------+---------+---------+ 24m
        0m       2.5m      5m       7.5m     10m      12.5m
```

**Note:** 
- Vertical wing: 14 zones (7 rows × 2 columns)
- Horizontal wing: 5 zones extending east from Zone14
- Total: 19 zones per floor

## Window Layout

Based on front and side views:
- **Front view (South elevation):** Shows 4 windows per floor - these are on the horizontal wing (Zones 15-18)
- **Side view (East elevation):** Shows 5 windows per floor - these are on the east side of vertical wing (Zones 2,4,6,8,10,12,14) and horizontal wing end (Zone19)

## Zone Naming Convention

### Floor 1 (Ground Floor)
- Zone1_F1 to Zone19_F1

### Floor 2 (Second Floor)
- Zone1_F2 to Zone19_F2

### Floor 3 (Third Floor)
- Zone1_F3 to Zone19_F3

## Construction Assumptions

- **Exterior walls:** Concrete with insulation
- **Interior walls:** Lightweight partitions between adjacent zones
- **Floor/Ceiling:** Concrete slab
- **Windows:** Double-glazed with aluminum frame
- **Roof:** Insulated concrete roof
