# compas_manifold.booleans

Robust, guaranteed-manifold mesh boolean operations, backed by the
[Manifold](https://github.com/elalish/manifold) library.

## Pairwise operations

Each takes two meshes `A` and `B`, given as `(vertices, faces)` tuples, and
returns `(V, F)` numpy arrays.

| Function | Result |
| --- | --- |
| `boolean_union_mesh_mesh(A, B)` | `A ∪ B` |
| `boolean_difference_mesh_mesh(A, B)` | `A − B` |
| `boolean_intersection_mesh_mesh(A, B)` | `A ∩ B` |
| `split_mesh_mesh(A, B)` | `A` split by `B` (inside + outside as one mesh) |

These are registered as COMPAS `booleans` pluggables
(`boolean_union_mesh_mesh`, `boolean_difference_mesh_mesh`,
`boolean_intersection_mesh_mesh`, `split_mesh_mesh`), so they can serve as a
COMPAS boolean backend.

```python
from compas.geometry import Box, Sphere, Polyhedron
from compas_manifold.booleans import boolean_difference_mesh_mesh

A = Box(2).to_vertices_and_faces(triangulated=True)
B = Sphere(1.0, point=[1, 1, 1]).to_vertices_and_faces(u=32, v=32, triangulated=True)

V, F = boolean_difference_mesh_mesh(A, B)
shape = Polyhedron(V.tolist(), F.tolist())
```

## Polygonal faces & clean outlines

Manifold returns triangles, but tags each one with a coplanar-face id so you can
merge the triangle soup back into n-gon faces.

| Function | Result |
| --- | --- |
| `boolean_union_mesh_mesh_with_polygons(A, B)` | `(V, F, P)`, `P[i]` = coplanar-face id of triangle `i` |
| `boolean_difference_mesh_mesh_with_polygons(A, B)` | as above, for `A − B` |
| `boolean_intersection_mesh_mesh_with_polygons(A, B)` | as above, for `A ∩ B` |
| `merge_coplanar_faces(V, F, P)` | `dict[id → list of boundary loops]` |
| `coplanar_outline_edges(V, F, P)` | `Ex2` clean feature edges (hole rims included) |
| `coplanar_polygons(V, F, P)` | list of `{normal, outer, holes}` faces |

```python
from compas_manifold.booleans import (
    boolean_difference_mesh_mesh_with_polygons,
    coplanar_outline_edges,
    coplanar_polygons,
)

V, F, P = boolean_difference_mesh_mesh_with_polygons(box, cylinder)
E = coplanar_outline_edges(V, F, P)   # clean outlines for a wireframe
faces = coplanar_polygons(V, F, P)    # n-gon faces, holes nested under each outer loop
```

### Holes

A face a solid passed through is an annulus (outer loop + hole loop), both
sharing one coplanar id. `merge_coplanar_faces` returns all loops; outer
boundaries and holes are distinguished by orientation (signed area vs. the face
normal). `coplanar_polygons` classifies and nests them for you, returning
`{"normal", "outer", "holes"}` per face — the right "polygon-with-holes" form,
since a plain mesh can't store a holed face. See the
[Polygonal faces example](../examples/example_boolean_polygons.md).

## Whole-pipeline operations (evaluated in C++)

### `boolean_chain(meshes, operations)`

Left-folds a sequence of operations
(`result = meshes[0]; result = result OP_i meshes[i+1]`). The whole mesh
collection is sent to C++ in one call; intermediate meshes never return to
Python. `operations` is a list of `"union" | "difference" | "intersection" |
"xor"`, of length `len(meshes) - 1`.

```python
from compas_manifold.booleans import boolean_chain

V, F = boolean_chain(
    [cube, sphere, cyl_x, cyl_y, cyl_z],
    ["intersection", "difference", "difference", "difference"],
)
```

### `boolean_batch(meshes, operation)`

Applies a single operation (`"union" | "difference" | "intersection"`) across
many meshes via Manifold's `BatchBoolean`, which evaluates the whole CSG batch
at once.

### `boolean_chain_with_face_source(meshes, operations)`

Like `boolean_chain` but also returns `S` (`Mx2` int): for each output face,
`[mesh_id, face_id]` of the input face that produced it. `"xor"` is not
supported. Use `split_by_source(V, F, S)` to separate the result into one
submesh per source.

### `boolean_difference_mesh_meshes(A, Bs)`

Subtract many cutters from `A` in a single batched operation.

## Notes on robustness

Manifold always returns a valid, watertight, oriented 2-manifold and uses its
own robust geometric predicates, so there is no "exact kernel" to opt into and
no precision crashes on degenerate input. Invalid (non-manifold) **input** is
rejected with an exception.
