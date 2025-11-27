cmake_minimum_required(VERSION 3.18)
project(everybeam_py LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

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

find_package(pybind11 CONFIG REQUIRED)
find_package(Threads REQUIRED)
find_package(OpenMP)
find_package(Boost REQUIRED)
message(STATUS "Boost include dirs: ${Boost_INCLUDE_DIRS}")

function(_find_required_library out_var lib_name)
  find_library(${out_var}
               NAMES ${lib_name}
               PATHS ${CASACORE_LIB_DIR} ${EVERYBEAM_LIB_DIR}
                     /opt/miniforge/envs/casa6/lib
                     /usr/lib/x86_64-linux-gnu /usr/lib /lib
               NO_DEFAULT_PATH)
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
    ${Boost_INCLUDE_DIRS}
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

# Provide the staged lib directory as an RPATH hint for runtime loading
set_target_properties(
  everybeam_py PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/python"
  INSTALL_RPATH "${EVERYBEAM_LIB_DIR};${CASACORE_LIB_DIR}"
  BUILD_RPATH "${EVERYBEAM_LIB_DIR};${CASACORE_LIB_DIR}"
)
