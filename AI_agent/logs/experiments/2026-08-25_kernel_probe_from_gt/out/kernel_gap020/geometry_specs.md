## zones

Zones (building-axis coordinates; values are absolute within the project building frame, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 3.60):
- Z01_F1_Office_N: x[11.06,14.88], y[18.00,19.88], z_floor=0.00, ceiling_height=3.60, role: office.
- Z02_F1_Office_NW: x[0.12,5.00], y[16.20,19.88], z_floor=0.00, ceiling_height=3.60, role: office.
- Z03_F1_Office_NW: x[5.00,9.94], y[16.20,19.88], z_floor=0.00, ceiling_height=3.60, role: office.
- Z04_F1_Office_N: x[11.06,14.88], y[16.00,18.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z05_F1_Office_N: x[11.06,14.88], y[14.00,16.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z06_F1_Office_N: x[11.06,14.88], y[12.00,14.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z07_F1_Office_NW: x[5.12,8.94], y[10.00,14.12], z_floor=0.00, ceiling_height=3.60, role: office.
- Z08_F1_Office_N: x[11.06,14.88], y[10.00,12.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z09_F1_Office_S: x[11.06,14.88], y[8.00,10.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z10_F1_Office_S: x[0.12,24.88], y[0.12,19.88], z_floor=0.00, ceiling_height=3.60, role: office.
- Z11_F1_Office_SW: x[5.12,8.94], y[5.88,10.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z12_F1_Office_S: x[11.06,14.88], y[5.88,8.00], z_floor=0.00, ceiling_height=3.60, role: office.
- Z13_F1_Office_SW: x[5.12,13.00], y[0.12,3.94], z_floor=0.00, ceiling_height=3.60, role: office.
- Z14_F1_Office_SE: x[13.00,20.94], y[0.12,3.94], z_floor=0.00, ceiling_height=3.60, role: office.

Floor 2 (z 3.60 to 7.20):
- Z15_F2_Office_NW: x[0.12,5.00], y[16.20,19.88], z_floor=3.60, ceiling_height=3.60, role: office.
- Z16_F2_Office_NW: x[5.00,9.94], y[16.20,19.88], z_floor=3.60, ceiling_height=3.60, role: office.
- Z17_F2_Office_N: x[9.94,14.88], y[16.20,19.88], z_floor=3.60, ceiling_height=3.60, role: office.
- Z18_F2_Office_N: x[11.06,14.88], y[14.00,16.20], z_floor=3.60, ceiling_height=3.60, role: office.
- Z19_F2_Office_N: x[11.06,14.88], y[12.00,14.00], z_floor=3.60, ceiling_height=3.60, role: office.
- Z20_F2_Office_N: x[11.06,14.88], y[10.00,12.00], z_floor=3.60, ceiling_height=3.60, role: office.
- Z21_F2_Office_W: x[5.12,8.94], y[5.88,14.12], z_floor=3.60, ceiling_height=3.60, role: office.
- Z22_F2_Office_SW: x[0.12,24.88], y[3.94,16.20], z_floor=3.60, ceiling_height=3.60, role: office.
- Z23_F2_Office_S: x[11.06,14.88], y[8.00,10.00], z_floor=3.60, ceiling_height=3.60, role: office.
- Z24_F2_Office_S: x[11.06,14.88], y[5.88,8.00], z_floor=3.60, ceiling_height=3.60, role: office.
- Z25_F2_Office_SW: x[5.12,9.09], y[0.12,3.94], z_floor=3.60, ceiling_height=3.60, role: office.
- Z26_F2_Office_SW: x[9.09,13.00], y[0.12,3.94], z_floor=3.60, ceiling_height=3.60, role: office.
- Z27_F2_Office_SE: x[13.00,16.91], y[0.12,3.94], z_floor=3.60, ceiling_height=3.60, role: office.
- Z28_F2_Office_SE: x[16.91,20.94], y[0.12,3.94], z_floor=3.60, ceiling_height=3.60, role: office.
- Z29_F2_Office_SE: x[20.94,24.88], y[0.12,3.94], z_floor=3.60, ceiling_height=3.60, role: office.

## surfaces

Surfaces (vertices CCW from outside, absolute building-axis coordinates (values are absolute within the project building frame) in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**Z01_F1_Office_N**:
- Z01_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_N, adjacent_surface=Z04_W3): (11.06,18.00,3.60)-(11.06,18.00,0.00)-(14.88,18.00,0.00)-(14.88,18.00,3.60)
- Z01_W2 (exterior wall, Default_Ext_Wall): (14.88,18.00,3.60)-(14.88,18.00,0.00)-(14.88,19.88,0.00)-(14.88,19.88,3.60)
- Z01_W3 (exterior wall, Default_Ext_Wall): (14.88,19.88,3.60)-(14.88,19.88,0.00)-(11.06,19.88,0.00)-(11.06,19.88,3.60)
- Z01_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W11): (11.06,19.88,3.60)-(11.06,19.88,0.00)-(11.06,18.00,0.00)-(11.06,18.00,3.60)
- Z01_Floor (ground floor, Default_GroundFloor): (11.06,18.00,0.00)-(11.06,19.88,0.00)-(14.88,19.88,0.00)-(14.88,18.00,0.00)
- Z01_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z17_F2_Office_N, adjacent_surface=Z17_Floor1): (11.06,19.88,3.60)-(11.06,18.00,3.60)-(14.88,18.00,3.60)-(14.88,19.88,3.60)

**Z02_F1_Office_NW**:
- Z02_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W15): (0.12,16.20,3.60)-(0.12,16.20,0.00)-(5.00,16.20,0.00)-(5.00,16.20,3.60)
- Z02_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_W4): (5.00,16.20,3.60)-(5.00,16.20,0.00)-(5.00,19.88,0.00)-(5.00,19.88,3.60)
- Z02_W3 (exterior wall, Default_Ext_Wall): (5.00,19.88,3.60)-(5.00,19.88,0.00)-(0.12,19.88,0.00)-(0.12,19.88,3.60)
- Z02_W4 (exterior wall, Default_Ext_Wall): (0.12,19.88,3.60)-(0.12,19.88,0.00)-(0.12,16.20,0.00)-(0.12,16.20,3.60)
- Z02_Floor (ground floor, Default_GroundFloor): (0.12,16.20,0.00)-(0.12,19.88,0.00)-(5.00,19.88,0.00)-(5.00,16.20,0.00)
- Z02_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z15_F2_Office_NW, adjacent_surface=Z15_Floor): (0.12,19.88,3.60)-(0.12,16.20,3.60)-(5.00,16.20,3.60)-(5.00,19.88,3.60)

**Z03_F1_Office_NW**:
- Z03_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W14): (5.00,16.20,3.60)-(5.00,16.20,0.00)-(9.94,16.20,0.00)-(9.94,16.20,3.60)
- Z03_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W13): (9.94,16.20,3.60)-(9.94,16.20,0.00)-(9.94,19.88,0.00)-(9.94,19.88,3.60)
- Z03_W3 (exterior wall, Default_Ext_Wall): (9.94,19.88,3.60)-(9.94,19.88,0.00)-(5.00,19.88,0.00)-(5.00,19.88,3.60)
- Z03_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_NW, adjacent_surface=Z02_W2): (5.00,19.88,3.60)-(5.00,19.88,0.00)-(5.00,16.20,0.00)-(5.00,16.20,3.60)
- Z03_Floor (ground floor, Default_GroundFloor): (5.00,16.20,0.00)-(5.00,19.88,0.00)-(9.94,19.88,0.00)-(9.94,16.20,0.00)
- Z03_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z16_F2_Office_NW, adjacent_surface=Z16_Floor): (5.00,19.88,3.60)-(5.00,16.20,3.60)-(9.94,16.20,3.60)-(9.94,19.88,3.60)

