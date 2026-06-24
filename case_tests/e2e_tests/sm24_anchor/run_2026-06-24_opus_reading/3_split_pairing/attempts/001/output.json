# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 4.50):
- Z01_F1_Reception_N: x[-0.10,9.90], y[16.10,19.90], z_floor=0.00, ceiling_height=4.50, role: reception.
- Z02_F1_Office_NE: x[5.90,9.90], y[15.05,16.10], z_floor=0.00, ceiling_height=4.50, role: office.
- Z03_F1_Office_NW: x[-0.10,4.10], y[13.00,16.10], z_floor=0.00, ceiling_height=4.50, role: office.
- Z04_F1_Office_NE: x[5.90,9.90], y[8.10,15.05], z_floor=0.00, ceiling_height=4.50, role: office.
- Z05_F1_Office_NW: x[-0.10,4.10], y[8.10,13.00], z_floor=0.00, ceiling_height=4.50, role: office.
- Z06_F1_Corridor_N: x[4.10,5.90], y[4.95,16.10], z_floor=0.00, ceiling_height=4.50, role: corridor.
- Z07_F1_Office_SE: x[5.90,9.90], y[4.95,8.10], z_floor=0.00, ceiling_height=4.50, role: office.
- Z08_F1_Office_SE: x[9.60,9.90], y[4.05,4.95], z_floor=0.00, ceiling_height=4.50, role: office.
- Z09_F1_Conference_SW: x[-0.10,4.10], y[-0.10,8.10], z_floor=0.00, ceiling_height=4.50, role: conference.
- Z10_F1_Corridor_SE: x[4.10,9.60], y[-0.10,4.95], z_floor=0.00, ceiling_height=4.50, role: corridor.
- Z11_F1_Office_SE: x[9.60,9.90], y[-0.10,4.05], z_floor=0.00, ceiling_height=4.50, role: office.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**Z01_F1_Reception_N**:
- Z01_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_W3): (-0.10,16.10,0.00)-(4.10,16.10,0.00)-(4.10,16.10,4.50)-(-0.10,16.10,4.50)
- Z01_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W5): (4.10,16.10,0.00)-(5.90,16.10,0.00)-(5.90,16.10,4.50)-(4.10,16.10,4.50)
- Z01_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_NE, adjacent_surface=Z02_W3): (5.90,16.10,0.00)-(9.90,16.10,0.00)-(9.90,16.10,4.50)-(5.90,16.10,4.50)
- Z01_W4 (exterior wall, Default_Ext_Wall): (9.90,16.10,0.00)-(9.90,19.90,0.00)-(9.90,19.90,4.50)-(9.90,16.10,4.50)
- Z01_W5 (exterior wall, Default_Ext_Wall): (9.90,19.90,0.00)-(-0.10,19.90,0.00)-(-0.10,19.90,4.50)-(9.90,19.90,4.50)
- Z01_W6 (exterior wall, Default_Ext_Wall): (-0.10,19.90,0.00)-(-0.10,16.10,0.00)-(-0.10,16.10,4.50)-(-0.10,19.90,4.50)
- Z01_Floor (ground floor, Default_GroundFloor): (-0.10,19.90,0.00)-(9.90,19.90,0.00)-(9.90,16.10,0.00)-(-0.10,16.10,0.00)
- Z01_Roof (roof roof, Default_Roof): (-0.10,16.10,4.50)-(9.90,16.10,4.50)-(9.90,19.90,4.50)-(-0.10,19.90,4.50)

**Z02_F1_Office_NE**:
- Z02_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_NE, adjacent_surface=Z04_W3): (5.90,15.05,0.00)-(9.90,15.05,0.00)-(9.90,15.05,4.50)-(5.90,15.05,4.50)
- Z02_W2 (exterior wall, Default_Ext_Wall): (9.90,15.05,0.00)-(9.90,16.10,0.00)-(9.90,16.10,4.50)-(9.90,15.05,4.50)
- Z02_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Reception_N, adjacent_surface=Z01_W3): (5.90,16.10,4.50)-(9.90,16.10,4.50)-(9.90,16.10,0.00)-(5.90,16.10,0.00)
- Z02_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W4): (5.90,16.10,0.00)-(5.90,15.05,0.00)-(5.90,15.05,4.50)-(5.90,16.10,4.50)
- Z02_Floor (ground floor, Default_GroundFloor): (5.90,16.10,0.00)-(9.90,16.10,0.00)-(9.90,15.05,0.00)-(5.90,15.05,0.00)
- Z02_Roof (roof roof, Default_Roof): (5.90,15.05,4.50)-(9.90,15.05,4.50)-(9.90,16.10,4.50)-(5.90,16.10,4.50)

