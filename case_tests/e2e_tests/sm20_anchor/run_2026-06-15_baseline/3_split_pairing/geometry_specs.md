# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 3.60):
- F1_SW: x[0.00,5.00], y[0.00,3.00], z_floor=0.00, ceiling_height=3.60, role: office.
- F1_SC: x[5.00,10.00], y[0.00,3.00], z_floor=0.00, ceiling_height=3.60, role: office.
- F1_SE: x[10.00,15.00], y[0.00,3.00], z_floor=0.00, ceiling_height=3.60, role: office.
- F1_Corridor: x[0.00,15.00], y[3.00,5.00], z_floor=0.00, ceiling_height=3.60, role: corridor.
- F1_NW: x[0.00,5.00], y[5.00,8.00], z_floor=0.00, ceiling_height=3.60, role: office.
- F1_NC: x[5.00,10.00], y[5.00,8.00], z_floor=0.00, ceiling_height=3.60, role: office.
- F1_NE: x[10.00,15.00], y[5.00,8.00], z_floor=0.00, ceiling_height=3.60, role: office.

Floor 2 (z 3.60 to 7.20):
- F2_SW: x[0.00,5.00], y[0.00,3.00], z_floor=3.60, ceiling_height=3.60, role: office.
- F2_SC: x[5.00,10.00], y[0.00,3.00], z_floor=3.60, ceiling_height=3.60, role: office.
- F2_SE: x[10.00,15.00], y[0.00,3.00], z_floor=3.60, ceiling_height=3.60, role: office.
- F2_Corridor: x[0.00,15.00], y[3.00,5.00], z_floor=3.60, ceiling_height=3.60, role: corridor.
- F2_NW: x[0.00,3.75], y[5.00,8.00], z_floor=3.60, ceiling_height=3.60, role: office.
- F2_N1: x[3.75,7.50], y[5.00,8.00], z_floor=3.60, ceiling_height=3.60, role: office.
- F2_N2: x[7.50,11.25], y[5.00,8.00], z_floor=3.60, ceiling_height=3.60, role: office.
- F2_NE: x[11.25,15.00], y[5.00,8.00], z_floor=3.60, ceiling_height=3.60, role: office.

Floor 3 (z 7.20 to 12.00):
- F3_SW: x[0.00,7.50], y[0.00,3.00], z_floor=7.20, ceiling_height=4.80, role: office.
- F3_SE: x[7.50,15.00], y[0.00,3.00], z_floor=7.20, ceiling_height=4.80, role: office.
- F3_Corridor: x[0.00,15.00], y[3.00,5.00], z_floor=7.20, ceiling_height=4.80, role: corridor.
- F3_N: x[0.00,15.00], y[5.00,8.00], z_floor=7.20, ceiling_height=4.80, role: office.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**F1_SW**:
- F1_SW_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_SC, adjacent_surface=F1_SC_Wall): (5.00,0.00,0.00)-(5.00,3.00,0.00)-(5.00,3.00,3.60)-(5.00,0.00,3.60)
- F1_SW_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Wall): (5.00,3.00,0.00)-(0.00,3.00,0.00)-(0.00,3.00,3.60)-(5.00,3.00,3.60)
- F1_SW_Wall_3 (exterior wall, Default_Ext_Wall): (0.00,0.00,0.00)-(5.00,0.00,0.00)-(5.00,0.00,3.60)-(0.00,0.00,3.60)
- F1_SW_Wall_4 (exterior wall, Default_Ext_Wall): (0.00,3.00,0.00)-(0.00,0.00,0.00)-(0.00,0.00,3.60)-(0.00,3.00,3.60)
- F1_SW_Floor (ground floor, Default_GroundFloor): (0.00,3.00,0.00)-(5.00,3.00,0.00)-(5.00,0.00,0.00)-(0.00,0.00,0.00)
- F1_SW_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_SW, adjacent_surface=F2_SW_Floor): (5.00,0.00,3.60)-(5.00,3.00,3.60)-(0.00,3.00,3.60)-(0.00,0.00,3.60)

**F1_SC**:
- F1_SC_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_SW, adjacent_surface=F1_SW_Wall): (5.00,0.00,3.60)-(5.00,3.00,3.60)-(5.00,3.00,0.00)-(5.00,0.00,0.00)
- F1_SC_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_SE, adjacent_surface=F1_SE_Wall): (10.00,0.00,0.00)-(10.00,3.00,0.00)-(10.00,3.00,3.60)-(10.00,0.00,3.60)
- F1_SC_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Wall_2): (10.00,3.00,0.00)-(5.00,3.00,0.00)-(5.00,3.00,3.60)-(10.00,3.00,3.60)
- F1_SC_Wall_4 (exterior wall, Default_Ext_Wall): (5.00,0.00,0.00)-(10.00,0.00,0.00)-(10.00,0.00,3.60)-(5.00,0.00,3.60)
- F1_SC_Floor (ground floor, Default_GroundFloor): (5.00,3.00,0.00)-(10.00,3.00,0.00)-(10.00,0.00,0.00)-(5.00,0.00,0.00)
- F1_SC_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_SC, adjacent_surface=F2_SC_Floor): (10.00,0.00,3.60)-(10.00,3.00,3.60)-(5.00,3.00,3.60)-(5.00,0.00,3.60)