**Z04_F1_Office_N**:
- Z04_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_N, adjacent_surface=Z05_W3): (11.06,16.00,3.60)-(11.06,16.00,0.00)-(14.88,16.00,0.00)-(14.88,16.00,3.60)
- Z04_W2 (exterior wall, Default_Ext_Wall): (14.88,16.00,3.60)-(14.88,16.00,0.00)-(14.88,18.00,0.00)-(14.88,18.00,3.60)
- Z04_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_N, adjacent_surface=Z01_W1): (14.88,18.00,3.60)-(14.88,18.00,0.00)-(11.06,18.00,0.00)-(11.06,18.00,3.60)
- Z04_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W10): (11.06,18.00,3.60)-(11.06,18.00,0.00)-(11.06,16.00,0.00)-(11.06,16.00,3.60)
- Z04_Floor (ground floor, Default_GroundFloor): (11.06,16.00,0.00)-(11.06,18.00,0.00)-(14.88,18.00,0.00)-(14.88,16.00,0.00)
- Z04_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z17_F2_Office_N, adjacent_surface=Z17_Floor3): (11.06,18.00,3.60)-(11.06,16.20,3.60)-(14.88,16.20,3.60)-(14.88,18.00,3.60)
- Z04_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z18_F2_Office_N, adjacent_surface=Z18_Floor1): (11.06,16.20,3.60)-(11.06,16.00,3.60)-(14.88,16.00,3.60)-(14.88,16.20,3.60)

**Z05_F1_Office_N**:
- Z05_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_N, adjacent_surface=Z06_W3): (11.06,14.00,3.60)-(11.06,14.00,0.00)-(14.88,14.00,0.00)-(14.88,14.00,3.60)
- Z05_W2 (exterior wall, Default_Ext_Wall): (14.88,14.00,3.60)-(14.88,14.00,0.00)-(14.88,16.00,0.00)-(14.88,16.00,3.60)
- Z05_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_N, adjacent_surface=Z04_W1): (14.88,16.00,3.60)-(14.88,16.00,0.00)-(11.06,16.00,0.00)-(11.06,16.00,3.60)
- Z05_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W9): (11.06,16.00,3.60)-(11.06,16.00,0.00)-(11.06,14.00,0.00)-(11.06,14.00,3.60)
- Z05_Floor (ground floor, Default_GroundFloor): (11.06,14.00,0.00)-(11.06,16.00,0.00)-(14.88,16.00,0.00)-(14.88,14.00,0.00)
- Z05_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z18_F2_Office_N, adjacent_surface=Z18_Floor2): (11.06,16.00,3.60)-(11.06,14.00,3.60)-(14.88,14.00,3.60)-(14.88,16.00,3.60)

**Z06_F1_Office_N**:
- Z06_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_N, adjacent_surface=Z08_W3): (11.06,12.00,3.60)-(11.06,12.00,0.00)-(14.88,12.00,0.00)-(14.88,12.00,3.60)
- Z06_W2 (exterior wall, Default_Ext_Wall): (14.88,12.00,3.60)-(14.88,12.00,0.00)-(14.88,14.00,0.00)-(14.88,14.00,3.60)
- Z06_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_N, adjacent_surface=Z05_W1): (14.88,14.00,3.60)-(14.88,14.00,0.00)-(11.06,14.00,0.00)-(11.06,14.00,3.60)
- Z06_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W8): (11.06,14.00,3.60)-(11.06,14.00,0.00)-(11.06,12.00,0.00)-(11.06,12.00,3.60)
- Z06_Floor (ground floor, Default_GroundFloor): (11.06,12.00,0.00)-(11.06,14.00,0.00)-(14.88,14.00,0.00)-(14.88,12.00,0.00)
- Z06_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z19_F2_Office_N, adjacent_surface=Z19_Floor): (11.06,14.00,3.60)-(11.06,12.00,3.60)-(14.88,12.00,3.60)-(14.88,14.00,3.60)

**Z07_F1_Office_NW**:
- Z07_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F1_Office_SW, adjacent_surface=Z11_W3): (5.12,10.00,3.60)-(5.12,10.00,0.00)-(8.94,10.00,0.00)-(8.94,10.00,3.60)
- Z07_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W19): (8.94,10.00,3.60)-(8.94,10.00,0.00)-(8.94,14.12,0.00)-(8.94,14.12,3.60)
- Z07_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W18): (8.94,14.12,3.60)-(8.94,14.12,0.00)-(5.12,14.12,0.00)-(5.12,14.12,3.60)
- Z07_W4 (exterior wall, Default_Ext_Wall): (5.12,14.12,3.60)-(5.12,14.12,0.00)-(5.12,10.00,0.00)-(5.12,10.00,3.60)
- Z07_Floor (ground floor, Default_GroundFloor): (5.12,10.00,0.00)-(5.12,14.12,0.00)-(8.94,14.12,0.00)-(8.94,10.00,0.00)
- Z07_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z21_F2_Office_W, adjacent_surface=Z21_Floor1): (5.12,14.12,3.60)-(5.12,10.00,3.60)-(8.94,10.00,3.60)-(8.94,14.12,3.60)

**Z08_F1_Office_N**:
- Z08_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F1_Office_S, adjacent_surface=Z09_W3): (11.06,10.00,3.60)-(11.06,10.00,0.00)-(14.88,10.00,0.00)-(14.88,10.00,3.60)
- Z08_W2 (exterior wall, Default_Ext_Wall): (14.88,10.00,3.60)-(14.88,10.00,0.00)-(14.88,12.00,0.00)-(14.88,12.00,3.60)
- Z08_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_N, adjacent_surface=Z06_W1): (14.88,12.00,3.60)-(14.88,12.00,0.00)-(11.06,12.00,0.00)-(11.06,12.00,3.60)
- Z08_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W7): (11.06,12.00,3.60)-(11.06,12.00,0.00)-(11.06,10.00,0.00)-(11.06,10.00,3.60)
- Z08_Floor (ground floor, Default_GroundFloor): (11.06,10.00,0.00)-(11.06,12.00,0.00)-(14.88,12.00,0.00)-(14.88,10.00,0.00)
- Z08_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z20_F2_Office_N, adjacent_surface=Z20_Floor): (11.06,12.00,3.60)-(11.06,10.00,3.60)-(14.88,10.00,3.60)-(14.88,12.00,3.60)

**Z09_F1_Office_S**:
- Z09_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F1_Office_S, adjacent_surface=Z12_W3): (11.06,8.00,3.60)-(11.06,8.00,0.00)-(14.88,8.00,0.00)-(14.88,8.00,3.60)
- Z09_W2 (exterior wall, Default_Ext_Wall): (14.88,8.00,3.60)-(14.88,8.00,0.00)-(14.88,10.00,0.00)-(14.88,10.00,3.60)
- Z09_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_N, adjacent_surface=Z08_W1): (14.88,10.00,3.60)-(14.88,10.00,0.00)-(11.06,10.00,0.00)-(11.06,10.00,3.60)
- Z09_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W6): (11.06,10.00,3.60)-(11.06,10.00,0.00)-(11.06,8.00,0.00)-(11.06,8.00,3.60)
- Z09_Floor (ground floor, Default_GroundFloor): (11.06,8.00,0.00)-(11.06,10.00,0.00)-(14.88,10.00,0.00)-(14.88,8.00,0.00)
- Z09_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z23_F2_Office_S, adjacent_surface=Z23_Floor): (11.06,10.00,3.60)-(11.06,8.00,3.60)-(14.88,8.00,3.60)-(14.88,10.00,3.60)

