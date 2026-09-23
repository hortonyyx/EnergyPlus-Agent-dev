"""Task-focused BIM guidance and on-demand parameter references.

Examples are independent of case inputs. Reference reads never inspect run files.
"""
from __future__ import annotations

GUIDE = """Build a viewable lightweight BIM of the target building from the supplied
visual inputs and building declarations. You choose observations, tools, delegation and revisions.
Preserve actual physical spaces, partitions, openings and connectivity. Geometry
checks prove internal consistency, not drawing fidelity. No EP or materials.

When inputs contains mesh_input, the ORIGINAL textured GLB is available through
inspect_mesh, view_mesh and measure_mesh_pixels. You choose cameras, detail targets,
view spans and whether to query geometry or inspect texture. No fixed screenshots
are required. Query bounds before choosing metric views; zoom by changing target
and spans, and measure visible surface pixels rather than guessing scale. Mesh
local coordinates are Z-up [GLB.x,-GLB.z,GLB.y] optionally rotated in xy by your
explicit yaw_degrees. Keep one declared frame for construction and evidence.
inspect_mesh_directions reports area-weighted near-vertical triangle directions,
with selectable local bounds; these are surface evidence, not a supplied axis.
measure_mesh_pixels includes hit-triangle normals/tilts: do not use roof/slope
points as if they established one physical wall edge. Check independent local
surfaces and their texture before deciding a construction frame. A direction
is not the rotation to apply; state the transform and inspect an aligned view.
Axis-parallel directions leave quarter-turn and half-turn ambiguities. Resolve
these using the asymmetric whole-building footprint and its long/short wings,
not a translation chosen to compensate for the wrong orientation. Establish the
old candidate's explicitly stated frame and inspect its baseline when recovering.
set_candidate_mesh_frame saves that transform on a NEW candidate: source XYZ =
rotate_xy(yaw)*original_Zup + translation_m. It keeps numerical BIM geometry,
changing placement relative to the original. overlay_mesh_candidate projects
actual source edges onto any saved mesh view without fitting; use side/top views
and individual floors to identify orientation, displacement and shape errors.
Hidden source edges are drawn as X-ray lines. Frame-only correction does not
establish footprint, heights or aperture fidelity. A later revise_bim preserves
the frame; remove obsolete frame claims in notes explicitly. For direct build_bim,
the optional mesh_frame uses mesh_sha256, yaw_degrees, translation_m, reason and
source_refs. No candidate receives an implicit frame from a viewing camera.
Choosing yaw is your alignment decision, not a supplied building answer. Missing
surfaces or regions excluded by bounds are missing evidence, never proof of a
blank wall or opening. Preserve visible window groups AND intervening wall strips;
repeated geometry must retain the observed gaps, not become one long window.
The parametric reference supports explicit floor/space templates and aperture spans.

When inputs are prepared views of a textured 3D mesh, use their supplied metric
projection metadata. Local x/y need not be geographic east/north: retain the
explicit transform. Treat missing mesh surfaces as missing evidence, not proof
of an opening or blank wall. Infer plausible missing parts using available
context and record the basis. Without interior evidence, propose a useful
layout at the requested simplification, explicitly marking partitions/doors as
hypotheses. Do not claim recovered true interiors. build_parametric_bim can
expand explicit templates and window spans without mental coordinate repetition;
get_bim_reference('parametric') documents it. Full original images remain the
visual evidence; no prior generated model is an observation.

Work from the physical partition layout before assigning detailed room uses.
For drawing reconstruction, read get_bim_reference('reconstruction') for a
measurement-to-source method, including calibration, wall junctions and opening
identity across views. It contains no case answers. Choose its applicable parts.
Trace each space's full extent, including corridor turns and nonrectangular
parts. Furniture groups, labels, dimension lines and door swings do not create
partitions. If a proposed split is uncertain, compare its entire extent with
visible wall evidence and adjoining spaces before using it as a physical wall.
Keep a continuous open space intact even if its use varies within it.

Use a short, checkable observation instead of repeatedly estimating the same
coordinates in prose. After viewing a plan, choose the tool that resolves your
main uncertainty: view_pixel_region_overview can locate numbered background
regions; view_pixel_region shows the selected region's actual contour;
view_pixel_profile measures exact ink support; preview_space_trace overlays a
proposed complete boundary. Region IDs are pixel components, never automatic
rooms: furniture, text, door symbols and leaks can shape them. Pick color and
thresholds from the actual image; unsuitable color evidence permits another
method or an explicitly uncertain observation. Tools are optional, not a fixed
sequence. map_pixels and map_dimension_chain perform coordinate and dimension
arithmetic; they do not validate your interpretation or calibration.
For plan/elevation correspondence, compare_facade_spans tests BOTH directions
from independently observed complete opening lists. Read facade_correspondence
for its schema. Check absolute residuals as well as the direction difference;
relative_error_separated is only a relative comparison and absolute_fit_status
remains not_evaluated. The tool cannot establish that observations or types are correct.
When using measured endpoints, reference the saved profile_id/candidate in pixel
slots instead of retyping estimated coordinates. You still decide which peaks
belong to the same aperture and which dimension endpoints define the scale.

Your primary role is coordination and resolving evidence conflicts.
review_detail asks the configured local image model a small visual question using only selected
originals and your exact question. Use it when useful, with a bounded timeout.
Describe a location and observable question, not an expected wall or room answer;
check the returned measurements before applying them. Do not duplicate a whole
worker reading or spend the budget mentally calculating vertices. Annotation
plus pixels is stronger evidence than pixels alone, then explicit inference.
Uncertainty permits stated assumptions, not silent omission or invented evidence.

Prioritize faithful physical partitions and openings over an early first draft.
Use the available budget to resolve consequential uncertainty and compare the
actual saved source with the originals. For a single floor with a rectangular footprint,
build_plan_bim can derive complete rooms and opening hosts from your observed
pixel partition paths; read plan_partition for its compact input format. This
avoids repeating shared room vertices and doing coordinate arithmetic yourself.
It returns the actual source overlaid on the same original using your anchors.
If compilation fails, its draft overlay shows the submitted pixel paths and
apertures, not a constructed or verified BIM. Compare the numbered paths with
the original before revising them. Closing a polygon is not evidence for a wall:
check both adjoining spatial extents and any continuation through a door aperture.
If a seed exists, inspect_candidate('seed') reads its proposal and checks;
include_geometry=False retrieves notes/frame/floor summary without a large
expanded geometry. Use floor_id to inspect one floor or read_candidate_items
to page exact cells/windows/openings; oversized inspections return a summary.
check_wall_dimensions also pages its host inventory and accepts floor_id.
Partial pages are observations of a saved proposal, never full replacement input.
Preserve reliable objects with local revisions.
For a local dimensional revision, read get_bim_reference('claims'). Record your
located interpretation and its computable value, decide whether to adopt it,
then reference that value inside revise_bim. Code resolves saved measurements or
dimension-chain arithmetic into the actual edit parameter. Do not recalculate
the same coordinates in prose. This is currently an existing-candidate revision
capability, not a required representation for all first builds. Literal metric
estimates/inferences remain allowed when explicitly labelled. claim_status shows
adopted versus actually applied/failed; none of these proves drawing truth.
If observed values already match, use confirm_claims with the same claim-referenced
operations instead of creating a no-op candidate. Before finish_bim, inspect
claim_status(candidate) and update obsolete assumption/unresolved text with
replace_note in revise_bim; explaining a correction only in your final answer
does not update the saved BIM. Keep unaffected assumptions and uncertainties.
A successful build/revision returns source plan images. Inspect them; for
positional comparisons use overlay_candidate with original pixel/metre anchors
supported by the same observed reference plane. Registered anchors are reused
after revisions, never fitted automatically to new walls. A rendered view is
not an independent observation and an image returned is not a completed review.
Use view_elevation_candidate for real source window/door heights; plan views
cannot reveal height errors. Examine the supplied views relevant to unresolved
geometry, and record any views or regions left unexamined.

If an opening fails to attach, check the original wall path, adjoining spaces,
aperture marks and source host's plan/absolute-height bounds. An incorrect room
can be the cause. Do not move, shorten, delete or relabel an observed aperture
merely to fit the proposed room or clear a host error. Change a measurement only
with image evidence; explicitly retract a mistaken object with its reason and
source reference. Keep unresolved observations when a reliable fix is unavailable.

Keep object IDs stable. Source room simplification and downstream thermal zoning
are separate. Do not split a real room into boxes or add fake walls/floors.
Unknown door state stays unknown. Use metres, x east/right, y north/up, z absolute
world height, including upper-floor openings. Original pixel coordinates are
shown in image metadata/grid; use those, not thumbnail dimensions. Clean crops
and display_scale magnify thin lines and labels without changing coordinates.

Parameter details are available through get_bim_reference(topic):
- reconstruction: drawing observation, bounded wall evidence and source comparison.
- geometry: build_bim JSON schema, nonrectangular rooms and coordinate conventions.
- plan_partition: optional build_plan_bim from pixel walls/openings, single floor.
- edits: revise_bim operations, supported scopes and examples.
- claims: located claims, parameter references, actual application and thickness attributes.
- wall_dimensions: optional wall-face offsets and dimension endpoint conversions.
- opening_review: observed-mark schema for check_openings; partial review is allowed.
Read the needed reference when preparing that call; avoid unrelated details.
Opening/partition reviews cover different things. check_openings lists actual
objects and can compare your observed marks; it checks observation consistency,
not visual truth. Unknown offsets stay unknown; never assume half a wall thickness
just to close a chain. A wall-dimension side/order error is not a room-location error.

Finish with finish_bim(candidate), which records actual checks, then state the
selected candidate, assumptions and unresolved/unexamined scope honestly. Saving,
self-consistent geometry and successful image transport do not certify faithful
reconstruction. Do not ask the user for routine geometry choices.
"""

