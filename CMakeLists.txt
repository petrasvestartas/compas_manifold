cmake_minimum_required(VERSION 3.24...3.30)

project(manifold_wrapper LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Static libs linked into a shared module need position-independent code.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# =====================================================================
# MSVC platform settings (mirrors compas_cgal). /bigobj is required by
# Manifold's heavily-templated translation units.
# =====================================================================
if(MSVC)
    set(CMAKE_GENERATOR_PLATFORM x64)
    add_compile_options(/bigobj)
endif()

# =====================================================================
# Superbuild dependency: the Manifold library.
#
# Manifold is NOT header-only: its boolean engine must be compiled. We
# fetch a pinned release into external/manifold (echoing the compas_cgal
# external/ layout) and build its core sources into a single STATIC
# library that is absorbed into our extension module. The resulting
# wheel therefore ships one self-contained binary with no runtime
# shared library to locate.
#
# We deliberately do NOT add_subdirectory() Manifold's own CMake: that
# would pull in its install()/export/test machinery. Manifold's core has
# no external dependencies (TBB and Tracy are the only optional ones and
# stay OFF), so compiling the ~two dozen core sources directly is fully
# offline and completely under our control. The SOURCE_SUBDIR trick
# below makes FetchContent download the sources WITHOUT configuring
# Manifold's CMakeLists.
# =====================================================================
include(FetchContent)

set(EXTERNAL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/external")
set(MANIFOLD_SOURCE_DIR "${EXTERNAL_DIR}/manifold")

FetchContent_Declare(
    manifold
    GIT_REPOSITORY https://github.com/elalish/manifold.git
    GIT_TAG v3.5.1
    GIT_SHALLOW TRUE
    SOURCE_DIR "${MANIFOLD_SOURCE_DIR}"
    # Point at a subdir with no CMakeLists.txt so MakeAvailable only
    # downloads and never configures Manifold's own build.
    SOURCE_SUBDIR _download_only
)
FetchContent_MakeAvailable(manifold)

# Eigen (header-only) is needed for nanobind's Eigen <-> numpy conversion in
# the binding layer. Downloaded with the same SOURCE_SUBDIR trick so its own
# CMake never runs; we only need the headers.
set(EIGEN_SOURCE_DIR "${EXTERNAL_DIR}/eigen")
FetchContent_Declare(
    eigen
    GIT_REPOSITORY https://gitlab.com/libeigen/eigen.git
    GIT_TAG 3.4.0
    GIT_SHALLOW TRUE
    SOURCE_DIR "${EIGEN_SOURCE_DIR}"
    SOURCE_SUBDIR _download_only
)
FetchContent_MakeAvailable(eigen)

# The Manifold core sources. The released src/ tree contains exactly the
# boolean-engine translation units (cross_section.cpp, which needs Clipper2,
# is only present when the 2D CrossSection feature is enabled, so it is not
# pulled in here). Globbing keeps this robust across Manifold's internal file
# reorganisations between releases.
file(GLOB MANIFOLD_CORE_SRCS CONFIGURE_DEPENDS "${MANIFOLD_SOURCE_DIR}/src/*.cpp")
if(NOT MANIFOLD_CORE_SRCS)
    message(FATAL_ERROR "No Manifold sources found in ${MANIFOLD_SOURCE_DIR}/src — fetch failed?")
endif()

add_library(manifold_core STATIC ${MANIFOLD_CORE_SRCS})
target_compile_features(manifold_core PUBLIC cxx_std_17)
target_include_directories(manifold_core
    PUBLIC "${MANIFOLD_SOURCE_DIR}/include"
    PRIVATE "${MANIFOLD_SOURCE_DIR}/src"
)
# Sequential backend (no TBB). Matches Manifold's own non-parallel build.
target_compile_definitions(manifold_core PUBLIC MANIFOLD_PAR=-1)

# Manifold disables floating-point contraction (e.g. FMA) so its robust
# predicates produce identical results across compilers. Replicate that.
include(CheckCXXCompilerFlag)
if(NOT MSVC)
    check_cxx_compiler_flag(-ffp-contract=off HAS_FP_CONTRACT)
    if(HAS_FP_CONTRACT)
        target_compile_options(manifold_core PRIVATE -ffp-contract=off)
    endif()
    target_compile_options(manifold_core PRIVATE -w) # silence upstream warnings
endif()

# =====================================================================
# Python binding via nanobind + scikit-build-core.
# =====================================================================
if(NOT SKBUILD)
    message(WARNING "\
  This CMake file is meant to be executed using 'scikit-build'. Running
  it directly will almost certainly not produce the desired result. If
  you are a user trying to install this package, please use:
  =====================================================================
   $ pip install .
  =====================================================================
  For development, install the build dependencies once and use:
  =====================================================================
   $ pip install nanobind scikit-build-core[pyproject]
   $ pip install --no-build-isolation -ve .
   $ pip install --no-build-isolation -ve . -Ceditable.rebuild=true
  =====================================================================")
endif()

find_package(Python 3.9
    REQUIRED COMPONENTS Interpreter Development.Module
    OPTIONAL_COMPONENTS Development.SABIModule)

find_package(nanobind CONFIG REQUIRED)

# Function to add a nanobind module that links against Manifold's core.
function(add_nanobind_module module_name source_file)
    nanobind_add_module(${module_name} STABLE_ABI NB_STATIC ${source_file})
    target_link_libraries(${module_name} PRIVATE manifold_core)
    target_include_directories(${module_name} PRIVATE "${EIGEN_SOURCE_DIR}")
    install(TARGETS ${module_name} LIBRARY DESTINATION compas_manifold)
endfunction()

# Add new modules here.
add_nanobind_module(_booleans src/booleans.cpp)
