# Copyright 2026 DreamWorks Animation LLC
# SPDX-License-Identifier: Apache-2.0
"""
Generate the Houdini plugin artifacts in moonray_dcc_plugins from RDL2 metadata.

Every file this writes is derived data: the shader/light/geometry attribute
descriptions come from rdl2_json_exporter, which reads the proxy DSOs on
RDL2_DSO_PATH. Outputs, relative to --output-dir:

    otls/Vop::DW_MOONRAY::<Class>::<v>.hda   one VOP HDA per shading class
    moonray_nodes.json                       serialized class/parm metadata
    soho/parameters/HdMoonrayRendererPlugin_{Light,Geometry,Global,Aov}.ds
    soho/parameters/moonray_Override.ds
    soho/parameters/moonray_<Class>.ds

Runtime dependencies:
    - hython / hou   (Houdini writes the .hda and .ds files itself)
    - rdl2_json_exporter on $PATH, with $RDL2_DSO_PATH set to the proxy DSOs
    - pxr Python modules (optional; falls back to static output tags)

To run this script:
    source <openmoonray install>/scripts/setup.sh
    hython update_houdini_hdas.py --output-dir <moonray_dcc_plugins>/houdini
"""
from __future__ import absolute_import, print_function

import argparse
import json
import logging
import os
import re
import shutil
import subprocess

import hou
from pxr import Sdf, Sdr, Usd, UsdLux


logger = logging.getLogger(__name__)

MOONRAY_DATA_JSON_FILE = os.path.join(os.path.dirname(__file__), "usd_attribute_map.json")
# The default output directory is the "houdini" subdirectory of the current 
# working directory, which is expected to be the root of the moonray_dcc_plugins repo. 
# This is where the script will write moonray_nodes.json and all generated HDAs and .ds files.
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), 'houdini')
MOONSHINE_DATA_FILE = "moonray_nodes.json"

MR_TYPE_CAMERA = 'Camera'
MR_TYPE_DISPLACEMENT = 'Displacement'
MR_TYPE_DISPLAY_FILTER = 'DisplayFilter'
MR_TYPE_GEOMETRY = 'Geometry'
MR_TYPE_HAIR_LAYERABLE = 'DwaBaseHairLayerable'
MR_TYPE_LAYERABLE = 'DwaBaseLayerable'
MR_TYPE_LIGHT = 'Light'
MR_TYPE_LIGHT_FILTER = 'LightFilter'
MR_TYPE_LIGHT_SET = 'LightSet'
MR_TYPE_MAP = 'Map'
MR_TYPE_MATERIAL = 'Material'
MR_TYPE_DWA_BASE = 'DwaBase'
MR_TYPE_NORMALMAP = 'NormalMap'
MR_TYPE_RENDER_OUTPUT = 'RenderOutput'
MR_TYPE_TRACESET = 'TraceSet'
MR_TYPE_VOLUME = 'Volume'

BOOL = 'Bool'
BOOLVECTOR = 'BoolVector'
INT = 'Int'
INTVECTOR = 'IntVector'
FLOAT = 'Float'
FLOATVECTOR = 'FloatVector'
DOUBLE = 'Double'
DOUBLEVECTOR = 'DoubleVector'
VEC2F = 'Vec2f'
VEC2FVECTOR = 'Vec2fVector'
VEC3D = 'Vec3d'
VEC3F = 'Vec3f'
VEC3FVECTOR = 'Vec3fVector'
VEC4F = 'Vec4f'
VEC4FVECTOR = 'Vec4fVector'
MAT4F = 'Mat4f'
MAT4FVECTOR = 'Mat4fVector'
MAT4D = 'Mat4d'
MAT4DVECTOR = 'Mat4dVector'
MAT3F = 'Mat3f'
MAT3FVECTOR = 'Mat3fVector'
RGB = 'Rgb'
RGBVECTOR = 'RgbVector'
RGBA = 'Rgba'
RGBAVECTOR = 'RgbaVector'
SCENEOBJECT = 'SceneObject*'
SCENEOBJECTVECTOR = 'SceneObjectVector'
SCENEOBJECTINDEXABLE = 'SceneObjectIndexable'
STRING = 'String'
STRINGVECTOR = 'StringVector'

BIND_SUFFIX = "_bind"
HANDLED_PARM_TYPES = [
    hou.parmTemplateType.Float,
    hou.parmTemplateType.Int,
    hou.parmTemplateType.String,
    hou.parmTemplateType.Toggle,
]

ARRAY_TYPE_MAP = {
    'FloatVector': (float, 1),
    'IntVector': (int, 1),
    'RgbVector': (float, 3),
    'SceneObjectVector': (str, 1),
    'StringVector': (str, 1),
    'Vec2fVector': (float, 2),
    'Vec3fVector': (float, 3),
    'Vec4fVector': (float, 4),
}

RAMP_COMPONENT_INTERPOLATIONS = 'interpolation_types'
RAMP_COMPONENT_VALUES = 'values'
RAMP_COMPONENT_POSITIONS = 'positions'

RAMP_MOONRAY_NONE = 0
RAMP_MOONRAY_LINEAR = 1
RAMP_MOONRAY_CATMULL_ROM = 5
RAMP_MOONRAY_MONOTONE_CUBIC = 6
RAMP_MOONRAY_SMOOTH = 4

RAMP_INTERP_LOOKUP = {
    hou.rampBasis.Constant: RAMP_MOONRAY_NONE,
    hou.rampBasis.Linear: RAMP_MOONRAY_LINEAR,
    hou.rampBasis.CatmullRom: RAMP_MOONRAY_CATMULL_ROM,
    hou.rampBasis.MonotoneCubic: RAMP_MOONRAY_MONOTONE_CUBIC,
    hou.rampBasis.Bezier: RAMP_MOONRAY_SMOOTH,
    hou.rampBasis.BSpline: RAMP_MOONRAY_SMOOTH,
    hou.rampBasis.Hermite: RAMP_MOONRAY_SMOOTH,
}

TAG_IS_MOONRAY_PARM = "moonray::is_parm"
TAG_SHADER_IS_PARM = "sidefx::shader_isparm"
DEFAULT_MOONRAY_PARM_TAGS = {TAG_IS_MOONRAY_PARM: "1"}
DISPLAY_LOGARITHMIC = 'logarithmic'

IGNORE_CODE_MISMATCHES = (
    'AttributeMap',
    'ImageMap',
    'MeshLight',
    'SpotLight',
    'StampMap',
)

VAR_SKIP_MOONRAY_BUGS = 'DWA_SKIP_MOONRAY_BUILD_BUGS'
VAR_CLASSES_JSON = 'MOONRAY_CLASSES_JSON'

VOP_TYPES = (
    MR_TYPE_DISPLACEMENT,
    MR_TYPE_DISPLAY_FILTER,
    MR_TYPE_HAIR_LAYERABLE,
    MR_TYPE_LAYERABLE,
    MR_TYPE_MAP,
    MR_TYPE_MATERIAL,
    MR_TYPE_NORMALMAP,
    MR_TYPE_VOLUME,
    MR_TYPE_DWA_BASE,
)

VOPS_WITH_CUSTOM_UIS = set((
    "AttributeMap",
    "DwaSwitchMaterial",
    "ImageMap",
    "ImageNormalMap",
    "SwitchColorMap",
    "SwitchFloatMap",
    "SwitchMaterial",
))

RENDER_PROPERTIES = (
    'label',
    'static',
    'side_type',
    'reverse_normals',
    'visible_in_camera',
    'visible_shadow',
    'visible_diffuse_reflection',
    'visible_diffuse_transmission',
    'visible_glossy_reflection',
    'visible_glossy_transmission',
    'visible_mirror_reflection',
    'visible_mirror_transmission',
    'visible_volume',
    'ray_epsilon',
    'shadow_ray_epsilon',
)

DEPRECATED_PREFIX = "_deprecated_"

# Documentation URL embedded in each HDA's HelpUrl section. Empty means no
# HelpUrl section is written; set it with --help-url.
HELP_URL = os.environ.get('MOONRAY_HDA_HELP_URL', '')

MOONRAY_TO_USD_TYPE = {
    "Int": "int",
    "Bool": "bool",
    "Float": "float",
    "Double": "double",
    "String": "string",
    "Rgb": "color3f",
    "RgbVector": "color3f[]",
    "Vec2f": "float2",
    "Vec3f": "float3",
    "FloatVector": "float[]",
}

try:
    with open(MOONRAY_DATA_JSON_FILE, 'r') as file:
        USD_ATTRIBUTE_MAP = json.load(file)
except Exception:
    USD_ATTRIBUTE_MAP = {}

def _decode(value):
    if value is None:
        return ''
    if hasattr(value, 'decode'):
        return value.decode()
    return value


