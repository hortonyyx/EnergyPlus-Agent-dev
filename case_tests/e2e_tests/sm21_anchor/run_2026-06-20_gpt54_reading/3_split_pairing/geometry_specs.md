# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 3.00):
- F1_office_01: x[0.10,5.00], y[0.10,3.10], z_floor=0.00, ceiling_height=3.00, role: office.
- F1_office_02: x[5.00,10.00], y[0.10,3.10], z_floor=0.00, ceiling_height=3.00, role: office.
- F1_office_03: x[10.00,14.90], y[0.10,3.10], z_floor=0.00, ceiling_height=3.00, role: office.
- F1_corridor: x[0.10,14.90], y[3.10,4.90], z_floor=0.00, ceiling_height=3.00, role: corridor.
- F1_office_04: x[0.10,5.00], y[4.90,7.90], z_floor=0.00, ceiling_height=3.00, role: office.
- F1_office_05: x[5.00,10.00], y[4.90,7.90], z_floor=0.00, ceiling_height=3.00, role: office.
- F1_office_06: x[10.00,14.90], y[4.90,7.90], z_floor=0.00, ceiling_height=3.00, role: office.

Floor 2 (z 3.00 to 6.60):
- F2_office_01: x[0.10,3.75], y[0.10,3.20], z_floor=3.00, ceiling_height=3.60, role: office.
- F2_office_02: x[3.75,7.50], y[0.10,3.20], z_floor=3.00, ceiling_height=3.60, role: office.
- F2_office_03: x[7.50,11.25], y[0.10,3.20], z_floor=3.00, ceiling_height=3.60, role: office.
- F2_office_04: x[11.25,14.90], y[0.10,3.20], z_floor=3.00, ceiling_height=3.60, role: office.
- F2_corridor: x[0.10,14.90], y[3.20,4.80], z_floor=3.00, ceiling_height=3.60, role: corridor.
- F2_conference_01: x[0.10,7.50], y[4.80,7.90], z_floor=3.00, ceiling_height=3.60, role: conference.
- F2_conference_02: x[7.50,14.90], y[4.80,7.90], z_floor=3.00, ceiling_height=3.60, role: conference.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**F1_office_01**:
- F1_office_01_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_office_02, adjacent_surface=F1_office_02_Wall): (5.00,0.10,0.00)-(5.00,3.10,0.00)-(5.00,3.10,3.00)-(5.00,0.10,3.00)
- F1_office_01_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Wall): (5.00,3.10,0.00)-(0.10,3.10,0.00)-(0.10,3.10,3.00)-(5.00,3.10,3.00)
- F1_office_01_Wall_3 (exterior wall, Default_Ext_Wall): (0.10,0.10,0.00)-(5.00,0.10,0.00)-(5.00,0.10,3.00)-(0.10,0.10,3.00)
- F1_office_01_Wall_4 (exterior wall, Default_Ext_Wall): (0.10,3.10,0.00)-(0.10,0.10,0.00)-(0.10,0.10,3.00)-(0.10,3.10,3.00)
- F1_office_01_Floor (ground floor, Default_GroundFloor): (0.10,3.10,0.00)-(5.00,3.10,0.00)-(5.00,0.10,0.00)-(0.10,0.10,0.00)
- F1_office_01_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_01, adjacent_surface=F2_office_01_Floor): (3.75,0.10,3.00)-(3.75,3.10,3.00)-(0.10,3.10,3.00)-(0.10,0.10,3.00)
- F1_office_01_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_02, adjacent_surface=F2_office_02_Floor): (5.00,0.10,3.00)-(5.00,3.10,3.00)-(3.75,3.10,3.00)-(3.75,0.10,3.00)