**Z03_F1_Office_NW**:
- Z03_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_NW, adjacent_surface=Z05_W3): (-0.10,13.00,0.00)-(4.10,13.00,0.00)-(4.10,13.00,4.50)-(-0.10,13.00,4.50)
- Z03_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W6): (4.10,13.00,0.00)-(4.10,16.10,0.00)-(4.10,16.10,4.50)-(4.10,13.00,4.50)
- Z03_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Reception_N, adjacent_surface=Z01_W1): (-0.10,16.10,4.50)-(4.10,16.10,4.50)-(4.10,16.10,0.00)-(-0.10,16.10,0.00)
- Z03_W4 (exterior wall, Default_Ext_Wall): (-0.10,16.10,0.00)-(-0.10,13.00,0.00)-(-0.10,13.00,4.50)-(-0.10,16.10,4.50)
- Z03_Floor (ground floor, Default_GroundFloor): (-0.10,16.10,0.00)-(4.10,16.10,0.00)-(4.10,13.00,0.00)-(-0.10,13.00,0.00)
- Z03_Roof (roof roof, Default_Roof): (-0.10,13.00,4.50)-(4.10,13.00,4.50)-(4.10,16.10,4.50)-(-0.10,16.10,4.50)

**Z04_F1_Office_NE**:
- Z04_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W4): (5.90,8.10,0.00)-(9.90,8.10,0.00)-(9.90,8.10,4.50)-(5.90,8.10,4.50)
- Z04_W2 (exterior wall, Default_Ext_Wall): (9.90,8.10,0.00)-(9.90,15.05,0.00)-(9.90,15.05,4.50)-(9.90,8.10,4.50)
- Z04_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_NE, adjacent_surface=Z02_W1): (5.90,15.05,4.50)-(9.90,15.05,4.50)-(9.90,15.05,0.00)-(5.90,15.05,0.00)
- Z04_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W3): (5.90,15.05,0.00)-(5.90,8.10,0.00)-(5.90,8.10,4.50)-(5.90,15.05,4.50)
- Z04_Floor (ground floor, Default_GroundFloor): (5.90,15.05,0.00)-(9.90,15.05,0.00)-(9.90,8.10,0.00)-(5.90,8.10,0.00)
- Z04_Roof (roof roof, Default_Roof): (5.90,8.10,4.50)-(9.90,8.10,4.50)-(9.90,15.05,4.50)-(5.90,15.05,4.50)

**Z05_F1_Office_NW**:
- Z05_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F1_Conference_SW, adjacent_surface=Z09_W4): (-0.10,8.10,0.00)-(4.10,8.10,0.00)-(4.10,8.10,4.50)-(-0.10,8.10,4.50)
- Z05_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W7): (4.10,8.10,0.00)-(4.10,13.00,0.00)-(4.10,13.00,4.50)-(4.10,8.10,4.50)
- Z05_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_W1): (-0.10,13.00,4.50)-(4.10,13.00,4.50)-(4.10,13.00,0.00)-(-0.10,13.00,0.00)
- Z05_W4 (exterior wall, Default_Ext_Wall): (-0.10,13.00,0.00)-(-0.10,8.10,0.00)-(-0.10,8.10,4.50)-(-0.10,13.00,4.50)
- Z05_Floor (ground floor, Default_GroundFloor): (-0.10,13.00,0.00)-(4.10,13.00,0.00)-(4.10,8.10,0.00)-(-0.10,8.10,0.00)
- Z05_Roof (roof roof, Default_Roof): (-0.10,8.10,4.50)-(4.10,8.10,4.50)-(4.10,13.00,4.50)-(-0.10,13.00,4.50)

