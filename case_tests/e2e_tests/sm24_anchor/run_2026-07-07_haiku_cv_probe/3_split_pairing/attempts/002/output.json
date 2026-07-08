# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 4.50):
- Z01_F1_Office_N: x[0.12,9.88], y[15.94,19.88], z_floor=0.00, ceiling_height=4.50, role: office.
- Z02_F1_Storage_NE: x[5.82,9.88], y[14.00,15.94], z_floor=0.00, ceiling_height=4.50, role: storage.
- Z03_F1_Meeting_NW: x[0.12,4.18], y[13.00,15.94], z_floor=0.00, ceiling_height=4.50, role: meeting.
- Z04_F1_Office_NE: x[5.82,9.88], y[8.06,14.00], z_floor=0.00, ceiling_height=4.50, role: office.
- Z05_F1_Office_NW: x[0.12,4.18], y[8.06,13.00], z_floor=0.00, ceiling_height=4.50, role: office.
- Z06_F1_Corridor_SE: x[4.18,9.88], y[0.12,15.94], z_floor=0.00, ceiling_height=4.50, role: corridor.
- Z07_F1_Conference_SW: x[0.12,4.18], y[0.12,8.06], z_floor=0.00, ceiling_height=4.50, role: conference.
- Z08_F1_Office_SE: x[5.82,9.88], y[0.12,4.94], z_floor=0.00, ceiling_height=4.50, role: office.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**Z01_F1_Office_N**:
- Z01_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Meeting_NW, adjacent_surface=Z03_W3): (0.12,15.94,0.00)-(4.18,15.94,0.00)-(4.18,15.94,4.50)-(0.12,15.94,4.50)
- Z01_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W8): (4.18,15.94,0.00)-(5.82,15.94,0.00)-(5.82,15.94,4.50)-(4.18,15.94,4.50)
- Z01_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Storage_NE, adjacent_surface=Z02_W3): (5.82,15.94,0.00)-(9.88,15.94,0.00)-(9.88,15.94,4.50)-(5.82,15.94,4.50)
- Z01_W4 (exterior wall, Default_Ext_Wall): (9.88,15.94,0.00)-(9.88,19.88,0.00)-(9.88,19.88,4.50)-(9.88,15.94,4.50)
- Z01_W5 (exterior wall, Default_Ext_Wall): (9.88,19.88,0.00)-(0.12,19.88,0.00)-(0.12,19.88,4.50)-(9.88,19.88,4.50)
- Z01_W6 (exterior wall, Default_Ext_Wall): (0.12,19.88,0.00)-(0.12,15.94,0.00)-(0.12,15.94,4.50)-(0.12,19.88,4.50)
- Z01_Floor (ground floor, Default_GroundFloor): (0.12,19.88,0.00)-(9.88,19.88,0.00)-(9.88,15.94,0.00)-(0.12,15.94,0.00)
- Z01_Roof (roof roof, Default_Roof): (0.12,15.94,4.50)-(9.88,15.94,4.50)-(9.88,19.88,4.50)-(0.12,19.88,4.50)

**Z02_F1_Storage_NE**:
- Z02_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_NE, adjacent_surface=Z04_W3): (5.82,14.00,0.00)-(9.88,14.00,0.00)-(9.88,14.00,4.50)-(5.82,14.00,4.50)
- Z02_W2 (exterior wall, Default_Ext_Wall): (9.88,14.00,0.00)-(9.88,15.94,0.00)-(9.88,15.94,4.50)-(9.88,14.00,4.50)
- Z02_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_N, adjacent_surface=Z01_W3): (5.82,15.94,4.50)-(9.88,15.94,4.50)-(9.88,15.94,0.00)-(5.82,15.94,0.00)
- Z02_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W7): (5.82,15.94,0.00)-(5.82,14.00,0.00)-(5.82,14.00,4.50)-(5.82,15.94,4.50)
- Z02_Floor (ground floor, Default_GroundFloor): (5.82,15.94,0.00)-(9.88,15.94,0.00)-(9.88,14.00,0.00)-(5.82,14.00,0.00)
- Z02_Roof (roof roof, Default_Roof): (5.82,14.00,4.50)-(9.88,14.00,4.50)-(9.88,15.94,4.50)-(5.82,15.94,4.50)

