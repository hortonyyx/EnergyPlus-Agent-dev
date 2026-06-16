# zone_specs

Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.

Floor 1 (z 0.00 to 3.00):
- R_1F_TL: x[-0.10,4.30], y[4.75,7.65], z_floor=0.00, ceiling_height=3.00, role: office.
- R_1F_TM: x[4.30,9.70], y[4.75,7.65], z_floor=0.00, ceiling_height=3.00, role: office.
- R_1F_TR: x[9.70,14.65], y[4.75,7.65], z_floor=0.00, ceiling_height=3.00, role: office.
- R_1F_BL: x[-0.10,4.75], y[-0.10,2.75], z_floor=0.00, ceiling_height=3.00, role: office.
- R_1F_BM: x[4.75,9.70], y[-0.10,2.75], z_floor=0.00, ceiling_height=3.00, role: office.
- R_1F_BR: x[9.70,14.65], y[-0.10,2.75], z_floor=0.00, ceiling_height=3.00, role: office.
- R_1F_Cor: x[-0.10,14.65], y[2.75,4.75], z_floor=0.00, ceiling_height=3.00, role: corridor.

Floor 2 (z 3.00 to 6.60):
- R_2F_TL: x[-0.10,7.20], y[4.75,7.65], z_floor=3.00, ceiling_height=3.60, role: conference.
- R_2F_TR: x[7.20,14.65], y[4.75,7.65], z_floor=3.00, ceiling_height=3.60, role: conference.
- R_2F_B1: x[-0.10,3.50], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- R_2F_B2: x[3.50,7.20], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- R_2F_B3: x[7.20,11.00], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- R_2F_B4: x[11.00,14.65], y[-0.10,2.75], z_floor=3.00, ceiling_height=3.60, role: office.
- R_2F_Cor: x[-0.10,14.65], y[2.75,4.75], z_floor=3.00, ceiling_height=3.60, role: corridor.

# surface_specs

Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the named adjacent surface is its reciprocal partner.

**R_1F_TL**:
- R_1F_TL_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TM, adjacent_surface=R_1F_TM_Wall): (4.30,4.75,0.00)-(4.30,7.65,0.00)-(4.30,7.65,3.00)-(4.30,4.75,3.00)
- R_1F_TL_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Wall): (-0.10,4.75,0.00)-(4.30,4.75,0.00)-(4.30,4.75,3.00)-(-0.10,4.75,3.00)
- R_1F_TL_Wall_3 (exterior wall, Default_Ext_Wall): (4.30,7.65,0.00)-(-0.10,7.65,0.00)-(-0.10,7.65,3.00)-(4.30,7.65,3.00)
- R_1F_TL_Wall_4 (exterior wall, Default_Ext_Wall): (-0.10,7.65,0.00)-(-0.10,4.75,0.00)-(-0.10,4.75,3.00)-(-0.10,7.65,3.00)
- R_1F_TL_Floor (ground floor, Default_GroundFloor): (-0.10,7.65,0.00)-(4.30,7.65,0.00)-(4.30,4.75,0.00)-(-0.10,4.75,0.00)
- R_1F_TL_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_TL, adjacent_surface=R_2F_TL_Floor): (4.30,4.75,3.00)-(4.30,7.65,3.00)-(-0.10,7.65,3.00)-(-0.10,4.75,3.00)

**R_1F_TM**:
- R_1F_TM_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TL, adjacent_surface=R_1F_TL_Wall): (4.30,4.75,3.00)-(4.30,7.65,3.00)-(4.30,7.65,0.00)-(4.30,4.75,0.00)
- R_1F_TM_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TR, adjacent_surface=R_1F_TR_Wall): (9.70,4.75,0.00)-(9.70,7.65,0.00)-(9.70,7.65,3.00)-(9.70,4.75,3.00)
- R_1F_TM_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Wall_2): (4.30,4.75,0.00)-(9.70,4.75,0.00)-(9.70,4.75,3.00)-(4.30,4.75,3.00)
- R_1F_TM_Wall_4 (exterior wall, Default_Ext_Wall): (9.70,7.65,0.00)-(4.30,7.65,0.00)-(4.30,7.65,3.00)-(9.70,7.65,3.00)
- R_1F_TM_Floor (ground floor, Default_GroundFloor): (4.30,7.65,0.00)-(9.70,7.65,0.00)-(9.70,4.75,0.00)-(4.30,4.75,0.00)
- R_1F_TM_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_TL, adjacent_surface=R_2F_TL_Floor_2): (7.20,4.75,3.00)-(7.20,7.65,3.00)-(4.30,7.65,3.00)-(4.30,4.75,3.00)
- R_1F_TM_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_TR, adjacent_surface=R_2F_TR_Floor): (9.70,4.75,3.00)-(9.70,7.65,3.00)-(7.20,7.65,3.00)-(7.20,4.75,3.00)

