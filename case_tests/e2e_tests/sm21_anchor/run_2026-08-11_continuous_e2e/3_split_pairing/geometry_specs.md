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
- Z08_F2_Conference_NW: x[0.00,7.50], y[5.00,8.00], z_floor=3.00, ceiling_height=3.60, role: conference.
- Z09_F2_Conference_NE: x[7.50,15.00], y[5.00,8.00], z_floor=3.00, ceiling_height=3.60, role: conference.
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
- Z01_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_Floor1): (0.00,8.00,3.00)-(0.00,5.00,3.00)-(5.00,5.00,3.00)-(5.00,8.00,3.00)

**Z02_F1_Office_N**:
- Z02_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W6): (5.00,5.00,3.00)-(5.00,5.00,0.00)-(10.00,5.00,0.00)-(10.00,5.00,3.00)
- Z02_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_W4): (10.00,5.00,3.00)-(10.00,5.00,0.00)-(10.00,8.00,0.00)-(10.00,8.00,3.00)
- Z02_W3 (exterior wall, Default_Ext_Wall): (10.00,8.00,3.00)-(10.00,8.00,0.00)-(5.00,8.00,0.00)-(5.00,8.00,3.00)
- Z02_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_W2): (5.00,8.00,3.00)-(5.00,8.00,0.00)-(5.00,5.00,0.00)-(5.00,5.00,3.00)
- Z02_Floor (ground floor, Default_GroundFloor): (5.00,5.00,0.00)-(5.00,8.00,0.00)-(10.00,8.00,0.00)-(10.00,5.00,0.00)
- Z02_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_Floor2): (5.00,8.00,3.00)-(5.00,5.00,3.00)-(7.50,5.00,3.00)-(7.50,8.00,3.00)
- Z02_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_Floor1): (7.50,8.00,3.00)-(7.50,5.00,3.00)-(10.00,5.00,3.00)-(10.00,8.00,3.00)

**Z03_F1_Office_NE**:
- Z03_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W5): (10.00,5.00,3.00)-(10.00,5.00,0.00)-(15.00,5.00,0.00)-(15.00,5.00,3.00)
- Z03_W2 (exterior wall, Default_Ext_Wall): (15.00,5.00,3.00)-(15.00,5.00,0.00)-(15.00,8.00,0.00)-(15.00,8.00,3.00)
- Z03_W3 (exterior wall, Default_Ext_Wall): (15.00,8.00,3.00)-(15.00,8.00,0.00)-(10.00,8.00,0.00)-(10.00,8.00,3.00)
- Z03_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W2): (10.00,8.00,3.00)-(10.00,8.00,0.00)-(10.00,5.00,0.00)-(10.00,5.00,3.00)
- Z03_Floor (ground floor, Default_GroundFloor): (10.00,5.00,0.00)-(10.00,8.00,0.00)-(15.00,8.00,0.00)-(15.00,5.00,0.00)
- Z03_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_Floor2): (10.00,8.00,3.00)-(10.00,5.00,3.00)-(15.00,5.00,3.00)-(15.00,8.00,3.00)

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

**Z08_F2_Conference_NW**:
- Z08_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W7): (0.00,5.00,6.60)-(0.00,5.00,3.00)-(7.50,5.00,3.00)-(7.50,5.00,6.60)
- Z08_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_W4): (7.50,5.00,6.60)-(7.50,5.00,3.00)-(7.50,8.00,3.00)-(7.50,8.00,6.60)
- Z08_W3 (exterior wall, Default_Ext_Wall): (7.50,8.00,6.60)-(7.50,8.00,3.00)-(0.00,8.00,3.00)-(0.00,8.00,6.60)
- Z08_W4 (exterior wall, Default_Ext_Wall): (0.00,8.00,6.60)-(0.00,8.00,3.00)-(0.00,5.00,3.00)-(0.00,5.00,6.60)
- Z08_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_Ceiling): (0.00,5.00,3.00)-(0.00,8.00,3.00)-(5.00,8.00,3.00)-(5.00,5.00,3.00)
- Z08_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_Ceiling1): (5.00,5.00,3.00)-(5.00,8.00,3.00)-(7.50,8.00,3.00)-(7.50,5.00,3.00)
- Z08_Roof (roof roof, Default_Roof): (0.00,8.00,6.60)-(0.00,5.00,6.60)-(7.50,5.00,6.60)-(7.50,8.00,6.60)

