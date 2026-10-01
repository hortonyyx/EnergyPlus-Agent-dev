# Selected BIM: candidate_04

The selected deliverable is a complete plausible office-building interpretation of the target GLB, with perimeter rooms, continuous circulation, two main stair/lift cores, a connected two-level annex, and separately interpreted attic/roof service volumes. This is an inferred architectural model, not a recovered or certified interior.

Files: [viewer](candidate_04/viewer.html), [actual source](candidate_04/source_model.json), [proposal](candidate_04/proposal.json), [geometry](candidate_04/display_geometry.json), [report](candidate_04/report.json). The bridge finish reply and persisted handoff record the selection.

## Evidence and architectural decisions

I inspected all four raw context crops and twelve original GLB views, queried selected mesh pixels, measured principal extents and façade rows, and kept the original fixed frame with a +15-degree yaw and Z-up mapping. The principal L-shaped building has a tall 6.4 m street level, six 3.15 m office levels above, a two-level courtyard annex, setback attic rooms, and separate north/south roof service volumes. Physical continuous stair and shaft spaces avoid duplicated core rooms and artificial intermediate slabs. Repeated office floors retain an L/T circulation route, office and team-office areas, meeting rooms, break/support rooms and restrooms. The north roof step was refined from the measured mesh, preserving a lower attic and smaller upper plant enclosure.

Saved source plans for every model group, source elevations, footprint and façade overlays were inspected through the common tools. Actual candidate_04 courtyard heights and roof/dormer overlays were reviewed after the final revision. Candidate_01 and candidate_03 contained material source findings; both were repaired before selection. Candidate_04 validation passes with no findings.

## Verified source facts

- 193 spaces, 1,210 boundaries and 639 openings: 421 windows, 216 doors, two open passages; 218 connections.
- No unbuilt openings or unsupported entries. Every space has recorded inferred role evidence.
- All 193 spaces are reachable from an exterior opening in the potential access graph when unknown doors may open. This is a graph check, not an accessibility or egress certification.
- The final audit against candidate_02 preserves 190 space geometries/roles and records the north roof refinement. Sixty-eight window height adjustments were adopted and applied; claim_0001 is applied_current, with no pending claim.
- Source SHA-256: 109a83c7eae69bae5514513ccce8b643439e9cdb2f9c378f82380cfac1c58f12.

## Material limitations

Interior partitions, room use, access and hidden façades are inferred. The source kernel represents orthogonal room volumes and wall openings: curved/pitched mansard and copper roofs are simplified as setback, flat-capped volumes. Four visible elongated annex roof skylights remain unmodeled horizontal apertures. Relief, mullions, stair flights/landings and lift equipment are simplified or omitted. Closely spaced façade panes are grouped where appropriate; some windows and the unseen south face are inferred. Neither mesh visibility nor passing source checks certifies whole-building fidelity, real interior geometry, code compliance or human acceptance.

Located-claim sources currently accept original supplied images rather than saved native mesh observations. The 68 mesh-measured height parameters therefore have honest non-image inference bindings, with original observations and measurement replies retained. Formal coverage is 68 non-image-linked, zero image-linked and 571 unlinked openings; no global height-coverage claim is made. The source opening constructor retains correction pointers but drops proposal window evidence/assumption fields; those remain in the proposal, claims and inference records.

## Retained history and interface limits

Raw evidence and exact tool replies are in mesh_observations/ and bridge/. Twelve inference records, candidate audits, claims, proposals, assembly scripts and final_quality_checks.json remain in this run. remove_opening could not retract windows; a complete preserved proposal removed two inferred ground windows that faced the annex. The failed operation and source findings are retained. A temporary local reply-wrapper omission of structuredContent was corrected; raw bridge replies always retained the results. No frozen inputs, controller or runtime code were modified; no other run/repository, history/evaluation, network, model, subagent or API was used.

## Persisted final selection

finish_bim selected candidate_04 and saved delivery.json. Final source validation passes, with zero findings and zero adopted/unapplied claims. Formal recorded scopes remain unreviewed: 54 opening scopes and 186 façade scopes; no calibrated source-image or point-pair review was registered. Direct native-mesh overlays and source plans were inspected, but those are not equivalent to formal image review coverage. Height coverage lists all 639 openings unchecked under that formal scheme. One failed claim-application attempt remains in the history; the selected claim is subsequently applied_current. The tool retains generation_state in_progress while recording the selected saved handoff.

Final selection elapsed: 3514 seconds, within the 3,600-second development budget.

The reported source SHA-256 above is the builder's embedded source-model identifier, which matches delivery.json; it is not the SHA-256 of the self-identifying JSON file bytes. final_selection_checks.json records both and verifies the selected source, viewer and validation.
