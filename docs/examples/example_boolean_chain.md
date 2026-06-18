# Boolean Chain

![Boolean Chain](../assets/images/example_boolean_chain.png)

`boolean_chain` runs a left-folded sequence of boolean operations **entirely in
C++**. The full set of input meshes is marshalled to C++ in a single call;
intermediate meshes never come back to Python; only the final `(V, F)` is
returned.

This example carves a rounded, drilled cube:

```
result = cube ∩ sphere − cyl_x − cyl_y − cyl_z
```

The three orthogonal cylinders all meet at the origin — a classically
degenerate CSG configuration that Manifold handles without any work-arounds.

Run it (requires `compas_viewer`):

```bash
python docs/examples/example_boolean_chain.py
```

```python
--8<-- "docs/examples/example_boolean_chain.py"
```

## Batch booleans

When you apply the *same* operation across many meshes, `boolean_batch` uses
Manifold's `BatchBoolean`, which evaluates the whole CSG batch at once and is
faster than folding pairwise:

```python
from compas_manifold.booleans import boolean_batch

V, F = boolean_batch([mesh_a, mesh_b, mesh_c], "union")
```
