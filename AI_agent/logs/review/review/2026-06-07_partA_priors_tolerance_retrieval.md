# partA Priors And Tolerance Retrieval Package

Date: 2026-06-07
Researcher: Codex
Scope: Retrieval package for `AI_agent/logs/review/request/2026-06-07_partA_priors_tolerance_retrieval_brief.md`. This is not a review and does not change code, skills, or contracts.

## Executive Summary

The reliable national-code anchors are:

- **Office door opening**: office-room door opening width >= 1.00 m, height >= 2.10 m (`JGJ/T 67-2019` 4.1.7).
- **Office corridor width**: 1.30/1.50 m for <=40 m single-/double-loaded corridors; 1.50/1.80 m for >40 m (`JGJ/T 67-2019` 4.1.9 table).
- **Office net height**: 2.50-2.90 m depending on office type/HVAC/ceiling; corridor >=2.20 m; storage >=2.00 m (`JGJ/T 67-2019` 4.1.11).
- **Office area**: ordinary office >=6 m2/person; single office room area >=10 m2 (`JGJ/T 67-2019` 4.2.3).
- **Public-window safety sill**: public-building exterior window sill height >=0.80 m unless guard provided (`GB 50352-2019` 6.11.6).
- **Module system**: 1M = 100 mm; horizontal dimensions use 2nM/3nM; vertical dimensions use nM; submodules include M/10, M/5, M/2 (`GB/T 50002-2013` 3.1-3.2; echoed by `GB 50352-2019` 3.5).
- **WWR**: for class-A public buildings, single-facade WWR should generally be <=0.60 in severe cold regions and <=0.70 elsewhere (`GB 50189-2015` 3.2.2).
- **ASHRAE perimeter depth**: 15 ft / 4.6 m default, user range 8-20 ft / 2.4-6.1 m (`ASHRAE 90.1-2019 Addendum ag`).

Important caveat: **common window width/height, office column grid, WC cubicle size, lift shaft size, MEP room area, lobby size, tea room size are mostly not national-code hard values**. Use them as A4 `warning/score` priors, not auto-correction rules.

## A4 Prior Table

Fields: `value_typical`, `range[min,max]`, `unit`, `building_type`, `space_type`, `source`, `authority`, `note`.

### Door And Window Openings

| item | value_typical | range[min,max] | unit | building_type | space_type | source | authority | note |
|---|---:|---:|---|---|---|---|---|---|
| office door opening width | 1.00 | [1.00, 1.20] | m | office | office room | `JGJ/T 67-2019` 4.1.7 | national_code | Hard lower bound for office-room door opening. Do not infer exact door leaf width from this; opening and leaf are different. |
| office door opening height | 2.10 | [2.10, 2.40] | m | office | office room | `JGJ/T 67-2019` 4.1.7 | national_code | Hard lower bound for office-room opening height. |
| public building exit / safe door net width | 0.90 | [0.90, 1.20] | m | public / office | evacuation door | `GB 50016-2014` 5.5.18 | national_code | Fire-safety minimum net width; office design standard's 1.00 m opening is stricter for office-room doors. |
| exterior window sill height | 0.90 | [0.80, 1.10] | m | office/public | exterior window | `GB 50352-2019` 6.11.6; Neufert / view-quality literature cross-check | national_code + international | 0.80 m is safety lower bound unless guard exists. 0.90 m is a good A4 typical value, but not a hard correction target. |
| exterior window height | 1.50 | [1.20, 1.80] | m | office | exterior window | `GB/T 5824-2021` / `GB/T 30591-2014` dimension-series basis; industry convention | convention | Use as score only. National codes coordinate dimensions but do not mandate one office window height. |
| exterior window head height | 2.40 | [1.80, 2.40] | m | office | exterior window | Neufert / office-window view literature; common China drafting convention | international + convention | Good fallback when elevation chain is missing. Do not override measured facade dimensions. |
| common single window width | 1.80 | [0.90, 2.40] | m | office | exterior window | `GB/T 50002-2013` modular grid; `GB/T 5824-2021` dimension series | national_code + convention | Treat 0.9/1.2/1.5/1.8/2.1/2.4 m as plausible modular widths. Use to reject ghost-room interpretations, not to resize measured windows. |
| large strip / combined facade window width | 2.40 | [2.40, 4.80] | m | office | facade band | modular convention; `GB/T 5824-2021` | convention | Many office facades use repeated larger bays. This should be facade/WWR score evidence, not a hard single-window prior. |

