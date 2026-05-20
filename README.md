# moonray_dcc_plugins
This repository contains plugins for DCC apps to support MoonRay.

This repository is part of the larger MoonRay/Arras codebase.  It is included as a submodule in the top-level
OpenMoonRay repository located here: [OpenMoonRay](https://github.com/OpenMoonRay/openmoonray)


## houdini 
Include the folders inside of the houdini folder into your HOUDINI_PATH by copying them into a folder already sourced or adding them to the HOUDINI_PATH environment variable

see https://www.sidefx.com/docs/houdini/basics/config.html

- Add to Variable:
    add the openmoonray/plugin/houdini/ folder to your HOUDINI_PATH
    ```
        HOUDINI_PATH = $HOUDINI_PATH:<openmoonray_install_dir>/plugin/houdini
    ```

- copy the folders inside into your local houdini:
    ```
        cp -r <openmoonray_install_dir>/plugin/houdini/* ~/houdini19.5/
    ```