**Z10_F1_Office_S**:
- Z10_W1 (exterior wall, Default_Ext_Wall): (20.94,0.12,3.60)-(20.94,0.12,0.00)-(24.88,0.12,0.00)-(24.88,0.12,3.60)
- Z10_W2 (exterior wall, Default_Ext_Wall): (24.88,0.12,3.60)-(24.88,0.12,0.00)-(24.88,5.88,0.00)-(24.88,5.88,3.60)
- Z10_W3 (exterior wall, Default_Ext_Wall): (24.88,5.88,3.60)-(24.88,5.88,0.00)-(14.88,5.88,0.00)-(14.88,5.88,3.60)
- Z10_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F1_Office_S, adjacent_surface=Z12_W1): (14.88,5.88,3.60)-(14.88,5.88,0.00)-(11.06,5.88,0.00)-(11.06,5.88,3.60)
- Z10_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F1_Office_S, adjacent_surface=Z12_W4): (11.06,5.88,3.60)-(11.06,5.88,0.00)-(11.06,8.00,0.00)-(11.06,8.00,3.60)
- Z10_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F1_Office_S, adjacent_surface=Z09_W4): (11.06,8.00,3.60)-(11.06,8.00,0.00)-(11.06,10.00,0.00)-(11.06,10.00,3.60)
- Z10_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_N, adjacent_surface=Z08_W4): (11.06,10.00,3.60)-(11.06,10.00,0.00)-(11.06,12.00,0.00)-(11.06,12.00,3.60)
- Z10_W8 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_N, adjacent_surface=Z06_W4): (11.06,12.00,3.60)-(11.06,12.00,0.00)-(11.06,14.00,0.00)-(11.06,14.00,3.60)
- Z10_W9 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_N, adjacent_surface=Z05_W4): (11.06,14.00,3.60)-(11.06,14.00,0.00)-(11.06,16.00,0.00)-(11.06,16.00,3.60)
- Z10_W10 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_N, adjacent_surface=Z04_W4): (11.06,16.00,3.60)-(11.06,16.00,0.00)-(11.06,18.00,0.00)-(11.06,18.00,3.60)
- Z10_W11 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_N, adjacent_surface=Z01_W4): (11.06,18.00,3.60)-(11.06,18.00,0.00)-(11.06,19.88,0.00)-(11.06,19.88,3.60)
- Z10_W12 (exterior wall, Default_Ext_Wall): (11.06,19.88,3.60)-(11.06,19.88,0.00)-(9.94,19.88,0.00)-(9.94,19.88,3.60)
- Z10_W13 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_W2): (9.94,19.88,3.60)-(9.94,19.88,0.00)-(9.94,16.20,0.00)-(9.94,16.20,3.60)
- Z10_W14 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_W1): (9.94,16.20,3.60)-(9.94,16.20,0.00)-(5.00,16.20,0.00)-(5.00,16.20,3.60)
- Z10_W15 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_NW, adjacent_surface=Z02_W1): (5.00,16.20,3.60)-(5.00,16.20,0.00)-(0.12,16.20,0.00)-(0.12,16.20,3.60)
- Z10_W16 (exterior wall, Default_Ext_Wall): (0.12,16.20,3.60)-(0.12,16.20,0.00)-(0.12,14.12,0.00)-(0.12,14.12,3.60)
- Z10_W17 (exterior wall, Default_Ext_Wall): (0.12,14.12,3.60)-(0.12,14.12,0.00)-(5.12,14.12,0.00)-(5.12,14.12,3.60)
- Z10_W18 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_NW, adjacent_surface=Z07_W3): (5.12,14.12,3.60)-(5.12,14.12,0.00)-(8.94,14.12,0.00)-(8.94,14.12,3.60)
- Z10_W19 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_NW, adjacent_surface=Z07_W2): (8.94,14.12,3.60)-(8.94,14.12,0.00)-(8.94,10.00,0.00)-(8.94,10.00,3.60)
- Z10_W20 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F1_Office_SW, adjacent_surface=Z11_W2): (8.94,10.00,3.60)-(8.94,10.00,0.00)-(8.94,5.88,0.00)-(8.94,5.88,3.60)
- Z10_W21 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F1_Office_SW, adjacent_surface=Z11_W1): (8.94,5.88,3.60)-(8.94,5.88,0.00)-(5.12,5.88,0.00)-(5.12,5.88,3.60)
- Z10_W22 (exterior wall, Default_Ext_Wall): (5.12,5.88,3.60)-(5.12,5.88,0.00)-(5.12,3.94,0.00)-(5.12,3.94,3.60)
- Z10_W23 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F1_Office_SW, adjacent_surface=Z13_W3): (5.12,3.94,3.60)-(5.12,3.94,0.00)-(13.00,3.94,0.00)-(13.00,3.94,3.60)
- Z10_W24 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F1_Office_SE, adjacent_surface=Z14_W3): (13.00,3.94,3.60)-(13.00,3.94,0.00)-(20.94,3.94,0.00)-(20.94,3.94,3.60)
- Z10_W25 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F1_Office_SE, adjacent_surface=Z14_W2): (20.94,3.94,3.60)-(20.94,3.94,0.00)-(20.94,0.12,0.00)-(20.94,0.12,3.60)
- Z10_Floor (ground floor, Default_GroundFloor): (20.94,0.12,0.00)-(11.06,5.88,0.00)-(8.94,5.88,0.00)-(5.12,3.94,0.00)-(5.12,5.88,0.00)-(0.12,14.12,0.00)-(0.12,16.20,0.00)-(8.94,14.12,0.00)-(9.94,16.20,0.00)-(9.94,19.88,0.00)-(11.06,19.88,0.00)-(24.88,5.88,0.00)-(20.94,3.94,0.00)-(24.88,0.12,0.00)
- Z10_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z17_F2_Office_N, adjacent_surface=Z17_Floor2): (9.94,19.88,3.60)-(9.94,16.20,3.60)-(11.06,16.20,3.60)-(11.06,19.88,3.60)
- Z10_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_Floor): (0.12,16.20,3.60)-(0.12,14.12,3.60)-(5.12,5.88,3.60)-(8.94,5.88,3.60)-(5.12,3.94,3.60)-(11.06,5.88,3.60)-(20.94,3.94,3.60)-(24.88,3.94,3.60)-(24.88,5.88,3.60)-(11.06,16.20,3.60)-(9.94,16.20,3.60)-(8.94,14.12,3.60)
- Z10_Ceiling3 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z29_F2_Office_SE, adjacent_surface=Z29_Floor): (20.94,3.94,3.60)-(20.94,0.12,3.60)-(24.88,0.12,3.60)-(24.88,3.94,3.60)

**Z11_F1_Office_SW**:
- Z11_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W21): (5.12,5.88,3.60)-(5.12,5.88,0.00)-(8.94,5.88,0.00)-(8.94,5.88,3.60)
- Z11_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W20): (8.94,5.88,3.60)-(8.94,5.88,0.00)-(8.94,10.00,0.00)-(8.94,10.00,3.60)
- Z11_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_NW, adjacent_surface=Z07_W1): (8.94,10.00,3.60)-(8.94,10.00,0.00)-(5.12,10.00,0.00)-(5.12,10.00,3.60)
- Z11_W4 (exterior wall, Default_Ext_Wall): (5.12,10.00,3.60)-(5.12,10.00,0.00)-(5.12,5.88,0.00)-(5.12,5.88,3.60)
- Z11_Floor (ground floor, Default_GroundFloor): (5.12,5.88,0.00)-(5.12,10.00,0.00)-(8.94,10.00,0.00)-(8.94,5.88,0.00)
- Z11_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z21_F2_Office_W, adjacent_surface=Z21_Floor2): (5.12,10.00,3.60)-(5.12,5.88,3.60)-(8.94,5.88,3.60)-(8.94,10.00,3.60)

**Z12_F1_Office_S**:
- Z12_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W4): (11.06,5.88,3.60)-(11.06,5.88,0.00)-(14.88,5.88,0.00)-(14.88,5.88,3.60)
- Z12_W2 (exterior wall, Default_Ext_Wall): (14.88,5.88,3.60)-(14.88,5.88,0.00)-(14.88,8.00,0.00)-(14.88,8.00,3.60)
- Z12_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F1_Office_S, adjacent_surface=Z09_W1): (14.88,8.00,3.60)-(14.88,8.00,0.00)-(11.06,8.00,0.00)-(11.06,8.00,3.60)
- Z12_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W5): (11.06,8.00,3.60)-(11.06,8.00,0.00)-(11.06,5.88,0.00)-(11.06,5.88,3.60)
- Z12_Floor (ground floor, Default_GroundFloor): (11.06,5.88,0.00)-(11.06,8.00,0.00)-(14.88,8.00,0.00)-(14.88,5.88,0.00)
- Z12_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z24_F2_Office_S, adjacent_surface=Z24_Floor): (11.06,8.00,3.60)-(11.06,5.88,3.60)-(14.88,5.88,3.60)-(14.88,8.00,3.60)