### Modular Coordination And Grids

| item | value_typical | range[min,max] | unit | building_type | space_type | source | authority | note |
|---|---:|---:|---|---|---|---|---|---|
| basic module | 0.10 | [0.10, 0.10] | m | all | all | `GB/T 50002-2013` 3.1.1 | national_code | 1M = 100 mm. |
| horizontal expanded module | 0.30 | [0.20, 1.20] | m | all | grid/opening | `GB/T 50002-2013` 3.1.2, 3.2.2; `GB 50352-2019` 3.5.2 | national_code | 2M/3M/6M/9M/12M are supported. Use 300 mm and 600 mm as common design-grid scoring. |
| vertical expanded module | 0.10 | [0.10, 0.60] | m | all | height/opening | `GB/T 50002-2013` 3.2.3; `GB 50352-2019` 3.5.2 | national_code | Layer heights and door/window opening heights should be nM. |
| submodule / fine tolerance basis | 0.05 | [0.01, 0.05] | m | all | correction grid | `GB/T 50002-2013` 3.1.2 | national_code | M/10=10 mm, M/5=20 mm, M/2=50 mm. Supports 10 mm output precision and 50 mm BEM snapping. |
| interior partition / pipe-shaft wall thickness prior | 0.10 | [0.05, 0.15] | m | office | partition/shaft | `GB/T 50002-2013` 4.3.2 | national_code | Useful for A1 centerline conversion. Do not force if drawing has measured wall thickness. |
| exterior / load-bearing wall thickness prior | 0.20 | [0.15, 0.30] | m | office | exterior wall | `GB/T 50002-2013` 4.3.2 | national_code | Use as centerline/face ambiguity prior only. |
| office column grid / bay | 8.10 | [7.20, 8.40] | m | office | structural grid | industry convention; modular multiples of 3M | convention | Common Chinese office grids, not a national-code mandate. Score only. |

### Space Types

