# SM25 Lite elevation visual review

Review date: 2026-10-10

Scope: North, South, East and West elevation-reader deliveries from
`manual_dispatch_sm25_lite_v1`, compared directly with the four frozen source
drawings in `case_tests/e2e_tests/sm25-L_anchor/case_data`.

This review did not use ground truth, an older BIM, an older evaluation, an
external service, or a model call. A delivery was reviewed only after both its
`reader_record.json` and lifecycle showed `completed`.

This is a pre-assembly review of the accepted reader artifacts. It does not
claim that facade-to-plan identity matching, height application, assembly or
final BIM delivery has passed.

## Result

No substantive facade omission or height error was found, so no bounded
elevation rework is recommended.

| Facade | Visible inventory and adopted heights | Review |
|---|---|---|
| North | F1 and F2 each contain four windows. Widths are 8.0, 0.6, 2.4 and 2.4 m. F1 sills are 1.0 m with heads 3.2/2.6 m; F2 sills are 4.6 m with heads 6.8/6.2 m. | Matches the drawing, including the taller 8.0 m-wide window in each storey. |
| South | F1 contains two 4.0 m windows at Z 1.0-2.8 m. F2 contains five 1.8 m windows at Z 4.6-6.2 m. | Matches the visible frames and dimension chains. |
| East | F1 contains seven 0.9 m windows plus one double door; F2 contains five 0.9 m windows. Window Z ranges are 1.0-2.6 m and 4.6-6.2 m. The door adopts width 1.6 m and Z 0.2-2.3 m. | Matches the visible inventory and frame locations. The door values are pixel-derived; its frame bottom is visibly about 0.2 m above the facade baseline, consistent with the analogous West door block. This uncertainty is retained in `unresolved`. |
| West | F1 contains two 1.8 m windows at Z 1.0-2.6 m and two 0.8 m doors at Z 0.2-2.3 m. F2 contains a 4.32 m source-width window at Z 4.6-6.8 m and a 1.2 m window at Z 4.6-6.2 m. | Matches the drawing. The 0.2 m door base is explicitly supported by the 200 + 2100 + 1300 mm vertical chain. |

All four deliveries use absolute levels 0.0, 3.6 and 7.2 m, matching the two
3.6 m storeys and 7.2 m total height.

## Lite-grid audit

All artifacts report a 0.1 m grid and retain an audit reading for every level,
opening width, sill and head:

- North: 28 readings, no changed values.
- South: 25 readings, no changed values.
- East: 43 readings. The pixel-derived door changes from 1.6136 to 1.6 m
  width, 0.1766 to 0.2 m sill, and 2.2958 to 2.3 m head.
- West: 22 readings. The large F2 window retains original width 4.32 m and
  adopts 4.3 m.

The changed entries preserve their pre-grid values and adopted values in the
regularization report. Opening boxes visually cover the corresponding frames;
no opening was bound to an unrelated frame or omitted from the reported count.

## Accepted artifact references

Paths below are relative to `manual_dispatch_sm25_lite_v1`. The SHA is the
accepted artifact reference in each `reader_record.json`.

| Facade | Accepted artifact path | SHA-256 |
|---|---|---|
| East | `tasks/269af70aac2f4eab46852b7e0fc72d074e3cebc865af9331311eb93b1c69518e/reader_artifact.json` | `aa4166537e4b684aa553a19b37e37a8ba88ddbb3594fae39f84035ba64083766` |
| West | `tasks/82fb5cb1c331a7c59fc3653ed66e7818b03fc62c85fc030c0b73c0d807910670/reader_artifact.json` | `77c68e855ae5259ad498bfe8daaa88c6459da8fbd717568b8044384792b0b099` |
| North | `tasks/a7fa4090718c93ffd4480743b544e5aec7f96d6526c7de6118616d0184f5e155/reader_artifact.json` | `86eae30f7beba2e22620d56ff7b11e2e170563e98cd7338202a553ea1d737815` |
| South | `tasks/c4d7a4df1c2d865492027fb6781bcac946c39f3b39d19165b8fa967eafee1dc5/reader_artifact.json` | `01ecffe428614ef22f4d717222e36df6352931479b00cf7e3bcdca5e706f8519` |

## Current-artifact overlay anchors

These values come directly from the accepted artifacts. No older anchor set was
constructed or reused. Horizontal overlay calibration is at `x_calibration`;
absolute vertical calibration is at `z_calibration`; independently located Z
anchor rows are at `elevations[*]`, with their source regions in each row's
`bbox`.

| Facade | `x_calibration` | `z_calibration` | Available absolute Z rows |
|---|---|---|---|
| East | px 312→1787 maps world y 0→20 m | px 272→802 maps Z 7.2→0 m | `ground`/`F1_floor` Z0 bbox `[1795,793,1885,812]`; `F2_floor` Z3.6 bbox `[1795,528,1885,546]`; `roof` Z7.2 bbox `[1795,263,1885,281]` |
| West | px 521→1998 maps world y 20→0 m | px 330→862 maps Z 7.2→0 m | `ground` Z0 bbox `[110,845,520,875]`; `floor_F1` Z0 bbox `[521,850,1000,870]`; `floor_F2` Z3.6 bbox `[540,588,1990,604]`; `roofline` Z7.2 bbox `[540,324,1990,340]` |
| North | px 441→2285 maps world x 25→0 m | px 308→839 maps Z 7.2→0 m | `ground`/`F1_floor` Z0 bbox `[250,820,440,860]`; `F2_floor` Z3.6 bbox `[250,555,440,595]`; `eave_top` Z7.2 bbox `[250,292,440,325]` |
| South | px 376.5→2221.5 maps world x 0→25 m | px 296→827.5 maps Z 7.2→0 m | `ground`/`F1_floor` Z0 bbox `[400,812,900,842]`; `F2_floor` Z3.6 bbox `[400,545,900,578]`; `eave` Z7.2 bbox `[400,283,900,310]` |