**F1_office_02**:
- F1_office_02_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_office_01, adjacent_surface=F1_office_01_Wall): (5.00,0.10,3.00)-(5.00,3.10,3.00)-(5.00,3.10,0.00)-(5.00,0.10,0.00)
- F1_office_02_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_03, adjacent_surface=F1_office_03_Wall): (10.00,0.10,0.00)-(10.00,3.10,0.00)-(10.00,3.10,3.00)-(10.00,0.10,3.00)
- F1_office_02_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Wall_2): (10.00,3.10,0.00)-(5.00,3.10,0.00)-(5.00,3.10,3.00)-(10.00,3.10,3.00)
- F1_office_02_Wall_4 (exterior wall, Default_Ext_Wall): (5.00,0.10,0.00)-(10.00,0.10,0.00)-(10.00,0.10,3.00)-(5.00,0.10,3.00)
- F1_office_02_Floor (ground floor, Default_GroundFloor): (5.00,3.10,0.00)-(10.00,3.10,0.00)-(10.00,0.10,0.00)-(5.00,0.10,0.00)
- F1_office_02_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_02, adjacent_surface=F2_office_02_Floor_2): (7.50,0.10,3.00)-(7.50,3.10,3.00)-(5.00,3.10,3.00)-(5.00,0.10,3.00)
- F1_office_02_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_03, adjacent_surface=F2_office_03_Floor): (10.00,0.10,3.00)-(10.00,3.10,3.00)-(7.50,3.10,3.00)-(7.50,0.10,3.00)

**F1_office_03**:
- F1_office_03_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_office_02, adjacent_surface=F1_office_02_Wall_2): (10.00,0.10,3.00)-(10.00,3.10,3.00)-(10.00,3.10,0.00)-(10.00,0.10,0.00)
- F1_office_03_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Wall_3): (14.90,3.10,0.00)-(10.00,3.10,0.00)-(10.00,3.10,3.00)-(14.90,3.10,3.00)
- F1_office_03_Wall_3 (exterior wall, Default_Ext_Wall): (10.00,0.10,0.00)-(14.90,0.10,0.00)-(14.90,0.10,3.00)-(10.00,0.10,3.00)
- F1_office_03_Wall_4 (exterior wall, Default_Ext_Wall): (14.90,0.10,0.00)-(14.90,3.10,0.00)-(14.90,3.10,3.00)-(14.90,0.10,3.00)
- F1_office_03_Floor (ground floor, Default_GroundFloor): (10.00,3.10,0.00)-(14.90,3.10,0.00)-(14.90,0.10,0.00)-(10.00,0.10,0.00)
- F1_office_03_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_03, adjacent_surface=F2_office_03_Floor_2): (11.25,0.10,3.00)-(11.25,3.10,3.00)-(10.00,3.10,3.00)-(10.00,0.10,3.00)
- F1_office_03_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_04, adjacent_surface=F2_office_04_Floor): (14.90,0.10,3.00)-(14.90,3.10,3.00)-(11.25,3.10,3.00)-(11.25,0.10,3.00)

