#!/usr/bin/env hython
"""Development validation for the MoonRay Render Settings LOP lifecycle.

Run with Houdini 20.5 hython:
/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/20.5/Resources/bin/hython \
  /Applications/MoonRay/openmoonray/moonray/moonray_dcc_plugins/houdini/tests/dev_validate_moonray_render_settings_lop.py
"""

from __future__ import annotations

import os
import subprocess
import tempfile

import hou
from pxr import Usd, UsdRender

OPERATOR_TYPE = "Lop::DW_MOONRAY::moonrayrendersettings::1"
ROP_NODE_TYPE = "usdrender_rop"
OUT_ROP_NODE_TYPE = "usdrender"
RENDERER_TOKEN = "HdMoonrayRendererPlugin"
OWNER_LOP_KEY = "moonray_render_settings_lop"
OWNER_OPERATOR_KEY = "moonray_render_settings_operator"
OWNER_SESSION_KEY = "moonray_render_settings_lop_session_id"
EXPECTED_SCENE_VARIABLE_COUNT = 52
EXPECTED_MODULE_SUFFIX = "/plugin/houdini/python3.11libs/moonray_render_settings.py"


RESULTS = []


def _print(status: str, name: str, details: object) -> None:
    RESULTS.append((status, name, str(details)))
    print(f"{status} {name}: {details}")


def pass_(name: str, details: object) -> None:
    _print("PASS", name, details)


def fail(name: str, details: object) -> None:
    _print("FAIL", name, details)


def skip(name: str, details: object) -> None:
    _print("SKIP", name, details)


def check(name: str, condition: bool, details: object) -> None:
    if condition:
        pass_(name, details)
    else:
        fail(name, details)


def disable_when(parm: hou.Parm) -> str | None:
    return parm.parmTemplate().conditionals().get(hou.parmCondType.DisableWhen)


def folder_template_names_and_labels(container) -> list[tuple[str, str]]:
    if hasattr(container, "entries"):
        entries = container.entries()
    else:
        entries = container.parmTemplates()
    names_and_labels = []
    for entry in entries:
        if entry.type() == hou.parmTemplateType.Folder:
            names_and_labels.append((entry.name(), entry.label()))
            names_and_labels.extend(folder_template_names_and_labels(entry))
    return names_and_labels


def clear_scene() -> hou.Node:
    hou.hipFile.clear(suppress_save_prompt=True)
    stage = hou.node("/stage") or hou.node("/").createNode("lopnet", "stage")
    for child in tuple(stage.children()):
        child.destroy()
    return stage


def render_setting_nodes(parent: hou.Node):
    return [child for child in parent.children() if child.type().name() == OPERATOR_TYPE]


def usd_render_rops(parent: hou.Node):
    return [child for child in parent.children() if child.type().name() == ROP_NODE_TYPE]


def out_usd_render_rops():
    out = hou.node("/out")
    if out is None:
        return []
    return [child for child in out.children() if child.type().name() == OUT_ROP_NODE_TYPE]


def owned_rops(parent: hou.Node):
    return [rop for rop in usd_render_rops(parent) if rop.userData(OWNER_OPERATOR_KEY) == OPERATOR_TYPE]


def rop_loppath_target(rop: hou.Node):
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


def rop_info(rop: hou.Node):
    info = {
        "path": rop.path(),
        "input0": rop.input(0).path() if rop.input(0) is not None else None,
        "renderer": rop.parm("renderer").eval() if rop.parm("renderer") else None,
        "loppath": rop.parm("loppath").eval() if rop.parm("loppath") else None,
        "loppath_target": rop_loppath_target(rop),
        "rendersettings": rop.parm("rendersettings").eval() if rop.parm("rendersettings") else None,
        "outputimage": rop.parm("outputimage").eval() if rop.parm("outputimage") else None,
        "owner_path": rop.userData(OWNER_LOP_KEY),
        "owner_operator": rop.userData(OWNER_OPERATOR_KEY),
        "owner_session": rop.userData(OWNER_SESSION_KEY),
    }
    for name in ("loppath", "rendersettings", "outputimage"):
        parm = rop.parm(name)
        if parm is None:
            continue
        try:
            info[name + "_raw"] = parm.rawValue()
        except hou.OperationFailed:
            info[name + "_raw"] = None
        try:
            info[name + "_expr"] = parm.expression()
        except hou.OperationFailed:
            info[name + "_expr"] = None
        try:
            info[name + "_unexpanded"] = parm.unexpandedString()
        except hou.OperationFailed:
            info[name + "_unexpanded"] = None
        try:
            info[name + "_keyframes"] = len(parm.keyframes())
        except hou.OperationFailed:
            info[name + "_keyframes"] = None
        try:
            info[name + "_time_dependent"] = parm.isTimeDependent()
        except hou.OperationFailed:
            info[name + "_time_dependent"] = None
    return info


def rop_graph_state(rop: hou.Node):
    return {
        **rop_info(rop),
        "position": tuple(round(v, 4) for v in rop.position()),
    }


def owned_rop_for_node(node: hou.Node):
    candidates = [rop for rop in owned_rops(node.parent()) if rop_loppath_target(rop) == node.path()]
    return candidates


def create_settings(parent: hou.Node, name: str | None = None) -> hou.Node:
    if name is None:
        return parent.createNode(OPERATOR_TYPE, exact_type_name=True)
    return parent.createNode(OPERATOR_TYPE, name, exact_type_name=True)


def press_repair(node: hou.Node) -> None:
    node.parm("create_update_usd_render_rop").pressButton()


def assert_one_owned_rop(test_name: str, node: hou.Node):
    rops = owned_rop_for_node(node)
    ok = len(rops) == 1 and rops[0].input(0) == node and rops[0].parm("renderer").eval() == RENDERER_TOKEN
    check(test_name, ok, [rop_info(rop) for rop in rops])
    return rops[0] if rops else None


