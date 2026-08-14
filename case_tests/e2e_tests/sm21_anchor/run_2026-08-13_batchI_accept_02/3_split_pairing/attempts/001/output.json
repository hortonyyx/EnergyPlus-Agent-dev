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
- Z01_W3_Win1: parent=Z01_W3, source_window=f1_north_1, segment=floor_1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=7b11b2d56260d8822995d1effab54539037ec3729137ae7dceb47457ad7a54b6, Construction=Default_Window, z=1.00-2.60, vertices: (3.64,8.00,2.60)-(3.64,8.00,1.00)-(1.24,8.00,1.00)-(1.24,8.00,2.60)
- Z02_W3_Win1: parent=Z02_W3, source_window=f1_north_2, segment=floor_1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=4b3907dd118a5822254d1704b04873229e4cb8030bcf511aa80f7001da243d6b, Construction=Default_Window, z=1.00-2.60, vertices: (8.70,8.00,2.60)-(8.70,8.00,1.00)-(6.30,8.00,1.00)-(6.30,8.00,2.60)
- Z03_W3_Win1: parent=Z03_W3, source_window=f1_north_3, segment=floor_1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=a4b4fe541aebfd321b8bd7dcd6e88154836e5425f96986ac8b39a7dc4b205506, Construction=Default_Window, z=1.00-2.60, vertices: (13.76,8.00,2.60)-(13.76,8.00,1.00)-(11.36,8.00,1.00)-(11.36,8.00,2.60)
- Z04_W4_Win1: parent=Z04_W4, source_window=f1_east_1, segment=floor_1:facade:3b268db789d0c17bf026f0e5f8bd710de9b96ed707c8ceca2def06c4e9e1ee68, host_proof=fa9e8c9ddcfab1d7081d23d93d380d5b1c7d195f413f8741db7d5fd15f3821d4, Construction=Default_Window, z=1.00-2.80, vertices: (15.00,3.40,2.80)-(15.00,3.40,1.00)-(15.00,4.60,1.00)-(15.00,4.60,2.80)
- Z05_W1_Win1: parent=Z05_W1, source_window=f1_south_1, segment=floor_1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=cdb2b62fd9cc8a93be1ac4af6ed5bae6a585051408db67553ee990704b5feed6, Construction=Default_Window, z=1.50-2.10, vertices: (3.44,0.00,2.10)-(3.44,0.00,1.50)-(4.64,0.00,1.50)-(4.64,0.00,2.10)
- Z06_W1_Win1: parent=Z06_W1, source_window=f1_south_2, segment=floor_1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=6280b418f2c5c57cdc29b0af3d13a6173ec1c446da94480834670cdf84773533, Construction=Default_Window, z=1.00-2.60, vertices: (6.30,0.00,2.60)-(6.30,0.00,1.00)-(8.70,0.00,1.00)-(8.70,0.00,2.60)
- Z07_W1_Win1: parent=Z07_W1, source_window=f1_south_3, segment=floor_1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=3d700c2260dd90f3c5126d8339b2f2c2a253a035902090055cb582476f443b84, Construction=Default_Window, z=1.00-2.60, vertices: (11.36,0.00,2.60)-(11.36,0.00,1.00)-(13.76,0.00,1.00)-(13.76,0.00,2.60)
- Z08_W3_Win1: parent=Z08_W3, source_window=f2_north_1, segment=floor_2:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=50fafeeadc543f72239261d970f1d55de832abb756634b9de85d0207fab738aa, Construction=Default_Window, z=4.00-5.80, vertices: (5.55,8.00,5.80)-(5.55,8.00,4.00)-(1.95,8.00,4.00)-(1.95,8.00,5.80)
- Z09_W3_Win1: parent=Z09_W3, source_window=f2_north_2, segment=floor_2:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=8a31686ac322e02949989273a0ac0b7df00111b2332390a46b63d54bc84288a0, Construction=Default_Window, z=4.00-5.80, vertices: (13.05,8.00,5.80)-(13.05,8.00,4.00)-(9.45,8.00,4.00)-(9.45,8.00,5.80)
- Z10_W5_Win1: parent=Z10_W5, source_window=f2_east_1, segment=floor_2:facade:3b268db789d0c17bf026f0e5f8bd710de9b96ed707c8ceca2def06c4e9e1ee68, host_proof=03bf87ae3d7ca603ec8b770f86fa2a1deb4ac96cc00b611efef56e344e626f05, Construction=Default_Window, z=4.00-5.80, vertices: (15.00,3.40,5.80)-(15.00,3.40,4.00)-(15.00,4.60,4.00)-(15.00,4.60,5.80)
- Z10_W8_Win1: parent=Z10_W8, source_window=f2_west_1, segment=floor_2:facade:f93561c1a634de26972b6a62a23157d4fbc226db55b7723dac46a69eb2dcf821, host_proof=13db9bb1a8a5960041f10426d4392ccc719313bf80a6d7600ae738ca0f1a16b1, Construction=Default_Window, z=4.00-5.80, vertices: (0.00,4.60,5.80)-(0.00,4.60,4.00)-(0.00,3.40,4.00)-(0.00,3.40,5.80)
- Z11_W1_Win1: parent=Z11_W1, source_window=f2_south_1, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=cfdd761c9a9f763e2b94675bbaff704092a0d03aad44a9a2fd275a9589da8471, Construction=Default_Window, z=4.00-5.80, vertices: (2.19,0.00,5.80)-(2.19,0.00,4.00)-(3.39,0.00,4.00)-(3.39,0.00,5.80)
- Z12_W1_Win1: parent=Z12_W1, source_window=f2_south_2, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=c594d860d8f25a216b5671a1dd791cf20fd3c2c5cdbcb49c0d48ad063e0dd8bc, Construction=Default_Window, z=4.00-5.80, vertices: (4.11,0.00,5.80)-(4.11,0.00,4.00)-(5.31,0.00,4.00)-(5.31,0.00,5.80)
- Z13_W1_Win1: parent=Z13_W1, source_window=f2_south_3, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=0919691300b737cae129563c3ca0a8c670e27a892e54ec1267b7ad63b32615e9, Construction=Default_Window, z=4.00-5.80, vertices: (9.69,0.00,5.80)-(9.69,0.00,4.00)-(10.89,0.00,4.00)-(10.89,0.00,5.80)
- Z14_W1_Win1: parent=Z14_W1, source_window=f2_south_4, segment=floor_2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=9253d35c5049e3a62b67905ee28245febd3f377951a7736f60d4334715a9fb6c, Construction=Default_Window, z=4.00-5.80, vertices: (11.61,0.00,5.80)-(11.61,0.00,4.00)-(12.81,0.00,4.00)-(12.81,0.00,5.80)
