# Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
# SPDX-License-Identifier: GPL-3.0-or-later

# This is the cmake config script for EveryBeam.
#
# It sets the following variables:
# - EVERYBEAM_INCLUDE_DIR / EVERYBEAM_INCLUDE_DIRS
# - EVERYBEAM_LIB
# - EVERYBEAM_LIB_PATH
# - EVERYBEAM_VERSION[_MAJOR/_MINOR/_PATCH]
# - EVERYBEAM_FOUND
# - EVERYBEAM_ROOT_DIR

include("${CMAKE_CURRENT_LIST_DIR}/EveryBeamTargets.cmake")

# Compute path
get_filename_component(_EVERYBEAM_CMAKE_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
get_filename_component(_EVERYBEAM_CMAKE_DIR_ABS "${_EVERYBEAM_CMAKE_DIR}" ABSOLUTE)
get_filename_component(_EVERYBEAM_ROOT_DIR "${_EVERYBEAM_CMAKE_DIR_ABS}/../.." ABSOLUTE)

set(EVERYBEAM_ROOT_DIR "${_EVERYBEAM_ROOT_DIR}"
    CACHE PATH "EveryBeam root (prefix) directory")

set(EVERYBEAM_INCLUDE_DIR "${EVERYBEAM_ROOT_DIR}/include"
    CACHE PATH "EveryBeam include directory")

set(EVERYBEAM_INCLUDE_DIRS ${EVERYBEAM_INCLUDE_DIR})

set(EVERYBEAM_LIB_PATH "${EVERYBEAM_ROOT_DIR}/lib"
    CACHE PATH "EveryBeam library directory")

find_library(EVERYBEAM_LIB everybeam PATH ${EVERYBEAM_LIB_PATH} NO_DEFAULT_PATH
             DOC "EveryBeam library directory")
message(STATUS "Found EveryBeam 0.7.4.")
message(STATUS "  EveryBeam include dir: ${EVERYBEAM_INCLUDE_DIR}")
message(STATUS "  EveryBeam lib: ${EVERYBEAM_LIB}")

# All capitals for version and found variables
set(EVERYBEAM_VERSION "0.7.4")
set(EVERYBEAM_VERSION_MAJOR 0)
set(EVERYBEAM_VERSION_MINOR 7)
set(EVERYBEAM_VERSION_PATCH 4)
set(EVERYBEAM_FOUND 1)

unset(_EVERYBEAM_ROOT_DIR)
unset(_EVERYBEAM_CMAKE_DIR)
unset(_EVERYBEAM_CMAKE_DIR_ABS)
