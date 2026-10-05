"""Exact fact comparison modulo GEOS's arbitrary start vertex of closed rings.

No coordinate tolerance, discarded field, reversed traversal, or sorted set of
edges: only cyclic shifts and their verified derived identifiers are normalized.
"""
import copy
import hashlib


def _edge_id(edge, sequence):
    parts = [edge["cavity_id"], sequence, edge["axis"], edge["cavity_const"],
             edge["span_lo"], edge["span_hi"], edge["side"], *edge["wall_ids"]]
    return "boundary-edge:" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def canonical_ring_origins(document):
    document = copy.deepcopy(document)
    for view in document["views"]:
        mapping = {}
        if view.get("footprint"):
            for ri, ring in enumerate(view["footprint"]["rings"]):
                points = ring["points"]
                assert len(points) >= 4 and points[0] == points[-1]
                count = len(points) - 1
                start = min(range(count), key=lambda i: tuple(points[i]))
                ring["points"] = points[start:count] + points[:start] + [points[start]]
                prefix = f"footprint:{view['view_id']}:ring:{ri}:edge:"
                mapping.update({prefix + str(i): prefix + str((i-start) % count)
                                for i in range(count)})
        groups = {}
        for edge in view.get("boundary_edges", []):
            witness = edge["evidence"].get("footprint_edge_id")
            if witness in mapping:
                edge["evidence"]["footprint_edge_id"] = mapping[witness]
            groups.setdefault(edge["cavity_id"], []).append(edge)
        for edges in groups.values():
            # Preserve traversal order: malformed, reordered, or duplicate
            # sequences cannot become valid merely through normalization.
            assert [e["sequence"] for e in edges] == list(range(len(edges)))
            for edge in edges:
                assert edge["id"] == _edge_id(edge, edge["sequence"])
            start = min(range(len(edges)), key=lambda i: (tuple(edges[i]["p1"]), tuple(edges[i]["p2"])))
            for sequence, edge in enumerate(edges[start:] + edges[:start]):
                edge["id"] = _edge_id(edge, sequence)
                edge["sequence"] = sequence
        if "boundary_edges" in view:
            view["boundary_edges"].sort(key=lambda e: (e["cavity_id"], e["sequence"]))
    return document