def ensure_directory(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def validate_public_packages(package_string):
    """Refuse a package set that would put proprietary shaders in a public repo.

    moonshine_dwa and friends carry DreamWorks' closed source shaders. The
    generator itself is package agnostic: it builds a node for every scene
    class it is given, so the package set is the only thing keeping those
    shaders out of the public artifacts.
    """
    for pkg in package_string.split():
        if 'dwa' in pkg.lower():
            raise ValueError(
                "DWA package detected: '{0}'. Public builds must not use DWA "
                "packages. Pass --internal to build the internal plugin set.".format(pkg)
            )


def get_major_moonshine_version(package_string):
    try:
        return package_string.partition("moonshine-")[2].split()[0].split(".")[0]
    except Exception:
        raise ValueError(
            "Couldn't determine major moonshine version from arg: {0}".format(
                package_string)
        )


def rdla_to_usd_type(type_name):
    type_map = {
        BOOL: Sdf.ValueTypeNames.Bool,
        BOOLVECTOR: Sdf.ValueTypeNames.BoolArray,
        INT: Sdf.ValueTypeNames.Int,
        INTVECTOR: Sdf.ValueTypeNames.IntArray,
        FLOAT: Sdf.ValueTypeNames.Float,
        FLOATVECTOR: Sdf.ValueTypeNames.FloatArray,
        DOUBLE: Sdf.ValueTypeNames.Double,
        DOUBLEVECTOR: Sdf.ValueTypeNames.DoubleArray,
        VEC2F: Sdf.ValueTypeNames.Float2,
        VEC2FVECTOR: Sdf.ValueTypeNames.Float2Array,
        VEC3D: Sdf.ValueTypeNames.Vector3d,
        VEC3F: Sdf.ValueTypeNames.Vector3f,
        VEC3FVECTOR: Sdf.ValueTypeNames.Vector3fArray,
        VEC4F: Sdf.ValueTypeNames.Float4,
        VEC4FVECTOR: Sdf.ValueTypeNames.Float4Array,
        MAT4F: Sdf.ValueTypeNames.FloatArray,
        MAT4FVECTOR: Sdf.ValueTypeNames.FloatArray,
        MAT4D: Sdf.ValueTypeNames.DoubleArray,
        MAT4DVECTOR: Sdf.ValueTypeNames.DoubleArray,
        MAT3F: Sdf.ValueTypeNames.FloatArray,
        MAT3FVECTOR: Sdf.ValueTypeNames.FloatArray,
        RGB: Sdf.ValueTypeNames.Color3f,
        RGBVECTOR: Sdf.ValueTypeNames.Color3fArray,
        RGBA: Sdf.ValueTypeNames.Color4f,
        RGBAVECTOR: Sdf.ValueTypeNames.Color4fArray,
        SCENEOBJECT: Usd.Relationship,
        SCENEOBJECTVECTOR: Usd.Relationship,
        SCENEOBJECTINDEXABLE: Usd.Relationship,
        STRING: Sdf.ValueTypeNames.String,
        STRINGVECTOR: Sdf.ValueTypeNames.StringArray,
    }
    usd_type = type_map.get(type_name)
    if usd_type is None:
        raise ValueError(
            "Unknown type name for USD class '{0}'. A new rdl2 attribute type has "
            "appeared; add it to rdla_to_usd_type.".format(type_name))
    return usd_type


class MoonrayBuildError(Exception):
    pass


def build_error(message):
    print(message)
    if os.environ.get(VAR_SKIP_MOONRAY_BUGS, '0') == '1':
        return
    logger.error(message)
    message += "\n\n    (To bypass build errors and force a build, set: {} = 1)".format(
        VAR_SKIP_MOONRAY_BUGS)
    raise MoonrayBuildError(message)


class MoonrayParm(object):

    __slots__ = [
        '_aliases',
        '_houdini_label',
        '_is_filepath',
        '_order',
        'bindable',
        'cast',
        'default_value',
        'disable_when',
        'display',
        'enable_if',
        'enclosing_folder_name',
        'fake_bind',
        'interface',
        'is_multiparm',
        'help',
        'houdini_name',
        'max',
        'menu',
        'menu_values',
        'min',
        'moonray_class',
        'moonray_name',
        'moonray_type',
        'ramp_is_color',
        'ramp_parm_name',
        'ramp_component',
        'subgroup',
        'tuple_size',
        'unrepresentableDefault',
    ]

    def __init__(self, moonray_class):
        self._aliases = []
        self._houdini_label = ''
        self._is_filepath = False
        self._order = -1
        self.bindable = False
        self.cast = str
        self.default_value = []
        self.disable_when = ''
        self.display = ''
        self.enable_if = ''
        self.enclosing_folder_name = ''
        self.fake_bind = False
        self.houdini_name = ''
        self.interface = None
        self.is_multiparm = False
        self.help = ''
        self.max = None
        self.menu = []
        self.menu_values = []
        self.min = None
        self.moonray_class = moonray_class
        self.moonray_name = ''
        self.moonray_type = ''
        self.ramp_is_color = False
        self.ramp_parm_name = None
        self.ramp_component = None
        self.subgroup = ''
        self.tuple_size = 0
        self.unrepresentableDefault = None

    @property
    def aliases(self):
        return self._aliases

    @aliases.setter
    def aliases(self, new_aliases):
        self._aliases = list(new_aliases)

    @property
    def bind_name(self):
        return self.houdini_name + BIND_SUFFIX

    @property
    def houdini_label(self):
        if self._houdini_label:
            return self._houdini_label
        if self.houdini_name == "auto_bump":
            return "Auto Bump (BROKEN: MOONRAY-3339)"
        return self._moonray_name_to_label(self.moonray_name)

    @property
    def is_filepath(self):
        return self._is_filepath

    @property
    def menu_default(self):
        idx = self.menu_values.index(str(self.default_value[0]))
        return self.menu[idx]

    @property
    def order(self):
        return self._order

    def _moonray_name_to_label(self, name):
        label = [word.title() if word and word[0].islower() else word
                 for word in name.split("_") if word]
        label = " ".join(label)
        if self.enclosing_folder_name and label.startswith(self.enclosing_folder_name + " "):
            label = label.replace(self.enclosing_folder_name + " ", "")
        return label

    def _multiparm_template(self, parm_template):
        parm_template.setName(parm_template.name() + "#")
        default_count = len(self.default_value)
        if self.unrepresentableDefault is not None:
            default_count = 0
        folder = hou.FolderParmTemplate(
            self.houdini_name,
            self.houdini_label,
            folder_type=hou.folderType.MultiparmBlock,
            default_value=default_count,
        )
        folder.setParmTemplates((parm_template,))
        return folder

    def _ramp_default_tag(self):
        lines = []
        ramp = self.get_ramp_default_value()
        if ramp is None:
            return ''
        if self.ramp_is_color:
            line = "{idx}pos ( {pos} ) {idx}c ( {r} {g} {b} ) {idx}interp ( {basis} )"
            for i in range(len(list(ramp.keys()))):
                pos = list(ramp.keys())[i]
                value = list(ramp.values())[i]
                basis = ramp.basis()[i].name().lower()
                lines.append(line.format(
                    idx=i + 1,
                    pos=pos,
                    r=value[0],
                    g=value[1],
                    b=value[2],
                    basis=basis,
                ))
        else:
            line = "{idx}pos ( {pos} ) {idx}value ( {val} ) {idx}interp ( {basis} )"
            for i in range(len(list(ramp.keys()))):
                pos = list(ramp.keys())[i]
                value = list(ramp.values())[i]
                basis = ramp.basis()[i].name().lower()
                lines.append(line.format(
                    idx=i + 1,
                    pos=pos,
                    val=value,
                    basis=basis,
                ))
        return " ".join(lines)

    def enable_if_to_disable_when(self, moonray_class):
        from collections import OrderedDict

        if not self.enable_if:
            return

        prefix = "OrderedDict("
        if not (self.enable_if.startswith(prefix) and self.enable_if.endswith(")")):
            raise ValueError("Bad Enable If: {0}".format(self.enable_if))

        import ast
        try:
            enable_if_items = ast.literal_eval(self.enable_if[len(prefix):-1])
            enable_if_dict = OrderedDict(enable_if_items)
        except Exception:
            raise ValueError("Bad Enable If: {0}".format(self.enable_if))
        if not isinstance(enable_if_dict, OrderedDict):
            raise ValueError("Bad Enable If: {0}".format(self.enable_if))

        disable_when = []
        for parm_name in enable_if_dict:
            value = enable_if_dict[parm_name]
            if value == 'true':
                value = 1
            elif value == 'false':
                value = 0
            target_parm = moonray_class.find_parameter(parm_name)
            if not target_parm:
                build_error(
                    "{0}'s attribute '{1}' references an invalid attribute '{2}' "
                    "in its enable if expression!".format(
                        moonray_class.moonray_name,
                        self.houdini_name,
                        parm_name,
                    )
                )
                return

            if target_parm.menu:
                value = str(value)
                if value in target_parm.menu:
                    pass
                elif value in target_parm.menu_values:
                    idx = target_parm.menu_values.index(str(value))
                    value = target_parm.menu[idx]
                else:
                    raise ValueError(
                        "{0} parm '{1}' should be disabled when '{2} != {3}' - "
                        "however, {2} is a menu and that is not a valid menu option!"
                        .format(
                            moonray_class.moonray_name,
                            self.houdini_name,
                            parm_name,
                            value,
                        )
                    )
                if " " in value:
                    value = '"{0}"'.format(value)

            disable_when.append("{{ {0} != {1} }}".format(parm_name, value))
        self.disable_when = " ".join(disable_when)

    @staticmethod
    def from_rdl2_json_exporter(name, data, moonray_class):
        parm = MoonrayParm(moonray_class)
        parm.moonray_name = name
        if " " in name:
            raise ValueError("SPACE IN NAME: {0}".format(name))

        parm._order = data['order']
        parm.moonray_type = str(data['attrType'])
        parm.cast, parm.tuple_size = ARRAY_TYPE_MAP.get(parm.moonray_type, (str, 0))
        parm.is_multiparm = parm.moonray_type in [
            FLOATVECTOR,
            INTVECTOR,
            RGBVECTOR,
            SCENEOBJECTVECTOR,
            STRINGVECTOR,
            VEC2FVECTOR,
            VEC3FVECTOR,
            VEC4FVECTOR,
        ]

        default = data['default']
        if default is None or parm.moonray_type in [SCENEOBJECT]:
            default = []
        elif parm.moonray_type in [INT, FLOAT, DOUBLE, BOOL, STRING]:
            default = [default]
        elif parm.is_multiparm:
            if any(default):
                parm.unrepresentableDefault = default
        elif parm.moonray_type == MAT4D:
            default = [item for sublist in default for item in sublist]

        if default and isinstance(default[0], float):
            for i in range(len(default)):
                default[i] = float("{0:.5f}".format(default[i]))
        parm.default_value = default
        parm.aliases = data.get("aliases", [])
        parm.bindable = data.get("bindable", False)
        parm.interface = data.get("interface")

        if moonray_class.houdini_context == 'Vop' and \
                parm.moonray_type == SCENEOBJECT and \
                parm.interface in (
                    MR_TYPE_LAYERABLE,
                    MR_TYPE_DISPLACEMENT,
                    MR_TYPE_HAIR_LAYERABLE,
                    MR_TYPE_MATERIAL,
                    MR_TYPE_DWA_BASE,
                    MR_TYPE_MAP,
                    MR_TYPE_NORMALMAP,
                    MR_TYPE_RENDER_OUTPUT,
                    MR_TYPE_VOLUME,
                ):
            parm.fake_bind = True

        parm._is_filepath = data.get("filename", False)

        if 'enum' in data:
            enum_dict = data['enum']
            labels = list(enum_dict.keys())
            labels.sort(key=lambda a: enum_dict[a])
            parm.menu = [str(label) for label in labels]
            parm.menu_values = [str(enum_dict[label]) for label in labels]

        meta = data.get("metadata", {})
        parm.houdini_name = data.get('houdini_name', parm.moonray_name)
        parm.help = meta.get("comment", "")
        enable_if = meta.get("enable if", '')
        parm.disable_when = meta.get('disable when', '').replace("'", '"')
        parm.subgroup = meta.get('subgroup', '')
        parm.display = meta.get("display")
        parm.ramp_is_color = meta.get('structure_type') == "ramp_color"
        parm.ramp_parm_name = meta.get('structure_name')
        parm.ramp_component = meta.get('structure_path')

        if parm.disable_when and enable_if:
            print("WARNING: '{0}' has an 'enable if' and a 'disable_when'! "
                  "Preferring the 'disable_when' field.".format(name))
        elif not parm.disable_when:
            parm.enable_if = enable_if

        if "min" in meta:
            value = str(meta["min"])
            if value[-1] == "f":
                value = float(value[:-1])
            elif "." in value:
                value = float(value)
            else:
                value = int(value)
            parm.min = value
        if "max" in meta:
            value = str(meta["max"])
            if value[-1] == "f":
                value = float(value[:-1])
            elif "." in value:
                value = float(value)
            else:
                value = int(value)
            parm.max = value

        label = meta.get("display name")
        if label and label[0].isupper():
            parm._houdini_label = label

        return parm

    def get_usd_type(self):
        if self.is_filepath:
            return Sdf.ValueTypeNames.Asset
        if self.menu or self.fake_bind:
            return Sdf.ValueTypeNames.Token
        if self.is_reference() and self.moonray_class.houdini_context == 'Vop':
            return Sdf.ValueTypeNames.Token
        return rdla_to_usd_type(self.moonray_type)

    def get_ramp_default_value(self):
        return self.get_ramp_default_value_from_name(self.moonray_class, self.ramp_parm_name)

    @staticmethod
    def get_ramp_default_value_from_name(moonray_class, ramp_parm_name):
        if not moonray_class or not ramp_parm_name:
            return None
        ramp_components = {}
        for parm in moonray_class.parms:
            name = parm.ramp_parm_name
            if name and name == ramp_parm_name:
                ramp_components[parm.ramp_component] = parm.default_value

        ramp_interps = dict([(value, key) for key, value in RAMP_INTERP_LOOKUP.items()])
        values = ramp_components[RAMP_COMPONENT_VALUES]
        pos = ramp_components[RAMP_COMPONENT_POSITIONS]
        interps = ramp_components[RAMP_COMPONENT_INTERPOLATIONS]
        interps = [ramp_interps[i] for i in interps]
        return hou.Ramp(interps, pos, values)

    def houdini_bind_type(self):
        if self.interface is None:
            interface = ''
        else:
            interface = str(self.interface)
        if interface == MR_TYPE_NORMALMAP:
            return "vector4"
        elif interface == MR_TYPE_VOLUME:
            return "volume"
        elif interface in (
                MR_TYPE_LAYERABLE,
                MR_TYPE_HAIR_LAYERABLE,
                MR_TYPE_MATERIAL,
                MR_TYPE_DWA_BASE):
            return "surface"
        elif interface == MR_TYPE_DISPLACEMENT:
            return "displacement"
        elif interface == MR_TYPE_RENDER_OUTPUT:
            return "struct_FuzzySet"
        elif interface == MR_TYPE_MAP:
            return "vector"
        if self.moonray_type in [VEC3F, VEC3D, VEC2F, RGB, MR_TYPE_NORMALMAP]:
            return "vector"
        if self.moonray_type in [VEC4F]:
            return "vector4"
        elif self.moonray_type in [FLOAT, DOUBLE]:
            return "float"
        elif self.moonray_type in [INT, BOOL]:
            return "int"
        elif self.moonray_type in [STRING, SCENEOBJECT]:
            return "string"
        elif self.moonray_type in [MAT4F, MAT4D]:
            return "matrix"
        return None

    def houdini_parm_template(self, int_menus=False, name_prefix="",
                              moonray_type=None, use_moonray_name=False,
                              alt_name=None, skip_multiparm=False):
        name = name_prefix + self.houdini_name
        if use_moonray_name:
            name = name_prefix + self.moonray_name
        elif alt_name:
            name = alt_name
        if not moonray_type:
            moonray_type = self.moonray_type

        if self.menu:
            if not int_menus:
                pt = hou.StringParmTemplate(
                    name,
                    self.houdini_label,
                    1,
                    default_value=(self.menu_default,),
                    help=self.help,
                    disable_when=self.disable_when,
                    tags=DEFAULT_MOONRAY_PARM_TAGS,
                )
                menu_labels = [label.title() if label.islower() else label
                               for label in self.menu]
                pt.setMenuItems(self.menu)
                pt.setMenuLabels(menu_labels)
                return pt
            else:
                def_value = str(self.default_value[0])
                default_idx = self.menu_values.index(def_value)
                pt = hou.IntParmTemplate(
                    name, self.houdini_label, 1,
                    default_value=[default_idx],
                    join_with_next=self.bindable,
                    help=self.help,
                    disable_when=self.disable_when,
                    min=self.min if self.min is not None else 0,
                    max=self.max if self.max is not None else 10,
                    tags=DEFAULT_MOONRAY_PARM_TAGS,
                )
                pt.setMenuItems(self.menu_values)
                pt.setMenuLabels(self.menu)
                return pt

        elif self.ramp_parm_name:
            if self.ramp_component and self.ramp_component != RAMP_COMPONENT_VALUES:
                return None
            label = self._moonray_name_to_label(self.ramp_parm_name)
            ramp_type = hou.rampParmType.Color if self.ramp_is_color else hou.rampParmType.Float
            pt = hou.RampParmTemplate(
                self.ramp_parm_name,
                label,
                ramp_type,
                default_value=len(self.default_value),
                disable_when=self.disable_when,
            )
            key = "rampcolordefault" if self.ramp_is_color else "rampfloatdefault"
            pt.setTags({
                key: self._ramp_default_tag(),
                TAG_IS_MOONRAY_PARM: "1",
            })
            return pt

        elif moonray_type in [INT, INTVECTOR]:
            pt = hou.IntParmTemplate(
                name, self.houdini_label, 1,
                default_value=self.default_value,
                help=self.help,
                disable_when=self.disable_when,
                min=self.min if self.min is not None else 0,
                max=self.max if self.max is not None else 10,
                tags=DEFAULT_MOONRAY_PARM_TAGS,
            )
            if self.display == DISPLAY_LOGARITHMIC:
                pt.setLook(hou.parmLook.Logarithmic)
            if self.is_multiparm:
                return self._multiparm_template(pt)
            return pt

        elif moonray_type in [FLOAT, DOUBLE, FLOATVECTOR]:
            look = hou.parmLook.Logarithmic if self.display == DISPLAY_LOGARITHMIC else hou.parmLook.Regular
            pt = hou.FloatParmTemplate(
                name,
                self.houdini_label,
                1,
                default_value=self.default_value[:1],
                help=self.help,
                disable_when=self.disable_when,
                min=self.min if self.min is not None else 0.0,
                max=self.max if self.max is not None else 10.0,
                tags=DEFAULT_MOONRAY_PARM_TAGS,
                look=look,
            )
            if self.is_multiparm:
                return self._multiparm_template(pt)
            return pt

        elif moonray_type in [VEC2F, VEC3F, VEC3D, MAT4D]:
            return hou.FloatParmTemplate(
                name,
                self.houdini_label,
                len(self.default_value),
                default_value=self.default_value,
                help=self.help,
                disable_when=self.disable_when,
                tags=DEFAULT_MOONRAY_PARM_TAGS,
            )

        elif moonray_type == BOOL:
            return hou.ToggleParmTemplate(
                name,
                self.houdini_label,
                bool(self.default_value[0]),
                help=self.help,
                disable_when=self.disable_when,
                tags=DEFAULT_MOONRAY_PARM_TAGS,
            )

        elif moonray_type in [RGB, RGBVECTOR]:
            if moonray_type == RGBVECTOR and self.default_value and isinstance(self.default_value[0], list):
                def_value = self.default_value[0]
            else:
                def_value = self.default_value
            if self.display == "tmi":
                parm_look = hou.parmLook.Regular
                naming_scheme = hou.parmNamingScheme.XYZW
            else:
                parm_look = hou.parmLook.ColorSquare
                naming_scheme = hou.parmNamingScheme.RGBA
            pt = hou.FloatParmTemplate(
                name,
                self.houdini_label,
                3,
                default_value=def_value,
                look=parm_look,
                naming_scheme=naming_scheme,
                help=self.help,
                disable_when=self.disable_when,
                tags=DEFAULT_MOONRAY_PARM_TAGS,
            )
            if self.is_multiparm:
                return self._multiparm_template(pt)
            return pt

        elif moonray_type in [STRING, STRINGVECTOR, SCENEOBJECT, SCENEOBJECTVECTOR]:
            if moonray_type in [SCENEOBJECT, SCENEOBJECTVECTOR]:
                str_type = hou.stringParmType.NodeReference
            elif self.is_filepath:
                str_type = hou.stringParmType.FileReference
            else:
                str_type = hou.stringParmType.Regular

            pt = hou.StringParmTemplate(
                name,
                self.houdini_label,
                1,
                string_type=str_type,
                default_value=self.default_value,
                help=self.help,
                disable_when=self.disable_when,
                is_hidden=self.fake_bind,
                tags=DEFAULT_MOONRAY_PARM_TAGS,
            )
            if self.is_multiparm and not skip_multiparm:
                return self._multiparm_template(pt)
            return pt

        print("\tWARNING: Unable to make Houdini Parm for {0} ({1})".format(
            self.houdini_name, moonray_type))
        return None

    def is_reference(self):
        is_scene_object = self.moonray_type in (
            SCENEOBJECT, SCENEOBJECTVECTOR, SCENEOBJECTINDEXABLE)
        return is_scene_object and not self.fake_bind

    def serialize(self):
        data = {
            'moonray_name': self.moonray_name,
            'moonray_type': self.moonray_type,
            'default_value': self.default_value,
            'houdini_name': self.houdini_name,
            'houdini_label': self.houdini_label,
            'order': self.order,
        }
        if self.interface:
            data['interface'] = self.interface
        if self.aliases:
            data['aliases'] = self.aliases
        if self.display:
            data['display'] = self.display
        if self.bindable:
            data['bindable'] = self.bindable
        if self.is_filepath:
            data['is_filepath'] = self.is_filepath
        if self.help:
            data['help'] = self.help
        if self.menu:
            data['menu'] = self.menu
            data['menu_values'] = self.menu_values
        if self.fake_bind:
            data['fake_bind'] = self.fake_bind
        if self.ramp_is_color:
            data['ramp_is_color'] = self.ramp_is_color
        if self.ramp_parm_name:
            data['ramp_parm_name'] = self.ramp_parm_name
        if self.ramp_component:
            data['ramp_parm_type'] = self.ramp_component
        return data


class MoonrayClass(object):

    __slots__ = [
        'parms', 'parms_dict', 'moonray_name', 'versionless_moonray_name',
        'version', 'moonray_type', 'folders_with_parms', 'folders_sorted',
        'houdini_context', 'houdini_name', '_hda',
    ]

    def __init__(self, name, mr_type):
        self._hda = None
        self.parms = []
        self.parms_dict = {}
        self.moonray_name = name
        self.versionless_moonray_name = re.sub(r'_v[0-9]*$', '', name)
        x = name.rfind('_v')
        self.version = int(name[x + 2:]) if x >= 0 else 1
        self.moonray_type = mr_type
        self.folders_with_parms = {}
        self.folders_sorted = []
        self.houdini_context = 'Vop' if mr_type in VOP_TYPES else 'Object'
        self.houdini_name = self.houdini_context + '::DW_MOONRAY::' + self.versionless_moonray_name + '::' + str(self.version)

    @property
    def hda(self):
        if self._hda:
            return self._hda
        category = hou.nodeTypeCategories()[self.houdini_context]
        nt = category.nodeType(self.houdini_name)
        if nt:
            return nt.definition()
        return None

    @hda.setter
    def hda(self, hda):
        self._hda = hda

    @property
    def icon_name(self):
        if self.versionless_moonray_name == 'AbcGeometry':
            return 'SOP_alembic'
        icons = {
            MR_TYPE_DISPLACEMENT: 'SOP_vdbfrompolygons',
            MR_TYPE_DISPLAY_FILTER: 'VOP_shadinglayer',
            MR_TYPE_MATERIAL: 'VIEW_materials',
            MR_TYPE_LIGHT_FILTER: 'SOP_cloudlight',
            MR_TYPE_LAYERABLE: 'VOP_raytrace',
            MR_TYPE_HAIR_LAYERABLE: 'VOP_pbrhair',
            MR_TYPE_MAP: 'NETWORKS_root',
            MR_TYPE_VOLUME: 'VOP_texture3d',
            MR_TYPE_NORMALMAP: 'SOP_normal',
            MR_TYPE_DWA_BASE: 'VIEW_materials',
        }
        return icons.get(self.moonray_type, 'DIALOG_question')

    @property
    def lop_hda(self):
        name = 'Lop::' + self.houdini_name.partition('::')[2]
        nt = hou.lopNodeTypeCategory().nodeType(name)
        if nt:
            return nt.definition()
        return None

    def add_parms_to_hda(self, verbose=True, hda=None):
        if not hda:
            hda = self.hda
        if not hda:
            return

        # Start with empty parm template group for fresh builds
        ptg = hou.ParmTemplateGroup()
        node_cat = hda.nodeTypeCategory()
        tab_categories = (hou.vopNodeTypeCategory(), hou.lopNodeTypeCategory())
        folder_type = hou.folderType.Tabs if node_cat in tab_categories else hou.folderType.Collapsible

        for folder_name in self.folders_sorted:
            if not ptg.findFolder(folder_name):
                folder = hou.FolderParmTemplate('folder', folder_name, folder_type=folder_type)
                ptg.append(folder)

        last_ungrouped_parm = None
        for parm in self.parms:
            name = parm.ramp_parm_name if parm.ramp_parm_name else parm.houdini_name
            if name in self.ignore_parm_names() or name == 'shadow_exclusion_mappings':
                continue
            folder_name = self.folder_name_for_parameter(parm)
            if node_cat == hou.vopNodeTypeCategory():
                parm.enclosing_folder_name = folder_name
            pt = parm.houdini_parm_template()
            if not pt:
                continue

            if verbose:
                print("\tADDING PARM: {0}".format(pt.name()))
                if pt.help():
                    print("\t\t{0}".format(pt.help()))

            if node_cat == hou.objNodeTypeCategory():
                if pt.name() in RENDER_PROPERTIES:
                    folder_name = 'Render Properties'
                elif not folder_name:
                    folder_name = self.versionless_moonray_name
                folder = ptg.findFolder(folder_name)
                if not folder:
                    folder = hou.FolderParmTemplate('folder', folder_name, folder_type=folder_type)
                    ptg.append(folder)
                ptg.appendToFolder(folder, pt)
            elif node_cat == hou.vopNodeTypeCategory():
                if folder_name:
                    if not parm.subgroup:
                        ptg.appendToFolder(folder_name, pt)
                    else:
                        subfolder_pt = None
                        subfolder_name = '_folder_' + parm.subgroup.replace(' ', '_')
                        for a_pt in ptg.findFolder(folder_name).parmTemplates():
                            if a_pt.name() == subfolder_name:
                                subfolder_pt = a_pt
                                break
                        if not subfolder_pt:
                            subfolder_pt = hou.FolderParmTemplate(
                                subfolder_name,
                                parm.subgroup,
                                folder_type=hou.folderType.Collapsible,
                            )
                            ptg.appendToFolder(folder_name, subfolder_pt)
                        ptg.appendToFolder(subfolder_pt, pt)
                else:
                    if last_ungrouped_parm:
                        ptg.insertAfter(last_ungrouped_parm, pt)
                    elif ptg.parmTemplates():
                        ptg.insertBefore(ptg.parmTemplates()[0].name(), pt)
                    else:
                        ptg.append(pt)
                    last_ungrouped_parm = pt.name()
            else:
                if not folder_name and self.folders_sorted and node_cat == hou.lopNodeTypeCategory():
                    folder_name = 'Other Settings'
                if folder_name:
                    folder = ptg.findFolder(folder_name)
                    if not folder:
                        folder = hou.FolderParmTemplate('folder', folder_name, folder_type=folder_type)
                        ptg.append(folder)
                    ptg.appendToFolder(folder, pt)
                else:
                    ptg.append(pt)

        hda.setParmTemplateGroup(ptg)
        self.configure_output_tag(hda)
        self.tag_ramp_parms(hda, verbose=verbose)
        if node_cat == hou.vopNodeTypeCategory() and hda.extraInfo() != '* moonray':
            hda.setExtraInfo('* moonray')

    def configure_output_tag(self, hda):
        if self.houdini_context != 'Vop':
            return
        outputs = HDAVopBuilder.OUTPUT_CONNECTIONS.get(self.moonray_type)
        ptg = hda.parmTemplateGroup()
        if not outputs:
            return
        name = outputs.split("\t")[2]
        if self.find_parameter(name):
            raise ValueError(
                "ERROR! {}: attribute name {} is same as the output name.".format(
                    self.moonray_name, name))
        output_tags = self.get_output_tag()
        if not output_tags:
            return

        pt = ptg.find(name)
        if pt:
            cur_tags = pt.tags()
            invalid_name = 'sidefx:shader_isparm'
            if invalid_name in cur_tags:
                del cur_tags[invalid_name]
            cur_tags.update(output_tags)
            if cur_tags != pt.tags():
                print("   Updating Output Tags! {} -> {}".format(pt.tags(), cur_tags))
                pt.setTags(cur_tags)
                ptg.replace(name, pt)
                hda.setParmTemplateGroup(ptg)
        else:
            pt = hou.IntParmTemplate(
                name, name, 1,
                is_hidden=True,
                is_label_hidden=True,
                tags=output_tags,
            )
            ptg.addParmTemplate(pt)
            hda.setParmTemplateGroup(ptg)

    def find_parameter(self, parm_name):
        return self.parms_dict.get(parm_name)

    def folder_name_for_parameter(self, parm):
        for folder_name, parm_names in self.folders_with_parms.items():
            if parm.moonray_name in parm_names or (
                    parm.ramp_parm_name and parm.ramp_parm_name in parm_names):
                return folder_name
        return None

    @staticmethod
    def from_rdl2_json_exporter(name, data):
        node = MoonrayClass(name, data['type'])
        attributes = data.get('attributes')
        if attributes:
            for parm_name, parm_data in attributes.items():
                parm = MoonrayParm.from_rdl2_json_exporter(parm_name, parm_data, node)
                if parm.houdini_name == 'node_xform' and parm.moonray_type == MAT4D:
                    continue
                node.parms.append(parm)
            node.parms.sort(key=lambda a: a.order)
            node.rebuild_parm_dict()
            for parm in node.parms:
                parm.enable_if_to_disable_when(node)
            for parm in node.parms:
                if parm.ramp_parm_name:
                    parm.get_ramp_default_value()

        grouping = data.get('grouping')
        if grouping:
            node.folders_sorted = grouping['order']
            node.folders_with_parms = grouping['groups']
        return node

    def get_output_tag(self):
        shader = Sdr.Registry().GetShaderNodeByName(self.moonray_name)
        if shader and shader.GetOutputNames():
            outputname = shader.GetOutputNames()[0]
            output = shader.GetShaderOutput(outputname)
            outputtype = str(output.GetTypeAsSdfType()[0])
        elif self.moonray_type in HDAVopBuilder.OUTPUT_TAG_TYPE:
            outputname, outputtype = HDAVopBuilder.OUTPUT_TAG_TYPE[self.moonray_type]
        else:
            return {}
        return {
            'sidefx::shader_parmname': outputname,
            'sidefx::shader_parmtype': outputtype,
            TAG_SHADER_IS_PARM: '0',
        }

    def ignore_parm_names(self):
        black_list = {
            'Object::DW_MOONRAY::InstanceGeometry::1':
                ['positions', 'orientations', 'scales', 'velocities', 'xform_list'],
        }
        result = black_list.get(self.houdini_name, [])
        if self.moonray_type == MR_TYPE_GEOMETRY:
            result = list(result) + ['primitive_attributes', 'part_list', 'static']
            if self.moonray_name != 'InstanceGeometry':
                result.append('references')
        if self.versionless_moonray_name.endswith('Geometry'):
            result.extend(['shadow_group', 'shadow_group_mode'])
        if self.versionless_moonray_name.endswith('Material'):
            result.extend(['diffuse_lightset', 'specular_lightset'])
        return result

    def rebuild_parm_dict(self):
        self.parms_dict.clear()
        for parm in self.parms:
            self.parms_dict[parm.houdini_name] = parm
            self.parms_dict[parm.moonray_name] = parm
            for alias in parm.aliases:
                self.parms_dict[alias] = parm

    def serialize(self):
        parms = {}
        for parm in self.parms:
            parms[parm.moonray_name] = parm.serialize()
        return {
            'moonray_name': self.moonray_name,
            'moonray_type': self.moonray_type,
            'parms': parms,
            'folders_sorted': self.folders_sorted,
            'folders_with_parms': self.folders_with_parms,
        }

    def set_tab_menu(self, menu='DW Moonray'):
        return None

    def tag_ramp_parms(self, hda, verbose):
        if self.houdini_context != 'Vop':
            return
        ramp_parms = [p for p in self.parms if p.ramp_parm_name]
        if not ramp_parms:
            return
        ptg = hda.parmTemplateGroup()
        tag_map = {
            'interpolation_types': 'rampbasis_var',
            'positions': 'rampkeys_var',
            'values': 'rampvalues_var',
        }
        for ramp_parm in ramp_parms:
            pt_name = ramp_parm.ramp_parm_name
            pt = ptg.find(pt_name)
            if not pt:
                continue
            cur_tags = pt.tags()
            tag_name = tag_map.get(ramp_parm.ramp_component)
            cur_tags.update({tag_name: ramp_parm.moonray_name})
            if cur_tags != pt.tags():
                if verbose:
                    print("   Updating Ramp Tags! {} -> {}".format(pt.tags(), cur_tags))
                pt.setTags(cur_tags)
                ptg.replace(pt_name, pt)
                hda.setParmTemplateGroup(ptg)


class HDABuilder(object):

    _houdini_create_bindings = {
        MR_TYPE_DISPLACEMENT: ("/mat", "subnet"),
        MR_TYPE_DISPLAY_FILTER: ("/mat", "subnet"),
        MR_TYPE_LIGHT_FILTER: ("/obj", "subnet"),
        MR_TYPE_MAP: ("/mat", "subnet"),
        MR_TYPE_LAYERABLE: ("/mat", "subnet"),
        MR_TYPE_HAIR_LAYERABLE: ("/mat", "subnet"),
        MR_TYPE_MATERIAL: ("/mat", "subnet"),
        MR_TYPE_DWA_BASE: ("/mat", "subnet"),
        MR_TYPE_NORMALMAP: ("/mat", "subnet"),
        MR_TYPE_VOLUME: ("/mat", "subnet"),
    }

    def __init__(self, hda, moonray_class):
        self._hda = hda
        self._moonray_class = moonray_class

    @property
    def hda(self):
        return self._hda

    @property
    def moonray_class(self):
        return self._moonray_class

    def _add_houdini_event_script(self, script_name, method_name, pass_kwargs=False):
        code = "kwargs['node'].hm().wrapper(kwargs['node']).{}({})".format(
            method_name, 'kwargs' if pass_kwargs else '')
        section = self.hda.sections().get(script_name)
        if not section:
            print("    Adding {0} Script".format(script_name))
            self.hda.addSection(script_name, code)
            self.hda.setExtraFileOption('{0}/IsPython'.format(script_name), True)
        elif section.contents() != code and self.moonray_class.moonray_name not in IGNORE_CODE_MISMATCHES:
            print("    Script code mis-match! {0}".format(script_name))

    def _add_python_module(self):
        if self.moonray_class.moonray_name in IGNORE_CODE_MISMATCHES:
            return
        if not self.hda.sections().get('PythonModule'):
            code = self._default_python_module()
            if not code:
                return
            self.hda.addSection('PythonModule', code)
            self.hda.setExtraFileOption('PythonModule/IsPython', True)
        else:
            cur_code = self.hda.sections().get('PythonModule').contents()
            code = self._default_python_module()
            if cur_code != code:
                print('   PythonModule != default script!!')

    def _default_python_module(self):
        # The internal build gave each node category a python module providing a
        # wrapper object that implemented on_create/on_input_changed/etc. None of
        # those modules were open sourced, so every branch here collapsed to the
        # same stub whose wrapper() returns None. Installing the event handlers
        # against that stub makes every node raise
        #   AttributeError: 'NoneType' object has no attribute 'on_create'
        # as soon as it is created. All 125 HDAs shipped in moonray_dcc_plugins
        # carry no PythonModule, OnCreated or OnInputChanged section at all, so
        # emit nothing and match them. An internal fork that restores a real
        # module here gets every event handler back automatically.
        return None

    @classmethod
    def can_create_hda(cls, moonray_class):
        return moonray_class.moonray_type in cls._houdini_create_bindings

    def add_python_scripts(self):
        if not self._default_python_module():
            return
        self._add_python_module()
        self._add_houdini_event_script('OnCreated', 'on_create')

    def cleanup_hda(self):
        self.update_url()

    @classmethod
    def create_hda(cls, moonray_class, directory):
        if not cls.can_create_hda(moonray_class):
            print("WARNING: Cannot create HDA for Node Type '{0}'".format(
                moonray_class.moonray_type))
            return None

        ensure_directory(directory)
        file_path = os.path.join(directory, moonray_class.houdini_name + '.hda')
        label = 'Moonray {0}'.format(moonray_class.versionless_moonray_name)
        parent_path, base = cls._houdini_create_bindings[moonray_class.moonray_type]
        parent_node = hou.node(parent_path)
        if parent_node is None:
            raise MoonrayBuildError(
                "Houdini network '{0}' does not exist in this session, so the HDA for "
                "'{1}' cannot be built. Run under hython with a default scene.".format(
                    parent_path, moonray_class.moonray_name))
        hda_source = parent_node.createNode(base)
        node = None
        try:
            node = hda_source.createDigitalAsset(
                name=moonray_class.houdini_name,
                description=label,
                hda_file_name=file_path,
            )
            hda = node.type().definition()
            hda.updateFromNode(node)
            if moonray_class.houdini_context == 'Object':
                hda.setMaxNumInputs(1)
            node.matchCurrentDefinition()
        except Exception:
            logger.exception("Failed to create HDA %s", moonray_class.houdini_name)
            raise MoonrayBuildError(
                "Failed to create HDA for '{0}'".format(moonray_class.moonray_name)
            )
        finally:
            # createDigitalAsset replaces hda_source with an instance of the new
            # asset type, so node and hda_source can name the same underlying
            # node. Destroying one then the other would raise from inside the
            # finally and mask the real result, so guard both.
            for leftover in (node, hda_source):
                if leftover is None:
                    continue
                try:
                    leftover.destroy()
                except Exception:
                    pass

        moonray_class.hda = hda
        hda.setIcon(moonray_class.icon_name)
        moonray_class.set_tab_menu()
        moonray_class.add_parms_to_hda()
        return hda

    def set_houdini_parm_names(self):
        """Set houdini_name to moonray_name for all parms (fresh build)."""
        for parm in self.moonray_class.parms:
            parm.houdini_name = parm.moonray_name
        self.moonray_class.rebuild_parm_dict()
        self.validate_disable_when()

    def update_url(self):
        if not HELP_URL:
            return
        section_name = 'HelpUrl'
        if not self.hda.sections().get(section_name):
            self.hda.addSection(section_name, HELP_URL)

    def validate_disable_when(self):
        no_changes = True
        for parm in self.moonray_class.parms:
            exp = parm.disable_when
            if not exp:
                continue
            conditions = []
            for condition in exp.split('}'):
                if not condition:
                    continue
                bits = condition.split()
                if len(bits) < 4:
                    continue
                var = bits[1]
                conditional = bits[2]
                value = ' '.join(bits[3:])
                conditional_parm = None
                for moonray_parm in self.moonray_class.parms:
                    if moonray_parm.moonray_name == var:
                        conditional_parm = moonray_parm
                        break
                if not conditional_parm:
                    raise ValueError(
                        "{0} -- Invalid variable '{1}' in 'disable when' expression: {2}".format(
                            self.moonray_class.moonray_name, var, exp))
                conditions.append("{{ {0} {1} {2} }}".format(var, conditional, value))
            new_exp = ' '.join(conditions)
            if conditions:
                parm.disable_when = new_exp
            if exp != new_exp:
                no_changes = False
                parm.disable_when = new_exp
        return no_changes


class HDAVopBuilder(HDABuilder):

    OUTPUT_CONNECTIONS = {
        MR_TYPE_MATERIAL: "    output\tsurface\tsurface\tMaterial",
        MR_TYPE_DWA_BASE: "    output\tsurface\tsurface\tDwaBase",
        MR_TYPE_LAYERABLE: "    output\tsurface\tsurface\tDwaBaseLayerable",
        MR_TYPE_HAIR_LAYERABLE: "    output\tsurface\tsurface\tDwaBaseHairLayerable",
        MR_TYPE_NORMALMAP: "    output\tvector4\tnormalmap\tNormalMap",
        MR_TYPE_MAP: "    output\tvector\tmap\tMap",
        MR_TYPE_DISPLACEMENT: "    output\tdisplacement\tdisplacement\tDisplacement",
        MR_TYPE_VOLUME: "    output\tvolume\tvolume\tVolume",
        MR_TYPE_DISPLAY_FILTER: "    output\tstruct_FuzzySet\tdisplayfilter\tDisplayFilter",
    }

    OUTPUT_TAG_TYPE = {
        MR_TYPE_DISPLACEMENT: ('out', 'float3'),
        MR_TYPE_MAP: ('out', 'float3'),
        MR_TYPE_NORMALMAP: ('out', 'float3'),
        MR_TYPE_MATERIAL: ('out', 'token'),
        MR_TYPE_VOLUME: ('out', 'token'),
        MR_TYPE_DWA_BASE: ('out', 'token'),
    }

    def _does_parm_need_input(self, mr_parm):
        return not mr_parm.is_multiparm

    def _generate_header(self):
        return [
            '# Dialog script for {0} automatically generated'.format(self.hda.nodeTypeName()),
            '',
            '{',
            '    name\t' + self.hda.nodeTypeName(),
            '    script\t' + self.moonray_class.moonray_name,
            '    label\t"{0}"'.format(self.hda.description()),
            '',
            '    rendermask\tmoonray',
            '    externalshader 1',
            '    shadertype\tgeneric',
        ]

    def add_python_scripts(self):
        super(HDAVopBuilder, self).add_python_scripts()
        # Same guard as the base class: without a python module to call into,
        # these handlers would only raise on every node.
        if not self._default_python_module():
            return
        self._add_houdini_event_script('OnInputChanged', 'on_input_changed', pass_kwargs=True)
        if self.moonray_class.moonray_type == MR_TYPE_DISPLAY_FILTER:
            self._add_houdini_event_script('OnLoaded', 'on_loaded')
            self._add_houdini_event_script('OnDeleted', 'on_deleted')
            self._add_houdini_event_script('OnNameChanged', 'on_name_changed')

    def cleanup_hda(self):
        super(HDAVopBuilder, self).cleanup_hda()
        self.fix_disable_when()
        self.update_parameter_inputs()
        self.update_output_connections()

    def deprecate_unused_inputs(self, dialog_script):
        header, inputs, outputs, inputflags, signature, tail = self.parse_dialog_script(dialog_script)
        new_inputs = []
        mr_parm_names = [p.houdini_name for p in self.moonray_class.parms if self._does_parm_need_input(p)]
        for i, input_line in enumerate(inputs):
            line_name = input_line.split()[2]
            if line_name not in mr_parm_names and not line_name.startswith(DEPRECATED_PREFIX):
                input_type = input_line.split()[1]
                new_name = '{0}{1}'.format(DEPRECATED_PREFIX, line_name)
                input_line = '\tinput\t{type}\t{name}\t"{label}"'.format(
                    type=input_type,
                    name=new_name,
                    label=new_name,
                )
                inputflags[i] = '\tinputflags\t{0}\t0'.format(new_name)
            new_inputs.append(input_line)
        return '\n'.join(header + new_inputs + outputs + inputflags + signature + tail)

    def fix_disable_when(self):
        broken_parms = []
        for parm in self.moonray_class.parms:
            if parm.disable_when and '"' in parm.disable_when:
                broken_parms.append(parm)
        if not broken_parms:
            return

        dialog_script = self.hda.sections()['DialogScript']
        dialog_contents = dialog_script.contents()
        header, inputs, outputs, inputflags, signature, tail = self.parse_dialog_script(dialog_contents)
        new_tail = tail[:]
        for parm in broken_parms:
            start_line = 'name    "{0}"'.format(parm.houdini_name)
            found_start = False
            for i, line in enumerate(tail):
                if not found_start:
                    if line.strip() == start_line:
                        found_start = True
                else:
                    if line.strip() == '}':
                        raise ValueError('Missing disablewhen!!')
                    elif line.strip().startswith('disablewhen'):
                        prefix = line.split('disablewhen', 1)[0]
                        new_tail[i] = '{0}disablewhen "{1}"'.format(
                            prefix, parm.disable_when.replace('"', '\\"'))
                        break
        dialog_contents = '\n'.join(header + inputs + outputs + inputflags + signature + new_tail)
        if dialog_script.contents().strip() != dialog_contents.strip():
            dialog_script.setContents(dialog_contents)

    def parse_dialog_script(self, contents):
        header = []
        inputs = []
        outputs = []
        inputflags = []
        signature = []
        tail = []

        lines = contents.splitlines()
        finish = False
        is_header = True
        for line in lines:
            first = line.split()[0] if line else ''
            if is_header:
                if first in ('input', 'output', 'inputflags', 'signature'):
                    is_header = False
                else:
                    header.append(line)
                    continue
            if finish:
                tail.append(line)
                continue
            if first == 'input':
                inputs.append(line)
            elif first == 'output':
                outputs.append(line)
            elif first == 'inputflags':
                inputflags.append(line)
            elif first == 'signature':
                signature.append(line)
                finish = True

        clean_inputs = []
        stripped_inputs = []
        for line in inputs:
            if line.split()[:3] in stripped_inputs:
                continue
            stripped_inputs.append(line.split()[:3])
            line = line.replace('\tbsdf', '\tsurface').replace('\tint ', '\tdisplacement ')
            line = line.replace('_bind', '')
            clean_inputs.append(line)

        clean_inputflags = []
        stripped_inputs = []
        for line in inputflags:
            if line.split()[:3] in stripped_inputs:
                continue
            stripped_inputs.append(line.split()[:3])
            clean_inputflags.append(line)

        header = self._generate_header()
        return header, clean_inputs, outputs, clean_inputflags, signature, tail

    def update_parameter_inputs(self):
        dialog_script = self.hda.sections()['DialogScript']
        dialog_contents = dialog_script.contents()
        dialog_contents = self.deprecate_unused_inputs(dialog_contents)
        for parm in self.moonray_class.parms:
            dialog_contents = self.update_dialog_script(parm, dialog_contents)
        if dialog_contents.strip().split() != dialog_script.contents().strip().split():
            dialog_script.setContents(dialog_contents)
        if not self.validate_parameter_inputs():
            raise OSError('Something went wrong with the vop inputs!')

    def update_output_connections(self):
        dialog_script = self.hda.sections()['DialogScript']
        dialog_contents = self.deprecate_unused_inputs(dialog_script.contents())
        if not dialog_contents:
            return
        header, inputs, outputs, inputflags, signature, tail = self.parse_dialog_script(dialog_contents)
        outputs = [self.OUTPUT_CONNECTIONS[self.moonray_class.moonray_type]]
        # The signature has to cover the outputs as well as the inputs, and
        # every type past the input count needs a matching default in the
        # outputoverrides block, or Houdini rejects the whole DialogScript with
        # "Expected more data for signature" and the node loads with no
        # parameters at all. update_dialog_script built the signature before
        # the outputs existed, so finish it here.
        signature = [self.build_signature_line(inputs, outputs)]
        tail = self.set_output_overrides(tail, outputs)
        dialog_contents = '\n'.join(header + inputs + outputs + inputflags + signature + tail)
        if dialog_script.contents().strip().split() != dialog_contents.strip().split():
            dialog_script.setContents(dialog_contents)

    @staticmethod
    def build_signature_line(inputs, outputs):
        types = ''.join(entry.split()[1] + ' ' for entry in (inputs + outputs))
        return '\tsignature\t"Default Inputs"\tdefault\t{ ' + types + '}'

    # Placeholder defaults for an output connector, by its VEX type. The value
    # is not meaningful (the entry is declared "auto"), but the shape has to
    # look like the type.
    OUTPUT_OVERRIDE_DEFAULTS = {
        'vector': '(0,0,0)',
        'vector4': '(0,0,0,0)',
        'displacement': '(0,0,0)',
    }

    @classmethod
    def set_output_overrides(cls, tail, outputs):
        entries = []
        for entry in outputs:
            default = cls.OUTPUT_OVERRIDE_DEFAULTS.get(entry.split()[1], '(0)')
            entries.append('\t___begin\tauto')
            entries.append('\t\t\t{0}'.format(default))

        new_tail = []
        i = 0
        while i < len(tail):
            line = tail[i]
            new_tail.append(line)
            if line.split()[:1] != ['outputoverrides']:
                i += 1
                continue
            # Copy the opening brace, replace the body, keep the closing brace.
            i += 1
            while i < len(tail) and tail[i].strip() != '{':
                new_tail.append(tail[i])
                i += 1
            if i >= len(tail):
                break
            new_tail.append(tail[i])
            i += 1
            depth = 1
            while i < len(tail) and depth:
                if tail[i].strip() == '}':
                    depth -= 1
                    if not depth:
                        new_tail.extend(entries)
                        new_tail.append(tail[i])
                i += 1
        return new_tail

    def update_dialog_script(self, parm, dialog_script):
        if not self._does_parm_need_input(parm):
            return dialog_script
        header, inputs, outputs, inputflags, signature, tail = self.parse_dialog_script(dialog_script)
        bind_type = parm.houdini_bind_type()
        if not bind_type:
            raise ValueError(
                "Unbindable Parameter Type: {0} {1} on {2}. This rdl2 type has no "
                "Houdini VOP equivalent to bind an input to. Either give the shader "
                "a representable type, or exclude the shader by adding it to "
                "UpdateHDAs.BLOCK_TYPES.".format(
                    parm.houdini_name, parm.moonray_type,
                    self.moonray_class.moonray_name))
        label_more_than_one_word = ' ' in parm.houdini_label
        line = '\tinput\t{type}\t{name}\t{quote}{label}{quote}'.format(
            type=bind_type,
            name=parm.houdini_name,
            label=parm.houdini_label,
            quote='"' if label_more_than_one_word else '',
        )
        is_invisible = '0'
        if not parm.bindable and not parm.fake_bind:
            is_invisible = '1'
        flag_line = '\tinputflags\t{0}\t{1}'.format(parm.houdini_name, is_invisible)

        new_inputs = []
        added_line = False
        for input_line in inputs:
            line_name = input_line.split()[2]
            if line_name == parm.houdini_name:
                added_line = True
                input_line = line
            new_inputs.append(input_line)

        if not added_line:
            for i, input_line in enumerate(inputs):
                line_name = input_line.split()[2]
                if line_name.startswith(DEPRECATED_PREFIX):
                    inputflag_name = inputflags[i].split()[1]
                    if inputflag_name != line_name:
                        raise IndexError('Corrupt Dialog Script -- Index mismatch for {0}'.format(line_name))
                    inputflags[i] = flag_line
                    new_inputs[i] = line
                    added_line = True
                    break

        if not added_line:
            new_inputs.append(line)
        inputs = new_inputs

        stripped_inputs = [l.split()[:3] for l in inputflags]
        if flag_line.split()[:3] not in stripped_inputs:
            inputflags.append(flag_line)

        signature = [self.build_signature_line(inputs, outputs)]
        return '\n'.join(header + inputs + outputs + inputflags + signature + tail)

    def validate_parameter_inputs(self):
        dialog_script = self.hda.sections()['DialogScript']
        dialog_contents = self.deprecate_unused_inputs(dialog_script.contents())
        parm_lines = self.parse_dialog_script(dialog_contents)[1]
        input_names = [line.split()[2] for line in parm_lines]
        valid = True
        for mr_parm in self.moonray_class.parms:
            if not self._does_parm_need_input(mr_parm):
                continue
            name = mr_parm.houdini_name
            if name not in input_names:
                valid = False
                print('Missing Input: {0}'.format(name))
                continue
            input_names.remove(name)
        if input_names:
            for name in input_names:
                if name.startswith(DEPRECATED_PREFIX) or not name.endswith(BIND_SUFFIX):
                    continue
                valid = False
                print('Unused Input: {0}'.format(name))
        return valid


def get_hda_builder(moonray_class, hda=None):
    if not hda:
        hda = moonray_class.hda
    if moonray_class.houdini_context == 'Vop':
        return HDAVopBuilder(hda, moonray_class)
    return HDABuilder(hda, moonray_class)


class UpdateHDAs(object):

    export_metadata = {}

    # Classes deliberately excluded from every output. These are MoonRay's
    # implementations of shaders that USD already defines, so Houdini/Solaris
    # supplies the authoring node natively; generating DW_MOONRAY duplicates
    # would give artists two nodes for the same UsdShade prim. Filtering
    # happens at ingest, so a name listed here is absent from the HDAs,
    # moonray_nodes.json and the .ds files alike.
    BLOCK_TYPES = [
        'UsdPreviewSurface',
        'UsdPrimvarReader_float',
        'UsdPrimvarReader_float2',
        'UsdPrimvarReader_float3',
        'UsdPrimvarReader_int',
        'UsdPrimvarReader_normal',
        'UsdPrimvarReader_point',
        'UsdPrimvarReader_vector',
        'UsdUVTexture',
        'UsdTransform2d',
    ]

    # Unit test DSOs. These ship in moonray's rdl2dso directory but are
    # fixtures for the shader test suite, not shaders anyone renders with.
    # TestInputs* in particular declare a parameter of every rdl2 type,
    # including Mat3f and Mat4f, which have no Houdini equivalent to bind to.
    BLOCK_PREFIXES = ('Test',)

    @classmethod
    def is_blocked(cls, class_name):
        return (class_name in cls.BLOCK_TYPES
                or class_name.startswith(cls.BLOCK_PREFIXES))

    SKIP_TYPES = [
        'ShadowSet',
        'LightFilterSet',
        'GeometrySet',
        'LayerSet',
        'LightSet',
        'Layer',
        'Metadata',
        'RenderOutput',
        'UserData',
        'TraceSet',
        'Joint',
        'SceneVariables',
        'UsdGeometry',
        'UsdInstanceGeometry',
    ] + BLOCK_TYPES

    def __init__(self, moonshine_packages, destination_directory):
        self.destination_directory = destination_directory
        self.destination_hda_directory = os.path.join(destination_directory, 'otls')
        self.destination_json = os.path.join(destination_directory, MOONSHINE_DATA_FILE)
        ensure_directory(self.destination_hda_directory)
        self.moonray_classes = self.moonray_classes_from_rdl(moonshine_packages)
        self.node_dict = self.get_moonshine_package_versions()

    def get_moonshine_package_versions(self):
        """Build the 'packages' block of moonray_nodes.json.

        The exporter embeds its own version strings (--rdl2_version /
        --moonray_version), so use those when present.
        """
        pkg_versions = {}
        exported = getattr(type(self), 'export_metadata', {}) or {}
        for key, pkg in (('moonray version', 'moonray'),
                         ('scene_rdl2_version', 'scene_rdl2')):
            version = exported.get(key)
            if version and version != 'unspecified':
                pkg_versions['{0}_folio'.format(pkg)] = '{0}-{1}'.format(pkg, version)

        return {'packages': pkg_versions}

    @classmethod
    def moonray_classes_from_rdl(cls, moonshine_packages):
        result = []
        data = cls._export_scene_classes()
        cls.export_metadata = {
            key: value for key, value in data.items() if key != 'scene_classes'
        }
        for node_name, node_data in data['scene_classes'].items():
            if cls.is_blocked(node_name):
                continue
            result.append(MoonrayClass.from_rdl2_json_exporter(node_name, node_data))
        result.sort(key=lambda a: a.moonray_name)
        return result

    @classmethod
    def _export_scene_classes(cls):
        """Return the rdl2_json_exporter document describing every scene class.

        Reading a previously exported file is preferred when running inside a
        DCC. Moonshine's USD build and Houdini's own USD cannot be loaded into
        one process, so exporting up front in a plain shell and passing the
        result in keeps the two apart. See --classes-json.
        """
        classes_json = os.environ.get(VAR_CLASSES_JSON)
        if classes_json:
            print('Reading scene classes from {0}'.format(classes_json))
            with open(classes_json) as file_pointer:
                return json.load(file_pointer)

        env = os.environ.copy()
        # rdl2_json_exporter with no --out streams every scene class (built-ins
        # plus everything on RDL2_DSO_PATH) to stdout as a single JSON doc.
        exporter = os.environ.get('RDL2_JSON_EXPORTER', 'rdl2_json_exporter')
        command = [exporter]
        if not env.get('RDL2_DSO_PATH'):
            raise ValueError(
                'RDL2_DSO_PATH is not set. Source <install>/scripts/setup.sh, or point '
                'it at <install>/rdl2dso.proxy before running. Alternatively export the '
                'scene classes separately and pass them with --classes-json.')
        print('=' * 80)
        print(' '.join(command))
        print('  RDL2_DSO_PATH={0}'.format(env['RDL2_DSO_PATH']))
        print('=' * 80)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        output, err = process.communicate()
        output = _decode(output)
        err = _decode(err)
        if process.returncode != 0:
            raise ValueError('Something went wrong finding the moonshine package: {0}'.format(err))
        return json.loads(output)

    def main(self):
        self.update_hdas()
        self.save_node_dict()
        self.remove_hda_backups()

    def remove_hda_backups(self):
        # Houdini drops a numbered copy into <otls>/backup every time an HDA is
        # saved, and each asset is saved several times while it is built. That
        # leaves close to a thousand files nobody wants, and they would be
        # copied straight into moonray_dcc_plugins along with the assets.
        backup_dir = os.path.join(self.destination_hda_directory, 'backup')
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)
            print('Removed intermediate HDA backups: {0}'.format(backup_dir))

    def update_hdas(self):
        for moonray_class in self.moonray_classes:
            if moonray_class.houdini_context != 'Vop':
                continue
            if moonray_class.moonray_name in self.SKIP_TYPES:
                continue
            if not HDABuilder.can_create_hda(moonray_class):
                print('{0}\n\tUnable to create operator type {1}'.format(
                    moonray_class.houdini_name, moonray_class.moonray_type))
                continue

            print('{0}\n\tNew Operator!'.format(moonray_class.houdini_name))
            HDABuilder.create_hda(moonray_class, self.destination_hda_directory)
            builder = get_hda_builder(moonray_class)
            builder.add_python_scripts()
            builder.set_houdini_parm_names()
            if not builder.validate_disable_when():
                moonray_class.add_parms_to_hda(verbose=False)
            builder.cleanup_hda()

    def save_node_dict(self):
        for moonray_class in self.moonray_classes:
            self.node_dict[moonray_class.moonray_name] = moonray_class.serialize()
        print('Writing JSON: {0}'.format(self.destination_json))
        with open(self.destination_json, 'w') as file_pointer:
            json.dump(self.node_dict, file_pointer, indent=4)


