# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 3.00):
- Z01_F1_Office_NW: x[0.00,5.00], y[5.00,8.00], z_floor=0.00, ceiling_height=3.00, role: office.
- Z02_F1_Office_N: x[5.00,10.00], y[5.00,8.00], z_floor=0.00, ceiling_height=3.00, role: office.
- Z03_F1_Office_NE: x[10.00,15.00], y[5.00,8.00], z_floor=0.00, ceiling_height=3.00, role: office.
- Z04_F1_Corridor_C: x[0.00,15.00], y[3.00,5.00], z_floor=0.00, ceiling_height=3.00, role: corridor.
- Z05_F1_Office_SW: x[0.00,5.00], y[0.00,3.00], z_floor=0.00, ceiling_height=3.00, role: office.
- Z06_F1_Office_S: x[5.00,10.00], y[0.00,3.00], z_floor=0.00, ceiling_height=3.00, role: office.
- Z07_F1_Office_SE: x[10.00,15.00], y[0.00,3.00], z_floor=0.00, ceiling_height=3.00, role: office.

Floor 2 (z 3.00 to 6.60):
- Z08_F2_Meeting_NW: x[0.00,7.50], y[5.00,8.00], z_floor=3.00, ceiling_height=3.60, role: meeting.
- Z09_F2_Meeting_NE: x[7.50,15.00], y[5.00,8.00], z_floor=3.00, ceiling_height=3.60, role: meeting.
- Z10_F2_Corridor_C: x[0.00,15.00], y[3.00,5.00], z_floor=3.00, ceiling_height=3.60, role: corridor.
- Z11_F2_Office_SW: x[0.00,3.75], y[0.00,3.00], z_floor=3.00, ceiling_height=3.60, role: office.
- Z12_F2_Office_SW: x[3.75,7.50], y[0.00,3.00], z_floor=3.00, ceiling_height=3.60, role: office.
- Z13_F2_Office_SE: x[7.50,11.25], y[0.00,3.00], z_floor=3.00, ceiling_height=3.60, role: office.
- Z14_F2_Office_SE: x[11.25,15.00], y[0.00,3.00], z_floor=3.00, ceiling_height=3.60, role: office.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**Z01_F1_Office_NW**:
- Z01_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W7): (0.00,5.00,3.00)-(0.00,5.00,0.00)-(5.00,5.00,0.00)-(5.00,5.00,3.00)
- Z01_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W4): (5.00,5.00,3.00)-(5.00,5.00,0.00)-(5.00,8.00,0.00)-(5.00,8.00,3.00)
- Z01_W3 (exterior wall, Default_Ext_Wall): (5.00,8.00,3.00)-(5.00,8.00,0.00)-(0.00,8.00,0.00)-(0.00,8.00,3.00)
- Z01_W4 (exterior wall, Default_Ext_Wall): (0.00,8.00,3.00)-(0.00,8.00,0.00)-(0.00,5.00,0.00)-(0.00,5.00,3.00)
- Z01_Floor (ground floor, Default_GroundFloor): (0.00,5.00,0.00)-(0.00,8.00,0.00)-(5.00,8.00,0.00)-(5.00,5.00,0.00)
- Z01_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z08_F2_Meeting_NW, adjacent_surface=Z08_Floor1): (0.00,8.00,3.00)-(0.00,5.00,3.00)-(5.00,5.00,3.00)-(5.00,8.00,3.00)