**Z13_F1_Office_SW**:
- Z13_W1 (exterior wall, Default_Ext_Wall): (5.12,0.12,3.60)-(5.12,0.12,0.00)-(13.00,0.12,0.00)-(13.00,0.12,3.60)
- Z13_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F1_Office_SE, adjacent_surface=Z14_W4): (13.00,0.12,3.60)-(13.00,0.12,0.00)-(13.00,3.94,0.00)-(13.00,3.94,3.60)
- Z13_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W23): (13.00,3.94,3.60)-(13.00,3.94,0.00)-(5.12,3.94,0.00)-(5.12,3.94,3.60)
- Z13_W4 (exterior wall, Default_Ext_Wall): (5.12,3.94,3.60)-(5.12,3.94,0.00)-(5.12,0.12,0.00)-(5.12,0.12,3.60)
- Z13_Floor (ground floor, Default_GroundFloor): (5.12,0.12,0.00)-(5.12,3.94,0.00)-(13.00,3.94,0.00)-(13.00,0.12,0.00)
- Z13_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z25_F2_Office_SW, adjacent_surface=Z25_Floor): (5.12,3.94,3.60)-(5.12,0.12,3.60)-(9.09,0.12,3.60)-(9.09,3.94,3.60)
- Z13_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z26_F2_Office_SW, adjacent_surface=Z26_Floor): (9.09,3.94,3.60)-(9.09,0.12,3.60)-(13.00,0.12,3.60)-(13.00,3.94,3.60)

**Z14_F1_Office_SE**:
- Z14_W1 (exterior wall, Default_Ext_Wall): (13.00,0.12,3.60)-(13.00,0.12,0.00)-(20.94,0.12,0.00)-(20.94,0.12,3.60)
- Z14_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W25): (20.94,0.12,3.60)-(20.94,0.12,0.00)-(20.94,3.94,0.00)-(20.94,3.94,3.60)
- Z14_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_W24): (20.94,3.94,3.60)-(20.94,3.94,0.00)-(13.00,3.94,0.00)-(13.00,3.94,3.60)
- Z14_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F1_Office_SW, adjacent_surface=Z13_W2): (13.00,3.94,3.60)-(13.00,3.94,0.00)-(13.00,0.12,0.00)-(13.00,0.12,3.60)
- Z14_Floor (ground floor, Default_GroundFloor): (13.00,0.12,0.00)-(13.00,3.94,0.00)-(20.94,3.94,0.00)-(20.94,0.12,0.00)
- Z14_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z27_F2_Office_SE, adjacent_surface=Z27_Floor): (13.00,3.94,3.60)-(13.00,0.12,3.60)-(16.91,0.12,3.60)-(16.91,3.94,3.60)
- Z14_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z28_F2_Office_SE, adjacent_surface=Z28_Floor): (16.91,3.94,3.60)-(16.91,0.12,3.60)-(20.94,0.12,3.60)-(20.94,3.94,3.60)

**Z15_F2_Office_NW**:
- Z15_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W16): (0.12,16.20,7.20)-(0.12,16.20,3.60)-(5.00,16.20,3.60)-(5.00,16.20,7.20)
- Z15_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z16_F2_Office_NW, adjacent_surface=Z16_W4): (5.00,16.20,7.20)-(5.00,16.20,3.60)-(5.00,19.88,3.60)-(5.00,19.88,7.20)
- Z15_W3 (exterior wall, Default_Ext_Wall): (5.00,19.88,7.20)-(5.00,19.88,3.60)-(0.12,19.88,3.60)-(0.12,19.88,7.20)
- Z15_W4 (exterior wall, Default_Ext_Wall): (0.12,19.88,7.20)-(0.12,19.88,3.60)-(0.12,16.20,3.60)-(0.12,16.20,7.20)
- Z15_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_NW, adjacent_surface=Z02_Ceiling): (0.12,16.20,3.60)-(0.12,19.88,3.60)-(5.00,19.88,3.60)-(5.00,16.20,3.60)
- Z15_Roof (roof roof, Default_Roof): (0.12,19.88,7.20)-(0.12,16.20,7.20)-(5.00,16.20,7.20)-(5.00,19.88,7.20)

**Z16_F2_Office_NW**:
- Z16_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W15): (5.00,16.20,7.20)-(5.00,16.20,3.60)-(9.94,16.20,3.60)-(9.94,16.20,7.20)
- Z16_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z17_F2_Office_N, adjacent_surface=Z17_W5): (9.94,16.20,7.20)-(9.94,16.20,3.60)-(9.94,19.88,3.60)-(9.94,19.88,7.20)
- Z16_W3 (exterior wall, Default_Ext_Wall): (9.94,19.88,7.20)-(9.94,19.88,3.60)-(5.00,19.88,3.60)-(5.00,19.88,7.20)
- Z16_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z15_F2_Office_NW, adjacent_surface=Z15_W2): (5.00,19.88,7.20)-(5.00,19.88,3.60)-(5.00,16.20,3.60)-(5.00,16.20,7.20)
- Z16_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_Ceiling): (5.00,16.20,3.60)-(5.00,19.88,3.60)-(9.94,19.88,3.60)-(9.94,16.20,3.60)
- Z16_Roof (roof roof, Default_Roof): (5.00,19.88,7.20)-(5.00,16.20,7.20)-(9.94,16.20,7.20)-(9.94,19.88,7.20)

**Z17_F2_Office_N**:
- Z17_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W14): (9.94,16.20,7.20)-(9.94,16.20,3.60)-(11.06,16.20,3.60)-(11.06,16.20,7.20)
- Z17_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z18_F2_Office_N, adjacent_surface=Z18_W3): (11.06,16.20,7.20)-(11.06,16.20,3.60)-(14.88,16.20,3.60)-(14.88,16.20,7.20)
- Z17_W3 (exterior wall, Default_Ext_Wall): (14.88,16.20,7.20)-(14.88,16.20,3.60)-(14.88,19.88,3.60)-(14.88,19.88,7.20)
- Z17_W4 (exterior wall, Default_Ext_Wall): (14.88,19.88,7.20)-(14.88,19.88,3.60)-(9.94,19.88,3.60)-(9.94,19.88,7.20)
- Z17_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z16_F2_Office_NW, adjacent_surface=Z16_W2): (9.94,19.88,7.20)-(9.94,19.88,3.60)-(9.94,16.20,3.60)-(9.94,16.20,7.20)
- Z17_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z01_F1_Office_N, adjacent_surface=Z01_Ceiling): (11.06,18.00,3.60)-(11.06,19.88,3.60)-(14.88,19.88,3.60)-(14.88,18.00,3.60)
- Z17_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_Ceiling1): (9.94,16.20,3.60)-(9.94,19.88,3.60)-(11.06,19.88,3.60)-(11.06,16.20,3.60)
- Z17_Floor3 (interzone floor, Cons_InterFloor, adjacent_zone=Z04_F1_Office_N, adjacent_surface=Z04_Ceiling1): (11.06,16.20,3.60)-(11.06,18.00,3.60)-(14.88,18.00,3.60)-(14.88,16.20,3.60)
- Z17_Roof (roof roof, Default_Roof): (9.94,19.88,7.20)-(9.94,16.20,7.20)-(14.88,16.20,7.20)-(14.88,19.88,7.20)

**Z18_F2_Office_N**:
- Z18_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z19_F2_Office_N, adjacent_surface=Z19_W3): (11.06,14.00,7.20)-(11.06,14.00,3.60)-(14.88,14.00,3.60)-(14.88,14.00,7.20)
- Z18_W2 (exterior wall, Default_Ext_Wall): (14.88,14.00,7.20)-(14.88,14.00,3.60)-(14.88,16.20,3.60)-(14.88,16.20,7.20)
- Z18_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z17_F2_Office_N, adjacent_surface=Z17_W2): (14.88,16.20,7.20)-(14.88,16.20,3.60)-(11.06,16.20,3.60)-(11.06,16.20,7.20)
- Z18_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W13): (11.06,16.20,7.20)-(11.06,16.20,3.60)-(11.06,14.00,3.60)-(11.06,14.00,7.20)
- Z18_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z04_F1_Office_N, adjacent_surface=Z04_Ceiling2): (11.06,16.00,3.60)-(11.06,16.20,3.60)-(14.88,16.20,3.60)-(14.88,16.00,3.60)
- Z18_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z05_F1_Office_N, adjacent_surface=Z05_Ceiling): (11.06,14.00,3.60)-(11.06,16.00,3.60)-(14.88,16.00,3.60)-(14.88,14.00,3.60)
- Z18_Roof (roof roof, Default_Roof): (11.06,16.20,7.20)-(11.06,14.00,7.20)-(14.88,14.00,7.20)-(14.88,16.20,7.20)