**R_1F_TR**:
- R_1F_TR_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TM, adjacent_surface=R_1F_TM_Wall_2): (9.70,4.75,3.00)-(9.70,7.65,3.00)-(9.70,7.65,0.00)-(9.70,4.75,0.00)
- R_1F_TR_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Wall_3): (9.70,4.75,0.00)-(14.65,4.75,0.00)-(14.65,4.75,3.00)-(9.70,4.75,3.00)
- R_1F_TR_Wall_3 (exterior wall, Default_Ext_Wall): (14.65,4.75,0.00)-(14.65,7.65,0.00)-(14.65,7.65,3.00)-(14.65,4.75,3.00)
- R_1F_TR_Wall_4 (exterior wall, Default_Ext_Wall): (14.65,7.65,0.00)-(9.70,7.65,0.00)-(9.70,7.65,3.00)-(14.65,7.65,3.00)
- R_1F_TR_Floor (ground floor, Default_GroundFloor): (9.70,7.65,0.00)-(14.65,7.65,0.00)-(14.65,4.75,0.00)-(9.70,4.75,0.00)
- R_1F_TR_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_TR, adjacent_surface=R_2F_TR_Floor_2): (14.65,4.75,3.00)-(14.65,7.65,3.00)-(9.70,7.65,3.00)-(9.70,4.75,3.00)

**R_1F_BL**:
- R_1F_BL_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BM, adjacent_surface=R_1F_BM_Wall): (4.75,-0.10,0.00)-(4.75,2.75,0.00)-(4.75,2.75,3.00)-(4.75,-0.10,3.00)
- R_1F_BL_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Wall_4): (4.75,2.75,0.00)-(-0.10,2.75,0.00)-(-0.10,2.75,3.00)-(4.75,2.75,3.00)
- R_1F_BL_Wall_3 (exterior wall, Default_Ext_Wall): (-0.10,-0.10,0.00)-(4.75,-0.10,0.00)-(4.75,-0.10,3.00)-(-0.10,-0.10,3.00)
- R_1F_BL_Wall_4 (exterior wall, Default_Ext_Wall): (-0.10,2.75,0.00)-(-0.10,-0.10,0.00)-(-0.10,-0.10,3.00)-(-0.10,2.75,3.00)
- R_1F_BL_Floor (ground floor, Default_GroundFloor): (-0.10,2.75,0.00)-(4.75,2.75,0.00)-(4.75,-0.10,0.00)-(-0.10,-0.10,0.00)
- R_1F_BL_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_B1, adjacent_surface=R_2F_B1_Floor): (3.50,-0.10,3.00)-(3.50,2.75,3.00)-(-0.10,2.75,3.00)-(-0.10,-0.10,3.00)
- R_1F_BL_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_B2, adjacent_surface=R_2F_B2_Floor): (4.75,-0.10,3.00)-(4.75,2.75,3.00)-(3.50,2.75,3.00)-(3.50,-0.10,3.00)