**Z02_F1_Office_N**:
- Z02_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W6): (5.00,5.00,3.00)-(5.00,5.00,0.00)-(10.00,5.00,0.00)-(10.00,5.00,3.00)
- Z02_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_W4): (10.00,5.00,3.00)-(10.00,5.00,0.00)-(10.00,8.00,0.00)-(10.00,8.00,3.00)
- Z02_W3 (exterior wall, Default_Ext_Wall): (10.00,8.00,3.00)-(10.00,8.00,0.00)-(5.00,8.00,0.00)-(5.00,8.00,3.00)
- Z02_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_W2): (5.00,8.00,3.00)-(5.00,8.00,0.00)-(5.00,5.00,0.00)-(5.00,5.00,3.00)
- Z02_Floor (ground floor, Default_GroundFloor): (5.00,5.00,0.00)-(5.00,8.00,0.00)-(10.00,8.00,0.00)-(10.00,5.00,0.00)
- Z02_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z08_F2_Meeting_NW, adjacent_surface=Z08_Floor2): (5.00,8.00,3.00)-(5.00,5.00,3.00)-(7.50,5.00,3.00)-(7.50,8.00,3.00)
- Z02_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z09_F2_Meeting_NE, adjacent_surface=Z09_Floor1): (7.50,8.00,3.00)-(7.50,5.00,3.00)-(10.00,5.00,3.00)-(10.00,8.00,3.00)

**Z03_F1_Office_NE**:
- Z03_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W5): (10.00,5.00,3.00)-(10.00,5.00,0.00)-(15.00,5.00,0.00)-(15.00,5.00,3.00)
- Z03_W2 (exterior wall, Default_Ext_Wall): (15.00,5.00,3.00)-(15.00,5.00,0.00)-(15.00,8.00,0.00)-(15.00,8.00,3.00)
- Z03_W3 (exterior wall, Default_Ext_Wall): (15.00,8.00,3.00)-(15.00,8.00,0.00)-(10.00,8.00,0.00)-(10.00,8.00,3.00)
- Z03_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W2): (10.00,8.00,3.00)-(10.00,8.00,0.00)-(10.00,5.00,0.00)-(10.00,5.00,3.00)
- Z03_Floor (ground floor, Default_GroundFloor): (10.00,5.00,0.00)-(10.00,8.00,0.00)-(15.00,8.00,0.00)-(15.00,5.00,0.00)
- Z03_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z09_F2_Meeting_NE, adjacent_surface=Z09_Floor2): (10.00,8.00,3.00)-(10.00,5.00,3.00)-(15.00,5.00,3.00)-(15.00,8.00,3.00)

**Z04_F1_Corridor_C**:
- Z04_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_W3): (0.00,3.00,3.00)-(0.00,3.00,0.00)-(5.00,3.00,0.00)-(5.00,3.00,3.00)
- Z04_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_W3): (5.00,3.00,3.00)-(5.00,3.00,0.00)-(10.00,3.00,0.00)-(10.00,3.00,3.00)
- Z04_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W3): (10.00,3.00,3.00)-(10.00,3.00,0.00)-(15.00,3.00,0.00)-(15.00,3.00,3.00)
- Z04_W4 (exterior wall, Default_Ext_Wall): (15.00,3.00,3.00)-(15.00,3.00,0.00)-(15.00,5.00,0.00)-(15.00,5.00,3.00)
- Z04_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_W1): (15.00,5.00,3.00)-(15.00,5.00,0.00)-(10.00,5.00,0.00)-(10.00,5.00,3.00)
- Z04_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W1): (10.00,5.00,3.00)-(10.00,5.00,0.00)-(5.00,5.00,0.00)-(5.00,5.00,3.00)
- Z04_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_W1): (5.00,5.00,3.00)-(5.00,5.00,0.00)-(0.00,5.00,0.00)-(0.00,5.00,3.00)
- Z04_W8 (exterior wall, Default_Ext_Wall): (0.00,5.00,3.00)-(0.00,5.00,0.00)-(0.00,3.00,0.00)-(0.00,3.00,3.00)
- Z04_Floor (ground floor, Default_GroundFloor): (0.00,3.00,0.00)-(0.00,5.00,0.00)-(15.00,5.00,0.00)-(15.00,3.00,0.00)
- Z04_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_Floor): (0.00,5.00,3.00)-(0.00,3.00,3.00)-(15.00,3.00,3.00)-(15.00,5.00,3.00)