def is_numerical_type(moonray_type):
    prefixes = ['Float', 'Double', 'Int', 'Mat', 'Rgb', 'Vec']
    for prefix in prefixes:
        if moonray_type.startswith(prefix):
            return True
    return False


def create_control_menu(moonray_type):
    menu = ['set', 'setexisting']
    labels = [
        '![BUTTONS_set_or_create]Set or Create',
        '![BUTTONS_set_if_exists]Set if Exists',
    ]
    if is_numerical_type(moonray_type):
        menu.extend(['add', 'multiply'])
        labels.extend([
            '![BUTTONS_set_add]Add if Exists',
            '![BUTTONS_set_multiply]Multiply if Exists',
        ])
    menu.extend(['block', 'none'])
    labels.extend(['![BUTTONS_set_block]Block', '![BUTTONS_set_nothing]Do Nothing'])
    return menu, labels


class LopDialogScriptBuilder(object):
    _usd_prim_type_attr = None

    def __init__(self, dest_dir, moonray_classes):
        self.dest_dir = dest_dir
        self.moonraylights = []
        self.moonray_classes = moonray_classes
        self.shader_class = {}
        self.light_class = {}
        self.lf_class = {}
        self.geometry_class = {}
        self.cam_class = {}
        for moonray_class in self.moonray_classes:
            name = moonray_class.moonray_name
            moonray_type = moonray_class.moonray_type
            if moonray_type == 'Light':
                self.light_class[name] = moonray_class
            elif moonray_type == 'LightFilter':
                self.lf_class[name] = moonray_class
            elif moonray_type == 'Geometry':
                self.geometry_class[name] = moonray_class
            elif moonray_type.endswith('Map'):
                self.shader_class[name] = moonray_class
            elif moonray_type.endswith('Layerable'):
                self.shader_class[name] = moonray_class
            elif moonray_type in ['Displacement', 'Material', 'Volume']:
                self.shader_class[name] = moonray_class
            elif moonray_type == 'Camera':
                self.cam_class[name] = moonray_class

    @property
    def usd_prim_type_attr(self):
        if LopDialogScriptBuilder._usd_prim_type_attr is None:
            LopDialogScriptBuilder._usd_prim_type_attr = {
                'CylinderLight': UsdLux.CylinderLight.GetSchemaAttributeNames(),
                'DiskLight': UsdLux.DiskLight.GetSchemaAttributeNames(),
                'DistantLight': UsdLux.DistantLight.GetSchemaAttributeNames(),
                'EnvLight': UsdLux.DomeLight.GetSchemaAttributeNames(),
                'RectLight': UsdLux.RectLight.GetSchemaAttributeNames(),
                'SphereLight': UsdLux.SphereLight.GetSchemaAttributeNames(),
                'MeshLight': UsdLux.GeometryLight.GetSchemaAttributeNames(),
                'SpotLight': UsdLux.DiskLight.GetSchemaAttributeNames(),
            }
        return LopDialogScriptBuilder._usd_prim_type_attr

    def __add_light_type_parm(self, group):
        parm_name = 'class'
        hide_when = ''
        prefix = 'moonray:'
        moonray_type = 'String'
        control_pt = self.__create_control_parm(parm_name, prefix, hide_when, moonray_type,
                                                default_value='set', is_hidden=True)
        control_pt_name = control_pt.name()
        pt = hou.StringParmTemplate('moonray:' + parm_name, parm_name, 1, is_hidden=True)
        extra_disable_when = '{{ {} == block }} {{ {} == none }}'.format(control_pt_name, control_pt_name)
        pt.setDisableWhen(pt.disableWhen() + extra_disable_when)
        expression = """
        parm = hou.parm("lighttype")
        if parm:
            value = parm.eval()
            label = parm.menuLabels()[value]
            if label == "Geometry":
                label = "Mesh"
            elif label == "Rectangle":
                label = "Rect"
            return label + "Light"
        else:
            parm = hou.parm("primtype")
            value = parm.eval()
            if value == "UsdLuxDomeLight":
                return "EnvLight"
        """
        pt.setDefaultExpression([expression])
        pt.setDefaultExpressionLanguage([hou.scriptLanguage.Python])
        pt.setTags({'usdvaluetype': 'token'})
        group.append(control_pt)
        group.append(pt)

    def __build_parms_for_class(self, group, moonray_class, prefix,
                                folder_hidewhen_dict, parm_hidewhen_dict,
                                parm_name_dict, skip_usd_attr,
                                ft=hou.folderType.Tabs):
        for folder_name in moonray_class.folders_sorted:
            if not group.findFolder(folder_name):
                folder = hou.FolderParmTemplate('folder', folder_name, folder_type=ft)
                folder.setConditional(hou.parmCondType.HideWhen, folder_hidewhen_dict.get(folder_name))
                group.append(folder)
                group.hideFolder(folder_name, True)

        usd_attr_list = USD_ATTRIBUTE_MAP.get(moonray_class.moonray_name)
        for parm in moonray_class.parms:
            usdvaluetype = str(parm.get_usd_type())
            if not usdvaluetype:
                continue
            attr_name = parm.moonray_name
            attr_prefix = prefix
            skip_multiparm = usdvaluetype in ['string[]']
            if usd_attr_list and attr_name in usd_attr_list and attr_name not in ['inner_cone_angle']:
                if skip_usd_attr:
                    continue
                attr_prefix = ''
                attr_name = usd_attr_list[attr_name]

            pt_name, control_pt_name = parm_name_dict.get(attr_name, ('', ''))
            pt = group.find(pt_name)
            if not pt:
                hide_when = parm_hidewhen_dict.get(attr_name)
                control_pt = self.__create_control_parm(attr_name, attr_prefix, hide_when, parm.moonray_type)
                if moonray_class.moonray_type == 'Camera':
                    pt = parm.houdini_parm_template(
                        int_menus=False,
                        name_prefix=attr_prefix,
                        moonray_type=parm.moonray_type,
                        use_moonray_name=False,
                        alt_name=attr_name,
                    )
                else:
                    if attr_name != parm.moonray_name:
                        pt = parm.houdini_parm_template(
                            int_menus=False,
                            name_prefix=attr_prefix,
                            moonray_type=parm.moonray_type,
                            use_moonray_name=False,
                            alt_name=attr_name,
                            skip_multiparm=skip_multiparm,
                        )
                    else:
                        pt = parm.houdini_parm_template(
                            int_menus=False,
                            name_prefix=attr_prefix,
                            moonray_type=parm.moonray_type,
                            use_moonray_name=True,
                            alt_name=None,
                            skip_multiparm=skip_multiparm,
                        )
                if not pt:
                    continue
                pt.setConditional(hou.parmCondType.HideWhen, hide_when)
                control_pt_name = control_pt.name()
                disable_when = '{{ {} == block }} {{ {} == none }}'.format(control_pt_name, control_pt_name)
                pt.setDisableWhen(disable_when)
                if usdvaluetype:
                    pt.setTags({'usdvaluetype': usdvaluetype})
                folder_name = moonray_class.folder_name_for_parameter(parm)
                if folder_name and group.findFolder(folder_name):
                    group.appendToFolder(folder_name, control_pt)
                    group.appendToFolder(folder_name, pt)
                    group.hideFolder(folder_name, False)
                else:
                    group.append(control_pt)
                    group.append(pt)
                parm_name_dict[attr_name] = (pt.name(), control_pt_name)

    def __build_parms_for_class_list(self, moonray_class_list, prefix, group,
                                     parm_name_dict, is_usd_primtype,
                                     skip_usd_attr, create_hide_when=True,
                                     ft=hou.folderType.Tabs):
        folder_hidewhen_dict = {}
        parm_hidewhen_dict = {}
        if create_hide_when:
            folder_hidewhen_dict, parm_hidewhen_dict = self.__create_hidewhen_dict(
                moonray_class_list, is_usd_primtype, skip_usd_attr)
            self.__update_light_hidewhen(
                folder_hidewhen_dict,
                parm_hidewhen_dict,
                moonray_class_list,
                skip_usd_attr,
            )
        for moonray_class in moonray_class_list:
            self.__build_parms_for_class(
                group,
                moonray_class,
                prefix,
                folder_hidewhen_dict,
                parm_hidewhen_dict,
                parm_name_dict,
                skip_usd_attr,
                ft,
            )

    def __build_settings(self, folder_name, parm_list, group, attr_prefix='moonray:',
                         added_parm_names=None):
        if added_parm_names is None:
            added_parm_names = set()
        folder = hou.FolderParmTemplate('folder', folder_name, folder_type=hou.folderType.Tabs)
        group.append(folder)
        for parm in parm_list:
            attr_name = parm.moonray_name
            pt = parm.houdini_parm_template(int_menus=False, name_prefix=attr_prefix, use_moonray_name=True)
            if not pt:
                # logger.warning(
                #     "Skipping unsupported parm template for %s.%s (%s)",
                #     folder_name,
                #     attr_name,
                #     parm.moonray_type,
                # )
                continue

            control_pt = self.__create_control_parm(attr_name, attr_prefix, '', parm.moonray_type)
            duplicate_names = [
                parm_name for parm_name in (control_pt.name(), pt.name())
                if parm_name in added_parm_names
            ]
            if duplicate_names:
                # logger.warning(
                #     "Skipping duplicate parm(s) for %s.%s: %s",
                #     folder_name,
                #     attr_name,
                #     ', '.join(duplicate_names),
                # )
                continue

            control_pt_name = control_pt.name()
            extra = '{{ {} == block }} {{ {} == none }}'.format(control_pt_name, control_pt_name)
            pt.setDisableWhen(pt.disableWhen() + extra)
            usdvaluetype = str(parm.get_usd_type())
            if usdvaluetype:
                pt.setTags({'usdvaluetype': usdvaluetype})
            group.appendToFolder(folder_name, control_pt)
            group.appendToFolder(folder_name, pt)
            added_parm_names.update((control_pt.name(), pt.name()))

    def __create_hidewhen_dict(self, moonray_class_list, is_usd_type, skip_usd_attr):
        folder_hide_dict = {}
        parm_hide_dict = {}
        for moonray_class in moonray_class_list:
            class_name = moonray_class.moonray_name
            hide_when = self.__get_hide_when_string(class_name, is_usd_type)
            for folder_name in moonray_class.folders_sorted:
                cur_hide_when = folder_hide_dict.get(folder_name)
                if cur_hide_when:
                    folder_hide_dict[folder_name] = '{{ {} {} }}'.format(
                        cur_hide_when[2:-2], hide_when[2:-2])
                else:
                    folder_hide_dict[folder_name] = hide_when

            usd_attr_list = self.usd_prim_type_attr.get(class_name)
            for parm in moonray_class.parms:
                attr_name = parm.moonray_name
                if skip_usd_attr and usd_attr_list and attr_name in usd_attr_list:
                    continue
                cur_hide_when = parm_hide_dict.get(attr_name)
                if cur_hide_when:
                    parm_hide_dict[attr_name] = '{{ {} {} }}'.format(
                        cur_hide_when[2:-2], hide_when[2:-2])
                else:
                    parm_hide_dict[attr_name] = hide_when
        return folder_hide_dict, parm_hide_dict

    def __update_light_hidewhen(self, folder_hide_dict, parm_hide_dict,
                                moonray_class_list, skip_usd_attr):
        hide_when = '{{ createprims == on }}'
        updated = []
        for moonray_class in moonray_class_list:
            if moonray_class.moonray_type != 'Light':
                continue
            class_name = moonray_class.moonray_name
            for folder_name in moonray_class.folders_sorted:
                if folder_name in updated:
                    continue
                cur_hide_when = folder_hide_dict.get(folder_name)
                if cur_hide_when:
                    folder_hide_dict[folder_name] = '{{ {} {} }}'.format(
                        cur_hide_when[2:-2], hide_when[2:-2])
                    updated.append(folder_name)

            usd_attr_list = self.usd_prim_type_attr.get(class_name)
            for parm in moonray_class.parms:
                attr_name = parm.moonray_name
                if attr_name in updated:
                    continue
                if skip_usd_attr and usd_attr_list and attr_name in usd_attr_list:
                    continue
                cur_hide_when = parm_hide_dict.get(attr_name)
                if cur_hide_when:
                    parm_hide_dict[attr_name] = '{{ {} {} }}'.format(
                        cur_hide_when[2:-2], hide_when[2:-2])
                    updated.append(attr_name)

    def __create_control_parm(self, parm_name, prefix, hide_when, moonray_type,
                              default_value='none', is_hidden=False):
        name = '{}{}_control'.format(prefix, parm_name)
        label = '{}{}'.format(prefix, parm_name)
        pt = hou.StringParmTemplate(
            name,
            label,
            1,
            default_value=[default_value],
            is_hidden=is_hidden,
        )
        menu, labels = create_control_menu(moonray_type)
        pt.setMenuItems(menu)
        pt.setMenuLabels(labels)
        pt.setMenuType(hou.menuType.ControlNextParameter)
        pt.setConditional(hou.parmCondType.HideWhen, hide_when)
        pt.setTags({'sidefx::look': 'icon'})
        return pt

    def __get_hide_when_string(self, class_name, is_usd_type):
        if is_usd_type:
            return '{{ primtype != UsdLux{} }}'.format(self.__get_usdclass_name(class_name))
        return '{{ primtype != {} }}'.format(class_name)

    def __get_usdclass_name(self, moonray_class_name):
        if moonray_class_name == 'SpotLight':
            return 'DiskLight'
        elif moonray_class_name == 'EnvLight':
            return 'DomeLight'
        elif moonray_class_name == 'MeshLight':
            return 'GeometryLight'
        return moonray_class_name

    def __get_shared_parms(self, geometry_class_list):
        common_settings = {}
        count = {}
        number = 0
        for moonray_class in self.geometry_class.values():
            if moonray_class.moonray_name in geometry_class_list:
                number += 1
                for parm in moonray_class.parms:
                    attr_name = parm.moonray_name
                    if number == 1:
                        common_settings[attr_name] = parm
                        count[attr_name] = 1
                    elif attr_name in common_settings:
                        count[attr_name] = count[attr_name] + 1
        for attr_name, attr_count in list(count.items()):
            if attr_count != number and attr_name in common_settings:
                del common_settings[attr_name]
        return list(common_settings.keys()), list(common_settings.values())

    def __get_moonrayclass_parms(self, moonray_class_name, attr_name_list=None):
        parm_list = []
        for moonray_class in self.moonray_classes:
            if moonray_class.moonray_name == moonray_class_name:
                if not attr_name_list:
                    return moonray_class.parms
                for parm in moonray_class.parms:
                    if parm.moonray_name in attr_name_list:
                        parm_list.append(parm)
        return parm_list

    def __save_ds_file(self, group, filename):
        script = '#include "$HFS/houdini/soho/parameters/CommonMacros.ds"\n' + group.asDialogScript()
        soho_dir = os.path.join(self.dest_dir, 'soho', 'parameters')
        ensure_directory(soho_dir)
        dest_file = os.path.join(soho_dir, filename)
        with open(dest_file, 'w') as file_pointer:
            file_pointer.write(script)

    def build_moonray_class(self, prefix, moonray_class):
        group = hou.ParmTemplateGroup()
        self.__build_parms_for_class(
            group,
            moonray_class,
            prefix,
            {},
            {},
            {},
            False,
        )
        self.__save_ds_file(group, 'moonray_{0}.ds'.format(moonray_class.moonray_name))

    def build_moonray_override(self):
        shaders = sorted(list(self.shader_class.keys()))
        lights = sorted(list(self.light_class.keys()))
        lfs = sorted(list(self.lf_class.keys()))
        cams = sorted(list(self.cam_class.keys()))
        geos = sorted(list(self.geometry_class.keys()))

        group = hou.ParmTemplateGroup()
        category = hou.MenuParmTemplate(
            'category',
            'Category',
            menu_items=['Shader', 'Light', 'Camera', 'Light Filter', 'Geometry'],
            is_button_strip=True,
        )
        script = """
        parm = hou.pwd().parm("category")
        selected = parm.eval()
        tokens = parm.parmTemplate().menuItems()
        menulist = []
        token = tokens[selected]
        if token == "Shader":
            menulist = %s
        elif token == "Light":
            menulist = %s
        elif token == "Camera":
            menulist = %s
        elif token == "Light Filter":
            menulist = %s
        elif token == "Geometry":
            menulist = %s
        return menulist
        """ % (shaders, lights, cams, lfs, geos)
        primtype = hou.StringParmTemplate(
            'primtype',
            'Primitive Type',
            1,
            item_generator_script=script,
            menu_type=hou.menuType.StringReplace,
            script_callback='hou.phm().wrapper(hou.pwd()).load_ds()',
            script_callback_language=hou.scriptLanguage.Python,
        )
        group.append(category)
        group.append(primtype)
        self.__save_ds_file(group, 'moonray_Override.ds')

        for a_class in self.shader_class.values():
            self.build_moonray_class('inputs:', a_class)

        others = list(self.light_class.values()) + list(self.lf_class.values()) + \
            list(self.geometry_class.values()) + list(self.cam_class.values())
        for a_class in others:
            if a_class.moonray_name.find('Deform') != -1 or a_class.moonray_name.startswith('Willow'):
                self.build_moonray_class('procedural:', a_class)
            elif a_class in self.geometry_class.values():
                self.build_moonray_class('primvars:moonray:', a_class)
            else:
                self.build_moonray_class('moonray:', a_class)

    def build_moonray_geometry(self):
        geo_dict = {
            'BoxGeometry': [],
            'RdlCurveGeometry': [],
            'RdlInstancerGeometry': [],
            'RdlMeshGeometry': [],
            'RdlPointGeometry': [],
            'SphereGeometry': [],
            'VdbGeometry': [],
        }
        geo_label_dict = {
            'BoxGeometry': 'Box',
            'RdlCurveGeometry': 'RdlCurve',
            'RdlInstancerGeometry': 'RdlInstancer',
            'RdlMeshGeometry': 'RdlMesh',
            'RdlPointGeometry': 'RdlPoint',
            'SphereGeometry': 'Sphere',
            'VdbGeometry': 'Vdb',
        }
        _parm_name_list, parm_list = self.__get_shared_parms(list(geo_dict.keys()))
        group = hou.ParmTemplateGroup()
        group.setLabel('Moonray')
        added_parm_names = set()
        self.__build_settings('Common Properties', parm_list, group, 'primvars:moonray:', added_parm_names)
        for class_name, attr_list in geo_dict.items():
            parm_list = self.__get_moonrayclass_parms(class_name, attr_list)
            if parm_list:
                self.__build_settings(
                    geo_label_dict.get(class_name, class_name),
                    parm_list,
                    group,
                    'primvars:moonray:',
                    added_parm_names,
                )
        self.__save_ds_file(group, 'HdMoonrayRendererPlugin_Geometry.ds')

    def build_moonray_lights(self):
        group = hou.ParmTemplateGroup()
        group.setLabel('Moonray')
        parm_name_dict = {}
        moonray_class_list = []
        for moonray_class in self.moonray_classes:
            if moonray_class.moonray_type == 'Light':
                moonray_class_list.append(moonray_class)
        self.__add_light_type_parm(group)
        self.__build_parms_for_class_list(
            moonray_class_list,
            'moonray:',
            group,
            parm_name_dict,
            True,
            True,
        )
        self.__save_ds_file(group, 'HdMoonrayRendererPlugin_Light.ds')

    def build_moonray_global(self):
        group = hou.ParmTemplateGroup()
        group.setLabel('Moonray')
        parm_name_dict = {}
        moonray_class_list = []
        for moonray_class in self.moonray_classes:
            if moonray_class.moonray_name == 'SceneVariables':
                moonray_class_list.append(moonray_class)
                break
        self.__build_parms_for_class_list(
            moonray_class_list,
            'moonray:sceneVariable:',
            group,
            parm_name_dict,
            False,
            True,
            False,
            hou.folderType.Tabs,
        )
        self.__save_ds_file(group, 'HdMoonrayRendererPlugin_Global.ds')

    def build_moonray_renderVar(self):
        group = hou.ParmTemplateGroup()
        group.setLabel('Moonray')
        parm_name_dict = {}
        moonray_class_list = []
        for moonray_class in self.moonray_classes:
            if moonray_class.moonray_name == 'RenderOutput':
                moonray_class_list.append(moonray_class)
                break
        self.__build_parms_for_class_list(
            moonray_class_list,
            'parameters:moonray:',
            group,
            parm_name_dict,
            True,
            True,
            False,
            hou.folderType.Tabs,
        )
        self.__save_ds_file(group, 'HdMoonrayRendererPlugin_Aov.ds')


