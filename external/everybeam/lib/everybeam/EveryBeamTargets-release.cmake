#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "EveryBeam::everybeam" for configuration "Release"
set_property(TARGET EveryBeam::everybeam APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(EveryBeam::everybeam PROPERTIES
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "Boost::date_time"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libeverybeam.so"
  IMPORTED_SONAME_RELEASE "libeverybeam.so"
  )

list(APPEND _cmake_import_check_targets EveryBeam::everybeam )
list(APPEND _cmake_import_check_files_for_EveryBeam::everybeam "${_IMPORT_PREFIX}/lib/libeverybeam.so" )

# Import target "EveryBeam::everybeam-core" for configuration "Release"
set_property(TARGET EveryBeam::everybeam-core APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(EveryBeam::everybeam-core PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libeverybeam-core.so"
  IMPORTED_SONAME_RELEASE "libeverybeam-core.so"
  )

list(APPEND _cmake_import_check_targets EveryBeam::everybeam-core )
list(APPEND _cmake_import_check_files_for_EveryBeam::everybeam-core "${_IMPORT_PREFIX}/lib/libeverybeam-core.so" )

# Import target "EveryBeam::hamaker" for configuration "Release"
set_property(TARGET EveryBeam::hamaker APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(EveryBeam::hamaker PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libeverybeam-hamaker.so"
  IMPORTED_SONAME_RELEASE "libeverybeam-hamaker.so"
  )

list(APPEND _cmake_import_check_targets EveryBeam::hamaker )
list(APPEND _cmake_import_check_files_for_EveryBeam::hamaker "${_IMPORT_PREFIX}/lib/libeverybeam-hamaker.so" )

# Import target "EveryBeam::oskar" for configuration "Release"
set_property(TARGET EveryBeam::oskar APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(EveryBeam::oskar PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libeverybeam-oskar.so"
  IMPORTED_SONAME_RELEASE "libeverybeam-oskar.so"
  )

list(APPEND _cmake_import_check_targets EveryBeam::oskar )
list(APPEND _cmake_import_check_files_for_EveryBeam::oskar "${_IMPORT_PREFIX}/lib/libeverybeam-oskar.so" )

# Import target "EveryBeam::skamidbeam" for configuration "Release"
set_property(TARGET EveryBeam::skamidbeam APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(EveryBeam::skamidbeam PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libeverybeam-skamidbeam.so"
  IMPORTED_SONAME_RELEASE "libeverybeam-skamidbeam.so"
  )

list(APPEND _cmake_import_check_targets EveryBeam::skamidbeam )
list(APPEND _cmake_import_check_files_for_EveryBeam::skamidbeam "${_IMPORT_PREFIX}/lib/libeverybeam-skamidbeam.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