**Z05_F1_Office_SW**:
- Z05_W1 (exterior wall, Default_Ext_Wall): (0.00,0.00,3.00)-(0.00,0.00,0.00)-(5.00,0.00,0.00)-(5.00,0.00,3.00)
- Z05_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_W4): (5.00,0.00,3.00)-(5.00,0.00,0.00)-(5.00,3.00,0.00)-(5.00,3.00,3.00)
- Z05_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W1): (5.00,3.00,3.00)-(5.00,3.00,0.00)-(0.00,3.00,0.00)-(0.00,3.00,3.00)
- Z05_W4 (exterior wall, Default_Ext_Wall): (0.00,3.00,3.00)-(0.00,3.00,0.00)-(0.00,0.00,0.00)-(0.00,0.00,3.00)
- Z05_Floor (ground floor, Default_GroundFloor): (0.00,0.00,0.00)-(0.00,3.00,0.00)-(5.00,3.00,0.00)-(5.00,0.00,0.00)
- Z05_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_Floor): (0.00,3.00,3.00)-(0.00,0.00,3.00)-(3.75,0.00,3.00)-(3.75,3.00,3.00)
- Z05_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_Floor1): (3.75,3.00,3.00)-(3.75,0.00,3.00)-(5.00,0.00,3.00)-(5.00,3.00,3.00)

**Z06_F1_Office_S**:
- Z06_W1 (exterior wall, Default_Ext_Wall): (5.00,0.00,3.00)-(5.00,0.00,0.00)-(10.00,0.00,0.00)-(10.00,0.00,3.00)
- Z06_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W4): (10.00,0.00,3.00)-(10.00,0.00,0.00)-(10.00,3.00,0.00)-(10.00,3.00,3.00)
- Z06_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W2): (10.00,3.00,3.00)-(10.00,3.00,0.00)-(5.00,3.00,0.00)-(5.00,3.00,3.00)
- Z06_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_W2): (5.00,3.00,3.00)-(5.00,3.00,0.00)-(5.00,0.00,0.00)-(5.00,0.00,3.00)
- Z06_Floor (ground floor, Default_GroundFloor): (5.00,0.00,0.00)-(5.00,3.00,0.00)-(10.00,3.00,0.00)-(10.00,0.00,0.00)
- Z06_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_Floor2): (5.00,3.00,3.00)-(5.00,0.00,3.00)-(7.50,0.00,3.00)-(7.50,3.00,3.00)
- Z06_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_Floor1): (7.50,3.00,3.00)-(7.50,0.00,3.00)-(10.00,0.00,3.00)-(10.00,3.00,3.00)

**Z07_F1_Office_SE**:
- Z07_W1 (exterior wall, Default_Ext_Wall): (10.00,0.00,3.00)-(10.00,0.00,0.00)-(15.00,0.00,0.00)-(15.00,0.00,3.00)
- Z07_W2 (exterior wall, Default_Ext_Wall): (15.00,0.00,3.00)-(15.00,0.00,0.00)-(15.00,3.00,0.00)-(15.00,3.00,3.00)
- Z07_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W3): (15.00,3.00,3.00)-(15.00,3.00,0.00)-(10.00,3.00,0.00)-(10.00,3.00,3.00)
- Z07_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_W2): (10.00,3.00,3.00)-(10.00,3.00,0.00)-(10.00,0.00,0.00)-(10.00,0.00,3.00)
- Z07_Floor (ground floor, Default_GroundFloor): (10.00,0.00,0.00)-(10.00,3.00,0.00)-(15.00,3.00,0.00)-(15.00,0.00,0.00)
- Z07_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_Floor2): (10.00,3.00,3.00)-(10.00,0.00,3.00)-(11.25,0.00,3.00)-(11.25,3.00,3.00)
- Z07_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_Floor): (11.25,3.00,3.00)-(11.25,0.00,3.00)-(15.00,0.00,3.00)-(15.00,3.00,3.00)