**F1_corridor**:
- F1_corridor_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_office_01, adjacent_surface=F1_office_01_Wall_2): (5.00,3.10,3.00)-(0.10,3.10,3.00)-(0.10,3.10,0.00)-(5.00,3.10,0.00)
- F1_corridor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_02, adjacent_surface=F1_office_02_Wall_3): (10.00,3.10,3.00)-(5.00,3.10,3.00)-(5.00,3.10,0.00)-(10.00,3.10,0.00)
- F1_corridor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_03, adjacent_surface=F1_office_03_Wall_2): (14.90,3.10,3.00)-(10.00,3.10,3.00)-(10.00,3.10,0.00)-(14.90,3.10,0.00)
- F1_corridor_Wall_4 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_04, adjacent_surface=F1_office_04_Wall): (5.00,4.90,0.00)-(0.10,4.90,0.00)-(0.10,4.90,3.00)-(5.00,4.90,3.00)
- F1_corridor_Wall_5 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_05, adjacent_surface=F1_office_05_Wall): (10.00,4.90,0.00)-(5.00,4.90,0.00)-(5.00,4.90,3.00)-(10.00,4.90,3.00)
- F1_corridor_Wall_6 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_06, adjacent_surface=F1_office_06_Wall): (14.90,4.90,0.00)-(10.00,4.90,0.00)-(10.00,4.90,3.00)-(14.90,4.90,3.00)
- F1_corridor_Wall_7 (exterior wall, Default_Ext_Wall): (14.90,3.10,0.00)-(14.90,4.90,0.00)-(14.90,4.90,3.00)-(14.90,3.10,3.00)
- F1_corridor_Wall_8 (exterior wall, Default_Ext_Wall): (0.10,4.90,0.00)-(0.10,3.10,0.00)-(0.10,3.10,3.00)-(0.10,4.90,3.00)
- F1_corridor_Floor (ground floor, Default_GroundFloor): (0.10,4.90,0.00)-(14.90,4.90,0.00)-(14.90,3.10,0.00)-(0.10,3.10,0.00)
- F1_corridor_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_01, adjacent_surface=F2_office_01_Floor_2): (0.10,3.20,3.00)-(0.10,3.10,3.00)-(3.75,3.10,3.00)-(3.75,3.20,3.00)
- F1_corridor_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_02, adjacent_surface=F2_office_02_Floor_3): (3.75,3.10,3.00)-(7.50,3.10,3.00)-(7.50,3.20,3.00)-(3.75,3.20,3.00)
- F1_corridor_Ceiling_3 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_03, adjacent_surface=F2_office_03_Floor_3): (7.50,3.10,3.00)-(11.25,3.10,3.00)-(11.25,3.20,3.00)-(7.50,3.20,3.00)
- F1_corridor_Ceiling_4 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_office_04, adjacent_surface=F2_office_04_Floor_2): (14.90,3.20,3.00)-(11.25,3.20,3.00)-(11.25,3.10,3.00)-(14.90,3.10,3.00)
- F1_corridor_Ceiling_5 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Floor): (14.90,3.20,3.00)-(14.90,4.80,3.00)-(0.10,4.80,3.00)-(0.10,3.20,3.00)
- F1_corridor_Ceiling_6 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_conference_01, adjacent_surface=F2_conference_01_Floor): (7.50,4.90,3.00)-(0.10,4.90,3.00)-(0.10,4.80,3.00)-(7.50,4.80,3.00)
- F1_corridor_Ceiling_7 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_conference_02, adjacent_surface=F2_conference_02_Floor): (14.90,4.80,3.00)-(14.90,4.90,3.00)-(7.50,4.90,3.00)-(7.50,4.80,3.00)

**F1_office_04**:
- F1_office_04_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Wall_4): (5.00,4.90,3.00)-(0.10,4.90,3.00)-(0.10,4.90,0.00)-(5.00,4.90,0.00)
- F1_office_04_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_05, adjacent_surface=F1_office_05_Wall_2): (5.00,4.90,0.00)-(5.00,7.90,0.00)-(5.00,7.90,3.00)-(5.00,4.90,3.00)
- F1_office_04_Wall_3 (exterior wall, Default_Ext_Wall): (5.00,7.90,0.00)-(0.10,7.90,0.00)-(0.10,7.90,3.00)-(5.00,7.90,3.00)
- F1_office_04_Wall_4 (exterior wall, Default_Ext_Wall): (0.10,7.90,0.00)-(0.10,4.90,0.00)-(0.10,4.90,3.00)-(0.10,7.90,3.00)
- F1_office_04_Floor (ground floor, Default_GroundFloor): (0.10,7.90,0.00)-(5.00,7.90,0.00)-(5.00,4.90,0.00)-(0.10,4.90,0.00)
- F1_office_04_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_conference_01, adjacent_surface=F2_conference_01_Floor_2): (0.10,7.90,3.00)-(0.10,4.90,3.00)-(5.00,4.90,3.00)-(5.00,7.90,3.00)

