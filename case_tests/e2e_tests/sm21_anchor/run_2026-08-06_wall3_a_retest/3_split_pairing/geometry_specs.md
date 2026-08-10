# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 3.00):
- Z01_F1_Office_NW: x[-0.10,4.30], y[4.75,7.65], z_floor=0.00, ceiling_height=3.00, role: office.
- Z02_F1_Office_N: x[4.30,9.70], y[4.75,7.65], z_floor=0.00, ceiling_height=3.00, role: office.
- Z03_F1_Office_NE: x[9.70,14.65], y[4.75,7.65], z_floor=0.00, ceiling_height=3.00, role: office.
- Z04_F1_Corridor_C: x[-0.10,14.65], y[2.75,4.75], z_floor=0.00, ceiling_height=3.00, role: corridor.
- Z05_F1_Office_SW: x[-0.10,4.75], y[-0.10,2.75], z_floor=0.00, ceiling_height=3.00, role: office.
- Z06_F1_Office_S: x[4.75,9.70], y[-0.10,2.75], z_floor=0.00, ceiling_height=3.00, role: office.
- Z07_F1_Office_SE: x[9.70,14.65], y[-0.10,2.75], z_floor=0.00, ceiling_height=3.00, role: office.

Floor 2 (z 3.00 to 6.60):
- Z08_F2_Conference_NW: x[-0.10,7.20], y[4.75,7.65], z_floor=3.00, ceiling_height=3.60, role: conference.
- Z09_F2_Conference_NE: x[7.20,14.65], y[4.75,7.65], z_floor=3.00, ceiling_height=3.60, role: conference.
- Z10_F2_Corridor_C: x[-0.10,14.65], y[2.75,4.75], z_floor=3.00, ceiling_height=3.60, role: corridor.
- Z11_F2_Office_SW: x[-0.10,3.50], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- Z12_F2_Office_SW: x[3.50,7.20], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- Z13_F2_Office_SE: x[7.20,11.00], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- Z14_F2_Office_SE: x[11.00,14.65], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**Z01_F1_Office_NW**:
- Z01_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W7): (-0.10,4.75,0.00)-(4.30,4.75,0.00)-(4.30,4.75,3.00)-(-0.10,4.75,3.00)
- Z01_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W4): (4.30,4.75,0.00)-(4.30,7.65,0.00)-(4.30,7.65,3.00)-(4.30,4.75,3.00)
- Z01_W3 (exterior wall, Default_Ext_Wall): (4.30,7.65,0.00)-(-0.10,7.65,0.00)-(-0.10,7.65,3.00)-(4.30,7.65,3.00)
- Z01_W4 (exterior wall, Default_Ext_Wall): (-0.10,7.65,0.00)-(-0.10,4.75,0.00)-(-0.10,4.75,3.00)-(-0.10,7.65,3.00)
- Z01_Floor (ground floor, Default_GroundFloor): (-0.10,7.65,0.00)-(4.30,7.65,0.00)-(4.30,4.75,0.00)-(-0.10,4.75,0.00)
- Z01_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_Floor1): (4.30,4.75,3.00)-(4.30,7.65,3.00)-(-0.10,7.65,3.00)-(-0.10,4.75,3.00)

**Z02_F1_Office_N**:
- Z02_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W6): (4.30,4.75,0.00)-(9.70,4.75,0.00)-(9.70,4.75,3.00)-(4.30,4.75,3.00)
- Z02_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_W4): (9.70,4.75,0.00)-(9.70,7.65,0.00)-(9.70,7.65,3.00)-(9.70,4.75,3.00)
- Z02_W3 (exterior wall, Default_Ext_Wall): (9.70,7.65,0.00)-(4.30,7.65,0.00)-(4.30,7.65,3.00)-(9.70,7.65,3.00)
- Z02_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_W2): (4.30,4.75,3.00)-(4.30,7.65,3.00)-(4.30,7.65,0.00)-(4.30,4.75,0.00)
- Z02_Floor (ground floor, Default_GroundFloor): (4.30,7.65,0.00)-(9.70,7.65,0.00)-(9.70,4.75,0.00)-(4.30,4.75,0.00)
- Z02_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_Floor2): (7.20,4.75,3.00)-(7.20,7.65,3.00)-(4.30,7.65,3.00)-(4.30,4.75,3.00)
- Z02_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_Floor1): (9.70,4.75,3.00)-(9.70,7.65,3.00)-(7.20,7.65,3.00)-(7.20,4.75,3.00)