**F1_SE**:
- F1_SE_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_SC, adjacent_surface=F1_SC_Wall_2): (10.00,0.00,3.60)-(10.00,3.00,3.60)-(10.00,3.00,0.00)-(10.00,0.00,0.00)
- F1_SE_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Wall_3): (15.00,3.00,0.00)-(10.00,3.00,0.00)-(10.00,3.00,3.60)-(15.00,3.00,3.60)
- F1_SE_Wall_3 (exterior wall, Default_Ext_Wall): (10.00,0.00,0.00)-(15.00,0.00,0.00)-(15.00,0.00,3.60)-(10.00,0.00,3.60)
- F1_SE_Wall_4 (exterior wall, Default_Ext_Wall): (15.00,0.00,0.00)-(15.00,3.00,0.00)-(15.00,3.00,3.60)-(15.00,0.00,3.60)
- F1_SE_Floor (ground floor, Default_GroundFloor): (10.00,3.00,0.00)-(15.00,3.00,0.00)-(15.00,0.00,0.00)-(10.00,0.00,0.00)
- F1_SE_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_SE, adjacent_surface=F2_SE_Floor): (15.00,0.00,3.60)-(15.00,3.00,3.60)-(10.00,3.00,3.60)-(10.00,0.00,3.60)

**F1_Corridor**:
- F1_Corridor_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_SW, adjacent_surface=F1_SW_Wall_2): (5.00,3.00,3.60)-(0.00,3.00,3.60)-(0.00,3.00,0.00)-(5.00,3.00,0.00)
- F1_Corridor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_SC, adjacent_surface=F1_SC_Wall_3): (10.00,3.00,3.60)-(5.00,3.00,3.60)-(5.00,3.00,0.00)-(10.00,3.00,0.00)
- F1_Corridor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F1_SE, adjacent_surface=F1_SE_Wall_2): (15.00,3.00,3.60)-(10.00,3.00,3.60)-(10.00,3.00,0.00)-(15.00,3.00,0.00)
- F1_Corridor_Wall_4 (interior wall, Default_Int_Wall, adjacent_zone=F1_NW, adjacent_surface=F1_NW_Wall): (5.00,5.00,0.00)-(0.00,5.00,0.00)-(0.00,5.00,3.60)-(5.00,5.00,3.60)
- F1_Corridor_Wall_5 (interior wall, Default_Int_Wall, adjacent_zone=F1_NC, adjacent_surface=F1_NC_Wall): (10.00,5.00,0.00)-(5.00,5.00,0.00)-(5.00,5.00,3.60)-(10.00,5.00,3.60)
- F1_Corridor_Wall_6 (interior wall, Default_Int_Wall, adjacent_zone=F1_NE, adjacent_surface=F1_NE_Wall): (15.00,5.00,0.00)-(10.00,5.00,0.00)-(10.00,5.00,3.60)-(15.00,5.00,3.60)
- F1_Corridor_Wall_7 (exterior wall, Default_Ext_Wall): (15.00,3.00,0.00)-(15.00,5.00,0.00)-(15.00,5.00,3.60)-(15.00,3.00,3.60)
- F1_Corridor_Wall_8 (exterior wall, Default_Ext_Wall): (0.00,5.00,0.00)-(0.00,3.00,0.00)-(0.00,3.00,3.60)-(0.00,5.00,3.60)
- F1_Corridor_Floor (ground floor, Default_GroundFloor): (0.00,5.00,0.00)-(15.00,5.00,0.00)-(15.00,3.00,0.00)-(0.00,3.00,0.00)
- F1_Corridor_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Floor): (15.00,3.00,3.60)-(15.00,5.00,3.60)-(0.00,5.00,3.60)-(0.00,3.00,3.60)