def assert_owned_rop_wiring(test_name: str, node: hou.Node, rop: hou.Node | None) -> None:
    if rop is None:
        fail(test_name, "no owned ROP")
        return
    info = rop_info(rop)
    expected_loppath_raw = '`opinput(".", 0)`'
    expected_settings_raw = '`chs("%s/render_settings_prim")`' % node.path()
    expected_output_raw = '`chs("%s/product_name")`' % node.path()
    ok = (
        info.get("loppath_target") == node.path()
        and info.get("loppath_raw") == expected_loppath_raw
        and info.get("loppath_keyframes") == 0
        and info.get("loppath_time_dependent") is False
        and info.get("rendersettings") == node.parm("render_settings_prim").eval()
        and info.get("rendersettings_raw") == expected_settings_raw
        and info.get("rendersettings_keyframes") == 0
        and info.get("rendersettings_time_dependent") is False
        and info.get("outputimage") == node.parm("product_name").eval()
        and info.get("outputimage_raw") == expected_output_raw
        and info.get("outputimage_keyframes") == 0
        and info.get("outputimage_time_dependent") is False
    )
    check(test_name, ok, info)


def test_module_and_hda() -> None:
    import moonray_render_settings

    module_file = moonray_render_settings.__file__
    check("module_import_path", module_file.endswith(EXPECTED_MODULE_SUFFIX), module_file)
    check("scene_variable_count", len(moonray_render_settings.SCENE_VARIABLES) == EXPECTED_SCENE_VARIABLE_COUNT, len(moonray_render_settings.SCENE_VARIABLES))
    check("native_aov_definition_count", len(moonray_render_settings.AOV_DEFINITIONS) == 9, [aov["parm"] for aov in moonray_render_settings.AOV_DEFINITIONS])
    check(
        "material_aov_definition_count",
        len(moonray_render_settings.MATERIAL_AOV_DEFINITIONS) == 7,
        [aov["parm"] for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS],
    )
    all_aov_parms = [aov["parm"] for aov in moonray_render_settings.AOV_DEFINITIONS] + [
        aov["parm"] for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS
    ]
    forbidden = ("aov_camera_" + "depth", "aov_cryptomatte", "aov_lpe", "aov_visibility", "aov_motion_vector")
    check("forbidden_aov_parms_absent", not any(name in all_aov_parms for name in forbidden), all_aov_parms)
    node_type = hou.lopNodeTypeCategory().nodeTypes().get(OPERATOR_TYPE)
    check("operator_type_name", node_type is not None, OPERATOR_TYPE)
    definition = node_type.definition() if node_type is not None else None
    check("hda_definition_library_path", definition is not None and definition.libraryFilePath().endswith("Lop::DW_MOONRAY::moonrayrendersettings::1.hda"), definition.libraryFilePath() if definition else None)
    matches = []
    for name, node_type in sorted(hou.lopNodeTypeCategory().nodeTypes().items()):
        desc = node_type.description()
        if "moonray" in (name + " " + desc).lower() and "rendersettings" in name.lower():
            node_definition = node_type.definition()
            matches.append(
                {
                    "name": name,
                    "label": desc,
                    "definition": node_definition.libraryFilePath() if node_definition else None,
                }
            )
    check("single_moonray_render_settings_operator_definition", len(matches) == 1 and matches[0]["name"] == OPERATOR_TYPE, matches)


def test_basic_creation_and_repair() -> hou.Node:
    stage = clear_scene()
    before_out = len(out_usd_render_rops())
    node = create_settings(stage, "moonrayrendersettings1")
    check("node_creation", node.type().name() == OPERATOR_TYPE and not node.errors(), {"path": node.path(), "errors": node.errors()})
    product_name = node.parm("product_name")
    check(
        "default_product_name_not_time_dependent",
        product_name is not None and product_name.rawValue().endswith("\\$F4.exr") and not product_name.isTimeDependent(),
        {
            "raw": product_name.rawValue() if product_name else None,
            "eval": product_name.eval() if product_name else None,
            "time_dependent": product_name.isTimeDependent() if product_name else None,
        },
    )
    rop = assert_one_owned_rop("one_owned_connected_usdrender_rop", node)
    assert_owned_rop_wiring("owned_usdrender_rop_uses_lop_expressions", node, rop)
    check("no_out_usdrender_creation", len(out_usd_render_rops()) == before_out, {"before": before_out, "after": len(out_usd_render_rops())})
    before_repair = rop_graph_state(rop) if rop is not None else None
    press_repair(node)
    press_repair(node)
    rop = assert_one_owned_rop("repair_button_idempotency", node)
    assert_owned_rop_wiring("repair_preserves_lop_expression_wiring", node, rop)
    after_repair = rop_graph_state(rop) if rop is not None else None
    check("initial_creation_matches_post_repair_graph", before_repair == after_repair, {"before": before_repair, "after": after_repair})
    return stage