**R_1F_BM**:
- R_1F_BM_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BL, adjacent_surface=R_1F_BL_Wall): (4.75,-0.10,3.00)-(4.75,2.75,3.00)-(4.75,2.75,0.00)-(4.75,-0.10,0.00)
- R_1F_BM_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BR, adjacent_surface=R_1F_BR_Wall): (9.70,-0.10,0.00)-(9.70,2.75,0.00)-(9.70,2.75,3.00)-(9.70,-0.10,3.00)
- R_1F_BM_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Wall_5): (9.70,2.75,0.00)-(4.75,2.75,0.00)-(4.75,2.75,3.00)-(9.70,2.75,3.00)
- R_1F_BM_Wall_4 (exterior wall, Default_Ext_Wall): (4.75,-0.10,0.00)-(9.70,-0.10,0.00)-(9.70,-0.10,3.00)-(4.75,-0.10,3.00)
- R_1F_BM_Floor (ground floor, Default_GroundFloor): (4.75,2.75,0.00)-(9.70,2.75,0.00)-(9.70,-0.10,0.00)-(4.75,-0.10,0.00)
- R_1F_BM_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_B2, adjacent_surface=R_2F_B2_Floor_2): (7.20,-0.10,3.00)-(7.20,2.75,3.00)-(4.75,2.75,3.00)-(4.75,-0.10,3.00)
- R_1F_BM_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_B3, adjacent_surface=R_2F_B3_Floor): (9.70,-0.10,3.00)-(9.70,2.75,3.00)-(7.20,2.75,3.00)-(7.20,-0.10,3.00)

**R_1F_BR**:
- R_1F_BR_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BM, adjacent_surface=R_1F_BM_Wall_2): (9.70,-0.10,3.00)-(9.70,2.75,3.00)-(9.70,2.75,0.00)-(9.70,-0.10,0.00)
- R_1F_BR_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Wall_6): (14.65,2.75,0.00)-(9.70,2.75,0.00)-(9.70,2.75,3.00)-(14.65,2.75,3.00)
- R_1F_BR_Wall_3 (exterior wall, Default_Ext_Wall): (9.70,-0.10,0.00)-(14.65,-0.10,0.00)-(14.65,-0.10,3.00)-(9.70,-0.10,3.00)
- R_1F_BR_Wall_4 (exterior wall, Default_Ext_Wall): (14.65,-0.10,0.00)-(14.65,2.75,0.00)-(14.65,2.75,3.00)-(14.65,-0.10,3.00)
- R_1F_BR_Floor (ground floor, Default_GroundFloor): (9.70,2.75,0.00)-(14.65,2.75,0.00)-(14.65,-0.10,0.00)-(9.70,-0.10,0.00)
- R_1F_BR_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_B3, adjacent_surface=R_2F_B3_Floor_2): (11.00,-0.10,3.00)-(11.00,2.75,3.00)-(9.70,2.75,3.00)-(9.70,-0.10,3.00)
- R_1F_BR_Ceiling_2 (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_B4, adjacent_surface=R_2F_B4_Floor): (14.65,-0.10,3.00)-(14.65,2.75,3.00)-(11.00,2.75,3.00)-(11.00,-0.10,3.00)

**R_1F_Cor**:
- R_1F_Cor_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TL, adjacent_surface=R_1F_TL_Wall_2): (-0.10,4.75,3.00)-(4.30,4.75,3.00)-(4.30,4.75,0.00)-(-0.10,4.75,0.00)
- R_1F_Cor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TM, adjacent_surface=R_1F_TM_Wall_3): (4.30,4.75,3.00)-(9.70,4.75,3.00)-(9.70,4.75,0.00)-(4.30,4.75,0.00)
- R_1F_Cor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_TR, adjacent_surface=R_1F_TR_Wall_2): (9.70,4.75,3.00)-(14.65,4.75,3.00)-(14.65,4.75,0.00)-(9.70,4.75,0.00)
- R_1F_Cor_Wall_4 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BL, adjacent_surface=R_1F_BL_Wall_2): (4.75,2.75,3.00)-(-0.10,2.75,3.00)-(-0.10,2.75,0.00)-(4.75,2.75,0.00)
- R_1F_Cor_Wall_5 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BM, adjacent_surface=R_1F_BM_Wall_3): (9.70,2.75,3.00)-(4.75,2.75,3.00)-(4.75,2.75,0.00)-(9.70,2.75,0.00)
- R_1F_Cor_Wall_6 (interior wall, Default_Int_Wall, adjacent_zone=R_1F_BR, adjacent_surface=R_1F_BR_Wall_2): (14.65,2.75,3.00)-(9.70,2.75,3.00)-(9.70,2.75,0.00)-(14.65,2.75,0.00)
- R_1F_Cor_Wall_7 (exterior wall, Default_Ext_Wall): (14.65,2.75,0.00)-(14.65,4.75,0.00)-(14.65,4.75,3.00)-(14.65,2.75,3.00)
- R_1F_Cor_Wall_8 (exterior wall, Default_Ext_Wall): (-0.10,4.75,0.00)-(-0.10,2.75,0.00)-(-0.10,2.75,3.00)-(-0.10,4.75,3.00)
- R_1F_Cor_Floor (ground floor, Default_GroundFloor): (-0.10,4.75,0.00)-(14.65,4.75,0.00)-(14.65,2.75,0.00)-(-0.10,2.75,0.00)
- R_1F_Cor_Ceiling (interzone ceiling, Cons_InterFloor, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Floor): (14.65,2.75,3.00)-(14.65,4.75,3.00)-(-0.10,4.75,3.00)-(-0.10,2.75,3.00)