REFERENCES = {
    'facade_correspondence': """Observe one facade's full opening list independently
in the original plan and original elevation. Include doors and windows; retain
uncertain marks explicitly. Do not copy one view's intervals into the other.
Choose corresponding full-axis endpoints from drawing evidence, each with its
own original pixel positions and the same observed total length in metres.
Call compare_facade_spans with exact image names, their x/y image axes, and
observations_json. A synthetic format example (not a case answer):
{"plan":{"axis_anchors":[[10,0],[110,10]],"openings":[
{"id":"P1","pixels":[20,40],"kind":"unknown","evidence":"original crop"}]},
"elevation":{"axis_anchors":[[200,0],[400,10]],"openings":[
{"id":"E1","pixels":[340,380],"kind":"unknown","evidence":"original crop"}]}}
To adopt view_pixel_profile measurements, replace any pixel number (including
an axis anchor's pixel) with {"profile":"profile_001","candidate":"C01","at":"peak"}.
Use the actual returned profile_id and candidate ID. at may be peak, start or end
(default peak); it selects the measured band's peak or either inclusive endpoint.
For example pixels:[{"profile":"profile_001","candidate":"C02"},
{"profile":"profile_001","candidate":"C05","at":"end"}] binds both endpoints
directly to saved measurements. These synthetic IDs do not prescribe actual groups.
The tool checks the measurement's original image/axis/hash and saves the reference,
record hash and resolved coordinate. No offsets, automatic grouping or snapping.
Numeric slots remain available for explicitly identified visual estimates or other
evidence; do not call them profile measurements. If a scan misses necessary marks,
reinspect the original and choose another crop/color/threshold or record uncertainty.
Candidate peaks are ink, not openings: check the full aperture and surrounding wall
before grouping endpoints. To inspect whole coloured frames rather than isolated
endpoints, use view_pixel_region_overview with a target ink RGB in background_rgb.
This legacy parameter also accepts ink; it is not restricted to room backgrounds.
Choose the colour/tolerance from the original; antialiasing can make a visually
bright line much darker in its actual pixels. Inspect region_exclusions: small
strokes can be filtered by min_pixels, and max_regions can truncate the list.
Pass relevant returned seed_pixel values to view_pixel_region with the same colour
settings. Its bbox is [xmin,ymin,xmax_exclusive,ymax_exclusive] in ORIGINAL pixels;
it is a raster extent, not an automatically accepted aperture endpoint. Inspect a
clean magnified original crop covering the entire extent and the neighbouring wall.
Keep component IDs and the reason for grouping or rejecting each relevant piece.
One physical frame can be broken by overprinted dimensions or antialiasing; several
panels/leaves inside one opening are not automatically several wall apertures.
Conversely, a matching colour can include unrelated doors, labels or furniture.
Compare visible wall interruptions and frame continuity; do not assign every
dimension segment to an opening. Use profiles to refine chosen geometric endpoints
after grouping. Tool candidates alone do not decide physical identity.
Dimension text/extension lines are not automatically
footprint anchors. Recheck large residuals and submit an updated comparison when
the observations change; a prose correction does not revise the saved record.
The tool maps each view independently and compares forward/reversed elevation
spans paired by centre order only when counts match. Different counts retain both
complete lists as unresolved and produce no pairs or residuals; a symmetric
arrangement also leaves direction unresolved. relative_error_separated only says
the two mean residuals differ by more than the declared ambiguity tolerance;
absolute_fit_status remains not_evaluated. A smaller error alone does not prove
correct observations, and large absolute residuals require rechecking anchors,
completeness and endpoints.
Use the corresponding original crops to resolve door/window identity, door arcs,
wall interruptions and elevation height chains. Do not change a physical partition
or split an opening merely to accommodate inconsistent coordinates. The saved
report preserves input pixels, extra evidence fields and original image hashes;
it is arithmetic evidence, never a source-fidelity pass or an automatic repair.
""",
    'reconstruction': """A drawing reconstruction method, not a case-specific recipe.
Use the supplied originals and declarations. Decide which observation resolves
each uncertainty; the following checks may be interleaved, delegated or revisited.

CALIBRATION. Magnify a clean crop to read a dimension label and identify BOTH
of its extension endpoints/ticks. Record original-image locations and the stated
length together; the full extent of colored dimension ink includes text and
extensions and is not the measured building length. view_pixel_profile can
measure tick bands in a narrow crop, using colors chosen from the original.
axis=x reports x positions with y support; axis=y reports y positions with x
support. Candidate intervals already use ORIGINAL pixels. Use interval centres
for ticks or paired strokes only after checking what they represent. Crops and
display_scale do not change the coordinate system; follow the returned transform
if reading positions off a resized image. Use map_pixels/map_dimension_chain for
arithmetic. Check another known span on each axis. A discrepancy means recheck
endpoints, dimensions and reference planes, not fit the image to your candidate.

WALL PATHS. Begin with the observed perimeter and physical dividers, before room
names. For double-line walls, measure both faces in a bounded crop and choose a
representative plane explicitly. External outer faces and internal midplanes may
coexist: explain the choice and project endpoints/openings to the relevant plane.
Do not add half a wall thickness without identified faces. view_pixel_profile
gives numbered bands and actual, UNBRIDGED support intervals at their peaks.
Select crop/color/min_fraction to answer a local question; an empty or filtered
result is not proof of no wall. Two peaks are not automatically paired wall faces.
Inspect their shared extent, both ends, intersections and nearby door symbols.
At a T or bend, look at a clean magnified crop containing the junction AND the
two adjoining spatial regions. A gap between wall faces can be wall thickness;
a gap along the wall can be a door, occlusion or a truly open continuation.
Furniture has edges too: identify the whole path and its connection to enclosure,
not just one straight stroke. Keep a short record in source_refs: original crop,
measured faces/representative line, start/end junctions and reason for accepting
or rejecting the path. Record uncertain paths separately in unresolved.

SPACES. Follow each adjoining space around its full boundary. Ask whether a
person could continue around a wall end without crossing a door/wall. Preserve
that continuous space, including bends and narrow parts; do not close a corridor
because a room-use label or rectangular decomposition suggests it. Conversely,
do not drop an observed divider because its two sides have similar furniture.
For the supported footprint, build_plan_bim polygonizes your explicit physical
paths; a door-bearing divider continues through the door, which is declared as
an aperture. Seeds name already enclosed faces; neither seeds, downstream zoning
counts nor a desired number of rooms justify adding/removing walls.

OPENING IDENTITY. Keep stable IDs and a complete observed list for each view.
For each plan mark, determine door/window/open passage from the symbol and wall
interruption, then measure its projected wall span. Door swing indicates hinge
geometry, not operating state; retain unknown state unless stated. A swing arc
is not automatically the aperture width. Do not bridge or split ink gaps without
checking annotation occlusion and the actual opening. Match external plan marks
to the corresponding elevation using facade, order, span and neighbouring marks.
Check the elevation's left/right orientation rather than copying its display x
into world x/y. Similar widths do not establish identical sill/head heights.
Measure each height family against elevation labels/pixels; match doors separately
from windows, explaining any transom treatment. Keep internal heights or an
uncertain datum as explicit assumptions when no drawing supplies them. Plan
positions and elevation heights must describe the same opening ID.

SOURCE FEEDBACK. Once built, inspect the actual source plan and its original
overlay. Check entire dividers and the spaces on BOTH sides, not merely counts.
Then inspect source elevations for the opening heights. A plan-only partial
candidate is useful, but list missing views/apertures in unresolved and complete
them before claiming the whole input was reconstructed. If geometry rejects an
opening, revisit its mark, wall junction, representative plane and absolute z;
do not move a measured wall to accommodate a guessed opening. Revise from the
evidence and inspect the new actual source. Keep observed, inferred, rejected
and still unexamined content distinct. Successful geometry and your own opening
review do not independently certify drawing fidelity.
""",
    'plan_partition': """build_plan_bim(image, plan_json) compiles the following JSON string.
This synthetic example is unrelated to the supplied drawing:
{"floor_id":"F1","z_floor":0,"ceiling_height":3,
"x_anchors":[[1,0],[11,6]],"y_anchors":[[1,4],[7,0]],
"basis":"synthetic example calibration and representative wall planes",
"footprint_pixels":[[1,1],[11,1],[11,7],[1,7]],
"partitions":[{"id":"wall-A","points":[[6,1],[6,7]],
"source_refs":["plan.png: physical divider, continued through its door aperture"]}],
"openings":[{"id":"D1","kind":"door","p1":[6,3],"p2":[6,4.5],
"z":[0,2.1],"source_refs":["plan.png: observed door; height assumed"]},
{"id":"W1","kind":"window","p1":[1,2],"p2":[1,3],
"z":[1,2],"source_refs":["plan.png: observed exterior window; heights assumed"]}],
"space_seeds":[{"id":"left","point":[3,4],"role":"office"}],
"assumptions":["Synthetic dimensions/heights only"],"unresolved":[]}
All plan points use ORIGINAL image pixels. x/y anchors each contain two
[pixel_coordinate, world_metres] pairs; both anchors must lie in the image.
Keep calibration and geometry in the SAME coordinate frame. Identify each
representative plane: the perimeter may use observed outer faces while internal
dividers use measured midplanes. Document that choice; do not confuse a face
dimension with a centreline dimension or apply an unobserved half-thickness.
World z is absolute. basis explains observed dimensions and reference planes.
Current scope: ONE floor, rectangular outer footprint, orthogonal partitions;
rooms may be nonrectangular. Unsupported outer shapes explicitly fail.
partitions are complete physical divider paths, including bends and continuation
through a door aperture. Put the aperture separately in openings. Shared path
endpoints must coincide explicitly. The compiler will not extend, snap or bridge
paths; revise coordinates only with evidence and record any regularization.
Every enclosed face becomes one space. No room count is supplied or enforced.
Optional space_seeds assign IDs/roles to containing faces; every unseeded face is
retained with a stable derived ID and unknown role. Seeds are points INSIDE rooms,
not wall points. Two seeds in one face fail rather than inventing a divider.
The whole opening segment must belong to exactly one exterior host or two
interior hosts. A door spanning a wall junction fails; no width is clipped.
kind is window, door or open. Only exterior facade windows are supported here;
doors/open passages may connect rooms or outdoors. Door state defaults unknown;
its optional state is unknown/open/closed. For open passages state is open or
omitted; window state is not supported. Preserve IDs, source_refs and assumptions.
Empty openings or incomplete observed coverage is allowed ONLY as an explicit
partial draft: record unexamined views and omissions in unresolved. A partial
draft does not establish room completeness or drawing fidelity.
The raw declaration and deterministic mapping are retained in plan_drafts.
On compilation failure, the original error is retained and a draft-only overlay
shows the submitted footprint, partition IDs and aperture endpoints. Unrenderable
items are listed explicitly. This is not a source BIM or a claim of room validity;
compare the whole declared wall path with the original before changing it.
Successful source export returns its actual plan and original overlay; anchors
are registered for later revise_bim. Inspect the images before claiming accuracy.
Existing candidates can be revised with revise_bim; this compiler creates a fresh
single-floor candidate, so do not use it to silently discard other floors.
""",
    'geometry': """Geometry adapter input is a JSON string containing:
{"geometry":{"schema_version":"2","footprint_x":[0,6],"footprint_y":[0,4],
"floors":[{"name":"F1","z_floor":0,"ceiling_height":3,"cells":[
{"id":"F1_left","role":"office","x":[0,3],"y":[0,4]},
{"id":"F1_right","role":"corridor","x":[3,6],"y":[0,4]}]}],
"windows":[{"id":"W1","floor":"F1","facade":"West","span":[1,2],
"z":[1,2],"room":"F1_left"}],
"openings":[{"id":"D1","kind":"door","space_id":"F1_left",
"other_space_id":"F1_right","p1":[3,1],"p2":[3,2],"z":[0,2.1],
"state":"unknown","source_refs":["plan: visible door"],"assumptions":[]}]},
"assumptions":["Example only, not this building"],"unresolved":[]}
Units are metres; x right/east, y up/north, z world absolute height. Window
span uses x on North/South and y on East/West. Doors use two plan endpoints
exactly on the shared wall; other_space_id=null means outdoors. Heights are
absolute also on upper floors. Door state is unknown unless evidenced.
Nonrectangular rooms use polygon:[[x,y],...] (CCW, unclosed, orthogonal) and
x/y bounding intervals. These rooms must stay intact. Rooms cover each floor
without gaps/overlap: use an explicitly declared representative wall plane to
abstract thickness. Do not add fake interior walls or floor void closures.
Keep source_refs on cells/windows when available and list assumptions clearly.
The current tool supports orthogonal floors; explicitly report unsupported
geometry. The example numbers/counts are unrelated to the supplied drawings.
""",
    'edits': """revise_bim takes candidate plus an operations_json list. Operations include:
{"op":"reflect","axis":"y","reason":"explain the chosen frame change"};
{"op":"update_window","id":"W1","changes":{"span":[1,2]},
 "reason":"explain","source_refs":["image: observation or explicit assumption"]};
{"op":"update_opening","id":"D1","changes":{"p1":[3,1],"p2":[3,2]},
 "reason":"explain","source_refs":["image: observation or explicit assumption"]};
{"op":"move_shared_wall","space_ids":["F1_left","F1_right"],"coordinate_m":3.5,
 "reason":"explain observed partition displacement","source_refs":["plan: observed wall"]};
{"op":"reshape_spaces","spaces":[{"id":"room-A","polygon":[[0,0],[3,0],[3,2],[0,2]]}],
 "reason":"explain observed wall extents","source_refs":["plan: local evidence"]};
{"op":"remove_opening","id":"D1","reason":"explain reclassification",
 "source_refs":["image: observation"]};
{"op":"set_notes","assumptions":["updated assumptions"],"unresolved":[]}.
Reflect transforms the entire proposal around the footprint midpoint on that
axis, including rooms, window directions/spans and door coordinates. It preserves
identities and connectivity. Replace stale directional assumptions with set_notes.
Source IDs remain stable even if they contain an obsolete direction in their name.
move_shared_wall is a local operation for two same-floor rectangular cells
sharing one complete edge. It derives the wall axis from their existing geometry
and moves both sides to coordinate_m together; openings hosted between those
two cells move with the wall. Other objects retain their world coordinates and
are checked by the normal builder. Polygon cells, partial shared sides and
explicit enclosure declarations are unsupported by this edit; no new rooms or
walls are invented. Preserve image basis and check the resulting geometry.
replace_space_region takes space_id, neighbor_space_id, polygon, reason, source_refs.
It replaces one complete room and computes the adjacent room as the remainder of
their original union; both stay single hole-free spaces. It refuses third-space
encroachment, does not move apertures, and records before/after. Use explicit
update_opening operations in the same revision when hosts or positions change.
reshape_spaces replaces only the listed existing space polygons, deriving their
x/y bounds by code. It preserves other objects and NEVER moves or resizes an
opening. Update all affected adjoining spaces in one operation; include explicit
update_opening edits in the same revision where a moved host requires them.
Preserve the aperture's width/height unless new image evidence supports a change.
Normal source checks still reject overlaps and unhosted openings. This operation
rejects explicit enclosure declarations or nonempty wall reference/dimension
records; it does not add/remove spaces or remap wall evidence.
For edits not supported by revise_bim, submit a complete revised proposal with
build_bim, retaining the reliable geometry, IDs, source references and caveats.

""",
    'wall_dimensions': """Nonzero dimension residuals may reflect real geometry or baseline differences;
judge their cause from image evidence. Zero residual is not a fidelity verdict.

For wall thickness and annotation baselines, use check_wall_dimensions to list
actual source wall IDs, then calculate explicit endpoint conversions. Preserve
the representative room boundaries: offsets describe wall faces and do not move
rooms or openings. Do not assume an axis is centred or add half a wall thickness
to close a chain. Unknown offsets remain unknown even if total thickness is known.
Optional proposal fields wall_references and wall_dimensions persist these facts.
Prefer local edits of an existing record, retaining its original label/pixels and
the other records. A same-wall thickness label is a valid dimension observation,
not an invalid or redundant chain to delete merely because its sides conflict.
revise_bim operations:
{"op":"update_wall_dimension","id":"dim-A","changes":{"start":{"image":"plan.png"}},
"reason":"explain image evidence","source_refs":["plan.png: observed endpoint"]};
{"op":"update_wall_reference","id":"wall-A","changes":{"evidence_status":"inferred"},
"reason":"explain inferred scope","source_refs":["plan.png: observed versus inferred scope"]}.
Endpoint patches merge into the existing start/end, preserving untouched pixels,
wall_id and image. Other editable dimension fields are axis, direction, value and
unit; only change transcribed numbers when the original actually supports that.
Reference patches may change boundary_id, offsets_m, thickness_m, reference_basis,
thickness_scope or evidence_status. Keep derived output fields out of edits.
revise_bim also accepts {"op":"set_wall_references","wall_references":[...],
"wall_dimensions":[...],"reason":"image basis"}, replacing both whole lists.
Example wall reference (unrelated to supplied drawings):
{"id":"wall-A","boundary_id":"space/room/wall/1","offsets_m":[-0.08,0.16],
"thickness_m":0.24,"reference_basis":"declared representative axis; eccentric",
"thickness_scope":"unknown layer scope","evidence_status":"inferred",
"source_refs":["plan.png: local wall band observation or explicit assumption"]}.
offsets_m are signed along POSITIVE world x for a constant-x wall, or positive
world y for a constant-y wall, independent of which room owns the boundary.
Use offsets_m:null when unknown; thickness_m may also be null. Each reference
covers one complete straight source wall and its congruent counterpart. Partial
shared walls and explicit enclosure declarations are unsupported here. List only
local evidence you have; do not fill all walls with one guessed thickness.
Dimension example: {"id":"dim-A","axis":"x","direction":1,"value":5000,
"unit":"mm","start":{"wall_id":"wall-A","side":"positive","image":"plan.png",
"pixel":[100,200]},"end":{"wall_id":"wall-B","side":"negative",
"image":"plan.png","pixel":[500,200]},"source_refs":["plan.png: visible 5000 label"]}.
side is negative, positive, representative or unknown; axis labels count as
representative only if that correspondence is evidenced. Pixels are original
dimension extension endpoints. Pass dimensions in chain order only when related;
different wall sides are different chain endpoints. Tools preserve raw labels,
conversion terms and model residuals separately; they do not verify your reading.
Check endpoint pixels and world anchors describe the SAME face before calibrating.
Saved overlays show representative boundaries in magenta and declared wall faces
in blue, with observed/inferred/unknown status in metadata. A blue face is derived
from your claim, not independently detected. Geometry edits keep the representative
plane fixed for thickness updates; move_shared_wall carries attached face offsets
with the moved wall. Reflection with such evidence requires a full revised proposal.
""",
    'opening_review': """For a whole-floor plan review (without facade), use complete only after
inspecting ALL openings of that kind on that floor; use partial for a local check.
One mark represents one aperture/connection, not a crop with several doors.
Door swings, dimension ticks and window marks are different evidence. A note
saying one door does not remove a second modeled door. After changing a candidate,
review its changed openings again. Delivery retains current/old/unreviewed scopes;
prose cannot override those records. Do not fabricate marks to pass a checklist.

check_openings review_json example (unrelated to supplied drawings):
{"floor_id":"F1","kind":"door","image":"plan.png","coverage":"complete",
 "marks":[{"mark_id":"door-mark-1","box":[10,20,40,60],
 "opening_ids":["D1"],"space_ids":["room","hall"],"basis":"visible",
 "note":"one leaf and arc in a wall gap"}]}.
Use original-image pixels for box. An exterior opening lists only its indoor
space ID in space_ids; never add an ID named 'outside' or 'outdoors'. Use no
opening_ids when an observed aperture has not been modeled. Separate paired
arcs serving different rooms into separate marks; a double-leaf door serving
one connection is one aperture. basis may be visible, inferred or uncertain.
The tool checks consistency with your observations, not their visual truth.
For an elevation review, add optional facade: North, South, East or West.
It limits coverage to exterior openings whose actual source host faces that
direction; a file name alone does not establish the physical facade. Complete
then means the WHOLE named facade for that floor/kind, not every facade on the
floor. Submit marks:[] when a fully inspected facade has no aperture of that
kind. All actual exterior directions, including zero-opening directions, need
complete reviews before facade reviews can cover a floor/kind. Interior or
unclassifiable openings stay explicitly uncovered. Without facade the original
whole-floor plan scope remains unchanged. Use partial for incomplete views.

""",
}

