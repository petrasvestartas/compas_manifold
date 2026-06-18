from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas_viewer import Viewer

from compas_manifold.booleans import boolean_difference_mesh_mesh_with_polygons
from compas_manifold.booleans import coplanar_outline_edges
from compas_manifold.booleans import coplanar_polygons

# A box with a cylinder drilled straight through it.
box = Box(2).to_vertices_and_faces(triangulated=True)
cyl = Cylinder(0.3, 4.0, Frame.worldXY()).to_vertices_and_faces(u=64, triangulated=True)

V, F, P = boolean_difference_mesh_mesh_with_polygons(box, cyl)

# The raw (triangulated) result, for context.
tri_mesh = Mesh.from_vertices_and_faces(V.tolist(), F.tolist())

# Clean outline edges: feature edges between coplanar faces + hole rims.
outline = coplanar_outline_edges(V, F, P)
outline_lines = [Line(V[a].tolist(), V[b].tolist()) for a, b in outline]

# Polygonal faces with holes (outer loop + hole loops), e.g. the drilled faces.
faces = coplanar_polygons(V, F, P)
n_holes = sum(len(f["holes"]) for f in faces)
print(f"{F.shape[0]} triangles -> {len(faces)} polygonal faces, {n_holes} holes")

# =============================================================================
# Visualize: triangle mesh faded, clean polygon outlines on top.
# =============================================================================

viewer = Viewer()
viewer.scene.add(tri_mesh, opacity=0.5, show_lines=False, show_points=False)
for line in outline_lines:
    viewer.scene.add(line, lineswidth=3, show_points=False)
viewer.show()