def test_lifecycle_scenarios() -> None:
    stage = clear_scene()

    node1 = create_settings(stage, "moonrayrendersettings1")
    node2 = create_settings(stage, "moonrayrendersettings2")
    distinct = owned_rop_for_node(node1) + owned_rop_for_node(node2)
    check("two_lops_two_distinct_owned_rops", len(distinct) == 2 and len({rop.path() for rop in distinct}) == 2, [rop_info(rop) for rop in distinct])
    check(
        "settings_nodes_do_not_share_rops",
        len(owned_rop_for_node(node1)) == 1
        and len(owned_rop_for_node(node2)) == 1
        and owned_rop_for_node(node1)[0] is not owned_rop_for_node(node2)[0],
        {"node1": [rop_info(rop) for rop in owned_rop_for_node(node1)], "node2": [rop_info(rop) for rop in owned_rop_for_node(node2)]},
    )
    duplicate_warning_key = "moonray_render_contract_warning"
    duplicate_warning_ok = (
        bool(node1.userData(duplicate_warning_key))
        and bool(node2.userData(duplicate_warning_key))
        and all("duplicate MoonRay Render Settings contract" in rop.comment() for rop in distinct)
    )
    check(
        "duplicate_render_contract_paths_warn",
        duplicate_warning_ok,
        {
            "node1_warning": node1.userData(duplicate_warning_key),
            "node2_warning": node2.userData(duplicate_warning_key),
            "rop_comments": [rop.comment() for rop in distinct],
        },
    )

    node1.setName("moonraysettings_renamed")
    press_repair(node1)
    rop1 = assert_one_owned_rop("rename_owner_then_repair_updates_by_session", node1)
    assert_owned_rop_wiring("rename_owner_then_repair_refreshes_expressions", node1, rop1)

    if rop1 is not None:
        rop1.setName("artist_renamed_rop")
        press_repair(node1)
        check("rename_owned_rop_then_repair_preserves_renamed_rop", rop1.name() == "artist_renamed_rop" and rop1.input(0) == node1, rop_info(rop1))
        assert_owned_rop_wiring("rename_owned_rop_then_repair_keeps_expressions", node1, rop1)

        rop1.destroy()
        press_repair(node1)
        rop1 = assert_one_owned_rop("delete_owned_rop_then_repair_recreates", node1)
        assert_owned_rop_wiring("delete_owned_rop_then_repair_recreates_expressions", node1, rop1)

    if rop1 is not None:
        rop1.setInput(0, None)
        press_repair(node1)
        check("disconnect_owned_rop_then_repair_rewires", rop1.input(0) == node1, rop_info(rop1))
        assert_owned_rop_wiring("disconnect_owned_rop_then_repair_keeps_expressions", node1, rop1)

    # Raw HOM copy of only the LOP does not run OnCreated; this is an accepted limitation.
    copied_lop = hou.copyNodesTo((node1,), stage)[0]
    copied_owned = owned_rop_for_node(copied_lop)
    if copied_owned:
        pass_("raw_hom_copy_lop_only", [rop_info(rop) for rop in copied_owned])
    else:
        skip("raw_hom_copy_lop_only", "HOM copy of an existing node does not run OnCreated; press repair on the copied LOP.")
        press_repair(copied_lop)
        assert_one_owned_rop("raw_hom_copy_lop_only_repair", copied_lop)

    pair_node = create_settings(stage, "pairsettings")
    pair_rop = owned_rop_for_node(pair_node)[0]
    copied_items = hou.copyNodesTo((pair_node, pair_rop), stage)
    copied_pair_lops = [item for item in copied_items if item.type().name() == OPERATOR_TYPE]
    copied_pair_rops = [item for item in copied_items if item.type().name() == ROP_NODE_TYPE]
    check("duplicate_lop_rop_pair_raw_copy_non_destructive", len(copied_pair_lops) == 1 and len(copied_pair_rops) == 1, {"lops": [n.path() for n in copied_pair_lops], "rops": [rop_info(r) for r in copied_pair_rops]})
    if copied_pair_lops:
        press_repair(copied_pair_lops[0])
        copied_pair_rop = assert_one_owned_rop("duplicate_lop_rop_pair_repair_refreshes_ownership", copied_pair_lops[0])
        assert_owned_rop_wiring("duplicate_lop_rop_pair_repair_refreshes_expressions", copied_pair_lops[0], copied_pair_rop)

    collision_stage = stage
    foreign = collision_stage.createNode(ROP_NODE_TYPE, "moonrayrendersettings1_usdrender")
    foreign.parm("renderer").set("BRAY_HdKarma")
    collision_node = create_settings(collision_stage, "moonrayrendersettings1")
    check("unrelated_colliding_rop_preserved", foreign.parm("renderer").eval() == "BRAY_HdKarma" and foreign not in owned_rop_for_node(collision_node), [rop_info(rop) for rop in usd_render_rops(collision_stage) if "moonrayrendersettings1_usdrender" in rop.name()])

    fake = stage.createNode(ROP_NODE_TYPE, "moonrayfake_usdrender")
    fake.setUserData(OWNER_OPERATOR_KEY, OPERATOR_TYPE)
    fake.setUserData(OWNER_LOP_KEY, "/stage/not_real")
    fake.parm("renderer").set("BRAY_HdKarma")
    fake_node = create_settings(stage, "moonrayfake")
    check("fake_stale_ownership_not_overwritten", fake.parm("renderer").eval() == "BRAY_HdKarma" and fake not in owned_rop_for_node(fake_node), [rop_info(rop) for rop in usd_render_rops(stage) if "moonrayfake" in rop.name()])

    before_save = len(usd_render_rops(stage))
    hip_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation.hip")
    hou.hipFile.save(hip_path)
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(hip_path, suppress_save_prompt=True, ignore_load_warnings=True)
    loaded_stage = hou.node("/stage")
    after_load = len(usd_render_rops(loaded_stage))
    check("save_reopen_no_extra_rops", before_save == after_load, {"before": before_save, "after": after_load, "file": hip_path})

    node_type = hou.lopNodeTypeCategory().nodeTypes().get(OPERATOR_TYPE)
    definition = node_type.definition() if node_type is not None else None
    if definition is None:
        skip("hda_reload_no_extra_rops", "operator definition unavailable")
    else:
        before_reload = len(usd_render_rops(loaded_stage))
        hou.hda.reloadFile(definition.libraryFilePath())
        after_reload = len(usd_render_rops(loaded_stage))
        check("hda_reload_no_extra_rops", before_reload == after_reload, {"before": before_reload, "after": after_reload, "library": definition.libraryFilePath()})

    loaded_settings = next((child for child in loaded_stage.children() if child.type().name() == OPERATOR_TYPE), None)
    if loaded_settings is None:
        skip("parameter_change_and_cook_no_extra_rops", "no loaded MoonRay Render Settings node found")
    else:
        before_change = len(usd_render_rops(loaded_stage))
        loaded_settings.parm("product_name").set("/tmp/moonray_lifecycle.\\$F4.exr")
        try:
            loaded_settings.cook(force=True)
            details = {"errors": loaded_settings.errors(), "warnings": loaded_settings.warnings()}
        except hou.OperationFailed as exc:
            details = {"exception": str(exc), "errors": loaded_settings.errors(), "warnings": loaded_settings.warnings()}
        after_change = len(usd_render_rops(loaded_stage))
        check("parameter_change_and_cook_no_extra_rops", before_change == after_change, {"before": before_change, "after": after_change, **details})
        loaded_rops = owned_rop_for_node(loaded_settings)
        follows_product = bool(loaded_rops) and loaded_rops[0].parm("outputimage").eval() == loaded_settings.parm("product_name").eval()
        check(
            "owned_rop_outputimage_follows_product_name",
            follows_product,
            {"rops": [rop_info(rop) for rop in loaded_rops], "product_name": loaded_settings.parm("product_name").eval()},
        )

    skip("undo_redo_creation", "Houdini hython does not provide a reliable undo/redo UI event test for this lifecycle; validate manually in UI if needed.")



