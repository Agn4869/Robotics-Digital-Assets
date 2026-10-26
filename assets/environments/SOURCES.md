# Environment assets — source and file manifest

All paths in `files` are relative to `assets/environments/`. SHA-256 hashes identify the packaged files. Source identities and licenses come from the retained upstream notices and metadata in this repository.

## AM-Bench objects redistributed by WasserMan

Upstream: `https://github.com/ambench/ambench/tree/60bf5b73041df4eab571f7d9f0a297aeecbf2e0d/source/ambench/ambench/assets/objects`  
License: Apache-2.0. Retained unchanged files: `ambench/push_button.usd`, `lever.usd`, `slider_with_rail.usd`, `valve.usd`. Copyright 2026 The AM-Bench Contributors. Exact notice and license: `ambench/NOTICE-upstream.md`, `ambench/LICENSE.txt`.

The `marine_mechanisms_v1` lever/slider files are WasserMan appearance derivatives; original mechanism geometry and physical USD definitions are preserved according to the local upstream manifest. WasserMan changes appearance/materials and authored the grounded-panel extension. See `marine_mechanisms_v1/NOTICE.md`, `manifest.json`, and `LICENSE.txt`. This is not manufacturer CAD.

## Industrial handwheel

Derived module source: WasserMan `src/wasman/assets/data/objects/industrial_valve/`, commit `42875221404900ab4789db39ebc0c537119b79be`; Apache-2.0 notice retained at `industrial_handwheel/NOTICE.md`. Underlying industrial-pipe model and included 2K texture maps: Jorge Camacho, Poly Haven, CC0-1.0, `https://polyhaven.com/a/modular_industrial_pipes_01`. Hashes and dimensions are recorded in `industrial_handwheel/provenance.json`. The valve USD adds WasserMan mechanism/collision structure and assumptions; CC0 on the underlying source does not make the WasserMan-derived module identical to a CC0 source asset.

## Textured panel

`panels/ship_green/panel.usda` and its PBR textures are based on Poly Haven `green_metal_rust`, CC0-1.0. Attribution/source URLs and texture hashes: `panels/ship_green/provenance.json`.

## Scope and dependencies

The original local scene files reference a private UVDMS path and are intentionally not copied. These standalone environment objects can be composed into new scenes; they are not a complete robot-plus-panel task. Some WasserMan appearance materials reference Omniverse MDL material libraries by URL/name; those materials require an Omniverse/Isaac-compatible runtime and may not resolve in generic USD viewers. Geometry and joint definitions remain in the asset files.

No SolidWorks files were used or uploaded. The local assets already existed as third-party exports in UVMS-DriftManip; this packaging adds directory organization and provenance, not new physics validation.

## Packaged file hashes

See `SHA256SUMS.txt` for SHA-256 hashes of every included object, texture, license, notice and provenance file (excluding the manifest and this guide to avoid a self-referential hash). Recompute after intentional edits.