**F1_office_05**:
- F1_office_05_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Wall_5): (10.00,4.90,3.00)-(5.00,4.90,3.00)-(5.00,4.90,0.00)-(10.00,4.90,0.00)
- F1_office_05_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_04, adjacent_surface=F1_office_04_Wall_2): (5.00,4.90,3.00)-(5.00,7.90,3.00)-(5.00,7.90,0.00)-(5.00,4.90,0.00)
- F1_office_05_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_06, adjacent_surface=F1_office_06_Wall_2): (10.00,4.90,0.00)-(10.00,7.90,0.00)-(10.00,7.90,3.00)-(10.00,4.90,3.00)
- F1_office_05_Wall_4 (exterior wall, Default_Ext_Wall): (10.00,7.90,0.00)-(5.00,7.90,0.00)-(5.00,7.90,3.00)-(10.00,7.90,3.00)
- F1_office_05_Floor (ground floor, Default_GroundFloor): (5.00,7.90,0.00)-(10.00,7.90,0.00)-(10.00,4.90,0.00)-(5.00,4.90,0.00)
- F1_office_05_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_conference_01, adjacent_surface=F2_conference_01_Floor_3): (7.50,7.90,3.00)-(5.00,7.90,3.00)-(5.00,4.90,3.00)-(7.50,4.90,3.00)
- F1_office_05_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_conference_02, adjacent_surface=F2_conference_02_Floor_2): (7.50,7.90,3.00)-(7.50,4.90,3.00)-(10.00,4.90,3.00)-(10.00,7.90,3.00)

**F1_office_06**:
- F1_office_06_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Wall_6): (14.90,4.90,3.00)-(10.00,4.90,3.00)-(10.00,4.90,0.00)-(14.90,4.90,0.00)
- F1_office_06_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_office_05, adjacent_surface=F1_office_05_Wall_3): (10.00,4.90,3.00)-(10.00,7.90,3.00)-(10.00,7.90,0.00)-(10.00,4.90,0.00)
- F1_office_06_Wall_3 (exterior wall, Default_Ext_Wall): (14.90,4.90,0.00)-(14.90,7.90,0.00)-(14.90,7.90,3.00)-(14.90,4.90,3.00)
- F1_office_06_Wall_4 (exterior wall, Default_Ext_Wall): (14.90,7.90,0.00)-(10.00,7.90,0.00)-(10.00,7.90,3.00)-(14.90,7.90,3.00)
- F1_office_06_Floor (ground floor, Default_GroundFloor): (10.00,7.90,0.00)-(14.90,7.90,0.00)-(14.90,4.90,0.00)-(10.00,4.90,0.00)
- F1_office_06_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_conference_02, adjacent_surface=F2_conference_02_Floor_3): (14.90,7.90,3.00)-(10.00,7.90,3.00)-(10.00,4.90,3.00)-(14.90,4.90,3.00)

**F2_office_01**:
- F2_office_01_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_office_02, adjacent_surface=F2_office_02_Wall): (3.75,0.10,3.00)-(3.75,3.20,3.00)-(3.75,3.20,6.60)-(3.75,0.10,6.60)
- F2_office_01_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Wall): (3.75,3.20,3.00)-(0.10,3.20,3.00)-(0.10,3.20,6.60)-(3.75,3.20,6.60)
- F2_office_01_Wall_3 (exterior wall, Default_Ext_Wall): (0.10,0.10,3.00)-(3.75,0.10,3.00)-(3.75,0.10,6.60)-(0.10,0.10,6.60)
- F2_office_01_Wall_4 (exterior wall, Default_Ext_Wall): (0.10,3.20,3.00)-(0.10,0.10,3.00)-(0.10,0.10,6.60)-(0.10,3.20,6.60)
- F2_office_01_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_01, adjacent_surface=F1_office_01_Ceiling): (0.10,0.10,3.00)-(0.10,3.10,3.00)-(3.75,3.10,3.00)-(3.75,0.10,3.00)
- F2_office_01_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling): (3.75,3.20,3.00)-(3.75,3.10,3.00)-(0.10,3.10,3.00)-(0.10,3.20,3.00)
- F2_office_01_Roof (roof roof, Default_Roof): (0.10,0.10,6.60)-(3.75,0.10,6.60)-(3.75,3.20,6.60)-(0.10,3.20,6.60)