**Z08_F2_Meeting_NW**:
- Z08_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W7): (0.00,5.00,6.60)-(0.00,5.00,3.00)-(7.50,5.00,3.00)-(7.50,5.00,6.60)
- Z08_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F2_Meeting_NE, adjacent_surface=Z09_W4): (7.50,5.00,6.60)-(7.50,5.00,3.00)-(7.50,8.00,3.00)-(7.50,8.00,6.60)
- Z08_W3 (exterior wall, Default_Ext_Wall): (7.50,8.00,6.60)-(7.50,8.00,3.00)-(0.00,8.00,3.00)-(0.00,8.00,6.60)
- Z08_W4 (exterior wall, Default_Ext_Wall): (0.00,8.00,6.60)-(0.00,8.00,3.00)-(0.00,5.00,3.00)-(0.00,5.00,6.60)
- Z08_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_Ceiling): (0.00,5.00,3.00)-(0.00,8.00,3.00)-(5.00,8.00,3.00)-(5.00,5.00,3.00)
- Z08_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_Ceiling1): (5.00,5.00,3.00)-(5.00,8.00,3.00)-(7.50,8.00,3.00)-(7.50,5.00,3.00)
- Z08_Roof (roof roof, Default_Roof): (0.00,8.00,6.60)-(0.00,5.00,6.60)-(7.50,5.00,6.60)-(7.50,8.00,6.60)

**Z09_F2_Meeting_NE**:
- Z09_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W6): (7.50,5.00,6.60)-(7.50,5.00,3.00)-(15.00,5.00,3.00)-(15.00,5.00,6.60)
- Z09_W2 (exterior wall, Default_Ext_Wall): (15.00,5.00,6.60)-(15.00,5.00,3.00)-(15.00,8.00,3.00)-(15.00,8.00,6.60)
- Z09_W3 (exterior wall, Default_Ext_Wall): (15.00,8.00,6.60)-(15.00,8.00,3.00)-(7.50,8.00,3.00)-(7.50,8.00,6.60)
- Z09_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F2_Meeting_NW, adjacent_surface=Z08_W2): (7.50,8.00,6.60)-(7.50,8.00,3.00)-(7.50,5.00,3.00)-(7.50,5.00,6.60)
- Z09_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_Ceiling2): (7.50,5.00,3.00)-(7.50,8.00,3.00)-(10.00,8.00,3.00)-(10.00,5.00,3.00)
- Z09_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_Ceiling): (10.00,5.00,3.00)-(10.00,8.00,3.00)-(15.00,8.00,3.00)-(15.00,5.00,3.00)
- Z09_Roof (roof roof, Default_Roof): (7.50,8.00,6.60)-(7.50,5.00,6.60)-(15.00,5.00,6.60)-(15.00,8.00,6.60)

**Z10_F2_Corridor_C**:
- Z10_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_W3): (0.00,3.00,6.60)-(0.00,3.00,3.00)-(3.75,3.00,3.00)-(3.75,3.00,6.60)
- Z10_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W3): (3.75,3.00,6.60)-(3.75,3.00,3.00)-(7.50,3.00,3.00)-(7.50,3.00,6.60)
- Z10_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W3): (7.50,3.00,6.60)-(7.50,3.00,3.00)-(11.25,3.00,3.00)-(11.25,3.00,6.60)
- Z10_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_W3): (11.25,3.00,6.60)-(11.25,3.00,3.00)-(15.00,3.00,3.00)-(15.00,3.00,6.60)
- Z10_W5 (exterior wall, Default_Ext_Wall): (15.00,3.00,6.60)-(15.00,3.00,3.00)-(15.00,5.00,3.00)-(15.00,5.00,6.60)
- Z10_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F2_Meeting_NE, adjacent_surface=Z09_W1): (15.00,5.00,6.60)-(15.00,5.00,3.00)-(7.50,5.00,3.00)-(7.50,5.00,6.60)
- Z10_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F2_Meeting_NW, adjacent_surface=Z08_W1): (7.50,5.00,6.60)-(7.50,5.00,3.00)-(0.00,5.00,3.00)-(0.00,5.00,6.60)
- Z10_W8 (exterior wall, Default_Ext_Wall): (0.00,5.00,6.60)-(0.00,5.00,3.00)-(0.00,3.00,3.00)-(0.00,3.00,6.60)
- Z10_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_Ceiling): (0.00,3.00,3.00)-(0.00,5.00,3.00)-(15.00,5.00,3.00)-(15.00,3.00,3.00)
- Z10_Roof (roof roof, Default_Roof): (0.00,5.00,6.60)-(0.00,3.00,6.60)-(15.00,3.00,6.60)-(15.00,5.00,6.60)

