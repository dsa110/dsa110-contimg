cmake_minimum_required(VERSION 3.18)

# Suppress deprecation warning for FindPythonLibsNew used by older pybind11
# This is needed when system pybind11 uses legacy Python finding approach
if(POLICY CMP0148)
  cmake_policy(SET CMP0148 OLD)
endif()

project(everybeam_py LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Prefer conda environment for pybind11 and other packages
if(DEFINED ENV{CONDA_PREFIX})
  list(INSERT CMAKE_PREFIX_PATH 0 "$ENV{CONDA_PREFIX}")
  # Prioritize conda libraries to avoid conflicts with system libraries
  link_directories(BEFORE "$ENV{CONDA_PREFIX}/lib")
  # Set RPATH to ensure conda libraries are found at runtime
  set(CMAKE_INSTALL_RPATH "$ENV{CONDA_PREFIX}/lib")
  set(CMAKE_BUILD_RPATH "$ENV{CONDA_PREFIX}/lib")
endif()

# Suppress CMake warnings about library path cycles and conflicts
# These occur because conda provides its own libc/libm/libpthread which creates
# circular dependencies with system libraries - this is expected in conda envs
set(CMAKE_NO_SYSTEM_FROM_IMPORTED ON)
set(CMAKE_LINK_DIRECTORIES_BEFORE ON)

# Explicitly tell CMake to prefer the libraries we specify over implicit ones
cmake_policy(SET CMP0060 NEW)  # Link libraries by full path when available

# Override implicit link directories to prevent conflicts with system libraries
# This removes /usr/lib/x86_64-linux-gnu from implicit search when we want conda libs
set(CMAKE_CXX_IMPLICIT_LINK_DIRECTORIES "")
set(CMAKE_C_IMPLICIT_LINK_DIRECTORIES "")

# Disable the "cannot generate safe linker search path" warnings
# The cycle is: conda-lib -> sysroot/libpthread -> system/libm -> conda-lib
# This is a known limitation of conda cross-compilation toolchains and is safe to ignore
set(CMAKE_POLICY_WARNING_CMP0060 OFF)

# Allow callers to override the staged EveryBeam artifacts location
set(EVERYBEAM_ROOT "${PROJECT_SOURCE_DIR}/../everybeam"
    CACHE PATH "Path to staged EveryBeam headers and libraries")
set(EVERYBEAM_INCLUDE_DIR "${EVERYBEAM_ROOT}/include")
set(EVERYBEAM_LIB_DIR "${EVERYBEAM_ROOT}/lib")

set(AOCOMMON_ROOT "${PROJECT_SOURCE_DIR}/../aocommon"
    CACHE PATH "Path to staged aocommon headers")
set(AOCOMMON_INCLUDE_DIR "${AOCOMMON_ROOT}")

set(CASACORE_ROOT "/opt/miniforge/envs/casa6"
    CACHE PATH "Path to casacore/ CASA installation")
set(CASACORE_INCLUDE_DIR "${CASACORE_ROOT}/include")
set(CASACORE_LIB_DIR "${CASACORE_ROOT}/lib")

# Use Boost's config package instead of the deprecated FindBoost module when available.
if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()

if(NOT EXISTS "${EVERYBEAM_INCLUDE_DIR}/EveryBeam")
  message(FATAL_ERROR "EveryBeam headers not found in ${EVERYBEAM_INCLUDE_DIR}")
endif()

if(NOT EXISTS "${EVERYBEAM_LIB_DIR}")
  message(FATAL_ERROR "EveryBeam libraries not found in ${EVERYBEAM_LIB_DIR}")
endif()

if(NOT EXISTS "${AOCOMMON_INCLUDE_DIR}/aocommon")
  message(FATAL_ERROR "aocommon headers not found in ${AOCOMMON_INCLUDE_DIR}")
endif()

if(NOT EXISTS "${CASACORE_INCLUDE_DIR}/casacore")
  message(FATAL_ERROR "casacore headers not found in ${CASACORE_INCLUDE_DIR}")
endif()

if(NOT EXISTS "${CASACORE_LIB_DIR}")
  message(FATAL_ERROR "casacore libraries not found in ${CASACORE_LIB_DIR}")
endif()

# Use conda's pybind11 (v3.0+) instead of system pybind11 (v2.2) to avoid deprecation warnings
# The system pybind11 at /usr/lib/cmake/pybind11/ uses deprecated FindPythonLibsNew
if(DEFINED ENV{CONDA_PREFIX})
  execute_process(
    COMMAND "$ENV{CONDA_PREFIX}/bin/python" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
  )
  if(PYBIND11_CMAKE_DIR)
    list(INSERT CMAKE_PREFIX_PATH 0 "${PYBIND11_CMAKE_DIR}")
    message(STATUS "Using conda pybind11 from: ${PYBIND11_CMAKE_DIR}")
  endif()
endif()

find_package(pybind11 CONFIG REQUIRED)
find_package(Threads REQUIRED)
find_package(OpenMP)
find_package(Boost CONFIG REQUIRED)

function(_find_required_library out_var lib_name)
  # Prefer conda libraries over system libraries to avoid cyclic dependencies
  if(DEFINED ENV{CONDA_PREFIX})
    find_library(${out_var}
                 NAMES ${lib_name}
                 PATHS ${CASACORE_LIB_DIR} ${EVERYBEAM_LIB_DIR}
                       "$ENV{CONDA_PREFIX}/lib"
                 NO_DEFAULT_PATH)
  else()
    find_library(${out_var}
                 NAMES ${lib_name}
                 PATHS ${CASACORE_LIB_DIR} ${EVERYBEAM_LIB_DIR}
                       /usr/lib/x86_64-linux-gnu /usr/lib /lib
                 NO_DEFAULT_PATH)
  endif()
  if(NOT ${out_var})
    find_library(${out_var} NAMES ${lib_name})
  endif()
  if(NOT ${out_var})
    message(FATAL_ERROR "Could not locate required library ${lib_name}. Set ${out_var} manually.")
  endif()
  set(${out_var} "${${out_var}}" PARENT_SCOPE)
endfunction()

set(EVERYBEAM_LIBRARIES)
foreach(lib everybeam everybeam-core everybeam-hamaker everybeam-oskar everybeam-skamidbeam)
  _find_required_library(EVERYBEAM_${lib}_LIB ${lib})
  list(APPEND EVERYBEAM_LIBRARIES ${EVERYBEAM_${lib}_LIB})
endforeach()

set(CASACORE_LIBRARIES)
foreach(lib casa_ms casa_fits casa_scimath casa_scimath_f casa_measures casa_tables casa_casa)
  string(REPLACE "." "_" lib_sanitized ${lib})
  _find_required_library(CASACORE_${lib_sanitized}_LIB ${lib})
  list(APPEND CASACORE_LIBRARIES ${CASACORE_${lib_sanitized}_LIB})
endforeach()

set(SYSTEM_LIBRARIES)
foreach(lib cfitsio hdf5_cpp hdf5 crypto curl sz z dl m fftw3f)
  string(REPLACE "." "_" lib_sanitized ${lib})
  _find_required_library(SYSTEM_${lib_sanitized}_LIB ${lib})
  list(APPEND SYSTEM_LIBRARIES ${SYSTEM_${lib_sanitized}_LIB})
endforeach()

pybind11_add_module(everybeam_py src/everybeam_py.cpp)

target_include_directories(
  everybeam_py
  PRIVATE
    ${EVERYBEAM_INCLUDE_DIR}
    ${AOCOMMON_INCLUDE_DIR}
    ${CASACORE_INCLUDE_DIR}
    ${CASACORE_INCLUDE_DIR}/casacore
)

target_link_libraries(
  everybeam_py
  PRIVATE
    ${EVERYBEAM_LIBRARIES}
    ${CASACORE_LIBRARIES}
    ${SYSTEM_LIBRARIES}
    Threads::Threads
    Boost::boost
)

if(OpenMP_CXX_FOUND)
  target_link_libraries(everybeam_py PRIVATE OpenMP::OpenMP_CXX)
endif()

# Match the EveryBeam build, which uses AVX2/FMA matrix types.
target_compile_definitions(everybeam_py PRIVATE USE_AVX_MATRIX)
target_compile_options(everybeam_py PRIVATE -mavx2 -mfma)

# Provide the staged lib directory as an RPATH hint for runtime loading
set_target_properties(
  everybeam_py PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/python"
  INSTALL_RPATH "${EVERYBEAM_LIB_DIR};${CASACORE_LIB_DIR}"
  BUILD_RPATH "${EVERYBEAM_LIB_DIR};${CASACORE_LIB_DIR}"
)