**F2_office_02**:
- F2_office_02_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_office_01, adjacent_surface=F2_office_01_Wall): (3.75,0.10,6.60)-(3.75,3.20,6.60)-(3.75,3.20,3.00)-(3.75,0.10,3.00)
- F2_office_02_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_office_03, adjacent_surface=F2_office_03_Wall): (7.50,0.10,3.00)-(7.50,3.20,3.00)-(7.50,3.20,6.60)-(7.50,0.10,6.60)
- F2_office_02_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Wall_2): (7.50,3.20,3.00)-(3.75,3.20,3.00)-(3.75,3.20,6.60)-(7.50,3.20,6.60)
- F2_office_02_Wall_4 (exterior wall, Default_Ext_Wall): (3.75,0.10,3.00)-(7.50,0.10,3.00)-(7.50,0.10,6.60)-(3.75,0.10,6.60)
- F2_office_02_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_01, adjacent_surface=F1_office_01_Ceiling_2): (3.75,0.10,3.00)-(3.75,3.10,3.00)-(5.00,3.10,3.00)-(5.00,0.10,3.00)
- F2_office_02_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_02, adjacent_surface=F1_office_02_Ceiling): (5.00,0.10,3.00)-(5.00,3.10,3.00)-(7.50,3.10,3.00)-(7.50,0.10,3.00)
- F2_office_02_Floor_3 (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling_2): (3.75,3.20,3.00)-(7.50,3.20,3.00)-(7.50,3.10,3.00)-(3.75,3.10,3.00)
- F2_office_02_Roof (roof roof, Default_Roof): (3.75,0.10,6.60)-(7.50,0.10,6.60)-(7.50,3.20,6.60)-(3.75,3.20,6.60)

**F2_office_03**:
- F2_office_03_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_office_02, adjacent_surface=F2_office_02_Wall_2): (7.50,0.10,6.60)-(7.50,3.20,6.60)-(7.50,3.20,3.00)-(7.50,0.10,3.00)
- F2_office_03_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_office_04, adjacent_surface=F2_office_04_Wall): (11.25,0.10,3.00)-(11.25,3.20,3.00)-(11.25,3.20,6.60)-(11.25,0.10,6.60)
- F2_office_03_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Wall_3): (11.25,3.20,3.00)-(7.50,3.20,3.00)-(7.50,3.20,6.60)-(11.25,3.20,6.60)
- F2_office_03_Wall_4 (exterior wall, Default_Ext_Wall): (7.50,0.10,3.00)-(11.25,0.10,3.00)-(11.25,0.10,6.60)-(7.50,0.10,6.60)
- F2_office_03_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_02, adjacent_surface=F1_office_02_Ceiling_2): (7.50,0.10,3.00)-(7.50,3.10,3.00)-(10.00,3.10,3.00)-(10.00,0.10,3.00)
- F2_office_03_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_03, adjacent_surface=F1_office_03_Ceiling): (10.00,0.10,3.00)-(10.00,3.10,3.00)-(11.25,3.10,3.00)-(11.25,0.10,3.00)
- F2_office_03_Floor_3 (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling_3): (7.50,3.20,3.00)-(11.25,3.20,3.00)-(11.25,3.10,3.00)-(7.50,3.10,3.00)
- F2_office_03_Roof (roof roof, Default_Roof): (7.50,0.10,6.60)-(11.25,0.10,6.60)-(11.25,3.20,6.60)-(7.50,3.20,6.60)

