# MoonRay Render Settings LOP Audit

## Scope

This is a technical development/audit note for the MoonRay Render Settings LOP work in Houdini Solaris. It is not a polished public user manual.

- Validation target for this pass: Houdini 20.5 only.
- Custom node name: `moonrayrendersettings1`.
- Custom HDA/operator: `Lop::DW_MOONRAY::moonrayrendersettings::1`.
- Repo source path: `moonray/moonray_dcc_plugins/houdini/python3.11libs/moonray_render_settings.py`.
- HDA path: `moonray/moonray_dcc_plugins/houdini/otls/Lop::DW_MOONRAY::moonrayrendersettings::1.hda`.
- Installed runtime module path used by Houdini 20.5 validation: `/Applications/MoonRay/installs/openmoonray/plugin/houdini/python3.11libs/moonray_render_settings.py`.
- Houdini 21 evidence is out of scope for this pass and should not be mixed with the Houdini 20.5 results below.

## Evidence-Gated Development Policy

Every important Render Settings, AOV, viewport/IPR, render-buffer, or backend lifecycle claim must be classified as one of:

- `PROVEN`: backed by exact source path/function, command output, exported USD/RDLA, log, installed-runtime provenance, render output, or EXR stats.
- `OBSERVED`: directly seen in Houdini/runtime behavior, but not fully explained.
- `HYPOTHESIS`: plausible explanation with a named test that can prove or disprove it.
- `UNKNOWN`: not enough evidence.
- `OUT OF SCOPE`: intentionally deferred.

Rules:

1. No claim without evidence.
2. No recommendation without a reproducer, source-path proof, exported USD proof, log proof, RDLA proof, render proof, or EXR proof.
3. Do not infer that something is working because a UI folder, parameter, channel, RenderVar, or SceneObject exists.
4. If the render is black, the path is functionally broken until render proof says otherwise.
5. Authored USD alone is not render proof.
6. RDLA/RenderOutput declaration alone is not image-buffer proof.
7. Debug renderer success is not production renderer success.
8. Houdini 21 behavior does not prove Houdini 20.5 behavior.
9. UI cleanup must not hide backend lifecycle, dirtying, render-buffer, AOV binding, or viewport/IPR refresh bugs.
10. If evidence conflicts, report the conflict instead of choosing the convenient explanation.

Primary source-of-truth hierarchy:

1. Local runtime behavior in the target Houdini version, currently H20.5.
2. Exported USD from the exact scene state being tested.
3. Installed hdMoonray source and binaries currently loaded by Houdini.
4. MoonRay native metadata: `/Applications/MoonRay/installs/openmoonray/coredata/SceneVariables.json` and `/Applications/MoonRay/installs/openmoonray/coredata/RenderOutput.json`.
5. MoonRay docs and source.
6. OpenUSD RenderSettings/Product/Var schemas.
7. SideFX Houdini/HDK docs and local Houdini headers.
8. Local project docs and prior audit notes.

Track A is DCC/UI/USD-contract work: custom Render Settings LOP generator, regenerated HDA, validation scripts, docs, and installed/runtime source alignment.

Track B is backend forensic work: backend source tracing, temporary diagnostics, logs, render proof, EXR stats, viewport/IPR lifecycle proof, and runtime symptom proof.

Track A and Track B may run in parallel when UI/USD authoring and backend runtime behavior are coupled. Parallel work is allowed. Unsupported blending is not. DCC/USD evidence and backend/runtime evidence must be separated in reports. Commits should stay separate unless the backend root cause is proven, the fix is narrow, and the diff explains why UI/USD and backend behavior must change together.

Backend files are not forbidden. They may be inspected or temporarily instrumented when runtime evidence points there, especially `RenderBuffer.cc`, `ArrasRenderer.cc`, `RenderPass.cc`, `RenderDelegate.cc`, `UsdRenderers.json`, Beauty/AOV binding lifecycle, render settings dirtying/versioning, and viewport/IPR refresh behavior. Backend behavioral changes require source-path proof, exported USD proof, log proof, and render/EXR or runtime symptom proof before implementation.

Do not flip `aovsupport` because it appears related. Do not broaden non-beauty AOV transport. Do not ship UI-only cleanup as a substitute for backend/runtime proof.

## References Consulted

### OpenUSD RenderSettings / RenderProduct / RenderVar

