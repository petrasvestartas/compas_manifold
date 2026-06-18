#pragma once

// =============================================================================
// Shared glue between COMPAS (numpy V, F arrays) and the Manifold library.
//
// COMPAS represents a triangle mesh as a pair of arrays:
//   V : (N, 3) float64 row-major  -- vertex coordinates
//   F : (M, 3) int32   row-major  -- triangle vertex indices
//
// Manifold's I/O struct is MeshGL64 (double precision positions, uint64
// indices), which is a loss-less match for COMPAS double-precision meshes.
// These helpers convert in both directions and are the only place that
// touches the Manifold ingest/egress API, so the individual binding files
// stay small.
// =============================================================================

#include <nanobind/nanobind.h>
#include <nanobind/eigen/dense.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>

#include <Eigen/Core>
#include <Eigen/Dense>

#include <algorithm>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#include <manifold/manifold.h>

namespace nb = nanobind;
using namespace nb::literals; // enables the "name"_a argument-annotation syntax

namespace compas
{
    using RowMatrixXd = Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    using RowMatrixXi = Eigen::Matrix<int, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;

    /**
     * @brief Build a manifold::Manifold from row-major (V, F) arrays.
     *
     * The vertices and triangles are copied into a MeshGL64 and ingested by
     * Manifold, which recovers the topology directly from the shared vertex
     * indices (no merge vectors needed for an index-shared closed mesh).
     *
     * @throws std::runtime_error if the input is not an oriented 2-manifold.
     */
    inline manifold::Manifold mesh_from_vertices_and_faces(
        const RowMatrixXd &V,
        const RowMatrixXi &F)
    {
        manifold::MeshGL64 mesh;
        mesh.numProp = 3;

        const std::size_t nv = static_cast<std::size_t>(V.rows());
        const std::size_t nf = static_cast<std::size_t>(F.rows());

        mesh.vertProperties.resize(nv * 3);
        for (std::size_t i = 0; i < nv; ++i)
        {
            mesh.vertProperties[3 * i + 0] = V(i, 0);
            mesh.vertProperties[3 * i + 1] = V(i, 1);
            mesh.vertProperties[3 * i + 2] = V(i, 2);
        }

        mesh.triVerts.resize(nf * 3);
        for (std::size_t i = 0; i < nf; ++i)
        {
            mesh.triVerts[3 * i + 0] = static_cast<uint64_t>(F(i, 0));
            mesh.triVerts[3 * i + 1] = static_cast<uint64_t>(F(i, 1));
            mesh.triVerts[3 * i + 2] = static_cast<uint64_t>(F(i, 2));
        }

        manifold::Manifold m(mesh);
        if (m.Status() != manifold::Manifold::Error::NoError)
        {
            throw std::runtime_error(
                "compas_manifold: input mesh is not a valid oriented 2-manifold "
                "(Manifold error code " +
                std::to_string(static_cast<int>(m.Status())) + ").");
        }
        return m;
    }

    /**
     * @brief Convert a MeshGL64 to row-major (V, F) arrays.
     *
     * Only the first three property channels (the x, y, z position) are read,
     * so meshes that carry extra vertex properties degrade gracefully to a
     * plain geometry mesh.
     */
    inline std::tuple<RowMatrixXd, RowMatrixXi>
    meshgl64_to_vertices_and_faces(const manifold::MeshGL64 &mesh)
    {
        const std::size_t nv = static_cast<std::size_t>(mesh.NumVert());
        const std::size_t nf = static_cast<std::size_t>(mesh.NumTri());

        RowMatrixXd V(nv, 3);
        RowMatrixXi F(nf, 3);

        for (std::size_t v = 0; v < nv; ++v)
        {
            auto p = mesh.GetVertPos(v);
            V(v, 0) = p[0];
            V(v, 1) = p[1];
            V(v, 2) = p[2];
        }

        for (std::size_t t = 0; t < nf; ++t)
        {
            auto tv = mesh.GetTriVerts(t);
            F(t, 0) = static_cast<int>(tv[0]);
            F(t, 1) = static_cast<int>(tv[1]);
            F(t, 2) = static_cast<int>(tv[2]);
        }

        return std::make_tuple(std::move(V), std::move(F));
    }

    /**
     * @brief Convert a manifold::Manifold back to row-major (V, F) arrays.
     */
    inline std::tuple<RowMatrixXd, RowMatrixXi>
    mesh_to_vertices_and_faces(const manifold::Manifold &m)
    {
        return meshgl64_to_vertices_and_faces(m.GetMeshGL64());
    }

    /**
     * @brief Per-triangle coplanar-face id for a boolean result.
     *
     * Manifold tags every output triangle with a faceID; triangles that are
     * coplanar and belong to the same original planar face share it (within a
     * triangle run). We fold (run, faceID) into a single dense polygon id so
     * the Python side can group triangles into n-gon faces and extract clean
     * outlines simply by grouping on one integer.
     *
     * @return Mx1 int matrix: P(i) is the polygon id of output triangle i.
     */
    inline RowMatrixXi polygon_ids(const manifold::MeshGL64 &mesh)
    {
        const std::size_t nf = static_cast<std::size_t>(mesh.NumTri());
        RowMatrixXi P(static_cast<Eigen::Index>(nf), 1);

        std::map<std::pair<long long, long long>, int> key_to_pid;

        for (std::size_t t = 0; t < nf; ++t)
        {
            const std::uint64_t tri_offset = static_cast<std::uint64_t>(3 * t);

            // Which run does this triangle belong to? runIndex is sorted
            // ascending and one longer than runOriginalID.
            long long run = 0;
            if (!mesh.runIndex.empty())
            {
                auto it = std::upper_bound(mesh.runIndex.begin(), mesh.runIndex.end(), tri_offset);
                run = static_cast<long long>(it - mesh.runIndex.begin());
                if (run > 0)
                    --run;
            }

            const long long fid = (t < mesh.faceID.size())
                                      ? static_cast<long long>(mesh.faceID[t])
                                      : static_cast<long long>(t);

            auto key = std::make_pair(run, fid);
            auto inserted = key_to_pid.emplace(key, static_cast<int>(key_to_pid.size()));
            P(static_cast<Eigen::Index>(t), 0) = inserted.first->second;
        }

        return P;
    }

} // namespace compas