**F1_NW**:
- F1_NW_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Wall_4): (5.00,5.00,3.60)-(0.00,5.00,3.60)-(0.00,5.00,0.00)-(5.00,5.00,0.00)
- F1_NW_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_NC, adjacent_surface=F1_NC_Wall_2): (5.00,5.00,0.00)-(5.00,8.00,0.00)-(5.00,8.00,3.60)-(5.00,5.00,3.60)
- F1_NW_Wall_3 (exterior wall, Default_Ext_Wall): (5.00,8.00,0.00)-(0.00,8.00,0.00)-(0.00,8.00,3.60)-(5.00,8.00,3.60)
- F1_NW_Wall_4 (exterior wall, Default_Ext_Wall): (0.00,8.00,0.00)-(0.00,5.00,0.00)-(0.00,5.00,3.60)-(0.00,8.00,3.60)
- F1_NW_Floor (ground floor, Default_GroundFloor): (0.00,8.00,0.00)-(5.00,8.00,0.00)-(5.00,5.00,0.00)-(0.00,5.00,0.00)
- F1_NW_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_NW, adjacent_surface=F2_NW_Floor): (3.75,5.00,3.60)-(3.75,8.00,3.60)-(0.00,8.00,3.60)-(0.00,5.00,3.60)
- F1_NW_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_N1, adjacent_surface=F2_N1_Floor): (5.00,5.00,3.60)-(5.00,8.00,3.60)-(3.75,8.00,3.60)-(3.75,5.00,3.60)

**F1_NC**:
- F1_NC_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Wall_5): (10.00,5.00,3.60)-(5.00,5.00,3.60)-(5.00,5.00,0.00)-(10.00,5.00,0.00)
- F1_NC_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_NW, adjacent_surface=F1_NW_Wall_2): (5.00,5.00,3.60)-(5.00,8.00,3.60)-(5.00,8.00,0.00)-(5.00,5.00,0.00)
- F1_NC_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F1_NE, adjacent_surface=F1_NE_Wall_2): (10.00,5.00,0.00)-(10.00,8.00,0.00)-(10.00,8.00,3.60)-(10.00,5.00,3.60)
- F1_NC_Wall_4 (exterior wall, Default_Ext_Wall): (10.00,8.00,0.00)-(5.00,8.00,0.00)-(5.00,8.00,3.60)-(10.00,8.00,3.60)
- F1_NC_Floor (ground floor, Default_GroundFloor): (5.00,8.00,0.00)-(10.00,8.00,0.00)-(10.00,5.00,0.00)-(5.00,5.00,0.00)
- F1_NC_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_N1, adjacent_surface=F2_N1_Floor_2): (7.50,5.00,3.60)-(7.50,8.00,3.60)-(5.00,8.00,3.60)-(5.00,5.00,3.60)
- F1_NC_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_N2, adjacent_surface=F2_N2_Floor): (10.00,5.00,3.60)-(10.00,8.00,3.60)-(7.50,8.00,3.60)-(7.50,5.00,3.60)

**F1_NE**:
- F1_NE_Wall (interior wall, Default_Int_Wall, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Wall_6): (15.00,5.00,3.60)-(10.00,5.00,3.60)-(10.00,5.00,0.00)-(15.00,5.00,0.00)
- F1_NE_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F1_NC, adjacent_surface=F1_NC_Wall_3): (10.00,5.00,3.60)-(10.00,8.00,3.60)-(10.00,8.00,0.00)-(10.00,5.00,0.00)
- F1_NE_Wall_3 (exterior wall, Default_Ext_Wall): (15.00,5.00,0.00)-(15.00,8.00,0.00)-(15.00,8.00,3.60)-(15.00,5.00,3.60)
- F1_NE_Wall_4 (exterior wall, Default_Ext_Wall): (15.00,8.00,0.00)-(10.00,8.00,0.00)-(10.00,8.00,3.60)-(15.00,8.00,3.60)
- F1_NE_Floor (ground floor, Default_GroundFloor): (10.00,8.00,0.00)-(15.00,8.00,0.00)-(15.00,5.00,0.00)-(10.00,5.00,0.00)
- F1_NE_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_N2, adjacent_surface=F2_N2_Floor_2): (11.25,5.00,3.60)-(11.25,8.00,3.60)-(10.00,8.00,3.60)-(10.00,5.00,3.60)
- F1_NE_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F2_NE, adjacent_surface=F2_NE_Floor): (15.00,5.00,3.60)-(15.00,8.00,3.60)-(11.25,8.00,3.60)-(11.25,5.00,3.60)

