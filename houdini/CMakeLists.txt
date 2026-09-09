# Copyright 2023-2024 DreamWorks Animation LLC
# SPDX-License-Identifier: Apache-2.0

set(component moonrayDccPluginsHoudini)

include(GNUInstallDirs)

install(FILES
        moonray_nodes.json
    DESTINATION
        plugin/houdini
)

install(DIRECTORY
        otls
        soho
        python2.7libs
    DESTINATION
        plugin/houdini
)

# Houdini 22 scans versioned Python package directories matching its Python
# runtime.  Keep the source layout compatible with older hosts while installing
# the startup hook under the H22 name.
install(DIRECTORY
        python3.9libs/
    DESTINATION
        plugin/houdini/python3.13libs
)