def test_manual_ui_creation_paths() -> None:
    skip(
        "moonray_menu_tool_creation_path",
        "Requires graphical Houdini 20.5 hou.ui interaction; hython cannot exercise the real MoonRay Tab/shelf UI path.",
    )
    skip(
        "digital_assets_creation_path",
        "Requires graphical Houdini 20.5 Tab menu interaction; hython can report the operator definition but cannot click the Digital Assets entry.",
    )
    skip(
        "mixed_menu_path_two_node_sharing",
        "Requires graphical Houdini 20.5 creation from both menu presentation paths; not claimable from hython.",
    )

def test_resolution_and_usd_contract() -> None:
    stage = clear_scene()
    setup = stage.createNode("pythonscript", "camera_setup")
    setup.parm("python").set(
        "import hou\n"
        "from pxr import UsdGeom, Gf\n"
        "stage = hou.pwd().editableStage()\n"
        "cam = UsdGeom.Camera.Define(stage, '/cameras/camera1')\n"
        "UsdGeom.Xformable(cam).AddTranslateOp().Set(Gf.Vec3d(0, 0, 5))\n"
        "cam.GetHorizontalApertureAttr().Set(40)\n"
        "cam.GetVerticalApertureAttr().Set(20)\n"
    )
    node = create_settings(stage, "moonrayrendersettings1")
    node.setInput(0, setup)

    check("computed_resolution_modes_removed", node.parm("res_mode") is None, "res_mode parm absent")
    mode_note = node.parm("resolution_mode_note")
    check("manual_resolution_mode_note", mode_note is not None, mode_note.eval() if mode_note is not None else None)
    ptg_text = str(node.parmTemplateGroup())
    check(
        "computed_resolution_callbacks_absent",
        "computeResolutionParameter" not in ptg_text and "updateResolutionParameters" not in ptg_text,
        "no loputils computed-resolution callback references",
    )
    import moonray_render_settings

    scene_variable_names = {name for name, _ in moonray_render_settings.SCENE_VARIABLES}
    check(
        "scene_variables_exclude_image_width_height",
        "image_width" not in scene_variable_names and "image_height" not in scene_variable_names,
        sorted(name for name in scene_variable_names if name in ("image_width", "image_height")),
    )
    check(
        "scene_variables_include_texture_cache_controls",
        {"texture_cache_size", "texture_file_handles"}.issubset(scene_variable_names),
        sorted(name for name in scene_variable_names if name in ("texture_cache_size", "texture_file_handles")),
    )
    expected_aov_toggles = sorted(
        ["aov_beauty"]
        + [aov["parm"] for aov in moonray_render_settings.AOV_DEFINITIONS]
        + [aov["parm"] for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS]
    )
    aov_toggles = sorted(
        parm.name()
        for parm in node.parms()
        if parm.name().startswith("aov_")
        and parm.parmTemplate().type() == hou.parmTemplateType.Toggle
    )
    check("aov_toggle_set", aov_toggles == expected_aov_toggles, aov_toggles)
    check("beauty_internal_name_preserved", "aov_beauty" in aov_toggles, aov_toggles)
    beauty = node.parm("aov_beauty")
    beauty_template = beauty.parmTemplate() if beauty is not None else None
    check("beauty_default_on_for_disk_output", beauty is not None and bool(beauty.eval()), beauty.eval() if beauty is not None else None)
    check(
        "beauty_disk_output_label",
        beauty_template is not None and beauty_template.label() == "Beauty RenderVar / Disk Output Path",
        beauty_template.label() if beauty_template is not None else None,
    )
    aov_defaults = {aov["parm"]: node.parm(aov["parm"]).eval() if node.parm(aov["parm"]) is not None else None for aov in moonray_render_settings.AOV_DEFINITIONS}
    check("native_aov_toggles_default_off", all(value == 0 for value in aov_defaults.values()), aov_defaults)
    folders = folder_template_names_and_labels(node.parmTemplateGroup())
    check("native_aov_folder_present", any(label == "AOVs" for _, label in folders), folders)
    check("material_denoise_aov_folder_present", any(label == "Material / Denoise AOVs" for _, label in folders), folders)
    check("color_management_folder_present", any(label == "Color Management" for _, label in folders), folders)
    rendering_color_space = node.parm("renderingColorSpace")
    check(
        "rendering_color_space_control_exists",
        rendering_color_space is not None and rendering_color_space.eval() == "",
        rendering_color_space.eval() if rendering_color_space is not None else None,
    )
    rendering_color_space_template = rendering_color_space.parmTemplate() if rendering_color_space is not None else None
    check(
        "rendering_color_space_has_menu",
        rendering_color_space_template is not None and "ocio_render_space_menu" in rendering_color_space_template.itemGeneratorScript(),
        rendering_color_space_template.itemGeneratorScript() if rendering_color_space_template is not None else None,
    )
    check(
        "deferred_aov_families_not_exposed",
        not any(name in aov_toggles for name in ("aov_camera_" + "depth", "aov_lpe", "aov_cryptomatte", "aov_visibility", "aov_motionvec")),
        aov_toggles,
    )
    sampling_mode_template = node.parm("sceneVariable_sampling_mode").parmTemplate()
    light_sampling_mode_template = node.parm("sceneVariable_light_sampling_mode").parmTemplate()
    sampling_mode_items = sampling_mode_template.menuItems()
    light_sampling_mode_items = light_sampling_mode_template.menuItems()
    check("sampling_menu_items", sampling_mode_items == ("uniform", "adaptive"), sampling_mode_items)
    check("light_sampling_menu_items", light_sampling_mode_items == ("uniform", "adaptive"), light_sampling_mode_items)
    uniform_token, adaptive_token = sampling_mode_items
    _, light_adaptive_token = light_sampling_mode_items
    sampling_conditions = {
        "sceneVariable_pixel_samples": "{ sceneVariable_sampling_mode != %s }" % uniform_token,
        "sceneVariable_min_adaptive_samples": "{ sceneVariable_sampling_mode != %s }" % adaptive_token,
        "sceneVariable_max_adaptive_samples": "{ sceneVariable_sampling_mode != %s }" % adaptive_token,
        "sceneVariable_target_adaptive_error": "{ sceneVariable_sampling_mode != %s }" % adaptive_token,
        "sceneVariable_light_sampling_quality": "{ sceneVariable_light_sampling_mode != %s }" % light_adaptive_token,
    }
    for parm_name, expected in sampling_conditions.items():
        parm = node.parm(parm_name)
        actual = disable_when(parm) if parm is not None else None
        check("sampling_disablewhen_" + parm_name, actual == expected, actual)

    node.parm("camera").set("/cameras/camera1")
    node.parm("resolutionx").set(512)
    node.parm("resolutiony").set(256)
    node.parm("pixelAspectRatio").set(1.25)
    value = tuple(node.parmTuple("resolution").eval())
    check("manual_resolution", value == (512, 256), value)

    node.cook(force=True)
    stage_obj = node.stage()
    settings = UsdRender.Settings(stage_obj.GetPrimAtPath("/Render/rendersettings"))
    product = UsdRender.Product(stage_obj.GetPrimAtPath("/Render/Products/renderproduct"))
    settings_resolution = settings.GetResolutionAttr().Get()
    product_resolution = product.GetResolutionAttr().Get()
    settings_pixel_aspect = settings.GetPixelAspectRatioAttr().Get()
    product_pixel_aspect = product.GetPixelAspectRatioAttr().Get()
    product_camera_targets = product.GetPrim().GetRelationship("camera").GetTargets()
    check(
        "usd_default_contract_settings_product_resolution_match",
        tuple(settings_resolution) == (512, 256) and tuple(product_resolution) == (512, 256),
        {"settings": settings_resolution, "product": product_resolution},
    )
    check(
        "usd_default_contract_settings_product_pixel_aspect_match",
        settings_pixel_aspect == 1.25 and product_pixel_aspect == 1.25,
        {"settings": settings_pixel_aspect, "product": product_pixel_aspect},
    )
    check("usd_default_contract_product_camera_not_authored", not product_camera_targets, product_camera_targets)
    check(
        "usd_default_contract_rendering_color_space_not_authored",
        not settings.GetRenderingColorSpaceAttr().HasAuthoredValueOpinion(),
        settings.GetRenderingColorSpaceAttr().Get(),
    )
    check(
        "usd_default_contract_data_window_not_authored",
        not settings.GetDataWindowNDCAttr().HasAuthoredValueOpinion()
        and not product.GetDataWindowNDCAttr().HasAuthoredValueOpinion(),
        {
            "settings": settings.GetDataWindowNDCAttr().HasAuthoredValueOpinion(),
            "product": product.GetDataWindowNDCAttr().HasAuthoredValueOpinion(),
        },
    )
    check(
        "usd_default_contract_aspect_policy_not_authored",
        not settings.GetAspectRatioConformPolicyAttr().HasAuthoredValueOpinion()
        and not product.GetAspectRatioConformPolicyAttr().HasAuthoredValueOpinion(),
        {
            "settings": settings.GetAspectRatioConformPolicyAttr().HasAuthoredValueOpinion(),
            "product": product.GetAspectRatioConformPolicyAttr().HasAuthoredValueOpinion(),
        },
    )
    usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation.usda")
    node.stage().Flatten().Export(usd_path)
    text = open(usd_path, "r", encoding="utf-8").read()
    default_checks = {
        "RenderSettings": 'def RenderSettings "rendersettings"' in text,
        "RenderProduct": 'def RenderProduct "renderproduct"' in text,
        "RenderVar_by_default": 'def RenderVar "beauty"' in text,
        "products_rel": 'rel products = </Render/Products/renderproduct>' in text,
        "orderedVars_by_default": 'rel orderedVars = </Render/Products/Vars/beauty>' in text,
        "camera_rel": 'rel camera = </cameras/camera1>' in text,
        "resolution": 'uniform int2 resolution = (512, 256)' in text,
        "no_custom_image_width": 'moonray:sceneVariable:image_width' not in text,
        "no_custom_image_height": 'moonray:sceneVariable:image_height' not in text,
    }
    for test_name, ok in default_checks.items():
        check("usd_default_contract_" + test_name, ok, usd_path)
    default_non_beauty_absent = {
        aov["render_var"]: ('def RenderVar "%s"' % aov["render_var"]) not in text
        for aov in moonray_render_settings.AOV_DEFINITIONS
    }
    check("usd_default_contract_non_beauty_aovs_absent", all(default_non_beauty_absent.values()), default_non_beauty_absent)

    node.parm("renderingColorSpace").set("scene_linear")
    node.cook(force=True)
    settings = UsdRender.Settings(node.stage().GetPrimAtPath("/Render/rendersettings"))
    check(
        "usd_rendering_color_space_authored_when_explicit",
        settings.GetRenderingColorSpaceAttr().Get() == "scene_linear",
        settings.GetRenderingColorSpaceAttr().Get(),
    )
    node.parm("renderingColorSpace").set("auto")
    node.cook(force=True)
    settings = UsdRender.Settings(node.stage().GetPrimAtPath("/Render/rendersettings"))
    check(
        "usd_rendering_color_space_auto_not_authored",
        not settings.GetRenderingColorSpaceAttr().HasAuthoredValueOpinion(),
        settings.GetRenderingColorSpaceAttr().Get(),
    )
    node.parm("renderingColorSpace").set("")

    node.parm("sceneVariable_sampling_mode").set(1)
    node.parm("sceneVariable_min_adaptive_samples").set(3)
    node.parm("sceneVariable_max_adaptive_samples").set(99)
    node.parm("sceneVariable_target_adaptive_error").set(7)
    node.cook(force=True)
    adaptive_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_adaptive.usda")
    node.stage().Flatten().Export(adaptive_usd_path)
    adaptive_text = open(adaptive_usd_path, "r", encoding="utf-8").read()
    adaptive_checks = {
        "sampling_mode_adaptive": 'custom token moonray:sceneVariable:sampling_mode = "adaptive"' in adaptive_text,
        "min_adaptive_samples": "custom int moonray:sceneVariable:min_adaptive_samples = 3" in adaptive_text,
        "max_adaptive_samples": "custom int moonray:sceneVariable:max_adaptive_samples = 99" in adaptive_text,
        "target_adaptive_error": "custom float moonray:sceneVariable:target_adaptive_error = 7" in adaptive_text,
        "pixel_samples_still_authored": "custom int moonray:sceneVariable:pixel_samples = 8" in adaptive_text,
    }
    for test_name, ok in adaptive_checks.items():
        check("usd_sampling_toggle_" + test_name, ok, adaptive_usd_path)

    node.parm("sceneVariable_sampling_mode").set(0)
    node.cook(force=True)
    uniform_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_uniform.usda")
    node.stage().Flatten().Export(uniform_usd_path)
    uniform_text = open(uniform_usd_path, "r", encoding="utf-8").read()
    uniform_checks = {
        "sampling_mode_uniform": 'custom token moonray:sceneVariable:sampling_mode = "uniform"' in uniform_text,
        "adaptive_values_preserved_but_inactive": "custom int moonray:sceneVariable:max_adaptive_samples = 99" in uniform_text,
    }
    for test_name, ok in uniform_checks.items():
        check("usd_sampling_toggle_" + test_name, ok, uniform_usd_path)

    node.parm("aov_beauty").set(0)
    node.cook(force=True)
    diagnostic_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_no_beauty.usda")
    node.stage().Flatten().Export(diagnostic_usd_path)
    diagnostic_text = open(diagnostic_usd_path, "r", encoding="utf-8").read()
    diagnostic_checks = {
        "no_RenderVar_when_disabled": 'def RenderVar "beauty"' not in diagnostic_text,
        "empty_orderedVars_when_disabled": 'rel orderedVars' in diagnostic_text and 'rel orderedVars = </Render/Products/Vars/beauty>' not in diagnostic_text,
    }
    for test_name, ok in diagnostic_checks.items():
        check("usd_diagnostic_no_beauty_contract_" + test_name, ok, diagnostic_usd_path)

    node.parm("aov_beauty").set(1)
    node.cook(force=True)
    debug_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_debug_beauty.usda")
    node.stage().Flatten().Export(debug_usd_path)
    debug_text = open(debug_usd_path, "r", encoding="utf-8").read()
    debug_checks = {
        "RenderVar_when_enabled": 'def RenderVar "beauty"' in debug_text,
        "orderedVars_when_enabled": 'rel orderedVars = </Render/Products/Vars/beauty>' in debug_text,
        "beauty_dataType": 'uniform token dataType = "color4f"' in debug_text,
        "beauty_sourceType": 'uniform token sourceType = "raw"' in debug_text,
        "beauty_format": 'driver:parameters:aov:format = "color4f"' in debug_text,
        "beauty_multiSampled": 'driver:parameters:aov:multiSampled = 0' in debug_text,
        "beauty_clearValue": 'driver:parameters:aov:clearValue = 0' in debug_text,
        "beauty_only_orderedVars": debug_text.count("rel orderedVars = </Render/Products/Vars/beauty>") == 1,
    }
    for test_name, ok in debug_checks.items():
        check("usd_debug_beauty_contract_" + test_name, ok, debug_usd_path)

    for aov in moonray_render_settings.AOV_DEFINITIONS:
        node.parm(aov["parm"]).set(1)
    node.cook(force=True)
    native_aov_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_native_aovs.usda")
    node.stage().Flatten().Export(native_aov_usd_path)
    stage_obj = node.stage()
    product = UsdRender.Product(stage_obj.GetPrimAtPath("/Render/Products/renderproduct"))
    targets = [str(target) for target in product.GetOrderedVarsRel().GetTargets()]
    expected_targets = ["/Render/Products/Vars/beauty"] + [
        "/Render/Products/Vars/" + aov["render_var"]
        for aov in moonray_render_settings.AOV_DEFINITIONS
    ]
    check("usd_native_aovs_orderedVars", targets == expected_targets, targets)
    expected_render_vars = {"beauty"} | {aov["render_var"] for aov in moonray_render_settings.AOV_DEFINITIONS}
    vars_prim = stage_obj.GetPrimAtPath("/Render/Products/Vars")
    authored_render_vars = {child.GetName() for child in vars_prim.GetChildren()} if vars_prim.IsValid() else set()
    check("usd_native_aovs_no_extra_renderVars", authored_render_vars == expected_render_vars, sorted(authored_render_vars))
    for aov in moonray_render_settings.AOV_DEFINITIONS:
        path = "/Render/Products/Vars/" + aov["render_var"]
        render_var = UsdRender.Var(stage_obj.GetPrimAtPath(path))
        attrs = {
            "dataType": str(render_var.GetDataTypeAttr().Get()),
            "sourceName": render_var.GetSourceNameAttr().Get(),
            "sourceType": str(render_var.GetSourceTypeAttr().Get()),
            "aov_name": render_var.GetPrim().GetAttribute("driver:parameters:aov:name").Get(),
            "aov_format": str(render_var.GetPrim().GetAttribute("driver:parameters:aov:format").Get()),
            "multiSampled": render_var.GetPrim().GetAttribute("driver:parameters:aov:multiSampled").Get(),
            "clearValue": render_var.GetPrim().GetAttribute("driver:parameters:aov:clearValue").Get(),
        }
        ok = (
            attrs["dataType"] == aov["data_type"]
            and attrs["sourceName"] == aov["source_name"]
            and attrs["sourceType"] == "raw"
            and attrs["aov_name"] == aov["source_name"]
            and attrs["aov_format"] == aov["data_type"]
            and attrs["multiSampled"] is False
            and attrs["clearValue"] == 0
        )
        check("usd_native_aov_contract_" + aov["render_var"], ok, {"path": path, **attrs})

    stage = clear_scene()
    node = create_settings(stage, "moonrayrendersettings1")
    folder_labels = folder_template_names_and_labels(node.parmTemplateGroup())
    check(
        "material_denoise_aov_folder_exists",
        any(label == "Material / Denoise AOVs" for _, label in folder_labels),
        folder_labels,
    )
    for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS:
        parm = node.parm(aov["parm"])
        check("material_aov_toggle_default_off_" + aov["parm"], parm is not None and parm.eval() == 0, parm.eval() if parm else None)

    required_controls = {"aov_denoise_albedo", "aov_denoise_normal"}
    material_controls = {aov["parm"] for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS}
    check("required_denoise_controls_exist", required_controls <= material_controls, sorted(material_controls))

    for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS:
        node.parm(aov["parm"]).set(1)
    node.cook(force=True)
    material_aov_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_material_aovs.usda")
    node.stage().Flatten().Export(material_aov_usd_path)
    stage_obj = node.stage()
    product = UsdRender.Product(stage_obj.GetPrimAtPath("/Render/Products/renderproduct"))
    targets = [str(target) for target in product.GetOrderedVarsRel().GetTargets()]
    expected_targets = ["/Render/Products/Vars/beauty"] + [
        "/Render/Products/Vars/" + aov["render_var"]
        for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS
    ]
    check("usd_material_aovs_orderedVars", targets == expected_targets, targets)
    expected_render_vars = {"beauty"} | {aov["render_var"] for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS}
    vars_prim = stage_obj.GetPrimAtPath("/Render/Products/Vars")
    authored_render_vars = {child.GetName() for child in vars_prim.GetChildren()} if vars_prim.IsValid() else set()
    check("usd_material_aovs_no_extra_renderVars", authored_render_vars == expected_render_vars, sorted(authored_render_vars))
    diagnostic_depth_token = "camera" + "Depth"
    check("usd_material_aovs_no_diagnostic_depth_token", diagnostic_depth_token not in authored_render_vars, sorted(authored_render_vars))
    for aov in moonray_render_settings.MATERIAL_AOV_DEFINITIONS:
        path = "/Render/Products/Vars/" + aov["render_var"]
        render_var = UsdRender.Var(stage_obj.GetPrimAtPath(path))
        prim = render_var.GetPrim()
        attrs = {
            "dataType": str(render_var.GetDataTypeAttr().Get()),
            "sourceName": render_var.GetSourceNameAttr().Get(),
            "sourceType": str(render_var.GetSourceTypeAttr().Get()),
            "aov_name": prim.GetAttribute("driver:parameters:aov:name").Get(),
            "aov_format": str(prim.GetAttribute("driver:parameters:aov:format").Get()),
            "multiSampled": prim.GetAttribute("driver:parameters:aov:multiSampled").Get(),
            "clearValue": prim.GetAttribute("driver:parameters:aov:clearValue").Get(),
        }
        for attr_name in aov.get("extra_attrs", {}):
            attrs[attr_name] = prim.GetAttribute(attr_name).Get()
        ok = (
            attrs["dataType"] == aov["data_type"]
            and attrs["sourceName"] == aov["source_name"]
            and attrs["sourceType"] == aov.get("source_type", "raw")
            and attrs["aov_name"] == aov["source_name"]
            and attrs["aov_format"] == aov["data_type"]
            and attrs["multiSampled"] is False
            and attrs["clearValue"] == 0
        )
        for attr_name, (_, expected_value) in aov.get("extra_attrs", {}).items():
            ok = ok and attrs[attr_name] == expected_value
        check("usd_material_aov_contract_" + aov["render_var"], ok, {"path": path, **attrs})