**F2_SW**:
- F2_SW_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_SC, adjacent_surface=F2_SC_Wall): (5.00,0.00,3.60)-(5.00,3.00,3.60)-(5.00,3.00,7.20)-(5.00,0.00,7.20)
- F2_SW_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall): (5.00,3.00,3.60)-(0.00,3.00,3.60)-(0.00,3.00,7.20)-(5.00,3.00,7.20)
- F2_SW_Wall_3 (exterior wall, Default_Ext_Wall): (0.00,0.00,3.60)-(5.00,0.00,3.60)-(5.00,0.00,7.20)-(0.00,0.00,7.20)
- F2_SW_Wall_4 (exterior wall, Default_Ext_Wall): (0.00,3.00,3.60)-(0.00,0.00,3.60)-(0.00,0.00,7.20)-(0.00,3.00,7.20)
- F2_SW_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_SW, adjacent_surface=F1_SW_Ceiling): (0.00,0.00,3.60)-(0.00,3.00,3.60)-(5.00,3.00,3.60)-(5.00,0.00,3.60)
- F2_SW_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_SW, adjacent_surface=F3_SW_Floor): (5.00,0.00,7.20)-(5.00,3.00,7.20)-(0.00,3.00,7.20)-(0.00,0.00,7.20)

**F2_SC**:
- F2_SC_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_SW, adjacent_surface=F2_SW_Wall): (5.00,0.00,7.20)-(5.00,3.00,7.20)-(5.00,3.00,3.60)-(5.00,0.00,3.60)
- F2_SC_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_SE, adjacent_surface=F2_SE_Wall): (10.00,0.00,3.60)-(10.00,3.00,3.60)-(10.00,3.00,7.20)-(10.00,0.00,7.20)
- F2_SC_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall_2): (10.00,3.00,3.60)-(5.00,3.00,3.60)-(5.00,3.00,7.20)-(10.00,3.00,7.20)
- F2_SC_Wall_4 (exterior wall, Default_Ext_Wall): (5.00,0.00,3.60)-(10.00,0.00,3.60)-(10.00,0.00,7.20)-(5.00,0.00,7.20)
- F2_SC_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_SC, adjacent_surface=F1_SC_Ceiling): (5.00,0.00,3.60)-(5.00,3.00,3.60)-(10.00,3.00,3.60)-(10.00,0.00,3.60)
- F2_SC_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_SW, adjacent_surface=F3_SW_Floor_2): (7.50,0.00,7.20)-(7.50,3.00,7.20)-(5.00,3.00,7.20)-(5.00,0.00,7.20)
- F2_SC_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_SE, adjacent_surface=F3_SE_Floor): (10.00,0.00,7.20)-(10.00,3.00,7.20)-(7.50,3.00,7.20)-(7.50,0.00,7.20)

**F2_SE**:
- F2_SE_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_SC, adjacent_surface=F2_SC_Wall_2): (10.00,0.00,7.20)-(10.00,3.00,7.20)-(10.00,3.00,3.60)-(10.00,0.00,3.60)
- F2_SE_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall_3): (15.00,3.00,3.60)-(10.00,3.00,3.60)-(10.00,3.00,7.20)-(15.00,3.00,7.20)
- F2_SE_Wall_3 (exterior wall, Default_Ext_Wall): (10.00,0.00,3.60)-(15.00,0.00,3.60)-(15.00,0.00,7.20)-(10.00,0.00,7.20)
- F2_SE_Wall_4 (exterior wall, Default_Ext_Wall): (15.00,0.00,3.60)-(15.00,3.00,3.60)-(15.00,3.00,7.20)-(15.00,0.00,7.20)
- F2_SE_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_SE, adjacent_surface=F1_SE_Ceiling): (10.00,0.00,3.60)-(10.00,3.00,3.60)-(15.00,3.00,3.60)-(15.00,0.00,3.60)
- F2_SE_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_SE, adjacent_surface=F3_SE_Floor_2): (15.00,0.00,7.20)-(15.00,3.00,7.20)-(10.00,3.00,7.20)-(10.00,0.00,7.20)