**Z03_F1_Meeting_NW**:
- Z03_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_NW, adjacent_surface=Z05_W3): (0.12,13.00,0.00)-(4.18,13.00,0.00)-(4.18,13.00,4.50)-(0.12,13.00,4.50)
- Z03_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W9): (4.18,13.00,0.00)-(4.18,15.94,0.00)-(4.18,15.94,4.50)-(4.18,13.00,4.50)
- Z03_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_N, adjacent_surface=Z01_W1): (0.12,15.94,4.50)-(4.18,15.94,4.50)-(4.18,15.94,0.00)-(0.12,15.94,0.00)
- Z03_W4 (exterior wall, Default_Ext_Wall): (0.12,15.94,0.00)-(0.12,13.00,0.00)-(0.12,13.00,4.50)-(0.12,15.94,4.50)
- Z03_Floor (ground floor, Default_GroundFloor): (0.12,15.94,0.00)-(4.18,15.94,0.00)-(4.18,13.00,0.00)-(0.12,13.00,0.00)
- Z03_Roof (roof roof, Default_Roof): (0.12,13.00,4.50)-(4.18,13.00,4.50)-(4.18,15.94,4.50)-(0.12,15.94,4.50)

**Z04_F1_Office_NE**:
- Z04_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W5): (5.82,8.06,0.00)-(9.88,8.06,0.00)-(9.88,8.06,4.50)-(5.82,8.06,4.50)
- Z04_W2 (exterior wall, Default_Ext_Wall): (9.88,8.06,0.00)-(9.88,14.00,0.00)-(9.88,14.00,4.50)-(9.88,8.06,4.50)
- Z04_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Storage_NE, adjacent_surface=Z02_W1): (5.82,14.00,4.50)-(9.88,14.00,4.50)-(9.88,14.00,0.00)-(5.82,14.00,0.00)
- Z04_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W6): (5.82,14.00,0.00)-(5.82,8.06,0.00)-(5.82,8.06,4.50)-(5.82,14.00,4.50)
- Z04_Floor (ground floor, Default_GroundFloor): (5.82,14.00,0.00)-(9.88,14.00,0.00)-(9.88,8.06,0.00)-(5.82,8.06,0.00)
- Z04_Roof (roof roof, Default_Roof): (5.82,8.06,4.50)-(9.88,8.06,4.50)-(9.88,14.00,4.50)-(5.82,14.00,4.50)

**Z05_F1_Office_NW**:
- Z05_W1 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Conference_SW, adjacent_surface=Z07_W3): (0.12,8.06,0.00)-(4.18,8.06,0.00)-(4.18,8.06,4.50)-(0.12,8.06,4.50)
- Z05_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W10): (4.18,8.06,0.00)-(4.18,13.00,0.00)-(4.18,13.00,4.50)-(4.18,8.06,4.50)
- Z05_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Meeting_NW, adjacent_surface=Z03_W1): (0.12,13.00,4.50)-(4.18,13.00,4.50)-(4.18,13.00,0.00)-(0.12,13.00,0.00)
- Z05_W4 (exterior wall, Default_Ext_Wall): (0.12,13.00,0.00)-(0.12,8.06,0.00)-(0.12,8.06,4.50)-(0.12,13.00,4.50)
- Z05_Floor (ground floor, Default_GroundFloor): (0.12,13.00,0.00)-(4.18,13.00,0.00)-(4.18,8.06,0.00)-(0.12,8.06,0.00)
- Z05_Roof (roof roof, Default_Roof): (0.12,8.06,4.50)-(4.18,8.06,4.50)-(4.18,13.00,4.50)-(0.12,13.00,4.50)

