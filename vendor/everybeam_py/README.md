# everybeam_py (prototype)

This directory contains a pybind11 prototype for exposing EveryBeam to Python.
It now links against the casacore/HDF5/FFTW toolchain shipped with CASA 6 and
uses the staged EveryBeam + aocommon headers harvested from the
`wsclean-everybeam:0.7.4` Docker image.

## Quick start

```bash
cd /data/dsa110-contimg/bindings/everybeam_py
python -m pip install --upgrade pip
python -m pip install pybind11 scikit-build-core
python -m build  # or: pip install .
```

By default the CMake configuration expects:

- `vendor/everybeam` – headers + shared libs copied from the Docker image
- `vendor/aocommon` – header-only dependency staged from the same image
- `CASACORE_ROOT=/opt/miniforge/envs/casa6` – provides casacore, HDF5, FFTW,
  etc.

Override any of these via `-DEVERYBEAM_ROOT=…`, `-DAOCOMMON_ROOT=…`, and
`-DCASACORE_ROOT=…`:

```bash
python -m build -- -DCASACORE_ROOT=$HOME/casa -DEVERYBEAM_ROOT=/tmp/everybeam
```

> **Toolchain note** The conda `x86_64-conda-linux-gnu-c++` compiler bundled
> with CASA uses a sysroot that hides the host `/usr/include`, so Boost headers
> from the OS are missing. Configure with the system compiler instead:
>
> ```bash
> cmake -S bindings/everybeam_py -B bindings/everybeam_py/build-gcc \
>   -DCMAKE_CXX_COMPILER=/usr/bin/g++-13 \
>   -Dpybind11_DIR=… -DPython3_EXECUTABLE=…
> cmake --build bindings/everybeam_py/build-gcc
> ```
>
> The committed `build-gcc` directory demonstrates a successful invocation built
> with `g++-13`.

## Exported symbols

The module currently exposes two helpers:

- `everybeam_py.version()` – returns the staged EveryBeam version string
- `everybeam_py.evaluate_primary_beam(...)` – loads a Measurement Set and
  computes full-Jones station responses for a given direction/time/frequency

Both are intentionally minimal but already rely on the real EveryBeam C++ API,
verifying that the staged artifacts + runtime dependencies link successfully.