**Z09_F2_Conference_NE**:
- Z09_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W6): (7.50,5.00,6.60)-(7.50,5.00,3.00)-(15.00,5.00,3.00)-(15.00,5.00,6.60)
- Z09_W2 (exterior wall, Default_Ext_Wall): (15.00,5.00,6.60)-(15.00,5.00,3.00)-(15.00,8.00,3.00)-(15.00,8.00,6.60)
- Z09_W3 (exterior wall, Default_Ext_Wall): (15.00,8.00,6.60)-(15.00,8.00,3.00)-(7.50,8.00,3.00)-(7.50,8.00,6.60)
- Z09_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_W2): (7.50,8.00,6.60)-(7.50,8.00,3.00)-(7.50,5.00,3.00)-(7.50,5.00,6.60)
- Z09_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_Ceiling2): (7.50,5.00,3.00)-(7.50,8.00,3.00)-(10.00,8.00,3.00)-(10.00,5.00,3.00)
- Z09_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_Ceiling): (10.00,5.00,3.00)-(10.00,8.00,3.00)-(15.00,8.00,3.00)-(15.00,5.00,3.00)
- Z09_Roof (roof roof, Default_Roof): (7.50,8.00,6.60)-(7.50,5.00,6.60)-(15.00,5.00,6.60)-(15.00,8.00,6.60)