**F2_Corridor**:
- F2_Corridor_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_SW, adjacent_surface=F2_SW_Wall_2): (5.00,3.00,7.20)-(0.00,3.00,7.20)-(0.00,3.00,3.60)-(5.00,3.00,3.60)
- F2_Corridor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_SC, adjacent_surface=F2_SC_Wall_3): (10.00,3.00,7.20)-(5.00,3.00,7.20)-(5.00,3.00,3.60)-(10.00,3.00,3.60)
- F2_Corridor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_SE, adjacent_surface=F2_SE_Wall_2): (15.00,3.00,7.20)-(10.00,3.00,7.20)-(10.00,3.00,3.60)-(15.00,3.00,3.60)
- F2_Corridor_Wall_4 (interior wall, Default_Int_Wall, adjacent_zone=F2_NW, adjacent_surface=F2_NW_Wall): (3.75,5.00,3.60)-(0.00,5.00,3.60)-(0.00,5.00,7.20)-(3.75,5.00,7.20)
- F2_Corridor_Wall_5 (interior wall, Default_Int_Wall, adjacent_zone=F2_N1, adjacent_surface=F2_N1_Wall): (7.50,5.00,3.60)-(3.75,5.00,3.60)-(3.75,5.00,7.20)-(7.50,5.00,7.20)
- F2_Corridor_Wall_6 (interior wall, Default_Int_Wall, adjacent_zone=F2_N2, adjacent_surface=F2_N2_Wall): (11.25,5.00,3.60)-(7.50,5.00,3.60)-(7.50,5.00,7.20)-(11.25,5.00,7.20)
- F2_Corridor_Wall_7 (interior wall, Default_Int_Wall, adjacent_zone=F2_NE, adjacent_surface=F2_NE_Wall): (15.00,5.00,3.60)-(11.25,5.00,3.60)-(11.25,5.00,7.20)-(15.00,5.00,7.20)
- F2_Corridor_Wall_8 (exterior wall, Default_Ext_Wall): (15.00,3.00,3.60)-(15.00,5.00,3.60)-(15.00,5.00,7.20)-(15.00,3.00,7.20)
- F2_Corridor_Wall_9 (exterior wall, Default_Ext_Wall): (0.00,5.00,3.60)-(0.00,3.00,3.60)-(0.00,3.00,7.20)-(0.00,5.00,7.20)
- F2_Corridor_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_Corridor, adjacent_surface=F1_Corridor_Ceiling): (0.00,3.00,3.60)-(0.00,5.00,3.60)-(15.00,5.00,3.60)-(15.00,3.00,3.60)
- F2_Corridor_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_Corridor, adjacent_surface=F3_Corridor_Floor): (15.00,3.00,7.20)-(15.00,5.00,7.20)-(0.00,5.00,7.20)-(0.00,3.00,7.20)

**F2_NW**:
- F2_NW_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall_4): (3.75,5.00,7.20)-(0.00,5.00,7.20)-(0.00,5.00,3.60)-(3.75,5.00,3.60)
- F2_NW_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_N1, adjacent_surface=F2_N1_Wall_2): (3.75,5.00,3.60)-(3.75,8.00,3.60)-(3.75,8.00,7.20)-(3.75,5.00,7.20)
- F2_NW_Wall_3 (exterior wall, Default_Ext_Wall): (3.75,8.00,3.60)-(0.00,8.00,3.60)-(0.00,8.00,7.20)-(3.75,8.00,7.20)
- F2_NW_Wall_4 (exterior wall, Default_Ext_Wall): (0.00,8.00,3.60)-(0.00,5.00,3.60)-(0.00,5.00,7.20)-(0.00,8.00,7.20)
- F2_NW_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_NW, adjacent_surface=F1_NW_Ceiling): (0.00,5.00,3.60)-(0.00,8.00,3.60)-(3.75,8.00,3.60)-(3.75,5.00,3.60)
- F2_NW_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_N, adjacent_surface=F3_N_Floor): (3.75,5.00,7.20)-(3.75,8.00,7.20)-(0.00,8.00,7.20)-(0.00,5.00,7.20)

**F2_N1**:
- F2_N1_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall_5): (7.50,5.00,7.20)-(3.75,5.00,7.20)-(3.75,5.00,3.60)-(7.50,5.00,3.60)
- F2_N1_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_NW, adjacent_surface=F2_NW_Wall_2): (3.75,5.00,7.20)-(3.75,8.00,7.20)-(3.75,8.00,3.60)-(3.75,5.00,3.60)
- F2_N1_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_N2, adjacent_surface=F2_N2_Wall_2): (7.50,5.00,3.60)-(7.50,8.00,3.60)-(7.50,8.00,7.20)-(7.50,5.00,7.20)
- F2_N1_Wall_4 (exterior wall, Default_Ext_Wall): (7.50,8.00,3.60)-(3.75,8.00,3.60)-(3.75,8.00,7.20)-(7.50,8.00,7.20)
- F2_N1_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_NW, adjacent_surface=F1_NW_Ceiling_2): (3.75,5.00,3.60)-(3.75,8.00,3.60)-(5.00,8.00,3.60)-(5.00,5.00,3.60)
- F2_N1_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_NC, adjacent_surface=F1_NC_Ceiling): (5.00,5.00,3.60)-(5.00,8.00,3.60)-(7.50,8.00,3.60)-(7.50,5.00,3.60)
- F2_N1_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_N, adjacent_surface=F3_N_Floor_2): (7.50,5.00,7.20)-(7.50,8.00,7.20)-(3.75,8.00,7.20)-(3.75,5.00,7.20)