**Z19_F2_Office_N**:
- Z19_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z20_F2_Office_N, adjacent_surface=Z20_W3): (11.06,12.00,7.20)-(11.06,12.00,3.60)-(14.88,12.00,3.60)-(14.88,12.00,7.20)
- Z19_W2 (exterior wall, Default_Ext_Wall): (14.88,12.00,7.20)-(14.88,12.00,3.60)-(14.88,14.00,3.60)-(14.88,14.00,7.20)
- Z19_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z18_F2_Office_N, adjacent_surface=Z18_W1): (14.88,14.00,7.20)-(14.88,14.00,3.60)-(11.06,14.00,3.60)-(11.06,14.00,7.20)
- Z19_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W12): (11.06,14.00,7.20)-(11.06,14.00,3.60)-(11.06,12.00,3.60)-(11.06,12.00,7.20)
- Z19_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z06_F1_Office_N, adjacent_surface=Z06_Ceiling): (11.06,12.00,3.60)-(11.06,14.00,3.60)-(14.88,14.00,3.60)-(14.88,12.00,3.60)
- Z19_Roof (roof roof, Default_Roof): (11.06,14.00,7.20)-(11.06,12.00,7.20)-(14.88,12.00,7.20)-(14.88,14.00,7.20)

**Z20_F2_Office_N**:
- Z20_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z23_F2_Office_S, adjacent_surface=Z23_W3): (11.06,10.00,7.20)-(11.06,10.00,3.60)-(14.88,10.00,3.60)-(14.88,10.00,7.20)
- Z20_W2 (exterior wall, Default_Ext_Wall): (14.88,10.00,7.20)-(14.88,10.00,3.60)-(14.88,12.00,3.60)-(14.88,12.00,7.20)
- Z20_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z19_F2_Office_N, adjacent_surface=Z19_W1): (14.88,12.00,7.20)-(14.88,12.00,3.60)-(11.06,12.00,3.60)-(11.06,12.00,7.20)
- Z20_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W11): (11.06,12.00,7.20)-(11.06,12.00,3.60)-(11.06,10.00,3.60)-(11.06,10.00,7.20)
- Z20_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z08_F1_Office_N, adjacent_surface=Z08_Ceiling): (11.06,10.00,3.60)-(11.06,12.00,3.60)-(14.88,12.00,3.60)-(14.88,10.00,3.60)
- Z20_Roof (roof roof, Default_Roof): (11.06,12.00,7.20)-(11.06,10.00,7.20)-(14.88,10.00,7.20)-(14.88,12.00,7.20)

**Z21_F2_Office_W**:
- Z21_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W21): (5.12,5.88,7.20)-(5.12,5.88,3.60)-(8.94,5.88,3.60)-(8.94,5.88,7.20)
- Z21_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W20): (8.94,5.88,7.20)-(8.94,5.88,3.60)-(8.94,14.12,3.60)-(8.94,14.12,7.20)
- Z21_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W19): (8.94,14.12,7.20)-(8.94,14.12,3.60)-(5.12,14.12,3.60)-(5.12,14.12,7.20)
- Z21_W4 (exterior wall, Default_Ext_Wall): (5.12,14.12,7.20)-(5.12,14.12,3.60)-(5.12,5.88,3.60)-(5.12,5.88,7.20)
- Z21_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z07_F1_Office_NW, adjacent_surface=Z07_Ceiling): (5.12,10.00,3.60)-(5.12,14.12,3.60)-(8.94,14.12,3.60)-(8.94,10.00,3.60)
- Z21_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z11_F1_Office_SW, adjacent_surface=Z11_Ceiling): (5.12,5.88,3.60)-(5.12,10.00,3.60)-(8.94,10.00,3.60)-(8.94,5.88,3.60)
- Z21_Roof (roof roof, Default_Roof): (5.12,14.12,7.20)-(5.12,5.88,7.20)-(8.94,5.88,7.20)-(8.94,14.12,7.20)

**Z22_F2_Office_SW**:
- Z22_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z25_F2_Office_SW, adjacent_surface=Z25_W3): (5.12,3.94,7.20)-(5.12,3.94,3.60)-(9.09,3.94,3.60)-(9.09,3.94,7.20)
- Z22_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z26_F2_Office_SW, adjacent_surface=Z26_W3): (9.09,3.94,7.20)-(9.09,3.94,3.60)-(13.00,3.94,3.60)-(13.00,3.94,7.20)
- Z22_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z27_F2_Office_SE, adjacent_surface=Z27_W3): (13.00,3.94,7.20)-(13.00,3.94,3.60)-(16.91,3.94,3.60)-(16.91,3.94,7.20)
- Z22_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z28_F2_Office_SE, adjacent_surface=Z28_W3): (16.91,3.94,7.20)-(16.91,3.94,3.60)-(20.94,3.94,3.60)-(20.94,3.94,7.20)
- Z22_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z29_F2_Office_SE, adjacent_surface=Z29_W3): (20.94,3.94,7.20)-(20.94,3.94,3.60)-(24.88,3.94,3.60)-(24.88,3.94,7.20)
- Z22_W6 (exterior wall, Default_Ext_Wall): (24.88,3.94,7.20)-(24.88,3.94,3.60)-(24.88,5.88,3.60)-(24.88,5.88,7.20)
- Z22_W7 (exterior wall, Default_Ext_Wall): (24.88,5.88,7.20)-(24.88,5.88,3.60)-(14.88,5.88,3.60)-(14.88,5.88,7.20)
- Z22_W8 (interior wall, Default_Int_Wall, adjacent_zone=Z24_F2_Office_S, adjacent_surface=Z24_W1): (14.88,5.88,7.20)-(14.88,5.88,3.60)-(11.06,5.88,3.60)-(11.06,5.88,7.20)
- Z22_W9 (interior wall, Default_Int_Wall, adjacent_zone=Z24_F2_Office_S, adjacent_surface=Z24_W4): (11.06,5.88,7.20)-(11.06,5.88,3.60)-(11.06,8.00,3.60)-(11.06,8.00,7.20)
- Z22_W10 (interior wall, Default_Int_Wall, adjacent_zone=Z23_F2_Office_S, adjacent_surface=Z23_W4): (11.06,8.00,7.20)-(11.06,8.00,3.60)-(11.06,10.00,3.60)-(11.06,10.00,7.20)
- Z22_W11 (interior wall, Default_Int_Wall, adjacent_zone=Z20_F2_Office_N, adjacent_surface=Z20_W4): (11.06,10.00,7.20)-(11.06,10.00,3.60)-(11.06,12.00,3.60)-(11.06,12.00,7.20)
- Z22_W12 (interior wall, Default_Int_Wall, adjacent_zone=Z19_F2_Office_N, adjacent_surface=Z19_W4): (11.06,12.00,7.20)-(11.06,12.00,3.60)-(11.06,14.00,3.60)-(11.06,14.00,7.20)
- Z22_W13 (interior wall, Default_Int_Wall, adjacent_zone=Z18_F2_Office_N, adjacent_surface=Z18_W4): (11.06,14.00,7.20)-(11.06,14.00,3.60)-(11.06,16.20,3.60)-(11.06,16.20,7.20)
- Z22_W14 (interior wall, Default_Int_Wall, adjacent_zone=Z17_F2_Office_N, adjacent_surface=Z17_W1): (11.06,16.20,7.20)-(11.06,16.20,3.60)-(9.94,16.20,3.60)-(9.94,16.20,7.20)
- Z22_W15 (interior wall, Default_Int_Wall, adjacent_zone=Z16_F2_Office_NW, adjacent_surface=Z16_W1): (9.94,16.20,7.20)-(9.94,16.20,3.60)-(5.00,16.20,3.60)-(5.00,16.20,7.20)
- Z22_W16 (interior wall, Default_Int_Wall, adjacent_zone=Z15_F2_Office_NW, adjacent_surface=Z15_W1): (5.00,16.20,7.20)-(5.00,16.20,3.60)-(0.12,16.20,3.60)-(0.12,16.20,7.20)
- Z22_W17 (exterior wall, Default_Ext_Wall): (0.12,16.20,7.20)-(0.12,16.20,3.60)-(0.12,14.12,3.60)-(0.12,14.12,7.20)
- Z22_W18 (exterior wall, Default_Ext_Wall): (0.12,14.12,7.20)-(0.12,14.12,3.60)-(5.12,14.12,3.60)-(5.12,14.12,7.20)
- Z22_W19 (interior wall, Default_Int_Wall, adjacent_zone=Z21_F2_Office_W, adjacent_surface=Z21_W3): (5.12,14.12,7.20)-(5.12,14.12,3.60)-(8.94,14.12,3.60)-(8.94,14.12,7.20)
- Z22_W20 (interior wall, Default_Int_Wall, adjacent_zone=Z21_F2_Office_W, adjacent_surface=Z21_W2): (8.94,14.12,7.20)-(8.94,14.12,3.60)-(8.94,5.88,3.60)-(8.94,5.88,7.20)
- Z22_W21 (interior wall, Default_Int_Wall, adjacent_zone=Z21_F2_Office_W, adjacent_surface=Z21_W1): (8.94,5.88,7.20)-(8.94,5.88,3.60)-(5.12,5.88,3.60)-(5.12,5.88,7.20)
- Z22_W22 (exterior wall, Default_Ext_Wall): (5.12,5.88,7.20)-(5.12,5.88,3.60)-(5.12,3.94,3.60)-(5.12,3.94,7.20)
- Z22_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_Ceiling2): (5.12,3.94,3.60)-(5.12,5.88,3.60)-(0.12,14.12,3.60)-(0.12,16.20,3.60)-(8.94,14.12,3.60)-(9.94,16.20,3.60)-(11.06,16.20,3.60)-(24.88,5.88,3.60)-(24.88,3.94,3.60)-(20.94,3.94,3.60)-(11.06,5.88,3.60)-(8.94,5.88,3.60)
- Z22_Roof (roof roof, Default_Roof): (0.12,16.20,7.20)-(0.12,14.12,7.20)-(5.12,5.88,7.20)-(5.12,3.94,7.20)-(8.94,5.88,7.20)-(11.06,5.88,7.20)-(24.88,3.94,7.20)-(24.88,5.88,7.20)-(11.06,16.20,7.20)-(8.94,14.12,7.20)