- [usdRender overview](https://openusd.org/dev/user_guides/schemas/usdRender/overview.html): Used for the RenderSettings, RenderProduct, and RenderVar schema relationship model.
- [RenderSettings schema](https://openusd.org/dev/user_guides/schemas/usdRender/RenderSettings.html): Used to confirm the render settings prim is the global render invocation/configuration prim.
- [RenderProduct schema](https://openusd.org/dev/user_guides/schemas/usdRender/RenderProduct.html): Used to confirm product/output path and ordered render variable ownership.
- [RenderVar schema](https://openusd.org/dev/user_guides/schemas/usdRender/RenderVar.html): Used to confirm output variable/AOV authoring expectations.
- [Render settings proposal](https://openusd.org/release/wp_render_settings.html): Used as background for the USD RenderSettings/Product/Var design.
- [USD render user guide](https://openusd.org/dev/user_guides/render_user_guide.html): Used for the broader USD rendering workflow context.

### SideFX Solaris / USD Render ROP

- [Render Settings LOP](https://www.sidefx.com/docs/houdini/nodes/lop/rendersettings.html): Primary Houdini/Solaris authoring reference.
- [Render Product LOP](https://www.sidefx.com/docs/houdini/nodes/lop/renderproduct.html): Used to compare productName/productType/orderedVars authoring.
- [Render Var LOP](https://www.sidefx.com/docs/houdini/nodes/lop/rendervar.html): Used to compare Beauty RenderVar authoring and driver parameter extras.
- [USD Render ROP](https://www.sidefx.com/docs/houdini/nodes/out/usdrender.html): Used to confirm the USD Render ROP execution/wiring model.

### SideFX HOM / LOP Python

- [hou.LopNode](https://www.sidefx.com/docs/houdini/hom/hou/LopNode.html): Used for Python LOP/HDA stage access and validation.
- [hou.lop](https://www.sidefx.com/docs/houdini/hom/hou/lop.html): Used for Solaris/HOM context.

### SideFX HDK / USD / Hydra

- [HDK USD Hydra customization](https://www.sidefx.com/docs/hdk/_h_d_k__u_s_d_hydra.html): Used for Houdini/Hydra integration context.
- [LOP_Node header/source](https://www.sidefx.com/docs/hdk/_l_o_p___node_8h_source.html): Used for LOP implementation and cooking context.

### SideFX Houdini Digital Asset / UI References

- [Asset UI](https://www.sidefx.com/docs/houdini/assets/asset_ui.html): Used for HDA parameter UI conventions.
- [Editing assets](https://www.sidefx.com/docs/houdini/assets/edit.html): Used for HDA/source-of-truth considerations.
- [Operator Type Properties](https://www.sidefx.com/docs/houdini/ref/windows/optype.html): Used for HDA operator definition behavior.
- [Edit Properties LOP](https://www.sidefx.com/docs/houdini/nodes/lop/editproperties.html): Used as context for Houdini's generic USD property authoring model.

### OpenMoonRay / HdMoonRay

- [HdMoonRay Render Settings](https://docs.openmoonray.org/user-reference/tools/hydra/render-settings/): Used for the MoonRay/Hydra render settings path.
- [HdMoonRay setup](https://docs.openmoonray.org/user-reference/tools/hydra/hdmoonray-setup/): Used for plugin/runtime environment context.
- [HdMoonRay commands](https://docs.openmoonray.org/user-reference/tools/hydra/commands/): Used for `husk`/Hydra command-line context.
- [HdMoonRay Houdini](https://docs.openmoonray.org/user-reference/tools/hydra/hdmoonray-houdini/): Used for Houdini integration context.
- [HdMoonRay features](https://docs.openmoonray.org/user-reference/tools/hydra/hdmoonray-features/): Used for feature support context.
- [MoonRay scene objects](https://docs.openmoonray.org/user-reference/scene-objects/): Used for RDL scene object context.
- [SceneVariables](https://docs.openmoonray.org/user-reference/scene-objects/scene-variables/SceneVariables/): Used to classify MoonRay SceneVariables.
- [RenderOutput](https://docs.openmoonray.org/user-reference/scene-objects/render-output/RenderOutput/): Used for MoonRay-side output/AOV realization.
- [Render outputs guide](https://docs.openmoonray.org/user-reference/how-to-guides/render-outputs/): Used for MoonRay RenderOutput workflow context.
- [OpenMoonRay developer reference](https://docs.openmoonray.org/developer-reference/): Used for developer-level source/library context.

### Autodesk / Arnold AOV References

These were treated only as practical renderer/AOV workflow references, not as MoonRay truth.

- [arnold-usd](https://github.com/Autodesk/arnold-usd)
- [Arnold expression AOVs](https://help.autodesk.com/cloudhelp/ENU/AR-Core/files/ac-output-aovs/arnold_user_guide_ac_output_aovs_ac_expression_aovs_html.html)
- [Arnold AOV shaders](https://help.autodesk.com/cloudhelp/ENU/AR-Core/files/ac-shading/arnold_user_guide_ac_shading_ac_aov_shaders_html.html)
- [Arnold for Cinema 4D AOVs](https://help.autodesk.com/cloudhelp/JPN/AR-Cinema4D/files/ci-arnold-render-settings/arnold_for_cinema_4d_ci_Arnold_Render_Settings_ci_AOVs_html.html)
- [Arnold for 3ds Max AOVs](https://help.autodesk.com/view/3DSMAX/2024/ENU/?guid=arnold_for_3ds_max_ax_render_setup_ax_aovs_html)

## Source of Truth and Runtime Import Rules

The repo `moonray_render_settings.py` is the source of truth for the custom MoonRay Render Settings LOP. The HDA UI and cook-time Python must come from the same definition list. The generated HDA imports `moonray_render_settings` at cook time, so the module imported by Houdini must match the source used to generate the HDA.

Runtime import path used by Houdini 20.5 validation:

```text
/Applications/MoonRay/installs/openmoonray/plugin/houdini/python3.11libs/moonray_render_settings.py
```

Verification commands inside Houdini 20.5 `hython`:

```python
import moonray_render_settings
print(moonray_render_settings.__file__)
print(len(moonray_render_settings.SCENE_VARIABLES))
print(any(name == "enable_dof" for name, _ in moonray_render_settings.SCENE_VARIABLES))
print(any(name == "light_sampling_mode" for name, _ in moonray_render_settings.SCENE_VARIABLES))
```

The drift bug happened because the visible HDA UI was newer than the installed Python module that Houdini imported at cook time. The repo source and HDA contained newer settings, but Houdini 20.5 loaded the stale installed module from the plugin install tree.

The local install-tree sync used during validation copied the repo source and regenerated HDA into the installed plugin tree. That was a validation step, not a final manual-install solution. Future repo/install tooling must keep the HDA and runtime Python module aligned reproducibly.

## Proven Drift Bug

Before the source/install sync:

- HDA UI showed `Enable DOF`.
- Installed runtime module had only 18 SceneVariables.
- `enable_dof` was missing from the installed runtime module.
- Custom USD did not author `moonray:sceneVariable:enable_dof`.
- Custom RDLA kept camera `["dof"] = true`.

After the source/install sync:

- Installed runtime module has 52 SceneVariables.
- `enable_dof` is present.
- `light_sampling_mode` is present.
- Custom USD authors `custom bool moonray:sceneVariable:enable_dof = 0`.
- Custom RDLA contains `["enable_dof"] = false`.

## USD RenderSettings / RenderProduct / RenderVar Contract

The USD render contract is:

- `RenderSettings` owns render invocation/global render settings.
- `RenderSettings` has the render camera relationship.
- `RenderSettings` has the products relationship.
- `RenderProduct` owns `productName`, `productType`, and `orderedVars`.
- `RenderVar` describes an AOV/output variable.
- AOVs flow through `RenderSettings -> RenderProduct -> orderedVars -> RenderVar`.
- The MoonRay backend realizes render outputs as MoonRay `RenderOutput` objects.

Current custom authored paths:

```text
/Render/rendersettings
/Render/Products/renderproduct
/Render/Products/Vars/beauty
```

## Render Product and Output Path Rules

`RenderProduct.productName` is the USD fallback image output path authored by the custom LOP. `$HIP`, `$HIPNAME`, `$OS`, and `$F4` are valid Houdini path tokens, but plain `husk` does not have the same node/project context as a Houdini USD Render ROP. The default custom LOP path escapes the frame token as `\$F4` so the filename remains frame-expandable for husk/ROP execution without making the Render Settings LOP itself time-dependent on the current Houdini frame.

For the owned MoonRay USD Render ROP, the ROP `outputimage` parameter is the primary output authority. It is linked to the LOP `product_name` parameter with a raw backtick HScript string expression so Houdini evaluates `$HIP`, `$HIPNAME`, and `$OS` in the ROP/HIP context while preserving the escaped frame token for husk frame expansion.

When the USD Render ROP `outputimage` override is blank, the RenderProduct output path wins. A Houdini 20.5 smoke test wrote:

```text
/tmp/moonray_render_settings_alignment_after/rop_product.0001.exr
```

That earlier smoke render was black, so it proved USD Render ROP wiring, RenderProduct output creation, and resolution/output path behavior only. The current H20.5 disk-output contract adds the default Beauty RenderVar/`orderedVars` path and has filled EXR proof; this evidence is scoped to Beauty and does not prove non-beauty AOV support.

2026 output-path regression evidence:

- Manual `husk -o /tmp/moonray_manual_husk_test2.exr` with `--settings /Render/rendersettings` writes a valid nonconstant 512x512 RGB float EXR.
- Manual `husk` with an absolute `RenderProduct.productName = "/tmp/moonray_product_abs.exr"` and no `-o` writes a valid nonconstant EXR.
- Manual `husk` with `RenderProduct.productName = "$HIP/render/$HIPNAME.$OS.$F4.exr"` and no `-o` writes `./render/untitled..0001.exr`, proving the fallback path is evaluated without the Houdini ROP/node context.
- A Houdini LOP `usdrender_rop` with blank `outputimage` and absolute `RenderProduct.productName = "/tmp/moonray_product_fallback.exr"` writes a valid nonconstant EXR, proving productName fallback still works when the path is concrete.
- The owned MoonRay ROP now links `outputimage` to the LOP `product_name`; a saved-HIP test wrote `/tmp/moonray_saved_hip_test/render/moonray_test.0001.exr`, not `untitled`.
- A later time-dependency audit showed that raw `$F4` in the custom LOP `product_name` makes the Render Settings LOP time-dependent. Escaping the default as `\$F4` keeps the frame placeholder for the ROP/husk filename but prevents unintended LOP time dependency. The owned ROP uses raw backtick strings such as `` `chs("<owning LOP>/product_name")` `` rather than `parm.setExpression()`, so repair/creation does not create expression keyframes on the owned ROP parms.

## Generic Houdini Render Settings Boundary

The generic Houdini Render Settings LOP with a MoonRay folder is UI integration evidence only. It is not complete render proof.

If flattened USDA has empty `rel products` and no `RenderProduct`, `productName`, or `productType`, generic Render Settings alone is not a complete MoonRay output setup. If it renders black, it is functionally broken until render proof says otherwise.

Generic Render Settings may still be useful as raw/advanced reference UI, but it should not be advertised as the primary working workflow without product/output proof and filled render proof.

## Resolution Behavior

The custom MoonRay Render Settings LOP uses manual resolution only.

Earlier prototypes mirrored Karma's computed camera-aperture modes:

- Set Width, Compute Height from Camera.
- Set Height, Compute Width from Camera.

Those computed modes were removed in the H20.5 UI/lifecycle cleanup pass to reduce callback and lifecycle complexity. The node now exposes a simple `Manual Resolution` note plus a directly editable `Resolution` integer pair.

Validated dimensions:

- Manual: `512 x 256`.

The custom LOP authors final numeric resolution as `RenderSettings.resolution`. It must not author `moonray:sceneVariable:image_width` or `moonray:sceneVariable:image_height`.

### Parameter Authority Policy

The custom MoonRay Render Settings LOP owns the default USD disk-output contract
when it authors both `/Render/rendersettings` and `/Render/Products/renderproduct`.
The policy is:

- The LOP `resolution` tuple is the single source of truth for offline USD
  Render ROP / husk resolution.
- Because the node authors a RenderProduct, it must also author
  `RenderProduct.resolution` to match `RenderSettings.resolution`. Leaving the
  product resolution unauthored lets native/stale/default product opinions
  conflict with the settings resolution, which can change render-pass aspect and
  camera conform behavior.
- `pixelAspectRatio` is a hidden companion parameter used by Houdini's native
  resolution preset menu. When present, it must be authored consistently on both
  RenderSettings and RenderProduct.
- `RenderProduct.camera` is not authored by default; `RenderSettings.camera`
  remains the camera authority for the default product.
- `dataWindowNDC` and `aspectRatioConformPolicy` are left to Solaris/USD schema
  defaults unless a dedicated user-facing control is added and validated.
- Viewport/IPR pixel dimensions remain viewport-driven. This node must still
  keep offline RenderSettings/Product metadata internally consistent so IPR temp
  stages and USD Render ROP exports do not carry contradictory output aspects.

H20.5 validation after the parameter-authority fix authored
`RenderSettings.resolution = (1828, 1332)` and
`RenderProduct.resolution = (1828, 1332)` from the same LOP tuple. It also
authored `pixelAspectRatio = 1.0` on both prims. `dataWindowNDC` and
`aspectRatioConformPolicy` resolved to USD schema fallback values
`(0, 0, 1, 1)` and `expandAperture` with no authored opinion on either prim.

### 2026 Camera / Product / Framing Alignment Audit

This audit was started because 1:1 and other non-camera-aspect renders can
look cropped or framed differently from the Houdini viewport/IPR when using the
custom MoonRay Render Settings LOP plus its owned USD Render ROP.

Evidence preserved before this audit:

```text
/tmp/moonray_camera_output_alignment_20260616_110950
```

Local source evidence:

- Houdini 20.5 USD header
  `/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/Current/Resources/toolkit/include/pxr/usd/usdRender/product.h`
  states that `UsdRenderProduct` inherits `UsdRenderSettingsBase` and provides
  optional overrides to the owning `UsdRenderSettings` prim.
- Houdini 20.5 USD header
  `/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/Current/Resources/toolkit/include/pxr/usd/usdRender/settingsBase.h`
  defines `resolution`, `pixelAspectRatio`, `aspectRatioConformPolicy`,
  `dataWindowNDC`, and `camera` on `UsdRenderSettingsBase`, so both
  RenderSettings and RenderProduct can carry those opinions.
- Houdini 20.5 HUSD header
  `/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/Current/Resources/toolkit/include/HUSD/XUSD_RenderSettings.h`
  exposes product-level override hooks for camera path, resolution, pixel
  aspect, and data window. It also says product values are true overrides only
  when authored on the product.
- Houdini 20.5 Hydra header
  `/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/Current/Resources/toolkit/include/pxr/imaging/hd/renderSettings.h`
  carries flattened `HdRenderSettings::RenderProduct` data including
  `cameraPath`, `resolution`, `pixelAspectRatio`, `aspectRatioConformPolicy`,
  `apertureSize`, and `dataWindowNDC`.
- Houdini 20.5 USD imaging header
  `/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/Current/Resources/toolkit/include/pxr/usdImaging/usdImaging/renderSettingsFlatteningSceneIndex.h`
  describes a scene index that flattens RenderSettings, targeted Products, and
  Vars into `HdRenderSettingsSchema` for Hydra backends.
- hdMoonray source
  `/Applications/MoonRay/source/openmoonray/moonray/hydra/hdMoonray/lib/hydramoonray/RenderPass.cc`
  computes render aspect from `HdRenderPassState::GetFraming().dataWindow`
  when valid, otherwise from viewport size, then calls
  `Camera::setAsPrimaryCamera(renderDelegate, double(w)/h)`.
- hdMoonray source
  `/Applications/MoonRay/source/openmoonray/moonray/hydra/hdMoonray/lib/hydramoonray/Camera.cc`
  adjusts the RDL camera using `CameraUtilConformedWindow`,
  `HdCamera::GetWindowPolicy()`, and the desired image aspect. The current
  path therefore depends on the camera/window policy and render-pass framing
  that Hydra gives hdMoonray, not on the DCC Python directly applying a custom
  crop.

Temporary runtime probes, with no repo source edits, were written under:

```text
/tmp/moonray_product_camera_cases
/tmp/moonray_aspect_marker_cases
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_A.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_B.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_C.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_D.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_E.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_F.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_G.txt
/Users/j7s/houdini-projects/sculpt-practice/render-test/moonray_alignment_case_H.txt
```

Product camera findings:

- Case 1 authored `RenderSettings.camera = /cameras/camera1` and left
  `RenderProduct.camera` absent. A production `husk -R
  HdMoonrayRendererPlugin --settings /Render/rendersettings` render produced
  the red camera1 view.
- Case 2 authored both `RenderSettings.camera` and `RenderProduct.camera` to
  `/cameras/camera1`. The render matched Case 1.
- Case 3 authored `RenderSettings.camera = /cameras/camera1` and
  `RenderProduct.camera = /cameras/camera2`. The render switched to the green
  camera2 view.

Verdict: `RenderProduct.camera` is a real product-level override in the
Houdini/husk path. When absent, husk falls back to `RenderSettings.camera` for
the default product. The custom MoonRay LOP does not need to author
`RenderProduct.camera` for the single default Beauty product. Authoring it by
default would be redundant and could fight future USD Render ROP camera
override workflows. If product-specific cameras are exposed later, they should
be explicit product controls, not an unconditional mirror.

Aspect/framing findings:

- A square `128x128` product with `RenderProduct.camera` absent and explicit
  `expandAperture` matched the same square render with Product.camera authored
  to camera1.
- A square product with explicit `cropAperture` rendered with the same OIIO
  stats as the square `expandAperture` case in the marker probe.
- A square product with explicit full-frame `dataWindowNDC = (0, 0, 1, 1)`
  also matched the square `expandAperture` case.
- A wide `128x72` control rendered different channel statistics from the
  square cases, proving the test was sensitive to output aspect, but not to
  explicit crop-vs-expand policy in this hdMoonray/husk path.

Verdict: the remaining 1:1 framing mismatch is not proven to be caused by
missing `RenderProduct.camera`, missing explicit full-frame `dataWindowNDC`, or
missing explicit `expandAperture` authoring. The stronger suspicion is that the
effective aspect/conform policy is resolved upstream into Hydra camera/framing
state, or is not being propagated/consumed by hdMoonray as expected. Do not
patch the DCC LOP to author Product.camera, dataWindowNDC, or aspect policy as
a blind workaround.

Current policy decision before editing:

| Attribute | Author in MoonRay LOP? | Location | Reason |
|-----------|------------------------|----------|--------|
| `RenderSettings.camera` | yes | Settings | Single default camera authority. |
| `RenderProduct.camera` | no by default | Product | Proven optional override; absent falls back to Settings camera in husk. |
| `RenderSettings.resolution` | yes | Settings | Offline output authority. |
| `RenderProduct.resolution` | yes | Product | Product override must match Settings to avoid stale/native conflicts. |
| `RenderSettings.pixelAspectRatio` | yes | Settings | Hidden Houdini preset companion value. |
| `RenderProduct.pixelAspectRatio` | yes | Product | Product override must match Settings. |
| `RenderSettings.dataWindowNDC` | no | Settings | Full-frame fallback is correct; explicit authoring did not fix square framing. |
| `RenderProduct.dataWindowNDC` | no | Product | Full-frame fallback is correct; explicit authoring did not fix square framing. |
| `RenderSettings.aspectRatioConformPolicy` | no for now | Settings | Fallback is `expandAperture`; explicit crop/expand did not change hdMoonray output in probe. |
| `RenderProduct.aspectRatioConformPolicy` | no for now | Product | Same as Settings; do not author until Hydra/hdMoonray propagation is proven. |
| `productName` | yes | Product | Required disk-output fallback and ROP outputimage source. |
| `productType` | yes | Product | Required raster product contract. |
| `orderedVars` | yes | Product | Required Beauty/AOV output contract. |

The next patch, if any, should be chosen only after comparing a live Houdini IPR
temp USD/render-pass state against the exported USD Render ROP stage. If the
USD is internally consistent but square framing still differs, investigate
hdMoonray camera/window-policy/framing translation before changing DCC
authoring.

## SceneVariables and Render Settings

MoonRay render settings that target RDL `SceneVariables` are authored as `moonray:sceneVariable:*` custom attributes on the `RenderSettings` prim where appropriate.

`image_width` and `image_height` should not be authored by the custom LOP. They appear in RDLA from Hydra/render-pass framing, not from custom USD SceneVariable attributes.

Current custom USD now authors:

- `moonray:sceneVariable:enable_dof`.
- `moonray:sceneVariable:light_sampling_mode`.
- Tile order settings.
- `moonray:sceneVariable:roughness_clamping_factor`.
- `moonray:sceneVariable:target_adaptive_error`.

RDLA proves MoonRay receives `enable_dof`, `light_sampling_mode`, `target_adaptive_error`, and `roughness_clamping_factor`.

| UI label | USD attr | USD type | RDLA key | Current status |
|---------|----------|----------|----------|----------------|
| Enable DOF | `moonray:sceneVariable:enable_dof` | bool | `enable_dof` | working after drift fix |
| Light Sampling Mode | `moonray:sceneVariable:light_sampling_mode` | token/string | `light_sampling_mode` | working after drift fix |
| Target Adaptive Error | `moonray:sceneVariable:target_adaptive_error` | float | `target_adaptive_error` | working after drift fix |
| Roughness Clamping Factor | `moonray:sceneVariable:roughness_clamping_factor` | float | `roughness_clamping_factor` | working after drift fix |
| Image Width | do not author | n/a | `image_width` | render-pass-derived |
| Image Height | do not author | n/a | `image_height` | render-pass-derived |

## Parameter Location Classification

The Render Settings LOP must not absorb every MoonRay or USD setting. Not every `moonray:*` attribute belongs on `RenderSettings`.

| Area | Example | Correct USD location | USD kind | MoonRay/RDL target | Should this Render Settings LOP author it? | Correct authoring path | Status |
|------|---------|----------------------|----------|--------------------|--------------------------------------------|------------------------|--------|
| Render settings | pixel samples | RenderSettings prim | `moonray:sceneVariable:*` attr | SceneVariables | yes | custom Render Settings LOP | verify/working |
| Render output/AOV | beauty/color | RenderProduct plus Beauty RenderVar by default for H20.5 disk output | UsdRenderProduct / UsdRenderVar | Hydra color AOV mapped to MoonRay beauty framebuffer | yes for disk output beauty; diagnostic disable path only | Output / Product | default Beauty RenderVar |
| Geometry settings | `moonray:mesh_resolution` | geometry prim | primvar or namespaced prim attr | RDL geometry setting | no | LOP wrangle / geometry settings node | document only |
| Camera/DOF settings | DOF enable/focus/aperture depending on native behavior | camera prim or RenderSettings depending on proven path | camera attr or SceneVariable | Camera / SceneVariables | only if native path proves it | match H20.5 generic/native | audit |
| Light settings | MoonRay light attrs | light prim | namespaced attrs | RDL light | no | light LOP / light-specific UI | document only |
| Material settings | material/shader attrs | material/shader prim | shader inputs | RDL material | no | material network | document only |
| Debug/RDLA output | RDLA dump path/options | RenderSettings/delegate setting if proven | renderer/debug setting | hdMoonRay/debug | yes, Advanced/Debug only | custom Render Settings LOP | verify |

Do not expose `moonray:mesh_resolution` in the Render Settings LOP as a global render setting. Geometry, light, material, and camera prim-level settings belong on their own prims unless Houdini 20.5 native/generic behavior proves otherwise.

### Sampling Mode Contract

The current H20.5 source and documentation split sampling controls by mode:

- MoonRay `sampling_mode` is a native SceneVariables enum. Local `SceneVariables.json`
  and the public SceneVariables reference define `uniform = 0` and `adaptive = 2`.
- The custom LOP authors token strings, `uniform` and `adaptive`, as
  `moonray:sceneVariable:sampling_mode`; `hdMoonray::ValueConverter` maps those
  enum tokens to the native MoonRay enum values.
- MoonRay `pixel_samples` is the uniform sampling control.
- MoonRay `min_adaptive_samples`, `max_adaptive_samples`, and
  `target_adaptive_error` are adaptive sampling controls.
- MoonRay `light_sampling_mode` uses `uniform = 0` and `adaptive = 1`;
  `light_sampling_quality` is active only in adaptive light sampling mode.

Houdini menu conditionals for this generated HDA use the custom LOP menu token
strings, not native MoonRay enum integer values. The HDA menu items are
`("uniform", "adaptive")`. The custom LOP therefore disables:

- `Pixel Samples` when `sceneVariable_sampling_mode != "uniform"`.
- `Min Adaptive Samples`, `Max Adaptive Samples`, and `Target Adaptive Error`
  when `sceneVariable_sampling_mode != "adaptive"`.
- `Light Sampling Quality` when `sceneVariable_light_sampling_mode != "adaptive"`.

The installed hdMoonray viewport DS uses integer parameters and numeric
disable-when expressions for Display Options. Do not blindly copy those numeric
conditions into the generated custom HDA: the previous numeric-condition attempt
passed a headless HOM probe but regressed the graphical H20.5 custom LOP UI.

Headless Hython validation can inspect the conditional strings, but it does not
prove the graphical disabled/greyed-out state. Fresh H20.5 GUI validation should
still be used before claiming viewport/UI parity with Solaris Display Options.

The LOP currently authors the curated SceneVariables consistently even when a
control is inactive for the selected mode. Validation shows changing sampling
values and toggling `Sampling Mode` updates the exported USD without requiring a
manual dropdown refresh. The inactive values are retained as SceneVariables, but
the UI now communicates which controls are relevant for the selected mode.

Do not add sampling `moonray:sceneVariable:*` keys to
`hdMoonray::RenderSettings::addDescriptors()` as a live-update workaround.
OpenUSD's `HdRenderSettingDescriptor` is a renderer-exported setting descriptor
used by hosts for UI/defaults, and adding these descriptors regressed Houdini
Display Options initialization. The custom LOP should author the USD
RenderSettings attrs; the viewport Display Options should continue to use the
existing DS-declared `sceneVariable_*` controls.

## Native MoonRay SpotLight Toggle Time Dependency

The Light LOP MoonRay tab exposes `Enable Native MoonRay SpotLight` from the
Houdini renderer-property DS files:

```text
houdini/soho/parameters/HdMoonrayRendererPlugin_Light.ds
houdini/soho/parameters/moonray_Light.ds
```

That toggle is a convenience wrapper around the generated MoonRay class override
parameters:

```text
xn__moonrayclass_control_o8a = set
xn__moonrayclass_nva = SpotLight
```

`xn__moonrayclass_nva` has a generated Python-expression default that derives the
MoonRay light class from the Houdini light type. The native-SpotLight callback
must replace that generated expression with a static `SpotLight` token without
leaving keyframes, expressions, helper user data, or USD time samples behind.
Earlier callback variants also wrote `moonray_native_spotlight_helper` node user
data; that bookkeeping was removed because Houdini can draw green network badges
for non-keyframe node data as well as for true time-dependency. H20.5 hython
validation executes the exact callback text and checks:

- the Light LOP remains non-time-dependent;
- the native SpotLight toggle, class-control parm, and class parm have static
  values after enable;
- `xn__moonrayclass_nva` has no expression and no keyframes after enable;
- no `moonray_native_spotlight_helper` user data is written;
- the flattened USD layer has no time-sampled attributes before or after enable.

The static class value is ignored when the control parm is reset to `none`, so
disabling the helper does not author a MoonRay class override.

## Beauty RenderVar and AOV Status

The H20.5 USD Render ROP / husk disk-output workflow now authors a Beauty RenderVar by default. A
custom LOP export with `aov_beauty = 0`, `RenderProduct.productName`, `productType = "raster"`, and
empty `orderedVars` failed in production `husk` with `No orderedVars to specify channels for
/Render/Products/renderproduct`. The same scene with the Beauty RenderVar produced a filled,
nonconstant EXR.

Current default custom LOP contract:

- `aov_beauty = 1`.
- Beauty RenderVar authored by default for disk output.
- `UsdRender.Settings`.
- `UsdRender.Product`.
- `settings.products`.
- `settings.camera`.
- `settings.resolution`.
- `product.productName`.
- `product.productType = "raster"`.
- `orderedVars` targets `/Render/Products/Vars/beauty`.
- Curated `moonray:sceneVariable:*`.

The Beauty control preserves the internal parameter name `aov_beauty` for compatibility. Its label is
`Beauty RenderVar / Disk Output Path`, and it belongs with Render Product/output controls. Disabling
it is a diagnostic viewport/default-framebuffer test path, not the production disk-output default.

This Beauty/default-output contract is separate from non-beauty AOV support. It is the minimal proven
H20.5 disk-output beauty contract.

Custom Beauty RenderVar when `aov_beauty` is enabled:

```text
Path: /Render/Products/Vars/beauty
sourceName = color
sourceType = raw
dataType = color4f
driver:parameters:aov:name = color
driver:parameters:aov:format = color4f
driver:parameters:aov:multiSampled = 0
driver:parameters:aov:clearValue = 0
```

Generic Houdini 20.5 RenderVar extras now aligned:

- `sourceType = raw`.
- `driver:parameters:aov:format = color4f` for the custom MoonRay Beauty RenderVar.
- `driver:parameters:aov:multiSampled = 0`.
- `driver:parameters:aov:clearValue = 0`.

Houdini `customData` appears to be UI/editor metadata and should not be hand-copied unless the integration deliberately adopts the generic/Edit Properties infrastructure.

Native non-beauty AOV status:

- A first native AOV set is exposed as opt-in checkboxes under the `AOVs` tab.
- The exposed set is limited to existing hdMoonray `RenderBuffer.cc` mappings with production filled-pixel proof after the RenderBuffer allocation/channel-count fix: `alpha`, `depth`, `Z`, `N`, `Ng`, `P`, `Wp`, `St`, and `weight`.
- Product-facing depth outputs are `depth` and `Z`.
- The historical diagnostic depth token is not exposed by the custom MoonRay Render Settings LOP in this pass.
- Material AOVs, LPE/light AOVs, visibility AOVs, primitive-attribute AOVs, Cryptomatte, display filters, auxiliary adaptive buffers, and motion vectors remain deferred.
- Debug/local path filling is still not enough for artist UI exposure; future AOVs require production `HdMoonrayRendererPlugin` filled-pixel proof through USD Render ROP/husk or equivalent production path.
- If a production path produces zero-filled buffers again, classify that as backend payload unresolved, not UI-ready.

Do not remove the default Beauty RenderVar for the custom LOP disk-output path unless fresh H20.5
viewport/IPR, USD Render ROP/husk, and filled image/EXR output prove a replacement contract. Do not
extend this evidence to non-beauty AOVs.

Do not claim AOV support from authored RenderVars, metadata, EXR channels, RDLA RenderOutput declarations, or debug renderer success alone.

Current native AOV RenderVar contract:

| UI toggle | RenderVar | sourceName | sourceType | dataType | Status |
|-----------|-----------|------------|------------|----------|--------|
| Beauty RenderVar / Disk Output Path | `beauty` | `color` | `raw` | `color4f` | default on; production Beauty/disk output |
| Alpha | `alpha` | `alpha` | `raw` | `float` | opt-in native AOV |
| Depth | `depth` | `depth` | `raw` | `float` | opt-in native AOV; follows hdMoonray depth mapping |
| Z | `Z` | `Z` | `raw` | `float` | opt-in native state-variable depth |
| N | `N` | `N` | `raw` | `normal3f` | opt-in native state variable |
| Ng | `Ng` | `Ng` | `raw` | `normal3f` | opt-in native state variable |
| P | `P` | `P` | `raw` | `point3f` | opt-in native state variable |
| Wp | `Wp` | `Wp` | `raw` | `point3f` | opt-in native state variable |
| St | `St` | `St` | `raw` | `float2` | opt-in native state variable |
| Weight | `weight` | `weight` | `raw` | `float` | opt-in native RenderOutput; simple fixture produced a constant sample-count value |

All selected native AOVs also author matching `driver:parameters:aov:name`, `driver:parameters:aov:format`, `driver:parameters:aov:multiSampled = 0`, and `driver:parameters:aov:clearValue = 0` attrs. These attrs match the working Beauty path and the H20.5 RenderVar metadata shape, but the source of truth for renderer data remains the `sourceName`/`sourceType` pair consumed by hdMoonray.

Manual H20.5 validation showed `color3f` Beauty output could produce vertical RGB/bayer-like EXR corruption in the explicit Beauty RenderVar path. Switching the custom Beauty RenderVar to `color4f` fixed that corruption by matching the RGBA beauty buffer contract. Copernicus and Nuke both read the resulting EXR channels correctly; an earlier Nuke channel-view issue was user selection error, not file corruption.

## Material / Denoise AOV Contract

Official MoonRay evidence:

- The [moonray_gui documentation](https://docs.openmoonray.org/user-reference/tools/moonray-gui/) states that denoiser auxiliary buffers must be represented by `RenderOutput` objects tagged with `denoiser_input`; names and filenames are not important to the denoiser.
- The documented OIDN albedo auxiliary contract is `result = material aov`, `material aov = D.albedo`, and `denoiser_input = as albedo`.
- The documented OIDN normal auxiliary contract is `result = state variable`, `state variable = N`, `channel_suffix_mode = rgb`, and `denoiser_input = as normal`.
- The [Material AOV guide](https://docs.openmoonray.org/user-reference/how-to-guides/render-outputs/material-aovs/) defines material AOVs as diagnostic material-property outputs with syntax `[('<Label>')+\\.][(SS | R | T | D | G | M)+\\.][fresnel\\.]<property>`.
- `/Applications/MoonRay/installs/openmoonray/coredata/RenderOutput.json` lists the relevant RenderOutput attrs: `result`, `material_aov`, `state_variable`, `channel_format`, `channel_suffix_mode`, and `denoiser_input`.

hdMoonray bridge evidence:

- `RenderBuffer.cc::aovNameFromSettings()` maps `sourceType = shader` to the internal `shader:<sourceName>` form.
- `RenderBuffer.cc::bind()` maps the `shader:` prefix to MoonRay `RESULT_MATERIAL_AOV` and copies `parameters:moonray:<RenderOutput attr>` AOV settings onto the created MoonRay `RenderOutput`.
- Therefore the custom LOP authors material AOV RenderVars with `sourceType = shader` and authors denoiser/channel metadata as `parameters:moonray:*` attrs on the RenderVar.

Current exposed Material / Denoise AOV set:

| UI toggle | RenderVar | sourceName | sourceType | dataType | Extra MoonRay RenderOutput attrs | Status |
|-----------|-----------|------------|------------|----------|----------------------------------|--------|
| Denoise Albedo | `denoise_albedo` | `D.albedo` | `shader` | `color3f` | `denoiser_input = as albedo`, `channel_suffix_mode = rgb`, `channel_format = float` | production H20.5 EXR proof; required OIDN auxiliary |
| Denoise Normal | `denoise_normal` | `N` | `raw` | `normal3f` | `denoiser_input = as normal`, `channel_suffix_mode = rgb`, `channel_format = float` | production H20.5 EXR proof; required OIDN auxiliary |
| Material Albedo | `material_albedo` | `albedo` | `shader` | `color3f` | none | production H20.5 EXR proof |
| Material Emission | `material_emission` | `emission` | `shader` | `color3f` | none | production H20.5 EXR proof |
| Material Normal | `material_normal` | `normal` | `shader` | `normal3f` | `channel_suffix_mode = rgb` | production H20.5 EXR proof |
| Material Roughness | `material_roughness` | `roughness` | `shader` | `float2` | none | production H20.5 EXR proof |
| Material PBR Validity | `material_pbr_validity` | `pbr_validity` | `shader` | `color3f` | none | production H20.5 EXR proof |

The expected OIDN auxiliary set is Beauty/color plus Denoise Albedo plus Denoise Normal. Beauty remains the `color4f` default disk-output RenderVar; the denoise auxiliaries are opt-in and default off.

Discovered but not exposed in this pass:

| Candidate | Official/local status | Reason not exposed |
|-----------|----------------------|--------------------|
| `color` | Listed as a material AOV property in official docs/metadata. | The H20.5 production proof scene did not produce a distinct `color` subimage through the current hdMoonray material-AOV bridge. |
| `factor` | Listed as a material AOV property in official docs/metadata. | The proof scene produced a constant zero output; no meaningful production proof yet. |
| `radius` | Listed as a material AOV property in official docs/metadata. | The proof scene produced a constant zero output; likely needs a subsurface-specific material setup and separate proof. |

Cryptomatte, LPE/light AOVs, visibility AOVs, primitive-attribute AOVs, arbitrary primvars, display-filter outputs, auxiliary adaptive buffers, and motion vectors remain deferred. The historical diagnostic depth token is not product-facing and is not exposed by this LOP.

## USD Render ROP Integration

Houdini 20.5 USD Render ROP parameter names for both LOP `usdrender_rop` and OUT `usdrender`:

- `renderer`.
- `loppath`.
- `rendersettings`.
- `outputimage`.

Houdini 20.5 `husk --list-renderers` sees:

- `HdMoonrayRendererPlugin (Moonray)`.
- `HdMoonrayRendererDebugPlugin (Moonray (debug))`.

Houdini 20.5 USD Render ROP menu shows Moonray. The repaired owned LOP `usdrender_rop` path uses:

```text
renderer = HdMoonrayRendererPlugin
loppath expression = opinput(".", 0)
rendersettings expression = chs("<owning MoonRay Render Settings LOP>/render_settings_prim")
outputimage raw string = `chs("<owning MoonRay Render Settings LOP>/product_name")`
```

Validated output paths:

```text
/tmp/moonray_rop_output_override.exr
/tmp/moonray_saved_hip_test/render/moonray_test.0001.exr
```

Both outputs were valid nonconstant 512x512 RGB float EXRs in H20.5. The socket disconnect message after successful file write remains shutdown noise for these batch renders, not an output-path failure.

## USD Render ROP Auto-Creation Policy

The MoonRay Render Settings LOP intentionally auto-creates a matching USD Render ROP LOP node on node creation. This is part of the desired integrated artist workflow: creating the render settings node should immediately leave the offline render path ready to use.

The custom LOP authors `/Render/rendersettings` and `RenderProduct.productName`. The auto-created `usdrender_rop` LOP is an execution wrapper connected below the settings LOP and pointed at that authored RenderSettings prim. The ROP `outputimage` parameter is linked to the LOP `product_name` parameter so Houdini evaluates `$HIP`, `$HIPNAME`, and `$OS` in a real Houdini ROP/HIP context before launching `husk`; the default frame token is escaped as `\$F4` so it stays scoped to filename/frame expansion and does not mark the custom LOP itself time-dependent.

Houdini 20.5 ROP details:

```text
Context: same LOP network as the MoonRay Render Settings LOP
Node type: usdrender_rop
renderer = HdMoonrayRendererPlugin
loppath = opinput(".", 0)
rendersettings = chs("<current MoonRay Render Settings LOP>/render_settings_prim")
outputimage raw string = `chs("<current MoonRay Render Settings LOP>/product_name")`
```

Ownership is recorded on the ROP with userData:

```text
moonray_render_settings_lop = <owning LOP path>
moonray_render_settings_operator = Lop::DW_MOONRAY::moonrayrendersettings::1
moonray_render_settings_lop_session_id = <owning LOP session id>
```

The deterministic LOP ROP node name is based on the MoonRay Render Settings LOP node name:

```text
/stage/moonrayrendersettings1_usdrender
```

The creation/update helper is idempotent and non-destructive:

- If the owned `usdrender_rop` exists, update it.
- If it does not exist, create it in the same LOP network.
- Running the helper repeatedly must not create duplicates.
- Do not overwrite unrelated user-created USD Render ROP LOPs.
- If the deterministic name already exists but is not owned by the MoonRay Render Settings LOP, create a unique safe name instead.
- Multiple MoonRay Render Settings LOPs should each create a distinct owned ROP.

Rename behavior:

- During the current Houdini session, the helper stores the owning LOP session id and can update the owned ROP after a LOP rename.
- Across saved/reloaded sessions, robust rename recovery may be limited if the old path and session id no longer identify the owner. In that case, the repair helper should avoid overwriting unrelated ROPs and create/update only clearly owned ROPs.

An optional `Create / Update USD Render ROP` repair button calls the same helper used by the HDA `OnCreated` event. It is a secondary repair/update affordance, not a replacement for automatic ROP creation.

Do not auto-create or update ROPs during normal cook or ordinary parameter changes.

## Design Guidelines

- Native Solaris first.
- Use Houdini 20.5 Generic Render Settings as UX/layout reference.
- Expose curated artist controls, not raw metadata dumps.
- Group by task, not JSON order.
- Do not show broken or unverified controls in main artist tabs.
- Put debug/RDLA/internal controls in Advanced/Debug.
- AOV tabs should expose only production-proven outputs.
- Defaults should match Houdini 20.5 Generic/Native or MoonRay defaults unless deliberately changed.
- No node creation Python errors.
- No callback errors on missing camera/path.
- No source/install drift between HDA UI and cook-time Python.

Suggested grouping:

- Output / Product.
- Camera / Resolution.
- Sampling.
- Ray Depth / Path.
- Lighting.
- Volumes.
- Filtering / Textures.
- Clamping / Fireflies.
- AOVs.
- Advanced / Debug.

## MoonRay Parameter Discovery

Parameter discovery for this pass used Houdini 20.5 only. Houdini 21 behavior is intentionally out of scope.

Sources inspected:

- `/Applications/MoonRay/installs/openmoonray/coredata/SceneVariables.json`
- `/Applications/MoonRay/installs/openmoonray/coredata/RenderOutput.json`
- `/Applications/MoonRay/installs/openmoonray/plugin/houdini/soho/parameters/HdMoonrayRendererPlugin_Global.ds`
- `moonray/hydra/hdMoonray/lib/hydramoonray/RenderSettings.cc`
- `moonray/hydra/hdMoonray/lib/hydramoonray/RenderBuffer.cc`
- `moonray/hydra/hdMoonray/lib/hydramoonray/RenderDelegate.cc`
- `moonray/moonray_dcc_plugins/houdini/python3.11libs/moonray_render_settings.py`
- The generated `Lop::DW_MOONRAY::moonrayrendersettings::1` parameter template.
- Houdini 20.5 `rendersettings`, `karmarenderproperties`, `usdrender_rop`, and `usdrender` parameter templates through HOM.

Inventory counts:

- `SceneVariables.json`: 112 attributes.
- `RenderOutput.json`: 37 attributes.
- Current custom MoonRay Render Settings LOP: 52 curated SceneVariable parameters plus default RenderSettings, RenderProduct, productName, productType, and Beauty RenderVar authoring for H20.5 disk output. The `aov_beauty` internal parameter is preserved; disabling it is diagnostic only.

Method:

- Use `SceneVariables.json` as the authoritative MoonRay type/default/enum source for RDL `SceneVariables`.
- Use `HdMoonrayRendererPlugin_Global.ds` as the Houdini 20.5 UI grouping/label/help source where it exposes global render settings.
- Use `RenderSettings.cc` to prove the supported USD render-settings path: `moonray:sceneVariable:<name>` or `sceneVariable_<name>` on the RenderSettings prim, excluding `camera`, `motion_steps`, `enable_motion_blur`, `layer`, `image_width`, and `image_height`.
- Use USD Render docs to decide whether a setting belongs on `RenderSettings`, `RenderProduct`, or `RenderVar`.
- Use `RenderBuffer.cc` and `RenderOutput.json` to classify AOV/output settings. Expose only the native and material/denoise outputs with production-filled proof; keep unproven material candidates plus LPE/light, visibility, primitive-attribute, Cryptomatte, auxiliary, and motion-vector AOV families deferred.

Important boundary:

Not every MoonRay parameter belongs in this LOP. This node authors a Solaris render contract plus curated MoonRay global renderer settings. Geometry, light, camera-prim, and material/shader settings remain outside this node even if they use `moonray:*` names elsewhere.

## Parameter Inventory

This table is a summarized inventory of the parameters relevant to the MoonRay Render Settings LOP decision. The complete raw discovery set is the 112 `SceneVariables` plus 37 `RenderOutput` attributes listed in the metadata files above.

| Source | Raw name | Label | Type | Default | Menu/range | Docs/help | MoonRay/RDL target | USD location | Current custom LOP status | Recommended UI status | Recommended tab | Notes |
|--------|----------|-------|------|---------|------------|-----------|--------------------|--------------|---------------------------|-----------------------|-----------------|-------|
| SceneVariables.json | `sampling_mode` | Sampling Mode | Int enum | `uniform=0` | `uniform=0`, `adaptive=2` | Controls uniform/adaptive sampling. | SceneVariables | RenderSettings prim | exposed/authored as token menu | expose main UI; keep H20.5 token/int validation note | Sampling | RDLA prints enum token; metadata type is Int. |
| SceneVariables.json | `light_sampling_mode` | Light Sampling Mode | Int enum | `uniform=0` | `uniform=0`, `adaptive=1` | Controls light sampling scheme. | SceneVariables | RenderSettings prim | exposed/authored as token menu | expose main UI | Sampling | RDLA-proven in current prototype. |
| SceneVariables.json | `light_sampling_quality` | Light Sampling Quality | Float | `0.5` | `0..1` artist range | Adaptive light sampling quality. | SceneVariables | RenderSettings prim | newly exposed | expose main UI | Sampling | Disabled unless Light Sampling Mode is adaptive. |
| SceneVariables.json | `pixel_samples` | Pixel Samples | Int | `8` | positive int | Primary samples in uniform mode. | SceneVariables | RenderSettings prim | exposed | expose main UI | Sampling | Existing curated control. |
| SceneVariables.json | `light_samples` | Light Samples | Int | `2` | positive int | Samples per light at primary intersection. | SceneVariables | RenderSettings prim | exposed | expose main UI | Sampling | Existing curated control. |
| SceneVariables.json | `bsdf_samples` | BSDF Samples | Int | `2` | positive int | BSDF lobe samples. | SceneVariables | RenderSettings prim | exposed | expose main UI | Sampling | Existing curated control. |
| SceneVariables.json | `bssrdf_samples` | BSSRDF Samples | Int | `2` | positive int | BSSRDF samples. | SceneVariables | RenderSettings prim | exposed | expose main UI | Sampling | Existing curated control. |
| SceneVariables.json | `min_adaptive_samples` | Min Adaptive Samples | Int | `16` | positive int | Adaptive-only min samples. | SceneVariables | RenderSettings prim | exposed | expose main UI | Sampling | Disabled unless Sampling Mode is adaptive. |
| SceneVariables.json | `max_adaptive_samples` | Max Adaptive Samples | Int | `4096` | positive int | Adaptive-only max samples. | SceneVariables | RenderSettings prim | exposed | expose main UI | Sampling | Disabled unless Sampling Mode is adaptive. |
| SceneVariables.json | `target_adaptive_error` | Target Adaptive Error | Float | `10.0` | positive float | Adaptive target error. | SceneVariables | RenderSettings prim | exposed/RDLA-proven | expose main UI | Sampling | Keep float typed to avoid old long-long issue. |
| SceneVariables.json | `lock_frame_noise` | Lock Frame Noise | Bool | `false` | toggle | Locks RNG seed across frames. | SceneVariables | RenderSettings prim | newly exposed | expose main UI | Sampling | Useful animation/render setting. |
| SceneVariables.json | `batch_tile_order` | Batch Tile Order | Int enum | `morton=4` | tile order enum | Batch tile scheduling. | SceneVariables | RenderSettings prim | exposed/authored as token menu | expose main UI | Tile Order | RDLA enum tokens acceptable in current path. |
| SceneVariables.json | `progressive_tile_order` | Progressive Tile Order | Int enum | `morton=4` | tile order enum | Progressive tile scheduling. | SceneVariables | RenderSettings prim | exposed/authored as token menu | expose main UI | Tile Order | Existing curated control. |
| SceneVariables.json | `checkpoint_tile_order` | Checkpoint Tile Order | Int enum | `morton=4` | tile order enum | Checkpoint tile scheduling. | SceneVariables | RenderSettings prim | exposed/authored as token menu | expose main UI | Tile Order | Existing curated control; checkpoint controls otherwise deferred. |
| SceneVariables.json | `max_depth` family | Max Ray Depth family | Int | metadata defaults | positive int | Ray/path depth limits. | SceneVariables | RenderSettings prim | exposed | expose main UI | Ray Depth / Path | Includes diffuse/glossy/mirror/presence/hair/volume. |
| SceneVariables.json | `max_subsurface_per_path` | Max Subsurface Per Path | Int | `1` | positive int | Subsurface path limit. | SceneVariables | RenderSettings prim | exposed | expose main UI | Ray Depth / Path | Existing curated control. |
| SceneVariables.json | `russian_roulette_threshold` | Russian Roulette Threshold | Float | `0.0375` | positive float | Path continuation threshold. | SceneVariables | RenderSettings prim | exposed | expose main UI | Ray Depth / Path | Existing curated control. |
| SceneVariables.json | `transparency_threshold` | Transparency Threshold | Float | `1.0` | positive float | Transparency stop threshold. | SceneVariables | RenderSettings prim | exposed | expose main UI | Ray Depth / Path | Existing curated control. |
| SceneVariables.json | `presence_threshold` | Presence Threshold | Float | `0.999` | positive float | Presence stop threshold. | SceneVariables | RenderSettings prim | exposed | expose main UI | Ray Depth / Path | Existing curated control. |
| SceneVariables.json | `presence_quality` | Presence Quality | Float | `0.75` | positive float | Stochastic presence threshold. | SceneVariables | RenderSettings prim | exposed | expose main UI | Ray Depth / Path | Existing curated control. |
| SceneVariables.json | `disable_optimized_hair_sampling` | Disable Optimized Hair Sampling | Bool | `false` | toggle | Forces independent hair BSDF lobe sampling. | SceneVariables | RenderSettings prim | newly exposed | expose Advanced | Advanced / Debug | Useful but not core artist first-pass. |
| SceneVariables.json | `sample_clamping_value` | Sample Clamping Value | Float | `10.0` | positive float | Radiance sample clamp. | SceneVariables | RenderSettings prim | exposed | expose main UI | Clamping / Fireflies | Existing curated control. |
| SceneVariables.json | `sample_clamping_depth` | Sample Clamping Depth | Int | `1` | positive int | Clamp after depth. | SceneVariables | RenderSettings prim | exposed | expose main UI | Clamping / Fireflies | Existing curated control. |
| SceneVariables.json | `roughness_clamping_factor` | Roughness Clamping Factor | Float | `0.0` | `0..10` artist range | Indirect roughness clamp/firefly reduction. | SceneVariables | RenderSettings prim | exposed/RDLA-proven | expose main UI | Clamping / Fireflies | Mirrored from generic MoonRay tab. |
| SceneVariables.json | `volume_*` curated group | Volume settings | Float/Int/enum | metadata defaults | metadata enums | Global volume quality/overlap/indirect settings. | SceneVariables | RenderSettings prim | exposed | expose main UI | Volumes | Artist-useful volume group only; deep output separate. |
| SceneVariables.json | `texture_blur`, `texture_cache_size`, `texture_file_handles`, `pixel_filter_width`, `pixel_filter` | Filtering / Textures | Float/int/enum | metadata defaults | metadata enum | Texture cache, file handles, and pixel/texture filtering. | SceneVariables | RenderSettings prim | exposed | expose main UI | Filtering / Textures | Texture cache default is 4000 MB; file handles default is 24000. |
| SceneVariables.json | `enable_dof` | Enable DOF | Bool | `true` | toggle | Global DOF enable. | SceneVariables | RenderSettings prim | exposed/RDLA-proven | expose main UI | Global Toggles | Camera focus/aperture remain camera prim settings. |
| SceneVariables.json | `enable_displacement`, `enable_subsurface_scattering`, `enable_shadowing`, `enable_presence_shadows`, `lights_visible_in_camera`, `propagate_visibility_bounce_type`, `shadow_terminator_fix` | Global toggles | Bool/enum | metadata defaults | metadata enum | Global production toggles. | SceneVariables | RenderSettings prim | exposed | expose main UI | Global Toggles | Keep curated; do not include all debug/internal toggles. |
| SceneVariables.json | `image_width`, `image_height` | Image dimensions | Int | `1920`, `1080` | n/a | Image dimensions. | SceneVariables | do not author here | not exposed | do not include in this LOP | n/a | Excluded by `RenderSettings.cc`; use USD RenderSettings resolution. |
| SceneVariables.json | `scene_scale` | Scene Scale | Float | `1.0` | n/a | World unit scale: one world unit equals `scene_scale` meters. | SceneVariables | do not author here by default | not exposed | document only | n/a | Default moved to `1.0`; hdMoonRay automatically bridges USD `metersPerUnit` to `SceneVariables.scene_scale`, while explicit `moonray:sceneVariable:scene_scale` opinions still win. |
| SceneVariables.json | `enable_motion_blur`, `motion_steps`, `fps`, `slerp_xforms` | Motion blur settings | Bool/Float/Vector | metadata defaults | n/a | Motion sampling. | SceneVariables | unknown/special-case | hidden | hide/defer | n/a | `enable_motion_blur` and `motion_steps` are special-cased/excluded in hdMoonRay. |
| SceneVariables.json | checkpoint/resume/deep settings | Checkpoint/deep output | mixed | metadata defaults | mixed | Output/deep/checkpoint internals. | SceneVariables | RenderSettings prim or output workflow | hidden | hide/defer | n/a | Needs separate render execution/deep/checkpoint pass. |
| SceneVariables.json | `output_file`, `primary_aov` | MoonRay native output linkage | String/SceneObject* | metadata defaults | n/a | Native MoonRay output path/AOV linkage. | RenderOutput/SceneVariables | do not author here | hidden | do not include in this LOP | n/a | Use USD RenderProduct.productName and RenderVars. |
| RenderOutput.json / RenderBuffer.cc | `alpha`, `depth`, `Z`, `N`, `Ng`, `P`, `Wp`, `St`, `weight` | Native RenderOutput/state-variable AOVs | mixed | off in UI | fixed native mappings | AOV/output realization. | RenderOutput | RenderVar prim / backend output path | exposed as opt-in native set | production filled proof exists for this set | AOVs | Broader AOV families remain deferred. |
| RenderOutput.json | `material_aov`, `lpe`, `visibility_aov`, primitive attributes, Cryptomatte, auxiliary outputs, motion vectors | Deferred AOV families | mixed | metadata defaults | metadata enums | AOV/output realization. | RenderOutput | RenderVar prim / backend output path | hidden | needs separate production proof | future AOV pass | Do not expose from guessed names. |
| hdMoonRay delegate | `rdlOutput` | Debug RDL/RDLA Output | String | blank | file path | Debug scene export. | delegate/debug setting | delegate/debug setting | exposed debug-only | expose Debug | Advanced / Debug | Not final image output. |
| Geometry prim attrs | `moonray:mesh_resolution` etc. | Geometry settings | mixed | n/a | n/a | Geometry tessellation/subdivision. | RDL geometry | geometry prim | not applicable | do not include in this LOP | n/a | Belongs to Render Geometry Settings. |
| Light prim attrs | per-light `moonray:*` | Light settings | mixed | n/a | n/a | Per-light MoonRay attrs. | RDL light | light prim | not applicable | do not include in this LOP | n/a | Belongs to light-specific UI. |
| Material/shader attrs | shader inputs | Material settings | mixed | n/a | n/a | Material behavior. | RDL material | material/shader prim | not applicable | do not include in this LOP | n/a | Belongs to material networks. |

## Exposed Parameters

Current exposed/custom-authored settings after discovery:

| Tab | Label | Parm name | USD attr / relationship | USD type | Default | Source for type/default | Validation status |
|-----|-------|-----------|-------------------------|----------|---------|-------------------------|------------------|
| Output / Product | RenderSettings Primitive Path | `render_settings_prim` | RenderSettings prim path | path | `/Render/rendersettings` | H20.5 Generic/Karma pattern | validated previously |
| Output / Product | RenderProducts Parent Primitive Path | `render_products_parent_prim` | RenderProduct parent path | path | `/Render/Products` | H20.5 Karma pattern | validated previously |
| Output / Product | RenderVars Parent Primitive Path | `render_vars_parent_prim` | RenderVar parent path | path | `/Render/Products/Vars` | H20.5 Karma pattern | validated previously |
| Output / Product | Output Picture | `product_name` | `RenderProduct.productName` | token | `$HIP/render/$HIPNAME.$OS.\$F4.exr` | USD RenderProduct / H20.5 Karma pattern | Escaped frame token prevents unintended LOP time dependency while preserving frame expansion for ROP/husk. |
| Camera / Resolution | Camera | `camera` | `RenderSettings.camera` relationship | rel | `/cameras/camera1` | H20.5 Karma pattern | validated previously |
| Camera / Resolution | Resolution Mode | `resolution_mode_note` | UI note only | n/a | Manual Resolution | H20.5 lifecycle cleanup decision | computed modes intentionally removed |
| Camera / Resolution | Resolution | `resolution` | `RenderSettings.resolution` and `RenderProduct.resolution` | `int2` | `1920, 1080` | USD RenderSettings / RenderProduct | validated; product resolution must match settings resolution |
| Camera / Resolution | Pixel Aspect Ratio | `pixelAspectRatio` | `RenderSettings.pixelAspectRatio` and `RenderProduct.pixelAspectRatio` | float | `1.0` | USD RenderSettingsBase / Houdini resolution preset callback | hidden companion parm; authored consistently |
| Output / Product | Beauty RenderVar / Disk Output Path | `aov_beauty` | `RenderProduct.orderedVars` + Beauty RenderVar | RenderVar | enabled | H20.5 `husk`/EXR evidence | Default disk-output path validated; disabled state is diagnostic only |
| Sampling | Sampling Mode | `sceneVariable_sampling_mode` | `moonray:sceneVariable:sampling_mode` | token-authored enum | `uniform` | SceneVariables metadata | RDLA token path proven for enum style |
| Sampling | Light Sampling Mode | `sceneVariable_light_sampling_mode` | `moonray:sceneVariable:light_sampling_mode` | token-authored enum | `uniform` | SceneVariables metadata | RDLA-proven |
| Sampling | Light Sampling Quality | `sceneVariable_light_sampling_quality` | `moonray:sceneVariable:light_sampling_quality` | float | `0.5` | SceneVariables metadata | RDLA-proven; disabled unless Light Sampling Mode is adaptive |
| Sampling | Pixel/Light/BSDF/BSSRDF Samples | `sceneVariable_*_samples` | `moonray:sceneVariable:*` | int | metadata defaults | SceneVariables metadata | validated for authoring; Pixel Samples disabled unless Sampling Mode is uniform |
| Sampling | Min/Max Adaptive Samples, Target Adaptive Error | `sceneVariable_min_adaptive_samples`, etc. | `moonray:sceneVariable:*` | int/float | metadata defaults | SceneVariables metadata | validated for authoring/toggle updates; adaptive controls disabled unless Sampling Mode is adaptive |
| Sampling | Lock Frame Noise | `sceneVariable_lock_frame_noise` | `moonray:sceneVariable:lock_frame_noise` | bool | false | SceneVariables metadata | newly added; needs RDLA validation |
| Tile Order | Batch/Progressive/Checkpoint Tile Order | `sceneVariable_*_tile_order` | `moonray:sceneVariable:*` | token-authored enum | `morton` | SceneVariables metadata | validated previously for authored attrs |
| Ray Depth / Path | Ray depth/path controls | `sceneVariable_max_*`, thresholds | `moonray:sceneVariable:*` | int/float | metadata defaults | SceneVariables metadata | validated previously for representative attrs |
| Clamping / Fireflies | Sample/Roughness clamps | `sceneVariable_sample_clamping_*`, `sceneVariable_roughness_clamping_factor` | `moonray:sceneVariable:*` | int/float | metadata defaults | SceneVariables metadata / generic MoonRay tab | roughness RDLA-proven |
| Volumes | Volume group | `sceneVariable_volume_*` | `moonray:sceneVariable:*` | int/float/token | metadata defaults | SceneVariables metadata / Global.ds | authored; representative validation needed |
| Filtering / Textures | Texture cache, file handles, texture blur, and pixel filter controls | `sceneVariable_texture_cache_size`, `sceneVariable_texture_file_handles`, etc. | `moonray:sceneVariable:*` | int/float/token | metadata defaults | SceneVariables metadata / Global.ds | authored; representative validation needed |
| Global Toggles | Production toggles | `sceneVariable_enable_*`, etc. | `moonray:sceneVariable:*` | bool/token | metadata defaults | SceneVariables metadata / Global.ds | `enable_dof` RDLA-proven |
| Advanced / Debug | Disable Optimized Hair Sampling | `sceneVariable_disable_optimized_hair_sampling` | `moonray:sceneVariable:disable_optimized_hair_sampling` | bool | false | SceneVariables metadata | newly added; needs RDLA validation |
| Advanced / Debug | Debug RDL/RDLA Output | `rdlOutput` | `rdlOutput` | string | blank | hdMoonRay delegate setting | validated previously |

## Hidden / Deferred Parameters

| Parameter/group | Reason | Correct authoring location | Future work |
|-----------------|--------|----------------------------|-------------|
| `image_width`, `image_height` | Excluded in hdMoonRay `RenderSettings.cc`; dimensions are driven by USD RenderSettings/Hydra framing. | `RenderSettings.resolution`, not `moonray:sceneVariable:*` | none for this LOP |
| `scene_scale` | Not exposed in the Render Settings LOP UI. The renderer now derives it from USD stage `metersPerUnit` unless explicitly authored as `moonray:sceneVariable:scene_scale`; raw light/material/camera/geometry distances remain unscaled. | renderer/unit-policy bridge | GUI/IPR parity check only |
| `motion_steps`, `enable_motion_blur`, `fps`, `slerp_xforms` | hdMoonRay has special handling/exclusions; motion blur path not validated for this UI. | future motion blur/settings pass | audit and implement separately |
| Checkpoint/resume settings | Execution/output behavior, not first-pass RenderSettings authoring. | future ROP/execution workflow | checkpoint pass |
| Deep output settings | Deep output is AOV/output-system work. | future AOV/deep pass | defer |
| Texture cache/file handles | Performance/cache policy and environment-sensitive. | Advanced only after validation | defer |
| `output_file`, `primary_aov`, `two_stage_output` | Native MoonRay output wiring conflicts with USD RenderProduct model unless carefully designed. | RenderProduct/ROP/backend output design | defer |
| `machine_id`, `num_machines`, `task_distribution_type`, `athena_debug` | Arras/internal/debug. | backend/Arras context | do not include |
| `max_geometry_resolution`, `enable_max_geometry_resolution`, `fast_geometry_update` | Geometry/procedural behavior, not artist render contract. | geometry/procedural settings | document only |
| Deferred RenderOutputs/AOVs | Unproven material candidates plus LPE/light, visibility, primitive-attribute, Cryptomatte, auxiliary, display-filter, and motion-vector paths are not part of the exposed proven set. | RenderVar + backend AOV pipeline | future AOV pass |

## Geometry / Camera / Light / Material Boundaries

- `moonray:mesh_resolution` is geometry-level and must not be exposed in this Render Settings LOP.
- Per-light MoonRay attributes belong on light prims or light-specific tooling.
- Material/shader attributes belong in material networks.
- Camera focal/aperture/focus settings belong on camera prims unless Houdini 20.5 native/generic behavior proves a different RenderSettings-level path.
- The global `enable_dof` SceneVariable is included because it is a real SceneVariable and RDLA-proven through `moonray:sceneVariable:enable_dof`; it does not replace camera prim DOF controls.

## Final Tab Architecture

| Final tab | Purpose | Parameters to include | Parameters explicitly excluded | Notes |
|----------|---------|-----------------------|-------------------------------|-------|
| Output / Product | USD render contract and output path | RenderSettings path, products parent, vars parent, output picture, optional advanced product/beauty names | Native MoonRay `output_file`, `primary_aov` | RenderProduct.productName remains final image output source. |
| Camera / Resolution | Render camera and offline resolution | Camera, manual resolution note, resolution | computed width/height modes, `image_width`, `image_height`, camera lens/focus attrs | Uses USD RenderSettings resolution and camera rel. |
| Sampling | Main sampling controls | sampling mode, light sampling mode/quality, sample counts, adaptive controls, lock frame noise | unrelated debug RNG/internal controls | Adaptive controls disabled when inactive. |
| Ray Depth / Path | Path limits and thresholds | max depth family, subsurface per path, russian roulette, transparency/presence threshold/quality | geometry resolution limits | SceneVariables only. |
| Lighting | Global lighting behavior if it remains useful as a separate tab | currently no separate tab; light sampling lives in Sampling and lights visibility in Global Toggles | per-light attrs | Keep per-light UI elsewhere. |
| Volumes | Global volume controls | volume quality/shadow/illumination/opacity/overlap/factors/indirect samples | deep output settings | Uses useful volume group from metadata/DS. |
| Filtering / Textures | Texture/pixel filtering | texture cache size, texture file handles, texture blur, pixel filter width/type | texture conversion/OCIO behavior | Cache controls exposed from `SceneVariables.json`; texture color management remains separate. |
| Clamping / Fireflies | Firefly reduction | sample clamp value/depth, roughness clamping factor | none currently | Roughness clamp mirrored from generic MoonRay tab. |
| AOVs | Artist AOV checkboxes | alpha, depth, Z, N, Ng, P, Wp, St, weight | material/LPE/light/visibility/primitive-attribute/Cryptomatte/motion-vector families | Native set only; all toggles default off. |
| Advanced / Debug | Troubleshooting/low-level controls | disable optimized hair sampling, debug RDL/RDLA output | Arras/internal/debug dumps and default Beauty disk-output controls | Keep sparse. |

## What Still Remains

- Broader AOV backend/UI work beyond the first native RenderBuffer set.
- Possible separate geometry settings LOP or expanded geometry tooling.
- Possible light/material-specific UI passes.
- Production filled Beauty proof, distinct from output-file smoke proof.
- Install/runtime tooling to prevent HDA UI and cook-time Python drift.

## HDA Lifecycle and Node Graph Mutation Policy

The MoonRay Render Settings LOP has a small amount of node-graph automation: when the LOP is created, it creates a connected LOP `usdrender_rop` configured for `HdMoonrayRendererPlugin`. This lifecycle policy documents where node graph mutation is allowed and where it is forbidden.

Validation target:

```bash
/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/20.5/Resources/bin/hython \
  /Applications/MoonRay/openmoonray/moonray/moonray_dcc_plugins/houdini/tests/dev_validate_moonray_render_settings_lop.py
```

Current validation summary:

```text
PASS=44
FAIL=0
SKIP=6
```

Skipped tests:

- `raw_hom_copy_lop_only`: Houdini HOM copy of an existing node does not run `OnCreated`; press the repair button on the copied LOP.
- `moonray_menu_tool_creation_path`: requires graphical Houdini 20.5 `hou.ui` interaction; hython cannot exercise the real MoonRay Tab/shelf UI path.
- `digital_assets_creation_path`: requires graphical Houdini 20.5 Tab menu interaction; hython can report the operator definition but cannot click the Digital Assets entry.
- `mixed_menu_path_two_node_sharing`: requires graphical Houdini 20.5 creation from both menu presentation paths.
- `undo_redo_creation`: Hython does not provide a reliable UI undo/redo event test for this lifecycle; validate manually in Houdini UI if needed.
- `rdla_scenevariable_receipt`: The optional RDLA smoke test timed out in the dev harness. This is not a lifecycle failure and should be rerun manually when render/RDLA timing is stable.

### Python Entry Points

| Entry point | File/location | When it runs | What it mutates | Safe? | Notes |
|------------|---------------|--------------|-----------------|-------|-------|
| HDA `OnCreated` | `Lop::DW_MOONRAY::moonrayrendersettings::1.hda` section `OnCreated` | Fresh MoonRay Render Settings LOP creation | Creates or updates one owned connected LOP `usdrender_rop` | Yes | Does not run on file load or HDA definition reload in H20.5 validation. |
| `author_from_node()` | `houdini/python3.11libs/moonray_render_settings.py` | HDA Python cook/export | USD stage only | Yes | Must not create, delete, rename, or wire Houdini nodes. |
| `create_or_update_usd_render_rop()` | `houdini/python3.11libs/moonray_render_settings.py` | HDA `OnCreated` and explicit repair button | Owned LOP `usdrender_rop` only | Yes | Idempotent; preserves unrelated ROPs. |
| `resolution_mode_note` label | generated HDA parameter | Display only | Nothing | Yes | Computed resolution mode callbacks were removed; manual resolution only. |
| resolution preset callback | generated HDA parameter tag | Resolution preset menu use | Resolution parameter values only | Yes | No ROP creation. |
| `Create / Update USD Render ROP` button callback | generated HDA parameter tag | Explicit user button press | Owned LOP `usdrender_rop` only | Yes | Repair/update affordance. |
| `MoonRayTools.shelf` tool | `houdini/toolbar/MoonRayTools.shelf` | Shelf/tab tool creation | Creates MoonRay Render Settings LOP via `loptoolutils.genericTool` | Yes | Shelf/tool behavior only; not cook-time behavior. |
| Module import | `moonray_render_settings.py` | Python import | Nothing | Yes | Import-time code must remain side-effect free. |
| `regenerate_hda()` | `moonray_render_settings.py` | Explicit developer regeneration | Creates temporary source node and HDA definition | Yes for dev only | Not a runtime artist action. |

### Allowed Mutation Points

- HDA `OnCreated` may create one owned LOP `usdrender_rop` for a fresh MoonRay Render Settings LOP.
- The explicit `Create / Update USD Render ROP` button may create, repair, or reconnect the owned LOP `usdrender_rop`.
- Shelf/tool creation may create the MoonRay Render Settings LOP through Houdini's `loptoolutils.genericTool`.

### Forbidden Mutation Points

- Cook/export must not create, delete, rename, connect, or rewire Houdini nodes.
- Ordinary parameter changes must not create ROPs.
- File load must not create extra ROPs.
- HDA definition reload must not create extra ROPs.
- Import-time code must not mutate the scene.
- Unrelated user-created `usdrender_rop` nodes must never be overwritten.

### Owned USD Render ROP Model

The owned ROP is a LOP `usdrender_rop`, not an `/out/usdrender` node.

Owned ROP values:

```text
renderer = HdMoonrayRendererPlugin
loppath = opinput(".", 0)
rendersettings = chs("<owning MoonRay Render Settings LOP>/render_settings_prim")
outputimage raw string = `chs("<owning MoonRay Render Settings LOP>/product_name")`
```

Ownership userData keys:

```text
moonray_render_settings_lop = <owning LOP path>
moonray_render_settings_operator = Lop::DW_MOONRAY::moonrayrendersettings::1
moonray_render_settings_lop_session_id = <owning LOP session id>
```

The helper uses the owner path, owner operator type, and session id to identify the owned ROP. The session id lets repair recover after renaming the owning LOP during the same Houdini session. A comment is also written on the ROP for human inspection.

### Operator Registration / Menu Entry Policy

Houdini 20.5 HOM sees one MoonRay Render Settings LOP operator definition:

| Menu entry | Operator type | Label | Definition path | Source mechanism | Creates node type | Stale/duplicate? | Recommended action |
|------------|---------------|-------|-----------------|------------------|-------------------|------------------|--------------------|
| Digital Assets entry | `Lop::DW_MOONRAY::moonrayrendersettings::1` | MoonRay Render Settings | `/Applications/MoonRay/installs/openmoonray/plugin/houdini/otls/Lop::DW_MOONRAY::moonrayrendersettings::1.hda` | Houdini generic HDA fallback/category listing | Same operator type | Not a second definition | Document; do not delete. |
| MoonRay shelf/tab entry | `Lop::DW_MOONRAY::moonrayrendersettings::1` | MoonRay Render Settings | same installed HDA path | `MoonRayTools.shelf` using `loptoolutils.genericTool` | Same operator type | Intended renderer-specific tool path | Keep. |

The observed `Digital Assets` and `MoonRay` entries are menu presentation paths for the same installed operator definition, not two separate MoonRay Render Settings operators. Do not remove the generic Digital Assets entry blindly. Users should prefer the MoonRay shelf/tab entry, but both creation paths must create the same operator type and should be lifecycle-safe.

Known installed/generated HDA paths observed during this work:

```text
/Applications/MoonRay/installs/openmoonray/plugin/houdini/otls/Lop::DW_MOONRAY::moonrayrendersettings::1.hda
/Applications/MoonRay/source/openmoonray/moonray/moonray_dcc_plugins/houdini/otls/Lop::DW_MOONRAY::moonrayrendersettings::1.hda
```

The H20.5 validation runtime used the installed plugin HDA path.

### USD Render ROP Initial Creation Policy

Initial creation and the repair button use the same idempotent helper, `create_or_update_usd_render_rop()`.

In graphical Houdini, `OnCreated` schedules only one deferred helper call through `hdefereval.executeDeferred`. The deferred pass exists because shelf/tool creation can finalize node naming, wiring, and placement after the HDA `OnCreated` hook starts. This avoids creating an incorrect intermediate ROP and then repairing it. The deferred call uses the same idempotent helper and the owning node session id, so it creates the final owned ROP in the same state as the explicit repair button. Hython does not provide `hdefereval`, so H20.5 command-line validation uses the immediate fallback path only.

Manual graphical Houdini 20.5 validation is still required before claiming the MoonRay shelf/menu path and the Digital Assets menu path are fully fixed. The command-line harness proves direct HDA/HOM behavior and records UI-only creation paths as skipped, not passed.

Expected initial creation behavior:

- Create exactly one owned connected LOP `usdrender_rop`.
- Connect it below the owning MoonRay Render Settings LOP.
- Set `renderer = HdMoonrayRendererPlugin`.
- Set `loppath` to `opinput(".", 0)`, normalized by validation to the owning MoonRay Render Settings LOP path.
- Set `rendersettings` to `chs("<owning LOP>/render_settings_prim")`.
- Set `outputimage` to the raw string `` `chs("<owning LOP>/product_name")` `` so the owned ROP follows the LOP output path without creating expression keyframes.
- Do not create `/out/usdrender`.
- Do not overwrite unrelated `usdrender_rop` nodes.

The repair button is only a repair/update affordance. It should not be required after normal creation. H20.5 hython validation confirms initial creation already matches repair behavior for direct HDA node creation; manual UI validation should still be used for shelf/menu presentation quirks.

Current validation also confirms:

- ROP graph comparisons include `moonray_render_settings_lop`, `moonray_render_settings_operator`, and `moonray_render_settings_lop_session_id`.
- Two MoonRay Render Settings LOPs do not share the same owned `usdrender_rop`.
- Beauty remains the default disk-output RenderVar. The AOV tab exposes only the first native, production-filled RenderBuffer set with toggles defaulting off.
- Computed resolution mode parms and `loputils.computeResolutionParameter` / `loputils.updateResolutionParameters` callback references are absent.
- `image_width` and `image_height` are absent from the curated `SCENE_VARIABLES` list and are not authored as custom USD SceneVariables.

### Frame Range and ROP Handoff

SideFX USD Render ROP documentation separates authored USD time metadata from
the ROP's actual render frame range. A layer can contain `startTimeCode`,
`endTimeCode`, `framesPerSecond`, and `timeCodesPerSecond`, but the USD Render
ROP still needs its `Valid Frame Range`/`trange` mode to request a sequence from
`husk`.

The owned MoonRay `usdrender_rop` keeps the native USD Render ROP default of
rendering the current frame. To render a sequence, set the ROP to a frame-range
mode, such as `Render Specific Frame Range`, or to the stage-driven mode when
that is the desired native USD Render ROP behavior.

H20.5 headless validation using the owned ROP, the committed output-path wiring,
and an existing proven MoonRay USD scene rendered frames `1-5` in explicit frame
range mode to:

```text
/tmp/moonray_frame_range_existing_usd/render/moonray_seq.0001.exr
/tmp/moonray_frame_range_existing_usd/render/moonray_seq.0002.exr
/tmp/moonray_frame_range_existing_usd/render/moonray_seq.0003.exr
/tmp/moonray_frame_range_existing_usd/render/moonray_seq.0004.exr
/tmp/moonray_frame_range_existing_usd/render/moonray_seq.0005.exr
```

All five files were valid nonconstant RGB float EXRs. The render launched a
separate `syncId:1` render per frame and did not reproduce the reported
single-render `syncId:1`, resolution-change, `syncId:2/3/4` restart sequence.
That restart sequence remains a GUI/runtime observation to investigate with a
normal H20.5 session, especially with viewport/IPR active versus inactive.

Stage-driven range mode was also checked against
`/Users/j7s/houdini-projects/simple-render-test/stage/stagetest-2.usda`, whose
root layer metadata contains `startTimeCode = 1` and `endTimeCode = 5`. With
the owned ROP set to `trange = stage`, H20.5 rendered frames `1-5`, wrote no
frames `6-7`, and produced valid nonconstant RGB float EXRs.

### EXR Metadata Observations

Current MoonRay/Husk output still records only generic color metadata such as
`oiio:ColorSpace = "Linear"` for the tested EXRs. It does not currently prove
specific ACEScg, Linear Rec.709, or Linear Rec.2020 EXR chromaticities/OCIO
metadata in the DCC wrapper layer.

Several tested EXRs also contain suspicious `renderTime_s` and `renderMemory_s`
values, such as render times far longer than the observed render wall time. Local
source inspection points to MoonRay/Husk/image-writing metadata paths rather than
the custom DCC ROP wrapper, so this audit records the issue but does not patch it
in the DCC layer.

### Lifecycle Scenario Summary

| Scenario | Result | Notes |
|----------|--------|-------|
| Create one MoonRay Render Settings LOP | PASS | One owned connected `usdrender_rop` is created. |
| Click repair button twice | PASS | No duplicate ROPs. |
| Initial graph equals post-repair graph | PASS | Direct HDA creation matches repair state, including placement. |
| Create two MoonRay Render Settings LOPs | PASS | Two distinct owned ROPs. |
| Settings nodes share one ROP | PASS | They do not share; each settings node owns one distinct ROP. |
| Rename owning LOP, then repair | PASS | Owned ROP updates by session id. |
| Rename owned `usdrender_rop`, then repair | PASS | Renamed ROP is preserved and updated in place. |
| Delete owned `usdrender_rop`, then repair | PASS | Owned ROP is recreated. |
| Disconnect owned `usdrender_rop`, then repair | PASS | Owned ROP is rewired. |
| Raw HOM copy of LOP only | SKIP/limitation | `OnCreated` does not run for raw HOM copy; repair is required. |
| Duplicate LOP+ROP pair | PASS with limitation | Non-destructive; copied ROP may have stale ownership until repair refreshes it. |
| Unrelated colliding ROP | PASS | Existing unrelated Karma/usdrender ROP is preserved. |
| Fake/stale ownership ROP | PASS | Stale/fake ROP is preserved; new owned ROP is created. |
| Save/reopen file | PASS | No extra ROPs are created. |
| HDA definition reload | PASS | No extra ROPs are created. |
| Parameter change + cook | PASS | No node graph mutation. |
| `/out/usdrender` creation | PASS | None created. |
| MoonRay menu/tool path | SKIP | Requires graphical Houdini 20.5. |
| Digital Assets menu path | SKIP | Requires graphical Houdini 20.5. |
| One node from each menu path | SKIP | Requires graphical Houdini 20.5. |
| Undo/redo | SKIP | Needs manual UI validation; not reliable in hython. |

### MoonRayTools.shelf Justification

The `MoonRayTools.shelf` change is intentional and should be kept. It updates shelf/tab creation behavior so the tool is available in LOP viewer/network contexts and creates the node with Houdini's `loptoolutils.genericTool`, matching Solaris tool conventions better than direct `kwargs["node"].createNode(...)`.

This shelf change:

- Affects shelf/tab creation only.
- Is not cook-time behavior.
- Is not backend/AOV behavior.
- Is not responsible for `usdrender_rop` mutation during cook.

### Known Accepted Limitations

- Raw HOM copy/paste of only the MoonRay Render Settings LOP does not auto-create a ROP because `OnCreated` is not run; press the repair button.
- Duplicating a LOP+ROP pair can leave stale ownership userData on the copied ROP until repair is pressed.
- Undo/redo lifecycle behavior still needs manual UI validation.
- MoonRay shelf/menu creation and Digital Assets menu creation still need real graphical Houdini 20.5 validation. Do not claim those menu paths are fully fixed from hython evidence alone.
- These limitations are non-destructive and accepted for now.

## Validation Checklist

Future passes should validate:

- [ ] Confirm Houdini 20.5 `hython` path.
- [ ] Confirm Houdini 20.5 `husk` path.
- [ ] Confirm `moonray_render_settings.__file__`.
- [ ] Confirm SceneVariables count.
- [ ] Confirm `enable_dof` is present.
- [ ] Regenerate HDA from repo source.
- [ ] Sync/install through a reproducible mechanism.
- [ ] Launch a fresh normal Houdini 20.5 GUI session after install sync.
- [ ] Confirm fresh GUI custom LOP defaults `aov_beauty` on and labels it `Beauty RenderVar / Disk Output Path`.
- [ ] Confirm fresh GUI custom LOP viewport/IPR and USD Render ROP render with the default Beauty RenderVar enabled.
- [ ] Export generic/native USD.
- [ ] Export custom USD.
- [ ] Diff RenderSettings/Product/Var.
- [ ] Export RDLA.
- [ ] Verify `enable_dof` in RDLA.
- [ ] Verify `image_width` and `image_height` are not authored as USD SceneVariables.
- [ ] Verify manual resolution.
- [ ] Verify computed resolution modes remain removed.
- [ ] Verify no computed resolution callback tags remain.
- [ ] Verify USD Render ROP `renderer`, `loppath`, `rendersettings`, and `outputimage` wiring.
- [ ] Verify RenderProduct `$F4` output path behavior.
- [ ] Treat black/zero-filled renders as output-wiring evidence only, not filled-pixel Beauty/AOV proof.

## Step 3 Render Contract Policy

The MoonRay Render Settings LOP is the DCC author of USD render intent, not the
execution engine. It should author a coherent default render contract:

- `/Render/rendersettings`
- `/Render/Products/renderproduct`
- `/Render/Products/Vars/*`

`RenderSettings` is the default authority for camera, products, resolution, pixel
aspect ratio, and MoonRay scene-variable attributes. `RenderProduct` is the
default authority for product name, product type, ordered vars, product
resolution, and product pixel aspect ratio. Product resolution and pixel aspect
must match RenderSettings unless an explicit future product-override UI is added.

`RenderProduct.camera` remains absent for the default beauty product. Local tests
proved that husk falls back to `RenderSettings.camera` when Product.camera is
absent, and that authored Product.camera is a real product-specific override.
The default MoonRay product should not claim that override until the UI exposes a
product-specific camera.

`dataWindowNDC` and `aspectRatioConformPolicy` are currently left to USD schema
fallback. Explicit full-frame `dataWindowNDC` and explicit expand/crop aperture
policies produced identical MoonRay/husk square-output stats in the marker probe,
so blindly authoring them would add opinions without proving a behavioral fix.

The Houdini USD Render ROP owns execution: selected LOP branch, selected
RenderSettings path, renderer, frame/range execution, and `outputimage` override.
The owned MoonRay ROP should point to the owning Render Settings LOP branch and
its `render_settings_prim`. `outputimage` should reference the owner's
`product_name` so Houdini expands `$HIP`, `$HIPNAME`, `$OS`, and `$F4` in the ROP
context. `RenderProduct.productName` remains the valid USD fallback.

Duplicate MoonRay Render Settings LOPs that author the same
`/Render/rendersettings` or `/Render/Products/renderproduct` paths are scene
poison. They can make a render use stale resolution/product/camera opinions even
when each individual node is valid. The DCC layer should warn when active sibling
MoonRay Render Settings LOPs target the same settings or product paths.

Houdini 20.5 HOM does not expose a mutable `hou.Node.addWarning()` API for this
HDA. The implemented warning path is therefore non-cook-time and non-destructive:
create/repair records the duplicate contract in node userData and appends a
visible warning to each owned USD Render ROP comment. This avoids raising
`hou.NodeWarning` during the cook, which would risk interrupting USD authoring.

### Step 3 Runtime Evidence

The table below records the original Step 3 audit observation. It is now
historical for the legacy command tools: the pushed H20.5 render-contract stack
filters raw `RenderProduct` and `RenderVar` traversal in `hd_render` and
`hd_usd2rdl` instead of adding fake Product/Var Bprim support. The current
contract remains:

- `RenderSettings` is the supported Hydra Bprim path.
- `RenderProduct` and `RenderVar` are not fake/no-op hdMoonray Bprims.
- legacy command-tool raw Product/Var traversal is filtered.

| Path | Evidence | Verdict |
|------|----------|---------|
| husk clean scene with `--settings /Render/rendersettings` | No unsupported RenderSettings/Product/Var warnings; EXR was 512x512 RGBA float and nonconstant. | Clean production path. |
| `hd_usd2rdl` clean scene | Historical: RDLA written, but legacy traversal logged unsupported RenderProduct before the command-tool filtering patch. | Superseded by pushed command-tool traversal filtering. |
| `hd_render` clean scene | Historical: EXR written, but legacy traversal logged unsupported RenderProduct before the command-tool filtering patch. | Superseded by pushed command-tool traversal filtering. |
| real-scene husk probe | No RenderSettings/Product warning before the manual timeout; render reached mcrt render prep. | Render contract warnings not observed in husk path. |
| real-scene `hd_usd2rdl` | Historical: RDLA written, unsupported RenderProduct warning plus unrelated light compatibility warnings before the command-tool filtering patch. | Product/Var traversal warning superseded; light warnings remain separate. |

### Rejected Step 3 Fixes

- Do not add fake/no-op RenderProduct or RenderVar Bprim support.
- Do not set `aovsupport=false` to hide UI paths.
- Do not author default Product.camera as a speculative framing fix.
- Do not hardcode camera, resolution, or project-specific paths.
- Do not collapse `RenderProduct.productName` and ROP `outputimage`; they are
  related but have different authority.

## 2026-06-20 Shipping Pass DCC Update

This section records the DCC-facing state after the final Step 3 shipping pass.
The runtime/command-tool details are recorded in the hdMoonray render-contract
docs; this section focuses on what the MoonRay Render Settings LOP and owned USD
Render ROP author or preserve.

### Authored USD Contract

The MoonRay Render Settings LOP authors a coherent default USD render contract:

- `UsdRenderSettings` at the configured `render_settings_prim`.
- one default `UsdRenderProduct` under the configured products parent/name.
- RenderVars for Beauty, native AOVs, and the currently supported
  material/denoise AOVs.
- `moonray:sceneVariable:*` attributes on RenderSettings.

Current parameter authority:

| USD value | DCC authority |
|-----------|---------------|
| `RenderSettings.camera` | camera path control / Solaris camera relationship |
| `RenderSettings.products` | generated default product relationship |
| `RenderSettings.resolution` | `resolutionx`, `resolutiony` |
| `RenderSettings.pixelAspectRatio` | DCC pixel-aspect value |
| `RenderProduct.productName` | `product_name` |
| `RenderProduct.productType` | default raster product |
| `RenderProduct.orderedVars` | enabled Beauty/AOV RenderVars |
| `RenderProduct.resolution` | same `resolutionx`, `resolutiony` tuple as RenderSettings |
| `RenderProduct.pixelAspectRatio` | same pixel-aspect value as RenderSettings |
| `RenderProduct.camera` | intentionally absent by default |
| `dataWindowNDC` | USD schema fallback |
| `aspectRatioConformPolicy` | USD schema fallback |

The default Product.camera remains absent because local tests proved that husk
falls back to RenderSettings.camera, and an authored Product.camera is a real
product-specific override. A future product-camera UI should be explicit rather
than silently authored for the default beauty product.

### Owned USD Render ROP Contract

The owned MoonRay USD Render ROP remains the Houdini execution authority:

- `loppath = opinput(".", 0)` so the ROP renders the owner branch.
- `rendersettings = chs("<owner>/render_settings_prim")`.
- `outputimage = chs("<owner>/product_name")` through the raw/backtick-safe
  expression model validated earlier.
- renderer is `HdMoonrayRendererPlugin`.

`RenderProduct.productName` remains the USD fallback product path, while ROP
`outputimage` is the Houdini execution override that expands `$HIP`, `$HIPNAME`,
`$OS`, and `$F4` in the correct node context.

### AOV And Beauty Invariants

- Beauty remains RGBA/color4f for the explicit disk-output RenderVar.
- `aovsupport` remains enabled in source and installed `UsdRenderers.json`.
- `cameraDepth` remains absent from the product-facing DCC AOV contract.
- Native AOVs remain: `alpha`, `depth`, `Z`, `N`, `Ng`, `P`, `Wp`, `St`,
  `weight`.
- Material/denoise AOVs remain opt-in and default off.
- Cryptomatte, LPEs, visibility AOVs, primvars, and motion vectors remain
  deferred.

### Provenance And Validation

Installed/source DCC SHA-256 checks matched:

| File | SHA-256 |
|------|---------|
| `moonray_render_settings.py` | `79e6564036fe759adcf34e830570d66aa6120834b2c1c25c3f79fa7d1b154a92` |
| `Lop::DW_MOONRAY::moonrayrendersettings::1.hda` | `42e5403d53040afdafe8dd2af5fcd0c35f55e4d667c51caa778cbbaa5180311b` |
| `UsdRenderers.json` | `fce8438e8c006cf3e80ca655e8ea299dc634651b1c37629c7eb4cf8aaa06e312` |

Installed H20.5 DCC validation passed:

```text
SUMMARY PASS=121 FAIL=0 SKIP=6
```

`husk --list-renderers` listed both the normal and debug MoonRay delegates.
`git diff --check` passed in parent, DCC, hdMoonray, and SDR after the shipping
pass.

### Remaining DCC Boundaries

- Fresh graphical Houdini/Solaris IPR validation is still needed for final
  viewport visual matching.
- The DCC layer does not own H20.5 husk's extra memory metadata emission.
- The DCC layer does not own GUI-only Qt/OpenGL warning noise unless a later
  fresh Houdini session proves a MoonRay-specific trigger.

## 2026-06 Config-Driven OCIO Controls

The MoonRay Render Settings LOP now exposes a minimal Color Management folder.
The folder does not bake display/view transforms and does not change AOV,
RenderProduct, scene-scale, or displacement behavior.

The OCIO implementation is config-driven. ARRI configs were validation inputs,
not hidden renderer policy. Render-space resolution is owned by hdMoonray and
uses the active OCIO config roles/aliases; texture `auto` uses OCIO file rules
only.

Current DCC color controls:

| Control | Authored USD / behavior | Notes |
| --- | --- | --- |
| `renderingColorSpace` | Authors `UsdRender.Settings.renderingColorSpace` only when non-empty and not `auto`. | Blank/`auto` clears stale authored values and lets hdMoonray resolve the active OCIO config roles. ARRI CG validation resolved to `Linear ARRI Wide Gamut 4`; other configs resolve through their own roles/aliases. |
| OCIO policy note | UI help only. | The render process uses `$OCIO`; standalone tools should be launched through the Houdini package environment or `setupHoudini.sh`. |
| Texture source policy note | UI help only. | Native `ImageMap.source_color_space` and `UsdUVTexture.sourceColorSpace` / `source_color_space` own texture source interpretation. |
| Display transform note | UI help only. | EXR output remains scene-linear/render-space; no display/view transform is baked by this pass. |

The native Houdini `moonray_ImageMap.ds` and `moonray_nodes.json` now expose
`source_color_space` with config-driven menu entries. Common validation examples
seen in tested H20.5 configs included:

- `auto`;
- `raw`;
- `data`;
- `Linear ARRI Wide Gamut 4`;
- `ARRI LogC4`;
- `ACEScg`;
- `Linear Rec.709 (sRGB)`;
- `Gamma 2.4 Rec.709 - Texture`.

There is no separate source `moonray_UsdUVTexture.ds` in this plugin tree. The
native `UsdUVTexture` scene-class metadata does expose `sourceColorSpace` and
the optional `source_color_space` override for translated USD and direct RDL
use.
