# compas_manifold

[![build](https://github.com/petrasvestartas/compas_manifold/actions/workflows/build.yml/badge.svg)](https://github.com/petrasvestartas/compas_manifold/actions/workflows/build.yml)

Robust, **guaranteed-manifold** mesh boolean operations for
[COMPAS](https://compas.dev), powered by the
[Manifold](https://github.com/elalish/manifold) library and bound with
[nanobind](https://github.com/wjakob/nanobind).

Manifold uses its own robust geometric predicates and always returns a valid,
watertight, oriented 2-manifold — no exact kernel to opt into, no precision
crashes on degenerate input.

## Quickstart

Needs [uv](https://docs.astral.sh/uv/) and a C++17 compiler. Manifold is fetched
and compiled automatically — no extra setup.

```bash
git clone https://github.com/petrasvestartas/compas_manifold.git
cd compas_manifold

uv venv --python 3.12
source .venv/Scripts/activate    # Git Bash on Windows  (Linux/macOS: source .venv/bin/activate)

uv pip install nanobind "scikit-build-core[pyproject]" cmake ninja
uv pip install --no-build-isolation -ve ".[dev]"

python docs/examples/example_booleans.py
```

Run the tests with `pytest tests`. More options in
[docs/installation.md](docs/installation.md).

## Usage

```python
from compas.geometry import Box, Sphere, Polyhedron
from compas_manifold.booleans import (
    boolean_union_mesh_mesh,
    boolean_difference_mesh_mesh,
    boolean_intersection_mesh_mesh,
    split_mesh_mesh,
)

A = Box(2).to_vertices_and_faces(triangulated=True)
B = Sphere(1.0, point=[1, 1, 1]).to_vertices_and_faces(u=32, v=32, triangulated=True)

V, F = boolean_difference_mesh_mesh(A, B)
shape = Polyhedron(V.tolist(), F.tolist())
```

### Whole-pipeline booleans (evaluated in C++)

Keep every intermediate mesh inside C++ and only return the final result:

```python
from compas_manifold.booleans import boolean_chain

# rounded, drilled cube: cube ∩ sphere − cyl_x − cyl_y − cyl_z
V, F = boolean_chain(
    [cube, sphere, cyl_x, cyl_y, cyl_z],
    ["intersection", "difference", "difference", "difference"],
)
```

| Function | Description |
| --- | --- |
| `boolean_union_mesh_mesh(A, B)` | Union of two meshes |
| `boolean_difference_mesh_mesh(A, B)` | Difference `A - B` |
| `boolean_intersection_mesh_mesh(A, B)` | Intersection of two meshes |
| `split_mesh_mesh(A, B)` | Split `A` with `B` |
| `boolean_*_mesh_mesh_with_polygons(A, B)` | `(V, F, P)` with coplanar-face ids (merge triangles into n-gons) |
| `merge_coplanar_faces` / `coplanar_polygons` / `coplanar_outline_edges` | recover polygonal faces (with holes) & clean outlines |
| `boolean_chain(meshes, operations)` | Left-folded chain of ops, in C++ |
| `boolean_batch(meshes, operation)` | Single op over many meshes (`BatchBoolean`) |
| `boolean_chain_with_face_source(meshes, operations)` | Chain + per-face source tracking |
| `boolean_difference_mesh_meshes(A, Bs)` | Subtract many cutters from `A` in one batch |

## Documentation

- [Boolean operations](docs/examples/example_booleans.md)
- [Boolean chain](docs/examples/example_boolean_chain.md)
- [Face source tracking](docs/examples/example_boolean_face_source.md)
- [API reference](docs/api/compas_manifold.booleans.md)

## License

`compas_manifold` is released under the Apache License 2.0, matching the
[Manifold](https://github.com/elalish/manifold) library it wraps. See
[LICENSE](LICENSE).
