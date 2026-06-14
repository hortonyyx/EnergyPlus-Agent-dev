# SmallOffice_4 Building Analysis

## Building Overview
- **Test Name:** SmallOffice_0
- **Location:** Shenzhen
- **Building Type:** Office
- **Number of Floors:** 3
- **Thermal Zones per Floor:** 19
- **Total Thermal Zones:** 57

## Top View Analysis

The building has an L-shaped layout:
- **Horizontal wing (top):** 6 zones across
- **Vertical wing (left):** 7 zones down
- **Middle section:** Zones connecting horizontal and vertical wings
- **Corridor:** Vertical corridor separating left column from right section

### Zone Layout (Per Floor)

```
        0m     2.5m   5m     7.5m   10m    12.5m  15m
    0m  +------+------+------+------+------+------+ 0m
        | Z1   | Z2   | Z3   | Z4   | Z5   | Z6   |    Row 1 (North)
    4m  +------+------+------+------+------+------+ 4m
        | Z7   |Corr  | Z8   | Z9   | Z10  |      |    Row 2
    8m  +------+      +------+------+------+------+ 8m
        | Z11  |Corr  | Z12  | Z13  | Z14  |      |    Row 3
   12m  +------+      +------+------+------+------+ 12m
        | Z15  |Corr  |      |      |      |      |    Row 4
   16m  +------+      +------+------+------+------+ 16m
        | Z16  |Corr  |      |      |      |      |    Row 5
   20m  +------+      +------+------+------+------+ 20m
        | Z17  |Corr  |      |      |      |      |    Row 6
   24m  +------+      +------+------+------+------+ 24m
        | Z18  |Corr  |      |      |      |      |    Row 7 (South)
   28m  +------+------+------+------+------+------+ 28m
        0m     2.5m   5m     7.5m   10m    12.5m  15m
```

**Zone Identification (19 zones per floor):**
- **Z1-Z6:** Top row (horizontal wing) - 6 zones
- **Z7, Z11, Z15, Z16, Z17, Z18:** Left column (vertical wing) - 6 zones  
- **Z8-Z10, Z12-Z14:** Middle-right section - 7 zones
- **Corridor:** One continuous vertical corridor zone - 1 zone
- **Total:** 6 + 6 + 7 + 1 = 20... 

Wait, let me recount from the image more carefully:

Looking at the top view image:
- Row 1: 6 cells
- Row 2: 6 cells (1 left + 1 corridor + 4 right)
- Row 3: 5 cells (1 left + 1 corridor + 3 right)
- Rows 4-7: 2 cells each (1 left + 1 corridor)

Total cells: 6 + 6 + 5 + 8 = 25 cells

But the JSON says 19 zones. The corridor must be ONE zone spanning rows 2-7.

**Correct count:**
- Office zones: 18 (Z1-Z18)
- Corridor: 1 (continuous)
- **Total: 19 zones per floor**

## Zone Matrix Chart (19 zones per floor)

| Zone | Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 | Z9 | Z10 | Z11 | Z12 | Z13 | Z14 | Z15 | Z16 | Z17 | Z18 | Corr |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|------|
| Z1   | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z2   | 1  | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z3   | 0  | 1  | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z4   | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0  | 0  | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z5   | 0  | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z6   | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z7   | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 1    |
| Z8   | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 1    |
| Z9   | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 1   | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z10  | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0   | 0   | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0    |
| Z11  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 0   | 0   | 1    |
| Z12  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0  | 0   | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 1    |
| Z13  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0   | 0   | 1   | 0   | 1   | 0   | 0   | 0   | 0   | 0    |
| Z14  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1   | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z15  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 1   | 0   | 0   | 0   | 0   | 1   | 0   | 0   | 1    |
| Z16  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 0   | 1    |
| Z17  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 1    |
| Z18  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1    |
| Corr | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 1  | 0  | 0   | 1   | 1   | 0   | 0   | 1   | 1   | 1   | 1   | 0    |

**Legend:** 1 = adjacent zones, 0 = non-adjacent zones or the zone itself

## Building Floor Plan Diagram (Per Floor)

```
        0m       2.5m     5m       7.5m     10m      12.5m    15m
    0m  +--------+--------+--------+--------+--------+--------+ 0m
        | Zone1  | Zone2  | Zone3  | Zone4  | Zone5  | Zone6  |
        | (NW)   | (N-1)  | (N-2)  | (N-3)  | (N-4)  | (NE)   |
    4m  +--------+--------+--------+--------+--------+--------+ 4m
        | Zone7  |Corridor| Zone8  | Zone9  | Zone10 |        |
        | (W-1)  | (C)    | (E-1)  | (E-2)  | (E-3)  |        |
    8m  +--------+        +--------+--------+--------+--------+ 8m
        | Zone11 |Corridor| Zone12 | Zone13 | Zone14 |        |
        | (W-2)  | (C)    | (E-4)  | (E-5)  | (E-6)  |        |
   12m  +--------+        +--------+--------+--------+--------+ 12m
        | Zone15 |Corridor|        |        |        |        |
        | (W-3)  | (C)    |        |        |        |        |
   16m  +--------+        +--------+--------+--------+--------+ 16m
        | Zone16 |Corridor|        |        |        |        |
        | (W-4)  | (C)    |        |        |        |        |
   20m  +--------+        +--------+--------+--------+--------+ 20m
        | Zone17 |Corridor|        |        |        |        |
        | (W-5)  | (C)    |        |        |        |        |
   24m  +--------+        +--------+--------+--------+--------+ 24m
        | Zone18 |Corridor|        |        |        |        |
        | (SW)   | (C)    |        |        |        |        |
   28m  +--------+--------+--------+--------+--------+--------+ 28m
        0m       2.5m     5m       7.5m     10m      12.5m    15m
```