**Z03_F1_Office_NE**:
- Z03_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W5): (9.70,4.75,0.00)-(14.65,4.75,0.00)-(14.65,4.75,3.00)-(9.70,4.75,3.00)
- Z03_W2 (exterior wall, Default_Ext_Wall): (14.65,4.75,0.00)-(14.65,7.65,0.00)-(14.65,7.65,3.00)-(14.65,4.75,3.00)
- Z03_W3 (exterior wall, Default_Ext_Wall): (14.65,7.65,0.00)-(9.70,7.65,0.00)-(9.70,7.65,3.00)-(14.65,7.65,3.00)
- Z03_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W2): (9.70,4.75,3.00)-(9.70,7.65,3.00)-(9.70,7.65,0.00)-(9.70,4.75,0.00)
- Z03_Floor (ground floor, Default_GroundFloor): (9.70,7.65,0.00)-(14.65,7.65,0.00)-(14.65,4.75,0.00)-(9.70,4.75,0.00)
- Z03_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_Floor2): (14.65,4.75,3.00)-(14.65,7.65,3.00)-(9.70,7.65,3.00)-(9.70,4.75,3.00)

**Z04_F1_Corridor_C**:
- Z04_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_W3): (-0.10,2.75,0.00)-(4.75,2.75,0.00)-(4.75,2.75,3.00)-(-0.10,2.75,3.00)
- Z04_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_W3): (4.75,2.75,0.00)-(9.70,2.75,0.00)-(9.70,2.75,3.00)-(4.75,2.75,3.00)
- Z04_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W3): (9.70,2.75,0.00)-(14.65,2.75,0.00)-(14.65,2.75,3.00)-(9.70,2.75,3.00)
- Z04_W4 (exterior wall, Default_Ext_Wall): (14.65,2.75,0.00)-(14.65,4.75,0.00)-(14.65,4.75,3.00)-(14.65,2.75,3.00)
- Z04_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_W1): (9.70,4.75,3.00)-(14.65,4.75,3.00)-(14.65,4.75,0.00)-(9.70,4.75,0.00)
- Z04_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_W1): (4.30,4.75,3.00)-(9.70,4.75,3.00)-(9.70,4.75,0.00)-(4.30,4.75,0.00)
- Z04_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_W1): (-0.10,4.75,3.00)-(4.30,4.75,3.00)-(4.30,4.75,0.00)-(-0.10,4.75,0.00)
- Z04_W8 (exterior wall, Default_Ext_Wall): (-0.10,4.75,0.00)-(-0.10,2.75,0.00)-(-0.10,2.75,3.00)-(-0.10,4.75,3.00)
- Z04_Floor (ground floor, Default_GroundFloor): (-0.10,4.75,0.00)-(14.65,4.75,0.00)-(14.65,2.75,0.00)-(-0.10,2.75,0.00)
- Z04_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_Floor): (14.65,2.75,3.00)-(14.65,4.75,3.00)-(-0.10,4.75,3.00)-(-0.10,2.75,3.00)

**Z05_F1_Office_SW**:
- Z05_W1 (exterior wall, Default_Ext_Wall): (-0.10,-0.10,0.00)-(4.75,-0.10,0.00)-(4.75,-0.10,3.00)-(-0.10,-0.10,3.00)
- Z05_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_W4): (4.75,-0.10,0.00)-(4.75,2.75,0.00)-(4.75,2.75,3.00)-(4.75,-0.10,3.00)
- Z05_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W1): (-0.10,2.75,3.00)-(4.75,2.75,3.00)-(4.75,2.75,0.00)-(-0.10,2.75,0.00)
- Z05_W4 (exterior wall, Default_Ext_Wall): (-0.10,2.75,0.00)-(-0.10,-0.10,0.00)-(-0.10,-0.10,3.00)-(-0.10,2.75,3.00)
- Z05_Floor (ground floor, Default_GroundFloor): (-0.10,2.75,0.00)-(4.75,2.75,0.00)-(4.75,-0.10,0.00)-(-0.10,-0.10,0.00)
- Z05_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_Floor): (3.50,-0.10,3.00)-(3.50,2.75,3.00)-(-0.10,2.75,3.00)-(-0.10,-0.10,3.00)
- Z05_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_Floor1): (4.75,-0.10,3.00)-(4.75,2.75,3.00)-(3.50,2.75,3.00)-(3.50,-0.10,3.00)

