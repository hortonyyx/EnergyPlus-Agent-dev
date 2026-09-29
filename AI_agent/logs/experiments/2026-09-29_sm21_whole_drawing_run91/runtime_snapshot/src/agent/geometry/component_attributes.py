"""Optional wall/slab thickness metadata, with no geometry displacement."""
import copy
import math


def boundary_identity(boundary):
    return {key: copy.deepcopy(boundary[key]) for key in
            ("id", "space_id", "geometry_type", "kind", "vertices", "counterpart_ids")}


def thickness_record(source, boundary_id, thickness_m, *, basis, source_refs):
    if type(thickness_m) not in (int, float) or not math.isfinite(thickness_m) or thickness_m <= 0:
        raise ValueError("thickness_m must be a finite positive number")
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("thickness basis must describe observed/inferred value and scope")
    if not isinstance(source_refs, list) or not source_refs or any(not isinstance(s, str) or not s.strip() for s in source_refs):
        raise ValueError("thickness requires source_refs")
    boundaries = {row["id"]: row for row in source["boundaries"]}
    if boundary_id not in boundaries:
        raise ValueError("unknown thickness boundary")
    boundary = boundaries[boundary_id]
    hosts = [boundary, *(boundaries[identity] for identity in boundary["counterpart_ids"])]
    category = "wall" if boundary["geometry_type"] == "wall" else "slab"
    if any(host["kind"] != "physical" or
           ("wall" if host["geometry_type"] == "wall" else "slab") != category for host in hosts):
        raise ValueError("thickness only supports physical wall/slab boundaries")
    # Partial contact may describe multiple physical elements. Do not silently
    # spread one thickness across an entire floor or multiple wall segments.
    if any({tuple(p) for p in host["vertices"]} != {tuple(p) for p in boundary["vertices"]} for host in hosts):
        raise ValueError("partial contacts need explicit component segmentation")
    return {"boundary_ids": sorted(host["id"] for host in hosts), "kind": category,
            "thickness_m": thickness_m, "basis": basis, "source_refs": source_refs,
            "host_identity": sorted((boundary_identity(host) for host in hosts), key=lambda row: row["id"]),
            "geometry_effect": "none"}


def validate_component_attributes(source, records):
    if not isinstance(records, list):
        raise ValueError("component_attributes must be a list")
    used, result = set(), []
    for row in records:
        if not isinstance(row, dict) or set(row) != {
                "boundary_ids", "kind", "thickness_m", "basis", "source_refs", "host_identity", "geometry_effect"}:
            raise ValueError("invalid component thickness record")
        ids = row["boundary_ids"]
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
            raise ValueError("component requires boundary IDs")
        expected = thickness_record(source, ids[0], row["thickness_m"],
                                    basis=row["basis"], source_refs=row["source_refs"])
        if expected != row:
            raise ValueError("component host changed; explicitly rebind thickness to the revised geometry")
        if used.intersection(ids):
            raise ValueError("duplicate thickness for the same physical component")
        used.update(ids)
        result.append(copy.deepcopy(row))
    return result