**F2_office_04**:
- F2_office_04_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_office_03, adjacent_surface=F2_office_03_Wall_2): (11.25,0.10,6.60)-(11.25,3.20,6.60)-(11.25,3.20,3.00)-(11.25,0.10,3.00)
- F2_office_04_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Wall_4): (14.90,3.20,3.00)-(11.25,3.20,3.00)-(11.25,3.20,6.60)-(14.90,3.20,6.60)
- F2_office_04_Wall_3 (exterior wall, Default_Ext_Wall): (11.25,0.10,3.00)-(14.90,0.10,3.00)-(14.90,0.10,6.60)-(11.25,0.10,6.60)
- F2_office_04_Wall_4 (exterior wall, Default_Ext_Wall): (14.90,0.10,3.00)-(14.90,3.20,3.00)-(14.90,3.20,6.60)-(14.90,0.10,6.60)
- F2_office_04_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_03, adjacent_surface=F1_office_03_Ceiling_2): (11.25,0.10,3.00)-(11.25,3.10,3.00)-(14.90,3.10,3.00)-(14.90,0.10,3.00)
- F2_office_04_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling_4): (14.90,3.10,3.00)-(11.25,3.10,3.00)-(11.25,3.20,3.00)-(14.90,3.20,3.00)
- F2_office_04_Roof (roof roof, Default_Roof): (11.25,0.10,6.60)-(14.90,0.10,6.60)-(14.90,3.20,6.60)-(11.25,3.20,6.60)

**F2_corridor**:
- F2_corridor_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_office_01, adjacent_surface=F2_office_01_Wall_2): (3.75,3.20,6.60)-(0.10,3.20,6.60)-(0.10,3.20,3.00)-(3.75,3.20,3.00)
- F2_corridor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_office_02, adjacent_surface=F2_office_02_Wall_3): (7.50,3.20,6.60)-(3.75,3.20,6.60)-(3.75,3.20,3.00)-(7.50,3.20,3.00)
- F2_corridor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_office_03, adjacent_surface=F2_office_03_Wall_3): (11.25,3.20,6.60)-(7.50,3.20,6.60)-(7.50,3.20,3.00)-(11.25,3.20,3.00)
- F2_corridor_Wall_4 (interior wall, Default_Int_Wall, adjacent_zone=F2_office_04, adjacent_surface=F2_office_04_Wall_2): (14.90,3.20,6.60)-(11.25,3.20,6.60)-(11.25,3.20,3.00)-(14.90,3.20,3.00)
- F2_corridor_Wall_5 (interior wall, Default_Int_Wall, adjacent_zone=F2_conference_01, adjacent_surface=F2_conference_01_Wall): (7.50,4.80,3.00)-(0.10,4.80,3.00)-(0.10,4.80,6.60)-(7.50,4.80,6.60)
- F2_corridor_Wall_6 (interior wall, Default_Int_Wall, adjacent_zone=F2_conference_02, adjacent_surface=F2_conference_02_Wall): (14.90,4.80,3.00)-(7.50,4.80,3.00)-(7.50,4.80,6.60)-(14.90,4.80,6.60)
- F2_corridor_Wall_7 (exterior wall, Default_Ext_Wall): (14.90,3.20,3.00)-(14.90,4.80,3.00)-(14.90,4.80,6.60)-(14.90,3.20,6.60)
- F2_corridor_Wall_8 (exterior wall, Default_Ext_Wall): (0.10,4.80,3.00)-(0.10,3.20,3.00)-(0.10,3.20,6.60)-(0.10,4.80,6.60)
- F2_corridor_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling_5): (0.10,3.20,3.00)-(0.10,4.80,3.00)-(14.90,4.80,3.00)-(14.90,3.20,3.00)
- F2_corridor_Roof (roof roof, Default_Roof): (0.10,3.20,6.60)-(14.90,3.20,6.60)-(14.90,4.80,6.60)-(0.10,4.80,6.60)