**Z11_F2_Office_SW**:
- Z11_W1 (exterior wall, Default_Ext_Wall): (0.00,0.00,6.60)-(0.00,0.00,3.00)-(3.75,0.00,3.00)-(3.75,0.00,6.60)
- Z11_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W4): (3.75,0.00,6.60)-(3.75,0.00,3.00)-(3.75,3.00,3.00)-(3.75,3.00,6.60)
- Z11_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W1): (3.75,3.00,6.60)-(3.75,3.00,3.00)-(0.00,3.00,3.00)-(0.00,3.00,6.60)
- Z11_W4 (exterior wall, Default_Ext_Wall): (0.00,3.00,6.60)-(0.00,3.00,3.00)-(0.00,0.00,3.00)-(0.00,0.00,6.60)
- Z11_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_Ceiling1): (0.00,0.00,3.00)-(0.00,3.00,3.00)-(3.75,3.00,3.00)-(3.75,0.00,3.00)
- Z11_Roof (roof roof, Default_Roof): (0.00,3.00,6.60)-(0.00,0.00,6.60)-(3.75,0.00,6.60)-(3.75,3.00,6.60)

**Z12_F2_Office_SW**:
- Z12_W1 (exterior wall, Default_Ext_Wall): (3.75,0.00,6.60)-(3.75,0.00,3.00)-(7.50,0.00,3.00)-(7.50,0.00,6.60)
- Z12_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W4): (7.50,0.00,6.60)-(7.50,0.00,3.00)-(7.50,3.00,3.00)-(7.50,3.00,6.60)
- Z12_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W2): (7.50,3.00,6.60)-(7.50,3.00,3.00)-(3.75,3.00,3.00)-(3.75,3.00,6.60)
- Z12_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_W2): (3.75,3.00,6.60)-(3.75,3.00,3.00)-(3.75,0.00,3.00)-(3.75,0.00,6.60)
- Z12_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_Ceiling2): (3.75,0.00,3.00)-(3.75,3.00,3.00)-(5.00,3.00,3.00)-(5.00,0.00,3.00)
- Z12_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_Ceiling1): (5.00,0.00,3.00)-(5.00,3.00,3.00)-(7.50,3.00,3.00)-(7.50,0.00,3.00)
- Z12_Roof (roof roof, Default_Roof): (3.75,3.00,6.60)-(3.75,0.00,6.60)-(7.50,0.00,6.60)-(7.50,3.00,6.60)

**Z13_F2_Office_SE**:
- Z13_W1 (exterior wall, Default_Ext_Wall): (7.50,0.00,6.60)-(7.50,0.00,3.00)-(11.25,0.00,3.00)-(11.25,0.00,6.60)
- Z13_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_W4): (11.25,0.00,6.60)-(11.25,0.00,3.00)-(11.25,3.00,3.00)-(11.25,3.00,6.60)
- Z13_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W3): (11.25,3.00,6.60)-(11.25,3.00,3.00)-(7.50,3.00,3.00)-(7.50,3.00,6.60)
- Z13_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W2): (7.50,3.00,6.60)-(7.50,3.00,3.00)-(7.50,0.00,3.00)-(7.50,0.00,6.60)
- Z13_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_Ceiling2): (7.50,0.00,3.00)-(7.50,3.00,3.00)-(10.00,3.00,3.00)-(10.00,0.00,3.00)
- Z13_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_Ceiling1): (10.00,0.00,3.00)-(10.00,3.00,3.00)-(11.25,3.00,3.00)-(11.25,0.00,3.00)
- Z13_Roof (roof roof, Default_Roof): (7.50,3.00,6.60)-(7.50,0.00,6.60)-(11.25,0.00,6.60)-(11.25,3.00,6.60)