**Note:** 
- **Zone dimensions:** Each zone is approximately 2.5m × 4m = 10m²
- **Corridor width:** 2.5m, length: 24m (rows 2-7)
- **Vertical wing:** Left column (Z7, Z11, Z15-Z18) + Corridor
- **Horizontal wing:** Top row (Z1-Z6)
- **Middle section:** Z8-Z10, Z12-Z14
- **Total:** 18 office zones + 1 corridor = 19 zones per floor
- **Floor Area per Floor:** 18 × 10 + 60 = 240m²
- **Total Building Area:** 240 × 3 = 720m²

## Window Layout

Based on front and side views:

### Front View (South/North Elevation)
- Shows 3 floors × 6 columns grid
- Windows (blue squares) appear in columns 4, 5, 6 (right side)
- This corresponds to Zones 4, 5, 6 on the north facade

### Side View (East/West Elevation)
- Shows 3 floors × 6 columns grid  
- Windows (blue squares) appear in columns 1, 2, 3, 4 (left side)
- This corresponds to east-facing windows

### Window Distribution per Floor:
- **North facade:** Zones 1, 2, 3, 4, 5, 6 (6 windows)
- **East facade:** Zones 6, 10, 14 (3 windows)
- **South facade:** Zone 18 (1 window)
- **West facade:** Zones 7, 11, 15, 16, 17, 18 (6 windows)

**Total windows per floor:** ~16 windows
**Total windows (3 floors):** ~48 windows

## Zone Naming Convention

### Floor 1 (Ground Floor, z=0m)
- Zone1_F1 to Zone18_F1, Corridor_F1

### Floor 2 (Second Floor, z=3m)
- Zone1_F2 to Zone18_F2, Corridor_F2

### Floor 3 (Third Floor, z=6m)
- Zone1_F3 to Zone18_F3, Corridor_F3

## Zone Dimensions and Coordinates

### Zone Sizes
- **Office Zones:** 2.5m × 4m = 10m² each
- **Corridor Zone:** 2.5m × 24m = 60m²
- **Ceiling Height:** 3m per floor

### Floor Z-Origins
- **Floor 1:** z_origin = 0m
- **Floor 2:** z_origin = 3m
- **Floor 3:** z_origin = 6m

### Zone Coordinates (x_origin, y_origin) and Floor Vertices (CCW)
| Zone | x (m) | y (m) | Floor Vertices (CCW) |
|------|-------|-------|---------------------|
| Z1   | 1.25  | 2     | [(0,0), (2.5,0), (2.5,4), (0,4)] |
| Z2   | 3.75  | 2     | [(2.5,0), (5,0), (5,4), (2.5,4)] |
| Z3   | 6.25  | 2     | [(5,0), (7.5,0), (7.5,4), (5,4)] |
| Z4   | 8.75  | 2     | [(7.5,0), (10,0), (10,4), (7.5,4)] |
| Z5   | 11.25 | 2     | [(10,0), (12.5,0), (12.5,4), (10,4)] |
| Z6   | 13.75 | 2     | [(12.5,0), (15,0), (15,4), (12.5,4)] |
| Z7   | 1.25  | 6     | [(0,4), (2.5,4), (2.5,8), (0,8)] |
| Z8   | 6.25  | 6     | [(5,4), (7.5,4), (7.5,8), (5,8)] |
| Z9   | 8.75  | 6     | [(7.5,4), (10,4), (10,8), (7.5,8)] |
| Z10  | 11.25 | 6     | [(10,4), (12.5,4), (12.5,8), (10,8)] |
| Z11  | 1.25  | 10    | [(0,8), (2.5,8), (2.5,12), (0,12)] |
| Z12  | 6.25  | 10    | [(5,8), (7.5,8), (7.5,12), (5,12)] |
| Z13  | 8.75  | 10    | [(7.5,8), (10,8), (10,12), (7.5,12)] |
| Z14  | 11.25 | 10    | [(10,8), (12.5,8), (12.5,12), (10,12)] |
| Z15  | 1.25  | 14    | [(0,12), (2.5,12), (2.5,16), (0,16)] |
| Z16  | 1.25  | 18    | [(0,16), (2.5,16), (2.5,20), (0,20)] |
| Z17  | 1.25  | 22    | [(0,20), (2.5,20), (2.5,24), (0,24)] |
| Z18  | 1.25  | 26    | [(0,24), (2.5,24), (2.5,28), (0,28)] |
| Corr | 3.75  | 16    | [(2.5,4), (5,4), (5,28), (2.5,28)] |

## Site Information
- **Location:** Shenzhen, China
- **Latitude:** 22.54°N
- **Longitude:** 114.05°E
- **Time Zone:** UTC+8
- **Elevation:** 10m

## Construction Assumptions

- **Exterior walls:** Concrete with insulation
- **Interior walls:** Lightweight partitions between adjacent zones
- **Floor/Ceiling:** Concrete slab
- **Windows:** Double-glazed
- **Roof:** Insulated concrete roof
