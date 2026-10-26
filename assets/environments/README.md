# Environment interaction assets

This directory contains reusable articulated environment objects for robot manipulation: push buttons, levers, sliders, panels and a wheel valve.

**No SolidWorks files are included.** No `.SLDASM`, `.SLDPRT`, CAD assembly, or private source project is redistributed here.

## Included assets

| Directory | Contents | Format | License / source |
|---|---|---|---|
| `ambench/` | `push_button.usd`, `lever.usd`, `slider_with_rail.usd`, `valve.usd` | USD | AM-Bench contributors, Apache-2.0 |
| `marine_mechanisms_v1/` | marine-looking `lever.usda`, `slider_with_rail.usda`, `grounded_panel.usda` | USDA | Appearance derivatives; original mechanisms retain AM-Bench notice |
| `industrial_handwheel/` | wheel valve, 2.5× scaled USDA, textures and provenance | USD/USDZ/USDA | WasserMan-derived Apache-2.0 module; underlying Poly Haven assets CC0-1.0 |
| `panels/ship_green/` | textured panel slab and PBR maps | USDA/JPG | Poly Haven `green_metal_rust`, CC0-1.0 |

The USD files are kept in the relative layout expected by their references. Use a USD-capable viewer such as Isaac Sim, Omniverse/USD tooling, or `usdview` where available. These are environment assets, not a complete task scene and not a calibrated model of a commercial mechanism.

## Provenance and attribution

The source organization is [WasserMan](https://github.com/dancher00/wasserman), Apache License 2.0. It in turn identifies [AM-Bench](https://github.com/ambench/ambench) as the source for the mechanism assets and [Poly Haven Modular Industrial Pipes 01](https://polyhaven.com/a/modular_industrial_pipes_01) / `green_metal_rust` for CC0 visual materials.

The original notices and licenses are kept next to each asset. See [`manifest.json`](manifest.json) for source paths, upstream commit references, hashes and whether an asset is an unmodified copy or an appearance derivative.

Suggested attribution when sharing this environment bundle:

> Environment interaction assets from Robotics-Digital-Assets by Agn4869, https://github.com/Agn4869/Robotics-Digital-Assets. AM-Bench-derived objects retain their Apache-2.0 notices; WasserMan-derived adaptations retain WasserMan/AM-Bench attribution; Poly Haven materials are CC0-1.0. Changes: state your changes here.

This repository's **Agn4869 attribution is required for the bundle and its original curation/documentation** under the repository policy. It does not replace upstream attribution or change the license of upstream files. Commercial use of the UVDMS assets and this bundle's original curation is not granted by the root CC BY-NC license; upstream Apache-2.0 and CC0 files retain their own terms.

## Physics boundary

The authored mass, friction, damping and travel values are simulation assumptions from the upstream asset packages. They are not measurements of real buttons, valves or underwater mechanisms. Do not use them as hardware ratings, contact-force limits or safety specifications without calibration.

This release intentionally excludes the local Isaac Sim task scenes because those scenes also reference the private robot workspace and are not portable on their own. The object files can be composed into new scenes using the relative references documented above.