**Z06_F1_Corridor_N**:
- Z06_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Corridor_SE, adjacent_surface=Z10_W5): (4.10,4.95,0.00)-(5.90,4.95,0.00)-(5.90,4.95,4.50)-(4.10,4.95,4.50)
- Z06_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W5): (5.90,4.95,0.00)-(5.90,8.10,0.00)-(5.90,8.10,4.50)-(5.90,4.95,4.50)
- Z06_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_NE, adjacent_surface=Z04_W4): (5.90,15.05,4.50)-(5.90,8.10,4.50)-(5.90,8.10,0.00)-(5.90,15.05,0.00)
- Z06_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Office_NE, adjacent_surface=Z02_W4): (5.90,16.10,4.50)-(5.90,15.05,4.50)-(5.90,15.05,0.00)-(5.90,16.10,0.00)
- Z06_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Reception_N, adjacent_surface=Z01_W2): (4.10,16.10,4.50)-(5.90,16.10,4.50)-(5.90,16.10,0.00)-(4.10,16.10,0.00)
- Z06_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Office_NW, adjacent_surface=Z03_W2): (4.10,13.00,4.50)-(4.10,16.10,4.50)-(4.10,16.10,0.00)-(4.10,13.00,0.00)
- Z06_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_NW, adjacent_surface=Z05_W2): (4.10,8.10,4.50)-(4.10,13.00,4.50)-(4.10,13.00,0.00)-(4.10,8.10,0.00)
- Z06_W8 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F1_Conference_SW, adjacent_surface=Z09_W3): (4.10,8.10,0.00)-(4.10,4.95,0.00)-(4.10,4.95,4.50)-(4.10,8.10,4.50)
- Z06_Floor (ground floor, Default_GroundFloor): (4.10,16.10,0.00)-(5.90,16.10,0.00)-(5.90,4.95,0.00)-(4.10,4.95,0.00)
- Z06_Roof (roof roof, Default_Roof): (4.10,4.95,4.50)-(5.90,4.95,4.50)-(5.90,16.10,4.50)-(4.10,16.10,4.50)

**Z07_F1_Office_SE**:
- Z07_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Corridor_SE, adjacent_surface=Z10_W4): (5.90,4.95,0.00)-(9.60,4.95,0.00)-(9.60,4.95,4.50)-(5.90,4.95,4.50)
- Z07_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_SE, adjacent_surface=Z08_W3): (9.60,4.95,0.00)-(9.90,4.95,0.00)-(9.90,4.95,4.50)-(9.60,4.95,4.50)
- Z07_W3 (exterior wall, Default_Ext_Wall): (9.90,4.95,0.00)-(9.90,8.10,0.00)-(9.90,8.10,4.50)-(9.90,4.95,4.50)
- Z07_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_NE, adjacent_surface=Z04_W1): (5.90,8.10,4.50)-(9.90,8.10,4.50)-(9.90,8.10,0.00)-(5.90,8.10,0.00)
- Z07_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W2): (5.90,4.95,4.50)-(5.90,8.10,4.50)-(5.90,8.10,0.00)-(5.90,4.95,0.00)
- Z07_Floor (ground floor, Default_GroundFloor): (5.90,8.10,0.00)-(9.90,8.10,0.00)-(9.90,4.95,0.00)-(5.90,4.95,0.00)
- Z07_Roof (roof roof, Default_Roof): (5.90,4.95,4.50)-(9.90,4.95,4.50)-(9.90,8.10,4.50)-(5.90,8.10,4.50)