**Z06_F1_Office_S**:
- Z06_W1 (exterior wall, Default_Ext_Wall): (4.75,-0.10,0.00)-(9.70,-0.10,0.00)-(9.70,-0.10,3.00)-(4.75,-0.10,3.00)
- Z06_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W4): (9.70,-0.10,0.00)-(9.70,2.75,0.00)-(9.70,2.75,3.00)-(9.70,-0.10,3.00)
- Z06_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W2): (4.75,2.75,3.00)-(9.70,2.75,3.00)-(9.70,2.75,0.00)-(4.75,2.75,0.00)
- Z06_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_W2): (4.75,-0.10,3.00)-(4.75,2.75,3.00)-(4.75,2.75,0.00)-(4.75,-0.10,0.00)
- Z06_Floor (ground floor, Default_GroundFloor): (4.75,2.75,0.00)-(9.70,2.75,0.00)-(9.70,-0.10,0.00)-(4.75,-0.10,0.00)
- Z06_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_Floor2): (7.20,-0.10,3.00)-(7.20,2.75,3.00)-(4.75,2.75,3.00)-(4.75,-0.10,3.00)
- Z06_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_Floor1): (9.70,-0.10,3.00)-(9.70,2.75,3.00)-(7.20,2.75,3.00)-(7.20,-0.10,3.00)

**Z07_F1_Office_SE**:
- Z07_W1 (exterior wall, Default_Ext_Wall): (9.70,-0.10,0.00)-(14.65,-0.10,0.00)-(14.65,-0.10,3.00)-(9.70,-0.10,3.00)
- Z07_W2 (exterior wall, Default_Ext_Wall): (14.65,-0.10,0.00)-(14.65,2.75,0.00)-(14.65,2.75,3.00)-(14.65,-0.10,3.00)
- Z07_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_W3): (9.70,2.75,3.00)-(14.65,2.75,3.00)-(14.65,2.75,0.00)-(9.70,2.75,0.00)
- Z07_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_W2): (9.70,-0.10,3.00)-(9.70,2.75,3.00)-(9.70,2.75,0.00)-(9.70,-0.10,0.00)
- Z07_Floor (ground floor, Default_GroundFloor): (9.70,2.75,0.00)-(14.65,2.75,0.00)-(14.65,-0.10,0.00)-(9.70,-0.10,0.00)
- Z07_Ceiling1 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_Floor2): (11.00,-0.10,3.00)-(11.00,2.75,3.00)-(9.70,2.75,3.00)-(9.70,-0.10,3.00)
- Z07_Ceiling2 (interzone ceiling, Cons_InterFloor, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_Floor): (14.65,-0.10,3.00)-(14.65,2.75,3.00)-(11.00,2.75,3.00)-(11.00,-0.10,3.00)

**Z08_F2_Conference_NW**:
- Z08_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W7): (-0.10,4.75,3.00)-(7.20,4.75,3.00)-(7.20,4.75,6.60)-(-0.10,4.75,6.60)
- Z08_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_W4): (7.20,4.75,3.00)-(7.20,7.65,3.00)-(7.20,7.65,6.60)-(7.20,4.75,6.60)
- Z08_W3 (exterior wall, Default_Ext_Wall): (7.20,7.65,3.00)-(-0.10,7.65,3.00)-(-0.10,7.65,6.60)-(7.20,7.65,6.60)
- Z08_W4 (exterior wall, Default_Ext_Wall): (-0.10,7.65,3.00)-(-0.10,4.75,3.00)-(-0.10,4.75,6.60)-(-0.10,7.65,6.60)
- Z08_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z01_F1_Office_NW, adjacent_surface=Z01_Ceiling): (-0.10,4.75,3.00)-(-0.10,7.65,3.00)-(4.30,7.65,3.00)-(4.30,4.75,3.00)
- Z08_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_Ceiling1): (4.30,4.75,3.00)-(4.30,7.65,3.00)-(7.20,7.65,3.00)-(7.20,4.75,3.00)
- Z08_Roof (roof roof, Default_Roof): (-0.10,4.75,6.60)-(7.20,4.75,6.60)-(7.20,7.65,6.60)-(-0.10,7.65,6.60)

