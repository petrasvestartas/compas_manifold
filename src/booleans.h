#pragma once

#include "compas.h"

// =============================================================================
// Manifold mesh-boolean wrapper, mirroring the compas_cgal booleans API.
//
// Manifold guarantees a valid, watertight, 2-manifold result for every
// operation and uses its own robust geometric predicates, so it does not
// suffer from CGAL's corefinement precision crashes. The "chain" / "batch"
// entry points are therefore offered for performance and ergonomics (keep
// every intermediate mesh in C++; never round-trip through Python) rather
// than as a robustness work-around -- but they serve the same role as the
// compas_cgal exact-kernel chain.
// =============================================================================

/**
 * Boolean union (A + B) of two triangle meshes.
 *
 * @param vertices_a Vertices of mesh A as Nx3 row-major float64 matrix.
 * @param faces_a    Faces of mesh A as Mx3 row-major int32 matrix.
 * @param vertices_b Vertices of mesh B as Px3 row-major float64 matrix.
 * @param faces_b    Faces of mesh B as Qx3 row-major int32 matrix.
 * @return (V, F) of the resulting manifold mesh.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_union(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Boolean difference (A - B) of two triangle meshes. See
 * manifold_boolean_union for the argument contract.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_difference(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Boolean intersection (A ^ B) of two triangle meshes. See
 * manifold_boolean_union for the argument contract.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_intersection(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Split mesh A with mesh B. Returns a single (V, F) holding both the part of
 * A inside B and the part of A outside B as disconnected components (the two
 * halves of Manifold::Split, concatenated).
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_split(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Run a left-folded chain of boolean operations entirely in C++:
 *     result = mesh_0
 *     for i in range(len(operations)):
 *         result = result  op[i]  mesh_{i+1}
 *
 * Marshalling matches the compas_cgal chain: the whole mesh collection is
 * sent in a SINGLE call as flat (vertices, faces) arrays. Mesh i occupies
 * rows [v_offset_i, v_offset_i + mesh_v_counts[i]) of vertices and
 * [f_offset_i, f_offset_i + mesh_f_counts[i]) of faces. Face indices are
 * mesh-local. Only the final (V, F) is returned; intermediate manifolds
 * never leave C++.
 *
 * Operation codes (length = number of meshes - 1):
 *     0 = union, 1 = difference, 2 = intersection, 3 = xor (symmetric diff).
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_chain(
    Eigen::Ref<const compas::RowMatrixXd> vertices,
    Eigen::Ref<const compas::RowMatrixXi> faces,
    const std::vector<int> &mesh_v_counts,
    const std::vector<int> &mesh_f_counts,
    const std::vector<int> &operations);

/**
 * Apply a single boolean operation across an arbitrary number of meshes using
 * Manifold::BatchBoolean, which evaluates the whole CSG batch at once and is
 * considerably faster than folding pairwise. Same flat marshalling as
 * manifold_boolean_chain.
 *
 * operation: 0 = union (Add), 1 = difference (first minus the rest),
 *            2 = intersection.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_batch(
    Eigen::Ref<const compas::RowMatrixXd> vertices,
    Eigen::Ref<const compas::RowMatrixXi> faces,
    const std::vector<int> &mesh_v_counts,
    const std::vector<int> &mesh_f_counts,
    int operation);

/**
 * Boolean union with coplanar-face grouping. Returns (V, F, P) where P is an
 * Mx1 int matrix tagging each output triangle with a polygon id: triangles
 * that are coplanar and belong to the same planar face share an id. Grouping
 * on P reconstructs polygonal (n-gon) faces and clean outlines from the
 * triangle soup. See manifold_boolean_union for the argument contract.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_union_with_polygons(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Boolean difference (A - B) with coplanar-face grouping. See
 * manifold_boolean_union_with_polygons for the (V, F, P) contract.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_difference_with_polygons(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Boolean intersection with coplanar-face grouping. See
 * manifold_boolean_union_with_polygons for the (V, F, P) contract.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_intersection_with_polygons(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b);

/**
 * Boolean chain that also reports, for every output triangle, which input
 * mesh and which input face it descended from. Returns (V, F, S) where
 * S[i] = [mesh_id, face_id]. Tracking uses Manifold's native mesh-relation
 * machinery (OriginalID + the output run / faceID arrays), the idiomatic
 * counterpart of the compas_cgal corefinement face-source visitor.
 *
 * xor (op code 3) is not supported here.
 */
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_chain_with_face_source(
    Eigen::Ref<const compas::RowMatrixXd> vertices,
    Eigen::Ref<const compas::RowMatrixXi> faces,
    const std::vector<int> &mesh_v_counts,
    const std::vector<int> &mesh_f_counts,
    const std::vector<int> &operations);