**Z23_F2_Office_S**:
- Z23_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z24_F2_Office_S, adjacent_surface=Z24_W3): (11.06,8.00,7.20)-(11.06,8.00,3.60)-(14.88,8.00,3.60)-(14.88,8.00,7.20)
- Z23_W2 (exterior wall, Default_Ext_Wall): (14.88,8.00,7.20)-(14.88,8.00,3.60)-(14.88,10.00,3.60)-(14.88,10.00,7.20)
- Z23_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z20_F2_Office_N, adjacent_surface=Z20_W1): (14.88,10.00,7.20)-(14.88,10.00,3.60)-(11.06,10.00,3.60)-(11.06,10.00,7.20)
- Z23_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W10): (11.06,10.00,7.20)-(11.06,10.00,3.60)-(11.06,8.00,3.60)-(11.06,8.00,7.20)
- Z23_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z09_F1_Office_S, adjacent_surface=Z09_Ceiling): (11.06,8.00,3.60)-(11.06,10.00,3.60)-(14.88,10.00,3.60)-(14.88,8.00,3.60)
- Z23_Roof (roof roof, Default_Roof): (11.06,10.00,7.20)-(11.06,8.00,7.20)-(14.88,8.00,7.20)-(14.88,10.00,7.20)

**Z24_F2_Office_S**:
- Z24_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W8): (11.06,5.88,7.20)-(11.06,5.88,3.60)-(14.88,5.88,3.60)-(14.88,5.88,7.20)
- Z24_W2 (exterior wall, Default_Ext_Wall): (14.88,5.88,7.20)-(14.88,5.88,3.60)-(14.88,8.00,3.60)-(14.88,8.00,7.20)
- Z24_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z23_F2_Office_S, adjacent_surface=Z23_W1): (14.88,8.00,7.20)-(14.88,8.00,3.60)-(11.06,8.00,3.60)-(11.06,8.00,7.20)
- Z24_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W9): (11.06,8.00,7.20)-(11.06,8.00,3.60)-(11.06,5.88,3.60)-(11.06,5.88,7.20)
- Z24_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z12_F1_Office_S, adjacent_surface=Z12_Ceiling): (11.06,5.88,3.60)-(11.06,8.00,3.60)-(14.88,8.00,3.60)-(14.88,5.88,3.60)
- Z24_Roof (roof roof, Default_Roof): (11.06,8.00,7.20)-(11.06,5.88,7.20)-(14.88,5.88,7.20)-(14.88,8.00,7.20)

**Z25_F2_Office_SW**:
- Z25_W1 (exterior wall, Default_Ext_Wall): (5.12,0.12,7.20)-(5.12,0.12,3.60)-(9.09,0.12,3.60)-(9.09,0.12,7.20)
- Z25_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z26_F2_Office_SW, adjacent_surface=Z26_W4): (9.09,0.12,7.20)-(9.09,0.12,3.60)-(9.09,3.94,3.60)-(9.09,3.94,7.20)
- Z25_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W1): (9.09,3.94,7.20)-(9.09,3.94,3.60)-(5.12,3.94,3.60)-(5.12,3.94,7.20)
- Z25_W4 (exterior wall, Default_Ext_Wall): (5.12,3.94,7.20)-(5.12,3.94,3.60)-(5.12,0.12,3.60)-(5.12,0.12,7.20)
- Z25_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z13_F1_Office_SW, adjacent_surface=Z13_Ceiling1): (5.12,0.12,3.60)-(5.12,3.94,3.60)-(9.09,3.94,3.60)-(9.09,0.12,3.60)
- Z25_Roof (roof roof, Default_Roof): (5.12,3.94,7.20)-(5.12,0.12,7.20)-(9.09,0.12,7.20)-(9.09,3.94,7.20)

**Z26_F2_Office_SW**:
- Z26_W1 (exterior wall, Default_Ext_Wall): (9.09,0.12,7.20)-(9.09,0.12,3.60)-(13.00,0.12,3.60)-(13.00,0.12,7.20)
- Z26_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z27_F2_Office_SE, adjacent_surface=Z27_W4): (13.00,0.12,7.20)-(13.00,0.12,3.60)-(13.00,3.94,3.60)-(13.00,3.94,7.20)
- Z26_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W2): (13.00,3.94,7.20)-(13.00,3.94,3.60)-(9.09,3.94,3.60)-(9.09,3.94,7.20)
- Z26_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z25_F2_Office_SW, adjacent_surface=Z25_W2): (9.09,3.94,7.20)-(9.09,3.94,3.60)-(9.09,0.12,3.60)-(9.09,0.12,7.20)
- Z26_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z13_F1_Office_SW, adjacent_surface=Z13_Ceiling2): (9.09,0.12,3.60)-(9.09,3.94,3.60)-(13.00,3.94,3.60)-(13.00,0.12,3.60)
- Z26_Roof (roof roof, Default_Roof): (9.09,3.94,7.20)-(9.09,0.12,7.20)-(13.00,0.12,7.20)-(13.00,3.94,7.20)

**Z27_F2_Office_SE**:
- Z27_W1 (exterior wall, Default_Ext_Wall): (13.00,0.12,7.20)-(13.00,0.12,3.60)-(16.91,0.12,3.60)-(16.91,0.12,7.20)
- Z27_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z28_F2_Office_SE, adjacent_surface=Z28_W4): (16.91,0.12,7.20)-(16.91,0.12,3.60)-(16.91,3.94,3.60)-(16.91,3.94,7.20)
- Z27_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W3): (16.91,3.94,7.20)-(16.91,3.94,3.60)-(13.00,3.94,3.60)-(13.00,3.94,7.20)
- Z27_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z26_F2_Office_SW, adjacent_surface=Z26_W2): (13.00,3.94,7.20)-(13.00,3.94,3.60)-(13.00,0.12,3.60)-(13.00,0.12,7.20)
- Z27_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z14_F1_Office_SE, adjacent_surface=Z14_Ceiling1): (13.00,0.12,3.60)-(13.00,3.94,3.60)-(16.91,3.94,3.60)-(16.91,0.12,3.60)
- Z27_Roof (roof roof, Default_Roof): (13.00,3.94,7.20)-(13.00,0.12,7.20)-(16.91,0.12,7.20)-(16.91,3.94,7.20)

