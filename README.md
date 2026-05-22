# moonray_dcc_plugins - part of the [MoonRay](https://github.com/OpenMoonRay/openmoonray) project
Policies concerning [Governance](https://github.com/OpenMoonRay/openmoonray/blob/main/GOVERNANCE.md), [Code of Conduct](https://github.com/OpenMoonRay/openmoonray/blob/main/CODE_OF_CONDUCT.md), and [Contribution](https://github.com/OpenMoonRay/openmoonray/blob/main/CONTRIBUTING.md) are available in the overarching MoonRay project, defined in the [`OpenMoonRay/openmoonray` GitHub repository superproject](https://github.com/OpenMoonRay/openmoonray).

This repository contains plugins for DCC apps to support MoonRay.

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