**F2_conference_01**:
- F2_conference_01_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Wall_5): (7.50,4.80,6.60)-(0.10,4.80,6.60)-(0.10,4.80,3.00)-(7.50,4.80,3.00)
- F2_conference_01_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_conference_02, adjacent_surface=F2_conference_02_Wall_2): (7.50,4.80,3.00)-(7.50,7.90,3.00)-(7.50,7.90,6.60)-(7.50,4.80,6.60)
- F2_conference_01_Wall_3 (exterior wall, Default_Ext_Wall): (7.50,7.90,3.00)-(0.10,7.90,3.00)-(0.10,7.90,6.60)-(7.50,7.90,6.60)
- F2_conference_01_Wall_4 (exterior wall, Default_Ext_Wall): (0.10,7.90,3.00)-(0.10,4.80,3.00)-(0.10,4.80,6.60)-(0.10,7.90,6.60)
- F2_conference_01_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling_6): (7.50,4.80,3.00)-(0.10,4.80,3.00)-(0.10,4.90,3.00)-(7.50,4.90,3.00)
- F2_conference_01_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_04, adjacent_surface=F1_office_04_Ceiling): (5.00,7.90,3.00)-(5.00,4.90,3.00)-(0.10,4.90,3.00)-(0.10,7.90,3.00)
- F2_conference_01_Floor_3 (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_05, adjacent_surface=F1_office_05_Ceiling): (7.50,4.90,3.00)-(5.00,4.90,3.00)-(5.00,7.90,3.00)-(7.50,7.90,3.00)
- F2_conference_01_Roof (roof roof, Default_Roof): (0.10,4.80,6.60)-(7.50,4.80,6.60)-(7.50,7.90,6.60)-(0.10,7.90,6.60)