def test_rdla_receipt() -> None:
    # RDLA export is practical but can be slow; use a tiny lit fixture and a timeout.
    stage = clear_scene()
    setup = stage.createNode("pythonscript", "rdla_setup")
    setup.parm("python").set(
        "import hou\n"
        "from pxr import UsdGeom, UsdLux, Gf\n"
        "stage = hou.pwd().editableStage()\n"
        "cam = UsdGeom.Camera.Define(stage, '/cameras/camera1')\n"
        "UsdGeom.Xformable(cam).AddTranslateOp().Set(Gf.Vec3d(0, 0, 5))\n"
        "UsdGeom.Sphere.Define(stage, '/World/Sphere')\n"
        "light = UsdLux.SphereLight.Define(stage, '/World/Light')\n"
        "light.CreateIntensityAttr().Set(500.0)\n"
        "UsdGeom.Xformable(light).AddTranslateOp().Set(Gf.Vec3d(0, 3, 3))\n"
    )
    node = create_settings(stage, "moonrayrendersettings1")
    node.setInput(0, setup)
    node.parm("rdlOutput").set(os.path.join(tempfile.gettempdir(), "moonray_lifecycle_validation.rdla"))
    node.parm("sceneVariable_target_adaptive_error").set(7.5)
    node.parm("sceneVariable_roughness_clamping_factor").set(0.35)
    node.parm("sceneVariable_light_sampling_quality").set(0.77)
    node.cook(force=True)
    usd_path = os.path.join(tempfile.gettempdir(), "moonray_lifecycle_rdla.usda")
    node.stage().Flatten().Export(usd_path)
    rdla_path = node.parm("rdlOutput").eval()
    husk = "/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/20.5/Resources/bin/husk"
    if not os.path.exists(husk):
        skip("rdla_scenevariable_receipt", "husk not found")
        return
    log_path = "/tmp/moonray_lifecycle_validation_husk.log"
    cmd = [husk, "-R", "HdMoonrayRendererPlugin", "--settings", "/Render/rendersettings", "-o", "/tmp/moonray_lifecycle_validation.exr", usd_path]
    try:
        with open(log_path, "w", encoding="utf-8") as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    except subprocess.TimeoutExpired:
        skip("rdla_scenevariable_receipt", f"husk timed out; see {log_path}")
        return
    if result.returncode != 0 or not os.path.exists(rdla_path):
        skip("rdla_scenevariable_receipt", f"husk/RDLA unavailable rc={result.returncode}; see {log_path}")
        return
    text = open(rdla_path, "r", encoding="utf-8", errors="replace").read()
    ok = all(key in text for key in ("target_adaptive_error", "roughness_clamping_factor", "light_sampling_quality", "texture_cache_size", "texture_file_handles"))
    check("rdla_scenevariable_receipt", ok, rdla_path)


