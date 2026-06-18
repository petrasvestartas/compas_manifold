#include "booleans.h"

#include <algorithm>
#include <unordered_map>

using manifold::Manifold;
using manifold::MeshGL64;
using manifold::OpType;

// =============================================================================
// Internal helpers
// =============================================================================
namespace
{
    // Map an integer op code to a Manifold OpType. xor (3) is handled
    // separately by the callers because Manifold has no native xor.
    OpType op_from_code(int code)
    {
        switch (code)
        {
        case 0:
            return OpType::Add;       // union
        case 1:
            return OpType::Subtract;  // difference
        case 2:
            return OpType::Intersect; // intersection
        default:
            throw std::invalid_argument(
                "operation must be 0 (union), 1 (difference), 2 (intersection), "
                "or 3 (xor)");
        }
    }

    // Symmetric difference: (A - B) + (B - A).
    Manifold boolean_xor(const Manifold &a, const Manifold &b)
    {
        return (a - b) + (b - a);
    }

    Manifold apply_op(const Manifold &a, const Manifold &b, int code)
    {
        if (code == 3)
            return boolean_xor(a, b);
        return a.Boolean(b, op_from_code(code));
    }

    // Materialise a single mesh out of the flat (V, F) collection. Face
    // indices are mesh-local, so the sub-block can be ingested directly.
    Manifold slice_manifold(
        const compas::RowMatrixXd &V_all,
        const compas::RowMatrixXi &F_all,
        int v_off, int v_cnt,
        int f_off, int f_cnt)
    {
        compas::RowMatrixXd V = V_all.block(v_off, 0, v_cnt, 3);
        compas::RowMatrixXi F = F_all.block(f_off, 0, f_cnt, 3);
        return compas::mesh_from_vertices_and_faces(V, F);
    }

    void check_inputs(
        const compas::RowMatrixXd &V_all, const compas::RowMatrixXi &F_all,
        const std::vector<int> &vc, const std::vector<int> &fc,
        std::size_t n_ops_plus_one)
    {
        if (vc.size() != fc.size())
            throw std::invalid_argument("mesh_v_counts and mesh_f_counts must have the same length");
        if (vc.empty())
            throw std::invalid_argument("at least one mesh is required");
        if (n_ops_plus_one != vc.size())
            throw std::invalid_argument("operations must have length number_of_meshes - 1");
        long long tv = 0, tf = 0;
        for (int c : vc)
            tv += c;
        for (int c : fc)
            tf += c;
        if (tv != V_all.rows() || tf != F_all.rows())
            throw std::invalid_argument("per-mesh counts do not sum to vertices/faces row counts");
    }
} // namespace