**R_2F_TL**:
- R_2F_TL_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_TR, adjacent_surface=R_2F_TR_Wall): (7.20,4.75,3.00)-(7.20,7.65,3.00)-(7.20,7.65,6.60)-(7.20,4.75,6.60)
- R_2F_TL_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Wall): (-0.10,4.75,3.00)-(7.20,4.75,3.00)-(7.20,4.75,6.60)-(-0.10,4.75,6.60)
- R_2F_TL_Wall_3 (exterior wall, Default_Ext_Wall): (7.20,7.65,3.00)-(-0.10,7.65,3.00)-(-0.10,7.65,6.60)-(7.20,7.65,6.60)
- R_2F_TL_Wall_4 (exterior wall, Default_Ext_Wall): (-0.10,7.65,3.00)-(-0.10,4.75,3.00)-(-0.10,4.75,6.60)-(-0.10,7.65,6.60)
- R_2F_TL_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_TL, adjacent_surface=R_1F_TL_Ceiling): (-0.10,4.75,3.00)-(-0.10,7.65,3.00)-(4.30,7.65,3.00)-(4.30,4.75,3.00)
- R_2F_TL_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_TM, adjacent_surface=R_1F_TM_Ceiling): (4.30,4.75,3.00)-(4.30,7.65,3.00)-(7.20,7.65,3.00)-(7.20,4.75,3.00)
- R_2F_TL_Roof (roof roof, Default_Roof): (-0.10,4.75,6.60)-(7.20,4.75,6.60)-(7.20,7.65,6.60)-(-0.10,7.65,6.60)

**R_2F_TR**:
- R_2F_TR_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_TL, adjacent_surface=R_2F_TL_Wall): (7.20,4.75,6.60)-(7.20,7.65,6.60)-(7.20,7.65,3.00)-(7.20,4.75,3.00)
- R_2F_TR_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Wall_2): (7.20,4.75,3.00)-(14.65,4.75,3.00)-(14.65,4.75,6.60)-(7.20,4.75,6.60)
- R_2F_TR_Wall_3 (exterior wall, Default_Ext_Wall): (14.65,4.75,3.00)-(14.65,7.65,3.00)-(14.65,7.65,6.60)-(14.65,4.75,6.60)
- R_2F_TR_Wall_4 (exterior wall, Default_Ext_Wall): (14.65,7.65,3.00)-(7.20,7.65,3.00)-(7.20,7.65,6.60)-(14.65,7.65,6.60)
- R_2F_TR_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_TM, adjacent_surface=R_1F_TM_Ceiling_2): (7.20,4.75,3.00)-(7.20,7.65,3.00)-(9.70,7.65,3.00)-(9.70,4.75,3.00)
- R_2F_TR_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_TR, adjacent_surface=R_1F_TR_Ceiling): (9.70,4.75,3.00)-(9.70,7.65,3.00)-(14.65,7.65,3.00)-(14.65,4.75,3.00)
- R_2F_TR_Roof (roof roof, Default_Roof): (7.20,4.75,6.60)-(14.65,4.75,6.60)-(14.65,7.65,6.60)-(7.20,7.65,6.60)

