from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Polyhedron
from compas.geometry import Sphere
from compas_viewer import Viewer

from compas_manifold.booleans import boolean_chain


def cyl(axis, r=0.6):
    if axis == "x":
        frame = Frame([0, 0, 0], [0, 1, 0], [0, 0, 1])
    elif axis == "y":
        frame = Frame([0, 0, 0], [0, 0, 1], [1, 0, 0])
    else:
        frame = Frame([0, 0, 0], [1, 0, 0], [0, 1, 0])
    return Cylinder(r, 4.0, frame).to_vertices_and_faces(u=48, triangulated=True)


cube = Box(2).to_vertices_and_faces(triangulated=True)
sphere = Sphere(1.3, point=[0, 0, 0]).to_vertices_and_faces(u=64, v=64, triangulated=True)

V, F = boolean_chain(
    [cube, sphere, cyl("x"), cyl("y"), cyl("z")],
    ["intersection", "difference", "difference", "difference"],
)

shape = Polyhedron(V.tolist(), F.tolist()).to_mesh()

# =============================================================================
# Visualize
# =============================================================================

viewer = Viewer()
viewer.scene.add(shape, lineswidth=1, show_points=False)
viewer.show()
