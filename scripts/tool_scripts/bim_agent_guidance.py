"""Task-focused BIM guidance and on-demand parameter references.

Examples are independent of case inputs. Reference reads never inspect run files.
"""
from __future__ import annotations

GUIDE = """Build a viewable lightweight BIM of the target building from the supplied
visual inputs and building declarations. You choose observations, tools, delegation and revisions.
Preserve actual physical spaces, partitions, openings and connectivity. Geometry
checks prove internal consistency, not drawing fidelity. No EP or materials.

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

Your primary role is coordination and resolving evidence conflicts.
review_detail asks Haiku a small local visual question using only selected
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
If a seed exists, inspect_candidate('seed')
reads its proposal and checks; preserve reliable objects with local revisions.
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
- geometry: build_bim JSON schema, nonrectangular rooms and coordinate conventions.
- plan_partition: optional build_plan_bim from pixel walls/openings, single floor.
- edits: revise_bim operations, supported scopes and examples.
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
Declare the SAME representative plane for calibration, perimeter and dividers.
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