**R_2F_B1**:
- R_2F_B1_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B2, adjacent_surface=R_2F_B2_Wall): (3.50,-0.10,3.00)-(3.50,2.75,3.00)-(3.50,2.75,6.60)-(3.50,-0.10,6.60)
- R_2F_B1_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Wall_3): (3.50,2.75,3.00)-(-0.10,2.75,3.00)-(-0.10,2.75,6.60)-(3.50,2.75,6.60)
- R_2F_B1_Wall_3 (exterior wall, Default_Ext_Wall): (-0.10,-0.10,3.00)-(3.50,-0.10,3.00)-(3.50,-0.10,6.60)-(-0.10,-0.10,6.60)
- R_2F_B1_Wall_4 (exterior wall, Default_Ext_Wall): (-0.10,2.75,3.00)-(-0.10,-0.10,3.00)-(-0.10,-0.10,6.60)-(-0.10,2.75,6.60)
- R_2F_B1_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_BL, adjacent_surface=R_1F_BL_Ceiling): (-0.10,-0.10,3.00)-(-0.10,2.75,3.00)-(3.50,2.75,3.00)-(3.50,-0.10,3.00)
- R_2F_B1_Roof (roof roof, Default_Roof): (-0.10,-0.10,6.60)-(3.50,-0.10,6.60)-(3.50,2.75,6.60)-(-0.10,2.75,6.60)

**R_2F_B2**:
- R_2F_B2_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B1, adjacent_surface=R_2F_B1_Wall): (3.50,-0.10,6.60)-(3.50,2.75,6.60)-(3.50,2.75,3.00)-(3.50,-0.10,3.00)
- R_2F_B2_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B3, adjacent_surface=R_2F_B3_Wall): (7.20,-0.10,3.00)-(7.20,2.75,3.00)-(7.20,2.75,6.60)-(7.20,-0.10,6.60)
- R_2F_B2_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Wall_4): (7.20,2.75,3.00)-(3.50,2.75,3.00)-(3.50,2.75,6.60)-(7.20,2.75,6.60)
- R_2F_B2_Wall_4 (exterior wall, Default_Ext_Wall): (3.50,-0.10,3.00)-(7.20,-0.10,3.00)-(7.20,-0.10,6.60)-(3.50,-0.10,6.60)
- R_2F_B2_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_BL, adjacent_surface=R_1F_BL_Ceiling_2): (3.50,-0.10,3.00)-(3.50,2.75,3.00)-(4.75,2.75,3.00)-(4.75,-0.10,3.00)
- R_2F_B2_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_BM, adjacent_surface=R_1F_BM_Ceiling): (4.75,-0.10,3.00)-(4.75,2.75,3.00)-(7.20,2.75,3.00)-(7.20,-0.10,3.00)
- R_2F_B2_Roof (roof roof, Default_Roof): (3.50,-0.10,6.60)-(7.20,-0.10,6.60)-(7.20,2.75,6.60)-(3.50,2.75,6.60)

**R_2F_B3**:
- R_2F_B3_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B2, adjacent_surface=R_2F_B2_Wall_2): (7.20,-0.10,6.60)-(7.20,2.75,6.60)-(7.20,2.75,3.00)-(7.20,-0.10,3.00)
- R_2F_B3_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B4, adjacent_surface=R_2F_B4_Wall): (11.00,-0.10,3.00)-(11.00,2.75,3.00)-(11.00,2.75,6.60)-(11.00,-0.10,6.60)
- R_2F_B3_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Wall_5): (11.00,2.75,3.00)-(7.20,2.75,3.00)-(7.20,2.75,6.60)-(11.00,2.75,6.60)
- R_2F_B3_Wall_4 (exterior wall, Default_Ext_Wall): (7.20,-0.10,3.00)-(11.00,-0.10,3.00)-(11.00,-0.10,6.60)-(7.20,-0.10,6.60)
- R_2F_B3_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_BM, adjacent_surface=R_1F_BM_Ceiling_2): (7.20,-0.10,3.00)-(7.20,2.75,3.00)-(9.70,2.75,3.00)-(9.70,-0.10,3.00)
- R_2F_B3_Floor_2 (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_BR, adjacent_surface=R_1F_BR_Ceiling): (9.70,-0.10,3.00)-(9.70,2.75,3.00)-(11.00,2.75,3.00)-(11.00,-0.10,3.00)
- R_2F_B3_Roof (roof roof, Default_Roof): (7.20,-0.10,6.60)-(11.00,-0.10,6.60)-(11.00,2.75,6.60)-(7.20,2.75,6.60)

