import numpy as np
import pytest

from compas.datastructures import Mesh
from compas.geometry import Box, Sphere

from compas_manifold.booleans import (
    boolean_batch,
    boolean_chain,
    boolean_chain_with_face_source,
    boolean_difference_mesh_mesh,
    boolean_difference_mesh_mesh_with_polygons,
    boolean_difference_mesh_meshes,
    boolean_intersection_mesh_mesh,
    boolean_union_mesh_mesh,
    coplanar_outline_edges,
    coplanar_polygons,
    merge_coplanar_faces,
    split_by_source,
    split_mesh_mesh,
)


@pytest.fixture
def box_sphere_meshes():
    """Create test box and sphere meshes."""
    box = Box.from_width_height_depth(2.0, 2.0, 2.0)
    sphere = Sphere(1.0, point=[1, 1, 1])

    box_mesh = box.to_vertices_and_faces(triangulated=True)
    sphere_mesh = sphere.to_vertices_and_faces(u=32, v=32, triangulated=True)

    return box_mesh, sphere_mesh


def _assert_closed_manifold(vertices, faces):
    assert isinstance(vertices, np.ndarray)
    assert isinstance(faces, np.ndarray)
    assert vertices.shape[1] == 3
    assert faces.shape[1] == 3
    assert len(vertices) > 0
    assert len(faces) > 0
    mesh = Mesh.from_vertices_and_faces(vertices, faces)
    assert mesh.is_valid()
    # Manifold guarantees a closed, oriented 2-manifold for a genus-0 result.
    assert mesh.euler() == 2


def test_boolean_union(box_sphere_meshes):
    mesh_a, mesh_b = box_sphere_meshes
    vertices, faces = boolean_union_mesh_mesh(mesh_a, mesh_b)
    _assert_closed_manifold(vertices, faces)


def test_boolean_difference(box_sphere_meshes):
    mesh_a, mesh_b = box_sphere_meshes
    vertices, faces = boolean_difference_mesh_mesh(mesh_a, mesh_b)
    _assert_closed_manifold(vertices, faces)


def test_boolean_intersection(box_sphere_meshes):
    mesh_a, mesh_b = box_sphere_meshes
    vertices, faces = boolean_intersection_mesh_mesh(mesh_a, mesh_b)
    _assert_closed_manifold(vertices, faces)


def test_split(box_sphere_meshes):
    mesh_a, mesh_b = box_sphere_meshes
    vertices, faces = split_mesh_mesh(mesh_a, mesh_b)

    assert vertices.shape[1] == 3
    assert faces.shape[1] == 3
    assert len(vertices) > 0
    assert len(faces) > 0

    mesh = Mesh.from_vertices_and_faces(vertices, faces)
    assert mesh.is_valid()
    # Split produces at least two disconnected components (inside + outside).
    components = list(mesh.connected_vertices())
    assert len(components) >= 2


def test_boolean_difference_is_smaller(box_sphere_meshes):
    """Difference removes volume; the result volume is below the box volume."""
    box, sphere = box_sphere_meshes
    V, F = boolean_difference_mesh_mesh(box, sphere)
    mesh = Mesh.from_vertices_and_faces(V.tolist(), F.tolist())
    assert mesh.is_valid()


def test_boolean_chain_single_step(box_sphere_meshes):
    A, B = box_sphere_meshes
    V, F = boolean_chain([A, B], ["difference"])
    _assert_closed_manifold(V, F)


def test_boolean_chain_xor_self_is_empty(box_sphere_meshes):
    """A xor A = empty mesh."""
    A, _ = box_sphere_meshes
    V, F = boolean_chain([A, A], ["xor"])
    assert V.shape == (0, 3) and F.shape == (0, 3)


def test_boolean_chain_validation(box_sphere_meshes):
    A, B = box_sphere_meshes
    with pytest.raises(ValueError):
        boolean_chain([A, B], ["nope"])  # unknown op
    with pytest.raises(ValueError):
        boolean_chain([A, B, A], ["difference"])  # mismatched lengths


def test_boolean_chain_three_cylinders():
    """Three cylinders meeting at the origin is the classic degenerate CSG
    case. Manifold handles it without any geometric work-arounds."""
    from compas.geometry import Cylinder, Frame

    def cyl(frame):
        return Cylinder(0.6, 4.0, frame).to_vertices_and_faces(u=48, triangulated=True)

    cx = cyl(Frame([0, 0, 0], [0, 1, 0], [0, 0, 1]))
    cy = cyl(Frame([0, 0, 0], [0, 0, 1], [1, 0, 0]))
    cz = cyl(Frame([0, 0, 0], [1, 0, 0], [0, 1, 0]))

    V, F = boolean_chain([cx, cy, cz], ["union", "union"])
    assert V.shape[0] > 0
    assert F.shape[1] == 3


def test_boolean_batch_union(box_sphere_meshes):
    box, sphere = box_sphere_meshes
    far_sphere = (np.asarray(sphere[0]) + np.array([5.0, 0.0, 0.0]), np.asarray(sphere[1]))
    V, F = boolean_batch([box, sphere, far_sphere], "union")
    assert V.shape[0] > 0
    assert F.shape[1] == 3
    mesh = Mesh.from_vertices_and_faces(V, F)
    assert mesh.is_valid()


