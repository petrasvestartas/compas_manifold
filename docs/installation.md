# Installation

## From source (recommended for now)

`compas_manifold` is built with [scikit-build-core](https://github.com/scikit-build/scikit-build-core)
and [nanobind](https://github.com/wjakob/nanobind). The
[Manifold](https://github.com/elalish/manifold) C++ library is fetched and
compiled automatically by CMake during the build — you do **not** need to
install Manifold separately. Manifold's core has no third-party dependencies,
so the build is fully offline once the source is fetched.

### Prerequisites

- A C++17 compiler (MSVC 2022, GCC ≥ 9, or Clang ≥ 10)
- CMake ≥ 3.24
- Python ≥ 3.9

### Quick install

```bash
git clone https://github.com/petrasvestartas/compas_manifold.git
cd compas_manifold
pip install .
```

### Editable / development install

Install the build dependencies once, then build without isolation so rebuilds
are fast:

```bash
pip install nanobind "scikit-build-core[pyproject]" cmake ninja
pip install "numpy>=1.24" "compas>=2.15,<3" pytest

pip install --no-build-isolation -ve .
```

### With [uv](https://docs.astral.sh/uv/)

`uv` creates the environment and resolves everything quickly. The `dev` extra
pulls in the build, test, docs, and visualization dependencies:

```bash
uv venv --python 3.12
source .venv/bin/activate           # Linux / macOS
# source .venv/Scripts/activate     # Windows (Git Bash / MINGW64)
# .venv\Scripts\activate            # Windows (PowerShell / cmd)

uv pip install nanobind "scikit-build-core[pyproject]" cmake ninja
uv pip install --no-build-isolation -ve ".[dev]"
```

To auto-rebuild the C++ when the module is imported after editing a `.cpp`:

```bash
pip install --no-build-isolation -ve . -Ceditable.rebuild=true
```

### Run the tests

```bash
pytest tests -ra
```

## Notes

- The first build clones Manifold into `external/manifold` and compiles it.
  Subsequent builds reuse the cached source.
- Manifold is statically linked into the `_booleans` extension module, so the
  wheel ships a single self-contained binary.