**Z09_F2_Conference_NE**:
- Z09_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W6): (7.20,4.75,3.00)-(14.65,4.75,3.00)-(14.65,4.75,6.60)-(7.20,4.75,6.60)
- Z09_W2 (exterior wall, Default_Ext_Wall): (14.65,4.75,3.00)-(14.65,7.65,3.00)-(14.65,7.65,6.60)-(14.65,4.75,6.60)
- Z09_W3 (exterior wall, Default_Ext_Wall): (14.65,7.65,3.00)-(7.20,7.65,3.00)-(7.20,7.65,6.60)-(14.65,7.65,6.60)
- Z09_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_W2): (7.20,4.75,6.60)-(7.20,7.65,6.60)-(7.20,7.65,3.00)-(7.20,4.75,3.00)
- Z09_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z02_F1_Office_N, adjacent_surface=Z02_Ceiling2): (7.20,4.75,3.00)-(7.20,7.65,3.00)-(9.70,7.65,3.00)-(9.70,4.75,3.00)
- Z09_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z03_F1_Office_NE, adjacent_surface=Z03_Ceiling): (9.70,4.75,3.00)-(9.70,7.65,3.00)-(14.65,7.65,3.00)-(14.65,4.75,3.00)
- Z09_Roof (roof roof, Default_Roof): (7.20,4.75,6.60)-(14.65,4.75,6.60)-(14.65,7.65,6.60)-(7.20,7.65,6.60)

**Z10_F2_Corridor_C**:
- Z10_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_W3): (-0.10,2.75,3.00)-(3.50,2.75,3.00)-(3.50,2.75,6.60)-(-0.10,2.75,6.60)
- Z10_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W3): (3.50,2.75,3.00)-(7.20,2.75,3.00)-(7.20,2.75,6.60)-(3.50,2.75,6.60)
- Z10_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W3): (7.20,2.75,3.00)-(11.00,2.75,3.00)-(11.00,2.75,6.60)-(7.20,2.75,6.60)
- Z10_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_W3): (11.00,2.75,3.00)-(14.65,2.75,3.00)-(14.65,2.75,6.60)-(11.00,2.75,6.60)
- Z10_W5 (exterior wall, Default_Ext_Wall): (14.65,2.75,3.00)-(14.65,4.75,3.00)-(14.65,4.75,6.60)-(14.65,2.75,6.60)
- Z10_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F2_Conference_NE, adjacent_surface=Z09_W1): (7.20,4.75,6.60)-(14.65,4.75,6.60)-(14.65,4.75,3.00)-(7.20,4.75,3.00)
- Z10_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F2_Conference_NW, adjacent_surface=Z08_W1): (-0.10,4.75,6.60)-(7.20,4.75,6.60)-(7.20,4.75,3.00)-(-0.10,4.75,3.00)
- Z10_W8 (exterior wall, Default_Ext_Wall): (-0.10,4.75,3.00)-(-0.10,2.75,3.00)-(-0.10,2.75,6.60)-(-0.10,4.75,6.60)
- Z10_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z04_F1_Corridor_C, adjacent_surface=Z04_Ceiling): (-0.10,2.75,3.00)-(-0.10,4.75,3.00)-(14.65,4.75,3.00)-(14.65,2.75,3.00)
- Z10_Roof (roof roof, Default_Roof): (-0.10,2.75,6.60)-(14.65,2.75,6.60)-(14.65,4.75,6.60)-(-0.10,4.75,6.60)

**Z11_F2_Office_SW**:
- Z11_W1 (exterior wall, Default_Ext_Wall): (-0.10,-0.10,3.00)-(3.50,-0.10,3.00)-(3.50,-0.10,6.60)-(-0.10,-0.10,6.60)
- Z11_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W4): (3.50,-0.10,3.00)-(3.50,2.75,3.00)-(3.50,2.75,6.60)-(3.50,-0.10,6.60)
- Z11_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W1): (-0.10,2.75,6.60)-(3.50,2.75,6.60)-(3.50,2.75,3.00)-(-0.10,2.75,3.00)
- Z11_W4 (exterior wall, Default_Ext_Wall): (-0.10,2.75,3.00)-(-0.10,-0.10,3.00)-(-0.10,-0.10,6.60)-(-0.10,2.75,6.60)
- Z11_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_Ceiling1): (-0.10,-0.10,3.00)-(-0.10,2.75,3.00)-(3.50,2.75,3.00)-(3.50,-0.10,3.00)
- Z11_Roof (roof roof, Default_Roof): (-0.10,-0.10,6.60)-(3.50,-0.10,6.60)-(3.50,2.75,6.60)-(-0.10,2.75,6.60)