**F2_N2**:
- F2_N2_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall_6): (11.25,5.00,7.20)-(7.50,5.00,7.20)-(7.50,5.00,3.60)-(11.25,5.00,3.60)
- F2_N2_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_N1, adjacent_surface=F2_N1_Wall_3): (7.50,5.00,7.20)-(7.50,8.00,7.20)-(7.50,8.00,3.60)-(7.50,5.00,3.60)
- F2_N2_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F2_NE, adjacent_surface=F2_NE_Wall_2): (11.25,5.00,3.60)-(11.25,8.00,3.60)-(11.25,8.00,7.20)-(11.25,5.00,7.20)
- F2_N2_Wall_4 (exterior wall, Default_Ext_Wall): (11.25,8.00,3.60)-(7.50,8.00,3.60)-(7.50,8.00,7.20)-(11.25,8.00,7.20)
- F2_N2_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_NC, adjacent_surface=F1_NC_Ceiling_2): (7.50,5.00,3.60)-(7.50,8.00,3.60)-(10.00,8.00,3.60)-(10.00,5.00,3.60)
- F2_N2_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F1_NE, adjacent_surface=F1_NE_Ceiling): (10.00,5.00,3.60)-(10.00,8.00,3.60)-(11.25,8.00,3.60)-(11.25,5.00,3.60)
- F2_N2_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_N, adjacent_surface=F3_N_Floor_3): (11.25,5.00,7.20)-(11.25,8.00,7.20)-(7.50,8.00,7.20)-(7.50,5.00,7.20)

**F2_NE**:
- F2_NE_Wall (interior wall, Default_Int_Wall, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Wall_7): (15.00,5.00,7.20)-(11.25,5.00,7.20)-(11.25,5.00,3.60)-(15.00,5.00,3.60)
- F2_NE_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F2_N2, adjacent_surface=F2_N2_Wall_3): (11.25,5.00,7.20)-(11.25,8.00,7.20)-(11.25,8.00,3.60)-(11.25,5.00,3.60)
- F2_NE_Wall_3 (exterior wall, Default_Ext_Wall): (15.00,5.00,3.60)-(15.00,8.00,3.60)-(15.00,8.00,7.20)-(15.00,5.00,7.20)
- F2_NE_Wall_4 (exterior wall, Default_Ext_Wall): (15.00,8.00,3.60)-(11.25,8.00,3.60)-(11.25,8.00,7.20)-(15.00,8.00,7.20)
- F2_NE_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F1_NE, adjacent_surface=F1_NE_Ceiling_2): (11.25,5.00,3.60)-(11.25,8.00,3.60)-(15.00,8.00,3.60)-(15.00,5.00,3.60)
- F2_NE_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=F3_N, adjacent_surface=F3_N_Floor_4): (15.00,5.00,7.20)-(15.00,8.00,7.20)-(11.25,8.00,7.20)-(11.25,5.00,7.20)

**F3_SW**:
- F3_SW_Wall (interior wall, Default_Int_Wall, adjacent_zone=F3_SE, adjacent_surface=F3_SE_Wall): (7.50,0.00,7.20)-(7.50,3.00,7.20)-(7.50,3.00,12.00)-(7.50,0.00,12.00)
- F3_SW_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F3_Corridor, adjacent_surface=F3_Corridor_Wall): (7.50,3.00,7.20)-(0.00,3.00,7.20)-(0.00,3.00,12.00)-(7.50,3.00,12.00)
- F3_SW_Wall_3 (exterior wall, Default_Ext_Wall): (0.00,0.00,7.20)-(7.50,0.00,7.20)-(7.50,0.00,12.00)-(0.00,0.00,12.00)
- F3_SW_Wall_4 (exterior wall, Default_Ext_Wall): (0.00,3.00,7.20)-(0.00,0.00,7.20)-(0.00,0.00,12.00)-(0.00,3.00,12.00)
- F3_SW_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F2_SW, adjacent_surface=F2_SW_Ceiling): (0.00,0.00,7.20)-(0.00,3.00,7.20)-(5.00,3.00,7.20)-(5.00,0.00,7.20)
- F3_SW_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F2_SC, adjacent_surface=F2_SC_Ceiling): (5.00,0.00,7.20)-(5.00,3.00,7.20)-(7.50,3.00,7.20)-(7.50,0.00,7.20)
- F3_SW_Roof (roof roof, Default_Roof): (0.00,0.00,12.00)-(7.50,0.00,12.00)-(7.50,3.00,12.00)-(0.00,3.00,12.00)

