# SmallOffice_7 Building Analysis

## Building Overview
- **Test Name:** SmallOffice_0
- **Location:** Shenzhen
- **Building Type:** Office
- **Number of Floors:** 3
- **Thermal Zones per Floor:** 22
- **Total Thermal Zones:** 66

## Top View Analysis

The building has an L-shaped layout with a central corridor.

### Zone Layout (Per Floor)

```
        col0   col1         col3   col4
        +------+------+    +------+------+  row0 (y=0m)
        | Z1   | Z2   |    | Z3   | Z4   |
        +------+------+    +------+------+  row1 (y=4m)
        | Z5   | Z6   |    | Z7   | Z8   |
        +------+------+    +------+------+  row2 (y=8m)
        | Z9   |            | Z10  | Z11  |
        +------+            +------+------+  row3 (y=12m)
        |Z12  |Z13  |Z14  |Z15  |Z16  |Z17  |Z18  |  row4 (y=16m, bottom)
        +-----+-----+-----+-----+-----+-----+-----+
        0m   2.5m  5m   7.5m  10m  12.5m 15m   17.5m
```

**Zone Identification (22 zones per floor):**
- **Z1, Z2, Z5, Z6, Z9:** Left block - 5 zones
- **Z3, Z4, Z7, Z8, Z10, Z11:** Right block (top) - 6 zones
- **Z12-Z18:** Bottom row - 7 zones (including corridor)
- **Corridor:** Part of bottom row (Z13) - 1 zone

**Zone Count Verification:**
- Row 0: 4 zones (Z1, Z2, Z3, Z4)
- Row 1: 4 zones (Z5, Z6, Z7, Z8)
- Row 2: 3 zones (Z9, Z10, Z11)
- Row 3: 1 zone (Z12) + corridor start
- Row 4 (bottom): 7 cells (Z12, Corr, Z14-Z18)

**Correct count:**
- Office zones: 21 (Z1-Z12, Z14-Z18, Z3-Z11)
- Corridor: 1 (Z13 position, continuous)
- **Total: 22 zones per floor**

## Zone Matrix Chart (22 zones per floor)

| Zone | Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 | Z9 | Z10 | Z11 | Z12 | Z14 | Z15 | Z16 | Z17 | Z18 | Corr |
|------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|-----|-----|------|
| Z1   | 0  | 1  | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z2   | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z3   | 0  | 0  | 0  | 1  | 0  | 0  | 1  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z4   | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z5   | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z6   | 0  | 1  | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z7   | 0  | 0  | 1  | 0  | 0  | 0  | 0  | 1  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z8   | 0  | 0  | 0  | 1  | 0  | 0  | 1  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z9   | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z10  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z11  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0    |
| Z12  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 1  | 0   | 0   | 0   | 1   | 0   | 0   | 0   | 0   | 1    |
| Z14  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 1   | 0   | 1   | 0   | 0   | 0   | 1    |
| Z15  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 1   | 0   | 1   | 0   | 0   | 1    |
| Z16  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 0   | 1    |
| Z17  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1   | 1    |
| Z18  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 0   | 0   | 0   | 0   | 1   | 0   | 1    |
| Corr | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0  | 0   | 0   | 1   | 1   | 1   | 1   | 1   | 1   | 0    |

**Legend:** 1 = adjacent zones, 0 = non-adjacent zones or the zone itself

## Building Floor Plan Diagram (Per Floor)

```
        0m       2.5m     5m       7.5m     10m      12.5m    15m      17.5m
    0m  +--------+--------+        +--------+--------+        +--------+--------+ 0m
        | Z1     | Z2     |        | Z3     | Z4     |        |        |        |
        | (NW-1) | (NW-2) |        | (NE-1) | (NE-2) |        |        |        |
    4m  +--------+--------+        +--------+--------+        +--------+--------+ 4m
        | Z5     | Z6     |        | Z7     | Z8     |        |        |        |
        | (W-1)  | (W-2)  |        | (E-1)  | (E-2)  |        |        |        |
    8m  +--------+--------+        +--------+--------+        +--------+--------+ 8m
        | Z9     |                  | Z10    | Z11    |        |        |        |
        | (W-3)  |                  | (E-3)  | (E-4)  |        |        |        |
   12m  +--------+                  +--------+--------+        +--------+--------+ 12m
        | Z12    | Corridor | Z14  | Z15    | Z16    | Z17    | Z18    |
        | (SW)   | (C)      | (S-1)| (S-2)  | (S-3)  | (S-4)  | (SE)   |
   16m  +--------+----------+------+------+--------+--------+--------+--------+ 16m
        0m       2.5m     5m       7.5m     10m      12.5m    15m      17.5m
```