def main():
    global HELP_URL
    parser = argparse.ArgumentParser(
        description='Build public Moonray HDAs and LOP .ds files against Moonshine.')
    parser.add_argument(
        'moonshine_packages',
        help="Optional package label(s) recorded in moonray_nodes.json, e.g. 'moonshine-15.0'. "
             "Shader data always comes from rdl2_json_exporter on RDL2_DSO_PATH.",
        type=str,
        nargs='*',
        default=[],
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help='Destination directory for HDAs, metadata JSON, and LOP .ds files (default: {}).'.format(
            DEFAULT_OUTPUT_DIR),
    )
    parser.add_argument(
        '--classes-json',
        default=os.environ.get(VAR_CLASSES_JSON),
        help='Read the scene class definitions from this file, as produced by '
             '"rdl2_json_exporter --out <file>", instead of running the exporter. '
             'Use this when running under hython: Moonshine is built against its own '
             'USD, which cannot share a process with the USD inside Houdini, so the '
             'export has to happen in a separate shell. Defaults to ${}.'.format(
                 VAR_CLASSES_JSON),
    )
    parser.add_argument(
        '--internal',
        action='store_true',
        help='Build the internal plugin set. Public builds refuse a package set '
             'containing DWA packages, because moonshine_dwa shaders must not end '
             'up in the public moonray_dcc_plugins repo. Pass this only when the '
             'output is going somewhere internal.',
    )
    parser.add_argument(
        '--help-url',
        default=HELP_URL,
        help='Documentation URL to embed in each HDA as its HelpUrl section. '
             'Defaults to $MOONRAY_HDA_HELP_URL; when empty no HelpUrl is written.',
    )

    args = parser.parse_args()
    HELP_URL = args.help_url
    if args.classes_json:
        os.environ[VAR_CLASSES_JSON] = args.classes_json
    pkgs = ' '.join(args.moonshine_packages)
    if args.internal:
        print('Building the INTERNAL plugin set; proprietary shaders are allowed.')
    else:
        validate_public_packages(pkgs)

    ensure_directory(args.output_dir)
    ensure_directory(os.path.join(args.output_dir, 'otls'))
    ensure_directory(os.path.join(args.output_dir, 'soho', 'parameters'))

    print('=' * 80)
    print('Public Moonshine build')
    print('  Packages    : {0}'.format(pkgs))
    print('  Output dir  : {0}'.format(args.output_dir))
    print('=' * 80)

    updater = UpdateHDAs(
        moonshine_packages=pkgs,
        destination_directory=args.output_dir,
    )
    updater.main()

    builder = LopDialogScriptBuilder(args.output_dir, updater.moonray_classes)
    builder.build_moonray_lights()
    builder.build_moonray_geometry()
    builder.build_moonray_override()
    builder.build_moonray_global()
    builder.build_moonray_renderVar()

    print('=' * 80)
    print('Public Moonshine build complete.')
    print('  HDAs      -> {0}'.format(os.path.join(args.output_dir, 'otls')))
    print('  Metadata  -> {0}'.format(os.path.join(args.output_dir, MOONSHINE_DATA_FILE)))
    print('  DS files  -> {0}'.format(os.path.join(args.output_dir, 'soho', 'parameters')))
    print('=' * 80)


if __name__ == '__main__':
    main()