**F3_SE**:
- F3_SE_Wall (interior wall, Default_Int_Wall, adjacent_zone=F3_SW, adjacent_surface=F3_SW_Wall): (7.50,0.00,12.00)-(7.50,3.00,12.00)-(7.50,3.00,7.20)-(7.50,0.00,7.20)
- F3_SE_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F3_Corridor, adjacent_surface=F3_Corridor_Wall_2): (15.00,3.00,7.20)-(7.50,3.00,7.20)-(7.50,3.00,12.00)-(15.00,3.00,12.00)
- F3_SE_Wall_3 (exterior wall, Default_Ext_Wall): (7.50,0.00,7.20)-(15.00,0.00,7.20)-(15.00,0.00,12.00)-(7.50,0.00,12.00)
- F3_SE_Wall_4 (exterior wall, Default_Ext_Wall): (15.00,0.00,7.20)-(15.00,3.00,7.20)-(15.00,3.00,12.00)-(15.00,0.00,12.00)
- F3_SE_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F2_SC, adjacent_surface=F2_SC_Ceiling_2): (7.50,0.00,7.20)-(7.50,3.00,7.20)-(10.00,3.00,7.20)-(10.00,0.00,7.20)
- F3_SE_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F2_SE, adjacent_surface=F2_SE_Ceiling): (10.00,0.00,7.20)-(10.00,3.00,7.20)-(15.00,3.00,7.20)-(15.00,0.00,7.20)
- F3_SE_Roof (roof roof, Default_Roof): (7.50,0.00,12.00)-(15.00,0.00,12.00)-(15.00,3.00,12.00)-(7.50,3.00,12.00)

**F3_Corridor**:
- F3_Corridor_Wall (interior wall, Default_Int_Wall, adjacent_zone=F3_SW, adjacent_surface=F3_SW_Wall_2): (7.50,3.00,12.00)-(0.00,3.00,12.00)-(0.00,3.00,7.20)-(7.50,3.00,7.20)
- F3_Corridor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=F3_SE, adjacent_surface=F3_SE_Wall_2): (15.00,3.00,12.00)-(7.50,3.00,12.00)-(7.50,3.00,7.20)-(15.00,3.00,7.20)
- F3_Corridor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=F3_N, adjacent_surface=F3_N_Wall): (15.00,5.00,7.20)-(0.00,5.00,7.20)-(0.00,5.00,12.00)-(15.00,5.00,12.00)
- F3_Corridor_Wall_4 (exterior wall, Default_Ext_Wall): (15.00,3.00,7.20)-(15.00,5.00,7.20)-(15.00,5.00,12.00)-(15.00,3.00,12.00)
- F3_Corridor_Wall_5 (exterior wall, Default_Ext_Wall): (0.00,5.00,7.20)-(0.00,3.00,7.20)-(0.00,3.00,12.00)-(0.00,5.00,12.00)
- F3_Corridor_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F2_Corridor, adjacent_surface=F2_Corridor_Ceiling): (0.00,3.00,7.20)-(0.00,5.00,7.20)-(15.00,5.00,7.20)-(15.00,3.00,7.20)
- F3_Corridor_Roof (roof roof, Default_Roof): (0.00,3.00,12.00)-(15.00,3.00,12.00)-(15.00,5.00,12.00)-(0.00,5.00,12.00)