**Z28_F2_Office_SE**:
- Z28_W1 (exterior wall, Default_Ext_Wall): (16.91,0.12,7.20)-(16.91,0.12,3.60)-(20.94,0.12,3.60)-(20.94,0.12,7.20)
- Z28_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z29_F2_Office_SE, adjacent_surface=Z29_W4): (20.94,0.12,7.20)-(20.94,0.12,3.60)-(20.94,3.94,3.60)-(20.94,3.94,7.20)
- Z28_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W4): (20.94,3.94,7.20)-(20.94,3.94,3.60)-(16.91,3.94,3.60)-(16.91,3.94,7.20)
- Z28_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z27_F2_Office_SE, adjacent_surface=Z27_W2): (16.91,3.94,7.20)-(16.91,3.94,3.60)-(16.91,0.12,3.60)-(16.91,0.12,7.20)
- Z28_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z14_F1_Office_SE, adjacent_surface=Z14_Ceiling2): (16.91,0.12,3.60)-(16.91,3.94,3.60)-(20.94,3.94,3.60)-(20.94,0.12,3.60)
- Z28_Roof (roof roof, Default_Roof): (16.91,3.94,7.20)-(16.91,0.12,7.20)-(20.94,0.12,7.20)-(20.94,3.94,7.20)

**Z29_F2_Office_SE**:
- Z29_W1 (exterior wall, Default_Ext_Wall): (20.94,0.12,7.20)-(20.94,0.12,3.60)-(24.88,0.12,3.60)-(24.88,0.12,7.20)
- Z29_W2 (exterior wall, Default_Ext_Wall): (24.88,0.12,7.20)-(24.88,0.12,3.60)-(24.88,3.94,3.60)-(24.88,3.94,7.20)
- Z29_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z22_F2_Office_SW, adjacent_surface=Z22_W5): (24.88,3.94,7.20)-(24.88,3.94,3.60)-(20.94,3.94,3.60)-(20.94,3.94,7.20)
- Z29_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z28_F2_Office_SE, adjacent_surface=Z28_W2): (20.94,3.94,7.20)-(20.94,3.94,3.60)-(20.94,0.12,3.60)-(20.94,0.12,7.20)
- Z29_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z10_F1_Office_S, adjacent_surface=Z10_Ceiling3): (20.94,0.12,3.60)-(20.94,3.94,3.60)-(24.88,3.94,3.60)-(24.88,0.12,3.60)
- Z29_Roof (roof roof, Default_Roof): (20.94,3.94,7.20)-(20.94,0.12,7.20)-(24.88,0.12,7.20)-(24.88,3.94,7.20)

