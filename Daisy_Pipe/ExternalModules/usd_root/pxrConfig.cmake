# - Configuration file for the pxr project
# Defines the following variables:
# PXR_MAJOR_VERSION - Major version number.
# PXR_MINOR_VERSION - Minor version number.
# PXR_PATCH_VERSION - Patch version number.
# PXR_VERSION       - Complete pxr version string.
# PXR_INCLUDE_DIRS  - Root include directory for the installed project.
# PXR_LIBRARIES     - List of all libraries, by target name.
# PXR_foo_LIBRARY   - Absolute path to individual libraries.
# The preprocessor definition PXR_STATIC will be defined if appropriate

get_filename_component(PXR_CMAKE_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)

set(PXR_MAJOR_VERSION "0")
set(PXR_MINOR_VERSION "25")
set(PXR_PATCH_VERSION "8")
set(PXR_VERSION "2508")

include(CMakeFindDependencyMacro)

# If Python support was enabled for this USD build, find the import
# targets by invoking the appropriate FindPython module.
if(ON)
    if(NOT Python3_FOUND)
        find_dependency(Python3 COMPONENTS Development)
    endif()
endif()

if (NOT DEFINED PXR_FIND_TBB_IN_CONFIG)
    set(PXR_FIND_TBB_IN_CONFIG "ON")
endif()
if (PXR_FIND_TBB_IN_CONFIG)
    # find the TBB find_dependency
    find_dependency(TBB 2020.3 CONFIG)
endif()

if (NOT DEFINED PXR_FIND_OPENSUBDIV_IN_CONFIG)
    set(PXR_FIND_OPENSUBDIV_IN_CONFIG "ON")
endif()
if (PXR_FIND_OPENSUBDIV_IN_CONFIG)
    find_dependency(OpenSubdiv 3.6.0 CONFIG)
endif()

# If MaterialX support was enabled for this USD build
# find the MaterialX dependency
if(ON)
    find_dependency(MaterialX)
endif()

# If Imath support was enabled for this USD build
# find the Imath dependency
if(1)
    find_dependency(Imath)
endif()

# If this build is using a custom work implementation, find the package
# providing that implementation.
if(NOT "" STREQUAL "")
    find_dependency()
endif()

include("${PXR_CMAKE_DIR}/cmake/pxrTargets.cmake")
if (TARGET usd_ms)
    set(libs "usd_ms")
else()
    set(libs "boost;python;arch;tf;gf;pegtl;js;trace;work;plug;vt;ts;ar;kind;sdf;sdr;pcp;usd;usdGeom;usdVol;usdMedia;usdShade;usdLux;usdProc;usdRender;usdHydra;usdRi;usdSemantics;usdSkel;usdUI;usdUtils;usdPhysics;usdMtlx;usdValidation;usdGeomValidators;usdPhysicsValidators;usdShadeValidators;usdSkelValidators;usdUtilsValidators;garch;hf;hio;cameraUtil;pxOsd;geomUtil;glf;hgi;hgiGL;hgiInterop;hd;hdar;hdGp;hdsi;hdMtlx;hdSt;hdx;usdImaging;usdImagingGL;usdProcImaging;usdRiPxrImaging;usdSkelImaging;usdVolImaging;usdAppUtils;usdviewq;usdBakeMtlx")
endif()
set(PXR_LIBRARIES "")
set(PXR_INCLUDE_DIRS "${PXR_CMAKE_DIR}/include")
string(REPLACE " " ";" libs "${libs}")
foreach(lib ${libs})
    get_target_property(location ${lib} LOCATION)
    set(PXR_${lib}_LIBRARY ${location})
    list(APPEND PXR_LIBRARIES ${lib})
endforeach()
if(NOT ON)
    if(WIN32)
        list(APPEND PXR_LIBRARIES Shlwapi.lib)
        list(APPEND PXR_LIBRARIES Dbghelp.lib)
    endif()
    add_definitions(-DPXR_STATIC)
endif()
