"""Robust, guaranteed-manifold mesh booleans backed by the Manifold library.

Manifold uses its own robust geometric predicates and always returns a valid,
watertight, oriented 2-manifold, so it does not suffer from precision crashes.
The :func:`boolean_chain` / :func:`boolean_batch` entry points run a whole
sequence of operations in C++ without round-tripping intermediate meshes
through Python -- pass the meshes in, get the final result back.
"""

from typing import Iterable
from typing import Literal

import numpy as np
from compas.plugins import plugin

from compas_manifold import _booleans  # type: ignore

from .types import VerticesFaces
from .types import VerticesFacesNumpy
from .types import VerticesFacesPolygonsNumpy
from .types import VerticesFacesSourceNumpy

# =============================================================================
# Pairwise booleans (COMPAS pluggables)
# =============================================================================


def _boolean(
    A: VerticesFaces,
    B: VerticesFaces,
    operation: Literal["union", "difference", "intersection", "split"],
) -> VerticesFacesNumpy:
    """Dispatch a single pairwise boolean operation to the C++ backend."""
    VA, FA = A
    VB, FB = B
    VA = np.asarray(VA, dtype=np.float64)
    FA = np.asarray(FA, dtype=np.int32)
    VB = np.asarray(VB, dtype=np.float64)
    FB = np.asarray(FB, dtype=np.int32)

    if operation == "union":
        return _booleans.boolean_union(VA, FA, VB, FB)
    elif operation == "difference":
        return _booleans.boolean_difference(VA, FA, VB, FB)
    elif operation == "intersection":
        return _booleans.boolean_intersection(VA, FA, VB, FB)
    elif operation == "split":
        return _booleans.split(VA, FA, VB, FB)
    else:
        raise NotImplementedError(operation)


