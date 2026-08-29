"""MoonRay Solaris Render Settings authoring and HDA generation."""

import os
from pathlib import Path

import hou

from pxr import Gf, Sdf, UsdRender


OPERATOR_TYPE = "Lop::DW_MOONRAY::moonrayrendersettings::1"
OPERATOR_LABEL = "MoonRay Render Settings"
RENDER_SETTINGS_PRIM = "/Render/rendersettings"
RENDER_PRODUCTS_PARENT_PRIM = "/Render/Products"
RENDER_VARS_PARENT_PRIM = "/Render/Products/Vars"
RENDER_PRODUCT_NAME = "renderproduct"
BEAUTY_RENDER_VAR_NAME = "beauty"
PRODUCT_NAME = "$HIP/render/$HIPNAME.$OS.\\$F4.exr"
DEFAULT_RESOLUTION = (1920, 1080)
DEFAULT_RENDERING_COLOR_SPACE = ""
ROP_NODE_TYPE = "usdrender_rop"
ROP_RENDERER_TOKEN = "HdMoonrayRendererPlugin"
ROP_OWNER_LOP_KEY = "moonray_render_settings_lop"
ROP_OWNER_OPERATOR_KEY = "moonray_render_settings_operator"
ROP_OWNER_SESSION_KEY = "moonray_render_settings_lop_session_id"
CONTRACT_WARNING_KEY = "moonray_render_contract_warning"
OCIO_RENDER_ROLE_ORDER = (
    "rendering",
    "scene_linear",
    "default_float",
    "reference",
    "default",
)
OCIO_TEXTURE_ROLE_ORDER = (
    "texture_paint",
    "color_picking",
    "default_byte",
)


AOV_DEFINITIONS = (
    {
        "parm": "aov_alpha",
        "label": "Alpha",
        "render_var": "alpha",
        "source_name": "alpha",
        "data_type": "float",
        "help": "MoonRay alpha RenderOutput. Production-tested as a native single-channel AOV.",
    },
    {
        "parm": "aov_depth",
        "label": "Depth",
        "render_var": "depth",
        "source_name": "depth",
        "data_type": "float",
        "help": "MoonRay depth RenderOutput. In hdMoonray this follows the existing depth mapping.",
    },
    {
        "parm": "aov_z",
        "label": "Z",
        "render_var": "Z",
        "source_name": "Z",
        "data_type": "float",
        "help": "MoonRay state-variable depth through the existing Z mapping.",
    },
    {
        "parm": "aov_n",
        "label": "N",
        "render_var": "N",
        "source_name": "N",
        "data_type": "normal3f",
        "help": "MoonRay shading normal state variable.",
    },
    {
        "parm": "aov_ng",
        "label": "Ng",
        "render_var": "Ng",
        "source_name": "Ng",
        "data_type": "normal3f",
        "help": "MoonRay geometric normal state variable.",
    },
    {
        "parm": "aov_p",
        "label": "P",
        "render_var": "P",
        "source_name": "P",
        "data_type": "point3f",
        "help": "MoonRay position state variable.",
    },
    {
        "parm": "aov_wp",
        "label": "Wp",
        "render_var": "Wp",
        "source_name": "Wp",
        "data_type": "point3f",
        "help": "MoonRay world-position state variable.",
    },
    {
        "parm": "aov_st",
        "label": "St",
        "render_var": "St",
        "source_name": "St",
        "data_type": "float2",
        "help": "MoonRay texture-coordinate state variable.",
    },
    {
        "parm": "aov_weight",
        "label": "Weight",
        "render_var": "weight",
        "source_name": "weight",
        "data_type": "float",
        "help": "MoonRay weight RenderOutput. Existing production proof showed a constant sample-count value in the simple fixture.",
    },
)

MATERIAL_AOV_DEFINITIONS = (
    {
        "parm": "aov_denoise_albedo",
        "label": "Denoise Albedo",
        "render_var": "denoise_albedo",
        "source_name": "D.albedo",
        "source_type": "shader",
        "data_type": "color3f",
        "extra_attrs": {
            "parameters:moonray:denoiser_input": (Sdf.ValueTypeNames.Token, "as albedo"),
            "parameters:moonray:channel_suffix_mode": (Sdf.ValueTypeNames.Token, "rgb"),
            "parameters:moonray:channel_format": (Sdf.ValueTypeNames.Token, "float"),
        },
        "help": "Official MoonRay OIDN albedo auxiliary output: material AOV D.albedo tagged as denoiser input.",
    },
    {
        "parm": "aov_denoise_normal",
        "label": "Denoise Normal",
        "render_var": "denoise_normal",
        "source_name": "N",
        "source_type": "raw",
        "data_type": "normal3f",
        "extra_attrs": {
            "parameters:moonray:denoiser_input": (Sdf.ValueTypeNames.Token, "as normal"),
            "parameters:moonray:channel_suffix_mode": (Sdf.ValueTypeNames.Token, "rgb"),
            "parameters:moonray:channel_format": (Sdf.ValueTypeNames.Token, "float"),
        },
        "help": "Official MoonRay OIDN normal auxiliary output: state variable N tagged as denoiser input.",
    },
    {
        "parm": "aov_material_albedo",
        "label": "Material Albedo",
        "render_var": "material_albedo",
        "source_name": "albedo",
        "source_type": "shader",
        "data_type": "color3f",
        "help": "MoonRay material AOV albedo expression.",
    },
    {
        "parm": "aov_material_emission",
        "label": "Material Emission",
        "render_var": "material_emission",
        "source_name": "emission",
        "source_type": "shader",
        "data_type": "color3f",
        "help": "MoonRay material AOV emission expression.",
    },
    {
        "parm": "aov_material_normal",
        "label": "Material Normal",
        "render_var": "material_normal",
        "source_name": "normal",
        "source_type": "shader",
        "data_type": "normal3f",
        "extra_attrs": {
            "parameters:moonray:channel_suffix_mode": (Sdf.ValueTypeNames.Token, "rgb"),
        },
        "help": "MoonRay material AOV normal expression.",
    },
    {
        "parm": "aov_material_roughness",
        "label": "Material Roughness",
        "render_var": "material_roughness",
        "source_name": "roughness",
        "source_type": "shader",
        "data_type": "float2",
        "help": "MoonRay material AOV glossy roughness expression.",
    },
    {
        "parm": "aov_material_pbr_validity",
        "label": "Material PBR Validity",
        "render_var": "material_pbr_validity",
        "source_name": "pbr_validity",
        "source_type": "shader",
        "data_type": "color3f",
        "help": "MoonRay material AOV PBR validity diagnostic expression.",
    },
)