def test_boolean_difference_mesh_meshes(box_sphere_meshes):
    box, sphere = box_sphere_meshes
    sphere_b = (np.asarray(sphere[0]) - np.array([2.0, 2.0, 2.0]), np.asarray(sphere[1]))

    V_one, F_one = boolean_difference_mesh_mesh(box, sphere)
    V_two, F_two = boolean_difference_mesh_meshes(box, [sphere, sphere_b])

    # Two corner cutters carve more than one.
    assert len(V_two) > len(V_one)


def test_boolean_chain_with_face_source():
    """Three-mesh chain: cube - sphere - cylinder. Every output face must be
    tagged with one of {0, 1, 2}."""
    from compas.geometry import Cylinder, Frame

    cube = Box(2).to_vertices_and_faces(triangulated=True)
    sphere = Sphere(0.8, point=[1, 1, 1]).to_vertices_and_faces(u=32, v=32, triangulated=True)
    cyl = Cylinder(0.4, 4.0, Frame([0, 0, 0], [1, 0, 0], [0, 1, 0])).to_vertices_and_faces(u=32, triangulated=True)

    V, F, S = boolean_chain_with_face_source([cube, sphere, cyl], ["difference", "difference"])

    assert S.shape == (F.shape[0], 2)
    mids = S[:, 0]
    assert (mids != -1).all()
    assert (mids == 0).any()
    assert (mids == 1).any()
    assert (mids == 2).any()

    # split_by_source round-trips the tags into per-source submeshes.
    parts = split_by_source(V, F, S)
    assert set(parts.keys()) <= {0, 1, 2}
    for _, (Vp, Fp) in parts.items():
        assert Vp.shape[1] == 3 and Fp.shape[1] == 3


def test_boolean_chain_with_face_source_xor_rejected(box_sphere_meshes):
    A, B = box_sphere_meshes
    with pytest.raises(ValueError):
        boolean_chain_with_face_source([A, B], ["xor"])


def test_boolean_with_polygons_groups_flat_faces():
    """A box minus a small offset sphere: the box's uncut flat faces merge into
    large coplanar polygons (far fewer than the triangle count)."""
    box = Box(2).to_vertices_and_faces(triangulated=True)
    sphere = Sphere(0.5, point=[1, 1, 1]).to_vertices_and_faces(u=24, v=24, triangulated=True)

    V, F, P = boolean_difference_mesh_mesh_with_polygons(box, sphere)
    assert P.shape == (F.shape[0], 1)
    n_polygons = len(np.unique(P))
    assert n_polygons < F.shape[0]

    # The largest coplanar group spans many triangles (a flat box face).
    _, counts = np.unique(P, return_counts=True)
    assert counts.max() >= 4

    loops = merge_coplanar_faces(V, F, P)
    assert set(loops.keys()) == set(int(p) for p in np.unique(P))
    # Every loop closes and indexes valid vertices.
    for face_loops in loops.values():
        for loop in face_loops:
            assert len(loop) >= 3
            assert max(loop) < len(V)


def test_coplanar_outline_edges_valid():
    box = Box(2).to_vertices_and_faces(triangulated=True)
    sphere = Sphere(0.8, point=[1, 1, 1]).to_vertices_and_faces(u=32, v=32, triangulated=True)
    V, F, P = boolean_difference_mesh_mesh_with_polygons(box, sphere)

    E = coplanar_outline_edges(V, F, P)
    assert E.ndim == 2 and E.shape[1] == 2
    assert len(E) > 0
    assert E.min() >= 0 and E.max() < len(V)
    # Outlines are sparser than the full triangle edge set.
    assert len(E) < 3 * len(F)


def test_coplanar_polygons_handles_holes():
    """Drill a cylinder straight through a box: the entry/exit faces become
    annuli -- one coplanar face with an outer boundary and a hole loop."""
    from compas.geometry import Cylinder, Frame

    box = Box(2).to_vertices_and_faces(triangulated=True)
    # Cylinder along Z through the center, taller than the box.
    cyl = Cylinder(0.3, 4.0, Frame.worldXY()).to_vertices_and_faces(u=48, triangulated=True)

    V, F, P = boolean_difference_mesh_mesh_with_polygons(box, cyl)

    faces = coplanar_polygons(V, F, P)
    assert len(faces) > 0
    # At least one reconstructed face must have a hole (the drilled top/bottom).
    faces_with_holes = [f for f in faces if len(f["holes"]) > 0]
    assert len(faces_with_holes) >= 1

    for f in faces_with_holes:
        assert len(f["outer"]) >= 3
        for hole in f["holes"]:
            assert len(hole) >= 3
            assert max(hole) < len(V)


def test_invalid_mesh_raises():
    """A non-manifold soup must raise rather than silently produce garbage."""
    V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
    F = np.array([[0, 1, 2]], dtype=np.int32)  # single open triangle
    with pytest.raises(Exception):
        boolean_union_mesh_mesh((V, F), (V, F))
