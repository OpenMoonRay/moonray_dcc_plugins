"""Validate MoonRay VOP network masks in Houdini.

Run with Houdini's hython after sourcing the OpenMoonRay Houdini setup:

    hython moonray_vopmask_check.py

The script is intentionally read-only. It verifies that DW_MOONRAY VOP
definitions include the MaterialX token in their vopnetMask/extraInfo so the
installed definitions are usable inside MaterialX VOP contexts without a
post-install HOM patch.
"""

from __future__ import print_function

import sys

import hou


TOKEN = "MaterialX"
TYPE_MARKER = "DW_MOONRAY"


def main():
    category = hou.vopNodeTypeCategory()
    missing = []
    checked = 0

    for type_name, node_type in sorted(category.nodeTypes().items()):
        if TYPE_MARKER not in type_name:
            continue

        checked += 1
        definition = node_type.definition()
        extra_info = definition.extraInfo() if definition else ""
        mask = node_type.vopnetMask()

        if TOKEN not in mask and TOKEN not in extra_info:
            missing.append((type_name, mask, extra_info,
                            definition.libraryFilePath() if definition else ""))

    print("DW_MOONRAY VOP definitions checked:", checked)
    print("Definitions missing MaterialX:", len(missing))

    for type_name, mask, extra_info, path in missing[:80]:
        print("MISSING:", type_name,
              "mask={!r}".format(mask),
              "extraInfo={!r}".format(extra_info),
              "path={}".format(path))

    if len(missing) > 80:
        print("... and {} more".format(len(missing) - 80))

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