@plugin(category="booleans", pluggable_name="boolean_union_mesh_mesh")
def boolean_union_mesh_mesh(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesNumpy:
    """Boolean union of two meshes.

    Parameters
    ----------
    A
        Mesh A as a tuple of vertices and faces.
    B
        Mesh B as a tuple of vertices and faces.

    Returns
    -------
    VerticesFacesNumpy

    Examples
    --------
    >>> from compas.geometry import Box, Sphere, Polyhedron
    >>> from compas_manifold.booleans import boolean_union_mesh_mesh

    >>> box = Box(2)
    >>> sphere = Sphere(1.0, point=[1, 1, 1])

    >>> A = box.to_vertices_and_faces(triangulated=True)
    >>> B = sphere.to_vertices_and_faces(u=32, v=32, triangulated=True)

    >>> V, F = boolean_union_mesh_mesh(A, B)
    >>> shape = Polyhedron(V.tolist(), F.tolist())

    """
    return _boolean(A, B, "union")


@plugin(category="booleans", pluggable_name="boolean_difference_mesh_mesh")
def boolean_difference_mesh_mesh(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesNumpy:
    """Boolean difference (A - B) of two meshes.

    Parameters
    ----------
    A
        Mesh A as a tuple of vertices and faces.
    B
        Mesh B as a tuple of vertices and faces.

    Returns
    -------
    VerticesFacesNumpy

    Examples
    --------
    >>> from compas.geometry import Box, Sphere, Polyhedron
    >>> from compas_manifold.booleans import boolean_difference_mesh_mesh

    >>> box = Box(2)
    >>> sphere = Sphere(1.0, point=[1, 1, 1])

    >>> A = box.to_vertices_and_faces(triangulated=True)
    >>> B = sphere.to_vertices_and_faces(u=32, v=32, triangulated=True)

    >>> V, F = boolean_difference_mesh_mesh(A, B)
    >>> shape = Polyhedron(V.tolist(), F.tolist())

    """
    return _boolean(A, B, "difference")


@plugin(category="booleans", pluggable_name="boolean_intersection_mesh_mesh")
def boolean_intersection_mesh_mesh(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesNumpy:
    """Boolean intersection of two meshes.

    Parameters
    ----------
    A
        Mesh A as a tuple of vertices and faces.
    B
        Mesh B as a tuple of vertices and faces.

    Returns
    -------
    VerticesFacesNumpy

    Examples
    --------
    >>> from compas.geometry import Box, Sphere, Polyhedron
    >>> from compas_manifold.booleans import boolean_intersection_mesh_mesh

    >>> box = Box(2)
    >>> sphere = Sphere(1.0, point=[1, 1, 1])

    >>> A = box.to_vertices_and_faces(triangulated=True)
    >>> B = sphere.to_vertices_and_faces(u=32, v=32, triangulated=True)

    >>> V, F = boolean_intersection_mesh_mesh(A, B)
    >>> shape = Polyhedron(V.tolist(), F.tolist())

    """
    return _boolean(A, B, "intersection")


@plugin(category="booleans", pluggable_name="split_mesh_mesh")
def split_mesh_mesh(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesNumpy:
    """Split mesh A with mesh B.

    The result is a single mesh holding the part of A inside B and the part of
    A outside B as disconnected components.

    Parameters
    ----------
    A
        Mesh A as a tuple of vertices and faces.
    B
        Mesh B as a tuple of vertices and faces.

    Returns
    -------
    VerticesFacesNumpy

    Examples
    --------
    >>> from compas.datastructures import Mesh
    >>> from compas.geometry import Box, Sphere
    >>> from compas_manifold.booleans import split_mesh_mesh

    >>> box = Box(2)
    >>> sphere = Sphere(1.0, point=[1, 1, 1])

    >>> A = box.to_vertices_and_faces(triangulated=True)
    >>> B = sphere.to_vertices_and_faces(u=32, v=32, triangulated=True)

    >>> V, F = split_mesh_mesh(A, B)
    >>> mesh = Mesh.from_vertices_and_faces(V, F)

    """
    return _boolean(A, B, "split")


split = split_mesh_mesh


# =============================================================================
# Polygonal faces from coplanar grouping (merge the triangle soup)
# =============================================================================
#
# Manifold is a triangle-mesh library, but it tags every output triangle with a
# coplanar-face id: triangles that are coplanar and belong to the same planar
# face share one id (see ``*_with_polygons`` below, which returns it as ``P``).
# Grouping triangles on that id recovers the polygonal (n-gon) faces and the
# clean outlines, discarding the interior triangulation diagonals.


def _boolean_with_polygons(
    A: VerticesFaces,
    B: VerticesFaces,
    operation: Literal["union", "difference", "intersection"],
) -> VerticesFacesPolygonsNumpy:
    VA, FA = A
    VB, FB = B
    VA = np.asarray(VA, dtype=np.float64)
    FA = np.asarray(FA, dtype=np.int32)
    VB = np.asarray(VB, dtype=np.float64)
    FB = np.asarray(FB, dtype=np.int32)

    if operation == "union":
        return _booleans.boolean_union_with_polygons(VA, FA, VB, FB)
    if operation == "difference":
        return _booleans.boolean_difference_with_polygons(VA, FA, VB, FB)
    if operation == "intersection":
        return _booleans.boolean_intersection_with_polygons(VA, FA, VB, FB)
    raise NotImplementedError(operation)


def boolean_union_mesh_mesh_with_polygons(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesPolygonsNumpy:
    """Boolean union returning ``(V, F, P)`` where ``P[i]`` is the coplanar-face id of triangle ``i``.

    Triangles sharing an id form one planar n-gon face. Pass the result to
    :func:`merge_coplanar_faces`, :func:`coplanar_outline_edges`, or
    :func:`coplanar_polygons` to recover polygonal faces / clean outlines.
    """
    return _boolean_with_polygons(A, B, "union")


def boolean_difference_mesh_mesh_with_polygons(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesPolygonsNumpy:
    """Boolean difference returning ``(V, F, P)`` of coplanar-face ids. See :func:`boolean_union_mesh_mesh_with_polygons`."""
    return _boolean_with_polygons(A, B, "difference")


def boolean_intersection_mesh_mesh_with_polygons(A: VerticesFaces, B: VerticesFaces) -> VerticesFacesPolygonsNumpy:
    """Boolean intersection returning ``(V, F, P)`` of coplanar-face ids. See :func:`boolean_union_mesh_mesh_with_polygons`."""
    return _boolean_with_polygons(A, B, "intersection")


def merge_coplanar_faces(
    V: np.ndarray,
    F: np.ndarray,
    P: np.ndarray,
) -> "dict[int, list[list[int]]]":
    """Merge each coplanar-face group into ordered boundary loops.

    For every polygon id in ``P`` this collects the triangles of that group and
    extracts its boundary as one or more **oriented closed loops** of vertex
    indices, dropping the interior triangulation diagonals.

    A simple face yields a single loop. **A face with holes yields several
    loops** — one outer boundary plus one loop per hole. They are distinguished
    by orientation: a loop wound consistently with the face normal (positive
    signed area) is an outer boundary; a reversed loop (negative signed area)
    is a hole. Use :func:`coplanar_polygons` to get them already classified and
    nested.

    Returns
    -------
    dict[int, list[list[int]]]
        Maps each polygon id to its list of boundary loops (each a list of
        vertex indices into ``V``).
    """
    F = np.asarray(F)
    P = np.asarray(P).reshape(-1)

    result: dict = {}
    for pid in np.unique(P):
        tris = F[P == pid]

        # All directed edges of the group. An interior diagonal appears in both
        # directions (shared by two triangles); a boundary edge appears once.
        present = set()
        for tri in tris:
            a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
            present.add((a, b))
            present.add((b, c))
            present.add((c, a))

        adj: dict = {}
        for (u, w) in present:
            if (w, u) not in present:
                adj.setdefault(u, []).append(w)

        # Walk the directed boundary edges into closed loops, consuming them.
        loops: list = []
        for start in list(adj.keys()):
            while adj.get(start):
                loop = [start]
                w = adj[start].pop()
                while w != start:
                    loop.append(w)
                    nxt = adj.get(w)
                    if not nxt:
                        break  # open chain (should not happen for a closed mesh)
                    w = nxt.pop()
                loops.append(loop)

        result[int(pid)] = loops
    return result


def coplanar_outline_edges(
    V: np.ndarray,
    F: np.ndarray,
    P: np.ndarray,
) -> np.ndarray:
    """Return the clean outline edges of the merged polygonal faces.

    An edge is part of an outline when it separates two different coplanar-face
    ids (a feature edge), or lies on an open boundary of the mesh. Interior
    triangulation diagonals — shared by two triangles of the *same* face — are
    excluded. **Hole boundaries are included automatically**, because a hole's
    rim separates the face from whatever geometry carved it (a different id).

    Returns
    -------
    np.ndarray
        ``Ex2`` int array of vertex-index pairs into ``V``.
    """
    F = np.asarray(F)
    P = np.asarray(P).reshape(-1)

    edge_pids: dict = {}
    edge_count: dict = {}
    for t in range(F.shape[0]):
        a, b, c = int(F[t, 0]), int(F[t, 1]), int(F[t, 2])
        pid = int(P[t])
        for u, w in ((a, b), (b, c), (c, a)):
            key = (u, w) if u < w else (w, u)
            edge_count[key] = edge_count.get(key, 0) + 1
            edge_pids.setdefault(key, set()).add(pid)

    edges = [key for key, pids in edge_pids.items() if edge_count[key] == 1 or len(pids) > 1]
    if not edges:
        return np.zeros((0, 2), dtype=np.int32)
    return np.asarray(edges, dtype=np.int32)


def _loop_signed_area(points: np.ndarray, normal: np.ndarray) -> float:
    """Signed area of a planar 3D loop, positive when wound CCW about ``normal``."""
    cross_sum = np.zeros(3)
    n = len(points)
    for i in range(n):
        cross_sum += np.cross(points[i], points[(i + 1) % n])
    return 0.5 * float(np.dot(normal, cross_sum))


def _face_normal(V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Area-weighted normal of a group of triangles (robust to slivers)."""
    n = np.zeros(3)
    for tri in tris:
        p0, p1, p2 = V[int(tri[0])], V[int(tri[1])], V[int(tri[2])]
        n += np.cross(p1 - p0, p2 - p0)
    norm = np.linalg.norm(n)
    return n / norm if norm > 0 else n


def coplanar_polygons(
    V: np.ndarray,
    F: np.ndarray,
    P: np.ndarray,
) -> "list[dict]":
    """Reconstruct polygonal faces with holes from a coplanar-grouped result.

    Builds on :func:`merge_coplanar_faces` and classifies the loops of each
    coplanar-face group into outer boundaries and holes by orientation
    (signed area relative to the face normal). Each hole is nested under the
    outer loop that contains it.

    Returns
    -------
    list[dict]
        One entry per outer boundary, with keys:

        * ``"normal"`` — the unit face normal (``(3,)`` array);
        * ``"outer"`` — vertex indices of the outer loop (CCW about the normal);
        * ``"holes"`` — list of vertex-index loops for the holes (CW).

    Notes
    -----
    A plain triangle/polygon mesh cannot store a face with a hole, so this
    "outer + holes" form is the right representation: feed it to a constrained
    triangulator if you need a watertight re-tessellation, or draw the outer
    and hole loops directly for clean outlines.
    """
    V = np.asarray(V, dtype=np.float64)
    F = np.asarray(F)
    P = np.asarray(P).reshape(-1)

    loops_by_pid = merge_coplanar_faces(V, F, P)

    faces: list = []
    for pid, loops in loops_by_pid.items():
        if not loops:
            continue
        normal = _face_normal(V, F[P == pid])

        outers: list = []
        holes: list = []
        for loop in loops:
            pts = V[np.asarray(loop, dtype=np.int64)]
            area = _loop_signed_area(pts, normal)
            (outers if area >= 0 else holes).append((loop, abs(area)))

        if not outers:
            # Degenerate: no positively-oriented loop -- treat the largest as outer.
            outers = [max(loops, key=lambda lp: abs(_loop_signed_area(V[np.asarray(lp, dtype=np.int64)], normal)))]
            outers = [(outers[0], 0.0)]
            holes = []

        # Build a 2D basis on the face plane for point-in-polygon hole nesting.
        ref = np.array([1.0, 0.0, 0.0]) if abs(normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u_axis = np.cross(normal, ref)
        u_axis = u_axis / (np.linalg.norm(u_axis) or 1.0)
        v_axis = np.cross(normal, u_axis)

        def to_2d(indices):
            pts = V[np.asarray(indices, dtype=np.int64)]
            return np.column_stack([pts @ u_axis, pts @ v_axis])

        def point_in_poly(pt, poly):
            x, y = pt
            inside = False
            n = len(poly)
            j = n - 1
            for i in range(n):
                xi, yi = poly[i]
                xj, yj = poly[j]
                if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi):
                    inside = not inside
                j = i
            return inside

        # Assign each hole to the outer loop containing its first vertex.
        outer_polys = [(loop, to_2d(loop)) for loop, _ in outers]
        assigned: dict = {id(loop): [] for loop, _ in outers}
        for hole_loop, _ in holes:
            hpt = to_2d([hole_loop[0]])[0]
            for loop, poly2d in outer_polys:
                if point_in_poly(hpt, poly2d):
                    assigned[id(loop)].append(hole_loop)
                    break

        for loop, _ in outers:
            faces.append(
                {
                    "normal": normal,
                    "outer": list(loop),
                    "holes": [list(h) for h in assigned[id(loop)]],
                }
            )

    return faces


# =============================================================================
# Chained / batched booleans (whole pipeline evaluated in C++)
# =============================================================================

_OP_CODES = {"union": 0, "difference": 1, "intersection": 2, "xor": 3}


def _flatten(meshes: Iterable[VerticesFaces]):
    """Concatenate meshes into flat (V, F) arrays + per-mesh row counts.

    Face indices stay mesh-local; the per-mesh counts tell C++ where each mesh
    begins. This is the entire Python -> C++ marshalling for the chain/batch
    entry points.
    """
    Vs: list = []
    Fs: list = []
    v_counts: list = []
    f_counts: list = []
    for V, F in meshes:
        V = np.asarray(V, dtype=np.float64)
        F = np.asarray(F, dtype=np.int32)
        Vs.append(V)
        Fs.append(F)
        v_counts.append(int(V.shape[0]))
        f_counts.append(int(F.shape[0]))

    V_flat = np.vstack(Vs) if Vs else np.zeros((0, 3), dtype=np.float64)
    F_flat = np.vstack(Fs) if Fs else np.zeros((0, 3), dtype=np.int32)
    return V_flat, F_flat, v_counts, f_counts


def boolean_chain(
    meshes: Iterable[VerticesFaces],
    operations: Iterable[Literal["union", "difference", "intersection", "xor"]],
) -> VerticesFacesNumpy:
    """Run a chain of boolean operations entirely in C++ without round-tripping intermediates.

    Computes ``result = meshes[0]; result = result OP_i meshes[i + 1]`` for each
    operation in order. The whole mesh collection is sent to C++ in a single
    call; intermediate meshes never leave C++; only the final ``(V, F)`` comes
    back to Python.

    Because Manifold guarantees a valid manifold result at every step, this
    handles geometrically degenerate input (e.g. three cylinders meeting at the
    origin) without any geometric work-arounds.

    Parameters
    ----------
    meshes : iterable of (V, F)
        Triangle meshes. Length must be ``len(operations) + 1``.
    operations : iterable of {"union", "difference", "intersection", "xor"}
        Per-step operation. ``"difference"`` is ``result - meshes[i + 1]``;
        ``"xor"`` is the symmetric difference.

    Returns
    -------
    (V, F) : VerticesFacesNumpy
        The final mesh.
    """
    meshes = list(meshes)
    V_flat, F_flat, v_counts, f_counts = _flatten(meshes)

    op_codes: list = []
    for op in operations:
        if op not in _OP_CODES:
            raise ValueError(f"unknown operation {op!r}; must be one of {sorted(_OP_CODES)}")
        op_codes.append(_OP_CODES[op])

    if len(op_codes) + 1 != len(meshes):
        raise ValueError("len(operations) must equal len(meshes) - 1")

    return _booleans.boolean_chain(V_flat, F_flat, v_counts, f_counts, op_codes)


def boolean_batch(
    meshes: Iterable[VerticesFaces],
    operation: Literal["union", "difference", "intersection"],
) -> VerticesFacesNumpy:
    """Apply a single boolean operation across many meshes using ``BatchBoolean``.

    Manifold's ``BatchBoolean`` evaluates the whole CSG batch at once, which is
    considerably faster than folding the operation pairwise. ``"union"`` merges
    all meshes; ``"difference"`` subtracts every later mesh from the first;
    ``"intersection"`` keeps the region common to all.

    Parameters
    ----------
    meshes : iterable of (V, F)
        Triangle meshes (at least one).
    operation : {"union", "difference", "intersection"}

    Returns
    -------
    (V, F) : VerticesFacesNumpy
    """
    if operation == "xor" or operation not in _OP_CODES:
        raise ValueError("operation must be one of 'union', 'difference', 'intersection'")
    V_flat, F_flat, v_counts, f_counts = _flatten(list(meshes))
    return _booleans.boolean_batch(V_flat, F_flat, v_counts, f_counts, _OP_CODES[operation])


def boolean_chain_with_face_source(
    meshes: Iterable[VerticesFaces],
    operations: Iterable[Literal["union", "difference", "intersection"]],
) -> VerticesFacesSourceNumpy:
    """Boolean chain that also tracks, for every output face, which input mesh and face produced it.

    Returns ``(V, F, S)`` where ``S[i] = [mesh_id, face_id]``. ``mesh_id`` is
    the position of the source mesh in ``meshes`` and ``face_id`` is the row of
    the original face in that mesh's input face array. Tracking uses Manifold's
    native mesh-relation machinery (``OriginalID`` + output run / face IDs).

    ``"xor"`` is not supported here.
    """
    meshes = list(meshes)
    V_flat, F_flat, v_counts, f_counts = _flatten(meshes)

    op_codes: list = []
    for op in operations:
        if op == "xor":
            raise ValueError("xor is not supported by boolean_chain_with_face_source")
        if op not in _OP_CODES:
            raise ValueError(f"unknown operation {op!r}; must be one of union/difference/intersection")
        op_codes.append(_OP_CODES[op])

    if len(op_codes) + 1 != len(meshes):
        raise ValueError("len(operations) must equal len(meshes) - 1")

    return _booleans.boolean_chain_with_face_source(V_flat, F_flat, v_counts, f_counts, op_codes)


def split_by_source(
    V: np.ndarray,
    F: np.ndarray,
    S: np.ndarray,
) -> "dict[int, tuple[np.ndarray, np.ndarray]]":
    """Split a face-source-tagged boolean result into one mesh per source.

    Given ``(V, F, S)`` from :func:`boolean_chain_with_face_source`, returns a
    dict mapping each ``mesh_id`` present in ``S[:, 0]`` to its own
    ``(V_sub, F_sub)`` pair. ``V_sub`` contains only the vertices referenced by
    that submesh's faces and ``F_sub`` is reindexed accordingly.
    """
    V = np.asarray(V)
    F = np.asarray(F)
    S = np.asarray(S)

    out: dict = {}
    for mesh_id in np.unique(S[:, 0]):
        if mesh_id < 0:
            continue
        face_mask = S[:, 0] == mesh_id
        F_sub = F[face_mask]
        used = np.unique(F_sub.reshape(-1))
        remap = np.full(V.shape[0], -1, dtype=np.int64)
        remap[used] = np.arange(used.shape[0])
        out[int(mesh_id)] = (V[used], remap[F_sub].astype(F.dtype))
    return out


# =============================================================================
# Convenience: subtract many cutters from a single mesh
# =============================================================================


def boolean_difference_mesh_meshes(A: VerticesFaces, Bs: Iterable[VerticesFaces]) -> VerticesFacesNumpy:
    """Subtract many meshes from A in a single batched operation.

    Uses Manifold's ``BatchBoolean`` so all cutters are removed in one robust
    CSG evaluation rather than an accumulating pairwise chain.
    """
    Bs = list(Bs)
    return boolean_batch([A, *Bs], "difference")
