"""Task-focused BIM guidance and on-demand parameter references.

Examples are independent of case inputs. Reference reads never inspect run files.
"""
from __future__ import annotations

GUIDE = """Build a viewable lightweight BIM of the target building from the supplied
original drawings. You choose observations, tools, delegation and revisions.
Preserve actual physical spaces, partitions, openings and connectivity. Geometry
checks prove internal consistency, not drawing fidelity. No EP or materials.

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

Your primary role is coordination and conflict decisions within the time budget.
review_detail asks Haiku a small local visual question using only selected
originals and your exact question. Use it when useful, with a bounded timeout.
Describe a location and observable question, not an expected wall or room answer;
check the returned measurements before applying them. Do not duplicate a whole
worker reading or spend the budget mentally calculating vertices. Annotation
plus pixels is stronger evidence than pixels alone, then explicit inference.
Uncertainty permits stated assumptions, not silent omission or invented evidence.

Save a useful initial candidate early and reserve time to compare the actual
saved source with the originals. If a seed exists, inspect_candidate('seed')
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
    'wall_dimensions': """For wall thickness and annotation baselines, use check_wall_dimensions to list
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
    'opening_review': """check_openings review_json example (unrelated to supplied drawings):
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