// =============================================================================
// Pairwise booleans
// =============================================================================
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_union(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    Manifold a = compas::mesh_from_vertices_and_faces(vertices_a, faces_a);
    Manifold b = compas::mesh_from_vertices_and_faces(vertices_b, faces_b);
    return compas::mesh_to_vertices_and_faces(a.Boolean(b, OpType::Add));
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_difference(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    Manifold a = compas::mesh_from_vertices_and_faces(vertices_a, faces_a);
    Manifold b = compas::mesh_from_vertices_and_faces(vertices_b, faces_b);
    return compas::mesh_to_vertices_and_faces(a.Boolean(b, OpType::Subtract));
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_intersection(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    Manifold a = compas::mesh_from_vertices_and_faces(vertices_a, faces_a);
    Manifold b = compas::mesh_from_vertices_and_faces(vertices_b, faces_b);
    return compas::mesh_to_vertices_and_faces(a.Boolean(b, OpType::Intersect));
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_split(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    Manifold a = compas::mesh_from_vertices_and_faces(vertices_a, faces_a);
    Manifold b = compas::mesh_from_vertices_and_faces(vertices_b, faces_b);

    // Split(cutter) -> (inside, outside). Concatenate the two halves as
    // disconnected components into a single (V, F) -- a boolean union would
    // re-merge them, so we offset the second half's indices instead. This
    // matches the compas_cgal split contract (one mesh, multiple components).
    std::pair<Manifold, Manifold> parts = a.Split(b);
    auto [V1, F1] = compas::mesh_to_vertices_and_faces(parts.first);
    auto [V2, F2] = compas::mesh_to_vertices_and_faces(parts.second);

    const Eigen::Index nv1 = V1.rows(), nv2 = V2.rows();
    const Eigen::Index nf1 = F1.rows(), nf2 = F2.rows();

    compas::RowMatrixXd V(nv1 + nv2, 3);
    if (nv1) V.topRows(nv1) = V1;
    if (nv2) V.bottomRows(nv2) = V2;

    compas::RowMatrixXi F(nf1 + nf2, 3);
    if (nf1) F.topRows(nf1) = F1;
    if (nf2) F.bottomRows(nf2) = F2.array() + static_cast<int>(nv1);

    return std::make_tuple(std::move(V), std::move(F));
}

// =============================================================================
// Pairwise booleans with coplanar-face (polygon) grouping
// =============================================================================
namespace
{
    std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
    boolean_with_polygons(
        Eigen::Ref<const compas::RowMatrixXd> VA,
        Eigen::Ref<const compas::RowMatrixXi> FA,
        Eigen::Ref<const compas::RowMatrixXd> VB,
        Eigen::Ref<const compas::RowMatrixXi> FB,
        OpType op)
    {
        Manifold a = compas::mesh_from_vertices_and_faces(VA, FA);
        Manifold b = compas::mesh_from_vertices_and_faces(VB, FB);
        MeshGL64 mesh = a.Boolean(b, op).GetMeshGL64();

        auto [V, F] = compas::meshgl64_to_vertices_and_faces(mesh);
        compas::RowMatrixXi P = compas::polygon_ids(mesh);
        return {std::move(V), std::move(F), std::move(P)};
    }
} // namespace

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_union_with_polygons(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    return boolean_with_polygons(vertices_a, faces_a, vertices_b, faces_b, OpType::Add);
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_difference_with_polygons(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    return boolean_with_polygons(vertices_a, faces_a, vertices_b, faces_b, OpType::Subtract);
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_intersection_with_polygons(
    Eigen::Ref<const compas::RowMatrixXd> vertices_a,
    Eigen::Ref<const compas::RowMatrixXi> faces_a,
    Eigen::Ref<const compas::RowMatrixXd> vertices_b,
    Eigen::Ref<const compas::RowMatrixXi> faces_b)
{
    return boolean_with_polygons(vertices_a, faces_a, vertices_b, faces_b, OpType::Intersect);
}

// =============================================================================
// Chained / batched booleans
// =============================================================================
std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_chain(
    Eigen::Ref<const compas::RowMatrixXd> vertices,
    Eigen::Ref<const compas::RowMatrixXi> faces,
    const std::vector<int> &mesh_v_counts,
    const std::vector<int> &mesh_f_counts,
    const std::vector<int> &operations)
{
    compas::RowMatrixXd V_all = vertices;
    compas::RowMatrixXi F_all = faces;
    check_inputs(V_all, F_all, mesh_v_counts, mesh_f_counts, operations.size() + 1);

    int v_off = 0, f_off = 0;
    Manifold m = slice_manifold(V_all, F_all, v_off, mesh_v_counts[0], f_off, mesh_f_counts[0]);
    v_off += mesh_v_counts[0];
    f_off += mesh_f_counts[0];

    for (std::size_t i = 0; i < operations.size(); ++i)
    {
        Manifold b = slice_manifold(V_all, F_all,
                                    v_off, mesh_v_counts[i + 1],
                                    f_off, mesh_f_counts[i + 1]);
        v_off += mesh_v_counts[i + 1];
        f_off += mesh_f_counts[i + 1];

        m = apply_op(m, b, operations[i]);
    }

    return compas::mesh_to_vertices_and_faces(m);
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi>
manifold_boolean_batch(
    Eigen::Ref<const compas::RowMatrixXd> vertices,
    Eigen::Ref<const compas::RowMatrixXi> faces,
    const std::vector<int> &mesh_v_counts,
    const std::vector<int> &mesh_f_counts,
    int operation)
{
    compas::RowMatrixXd V_all = vertices;
    compas::RowMatrixXi F_all = faces;
    // For a batch there is no per-pair operations list; require >= 1 mesh and
    // matching counts only.
    check_inputs(V_all, F_all, mesh_v_counts, mesh_f_counts, mesh_v_counts.size());

    std::vector<Manifold> meshes;
    meshes.reserve(mesh_v_counts.size());

    int v_off = 0, f_off = 0;
    for (std::size_t i = 0; i < mesh_v_counts.size(); ++i)
    {
        meshes.push_back(slice_manifold(V_all, F_all,
                                        v_off, mesh_v_counts[i],
                                        f_off, mesh_f_counts[i]));
        v_off += mesh_v_counts[i];
        f_off += mesh_f_counts[i];
    }

    Manifold result = Manifold::BatchBoolean(meshes, op_from_code(operation));
    return compas::mesh_to_vertices_and_faces(result);
}

std::tuple<compas::RowMatrixXd, compas::RowMatrixXi, compas::RowMatrixXi>
manifold_boolean_chain_with_face_source(
    Eigen::Ref<const compas::RowMatrixXd> vertices,
    Eigen::Ref<const compas::RowMatrixXi> faces,
    const std::vector<int> &mesh_v_counts,
    const std::vector<int> &mesh_f_counts,
    const std::vector<int> &operations)
{
    compas::RowMatrixXd V_all = vertices;
    compas::RowMatrixXi F_all = faces;
    check_inputs(V_all, F_all, mesh_v_counts, mesh_f_counts, operations.size() + 1);

    for (int op : operations)
        if (op == 3)
            throw std::invalid_argument("xor (op code 3) is not supported by boolean_chain_with_face_source");

    // Tag every input mesh as a fresh "original" so Manifold tracks which
    // input each output triangle descends from via runOriginalID.
    std::unordered_map<int, int> id_to_index; // OriginalID -> position in `meshes`

    int v_off = 0, f_off = 0;
    Manifold m = slice_manifold(V_all, F_all, v_off, mesh_v_counts[0], f_off, mesh_f_counts[0]).AsOriginal();
    id_to_index[m.OriginalID()] = 0;
    v_off += mesh_v_counts[0];
    f_off += mesh_f_counts[0];

    for (std::size_t i = 0; i < operations.size(); ++i)
    {
        Manifold b = slice_manifold(V_all, F_all,
                                    v_off, mesh_v_counts[i + 1],
                                    f_off, mesh_f_counts[i + 1])
                         .AsOriginal();
        id_to_index[b.OriginalID()] = static_cast<int>(i + 1);
        v_off += mesh_v_counts[i + 1];
        f_off += mesh_f_counts[i + 1];

        m = apply_op(m, b, operations[i]);
    }

    MeshGL64 mesh = m.GetMeshGL64();
    auto [V_out, F_out] = compas::mesh_to_vertices_and_faces(m);

    const std::size_t nf = static_cast<std::size_t>(mesh.NumTri());
    compas::RowMatrixXi S(static_cast<Eigen::Index>(nf), 2);

    for (std::size_t t = 0; t < nf; ++t)
    {
        const std::uint64_t tri_offset = static_cast<std::uint64_t>(3 * t);

        // Find the run this triangle belongs to: largest r with
        // runIndex[r] <= 3*t. runIndex is sorted ascending and is one longer
        // than runOriginalID.
        int mesh_id = -1;
        if (!mesh.runOriginalID.empty())
        {
            std::size_t run = 0;
            if (!mesh.runIndex.empty())
            {
                auto it = std::upper_bound(mesh.runIndex.begin(), mesh.runIndex.end(), tri_offset);
                run = static_cast<std::size_t>(it - mesh.runIndex.begin());
                if (run > 0)
                    --run;
            }
            if (run >= mesh.runOriginalID.size())
                run = mesh.runOriginalID.size() - 1;

            const int orig = static_cast<int>(mesh.runOriginalID[run]);
            auto found = id_to_index.find(orig);
            mesh_id = (found != id_to_index.end()) ? found->second : -1;
        }

        const int face_id = (t < mesh.faceID.size())
                                ? static_cast<int>(mesh.faceID[t])
                                : -1;

        S(static_cast<Eigen::Index>(t), 0) = mesh_id;
        S(static_cast<Eigen::Index>(t), 1) = face_id;
    }

    return {std::move(V_out), std::move(F_out), std::move(S)};
}

// =============================================================================
// nanobind module
// =============================================================================
NB_MODULE(_booleans, m)
{
    m.def(
        "boolean_union",
        &manifold_boolean_union,
        "Boolean union of two triangle meshes given as (V, F) arrays.",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "boolean_difference",
        &manifold_boolean_difference,
        "Boolean difference (A - B) of two triangle meshes given as (V, F) arrays.",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "boolean_intersection",
        &manifold_boolean_intersection,
        "Boolean intersection of two triangle meshes given as (V, F) arrays.",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "split",
        &manifold_split,
        "Split mesh A with mesh B, returning both halves as one (V, F).",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "boolean_union_with_polygons",
        &manifold_boolean_union_with_polygons,
        "Boolean union returning (V, F, P) where P[i] is the coplanar-face "
        "(polygon) id of output triangle i. Triangles sharing an id form one "
        "planar n-gon face; group on P to recover polygonal faces / outlines.",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "boolean_difference_with_polygons",
        &manifold_boolean_difference_with_polygons,
        "Boolean difference returning (V, F, P) of coplanar-face ids. See "
        "boolean_union_with_polygons.",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "boolean_intersection_with_polygons",
        &manifold_boolean_intersection_with_polygons,
        "Boolean intersection returning (V, F, P) of coplanar-face ids. See "
        "boolean_union_with_polygons.",
        "VA"_a, "FA"_a, "VB"_a, "FB"_a);

    m.def(
        "boolean_chain",
        &manifold_boolean_chain,
        "Run a left-folded chain of boolean operations entirely in C++. The "
        "whole mesh collection is sent as flat (vertices, faces) arrays plus "
        "per-mesh row counts. operations is a list of int codes "
        "(0=union, 1=difference, 2=intersection, 3=xor) of length "
        "number_of_meshes - 1.",
        "vertices"_a, "faces"_a, "mesh_v_counts"_a, "mesh_f_counts"_a, "operations"_a);

    m.def(
        "boolean_batch",
        &manifold_boolean_batch,
        "Apply a single boolean operation (0=union, 1=difference, "
        "2=intersection) across many meshes using Manifold::BatchBoolean, "
        "which evaluates the whole CSG batch at once.",
        "vertices"_a, "faces"_a, "mesh_v_counts"_a, "mesh_f_counts"_a, "operation"_a);

    m.def(
        "boolean_chain_with_face_source",
        &manifold_boolean_chain_with_face_source,
        "Like boolean_chain but also returns S (Mx2 int): for each output face, "
        "[mesh_id, face_id] of the input face that produced it, tracked through "
        "Manifold's native OriginalID / run relations. xor is not supported.",
        "vertices"_a, "faces"_a, "mesh_v_counts"_a, "mesh_f_counts"_a, "operations"_a);
}