**Z12_F2_Office_SW**:
- Z12_W1 (exterior wall, Default_Ext_Wall): (3.50,-0.10,3.00)-(7.20,-0.10,3.00)-(7.20,-0.10,6.60)-(3.50,-0.10,6.60)
- Z12_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W4): (7.20,-0.10,3.00)-(7.20,2.75,3.00)-(7.20,2.75,6.60)-(7.20,-0.10,6.60)
- Z12_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W2): (3.50,2.75,6.60)-(7.20,2.75,6.60)-(7.20,2.75,3.00)-(3.50,2.75,3.00)
- Z12_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F2_Office_SW, adjacent_surface=Z11_W2): (3.50,-0.10,6.60)-(3.50,2.75,6.60)-(3.50,2.75,3.00)-(3.50,-0.10,3.00)
- Z12_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z05_F1_Office_SW, adjacent_surface=Z05_Ceiling2): (3.50,-0.10,3.00)-(3.50,2.75,3.00)-(4.75,2.75,3.00)-(4.75,-0.10,3.00)
- Z12_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_Ceiling1): (4.75,-0.10,3.00)-(4.75,2.75,3.00)-(7.20,2.75,3.00)-(7.20,-0.10,3.00)
- Z12_Roof (roof roof, Default_Roof): (3.50,-0.10,6.60)-(7.20,-0.10,6.60)-(7.20,2.75,6.60)-(3.50,2.75,6.60)

**Z13_F2_Office_SE**:
- Z13_W1 (exterior wall, Default_Ext_Wall): (7.20,-0.10,3.00)-(11.00,-0.10,3.00)-(11.00,-0.10,6.60)-(7.20,-0.10,6.60)
- Z13_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z14_F2_Office_SE, adjacent_surface=Z14_W4): (11.00,-0.10,3.00)-(11.00,2.75,3.00)-(11.00,2.75,6.60)-(11.00,-0.10,6.60)
- Z13_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W3): (7.20,2.75,6.60)-(11.00,2.75,6.60)-(11.00,2.75,3.00)-(7.20,2.75,3.00)
- Z13_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z12_F2_Office_SW, adjacent_surface=Z12_W2): (7.20,-0.10,6.60)-(7.20,2.75,6.60)-(7.20,2.75,3.00)-(7.20,-0.10,3.00)
- Z13_Floor1 (interzone floor, Cons_InterFloor, adjacent_zone=Z06_F1_Office_S, adjacent_surface=Z06_Ceiling2): (7.20,-0.10,3.00)-(7.20,2.75,3.00)-(9.70,2.75,3.00)-(9.70,-0.10,3.00)
- Z13_Floor2 (interzone floor, Cons_InterFloor, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_Ceiling1): (9.70,-0.10,3.00)-(9.70,2.75,3.00)-(11.00,2.75,3.00)-(11.00,-0.10,3.00)
- Z13_Roof (roof roof, Default_Roof): (7.20,-0.10,6.60)-(11.00,-0.10,6.60)-(11.00,2.75,6.60)-(7.20,2.75,6.60)