**R_2F_B4**:
- R_2F_B4_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B3, adjacent_surface=R_2F_B3_Wall_2): (11.00,-0.10,6.60)-(11.00,2.75,6.60)-(11.00,2.75,3.00)-(11.00,-0.10,3.00)
- R_2F_B4_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_Cor, adjacent_surface=R_2F_Cor_Wall_6): (14.65,2.75,3.00)-(11.00,2.75,3.00)-(11.00,2.75,6.60)-(14.65,2.75,6.60)
- R_2F_B4_Wall_3 (exterior wall, Default_Ext_Wall): (11.00,-0.10,3.00)-(14.65,-0.10,3.00)-(14.65,-0.10,6.60)-(11.00,-0.10,6.60)
- R_2F_B4_Wall_4 (exterior wall, Default_Ext_Wall): (14.65,-0.10,3.00)-(14.65,2.75,3.00)-(14.65,2.75,6.60)-(14.65,-0.10,6.60)
- R_2F_B4_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_BR, adjacent_surface=R_1F_BR_Ceiling_2): (11.00,-0.10,3.00)-(11.00,2.75,3.00)-(14.65,2.75,3.00)-(14.65,-0.10,3.00)
- R_2F_B4_Roof (roof roof, Default_Roof): (11.00,-0.10,6.60)-(14.65,-0.10,6.60)-(14.65,2.75,6.60)-(11.00,2.75,6.60)

**R_2F_Cor**:
- R_2F_Cor_Wall (interior wall, Default_Int_Wall, adjacent_zone=R_2F_TL, adjacent_surface=R_2F_TL_Wall_2): (-0.10,4.75,6.60)-(7.20,4.75,6.60)-(7.20,4.75,3.00)-(-0.10,4.75,3.00)
- R_2F_Cor_Wall_2 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_TR, adjacent_surface=R_2F_TR_Wall_2): (7.20,4.75,6.60)-(14.65,4.75,6.60)-(14.65,4.75,3.00)-(7.20,4.75,3.00)
- R_2F_Cor_Wall_3 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B1, adjacent_surface=R_2F_B1_Wall_2): (3.50,2.75,6.60)-(-0.10,2.75,6.60)-(-0.10,2.75,3.00)-(3.50,2.75,3.00)
- R_2F_Cor_Wall_4 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B2, adjacent_surface=R_2F_B2_Wall_3): (7.20,2.75,6.60)-(3.50,2.75,6.60)-(3.50,2.75,3.00)-(7.20,2.75,3.00)
- R_2F_Cor_Wall_5 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B3, adjacent_surface=R_2F_B3_Wall_3): (11.00,2.75,6.60)-(7.20,2.75,6.60)-(7.20,2.75,3.00)-(11.00,2.75,3.00)
- R_2F_Cor_Wall_6 (interior wall, Default_Int_Wall, adjacent_zone=R_2F_B4, adjacent_surface=R_2F_B4_Wall_2): (14.65,2.75,6.60)-(11.00,2.75,6.60)-(11.00,2.75,3.00)-(14.65,2.75,3.00)
- R_2F_Cor_Wall_7 (exterior wall, Default_Ext_Wall): (14.65,2.75,3.00)-(14.65,4.75,3.00)-(14.65,4.75,6.60)-(14.65,2.75,6.60)
- R_2F_Cor_Wall_8 (exterior wall, Default_Ext_Wall): (-0.10,4.75,3.00)-(-0.10,2.75,3.00)-(-0.10,2.75,6.60)-(-0.10,4.75,6.60)
- R_2F_Cor_Floor (interzone floor, Cons_InterFloor, adjacent_zone=R_1F_Cor, adjacent_surface=R_1F_Cor_Ceiling): (-0.10,2.75,3.00)-(-0.10,4.75,3.00)-(14.65,4.75,3.00)-(14.65,2.75,3.00)
- R_2F_Cor_Roof (roof roof, Default_Roof): (-0.10,2.75,6.60)-(14.65,2.75,6.60)-(14.65,4.75,6.60)-(-0.10,4.75,6.60)

# fenestration_specs

