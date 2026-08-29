"""Add MaterialX to source DW_MOONRAY VOP HDA masks.

This is a source-definition maintenance helper. Run it with Houdini's hython
against the source otls directory before install-time packaging if regenerated
HDAs lose the MaterialX VOP context token:

    hython moonray_vopmask_materialx_patch.py /path/to/houdini/otls

It updates the HDA files in-place so installed definitions do not need a manual
post-install HOM patch.
"""

from __future__ import print_function

import os
import sys

import hou


TOKEN = "MaterialX"
TYPE_MARKER = "DW_MOONRAY"


def _with_materialx(extra_info):
    parts = extra_info.split()
    if TOKEN in parts:
        return extra_info
    if not parts:
        return extra_info
    if parts[0] == "*":
        parts.insert(1, TOKEN)
    elif "moonray" in parts:
        parts.insert(parts.index("moonray"), TOKEN)
    else:
        parts.append(TOKEN)
    return " ".join(parts)


def main(argv):
    if len(argv) != 2:
        print("Usage: hython {} /path/to/houdini/otls".format(argv[0]))
        return 2

    otls_dir = argv[1]
    if not os.path.isdir(otls_dir):
        print("Not a directory:", otls_dir)
        return 2

    changed = []
    skipped = []

    for filename in sorted(os.listdir(otls_dir)):
        if TYPE_MARKER not in filename or not filename.endswith((".hda", ".otl")):
            continue

        hda_path = os.path.join(otls_dir, filename)
        hou.hda.installFile(hda_path)
        definitions = hou.hda.definitionsInFile(hda_path)

        for definition in definitions:
            node_type = definition.nodeType()
            type_name = node_type.nameWithCategory()
            if TYPE_MARKER not in type_name:
                continue

            old_info = definition.extraInfo()
            new_info = _with_materialx(old_info)
            if new_info == old_info:
                skipped.append(type_name)
                continue

            definition.setExtraInfo(new_info)
            definition.save(hda_path, create_backup=False)
            changed.append((type_name, old_info, new_info, hda_path))

    print("Changed:", len(changed))
    print("Skipped:", len(skipped))
    for type_name, old_info, new_info, hda_path in changed[:80]:
        print("CHANGED:", type_name,
              repr(old_info), "->", repr(new_info),
              hda_path)
    if len(changed) > 80:
        print("... and {} more".format(len(changed) - 80))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
