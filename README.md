# moonray_dcc_plugins - part of the [MoonRay](https://github.com/OpenMoonRay/openmoonray) project

Policies concerning [Governance](https://github.com/OpenMoonRay/openmoonray/blob/main/GOVERNANCE.md), [Code of Conduct](https://github.com/OpenMoonRay/openmoonray/blob/main/CODE_OF_CONDUCT.md), and [Contribution](https://github.com/OpenMoonRay/openmoonray/blob/main/CONTRIBUTING.md) are available in the overarching MoonRay project, defined in the [`OpenMoonRay/openmoonray` GitHub repository superproject](https://github.com/OpenMoonRay/openmoonray).

This repository contains plugins for DCC apps to support MoonRay.

# Houdini 
## Installation

If you folow the cmake build and install instructions in the root repo, this plugin is copied as an installation step and you should not need to do anything if you source the `setupHoudini.sh` script.

If you want to make changes or develop the plugin, note that 
1. The plugin is copied to `<openmoonray_install_dir>/plugin/houdini`
2. This path is added to the `HOUDINI_PATH` in `<openmoonray_install_dir>/scripts/{macOS, Rocky9}/setupHoudini.sh` 

It is also possible to copy the plugin to your `~/Houdini20.0/` directory, or another location in `HOUINI_PATH`. Just be careful to not include two different versions of these folders.

> see https://www.sidefx.com/docs/houdini/basics/config.html


## Updating

We provide a script `moonray_dcc_plugins/scripts/update_hdas.py` to update the existing `.hda` and `.ds` files from local Moonray modifications. We encourage developers to update relevant nodes with modifications to the underlying renderer.

Runtime dependencies:
    - hython / hou (Houdini writes the `.hda` and `.ds` files itself)
    - `rdl2_json_exporter` on $PATH, with $RDL2_DSO_PATH set to the proxy DSOs
    - pxr Python modules (optional; falls back to static output tags)

1. Set up environment:
Use houdini shell, or source their setup.sh, for example:
```
source <houdini_install_dir>/Houdini20.0.751/Frameworks/Houdini.framework/Versions/Current/Resources/houdini_setup
```

Add the moonray environment:
```
source <openmoonray_install_dir>/scripts/{macOS, Rocky9}/setupHoudini.sh
```

2. Run script

```
cd <moonray_dcc_plugins_repo_root>
hython scripts/update_hdas.py --output-dir ./houdini
```

3. Install
```
cp houdini/moonray_nodes.json <openmoonray_install_dir>/plugin/houdini
cp -r houdini/{otls,soho,python*} <openmoonray_install_dir>/plugin/houdini
```