| item | value_typical | range[min,max] | unit | building_type | space_type | source | authority | note |
|---|---:|---:|---|---|---|---|---|---|
| ordinary office area per person | 6.0 | [6.0, 10.0] | m2/person | office | office | `JGJ/T 67-2019` 4.2.3 | national_code | Hard minimum for use-area/person. Useful to detect impossible tiny "office" cells. |
| single office room area | 10.0 | [10.0, 25.0] | m2 | office | single office | `JGJ/T 67-2019` 4.2.3 | national_code + convention | 10 m2 is "not less than / not advisable below" office-room prior. Width/depth remain convention. |
| office room width | 3.0 | [2.7, 4.5] | m | office | single office | derived from 10 m2 + modular grid | convention | Score only. Do not override real small support rooms. |
| office room depth | 3.6 | [3.0, 6.0] | m | office | single office | derived from 10 m2 + modular grid | convention | Score only. |
| open office density | 8.0 | [6.0, 12.0] | m2/person | office | open office | `JGJ/T 67-2019` 4.2.3 and appendix explanation | national_code + convention | Use 6 m2/person as lower bound; 8-10 m2/person as score typical. |
| corridor width, <=40 m, single-loaded | 1.30 | [1.30, 1.50] | m | office | corridor | `JGJ/T 67-2019` 4.1.9 table | national_code | Hard minimum net width. |
| corridor width, <=40 m, double-loaded | 1.50 | [1.50, 1.80] | m | office | corridor | `JGJ/T 67-2019` 4.1.9 table | national_code | Hard minimum net width. |
| corridor width, >40 m, single-loaded | 1.50 | [1.50, 1.80] | m | office | corridor | `JGJ/T 67-2019` 4.1.9 table | national_code | Hard minimum net width. |
| corridor width, >40 m, double-loaded | 1.80 | [1.80, 2.40] | m | office | corridor | `JGJ/T 67-2019` 4.1.9 table | national_code | Hard minimum net width. |
| WC service radius | 50 | [0, 50] | m | office | public WC | `JGJ/T 67-2019` 4.3.5 | national_code | WC should not vanish from plan attribution. Dimensions below are convention only. |
| WC cubicle size | 1.20 | [0.90, 1.50] | m depth | office/public | WC | common public-toilet planning convention; `JGJ/T 67-2019` 4.3.5 fixture-count basis | convention | Score only. Use OCR/fixtures to confirm. |
| WC room minimum area | 3.0 | [2.0, 8.0] | m2 | office | WC | convention | convention | Never auto-expand/erase if labeled WC. |
| stair flight net width | 1.20 | [1.10, 1.50] | m | office/public | stair | `GB 50352-2019` 6.8.3; `GB 50016-2014` 5.5.18 | national_code | 1.10 m is general public min; high-rise other public stairs min 1.20 m. |
| stair tread width / riser height | 0.26 / 0.175 | [0.26,0.32] / [0.13,0.175] | m | office/public | stair | `GB 50352-2019` 6.8.10 | national_code | Use for stair recognition, not BEM zone sizing. |
| stair platform width | 1.20 | [1.20, 1.50] | m | office/public | stair | `GB 50352-2019` 6.8.4 | national_code | Platform at direction change should be at least stair width and not less than 1.20 m. |
| lift required trigger | 4 | [4, null] | floors | office | lift | `JGJ/T 67-2019` 4.1.5 | national_code | Office buildings four floors and above, or floor elevation >12 m, should have elevator. |
| lift shaft / core cell | 2.0 | [1.6, 2.8] | m width/depth | office | lift | convention; elevator sizing is project-specific | convention | Score only. Use elevator symbol/shaft label, not size alone. |
| lobby / entrance hall | 30 | [10, 200] | m2 | office | lobby | `JGJ/T 67-2019` 4.1.8 qualitative functions | convention | No national hard area. Use label and adjacency to entrance/elevators. |
| storage room area | 4.0 | [2.0, 10.0] | m2 | office | storage | `JGJ/T 67-2019` 4.1.11 storage net-height note | convention | Small labeled storage is real; do not normalize into office. |
| floor electrical / weak-current room | 4.0 | [2.0, 12.0] | m2 | office | MEP/electrical | `JGJ/T 67-2019` 4.5.7-4.5.8 | national_code + convention | Code requires suitability, not a fixed area. Treat as semantic exception. |
| equipment room | project-specific | [null,null] | m2 | office | MEP | `JGJ/T 67-2019` 4.5.1-4.5.5 | national_code | Do not infer from generic size; equipment room dimensions follow equipment and maintenance clearance. |
| tea / pantry room | 6.0 | [3.0, 12.0] | m2 | office | pantry/tea | `JGJ/T 67-2019` 4.3.6 | national_code + convention | Code supports distributed setup, not exact size. Use score only. |
| meeting room, small | 30 | [30, 60] | m2 | office | meeting | `JGJ/T 67-2019` 4.3.2 | national_code | Small meeting room should not be below 30 m2 if identified as meeting room. |
| meeting room, medium | 60 | [60, 120] | m2 | office | meeting | `JGJ/T 67-2019` 4.3.2 | national_code | Medium meeting room should not be below 60 m2. |

### Floor Height / Net Height