**Z08_F1_Office_SE**:
- Z08_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F1_Office_SE, adjacent_surface=Z11_W3): (9.60,4.05,0.00)-(9.90,4.05,0.00)-(9.90,4.05,4.50)-(9.60,4.05,4.50)
- Z08_W2 (exterior wall, Default_Ext_Wall): (9.90,4.05,0.00)-(9.90,4.95,0.00)-(9.90,4.95,4.50)-(9.90,4.05,4.50)
- Z08_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W2): (9.60,4.95,4.50)-(9.90,4.95,4.50)-(9.90,4.95,0.00)-(9.60,4.95,0.00)
- Z08_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Corridor_SE, adjacent_surface=Z10_W3): (9.60,4.95,0.00)-(9.60,4.05,0.00)-(9.60,4.05,4.50)-(9.60,4.95,4.50)
- Z08_Floor (ground floor, Default_GroundFloor): (9.60,4.95,0.00)-(9.90,4.95,0.00)-(9.90,4.05,0.00)-(9.60,4.05,0.00)
- Z08_Roof (roof roof, Default_Roof): (9.60,4.05,4.50)-(9.90,4.05,4.50)-(9.90,4.95,4.50)-(9.60,4.95,4.50)

**Z09_F1_Conference_SW**:
- Z09_W1 (exterior wall, Default_Ext_Wall): (-0.10,-0.10,0.00)-(4.10,-0.10,0.00)-(4.10,-0.10,4.50)-(-0.10,-0.10,4.50)
- Z09_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Corridor_SE, adjacent_surface=Z10_W6): (4.10,-0.10,0.00)-(4.10,4.95,0.00)-(4.10,4.95,4.50)-(4.10,-0.10,4.50)
- Z09_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W8): (4.10,8.10,4.50)-(4.10,4.95,4.50)-(4.10,4.95,0.00)-(4.10,8.10,0.00)
- Z09_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_NW, adjacent_surface=Z05_W1): (-0.10,8.10,4.50)-(4.10,8.10,4.50)-(4.10,8.10,0.00)-(-0.10,8.10,0.00)
- Z09_W5 (exterior wall, Default_Ext_Wall): (-0.10,8.10,0.00)-(-0.10,-0.10,0.00)-(-0.10,-0.10,4.50)-(-0.10,8.10,4.50)
- Z09_Floor (ground floor, Default_GroundFloor): (-0.10,8.10,0.00)-(4.10,8.10,0.00)-(4.10,-0.10,0.00)-(-0.10,-0.10,0.00)
- Z09_Roof (roof roof, Default_Roof): (-0.10,-0.10,4.50)-(4.10,-0.10,4.50)-(4.10,8.10,4.50)-(-0.10,8.10,4.50)

**Z10_F1_Corridor_SE**:
- Z10_W1 (exterior wall, Default_Ext_Wall): (4.10,-0.10,0.00)-(9.60,-0.10,0.00)-(9.60,-0.10,4.50)-(4.10,-0.10,4.50)
- Z10_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z11_F1_Office_SE, adjacent_surface=Z11_W4): (9.60,-0.10,0.00)-(9.60,4.05,0.00)-(9.60,4.05,4.50)-(9.60,-0.10,4.50)
- Z10_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_SE, adjacent_surface=Z08_W4): (9.60,4.95,4.50)-(9.60,4.05,4.50)-(9.60,4.05,0.00)-(9.60,4.95,0.00)
- Z10_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Office_SE, adjacent_surface=Z07_W1): (5.90,4.95,4.50)-(9.60,4.95,4.50)-(9.60,4.95,0.00)-(5.90,4.95,0.00)
- Z10_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_N, adjacent_surface=Z06_W1): (4.10,4.95,4.50)-(5.90,4.95,4.50)-(5.90,4.95,0.00)-(4.10,4.95,0.00)
- Z10_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z09_F1_Conference_SW, adjacent_surface=Z09_W2): (4.10,-0.10,4.50)-(4.10,4.95,4.50)-(4.10,4.95,0.00)-(4.10,-0.10,0.00)
- Z10_Floor (ground floor, Default_GroundFloor): (4.10,4.95,0.00)-(9.60,4.95,0.00)-(9.60,-0.10,0.00)-(4.10,-0.10,0.00)
- Z10_Roof (roof roof, Default_Roof): (4.10,-0.10,4.50)-(9.60,-0.10,4.50)-(9.60,4.95,4.50)-(4.10,4.95,4.50)