SCENE_VARIABLES = (
    ("sampling_mode", Sdf.ValueTypeNames.Token),
    ("light_sampling_mode", Sdf.ValueTypeNames.Token),
    ("light_sampling_quality", Sdf.ValueTypeNames.Float),
    ("pixel_samples", Sdf.ValueTypeNames.Int),
    ("light_samples", Sdf.ValueTypeNames.Int),
    ("bsdf_samples", Sdf.ValueTypeNames.Int),
    ("bssrdf_samples", Sdf.ValueTypeNames.Int),
    ("target_adaptive_error", Sdf.ValueTypeNames.Float),
    ("min_adaptive_samples", Sdf.ValueTypeNames.Int),
    ("max_adaptive_samples", Sdf.ValueTypeNames.Int),
    ("batch_tile_order", Sdf.ValueTypeNames.Token),
    ("progressive_tile_order", Sdf.ValueTypeNames.Token),
    ("checkpoint_tile_order", Sdf.ValueTypeNames.Token),
    ("sample_clamping_value", Sdf.ValueTypeNames.Float),
    ("sample_clamping_depth", Sdf.ValueTypeNames.Int),
    ("roughness_clamping_factor", Sdf.ValueTypeNames.Float),
    ("max_depth", Sdf.ValueTypeNames.Int),
    ("max_diffuse_depth", Sdf.ValueTypeNames.Int),
    ("max_glossy_depth", Sdf.ValueTypeNames.Int),
    ("max_mirror_depth", Sdf.ValueTypeNames.Int),
    ("max_presence_depth", Sdf.ValueTypeNames.Int),
    ("max_hair_depth", Sdf.ValueTypeNames.Int),
    ("max_volume_depth", Sdf.ValueTypeNames.Int),
    ("max_subsurface_per_path", Sdf.ValueTypeNames.Int),
    ("russian_roulette_threshold", Sdf.ValueTypeNames.Float),
    ("transparency_threshold", Sdf.ValueTypeNames.Float),
    ("presence_threshold", Sdf.ValueTypeNames.Float),
    ("presence_quality", Sdf.ValueTypeNames.Float),
    ("lock_frame_noise", Sdf.ValueTypeNames.Bool),
    ("disable_optimized_hair_sampling", Sdf.ValueTypeNames.Bool),
    ("volume_quality", Sdf.ValueTypeNames.Float),
    ("volume_shadow_quality", Sdf.ValueTypeNames.Float),
    ("volume_illumination_samples", Sdf.ValueTypeNames.Int),
    ("volume_opacity_threshold", Sdf.ValueTypeNames.Float),
    ("volume_overlap_mode", Sdf.ValueTypeNames.Token),
    ("volume_attenuation_factor", Sdf.ValueTypeNames.Float),
    ("volume_contribution_factor", Sdf.ValueTypeNames.Float),
    ("volume_phase_attenuation_factor", Sdf.ValueTypeNames.Float),
    ("volume_indirect_samples", Sdf.ValueTypeNames.Int),
    ("texture_blur", Sdf.ValueTypeNames.Float),
    ("texture_cache_size", Sdf.ValueTypeNames.Int),
    ("texture_file_handles", Sdf.ValueTypeNames.Int),
    ("pixel_filter_width", Sdf.ValueTypeNames.Float),
    ("pixel_filter", Sdf.ValueTypeNames.Token),
    ("enable_dof", Sdf.ValueTypeNames.Bool),
    ("enable_displacement", Sdf.ValueTypeNames.Bool),
    ("enable_subsurface_scattering", Sdf.ValueTypeNames.Bool),
    ("enable_shadowing", Sdf.ValueTypeNames.Bool),
    ("enable_presence_shadows", Sdf.ValueTypeNames.Bool),
    ("lights_visible_in_camera", Sdf.ValueTypeNames.Bool),
    ("propagate_visibility_bounce_type", Sdf.ValueTypeNames.Bool),
    ("shadow_terminator_fix", Sdf.ValueTypeNames.Token),
)


def _parm(node, name, default=None):
    parm = node.parm(name)
    if parm is None:
        return default
    return parm.eval()


def _string_parm(node, name, default=""):
    parm = node.parm(name)
    if parm is None:
        return default
    try:
        return parm.unexpandedString()
    except hou.OperationFailed:
        return str(parm.eval())


def _path(node, name, default):
    value = _string_parm(node, name, default).strip()
    return value or default


def _child_path(parent, child):
    parent_path = Sdf.Path(parent)
    return str(parent_path.AppendChild(child))


def _set_rel_targets(schema_obj, create_rel, paths):
    valid = [Sdf.Path(path) for path in paths if path]
    rel = create_rel()
    rel.SetTargets(valid)
    return rel


def _define_render_var(stage, path, data_type, source_name, source_type="raw", extra_attrs=None):
    render_var = UsdRender.Var.Define(stage, path)
    render_var.CreateDataTypeAttr().Set(data_type)
    render_var.CreateSourceNameAttr().Set(source_name)
    render_var.CreateSourceTypeAttr().Set(source_type)
    prim = render_var.GetPrim()
    prim.CreateAttribute(
        "driver:parameters:aov:name",
        Sdf.ValueTypeNames.String,
        custom=True,
    ).Set(source_name)
    prim.CreateAttribute(
        "driver:parameters:aov:format",
        Sdf.ValueTypeNames.Token,
        custom=True,
    ).Set(data_type)
    prim.CreateAttribute(
        "driver:parameters:aov:multiSampled",
        Sdf.ValueTypeNames.Bool,
        custom=True,
    ).Set(False)
    prim.CreateAttribute(
        "driver:parameters:aov:clearValue",
        Sdf.ValueTypeNames.Int,
        custom=True,
    ).Set(0)
    for attr_name, (value_type, value) in (extra_attrs or {}).items():
        prim.CreateAttribute(attr_name, value_type, custom=True).Set(value)
    return render_var


def _bool_parm(node, name, default=False):
    parm = node.parm(name)
    if parm is None:
        return default
    return bool(parm.eval())


