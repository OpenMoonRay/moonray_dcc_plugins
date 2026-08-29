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
        toolbar
        python2.7libs
        python3.9libs
        python3.11libs
    DESTINATION
        plugin/houdini
)