| item | value_typical | range[min,max] | unit | building_type | space_type | source | authority | note |
|---|---:|---:|---|---|---|---|---|---|
| cellular/unit office net height with central AC + ceiling | 2.50 | [2.50, 2.90] | m | office | office | `JGJ/T 67-2019` 4.1.11 | national_code | Hard minimum by condition. |
| cellular/unit office net height without central AC | 2.70 | [2.70, 3.20] | m | office | office | `JGJ/T 67-2019` 4.1.11 | national_code | Hard minimum by condition. |
| open/semi-open office net height with central AC + ceiling | 2.70 | [2.70, 3.20] | m | office | open office | `JGJ/T 67-2019` 4.1.11 | national_code | Hard minimum by condition. |
| open/semi-open office net height without central AC | 2.90 | [2.90, 3.40] | m | office | open office | `JGJ/T 67-2019` 4.1.11 | national_code | Hard minimum by condition. |
| office corridor net height | 2.20 | [2.20, 2.80] | m | office | corridor | `JGJ/T 67-2019` 4.1.11 | national_code | Hard minimum for office corridors. |
| storage net height | 2.00 | [2.00, 2.40] | m | office | storage | `JGJ/T 67-2019` 4.1.11 | national_code | "Should preferably not be below"; use as warning. |
| general occupied minimum net height | 2.00 | [2.00, null] | m | public | occupied low point | `GB 50352-2019` 6.3.3 | national_code | General fallback for basements, mezzanines, corridors with normal activity. |
| office floor-to-floor height | 3.60 | [3.30, 4.50] | m | office | typical floor | derived from net height + ceiling/services; modular convention | convention | Use only if elevation/floor-height chain is missing. Do not override measured facade heights. |

### WWR / Facade

| item | value_typical | range[min,max] | unit | building_type | space_type | source | authority | note |
|---|---:|---:|---|---|---|---|---|---|
| WWR, class-A public, severe cold | 0.40 | [0.20, 0.60] | ratio | office/public | single facade | `GB 50189-2015` 3.2.2 | national_code | Code says single-facade WWR should generally not exceed 0.60 in severe cold regions. |
| WWR, class-A public, other regions | 0.40 | [0.20, 0.70] | ratio | office/public | single facade | `GB 50189-2015` 3.2.2 | national_code | Code says single-facade WWR should generally not exceed 0.70 outside severe cold. |
| roof transparent area ratio | 0.10 | [0.00, 0.20] | ratio | public | roof skylight | `GB 50189-2015` 3.2.7 | national_code | Roof transparent area should not exceed 20% unless tradeoff method is used. |
| facade orientation bucket | N/S/E/W | code-defined | deg | public | facade | `GB 50189-2015` 3.2.6 | national_code | North: N +/-60 deg; South: S +/-30 deg; East/West asymmetric 30/60 deg buckets. |

## A0 Tolerance Constants

| constant | recommended value | basis | source | authority | A0 usage |
|---|---:|---|---|---|---|
| coordinate snap grid | 50 mm | 50 mm equals M/2 submodule; also matches common partition thickness granularity and sm21 5cm jitter failure class. | `GB/T 50002-2013` 3.1.2 | national_code | Use for canonical axis snapping after evidence reconciliation, not blind raw-coordinate rounding. |
| output coordinate precision | 10 mm | 10 mm equals M/10 submodule; good display / JSON precision without pretending survey accuracy. | `GB/T 50002-2013` 3.1.2 | national_code | Use as final formatting/quantization. Do not treat 10 mm differences as meaningful BEM evidence. |
| minimum generated edge / sliver width | 0.10 m | EnergyPlus warns when vertex distance is very small around 0.01 m; sm21 produced 0.05 m slivers and instability. 0.10 m is a project safety gate, not an EP official minimum. | EnergyPlus Tips and Tricks "Distance between two vertices < .01" warning; project sm21 evidence | international + project_empirical | Hard gate for generated interzone/surface pieces. If below 0.10 m, merge, re-snap, or mark unsupported. |
| deterministic gap-close threshold | <=100 mm | Fits common partition/shaft wall thickness series; safe for centerline/face ambiguity. | `GB/T 50002-2013` 4.3.2 wall thickness priors | national_code | Auto-close only with matching topology/evidence. |
| conflict gap band | 100-300 mm | Comparable to wall thickness; can be inner-face vs centerline/exterior-face ambiguity. | `GB/T 50002-2013` 4.3.2 | national_code + heuristic | Do not auto-close without evidence. Escalate to A3 and log conflict/correction. |
| large gap / unsupported threshold | >=500 mm | Too large for normal wall-thickness noise; likely real space/void or source error. | heuristic based on wall thickness priors | convention | Do not auto-close. Require A3 decision or unsupported flag. |
| area residual tolerance | +/-5% | Common BEM QA tolerance; no direct national-code geometry tolerance found. `GB 50189` requires reference building to match shape/WWR/use, which supports tracking residuals tightly. | `GB 50189-2015` 3.4.3; BEM practice | national_code + convention | Warning/acceptance metric, not geometry auto-correction license. |
| WWR residual tolerance | +/-5% relative, or +/-0.02 absolute ratio | Keeps facade load signal stable; `GB 50189` uses single-facade WWR bands and performance tables. | `GB 50189-2015` 3.2.2, 3.3.1 tables | national_code + convention | Use for facade/window reconciliation. If measured WWR conflicts, log. |
| perimeter depth | 4.6 m | ASHRAE simplified block / perimeter-core default is 15 ft; allowed range 8-20 ft. | `ASHRAE 90.1-2019 Addendum ag`; `ASHRAE 90.1-2016 Appendix G` addenda | international | For zonification `perimeter_core`, not for partA geometry correction. |
| perimeter depth user range | 2.4-6.1 m | ASHRAE 8-20 ft range. | `ASHRAE 90.1-2019 Addendum ag` | international | User-visible knob. |