**F2_conference_02**:
- F2_conference_02_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_corridor, adjacent_surface=F2_corridor_Wall_6): (14.90,4.80,6.60)-(7.50,4.80,6.60)-(7.50,4.80,3.00)-(14.90,4.80,3.00)
- F2_conference_02_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_conference_01, adjacent_surface=F2_conference_01_Wall_2): (7.50,4.80,6.60)-(7.50,7.90,6.60)-(7.50,7.90,3.00)-(7.50,4.80,3.00)
- F2_conference_02_Wall_3 (exterior wall, Default_Ext_Wall): (14.90,4.80,3.00)-(14.90,7.90,3.00)-(14.90,7.90,6.60)-(14.90,4.80,6.60)
- F2_conference_02_Wall_4 (exterior wall, Default_Ext_Wall): (14.90,7.90,3.00)-(7.50,7.90,3.00)-(7.50,7.90,6.60)-(14.90,7.90,6.60)
- F2_conference_02_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_corridor, adjacent_surface=F1_corridor_Ceiling_7): (7.50,4.80,3.00)-(7.50,4.90,3.00)-(14.90,4.90,3.00)-(14.90,4.80,3.00)
- F2_conference_02_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_05, adjacent_surface=F1_office_05_Ceiling_2): (10.00,7.90,3.00)-(10.00,4.90,3.00)-(7.50,4.90,3.00)-(7.50,7.90,3.00)
- F2_conference_02_Floor_3 (interzone floor, Cons_InterFloor, adjacent_zone=F1_office_06, adjacent_surface=F1_office_06_Ceiling): (14.90,4.90,3.00)-(10.00,4.90,3.00)-(10.00,7.90,3.00)-(14.90,7.90,3.00)
- F2_conference_02_Roof (roof roof, Default_Roof): (7.50,4.80,6.60)-(14.90,4.80,6.60)-(14.90,7.90,6.60)-(7.50,7.90,6.60)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- F1_office_04_Win: parent=F1_office_04_Wall_3, Construction=Default_Window, z=1.00-2.60, vertices: (1.24,7.90,2.60)-(3.64,7.90,2.60)-(3.64,7.90,1.00)-(1.24,7.90,1.00)
- F1_office_05_Win: parent=F1_office_05_Wall_4, Construction=Default_Window, z=1.00-2.60, vertices: (6.30,7.90,2.60)-(8.70,7.90,2.60)-(8.70,7.90,1.00)-(6.30,7.90,1.00)
- F1_office_06_Win: parent=F1_office_06_Wall_4, Construction=Default_Window, z=1.00-2.60, vertices: (11.36,7.90,2.60)-(13.76,7.90,2.60)-(13.76,7.90,1.00)-(11.36,7.90,1.00)
- F1_office_01_Win: parent=F1_office_01_Wall_3, Construction=Default_Window, z=1.50-2.10, vertices: (3.44,0.10,1.50)-(4.64,0.10,1.50)-(4.64,0.10,2.10)-(3.44,0.10,2.10)
- F1_office_02_Win: parent=F1_office_02_Wall_4, Construction=Default_Window, z=1.00-2.60, vertices: (6.30,0.10,1.00)-(8.70,0.10,1.00)-(8.70,0.10,2.60)-(6.30,0.10,2.60)
- F1_office_03_Win: parent=F1_office_03_Wall_3, Construction=Default_Window, z=1.00-2.60, vertices: (11.36,0.10,1.00)-(13.76,0.10,1.00)-(13.76,0.10,2.60)-(11.36,0.10,2.60)
- F1_corridor_Win: parent=F1_corridor_Wall_7, Construction=Default_Window, z=1.00-2.80, vertices: (14.90,3.28,1.00)-(14.90,4.48,1.00)-(14.90,4.48,2.80)-(14.90,3.28,2.80)
- F2_office_01_Win: parent=F2_office_01_Wall_3, Construction=Default_Window, z=4.00-5.80, vertices: (2.19,0.10,4.00)-(3.39,0.10,4.00)-(3.39,0.10,5.80)-(2.19,0.10,5.80)
- F2_office_02_Win: parent=F2_office_02_Wall_4, Construction=Default_Window, z=4.00-5.80, vertices: (4.11,0.10,4.00)-(5.31,0.10,4.00)-(5.31,0.10,5.80)-(4.11,0.10,5.80)
- F2_office_03_Win: parent=F2_office_03_Wall_4, Construction=Default_Window, z=4.00-5.80, vertices: (9.69,0.10,4.00)-(10.89,0.10,4.00)-(10.89,0.10,5.80)-(9.69,0.10,5.80)
- F2_office_04_Win: parent=F2_office_04_Wall_3, Construction=Default_Window, z=4.00-5.80, vertices: (11.61,0.10,4.00)-(12.81,0.10,4.00)-(12.81,0.10,5.80)-(11.61,0.10,5.80)
- F2_conference_01_Win: parent=F2_conference_01_Wall_3, Construction=Default_Window, z=4.00-5.80, vertices: (1.95,7.90,5.80)-(5.55,7.90,5.80)-(5.55,7.90,4.00)-(1.95,7.90,4.00)
- F2_conference_02_Win: parent=F2_conference_02_Wall_4, Construction=Default_Window, z=4.00-5.80, vertices: (9.45,7.90,5.80)-(13.05,7.90,5.80)-(13.05,7.90,4.00)-(9.45,7.90,4.00)
- F2_corridor_Win: parent=F2_corridor_Wall_7, Construction=Default_Window, z=4.00-5.80, vertices: (14.90,3.40,4.00)-(14.90,4.60,4.00)-(14.90,4.60,5.80)-(14.90,3.40,5.80)
- F2_corridor_Win_2: parent=F2_corridor_Wall_8, Construction=Default_Window, z=4.00-5.80, vertices: (0.10,3.40,5.80)-(0.10,4.60,5.80)-(0.10,4.60,4.00)-(0.10,3.40,4.00)
