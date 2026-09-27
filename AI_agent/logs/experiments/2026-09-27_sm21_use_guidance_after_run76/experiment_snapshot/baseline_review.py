"""Frozen pre-change coverage/action feedback, a591ef4d; experiment only."""
def room_use_review(source: dict) -> dict:
    """Report saved use-basis coverage, never certify function interpretation."""
    counts = {basis: 0 for basis in ("observed", "inferred", "unknown")}
    unrecorded = []
    unknown = []
    for space in source.get("spaces", []):
        if space.get("role", "unknown") == "unknown":
            unknown.append(space["id"])
        evidence = space.get("role_evidence")
        if evidence is None:
            unrecorded.append(space["id"])
        else:
            counts[evidence["basis"]] += 1
    return {
        "source_model_sha256": source.get("source_model_sha256"),
        "summary": {"total_count": len(source.get("spaces", [])),
                    "recorded_count": sum(counts.values()), "unrecorded_count": len(unrecorded),
                    **{basis + "_count": count for basis, count in counts.items()}},
        "unrecorded_space_ids": unrecorded[:20],
        "unrecorded_ids_truncated": len(unrecorded) > 20,
        "unknown_space_ids": unknown[:20],
        "unknown_ids_truncated": len(unknown) > 20,
        "next_action": ("Read room_types and edits, inspect original room interiors, then use "
                        "revise_bim/set_space_role to choose a plausible use, including a reasonable "
                        "inference from building context. Prefer a broad listed type over unknown; "
                        "avoid spending excessive effort distinguishing similar plausible uses. "
                        "Read remaining cells with read_candidate_items; preserve physical partitions."
                        if unrecorded or unknown else "Use-basis records saved; unresolved inferences remain explicit."),
        "interpretation": "Counts cover structured role_evidence only, not semantic correctness. "
                          "Legacy source_refs may contain other evidence. Unknown remains a fallback when "
                          "no defensible listed use fits; it is not a preferred response to ambiguity.",
        "drawing_fidelity": "not_evaluated", "delivery_blocked": False,
    }