def author_from_node(node=None):
    """Author USD RenderSettings, RenderProduct, beauty RenderVar, and MoonRay settings."""

    node = node or hou.pwd()
    stage = node.editableStage()

    settings_path = _path(node, "render_settings_prim", RENDER_SETTINGS_PRIM)
    products_parent_path = _path(node, "render_products_parent_prim", RENDER_PRODUCTS_PARENT_PRIM)
    vars_parent_path = _path(node, "render_vars_parent_prim", RENDER_VARS_PARENT_PRIM)
    product_name = _string_parm(node, "render_product_name", RENDER_PRODUCT_NAME).strip() or RENDER_PRODUCT_NAME
    beauty_var_name = _string_parm(node, "beauty_render_var_name", BEAUTY_RENDER_VAR_NAME).strip() or BEAUTY_RENDER_VAR_NAME
    product_path = _child_path(products_parent_path, product_name)
    beauty_var_path = _child_path(vars_parent_path, beauty_var_name)
    camera_path = _path(node, "camera", "/cameras/camera1")

    settings = UsdRender.Settings.Define(stage, settings_path)
    product = UsdRender.Product.Define(stage, product_path)

    _set_rel_targets(settings, settings.CreateProductsRel, [product_path])
    if camera_path:
        _set_rel_targets(settings, settings.CreateCameraRel, [camera_path])

    rendering_color_space = _string_parm(node, "renderingColorSpace", DEFAULT_RENDERING_COLOR_SPACE).strip()
    if rendering_color_space and rendering_color_space.lower() != "auto":
        settings.CreateRenderingColorSpaceAttr().Set(rendering_color_space)
    else:
        settings.GetRenderingColorSpaceAttr().Clear()

    width = int(_parm(node, "resolutionx", DEFAULT_RESOLUTION[0]))
    height = int(_parm(node, "resolutiony", DEFAULT_RESOLUTION[1]))
    resolution = Gf.Vec2i(width, height)
    pixel_aspect = float(_parm(node, "pixelAspectRatio", 1.0))
    settings.CreateResolutionAttr().Set(resolution)
    settings.CreatePixelAspectRatioAttr().Set(pixel_aspect)
    product.CreateResolutionAttr().Set(resolution)
    product.CreatePixelAspectRatioAttr().Set(pixel_aspect)

    product_name = _string_parm(node, "product_name", PRODUCT_NAME).strip() or PRODUCT_NAME
    product.CreateProductNameAttr().Set(product_name)
    product.CreateProductTypeAttr().Set("raster")

    ordered_vars = []
    if _bool_parm(node, "aov_beauty", True):
        _define_render_var(stage, beauty_var_path, "color4f", "color")
        ordered_vars.append(beauty_var_path)
    for aov in AOV_DEFINITIONS:
        if not _bool_parm(node, aov["parm"], False):
            continue
        aov_path = _child_path(vars_parent_path, aov["render_var"])
        _define_render_var(stage, aov_path, aov["data_type"], aov["source_name"])
        ordered_vars.append(aov_path)
    for aov in MATERIAL_AOV_DEFINITIONS:
        if not _bool_parm(node, aov["parm"], False):
            continue
        aov_path = _child_path(vars_parent_path, aov["render_var"])
        _define_render_var(
            stage,
            aov_path,
            aov["data_type"],
            aov["source_name"],
            aov.get("source_type", "raw"),
            aov.get("extra_attrs"),
        )
        ordered_vars.append(aov_path)
    _set_rel_targets(product, product.CreateOrderedVarsRel, ordered_vars)

    settings_prim = settings.GetPrim()
    for name, value_type in SCENE_VARIABLES:
        parm = node.parm("sceneVariable_" + name)
        if parm is None:
            continue
        if value_type == Sdf.ValueTypeNames.Token:
            value = parm.evalAsString()
        elif value_type == Sdf.ValueTypeNames.Int:
            value = int(parm.eval())
        elif value_type == Sdf.ValueTypeNames.Float:
            value = float(parm.eval())
        elif value_type == Sdf.ValueTypeNames.Bool:
            value = bool(parm.eval())
        settings_prim.CreateAttribute(
            "moonray:sceneVariable:" + name,
            value_type,
            custom=True,
        ).Set(value)

    rdl_output = _string_parm(node, "rdlOutput", "").strip()
    if rdl_output:
        settings_prim.CreateAttribute(
            "rdlOutput",
            Sdf.ValueTypeNames.String,
            custom=True,
        ).Set(rdl_output)


def _safe_node_name(name):
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)


def _rop_loppath_target(rop):
    parm = rop.parm("loppath")
    if parm is None:
        return None
    value = parm.eval()
    if value.startswith("/"):
        target = hou.node(value)
    else:
        target = rop.node(value)
        if target is None and rop.parent() is not None:
            target = rop.parent().node(value)
    return target.path() if target is not None else value


def _owned_rop_for_lop(lop_node):
    parent = lop_node.parent()
    if parent is None:
        return None

    lop_path = lop_node.path()
    lop_session_id = str(lop_node.sessionId())
    fallback_by_path = None
    fallback_by_session = None
    for rop in parent.children():
        if rop.type().name() != ROP_NODE_TYPE:
            continue
        if rop.userData(ROP_OWNER_OPERATOR_KEY) != OPERATOR_TYPE:
            continue
        if rop.userData(ROP_OWNER_LOP_KEY) == lop_path:
            return rop
        if rop.userData(ROP_OWNER_SESSION_KEY) == lop_session_id:
            fallback_by_session = rop
        elif _rop_loppath_target(rop) == lop_path:
            fallback_by_path = rop
    return fallback_by_session or fallback_by_path


def _render_contract_paths(lop_node):
    settings_path = _path(lop_node, "render_settings_prim", RENDER_SETTINGS_PRIM)
    products_parent_path = _path(lop_node, "render_products_parent_prim", RENDER_PRODUCTS_PARENT_PRIM)
    product_name = _string_parm(lop_node, "render_product_name", RENDER_PRODUCT_NAME).strip() or RENDER_PRODUCT_NAME
    return settings_path, _child_path(products_parent_path, product_name)


def _duplicate_render_contract_nodes(lop_node):
    parent = lop_node.parent()
    if parent is None:
        return []
    settings_path, product_path = _render_contract_paths(lop_node)
    duplicates = []
    for other in parent.children():
        if other == lop_node or other.type().name() != OPERATOR_TYPE:
            continue
        try:
            if other.isBypassed():
                continue
        except hou.OperationFailed:
            pass
        other_settings_path, other_product_path = _render_contract_paths(other)
        if other_settings_path == settings_path or other_product_path == product_path:
            duplicates.append(other)
    return duplicates


def _set_user_data_or_clear(node, key, value):
    if value:
        node.setUserData(key, value)
        return
    try:
        node.destroyUserData(key)
    except (AttributeError, hou.OperationFailed):
        node.setUserData(key, "")