**Z10_F2_Corridor_C**:
- Z10_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_W3): (0.00,3.00,6.60)-(0.00,3.00,3.00)-(3.75,3.00,3.00)-(3.75,3.00,6.60)
- Z10_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W3): (3.75,3.00,6.60)-(3.75,3.00,3.00)-(7.50,3.00,3.00)-(7.50,3.00,6.60)
- Z10_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W3): (7.50,3.00,6.60)-(7.50,3.00,3.00)-(11.25,3.00,3.00)-(11.25,3.00,6.60)
- Z10_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_W3): (11.25,3.00,6.60)-(11.25,3.00,3.00)-(15.00,3.00,3.00)-(15.00,3.00,6.60)
- Z10_W5 (exterior wall, Default_Ext_Wall): (15.00,3.00,6.60)-(15.00,3.00,3.00)-(15.00,5.00,3.00)-(15.00,5.00,6.60)
- Z10_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_W1): (15.00,5.00,6.60)-(15.00,5.00,3.00)-(7.50,5.00,3.00)-(7.50,5.00,6.60)
- Z10_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_W1): (7.50,5.00,6.60)-(7.50,5.00,3.00)-(0.00,5.00,3.00)-(0.00,5.00,6.60)
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
- Z01_W3_Win1: parent=Z01_W3, source_window=W1_N1, segment=F1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=d391394e4f4adfd93eba3b0544ab48c14ca2abc2323be82c8118462967a07f6d, Construction=Default_Window, z=1.00-2.60, vertices: (3.64,8.00,2.60)-(3.64,8.00,1.00)-(1.24,8.00,1.00)-(1.24,8.00,2.60)
- Z02_W3_Win1: parent=Z02_W3, source_window=W1_N2, segment=F1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=b4425bc34dc9ed27c1a71e0cc5b9034867767c9628e939452bcabb5a898abacd, Construction=Default_Window, z=1.00-2.60, vertices: (8.70,8.00,2.60)-(8.70,8.00,1.00)-(6.30,8.00,1.00)-(6.30,8.00,2.60)
- Z03_W3_Win1: parent=Z03_W3, source_window=W1_N3, segment=F1:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=7e11287d72a77170fabbf9237f511e7feb43b3be9b097869e595f2d8af41581a, Construction=Default_Window, z=1.00-2.60, vertices: (13.76,8.00,2.60)-(13.76,8.00,1.00)-(11.36,8.00,1.00)-(11.36,8.00,2.60)
- Z04_W4_Win1: parent=Z04_W4, source_window=W1_E1, segment=F1:facade:3b268db789d0c17bf026f0e5f8bd710de9b96ed707c8ceca2def06c4e9e1ee68, host_proof=ef9d4018abd5095fbcf03ed5dc888214a89fbd546974e94fa2d9e4722487174c, Construction=Default_Window, z=1.00-2.80, vertices: (15.00,3.40,2.80)-(15.00,3.40,1.00)-(15.00,4.60,1.00)-(15.00,4.60,2.80)
- Z05_W1_Win1: parent=Z05_W1, source_window=W1_S1, segment=F1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=c203063fc0db30378a007bea64d689439267d06e64fdd47ed00bc371852b49bf, Construction=Default_Window, z=1.50-2.10, vertices: (3.44,0.00,2.10)-(3.44,0.00,1.50)-(4.64,0.00,1.50)-(4.64,0.00,2.10)
- Z06_W1_Win1: parent=Z06_W1, source_window=W1_S2, segment=F1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=de78090fe2983fdfc8f512814703de16c7411992be2eac0768a2833d0aaab686, Construction=Default_Window, z=1.00-2.60, vertices: (6.30,0.00,2.60)-(6.30,0.00,1.00)-(8.70,0.00,1.00)-(8.70,0.00,2.60)
- Z07_W1_Win1: parent=Z07_W1, source_window=W1_S3, segment=F1:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=9efadf09ad5bbbaa7a2065c1eeb3a0653561ea38066fec896eb274a807b70f4f, Construction=Default_Window, z=1.00-2.60, vertices: (11.36,0.00,2.60)-(11.36,0.00,1.00)-(13.76,0.00,1.00)-(13.76,0.00,2.60)
- Z08_W3_Win1: parent=Z08_W3, source_window=W2_N1, segment=F2:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=f6639ce1240181069dfb9fe59dd470b84c8e54ee4c52ad3a7591b7c59a2f327c, Construction=Default_Window, z=4.00-5.80, vertices: (5.55,8.00,5.80)-(5.55,8.00,4.00)-(1.95,8.00,4.00)-(1.95,8.00,5.80)
- Z09_W3_Win1: parent=Z09_W3, source_window=W2_N2, segment=F2:facade:327996e6f4a7d678e65956ee9a8bb8e0de3c0d122a32cf53f8738c07bd87070a, host_proof=2bcdcb3eee553300a4918b97ee06be6090f18ee2cc416684130ec87fa5a239e0, Construction=Default_Window, z=4.00-5.80, vertices: (13.05,8.00,5.80)-(13.05,8.00,4.00)-(9.45,8.00,4.00)-(9.45,8.00,5.80)
- Z10_W5_Win1: parent=Z10_W5, source_window=W2_E1, segment=F2:facade:3b268db789d0c17bf026f0e5f8bd710de9b96ed707c8ceca2def06c4e9e1ee68, host_proof=364aede87d92f8b39f59d65dd4be369d921593ed2f0f2e1867568f333f586d73, Construction=Default_Window, z=4.00-5.80, vertices: (15.00,3.40,5.80)-(15.00,3.40,4.00)-(15.00,4.60,4.00)-(15.00,4.60,5.80)
- Z10_W8_Win1: parent=Z10_W8, source_window=W2_W1, segment=F2:facade:f93561c1a634de26972b6a62a23157d4fbc226db55b7723dac46a69eb2dcf821, host_proof=894001ba8c5524817ae394fe2bcb8391defdf197eb2555994ee42e9653984be2, Construction=Default_Window, z=4.00-5.80, vertices: (0.00,4.60,5.80)-(0.00,4.60,4.00)-(0.00,3.40,4.00)-(0.00,3.40,5.80)
- Z11_W1_Win1: parent=Z11_W1, source_window=W2_S1, segment=F2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=a8598454c9c70ffdc33c86a097b5966cd22364a2901157a47a07a220e2e10ab2, Construction=Default_Window, z=4.00-5.80, vertices: (2.19,0.00,5.80)-(2.19,0.00,4.00)-(3.39,0.00,4.00)-(3.39,0.00,5.80)
- Z12_W1_Win1: parent=Z12_W1, source_window=W2_S2, segment=F2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=2634f1f5b45bd832ac75115e60b4e2bf1a0f58347167dfc6011ec755baea2816, Construction=Default_Window, z=4.00-5.80, vertices: (4.11,0.00,5.80)-(4.11,0.00,4.00)-(5.31,0.00,4.00)-(5.31,0.00,5.80)
- Z13_W1_Win1: parent=Z13_W1, source_window=W2_S3, segment=F2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=9c8f5a9afc9151b28e6cd74403668512a481b064c28bce85f2d8274f9537b6da, Construction=Default_Window, z=4.00-5.80, vertices: (9.69,0.00,5.80)-(9.69,0.00,4.00)-(10.89,0.00,4.00)-(10.89,0.00,5.80)
- Z14_W1_Win1: parent=Z14_W1, source_window=W2_S4, segment=F2:facade:121355024686ae32fceeb10835c67904f4b40e529a960083b8edfe4905f5c465, host_proof=8a701a0487559c77062022feaec20cc496dd4a3615474685b8a51666581c3e2c, Construction=Default_Window, z=4.00-5.80, vertices: (11.61,0.00,5.80)-(11.61,0.00,4.00)-(12.81,0.00,4.00)-(12.81,0.00,5.80)