**Z06_F1_Corridor_SE**:
- Z06_W1 (exterior wall, Default_Ext_Wall): (4.18,0.12,0.00)-(5.82,0.12,0.00)-(5.82,0.12,4.50)-(4.18,0.12,4.50)
- Z06_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_SE, adjacent_surface=Z08_W4): (5.82,0.12,0.00)-(5.82,4.94,0.00)-(5.82,4.94,4.50)-(5.82,0.12,4.50)
- Z06_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z08_F1_Office_SE, adjacent_surface=Z08_W3): (5.82,4.94,0.00)-(9.88,4.94,0.00)-(9.88,4.94,4.50)-(5.82,4.94,4.50)
- Z06_W4 (exterior wall, Default_Ext_Wall): (9.88,4.94,0.00)-(9.88,8.06,0.00)-(9.88,8.06,4.50)-(9.88,4.94,4.50)
- Z06_W5 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_NE, adjacent_surface=Z04_W1): (5.82,8.06,4.50)-(9.88,8.06,4.50)-(9.88,8.06,0.00)-(5.82,8.06,0.00)
- Z06_W6 (interior wall, Default_Int_Wall, adjacent_zone=Z04_F1_Office_NE, adjacent_surface=Z04_W4): (5.82,14.00,4.50)-(5.82,8.06,4.50)-(5.82,8.06,0.00)-(5.82,14.00,0.00)
- Z06_W7 (interior wall, Default_Int_Wall, adjacent_zone=Z02_F1_Storage_NE, adjacent_surface=Z02_W4): (5.82,15.94,4.50)-(5.82,14.00,4.50)-(5.82,14.00,0.00)-(5.82,15.94,0.00)
- Z06_W8 (interior wall, Default_Int_Wall, adjacent_zone=Z01_F1_Office_N, adjacent_surface=Z01_W2): (4.18,15.94,4.50)-(5.82,15.94,4.50)-(5.82,15.94,0.00)-(4.18,15.94,0.00)
- Z06_W9 (interior wall, Default_Int_Wall, adjacent_zone=Z03_F1_Meeting_NW, adjacent_surface=Z03_W2): (4.18,13.00,4.50)-(4.18,15.94,4.50)-(4.18,15.94,0.00)-(4.18,13.00,0.00)
- Z06_W10 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_NW, adjacent_surface=Z05_W2): (4.18,8.06,4.50)-(4.18,13.00,4.50)-(4.18,13.00,0.00)-(4.18,8.06,0.00)
- Z06_W11 (interior wall, Default_Int_Wall, adjacent_zone=Z07_F1_Conference_SW, adjacent_surface=Z07_W2): (4.18,8.06,0.00)-(4.18,0.12,0.00)-(4.18,0.12,4.50)-(4.18,8.06,4.50)
- Z06_Floor (ground floor, Default_GroundFloor): (4.18,15.94,0.00)-(5.82,15.94,0.00)-(5.82,8.06,0.00)-(9.88,8.06,0.00)-(9.88,4.94,0.00)-(5.82,4.94,0.00)-(5.82,0.12,0.00)-(4.18,0.12,0.00)
- Z06_Roof (roof roof, Default_Roof): (4.18,0.12,4.50)-(5.82,0.12,4.50)-(5.82,4.94,4.50)-(9.88,4.94,4.50)-(9.88,8.06,4.50)-(5.82,8.06,4.50)-(5.82,15.94,4.50)-(4.18,15.94,4.50)

**Z07_F1_Conference_SW**:
- Z07_W1 (exterior wall, Default_Ext_Wall): (0.12,0.12,0.00)-(4.18,0.12,0.00)-(4.18,0.12,4.50)-(0.12,0.12,4.50)
- Z07_W2 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W11): (4.18,8.06,4.50)-(4.18,0.12,4.50)-(4.18,0.12,0.00)-(4.18,8.06,0.00)
- Z07_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z05_F1_Office_NW, adjacent_surface=Z05_W1): (0.12,8.06,4.50)-(4.18,8.06,4.50)-(4.18,8.06,0.00)-(0.12,8.06,0.00)
- Z07_W4 (exterior wall, Default_Ext_Wall): (0.12,8.06,0.00)-(0.12,0.12,0.00)-(0.12,0.12,4.50)-(0.12,8.06,4.50)
- Z07_Floor (ground floor, Default_GroundFloor): (0.12,8.06,0.00)-(4.18,8.06,0.00)-(4.18,0.12,0.00)-(0.12,0.12,0.00)
- Z07_Roof (roof roof, Default_Roof): (0.12,0.12,4.50)-(4.18,0.12,4.50)-(4.18,8.06,4.50)-(0.12,8.06,4.50)