## Redline Implementation Notes

Use as hard lower bounds:

- office door opening width/height from `JGJ/T 67-2019` 4.1.7;
- office corridor net widths from `JGJ/T 67-2019` 4.1.9;
- office net heights from `JGJ/T 67-2019` 4.1.11;
- public-window sill safety lower bound from `GB 50352-2019` 6.11.6, unless guard exists;
- WWR upper advisory bands from `GB 50189-2015` 3.2.2, but remember this can be exceeded only through compliant tradeoff / better envelope treatment;
- generated min-edge gate 0.10 m as a project safety rule, not as a building-code rule.

Use only as warning / score:

- common window width/height/head height;
- office column grids 7.2/8.1/8.4 m;
- WC cubicle dimensions;
- lift shaft dimensions;
- MEP room, lobby, storage, tea room typical sizes;
- floor-to-floor height when elevation data exists.

Never allow A4 priors to override consistent measured evidence:

- A4 should emit `prior_score`, `warning`, or `conflict`.
- A prior-driven correction requires missing / contradictory / low-confidence evidence.
- Every prior use must include `prior_id`, source, original value, proposed value, and reason in `corrections[]` or `conflicts[]`.
- Space-type priors must be typed. A 1.2 m-wide space is impossible as a normal office but may be plausible as shaft/storage/WC/service; semantic labels must gate the correction.

## Source Index

- `JGJ/T 67-2019` office standard, CABR Fire code pages: 4.1 general requirements, 4.2 office rooms, 4.3 public rooms, 4.4 service rooms, 4.5 equipment rooms: https://gf.cabr-fire.com/article-33153.htm
- `GB 50352-2019` civil building unified design standard: https://zlglpt.com/book/book_view.aspx?id=3707
- `GB 50189-2015` public building energy design standard: https://www.zlglpt.com/book/book_view.aspx?id=2938
- `GB/T 50002-2013` modular coordination: https://www.zlglpt.com/book/book_view.aspx?catalogid=171&id=349
- `GB/T 30591-2014` door/window opening coordination, SAMR page: https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E02A652B4609A67C7BF5D525E23C44CB
- `GB/T 5824-2021` building door/window opening size series: https://www.antpedia.com/standard/1195815574.html
- `GB 50016-2014` fire code search/source mirror for 5.5.18: https://www.htu.edu.cn/bwc/2019/0712/c11987a148531/pagem.htm
- EnergyPlus Tips and Tricks example warning for very small vertex distance: https://energyplus.net/assets/nrel_custom/pdfs/pdfs_v23.1.0/TipsAndTricksUsingEnergyPlus.pdf
- ASHRAE 90.1-2019 Addendum ag simplified block / perimeter depth: https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90_1_2019_ag_20220909.pdf
- ASHRAE 90.1-2016 addenda / Appendix G thermal blocks: https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90.1-2016/90_1_2016_k_o_x_ab_ac_ad_ae_ag_ah_ak_am_20210324.pdf
- OpenStudio Standards geometry reference for core/perimeter polygons: https://rubydoc.info/gems/openstudio-standards/OpenstudioStandards/Geometry
- Office window view study with sill/head-height range cross-check: https://www.sciencedirect.com/science/article/pii/0007362873900169
