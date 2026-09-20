You are reproducing the historical reading method on sm24_anchor.
Read and follow skills/intake_pipeline/0_reading/session_kickoff.md and its required
rule documents and worked example. The actual inputs are the five original PNGs
and unmodified building declaration in case_data/. Its path strings identify the
same basenames here; do not follow paths outside this workspace.

For this run cv_toolbox.md is REQUIRED, not optional: measure before drawing.
Use the provided historical scripts/tool_scripts/cv_probe.py tools. Calibrate from
dimension ticks, measure walls/windows, crop to classify candidates and retain
accepted/rejected decisions with reasons. Pixel measurement of unlabeled components
is allowed with honest provenance and no invented dimension references.

Complete ONE pilot, case_data/1f_view.png, write 0_reading/1f_view.json plus its
CV evidence and self-check, then STOP for external review. Do not batch other
images until explicitly approved. Follow the historical JSON schema rather than
inventing a room/BIM output. Keep the exact image pixel frame; no resizing originals.

You may use Read, Write, Edit and Bash/Python within THIS workspace only. Do not
read repository/history/results/GT, other workspaces, credentials, or home files.
No network commands, subprocess model calls, or other agents. Do not modify supplied
src/, scripts/, skills/, case_data/ or the format example. Put any helper scripts in
requests/ and generated artifacts in 0_reading/. All calculations may use Python.
The external review is part of this experiment; report your actual unexamined items.