## fenestration

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- Z01_W2_Win1: parent=Z01_W2, source_window=gt_op_1588, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=a5ae1437d56984edeff57279e7e0e4600881ec824761e179c85694d7d72c8402, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,18.36,2.60)-(14.88,18.36,1.00)-(14.88,19.26,1.00)-(14.88,19.26,2.60)
- Z02_W3_Win1: parent=Z02_W3, source_window=gt_op_157f, segment=floor_1:facade:74f9afd7473b749caab78b93b2341b27b4596c3a733cf39ef3b21865d0ce16b8, host_proof=89e30b692720bdece2c539fb098c3d3db981e4fbcf4e5c4452ffc777bd086e90, Construction=Default_Window, z=1.00-2.60, vertices: (4.64,19.88,2.60)-(4.64,19.88,1.00)-(2.24,19.88,1.00)-(2.24,19.88,2.60)
- Z03_W3_Win1: parent=Z03_W3, source_window=gt_op_1582, segment=floor_1:facade:74f9afd7473b749caab78b93b2341b27b4596c3a733cf39ef3b21865d0ce16b8, host_proof=85f02203d33f1f3eb37a5c741b590176c9b38acafde007f7d8f1c32f5516e118, Construction=Default_Window, z=1.00-2.60, vertices: (7.76,19.88,2.60)-(7.76,19.88,1.00)-(5.36,19.88,1.00)-(5.36,19.88,2.60)
- Z04_W2_Win1: parent=Z04_W2, source_window=gt_op_158b, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=75e35d6c1ddc80bde1ecd78651aabce775881ec1071558d9dbd0e959f4a9f62a, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,16.74,2.60)-(14.88,16.74,1.00)-(14.88,17.64,1.00)-(14.88,17.64,2.60)
- Z05_W2_Win1: parent=Z05_W2, source_window=gt_op_158e, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=92b1ff2b20221eecea62ccb919ac4501c1924429c341617d0eafec3d05fdbaae, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,14.36,2.60)-(14.88,14.36,1.00)-(14.88,15.26,1.00)-(14.88,15.26,2.60)
- Z06_W2_Win1: parent=Z06_W2, source_window=gt_op_1591, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=1ae635d9bc78c3c88fb3b444c91dc3ec6252ca67f460441b8a53021a8ac34e0f, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,12.74,2.60)-(14.88,12.74,1.00)-(14.88,13.64,1.00)-(14.88,13.64,2.60)
- Z07_W4_Win1: parent=Z07_W4, source_window=gt_op_159d, segment=floor_1:facade:844579254733c651b72d7504f0c29abf2d9521e2eb6fbfca32645cf13726c2fe, host_proof=92f8f6689773b8dfed3cbfb458ca0e92e1b6d030970012664756e30ad3aefd62, Construction=Default_Window, z=1.00-2.60, vertices: (5.12,12.16,2.60)-(5.12,12.16,1.00)-(5.12,10.36,1.00)-(5.12,10.36,2.60)
- Z08_W2_Win1: parent=Z08_W2, source_window=gt_op_1594, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=bf4f218d36451141fce95b178f3f999227c4ed4637c052805be47559bc3a7c15, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,10.36,2.60)-(14.88,10.36,1.00)-(14.88,11.26,1.00)-(14.88,11.26,2.60)
- Z09_W2_Win1: parent=Z09_W2, source_window=gt_op_1597, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=ec347fe37c60451b5f989584df349728b0c96607756fce9ffcd555940500a44f, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,8.74,2.60)-(14.88,8.74,1.00)-(14.88,9.64,1.00)-(14.88,9.64,2.60)
- Z10_W3_Win1: parent=Z10_W3, source_window=gt_op_15d6, segment=floor_1:facade:2c471dfe33d10e9194997431dd55c5fc9de38868b20ff9c85319bf0443238e52, host_proof=681c6d47886a50d081562725c17e59b79a6c3e4c7f958b95f84d744d936d4f5b, Construction=Default_Window, z=1.00-3.20, vertices: (23.30,5.88,3.20)-(23.30,5.88,1.00)-(15.30,5.88,1.00)-(15.30,5.88,3.20)
- Z10_W12_Win1: parent=Z10_W12, source_window=gt_op_1585, segment=floor_1:facade:74f9afd7473b749caab78b93b2341b27b4596c3a733cf39ef3b21865d0ce16b8, host_proof=37565379db320143947d1d33d344b1135a8d9c2cb904be3372d004765d1c77c4, Construction=Default_Window, z=1.00-2.60, vertices: (10.90,19.88,2.60)-(10.90,19.88,1.00)-(10.30,19.88,1.00)-(10.30,19.88,2.60)
- Z11_W4_Win1: parent=Z11_W4, source_window=gt_op_15a0, segment=floor_1:facade:844579254733c651b72d7504f0c29abf2d9521e2eb6fbfca32645cf13726c2fe, host_proof=0e48afdb6c93ba886282c50967d552aac5f28725ecaea379826f86c55fa364b3, Construction=Default_Window, z=1.00-2.60, vertices: (5.12,9.64,2.60)-(5.12,9.64,1.00)-(5.12,7.84,1.00)-(5.12,7.84,2.60)
- Z12_W2_Win1: parent=Z12_W2, source_window=gt_op_159a, segment=floor_1:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=b03c266bad893dbde4be05c2f426073f7377b0ac0b4f6093fa799f1a7e452dc0, Construction=Default_Window, z=1.00-2.60, vertices: (14.88,6.74,2.60)-(14.88,6.74,1.00)-(14.88,7.64,1.00)-(14.88,7.64,2.60)
- Z13_W1_Win1: parent=Z13_W1, source_window=gt_op_15be, segment=floor_1:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=b11bd729d5bce8cf7730249909d182660b68f4c52fc1fee9698195190e3de88e, Construction=Default_Window, z=1.00-2.80, vertices: (8.64,0.12,2.80)-(8.64,0.12,1.00)-(12.64,0.12,1.00)-(12.64,0.12,2.80)
- Z14_W1_Win1: parent=Z14_W1, source_window=gt_op_15c1, segment=floor_1:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=6ceeaf0228300899783a47b7502f1d045c2dd982f2882dd9d5b039d5abe3860a, Construction=Default_Window, z=1.00-2.80, vertices: (13.36,0.12,2.80)-(13.36,0.12,1.00)-(17.36,0.12,1.00)-(17.36,0.12,2.80)
- Z15_W3_Win1: parent=Z15_W3, source_window=gt_op_15a3, segment=floor_2:facade:74f9afd7473b749caab78b93b2341b27b4596c3a733cf39ef3b21865d0ce16b8, host_proof=75994dc7111903f391152fe771883885c3c65273ebb64751eea7fa16682c034e, Construction=Default_Window, z=4.60-6.20, vertices: (4.64,19.88,6.20)-(4.64,19.88,4.60)-(2.24,19.88,4.60)-(2.24,19.88,6.20)
- Z16_W3_Win1: parent=Z16_W3, source_window=gt_op_15a6, segment=floor_2:facade:74f9afd7473b749caab78b93b2341b27b4596c3a733cf39ef3b21865d0ce16b8, host_proof=658b784e5ab703f6a56a1ff49f2867b5b6cbd692090a56a58b10d8ac4c0f6623, Construction=Default_Window, z=4.60-6.20, vertices: (7.76,19.88,6.20)-(7.76,19.88,4.60)-(5.36,19.88,4.60)-(5.36,19.88,6.20)
- Z17_W4_Win1: parent=Z17_W4, source_window=gt_op_15bb, segment=floor_2:facade:74f9afd7473b749caab78b93b2341b27b4596c3a733cf39ef3b21865d0ce16b8, host_proof=5ddada20e354553bcdf6474e440ff6e87deb940436e04984e9afad8edf7b309f, Construction=Default_Window, z=4.60-6.20, vertices: (10.90,19.88,6.20)-(10.90,19.88,4.60)-(10.30,19.88,4.60)-(10.30,19.88,6.20)
- Z18_W2_Win1: parent=Z18_W2, source_window=gt_op_15a9, segment=floor_2:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=315c8517c29d27a4b5b36beab1cd62af1d5da8f96f2d756073e37223007608a2, Construction=Default_Window, z=4.60-6.20, vertices: (14.88,14.36,6.20)-(14.88,14.36,4.60)-(14.88,15.26,4.60)-(14.88,15.26,6.20)
- Z19_W2_Win1: parent=Z19_W2, source_window=gt_op_15ac, segment=floor_2:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=f27be9ce530784ab2cc67185d0ddbfaf7106e7dd14f12f24e69602c848fcbde2, Construction=Default_Window, z=4.60-6.20, vertices: (14.88,12.74,6.20)-(14.88,12.74,4.60)-(14.88,13.64,4.60)-(14.88,13.64,6.20)
- Z20_W2_Win1: parent=Z20_W2, source_window=gt_op_15af, segment=floor_2:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=3581231129cb4eab7cc150a82040efed2dc48faa6586cd6c15bc5618d876a59f, Construction=Default_Window, z=4.60-6.20, vertices: (14.88,10.36,6.20)-(14.88,10.36,4.60)-(14.88,11.26,4.60)-(14.88,11.26,6.20)
- Z21_W4_Win1: parent=Z21_W4, source_window=gt_op_15b8, segment=floor_2:facade:844579254733c651b72d7504f0c29abf2d9521e2eb6fbfca32645cf13726c2fe, host_proof=60d261915e4443581ac545a045b355dec174db0ae43d5388b8a16a6ee17492e0, Construction=Default_Window, z=4.60-6.80, vertices: (5.12,12.16,6.80)-(5.12,12.16,4.60)-(5.12,7.84,4.60)-(5.12,7.84,6.80)
- Z22_W7_Win1: parent=Z22_W7, source_window=gt_op_15d9, segment=floor_2:facade:2c471dfe33d10e9194997431dd55c5fc9de38868b20ff9c85319bf0443238e52, host_proof=693cb7212fb8c5244ff03e8915e39deb488160b508c49bf093fb67c83ca7aba7, Construction=Default_Window, z=4.60-6.80, vertices: (23.30,5.88,6.80)-(23.30,5.88,4.60)-(15.30,5.88,4.60)-(15.30,5.88,6.80)
- Z22_W22_Win1: parent=Z22_W22, source_window=gt_op_15d3, segment=floor_2:facade:844579254733c651b72d7504f0c29abf2d9521e2eb6fbfca32645cf13726c2fe, host_proof=3bd99eb136144d3f4d3064398c1ca6177203b074f9b14502817fd094ee78e13b, Construction=Default_Window, z=4.60-6.20, vertices: (5.12,5.46,6.20)-(5.12,5.46,4.60)-(5.12,4.26,4.60)-(5.12,4.26,6.20)
- Z23_W2_Win1: parent=Z23_W2, source_window=gt_op_15b2, segment=floor_2:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=2782ab66d93edcf980ef8355ca277a787d9c8762d01098b23514cb2103a06edd, Construction=Default_Window, z=4.60-6.20, vertices: (14.88,8.74,6.20)-(14.88,8.74,4.60)-(14.88,9.64,4.60)-(14.88,9.64,6.20)
- Z24_W2_Win1: parent=Z24_W2, source_window=gt_op_15b5, segment=floor_2:facade:baeb58da71c34806ef3cb729d09a1176d9e47afdfbf3f2e21882546daf685d32, host_proof=1b588821570fa116aad0249b4971bb8efdc1315b40daf3a2e4916ffe386608d1, Construction=Default_Window, z=4.60-6.20, vertices: (14.88,6.74,6.20)-(14.88,6.74,4.60)-(14.88,7.64,4.60)-(14.88,7.64,6.20)
- Z25_W1_Win1: parent=Z25_W1, source_window=gt_op_15c4, segment=floor_2:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=337c839846bc6dca5bc24920d8054e2b6de7394b5ae91f1d336a7c1db6cddebb, Construction=Default_Window, z=4.60-6.20, vertices: (6.93,0.12,6.20)-(6.93,0.12,4.60)-(8.73,0.12,4.60)-(8.73,0.12,6.20)
- Z26_W1_Win1: parent=Z26_W1, source_window=gt_op_15c7, segment=floor_2:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=72c823bcf5a573ee269001888f50920e08022eec9ea77c8fdb6e1646e81e3748, Construction=Default_Window, z=4.60-6.20, vertices: (9.45,0.12,6.20)-(9.45,0.12,4.60)-(11.25,0.12,4.60)-(11.25,0.12,6.20)
- Z27_W1_Win1: parent=Z27_W1, source_window=gt_op_15ca, segment=floor_2:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=768f6e1534e0a1fe3d2801513e1deeb2920a49405315ac4773c7d0fceef6e15b, Construction=Default_Window, z=4.60-6.20, vertices: (14.75,0.12,6.20)-(14.75,0.12,4.60)-(16.55,0.12,4.60)-(16.55,0.12,6.20)
- Z28_W1_Win1: parent=Z28_W1, source_window=gt_op_15cd, segment=floor_2:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=f685f1b485c1d9da2c606126ce30f94427fd24153e48774104149054f1b5690c, Construction=Default_Window, z=4.60-6.20, vertices: (17.27,0.12,6.20)-(17.27,0.12,4.60)-(19.07,0.12,4.60)-(19.07,0.12,6.20)
- Z29_W1_Win1: parent=Z29_W1, source_window=gt_op_15d0, segment=floor_2:facade:0a6dc13ec121bff41cec668d86f1c359905b5440f0eae3947dc70ca959fd0b91, host_proof=42f31b89b9b55e74585dd4dc03ca768032b98cd947d67434b013dc9d1e8c8b0d, Construction=Default_Window, z=4.60-6.20, vertices: (21.30,0.12,6.20)-(21.30,0.12,4.60)-(23.10,0.12,4.60)-(23.10,0.12,6.20)