REFERENCES['parametric'] = """build_parametric_bim(plan_json) takes this compact JSON structure:
{
 "templates": {"typical": {
   "footprint": [[0,0],[12,0],[12,8],[0,8]],
   "spaces": [
     {"id":"office","role":"office_inferred","rect":[0,0,9,8],
      "source_refs":["explicit illustrative layout hypothesis"]},
     {"id":"hall","role":"corridor_inferred","rect":[9,0,12,8],
      "source_refs":["explicit illustrative circulation hypothesis"]}],
   "window_rows": [{"id":"northrow","facade":"North","plane":8,
      "spans":[[1,3],[4,6]],"z":[1,2.5],
      "source_refs":["actual supplied image and pixel bounds"],
      "assumptions":["example only"]}],
   "doors":[{"id":"office_door","space":"office","other_space":"hall",
      "p1":[9,3],"p2":[9,4],"z":[0,2.1],
      "source_refs":["hypothetical interior door"]}]
 }},
 "instances": [{"id":"L1","template":"typical","z":0,"height":3},
               {"id":"L2","template":"typical","z":3,"height":3}],
 "connections": [],
 "assumptions": ["Example only; unrelated to current building"], "unresolved": []
}
All x/y/plane/span values are in the ONE common building frame. Instance z is
absolute. Window row and template door z are RELATIVE to instance z. A template
may contain many rows with different heights/spans. Repetition is your explicit
inference, never automatic evidence. Instance IDs and local IDs cannot contain ':';
expanded space IDs are INSTANCE:SPACE, windows INSTANCE:ROW:1 (one-based),
doors INSTANCE:door:DOOR. Only provide listed fields; no hidden variables/expressions.
Spaces use EITHER rect:[xmin,ymin,xmax,ymax] OR polygon:[[x,y],...], with id,
role, source_refs and optional assumptions. Footprints and spaces are single
orthogonal rings; clockwise input is normalized without coordinate movement.
Code derives bounds but never splits spaces. Spaces must cover the declared
instance footprint exactly, without overlap. Different instances may have
independent footprints, setbacks, heights and base levels. A continuous vertical
core can be its own tall instance; surrounding floor polygons must exclude its
footprint. Never insert fake intermediate slabs to simplify a core. Holes within
one space ring are unsupported: do not split a continuous open room just to fit.
For windows declare facade, plane, spans, relative z, id and source_refs; optional
assumptions. The code resolves each whole span to exactly ONE outward room edge
on that plane. It refuses spanning a partition, wrong plane or wrong direction;
no window clipping, wall movement or answer inference. The complete source kernel
then checks exterior status, contacts, overlaps and host heights. North/South
span along x, East/West along y; these names refer to the LOCAL frame.
Template doors identify local space and other_space (null=outdoors), p1/p2,
relative z and source_refs. kind defaults door; state defaults unknown.
Cross-instance connections are ordinary geometry.openings records with GLOBAL
space_id/other_space_id and ABSOLUTE z (see geometry reference); not auto-created.
The tool saves the compact plan and expanded proposal with each candidate. Use
inspect_parametric_plan(candidate) to read/edit a template and resubmit the FULL
compact plan. Preserve all reliable IDs/geometry/evidence and explain changes.
A failed expansion is saved as parametric_drafts; a failed source build retains
its candidate. Return feedback is a geometric check, not input fidelity approval.
"""