**Z11_F1_Office_SE**:
- Z11_W1 (exterior wall, Default_Ext_Wall): (9.60,-0.10,0.00)-(9.90,-0.10,0.00)-(9.90,-0.10,4.50)-(9.60,-0.10,4.50)
- Z11_W2 (exterior wall, Default_Ext_Wall): (9.90,-0.10,0.00)-(9.90,4.05,0.00)-(9.90,4.05,4.50)-(9.90,-0.10,4.50)
- Z11_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_SE, adjacent_surface=Z08_W1): (9.60,4.05,4.50)-(9.90,4.05,4.50)-(9.90,4.05,0.00)-(9.60,4.05,0.00)
- Z11_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z10_F1_Corridor_SE, adjacent_surface=Z10_W2): (9.60,-0.10,4.50)-(9.60,4.05,4.50)-(9.60,4.05,0.00)-(9.60,-0.10,0.00)
- Z11_Floor (ground floor, Default_GroundFloor): (9.60,4.05,0.00)-(9.90,4.05,0.00)-(9.90,-0.10,0.00)-(9.60,-0.10,0.00)
- Z11_Roof (roof roof, Default_Roof): (9.60,-0.10,4.50)-(9.90,-0.10,4.50)-(9.90,4.05,4.50)-(9.60,4.05,4.50)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- Z01_W4_Win1: parent=Z01_W4, Construction=Default_Window, z=1.00-2.80, vertices: (9.90,17.96,1.00)-(9.90,19.46,1.00)-(9.90,19.46,2.80)-(9.90,17.96,2.80)
- Z01_W5_Win1: parent=Z01_W5, Construction=Default_Window, z=1.00-3.40, vertices: (4.66,19.90,3.40)-(9.46,19.90,3.40)-(9.46,19.90,1.00)-(4.66,19.90,1.00)
- Z01_W6_Win1: parent=Z01_W6, Construction=Default_Window, z=1.00-2.80, vertices: (-0.10,17.96,2.80)-(-0.10,19.46,2.80)-(-0.10,19.46,1.00)-(-0.10,17.96,1.00)
- Z02_W2_Win1: parent=Z02_W2, Construction=Default_Window, z=1.00-2.80, vertices: (9.90,15.05,1.00)-(9.90,15.58,1.00)-(9.90,15.58,2.80)-(9.90,15.05,2.80)
- Z03_W4_Win1: parent=Z03_W4, Construction=Default_Window, z=1.00-2.80, vertices: (-0.10,14.38,2.80)-(-0.10,15.58,2.80)-(-0.10,15.58,1.00)-(-0.10,14.38,1.00)
- Z04_W2_Win1: parent=Z04_W2, Construction=Default_Window, z=1.00-3.40, vertices: (9.90,8.84,1.00)-(9.90,13.64,1.00)-(9.90,13.64,3.40)-(9.90,8.84,3.40)
- Z05_W4_Win1: parent=Z05_W4, Construction=Default_Window, z=1.00-2.80, vertices: (-0.10,8.42,2.80)-(-0.10,9.92,2.80)-(-0.10,9.92,1.00)-(-0.10,8.42,1.00)
- Z05_W4_Win2: parent=Z05_W4, Construction=Default_Window, z=1.00-2.80, vertices: (-0.10,11.14,2.80)-(-0.10,12.64,2.80)-(-0.10,12.64,1.00)-(-0.10,11.14,1.00)
- Z09_W1_Win1: parent=Z09_W1, Construction=Default_Window, z=1.00-2.80, vertices: (0.54,-0.10,1.00)-(2.04,-0.10,1.00)-(2.04,-0.10,2.80)-(0.54,-0.10,2.80)
- Z09_W5_Win1: parent=Z09_W5, Construction=Default_Window, z=1.00-3.40, vertices: (-0.10,0.54,3.40)-(-0.10,5.34,3.40)-(-0.10,5.34,1.00)-(-0.10,0.54,1.00)
- Z10_W1_Win1: parent=Z10_W1, Construction=Default_Window, z=1.00-2.80, vertices: (7.96,-0.10,1.00)-(9.46,-0.10,1.00)-(9.46,-0.10,2.80)-(7.96,-0.10,2.80)