**Z08_F1_Office_SE**:
- Z08_W1 (exterior wall, Default_Ext_Wall): (5.82,0.12,0.00)-(9.88,0.12,0.00)-(9.88,0.12,4.50)-(5.82,0.12,4.50)
- Z08_W2 (exterior wall, Default_Ext_Wall): (9.88,0.12,0.00)-(9.88,4.94,0.00)-(9.88,4.94,4.50)-(9.88,0.12,4.50)
- Z08_W3 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W3): (5.82,4.94,4.50)-(9.88,4.94,4.50)-(9.88,4.94,0.00)-(5.82,4.94,0.00)
- Z08_W4 (interior wall, Default_Int_Wall, adjacent_zone=Z06_F1_Corridor_SE, adjacent_surface=Z06_W2): (5.82,0.12,4.50)-(5.82,4.94,4.50)-(5.82,4.94,0.00)-(5.82,0.12,0.00)
- Z08_Floor (ground floor, Default_GroundFloor): (5.82,4.94,0.00)-(9.88,4.94,0.00)-(9.88,0.12,0.00)-(5.82,0.12,0.00)
- Z08_Roof (roof roof, Default_Roof): (5.82,0.12,4.50)-(9.88,0.12,4.50)-(9.88,4.94,4.50)-(5.82,4.94,4.50)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- Z01_W4_Win1: parent=Z01_W4, Construction=Default_Window, z=1.00-2.80, vertices: (9.88,17.96,1.00)-(9.88,19.46,1.00)-(9.88,19.46,2.80)-(9.88,17.96,2.80)
- Z01_W5_Win1: parent=Z01_W5, Construction=Default_Window, z=1.00-3.40, vertices: (4.66,19.88,3.40)-(9.46,19.88,3.40)-(9.46,19.88,1.00)-(4.66,19.88,1.00)
- Z01_W6_Win1: parent=Z01_W6, Construction=Default_Window, z=1.00-2.80, vertices: (0.12,17.96,2.80)-(0.12,19.46,2.80)-(0.12,19.46,1.00)-(0.12,17.96,1.00)
- Z02_W2_Win1: parent=Z02_W2, Construction=Default_Window, z=1.00-2.80, vertices: (9.88,14.38,1.00)-(9.88,15.58,1.00)-(9.88,15.58,2.80)-(9.88,14.38,2.80)
- Z03_W4_Win1: parent=Z03_W4, Construction=Default_Window, z=1.00-2.80, vertices: (0.12,14.38,2.80)-(0.12,15.58,2.80)-(0.12,15.58,1.00)-(0.12,14.38,1.00)
- Z04_W2_Win1: parent=Z04_W2, Construction=Default_Window, z=1.00-3.40, vertices: (9.88,8.84,1.00)-(9.88,13.64,1.00)-(9.88,13.64,3.40)-(9.88,8.84,3.40)
- Z05_W4_Win1: parent=Z05_W4, Construction=Default_Window, z=1.00-2.80, vertices: (0.12,8.42,2.80)-(0.12,9.92,2.80)-(0.12,9.92,1.00)-(0.12,8.42,1.00)
- Z05_W4_Win2: parent=Z05_W4, Construction=Default_Window, z=1.00-2.80, vertices: (0.12,11.14,2.80)-(0.12,12.64,2.80)-(0.12,12.64,1.00)-(0.12,11.14,1.00)
- Z07_W1_Win1: parent=Z07_W1, Construction=Default_Window, z=1.00-2.80, vertices: (0.54,0.12,1.00)-(2.04,0.12,1.00)-(2.04,0.12,2.80)-(0.54,0.12,2.80)
- Z07_W4_Win1: parent=Z07_W4, Construction=Default_Window, z=1.00-3.40, vertices: (0.12,0.54,3.40)-(0.12,5.34,3.40)-(0.12,5.34,1.00)-(0.12,0.54,1.00)
- Z08_W1_Win1: parent=Z08_W1, Construction=Default_Window, z=1.00-2.80, vertices: (7.96,0.12,1.00)-(9.46,0.12,1.00)-(9.46,0.12,2.80)-(7.96,0.12,2.80)