Windows are FenestrationSurface:Detailed, vertices CCW from outside, Construction=Default_Window. parent is the exterior wall surface name (transcribe verbatim). Create EXACTLY the windows listed below — no more, no fewer.
- R_1F_TL_Win: parent=R_1F_TL_Wall_3, Construction=Default_Window, z=1.00-2.60, vertices: (1.00,7.65,2.60)-(3.40,7.65,2.60)-(3.40,7.65,1.00)-(1.00,7.65,1.00)
- R_1F_TM_Win: parent=R_1F_TM_Wall_4, Construction=Default_Window, z=1.00-2.60, vertices: (5.84,7.65,2.60)-(8.24,7.65,2.60)-(8.24,7.65,1.00)-(5.84,7.65,1.00)
- R_1F_TR_Win: parent=R_1F_TR_Wall_4, Construction=Default_Window, z=1.00-2.60, vertices: (10.88,7.65,2.60)-(13.28,7.65,2.60)-(13.28,7.65,1.00)-(10.88,7.65,1.00)
- R_1F_BL_Win: parent=R_1F_BL_Wall_3, Construction=Default_Window, z=1.50-2.10, vertices: (3.20,-0.10,1.50)-(4.40,-0.10,1.50)-(4.40,-0.10,2.10)-(3.20,-0.10,2.10)
- R_1F_BM_Win: parent=R_1F_BM_Wall_4, Construction=Default_Window, z=1.00-2.60, vertices: (6.06,-0.10,1.00)-(8.46,-0.10,1.00)-(8.46,-0.10,2.60)-(6.06,-0.10,2.60)
- R_1F_BR_Win: parent=R_1F_BR_Wall_3, Construction=Default_Window, z=1.00-2.60, vertices: (11.12,-0.10,1.00)-(13.52,-0.10,1.00)-(13.52,-0.10,2.60)-(11.12,-0.10,2.60)
- R_1F_Cor_Win: parent=R_1F_Cor_Wall_7, Construction=Default_Window, z=1.00-2.80, vertices: (14.65,3.16,1.00)-(14.65,4.36,1.00)-(14.65,4.36,2.80)-(14.65,3.16,2.80)
- R_2F_TL_Win: parent=R_2F_TL_Wall_3, Construction=Default_Window, z=4.00-5.80, vertices: (1.71,7.65,5.80)-(5.31,7.65,5.80)-(5.31,7.65,4.00)-(1.71,7.65,4.00)
- R_2F_TR_Win: parent=R_2F_TR_Wall_4, Construction=Default_Window, z=4.00-5.80, vertices: (9.21,7.65,5.80)-(12.81,7.65,5.80)-(12.81,7.65,4.00)-(9.21,7.65,4.00)
- R_2F_B1_Win: parent=R_2F_B1_Wall_3, Construction=Default_Window, z=4.00-5.80, vertices: (1.95,-0.10,4.00)-(3.15,-0.10,4.00)-(3.15,-0.10,5.80)-(1.95,-0.10,5.80)
- R_2F_B2_Win: parent=R_2F_B2_Wall_4, Construction=Default_Window, z=4.00-5.80, vertices: (5.07,-0.10,4.00)-(6.27,-0.10,4.00)-(6.27,-0.10,5.80)-(5.07,-0.10,5.80)
- R_2F_B3_Win: parent=R_2F_B3_Wall_4, Construction=Default_Window, z=4.00-5.80, vertices: (8.25,-0.10,4.00)-(9.45,-0.10,4.00)-(9.45,-0.10,5.80)-(8.25,-0.10,5.80)
- R_2F_B4_Win: parent=R_2F_B4_Wall_3, Construction=Default_Window, z=4.00-5.80, vertices: (11.37,-0.10,4.00)-(12.57,-0.10,4.00)-(12.57,-0.10,5.80)-(11.37,-0.10,5.80)
- R_2F_Cor_Win: parent=R_2F_Cor_Wall_7, Construction=Default_Window, z=4.00-5.80, vertices: (14.65,3.16,4.00)-(14.65,4.36,4.00)-(14.65,4.36,5.80)-(14.65,3.16,5.80)
- R_2F_Cor_Win_2: parent=R_2F_Cor_Wall_8, Construction=Default_Window, z=4.00-5.80, vertices: (-0.10,3.16,5.80)-(-0.10,4.36,5.80)-(-0.10,4.36,4.00)-(-0.10,3.16,4.00)
