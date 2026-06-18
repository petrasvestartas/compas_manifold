# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Added

* Initial release of `compas_manifold`: a nanobind wrapper around the
  [Manifold](https://github.com/elalish/manifold) library (v3.5.1).
* Pairwise booleans registered as COMPAS pluggables:
  `boolean_union_mesh_mesh`, `boolean_difference_mesh_mesh`,
  `boolean_intersection_mesh_mesh`, `split_mesh_mesh`.
* Whole-pipeline booleans evaluated entirely in C++:
  `boolean_chain`, `boolean_batch`, `boolean_chain_with_face_source`,
  `boolean_difference_mesh_meshes`, plus the `split_by_source` helper.
* Coplanar-face (polygon) recovery from boolean results:
  `boolean_{union,difference,intersection}_mesh_mesh_with_polygons` return
  `(V, F, P)` with a coplanar-face id per triangle, plus `merge_coplanar_faces`,
  `coplanar_outline_edges`, and `coplanar_polygons` (with hole handling) to turn
  the triangle soup into polygonal n-gon faces and clean outlines.
* scikit-build-core + CMake superbuild that fetches and statically links
  Manifold and Eigen.
* GitHub Actions CI: build/test on Linux/macOS/Windows, cibuildwheel, sdist,
  and docs.

### Changed

### Removed