def _refresh_render_contract_warnings(parent):
    if parent is None:
        return
    for lop_node in parent.children():
        if lop_node.type().name() != OPERATOR_TYPE:
            continue
        duplicates = _duplicate_render_contract_nodes(lop_node)
        message = ""
        if duplicates:
            settings_path, product_path = _render_contract_paths(lop_node)
            message = (
                "WARNING: duplicate MoonRay Render Settings contract. "
                "This node shares %s or %s with: %s"
                % (settings_path, product_path, ", ".join(sorted(node.path() for node in duplicates)))
            )
        _set_user_data_or_clear(lop_node, CONTRACT_WARNING_KEY, message)
        rop = _owned_rop_for_lop(lop_node)
        if rop is not None:
            comment = "Owned by %s (%s)." % (lop_node.path(), OPERATOR_TYPE)
            if message:
                comment += "\n" + message
            rop.setComment(comment)
            try:
                rop.setGenericFlag(hou.nodeFlag.DisplayComment, True)
            except hou.OperationFailed:
                pass


def _create_owned_rop(lop_node):
    parent = lop_node.parent()
    if parent is None:
        raise hou.OperationFailed("MoonRay Render Settings LOP has no parent network.")
    base_name = _safe_node_name(lop_node.name() + "_usdrender")
    existing = parent.node(base_name)
    if existing is not None:
        if (
            existing.type().name() == ROP_NODE_TYPE
            and existing.userData(ROP_OWNER_OPERATOR_KEY) == OPERATOR_TYPE
            and existing.userData(ROP_OWNER_LOP_KEY) == lop_node.path()
        ):
            return existing
        rop = parent.createNode(ROP_NODE_TYPE)
        rop.setName(base_name, unique_name=True)
        return rop
    return parent.createNode(ROP_NODE_TYPE, base_name)


def _set_hscript_string_expression(parm, expression):
    value = "`%s`" % expression
    try:
        if parm.rawValue() == value:
            return
    except hou.OperationFailed:
        pass
    parm.set(value)


def _chs_expression(node, parm_name):
    return 'chs("%s/%s")' % (node.path(), parm_name)


def create_or_update_usd_render_rop(lop_node=None):
    """Create or update the USD Render ROP owned by this MoonRay Render Settings LOP."""

    lop_node = lop_node or hou.pwd()
    rop = _owned_rop_for_lop(lop_node) or _create_owned_rop(lop_node)

    try:
        rop.setInput(0, lop_node)
    except hou.OperationFailed:
        pass

    renderer = rop.parm("renderer")
    if renderer is not None:
        renderer.set(ROP_RENDERER_TOKEN)

    loppath = rop.parm("loppath")
    if loppath is not None:
        _set_hscript_string_expression(loppath, 'opinput(".", 0)')

    render_settings = rop.parm("rendersettings")
    if render_settings is not None:
        _set_hscript_string_expression(render_settings, _chs_expression(lop_node, "render_settings_prim"))

    output_image = rop.parm("outputimage")
    if output_image is not None:
        _set_hscript_string_expression(output_image, _chs_expression(lop_node, "product_name"))

    try:
        rop.setPosition(lop_node.position() + hou.Vector2(0, -1.0))
    except hou.OperationFailed:
        pass

    rop.setUserData(ROP_OWNER_LOP_KEY, lop_node.path())
    rop.setUserData(ROP_OWNER_OPERATOR_KEY, OPERATOR_TYPE)
    rop.setUserData(ROP_OWNER_SESSION_KEY, str(lop_node.sessionId()))
    rop.setComment("Owned by %s (%s)." % (lop_node.path(), OPERATOR_TYPE))
    try:
        rop.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    except hou.OperationFailed:
        pass
    _refresh_render_contract_warnings(lop_node.parent())
    return rop


def _deferred_update_usd_render_rop(session_id):
    node = hou.nodeBySessionId(session_id)
    if node is not None and node.type().name() == OPERATOR_TYPE:
        create_or_update_usd_render_rop(node)


def on_created(kwargs):
    node = kwargs.get("node")
    if node is not None:
        try:
            import hdefereval

            hdefereval.executeDeferred(_deferred_update_usd_render_rop, node.sessionId())
        except Exception:
            create_or_update_usd_render_rop(node)


def _prim_path_tags(select_existing=False, input_index=None):
    tags = {
        "script_action": "import loputils\nloputils.selectPrimsInParm(kwargs, %s)" % (
            "True" if select_existing else "False"
        ),
        "script_action_icon": "BUTTONS_reselect",
        "sidefx::usdpathtype": "prim",
    }
    if input_index is not None:
        tags["sidefx::usdpathinput"] = str(input_index)
    return tags


def _parm_tags(**tags):
    return {key: value for key, value in tags.items() if value is not None}


def _string_prim_path(name, label, default, help_text, select_existing=False, input_index=None):
    parm = hou.StringParmTemplate(
        name,
        label,
        1,
        (default,),
        string_type=hou.stringParmType.Regular,
        help=help_text,
    )
    parm.setTags(_prim_path_tags(select_existing=select_existing, input_index=input_index))
    return parm


def _label(name, label, text):
    return hou.LabelParmTemplate(name, label, (text,))


def _regular_string(name, label, default, help_text):
    return hou.StringParmTemplate(
        name,
        label,
        1,
        (default,),
        string_type=hou.stringParmType.Regular,
        help=help_text,
    )

def _ocio_config():
    try:
        import PyOpenColorIO as ocio
        return ocio, ocio.GetCurrentConfig()
    except Exception:
        return None, None


def _ocio_color_space_name(color_space):
    try:
        return color_space.getName()
    except Exception:
        return ""


def _ocio_color_spaces(config):
    if config is None:
        return []
    try:
        return list(config.getColorSpaces())
    except Exception:
        pass
    try:
        return [config.getColorSpace(name) for name in config.getColorSpaceNames()]
    except Exception:
        return []


def _ocio_categories(color_space):
    categories = []
    try:
        for index in range(color_space.getNumCategories()):
            categories.append(color_space.getCategory(index))
    except Exception:
        pass
    return categories


def _ocio_family(color_space):
    try:
        return color_space.getFamily() or ""
    except Exception:
        return ""


def _ocio_role_color_space(config, role):
    if config is None:
        return ""
    try:
        color_space = config.getColorSpace(role)
        return _ocio_color_space_name(color_space)
    except Exception:
        return ""


def _append_unique(items, token, label=None):
    if token in [item[0] for item in items]:
        return
    items.append((token, label or token))