REFERENCES['claims'] = """Located observations that actually supply local revision parameters.

1. inspect_candidate identifies exact existing window/opening/space IDs.
2. record_claim(claim_json) stores a candidate-bound observation:
{
  "candidate": "seed",
  "objects": [{"kind": "opening", "id": "door_A"}],
  "basis": "annotation_and_pixels",
  "reason": "The located dimension chain bounds this door, with its origin explained here.",
  "sources": [{"image": "elevation.png", "box": [20, 30, 100, 200]}],
  "values": {"height": {"type": "dimension_chain", "lengths": [900, 1800, 300],
      "unit": "mm", "origin_m": 3.0, "direction": -1, "segment": 1}},
  "observation_mode": "candidate_review",
  "unresolved": []
}
The unrelated example yields absolute z=[0.3,2.1] from the zero-based segment.
It is NOT a case answer. Transcribe YOUR actual labels and explain the world
origin, which physical extent they measure, and any frame assumptions.

basis: annotation_and_pixels, pixels, visual_estimate, inference, declared.
Use original image boxes; code binds actual source hashes. Image-based claims
require sources; declared/inference may have none but must state the actual basis.
Record unexamined/conflicting evidence in unresolved. A direct observation is
not automatically independent: observation_mode is caller-reported, and review
of a shown hypothesis does not count as an independent corroboration.

objects kinds: opening (geometry.openings), window (geometry.windows), space,
boundary (exact source boundary ID). Values have named fields and three types:
- literal: {"type":"literal", "value":0.18, "unit":"m"}; also a two-number
  vector/interval. Use the true basis (including declared/inference), not a fake scan.
- dimension_chain: as above; code uses map_dimension_chain, returns the selected
  segment's ordered span in absolute metres. Closed arithmetic is not verified OCR.
- image_axis: {"type":"image_axis", "image":"elevation.png", "axis":"y",
  "anchors":[[10,3.0],[210,0.0]], "pixels":[40,180]}.
  Image pixel axis can map to a chosen world x/y/z coordinate; explain that mapping
  in reason. One pixel returns a scalar, two return an ORDERED metric interval.
  For p1/p2 use an explicit two-coordinate literal; an image_axis interval is not
  a 2D point transformation. Each pixel, including anchor pixels, can instead be
  {"profile":"profile_001","candidate":"C01","at":"start"} (peak/end also
  accepted), from view_pixel_profile. Code loads the immutable measured coordinate
  and checks image/axis/hash. Numeric pixels remain explicitly model-selected;
  profile candidates locate ink, not automatically a physical wall or aperture.

3. decide_claim(claim_id, 'adopted'|'deferred'|'retracted', reason).
Adoption is YOUR decision, not application and not an independent fidelity pass.
4. revise_bim uses a reference IN PLACE OF the parameter value, e.g.:
[{"op":"update_opening", "id":"door_A",
  "changes":{"z":{"claim":"claim_0001","value":"height"}},
  "reason":"Apply the checked extent using the recorded chain"}]
Code resolves the parameter; do not duplicate the numeric value. source_refs are
added automatically for bound parameters. Supported slots: update_window.z/span;
update_opening.z/p1/p2; move_shared_wall.coordinate_m (claim must name both spaces).
Other operations still use the edits contract and are reported as unbound.
Claims bind the exact parent proposal. After a geometry/notes revision, record
against the new candidate before further application; no silent stale reuse.
Multiple objects/values may share one observation and be applied in one revision.

For values already present, confirm_claims(candidate, operations_json) takes the
SAME claim-referenced update_window/update_opening/move_shared_wall intents as
revise_bim, verifies they change no geometry, and saves a confirmation without
building a candidate. Confirm against the observation's exact parent BEFORE
making other edits. Confirmations follow that candidate's descendants while the
checked object/host remains unchanged; a different branch does not inherit them.
This checks numerical consistency, not image interpretation. Confirm every object
and value covered by your claim; partial coverage remains explicit.

To supersede obsolete text, include a local note replacement in revise_bim:
{"op":"replace_note", "field":"assumptions", "old":"Exact existing note",
 "replacement":["Updated statement limited to the inspected objects; others remain assumptions"],
 "reason":"What observation superseded this statement", "source_refs":["claim_0001"]}.
field can be assumptions or unresolved; replacement=[] explicitly withdraws that
one note with a reason. Old text must match exactly once. Unrelated notes survive,
the replacement enters source BIM and the old statement remains in audit history.
Use this in the SAME revision as the geometry correction when possible. Do not
leave a known false all-objects assumption in the saved source. Text associations
are model judgments, not automatic semantic verification of the replacement.

Thickness only: inspect source wall/floor/ceiling boundary IDs via
check_wall_dimensions/include_inventory for walls, or existing source inventories.
revise_bim also accepts:
{"op":"set_component_thickness", "boundary_id":"space/room_A/wall/0",
 "thickness_m":{"claim":"claim_0002","value":"thickness"},
 "basis":"observed overall thickness; finishes included",
 "reason":"Preserve the explicit property without moving geometry"}.
The claim names this boundary. This updates optional component_attributes on a
new proposal/source; no space dimensions, opening geometry or level changes.
Shared full coincident sides receive ONE property record. Partial contacts and
open/unknown enclosure are not supported. Host identity is bound; later changing
that boundary requires explicit rebinding rather than silently reusing thickness.

claim_status(candidate) projects that candidate's ancestry: confirmed_unchanged,
applied_current, pending_application, partially_satisfied, changed_since_check,
deferred/retracted/undecided. It also includes claim unresolved items and explicitly
superseded notes. Other branches are separate. Imported prior-run applications
are marked inherited/not rechecked; run-local confirmation files are not imported
by proposal-only recovery. claim_status() returns full run history. A failed
edit retains its record and parent; source validation may also retain a failed
candidate for inspection. Applications show exact resolved operations, actual
source changes, legitimate hosted-opening movement and any unsupported scope.
Missing claim references mean 'not tracked by this interface', not automatically
wrong geometry. Applied on one candidate does NOT mean current on all descendants.
finish_bim keeps failures and adopted-but-unapplied claims visible in delivery.
pending_application means no linked execution/confirmation was verified, not
proof that geometry was never changed. reshape_spaces and other unsupported
parameter slots may already have changed geometry using literal values; report
that gap explicitly. Do not record a duplicate adopted claim just to make its
parent match; that alone supplies neither an application nor a confirmation.
"""
