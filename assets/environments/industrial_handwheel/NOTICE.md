# industrial_handwheel — third-party asset

- Source of the USD (wheel valve with capsule collision proxy, revolute joint):
  https://github.com/dancher00/wasserman , path `src/wasman/assets/data/objects/industrial_valve/`, commit `42875221404900ab4789db39ebc0c537119b79be`
  (Apache License 2.0, copy in `LICENSE-wasserman-apache-2.0.txt`). Files are unmodified copies.
- Underlying 3D model and textures: "modular_industrial_pipes_01" by Jorge Camacho, Poly Haven, CC0-1.0
  (https://polyhaven.com/a/modular_industrial_pipes_01); see `provenance.json`.
- Physics values (mass 3 kg body / 0.18 kg wheel, friction 0.8/0.6, joint damping 0.08) are the upstream authors'
  assumptions, not calibrated hardware. `valve_bimanual_4x.json` documents their 4x scaled variant (not vendored).