def _time_sampled_attrs(stage: Usd.Stage) -> list[tuple[str, str, tuple[float, ...]]]:
    samples = []
    for prim in stage.Traverse():
        for attr in prim.GetAttributes():
            times = attr.GetTimeSamples()
            if times:
                samples.append((str(prim.GetPath()), attr.GetName(), tuple(times)))
    return samples


def test_native_spotlight_toggle_is_static() -> None:
    stage = clear_scene()
    light = stage.createNode("light", "moonray_spotlight_static_probe")
    light.cook(force=True)

    enable = light.parm("xn__moonraynative_spotlight_rqa")
    control = light.parm("xn__moonrayclass_control_o8a")
    klass = light.parm("xn__moonrayclass_nva")
    if enable is None or control is None or klass is None:
        skip("native_spotlight_static_toggle", "MoonRay Light DS parameters are unavailable")
        return

    before_samples = _time_sampled_attrs(light.stage())
    before_helper = light.userData("moonray_native_spotlight_helper")
    callback = enable.parmTemplate().tags().get("script_callback")
    if not callback:
        fail("native_spotlight_static_toggle", "missing callback")
        return

    enable.set(1)
    exec(callback, {"hou": hou}, {"kwargs": {"node": light, "parm": enable}})
    light.cook(force=True)

    try:
        klass_expression = klass.expression()
    except hou.OperationFailed:
        klass_expression = None

    after_samples = _time_sampled_attrs(light.stage())
    after_helper = light.userData("moonray_native_spotlight_helper")
    details = {
        "node_time_dependent": light.isTimeDependent(),
        "enable": enable.evalAsString(),
        "control": control.evalAsString(),
        "class": klass.evalAsString(),
        "class_raw": klass.rawValue(),
        "class_expression": klass_expression,
        "class_keyframes": [(kf.frame(), kf.expression()) for kf in klass.keyframes()],
        "before_helper_user_data": before_helper,
        "after_helper_user_data": after_helper,
        "before_time_samples": before_samples,
        "after_time_samples": after_samples,
    }
    check(
        "native_spotlight_static_toggle",
        not light.isTimeDependent()
        and enable.eval() == 1
        and control.evalAsString() == "set"
        and klass.evalAsString() == "SpotLight"
        and klass.rawValue() == "SpotLight"
        and klass_expression is None
        and not klass.keyframes()
        and before_helper is None
        and after_helper is None
        and not before_samples
        and not after_samples,
        details,
    )


def main() -> int:
    test_module_and_hda()
    test_basic_creation_and_repair()
    test_lifecycle_scenarios()
    test_manual_ui_creation_paths()
    test_resolution_and_usd_contract()
    test_native_spotlight_toggle_is_static()
    test_rdla_receipt()

    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for status, _, _ in RESULTS:
        counts[status] = counts.get(status, 0) + 1
    print("SUMMARY PASS={PASS} FAIL={FAIL} SKIP={SKIP}".format(**counts))
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