**Z14_F2_Office_SE**:
- Z14_W1 (exterior wall, Default_Ext_Wall): (11.25,0.00,6.60)-(11.25,0.00,3.00)-(15.00,0.00,3.00)-(15.00,0.00,6.60)
- Z14_W2 (exterior wall, Default_Ext_Wall): (15.00,0.00,6.60)-(15.00,0.00,3.00)-(15.00,3.00,3.00)-(15.00,3.00,6.60)
- Z14_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W4): (15.00,3.00,6.60)-(15.00,3.00,3.00)-(11.25,3.00,3.00)-(11.25,3.00,6.60)
- Z14_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W2): (11.25,3.00,6.60)-(11.25,3.00,3.00)-(11.25,0.00,3.00)-(11.25,0.00,6.60)
- Z14_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_Ceiling2): (11.25,0.00,3.00)-(11.25,3.00,3.00)-(15.00,3.00,3.00)-(15.00,0.00,3.00)
- Z14_Roof (roof roof, Default_Roof): (11.25,3.00,6.60)-(11.25,0.00,6.60)-(15.00,0.00,6.60)-(15.00,3.00,6.60)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- Z01_W3_Win1: parent=Z01_W3, source_window=win_f1_N1, segment=floor_1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=17b36a0ce779730ff496241cf258722513c56449091c196ceb1774622cfa57d9, Construction=Default_Window, z=1.00-2.60, vertices: (3.64,8.00,2.60)-(3.64,8.00,1.00)-(1.24,8.00,1.00)-(1.24,8.00,2.60)
- Z02_W3_Win1: parent=Z02_W3, source_window=win_f1_N2, segment=floor_1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=b1ef230283f44ef772466cf71bdf4f4458236a32a5bfefe56e6e597318f58619, Construction=Default_Window, z=1.00-2.60, vertices: (8.70,8.00,2.60)-(8.70,8.00,1.00)-(6.30,8.00,1.00)-(6.30,8.00,2.60)
- Z03_W3_Win1: parent=Z03_W3, source_window=win_f1_N3, segment=floor_1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=c854bf59c5c38b117f5016e574bc0a3d8a2a5c7f357bcbd0e297408ec55ac1fd, Construction=Default_Window, z=1.00-2.60, vertices: (13.76,8.00,2.60)-(13.76,8.00,1.00)-(11.36,8.00,1.00)-(11.36,8.00,2.60)
- Z04_W4_Win1: parent=Z04_W4, source_window=win_f1_E1, segment=floor_1:facade:3b268db789d0c17bf026f0e5f8bd710de9b96ed707c8ceca2def06c4e9e1ee68, host_proof=b303965d5585f069f4d28de922b8a9219f2b224a0870107357c32e8039e47e7d, Construction=Default_Window, z=1.00-2.80, vertices: (15.00,3.40,2.80)-(15.00,3.40,1.00)-(15.00,4.60,1.00)-(15.00,4.60,2.80)
- Z05_W1_Win1: parent=Z05_W1, source_window=win_f1_S1, segment=floor_1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=f3b1dc5a73a1ee2810e87d4a27d4ee6cb2ebdc0a025acdde5e3777d721bd46a3, Construction=Default_Window, z=1.50-2.10, vertices: (3.44,0.00,2.10)-(3.44,0.00,1.50)-(4.64,0.00,1.50)-(4.64,0.00,2.10)
- Z06_W1_Win1: parent=Z06_W1, source_window=win_f1_S2, segment=floor_1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=c2feddf2b8115a5e43feae169fcc33b0c2cff19d3fd57109ce40c90f85c31bf5, Construction=Default_Window, z=1.00-2.60, vertices: (6.30,0.00,2.60)-(6.30,0.00,1.00)-(8.70,0.00,1.00)-(8.70,0.00,2.60)
- Z07_W1_Win1: parent=Z07_W1, source_window=win_f1_S3, segment=floor_1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=364147afe380189800676e2394ae39bed34e63088449416ba6cca54f145642d8, Construction=Default_Window, z=1.00-2.60, vertices: (11.36,0.00,2.60)-(11.36,0.00,1.00)-(13.76,0.00,1.00)-(13.76,0.00,2.60)
- Z08_W3_Win1: parent=Z08_W3, source_window=win_f2_N1, segment=floor_2:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=82976c790f9223955b1aaa78dfe8eceaf7aaa6690de007ea8eb48b89fa924f1c, Construction=Default_Window, z=4.00-5.80, vertices: (5.55,8.00,5.80)-(5.55,8.00,4.00)-(1.95,8.00,4.00)-(1.95,8.00,5.80)
- Z09_W3_Win1: parent=Z09_W3, source_window=win_f2_N2, segment=floor_2:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=3775977b38d2b0851865da63e10b5f2ec47a70088c06d64bd84ad2aebdce3668, Construction=Default_Window, z=4.00-5.80, vertices: (13.05,8.00,5.80)-(13.05,8.00,4.00)-(9.45,8.00,4.00)-(9.45,8.00,5.80)
- Z10_W5_Win1: parent=Z10_W5, source_window=win_f2_E1, segment=floor_2:facade:3b268db789d0c17bf026f0e5f8bd710de9b96ed707c8ceca2def06c4e9e1ee68, host_proof=b7ad110ad2a9aa8d8ace587a69c7fad57bc8054c7c7e8c7efeeb0b76fee44065, Construction=Default_Window, z=4.00-5.80, vertices: (15.00,3.40,5.80)-(15.00,3.40,4.00)-(15.00,4.60,4.00)-(15.00,4.60,5.80)
- Z10_W8_Win1: parent=Z10_W8, source_window=win_f2_W1, segment=floor_2:facade:f93561c1a634de26972b6a62a23157d4fbc226db55b7723dac46a69eb2dcf821, host_proof=6a473bf39263b444e1b7096f38a6281027eac0c77e515b6b8dd7da032c8fcd8f, Construction=Default_Window, z=4.00-5.80, vertices: (0.00,4.60,5.80)-(0.00,4.60,4.00)-(0.00,3.40,4.00)-(0.00,3.40,5.80)
- Z11_W1_Win1: parent=Z11_W1, source_window=win_f2_S1, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=599f1d2a56bd8b186f060f96b6e614cc887ba61d727b796f961f327be5f0306d, Construction=Default_Window, z=4.00-5.80, vertices: (2.19,0.00,5.80)-(2.19,0.00,4.00)-(3.39,0.00,4.00)-(3.39,0.00,5.80)
- Z12_W1_Win1: parent=Z12_W1, source_window=win_f2_S2, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=8339ceb095f5e3aa4978465576bea51620652264b3543129dc2e38bd337cf222, Construction=Default_Window, z=4.00-5.80, vertices: (4.11,0.00,5.80)-(4.11,0.00,4.00)-(5.31,0.00,4.00)-(5.31,0.00,5.80)
- Z13_W1_Win1: parent=Z13_W1, source_window=win_f2_S3, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=ebd66bf46357405d9cf0a753236ef679575b8e02d64fe2b8d38ea581c2405026, Construction=Default_Window, z=4.00-5.80, vertices: (9.69,0.00,5.80)-(9.69,0.00,4.00)-(10.89,0.00,4.00)-(10.89,0.00,5.80)
- Z14_W1_Win1: parent=Z14_W1, source_window=win_f2_S4, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=44566ce350ca920a13802feee612b6298238efb5cbbfb0deb2fe251257873a07, Construction=Default_Window, z=4.00-5.80, vertices: (11.61,0.00,5.80)-(11.61,0.00,4.00)-(12.81,0.00,4.00)-(12.81,0.00,5.80)