**F3_N**:
- F3_N_Wall (interior wall, Default_Int_Wall, adjacent_zone=F3_Corridor, adjacent_surface=F3_Corridor_Wall_3): (15.00,5.00,12.00)-(0.00,5.00,12.00)-(0.00,5.00,7.20)-(15.00,5.00,7.20)
- F3_N_Wall_2 (exterior wall, Default_Ext_Wall): (15.00,5.00,7.20)-(15.00,8.00,7.20)-(15.00,8.00,12.00)-(15.00,5.00,12.00)
- F3_N_Wall_3 (exterior wall, Default_Ext_Wall): (15.00,8.00,7.20)-(0.00,8.00,7.20)-(0.00,8.00,12.00)-(15.00,8.00,12.00)
- F3_N_Wall_4 (exterior wall, Default_Ext_Wall): (0.00,8.00,7.20)-(0.00,5.00,7.20)-(0.00,5.00,12.00)-(0.00,8.00,12.00)
- F3_N_Floor (interzone floor, Cons_InterFloor, adjacent_zone=F2_NW, adjacent_surface=F2_NW_Ceiling): (0.00,5.00,7.20)-(0.00,8.00,7.20)-(3.75,8.00,7.20)-(3.75,5.00,7.20)
- F3_N_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=F2_N1, adjacent_surface=F2_N1_Ceiling): (3.75,5.00,7.20)-(3.75,8.00,7.20)-(7.50,8.00,7.20)-(7.50,5.00,7.20)
- F3_N_Floor_3 (interzone floor, Cons_InterFloor, adjacent_zone=F2_N2, adjacent_surface=F2_N2_Ceiling): (7.50,5.00,7.20)-(7.50,8.00,7.20)-(11.25,8.00,7.20)-(11.25,5.00,7.20)
- F3_N_Floor_4 (interzone floor, Cons_InterFloor, adjacent_zone=F2_NE, adjacent_surface=F2_NE_Ceiling): (11.25,5.00,7.20)-(11.25,8.00,7.20)-(15.00,8.00,7.20)-(15.00,5.00,7.20)
- F3_N_Roof (roof roof, Default_Roof): (0.00,5.00,12.00)-(15.00,5.00,12.00)-(15.00,8.00,12.00)-(0.00,8.00,12.00)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- F1_SW_Win: parent=F1_SW_Wall_3, Construction=Default_Window, z=1.00-2.80, vertices: (1.40,0.00,1.00)-(3.80,0.00,1.00)-(3.80,0.00,2.80)-(1.40,0.00,2.80)
- F1_SC_Win: parent=F1_SC_Wall_4, Construction=Default_Window, z=1.00-2.80, vertices: (6.30,0.00,1.00)-(8.70,0.00,1.00)-(8.70,0.00,2.80)-(6.30,0.00,2.80)
- F1_SE_Win: parent=F1_SE_Wall_3, Construction=Default_Window, z=1.00-2.80, vertices: (11.20,0.00,1.00)-(13.60,0.00,1.00)-(13.60,0.00,2.80)-(11.20,0.00,2.80)
- F2_SW_Win: parent=F2_SW_Wall_3, Construction=Default_Window, z=4.40-6.20, vertices: (1.40,0.00,4.40)-(3.80,0.00,4.40)-(3.80,0.00,6.20)-(1.40,0.00,6.20)
- F2_SC_Win: parent=F2_SC_Wall_4, Construction=Default_Window, z=4.40-6.20, vertices: (6.30,0.00,4.40)-(8.70,0.00,4.40)-(8.70,0.00,6.20)-(6.30,0.00,6.20)
- F2_SE_Win: parent=F2_SE_Wall_3, Construction=Default_Window, z=4.40-6.20, vertices: (11.20,0.00,4.40)-(13.60,0.00,4.40)-(13.60,0.00,6.20)-(11.20,0.00,6.20)
- F1_NE_Win: parent=F1_NE_Wall_4, Construction=Default_Window, z=1.00-2.80, vertices: (11.20,8.00,2.80)-(13.60,8.00,2.80)-(13.60,8.00,1.00)-(11.20,8.00,1.00)
- F1_NC_Win: parent=F1_NC_Wall_4, Construction=Default_Window, z=1.00-2.80, vertices: (6.30,8.00,2.80)-(8.70,8.00,2.80)-(8.70,8.00,1.00)-(6.30,8.00,1.00)
- F1_NW_Win: parent=F1_NW_Wall_3, Construction=Default_Window, z=1.00-2.80, vertices: (1.40,8.00,2.80)-(3.80,8.00,2.80)-(3.80,8.00,1.00)-(1.40,8.00,1.00)
- F2_NE_Win: parent=F2_NE_Wall_4, Construction=Default_Window, z=4.40-6.20, vertices: (11.85,8.00,6.20)-(13.60,8.00,6.20)-(13.60,8.00,4.40)-(11.85,8.00,4.40)
- F2_N2_Win: parent=F2_N2_Wall_4, Construction=Default_Window, z=4.40-6.20, vertices: (8.45,8.00,6.20)-(10.20,8.00,6.20)-(10.20,8.00,4.40)-(8.45,8.00,4.40)
- F2_N1_Win: parent=F2_N1_Wall_4, Construction=Default_Window, z=4.40-6.20, vertices: (4.80,8.00,6.20)-(6.55,8.00,6.20)-(6.55,8.00,4.40)-(4.80,8.00,4.40)
- F2_NW_Win: parent=F2_NW_Wall_3, Construction=Default_Window, z=4.40-6.20, vertices: (1.40,8.00,6.20)-(3.15,8.00,6.20)-(3.15,8.00,4.40)-(1.40,8.00,4.40)
- F3_N_Win: parent=F3_N_Wall_3, Construction=Default_Window, z=8.40-11.00, vertices: (1.40,8.00,11.00)-(13.60,8.00,11.00)-(13.60,8.00,8.40)-(1.40,8.00,8.40)
- F3_Corridor_Win: parent=F3_Corridor_Wall_4, Construction=Default_Window, z=8.60-11.00, vertices: (15.00,3.50,8.60)-(15.00,4.50,8.60)-(15.00,4.50,11.00)-(15.00,3.50,11.00)
- F3_Corridor_Win_2: parent=F3_Corridor_Wall_5, Construction=Default_Window, z=8.60-11.00, vertices: (0.00,3.50,11.00)-(0.00,4.50,11.00)-(0.00,4.50,8.60)-(0.00,3.50,8.60)