def _ocio_menu_items(kind):
    _, config = _ocio_config()
    items = []
    if kind == "render":
        _append_unique(items, "", "Auto (OCIO roles)")
        for role in OCIO_RENDER_ROLE_ORDER:
            if role == "default" and len(items) > 1:
                continue
            name = _ocio_role_color_space(config, role)
            if name:
                suffix = "role: %s" % role
                if role == "default":
                    suffix += ", last fallback"
                _append_unique(items, name, "%s (%s)" % (name, suffix))
        keywords = ("render", "scene", "working", "linear")
    else:
        _append_unique(items, "auto", "Auto (OCIO file rules)")
        for role in OCIO_TEXTURE_ROLE_ORDER:
            name = _ocio_role_color_space(config, role)
            if name:
                _append_unique(items, name, "%s (role: %s)" % (name, role))
        keywords = ("texture", "input", "utility", "log", "data", "scene", "linear")

    for color_space in _ocio_color_spaces(config):
        name = _ocio_color_space_name(color_space)
        if not name:
            continue
        haystack = " ".join(
            [name, _ocio_family(color_space)] + _ocio_categories(color_space)
        ).lower()
        if any(keyword in haystack for keyword in keywords):
            _append_unique(items, name)

    return items


def ocio_render_space_menu():
    flat = []
    for token, label in _ocio_menu_items("render"):
        flat.extend([token, label])
    return flat


def ocio_texture_source_menu():
    flat = []
    for token, label in _ocio_menu_items("texture"):
        flat.extend([token, label])
    return flat


def _dialog_menu_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def ocio_texture_source_dialog_menu():
    return " ".join(
        _dialog_menu_quote(item)
        for pair in _ocio_menu_items("texture")
        for item in pair
    )


def _ocio_string_menu(name, label, default, help_text, menu_kind):
    parm = hou.StringParmTemplate(
        name,
        label,
        1,
        (default,),
        string_type=hou.stringParmType.Regular,
        menu_items=tuple(token for token, _ in _ocio_menu_items(menu_kind)),
        menu_labels=tuple(text for _, text in _ocio_menu_items(menu_kind)),
        help=help_text,
    )
    parm.setItemGeneratorScript(
        "import moonray_render_settings\n"
        "return moonray_render_settings.%s()"
        % ("ocio_render_space_menu" if menu_kind == "render" else "ocio_texture_source_menu")
    )
    parm.setItemGeneratorScriptLanguage(hou.scriptLanguage.Python)
    parm.setMenuType(hou.menuType.Normal)
    return parm


def _scene_int(name, label, default, min_value=0, max_value=128, help_text=None):
    return hou.IntParmTemplate(
        "sceneVariable_" + name,
        label,
        1,
        (default,),
        min=min_value,
        max=max_value,
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )


def _scene_float(name, label, default, min_value=0.0, max_value=10.0, help_text=None):
    return hou.FloatParmTemplate(
        "sceneVariable_" + name,
        label,
        1,
        (default,),
        min=min_value,
        max=max_value,
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )


def _scene_toggle(name, label, default, help_text=None):
    return hou.ToggleParmTemplate(
        "sceneVariable_" + name,
        label,
        default_value=default,
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )


def _scene_menu(name, label, tokens, labels, default_token, help_text=None):
    parm = hou.MenuParmTemplate(
        "sceneVariable_" + name,
        label,
        tokens,
        labels,
        default_value=tokens.index(default_token),
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )
    parm.setMenuType(hou.menuType.Normal)
    return parm


TILE_ORDER_TOKENS = (
    "top",
    "bottom",
    "left",
    "right",
    "morton",
    "random",
    "spiral square",
    "spiral rect",
    "morton shiftflip",
)
TILE_ORDER_LABELS = (
    "Top",
    "Bottom",
    "Left",
    "Right",
    "Morton",
    "Random",
    "Spiral Square",
    "Spiral Rect",
    "Morton Shift Flip",
)