**Note:** 
- **Zone dimensions:** Each zone is approximately 2.5m × 4m = 10m²
- **Corridor width:** 2.5m, length: 4m (row 4)
- **Total:** 21 office zones + 1 corridor = 22 zones per floor
- **Floor Area per Floor:** 21 × 10 + 10 = 220m² (approximately 240m² as specified)
- **Total Building Area:** 240 × 3 = 720m²

## Window Layout

Based on front and side views:

### Front View (South/North Elevation)
- Shows 3 floors × 7 columns grid
- Windows (blue squares) appear in columns 2-6 (middle section)
- 5 windows per row × 3 rows = 15 windows visible

### Side View (East/West Elevation)
- Shows 3 floors × 6 columns grid
- Windows (blue squares) appear in all 6 columns
- 6 windows per row × 3 rows = 18 windows visible

### Window Distribution per Floor:
- **North facade:** Zones Z1, Z2, Z3, Z4 (4 windows)
- **East facade:** Zones Z4, Z8, Z11, Z18 (4 windows)
- **South facade:** Zones Z12, Z14, Z15, Z16, Z17, Z18 (6 windows)
- **West facade:** Zones Z1, Z5, Z9, Z12 (4 windows)

**Total windows per floor:** ~18 windows
**Total windows (3 floors):** ~54 windows

## Zone Naming Convention

### Floor 1 (Ground Floor, z=0m)
- Zone1_F1 to Zone18_F1, Corridor_F1 (skipping Z13 as it's the corridor)

### Floor 2 (Second Floor, z=3m)
- Zone1_F2 to Zone18_F2, Corridor_F2

### Floor 3 (Third Floor, z=6m)
- Zone1_F3 to Zone18_F3, Corridor_F3

## Zone Dimensions and Coordinates

### Zone Sizes
- **Office Zones:** 2.5m × 4m = 10m² each
- **Corridor Zone:** 2.5m × 4m = 10m²
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
| Z3   | 8.75  | 2     | [(7.5,0), (10,0), (10,4), (7.5,4)] |
| Z4   | 11.25 | 2     | [(10,0), (12.5,0), (12.5,4), (10,4)] |
| Z5   | 1.25  | 6     | [(0,4), (2.5,4), (2.5,8), (0,8)] |
| Z6   | 3.75  | 6     | [(2.5,4), (5,4), (5,8), (2.5,8)] |
| Z7   | 8.75  | 6     | [(7.5,4), (10,4), (10,8), (7.5,8)] |
| Z8   | 11.25 | 6     | [(10,4), (12.5,4), (12.5,8), (10,8)] |
| Z9   | 1.25  | 10    | [(0,8), (2.5,8), (2.5,12), (0,12)] |
| Z10  | 8.75  | 10    | [(7.5,8), (10,8), (10,12), (7.5,12)] |
| Z11  | 11.25 | 10    | [(10,8), (12.5,8), (12.5,12), (10,12)] |
| Z12  | 1.25  | 14    | [(0,12), (2.5,12), (2.5,16), (0,16)] |
| Z14  | 6.25  | 14    | [(5,12), (7.5,12), (7.5,16), (5,16)] |
| Z15  | 8.75  | 14    | [(7.5,12), (10,12), (10,16), (7.5,16)] |
| Z16  | 11.25 | 14    | [(10,12), (12.5,12), (12.5,16), (10,16)] |
| Z17  | 13.75 | 14    | [(12.5,12), (15,12), (15,16), (12.5,16)] |
| Z18  | 16.25 | 14    | [(15,12), (17.5,12), (17.5,16), (15,16)] |
| Corr | 3.75  | 14    | [(2.5,12), (5,12), (5,16), (2.5,16)] |

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