**Z14_F2_Office_SE**:
- Z14_W1 (exterior wall, Default_Ext_Wall): (11.00,-0.10,3.00)-(14.65,-0.10,3.00)-(14.65,-0.10,6.60)-(11.00,-0.10,6.60)
- Z14_W2 (exterior wall, Default_Ext_Wall): (14.65,-0.10,3.00)-(14.65,2.75,3.00)-(14.65,2.75,6.60)-(14.65,-0.10,6.60)
- Z14_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F2_Corridor_C, adjacent_surface=Z10_W4): (11.00,2.75,6.60)-(14.65,2.75,6.60)-(14.65,2.75,3.00)-(11.00,2.75,3.00)
- Z14_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z13_F2_Office_SE, adjacent_surface=Z13_W2): (11.00,-0.10,6.60)-(11.00,2.75,6.60)-(11.00,2.75,3.00)-(11.00,-0.10,3.00)
- Z14_Floor (interzone floor, Cons_InterFloor, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_Ceiling2): (11.00,-0.10,3.00)-(11.00,2.75,3.00)-(14.65,2.75,3.00)-(14.65,-0.10,3.00)
- Z14_Roof (roof roof, Default_Roof): (11.00,-0.10,6.60)-(14.65,-0.10,6.60)-(14.65,2.75,6.60)-(11.00,2.75,6.60)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- Z01_W3_Win1: parent=Z01_W3, Construction=Default_Window, z=1.00-2.60, vertices: (1.00,7.65,2.60)-(3.40,7.65,2.60)-(3.40,7.65,1.00)-(1.00,7.65,1.00)
- Z02_W3_Win1: parent=Z02_W3, Construction=Default_Window, z=1.00-2.60, vertices: (5.84,7.65,2.60)-(8.24,7.65,2.60)-(8.24,7.65,1.00)-(5.84,7.65,1.00)
- Z03_W3_Win1: parent=Z03_W3, Construction=Default_Window, z=1.00-2.60, vertices: (10.88,7.65,2.60)-(13.28,7.65,2.60)-(13.28,7.65,1.00)-(10.88,7.65,1.00)
- Z04_W4_Win1: parent=Z04_W4, Construction=Default_Window, z=1.00-2.80, vertices: (14.65,3.16,1.00)-(14.65,4.36,1.00)-(14.65,4.36,2.80)-(14.65,3.16,2.80)
- Z05_W1_Win1: parent=Z05_W1, Construction=Default_Window, z=1.50-2.10, vertices: (3.20,-0.10,1.50)-(4.40,-0.10,1.50)-(4.40,-0.10,2.10)-(3.20,-0.10,2.10)
- Z06_W1_Win1: parent=Z06_W1, Construction=Default_Window, z=1.00-2.60, vertices: (6.06,-0.10,1.00)-(8.46,-0.10,1.00)-(8.46,-0.10,2.60)-(6.06,-0.10,2.60)
- Z07_W1_Win1: parent=Z07_W1, Construction=Default_Window, z=1.00-2.60, vertices: (11.12,-0.10,1.00)-(13.52,-0.10,1.00)-(13.52,-0.10,2.60)-(11.12,-0.10,2.60)
- Z08_W3_Win1: parent=Z08_W3, Construction=Default_Window, z=4.00-5.80, vertices: (1.71,7.65,5.80)-(5.31,7.65,5.80)-(5.31,7.65,4.00)-(1.71,7.65,4.00)
- Z09_W3_Win1: parent=Z09_W3, Construction=Default_Window, z=4.00-5.80, vertices: (9.21,7.65,5.80)-(12.81,7.65,5.80)-(12.81,7.65,4.00)-(9.21,7.65,4.00)
- Z10_W5_Win1: parent=Z10_W5, Construction=Default_Window, z=4.00-5.80, vertices: (14.65,3.16,4.00)-(14.65,4.36,4.00)-(14.65,4.36,5.80)-(14.65,3.16,5.80)
- Z10_W8_Win1: parent=Z10_W8, Construction=Default_Window, z=4.00-5.80, vertices: (-0.10,3.16,5.80)-(-0.10,4.36,5.80)-(-0.10,4.36,4.00)-(-0.10,3.16,4.00)
- Z11_W1_Win1: parent=Z11_W1, Construction=Default_Window, z=4.00-5.80, vertices: (1.95,-0.10,4.00)-(3.15,-0.10,4.00)-(3.15,-0.10,5.80)-(1.95,-0.10,5.80)
- Z12_W1_Win1: parent=Z12_W1, Construction=Default_Window, z=4.00-5.80, vertices: (5.07,-0.10,4.00)-(6.27,-0.10,4.00)-(6.27,-0.10,5.80)-(5.07,-0.10,5.80)
- Z13_W1_Win1: parent=Z13_W1, Construction=Default_Window, z=4.00-5.80, vertices: (8.25,-0.10,4.00)-(9.45,-0.10,4.00)-(9.45,-0.10,5.80)-(8.25,-0.10,5.80)
- Z14_W1_Win1: parent=Z14_W1, Construction=Default_Window, z=4.00-5.80, vertices: (11.37,-0.10,4.00)-(12.57,-0.10,4.00)-(12.57,-0.10,5.80)-(11.37,-0.10,5.80)