def _build_parm_template_group():
    ptg = hou.ParmTemplateGroup()

    render_settings_prim = (
        _label(
            "render_prim_note",
            "",
            "The primitives MUST be located under the /Render/ primitive to match the USD spec.",
        ),
        _string_prim_path(
            "render_settings_prim",
            "RenderSettings Primitive Path",
            RENDER_SETTINGS_PRIM,
            "USD RenderSettings prim authored by this node. Point USD Render ROP or a future MoonRay ROP at this prim.",
            input_index=0,
        ),
        _string_prim_path(
            "render_products_parent_prim",
            "RenderProducts Parent Primitive Path",
            RENDER_PRODUCTS_PARENT_PRIM,
            "Parent prim under which the beauty RenderProduct is authored.",
            select_existing=True,
            input_index=0,
        ),
        _string_prim_path(
            "render_vars_parent_prim",
            "RenderVars Parent Primitive Path",
            RENDER_VARS_PARENT_PRIM,
            "Parent prim under which the first-pass beauty RenderVar is authored.",
            select_existing=True,
            input_index=0,
        ),
    )
    ptg.append(
        hou.FolderParmTemplate(
            "render_settings_prim_folder",
            "Render Settings Prim",
            render_settings_prim,
            folder_type=hou.folderType.Collapsible,
        )
    )

    output_picture = hou.StringParmTemplate(
        "product_name",
        "Output Picture",
        1,
        (PRODUCT_NAME,),
        string_type=hou.stringParmType.FileReference,
        help="Final raster output path authored as RenderProduct.productName. This is separate from debug RDL/RDLA scene export.",
    )
    output_picture.setTags({"filechooser_mode": "write"})
    ptg.append(output_picture)
    ptg.append(
        _string_prim_path(
            "camera",
            "Camera",
            "/cameras/camera1",
            "Render camera prim targeted by the RenderSettings camera relationship.",
            input_index=0,
        )
    )
    ptg.append(
        _label(
            "resolution_mode_note",
            "Resolution Mode",
            "Manual Resolution",
        )
    )
    resolution = hou.IntParmTemplate(
        "resolution",
        "Resolution",
        2,
        DEFAULT_RESOLUTION,
        naming_scheme=hou.parmNamingScheme.XYZW,
        min=1,
        max=8192,
        min_is_strict=True,
        help="Offline husk/USD renders use this resolution through RenderSettings. Viewport/IPR resolution is driven by the viewport.",
    )
    ptg.append(resolution)
    resolution_menu = hou.MenuParmTemplate(
        "resolutionMenu",
        "Choose Resolution",
        (),
        (),
        help="Choose a common image resolution.",
    )
    resolution_menu.setItemGeneratorScript(
        'echo `pythonexprs("__import__(\'toolutils\').parseDialogScriptMenu(\'FBres\')")`'
    )
    resolution_menu.setItemGeneratorScriptLanguage(hou.scriptLanguage.Hscript)
    resolution_menu.setMenuType(hou.menuType.Mini)
    resolution_menu.hideLabel(True)
    resolution_menu.setTags(
        {
            "script_callback": 'opparm . resolution ( `arg("$script_value", 0)` `arg("$script_value", 1)` pixelAspectRatio ( `arg("$script_value", 2)` )'
        }
    )
    ptg.append(resolution_menu)
    pixel_aspect = hou.FloatParmTemplate(
        "pixelAspectRatio",
        "Pixel Aspect Ratio",
        1,
        (1.0,),
        help="Companion value used by Houdini's native resolution preset menu. Authored on RenderSettings and RenderProduct for offline USD output consistency.",
    )
    pixel_aspect.hide(True)
    ptg.append(pixel_aspect)
    ptg.append(
        _label(
            "resolution_note",
            "Resolution Note",
            "Offline husk/USD renders use this RenderSettings resolution. Viewport/IPR resolution is driven by the viewport.",
        )
    )

    color_management = (
        _label(
            "ocio_policy_note",
            "OCIO Policy",
            "MoonRay uses the render process OCIO environment. Texture source spaces use native ImageMap/UsdUVTexture controls; final EXRs remain scene-linear in the selected rendering space.",
        ),
        _ocio_string_menu(
            "renderingColorSpace",
            "Rendering Color Space",
            DEFAULT_RENDERING_COLOR_SPACE,
            "Optional USD RenderSettings.renderingColorSpace. Leave blank to let hdMoonray resolve the active OCIO config roles in priority order: rendering, scene_linear, default_float, reference, then default as a warning fallback. Explicit names must resolve as a color-space name, role, or alias in the active OCIO config.",
            "render",
        ),
        _label(
            "texture_color_policy_note",
            "Texture Source Policy",
            "Native ImageMap source_color_space defaults to auto for OCIO file rules. UsdUVTexture preserves authored USD sourceColorSpace, with an optional source_color_space override. Utility/data choices come from the active OCIO config or file rules.",
        ),
        _label(
            "display_transform_note",
            "Display Transform",
            "MoonRay does not bake display/view transforms into the raster output in this pass. Apply Houdini/Nuke display views downstream.",
        ),
    )
    ptg.append(
        hou.FolderParmTemplate(
            "color_management_folder",
            "Color Management",
            color_management,
            folder_type=hou.folderType.Collapsible,
        )
    )

    update_rop = hou.ButtonParmTemplate(
        "create_update_usd_render_rop",
        "Create / Update USD Render ROP",
        help="Create or repair the USD Render ROP owned by this MoonRay Render Settings LOP.",
    )
    update_rop.setTags(
        {
            "script_callback": "import moonray_render_settings\nmoonray_render_settings.create_or_update_usd_render_rop(hou.pwd())",
            "script_callback_language": "python",
        }
    )
    ptg.append(update_rop)

    beauty_output = (
        hou.ToggleParmTemplate(
            "aov_beauty",
            "Beauty RenderVar / Disk Output Path",
            default_value=True,
            help="Author the Beauty RenderVar required by H20.5 USD Render ROP/husk disk output. Disable only for viewport/default-framebuffer diagnostics.",
        ),
        _label(
            "experimental_aov_note",
            "AOV Status",
            "The AOV tab exposes only native RenderBuffer mappings with production filled-pixel proof. Broader material, LPE, visibility, Cryptomatte, primitive-attribute, and motion-vector AOVs remain deferred.",
        ),
    )

    render_product = (
        hou.StringParmTemplate(
            "render_product_name",
            "RenderProduct Name",
            1,
            (RENDER_PRODUCT_NAME,),
            help="Advanced name for the default beauty RenderProduct authored under the RenderProducts parent prim.",
        ),
        hou.StringParmTemplate(
            "beauty_render_var_name",
            "Beauty RenderVar Name",
            1,
            (BEAUTY_RENDER_VAR_NAME,),
            help="Advanced name for the default beauty RenderVar authored under the RenderVars parent prim.",
        ),
        _label(
            "beauty_note",
            "Beauty Output",
            "Default disk rendering authors a Beauty RenderVar because H20.5 husk rejects raster RenderProducts with no orderedVars. The internal parameter name remains aov_beauty for compatibility.",
        ),
    )

    aov_controls = [
        _label(
            "native_aov_note",
            "Native AOV Scope",
            "These toggles author fixed USD RenderVars for existing hdMoonray native RenderBuffer mappings. They default off and do not imply material/LPE/Cryptomatte or arbitrary AOV support.",
        )
    ]
    for aov in AOV_DEFINITIONS:
        aov_controls.append(
            hou.ToggleParmTemplate(
                aov["parm"],
                aov["label"],
                default_value=False,
                help=aov["help"],
            )
        )

    material_aov_controls = [
        _label(
            "material_aov_note",
            "Material / Denoise AOV Scope",
            "These toggles author documented MoonRay material AOV and denoiser auxiliary RenderVars. They default off and stay limited to production-proven MoonRay material/state-variable contracts.",
        )
    ]
    for aov in MATERIAL_AOV_DEFINITIONS:
        material_aov_controls.append(
            hou.ToggleParmTemplate(
                aov["parm"],
                aov["label"],
                default_value=False,
                help=aov["help"],
            )
        )

    pixel_samples = _scene_int(
        "pixel_samples",
        "Pixel Samples",
        8,
        max_value=4096,
        help_text="The square root of the number of primary samples taken for each pixel in uniform sampling mode.",
    )
    sampling = [
        _scene_menu(
            "sampling_mode",
            "Sampling Mode",
            ("uniform", "adaptive"),
            ("Uniform", "Adaptive"),
            "uniform",
            "Controls which sampling scheme to use: uniform or adaptive.",
        ),
        _scene_menu(
            "light_sampling_mode",
            "Light Sampling Mode",
            ("uniform", "adaptive"),
            ("Uniform", "Adaptive"),
            "uniform",
            "Controls which light sampling scheme to use: uniform or adaptive.",
        ),
        pixel_samples,
        _scene_int(
            "light_samples",
            "Light Samples",
            2,
            max_value=4096,
            help_text="The square root of the number of samples taken for each light on the primary intersection.",
        ),
        _scene_int(
            "bsdf_samples",
            "BSDF Samples",
            2,
            max_value=4096,
            help_text="The square root of the number of samples taken for BSDF lobe evaluations on the primary intersection.",
        ),
        _scene_int(
            "bssrdf_samples",
            "BSSRDF Samples",
            2,
            max_value=4096,
            help_text="The square root of the number of samples taken to evaluate BSSRDF contributions on the primary intersection.",
        ),
    ]
    light_sampling_quality = _scene_float(
        "light_sampling_quality",
        "Light Sampling Quality",
        0.5,
        max_value=1,
        help_text="When the light sampling mode is adaptive, this controls how many lights are sampled per light sample, where 0.0 is low quality and 1.0 is high quality.",
    )
    light_sampling_quality.setConditional(
        hou.parmCondType.DisableWhen,
        '{ sceneVariable_light_sampling_mode != "adaptive" }',
    )
    sampling.insert(2, light_sampling_quality)
    pixel_samples.setConditional(hou.parmCondType.DisableWhen, '{ sceneVariable_sampling_mode != "uniform" }')
    adaptive_cond = '{ sceneVariable_sampling_mode != "adaptive" }'
    for name, label, default, help_text in (
        (
            "sceneVariable_min_adaptive_samples",
            "Min Adaptive Samples",
            16,
            "MoonRay min_adaptive_samples SceneVariable. Used by adaptive sampling.",
        ),
        (
            "sceneVariable_max_adaptive_samples",
            "Max Adaptive Samples",
            4096,
            "MoonRay max_adaptive_samples SceneVariable. Used by adaptive sampling.",
        ),
    ):
        parm = _scene_int(name.replace("sceneVariable_", ""), label, default, max_value=8192, help_text=help_text)
        parm.setConditional(hou.parmCondType.DisableWhen, adaptive_cond)
        sampling.append(parm)
    target_error = _scene_float(
        "target_adaptive_error",
        "Target Adaptive Error",
        10.0,
        max_value=100.0,
        help_text="When adaptive sampling is turned on, this represents the desired quality of the output images.",
    )
    target_error.setConditional(hou.parmCondType.DisableWhen, adaptive_cond)
    sampling.append(target_error)
    sampling.append(
        _scene_toggle(
            "lock_frame_noise",
            "Lock Frame Noise",
            False,
            help_text="Use the same random seed from frame to frame instead of considering the frame number.",
        )
    )

    tile_order = (
        _scene_menu(
            "batch_tile_order",
            "Batch Tile Order",
            TILE_ORDER_TOKENS,
            TILE_ORDER_LABELS,
            "morton",
            "Specifies the order in which tiles are prioritized for batch rendering.",
        ),
        _scene_menu(
            "progressive_tile_order",
            "Progressive Tile Order",
            TILE_ORDER_TOKENS,
            TILE_ORDER_LABELS,
            "morton",
            "Specifies the order in which tiles are prioritized for progressive rendering.",
        ),
        _scene_menu(
            "checkpoint_tile_order",
            "Checkpoint Tile Order",
            TILE_ORDER_TOKENS,
            TILE_ORDER_LABELS,
            "morton",
            "Specifies the order in which tiles are prioritized for checkpoint rendering.",
        ),
    )

    ray_depth = []
    for name, label, default in (
        ("sceneVariable_max_depth", "Max Ray Depth", 5),
        ("sceneVariable_max_diffuse_depth", "Max Diffuse Depth", 2),
        ("sceneVariable_max_glossy_depth", "Max Glossy Depth", 2),
        ("sceneVariable_max_mirror_depth", "Max Mirror Depth", 3),
        ("sceneVariable_max_presence_depth", "Max Presence Depth", 16),
        ("sceneVariable_max_hair_depth", "Max Hair Depth", 5),
        ("sceneVariable_max_volume_depth", "Max Volume Depth", 1),
    ):
        ray_depth.append(
            _scene_int(
                name.replace("sceneVariable_", ""),
                label,
                default,
                max_value=128,
                help_text="MoonRay %s SceneVariable." % name.replace("sceneVariable_", ""),
            )
        )
    ray_depth.extend(
        (
            _scene_int(
                "max_subsurface_per_path",
                "Max Subsurface Per Path",
                1,
                max_value=32,
                help_text='The maximum ray depth to allow subsurface scattering. For ray depths beyond this limit Lambertian diffuse is used to approximate subsurface scattering.',
            ),
            _scene_float(
                "russian_roulette_threshold",
                "Russian Roulette Threshold",
                0.0375,
                max_value=10,
                help_text="The Russian roulette threshold specifies the luminance point at which Russian roulette is evaluated for direct light sampling and BSDF continuation.",
            ),
            _scene_float(
                "transparency_threshold",
                "Transparency Threshold",
                1.0,
                max_value=10,
                help_text="The transparency threshold defines the point at which accumulated opacity can be considered opaque.",
            ),
            _scene_float(
                "presence_threshold",
                "Presence Threshold",
                0.999,
                max_value=10,
                help_text="The presence threshold defines the point at which accumulated presence can be considered opaque.",
            ),
            _scene_float(
                "presence_quality",
                "Presence Quality",
                0.75,
                max_value=10,
                help_text="Controls the threshold for stochastic presence sampling along paths.",
            ),
        )
    )

    clamping = (
        _scene_float(
            "sample_clamping_value",
            "Sample Clamping Value",
            10.0,
            max_value=100,
            help_text="Clamp sample radiance values to this maximum value. A value of 0 disables the effect.",
        ),
        _scene_int(
            "sample_clamping_depth",
            "Sample Clamping Depth",
            1,
            max_value=32,
            help_text="Clamp sample values only after the given non-specular ray depth.",
        ),
        _scene_float(
            "roughness_clamping_factor",
            "Roughness Clamping Factor",
            0.0,
            max_value=10,
            help_text="Clamp material roughness along paths. A value of 1 clamps values to the maximum roughness encountered, while lower values temper the clamping value. 0 disables the effect. Using this technique reduces fireflies from indirect caustics but is biased.",
        ),
    )

    volumes = (
        _scene_float("volume_quality", "Volume Quality", 0.5, max_value=10, help_text="Controls the overall quality of volume rendering."),
        _scene_float("volume_shadow_quality", "Volume Shadow Quality", 1.0, max_value=10, help_text="Controls the quality of volume shadow transmittance."),
        _scene_int("volume_illumination_samples", "Volume Illumination Samples", 4, max_value=128, help_text="Sample number along the ray when computing volume scattering radiance towards the eye. Set to 0 to turn off volume lighting completely."),
        _scene_float("volume_opacity_threshold", "Volume Opacity Threshold", 0.995, max_value=10, help_text="Stop further volume integration when accumulated opacity exceeds this threshold."),
        _scene_menu(
            "volume_overlap_mode",
            "Volume Overlap Mode",
            ("sum", "max", "rnd"),
            ("Sum", "Max", "Random"),
            "sum",
            "Selects how to handle contributions from overlapping volumes.",
        ),
        _scene_float("volume_attenuation_factor", "Volume Attenuation Factor", 0.65, max_value=10, help_text="Controls how volume attenuation gets exponentially scaled down when rendering multiple scattering volumes."),
        _scene_float("volume_contribution_factor", "Volume Contribution Factor", 0.65, max_value=10, help_text="Controls how scattering contribution gets exponentially scaled down when rendering multiple scattering volumes."),
        _scene_float("volume_phase_attenuation_factor", "Volume Phase Attenuation Factor", 0.5, max_value=10, help_text="Controls how phase function anisotropy gets exponentially scaled down when rendering multiple scattering volumes."),
        _scene_int("volume_indirect_samples", "Volume Indirect Samples", 0, max_value=128, help_text="Number of indirect illumination samples on volumes per primary ray."),
    )

    filtering = (
        _scene_float("texture_blur", "Texture Blur", 0.0, max_value=10, help_text="Adjusts the amount of texture filtering."),
        _scene_int("texture_cache_size", "Texture Cache Size (MB)", 4000, max_value=131072, help_text="Maximum MoonRay texture cache size in megabytes. Lower values such as 2048 or 4096 can be useful on memory-constrained macOS systems."),
        _scene_int("texture_file_handles", "Texture File Handles", 24000, max_value=65536, help_text="Maximum number of simultaneous open texture file handles used by MoonRay texture loading."),
        _scene_float("pixel_filter_width", "Pixel Filter Width", 3.0, max_value=10, help_text="The overall extents, in pixels, of the pixel filter."),
        _scene_menu(
            "pixel_filter",
            "Pixel Filter Type",
            ("box", "cubic b-spline", "quadratic b-spline"),
            ("Box", "Cubic B-Spline", "Quadratic B-Spline"),
            "cubic b-spline",
            "The type of filter used for filter importance sampling.",
        ),
    )

    global_toggles = (
        _scene_toggle("enable_dof", "Enable DOF", True, help_text="Enables or disables camera depth-of-field."),
        _scene_toggle("enable_displacement", "Enable Displacement", True, help_text="Enables or disables geometry displacement."),
        _scene_toggle("enable_subsurface_scattering", "Enable Subsurface Scattering", True, help_text="Enables or disables subsurface scattering."),
        _scene_toggle("enable_shadowing", "Enable Shadowing", True, help_text="Enables or disables shadowing through occlusion rays."),
        _scene_toggle("enable_presence_shadows", "Enable Presence Shadows", False, help_text='Whether or not to respect a material\'s "presence" value for shadow rays.'),
        _scene_toggle("lights_visible_in_camera", "Lights Visible in Camera", False, help_text="Globally enables or disables lights being visible in camera."),
        _scene_toggle("propagate_visibility_bounce_type", "Propagate Visibility Bounce Type", False, help_text="Turns on/off propagation for ray visibility masks."),
        _scene_menu(
            "shadow_terminator_fix",
            "Shadow Terminator Fix",
            (
                "Off",
                "On",
                "On (Sine Compensation Alternative)",
                "On (GGX Compensation Alternative)",
                "On (Cosine Compensation Alternative)",
            ),
            (
                "Off",
                "On",
                "On (Sine Compensation Alternative)",
                "On (GGX Compensation Alternative)",
                "On (Cosine Compensation Alternative)",
            ),
            "Off",
            "Attempt to soften hard shadow terminator boundaries due to shading/geometric normal deviations.",
        ),
    )

    debug = (
        _scene_toggle(
            "disable_optimized_hair_sampling",
            "Disable Optimized Hair Sampling",
            False,
            help_text="Forces all hair materials to sample each hair BSDF lobe independently. This is mainly useful for troubleshooting hair LPE label behavior.",
        ),
        hou.StringParmTemplate(
            "rdlOutput",
            "Debug RDL/RDLA Output",
            1,
            ("",),
            string_type=hou.stringParmType.FileReference,
            help="Optional debug scene export path consumed by hdMoonRay rdlOutput. This writes RDL/RDLA scene data, not the final raster image.",
        ),
    )
    debug[0].setTags({"filechooser_mode": "write"})

    ptg.append(
        hou.FolderParmTemplate(
            "moonray_settings",
            "MoonRay Render Settings",
            (
                hou.FolderParmTemplate("render_product", "Render Product", tuple(render_product) + beauty_output),
                hou.FolderParmTemplate("aovs", "AOVs", tuple(aov_controls)),
                hou.FolderParmTemplate("material_denoise_aovs", "Material / Denoise AOVs", tuple(material_aov_controls)),
                hou.FolderParmTemplate("sampling", "Sampling", sampling),
                hou.FolderParmTemplate("tile_order", "Tile Order", tile_order),
                hou.FolderParmTemplate("ray_depth", "Ray Depth / Path", ray_depth),
                hou.FolderParmTemplate("clamping", "Clamping / Fireflies", clamping),
                hou.FolderParmTemplate("volumes", "Volumes", volumes),
                hou.FolderParmTemplate("filtering", "Filtering / Textures", filtering),
                hou.FolderParmTemplate("global_toggles", "Global Toggles", global_toggles),
                hou.FolderParmTemplate("advanced_debug", "Advanced / Debug", tuple(debug)),
            ),
            folder_type=hou.folderType.Tabs,
        )
    )

    return ptg


def regenerate_hda(hda_path):
    """Regenerate the MoonRay Render Settings HDA from this source module."""

    hda_path = Path(hda_path)
    hda_path.parent.mkdir(parents=True, exist_ok=True)
    if hda_path.exists():
        hda_path.unlink()

    stage = hou.node("/stage") or hou.node("/").createNode("lopnet", "stage")
    source = stage.createNode("pythonscript", "moonrayrendersettings_src")
    source.parm("python").set(
        "import hou\n"
        "import moonray_render_settings\n\n"
        "moonray_render_settings.author_from_node(hou.pwd())\n"
    )

    hda_node = source.createDigitalAsset(
        name=OPERATOR_TYPE,
        hda_file_name=str(hda_path),
        description=OPERATOR_LABEL,
        min_num_inputs=0,
        max_num_inputs=1,
        ignore_external_references=True,
    )
    definition = hda_node.type().definition()
    definition.setComment(
        "Authors an artist-friendly USD RenderSettings/RenderProduct setup and curated hdMoonRay moonray:sceneVariable settings."
    )
    definition.setParmTemplateGroup(_build_parm_template_group())
    definition.addSection(
        "OnCreated",
        "import moonray_render_settings\n"
        "moonray_render_settings.on_created(kwargs)\n",
    )
    definition.setExtraFileOption("OnCreated/IsPython", True)
    try:
        definition.setIcon("ROP_usdrender")
    except hou.OperationFailed:
        pass
    definition.updateFromNode(hda_node)
    hda_node.destroy()
    return str(hda_path)
