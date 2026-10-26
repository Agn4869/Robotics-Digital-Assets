#!/usr/bin/env python3
"""Render the shipped UVDMS model and a real MuJoCo stepped motion preview.

Copyright (c) 2026 Agn4869. Code: MIT (LICENSE-CODE).
Generated asset images: CC BY-NC 4.0 (LICENSE / NOTICE.md).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def label(frame: np.ndarray, title: str, subtitle: str) -> Image.Image:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 24)
        small = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            small = ImageFont.truetype("arial.ttf", 15)
        except OSError:
            font = small = ImageFont.load_default()
    draw.rectangle((0, 0, image.width, 80), fill=(18, 30, 45))
    draw.text((22, 14), title, font=font, fill=(236, 244, 250))
    draw.text((22, 48), subtitle, font=small, fill=(169, 198, 218))
    draw.rectangle((0, image.height - 30, image.width, image.height), fill=(18, 30, 45))
    draw.text((20, image.height - 24), "Agn4869  |  Robotics-Digital-Assets  |  CC BY-NC 4.0", font=small, fill=(190, 211, 224))
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "images")
    parser.add_argument("--frames", type=int, default=90)
    args = parser.parse_args()
    if args.frames < 2:
        parser.error("--frames must be at least 2")
    args.output.mkdir(parents=True, exist_ok=True)
    model = mujoco.MjModel.from_xml_path(str(ROOT / "assets/uvdms/mujoco/scene.xml"))
    data = mujoco.MjData(model)
    # Gallery colors are presentation choices, not measured paint/material properties.
    for i in range(model.ngeom):
        if model.geom_group[i] != 2:
            continue
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(model.geom_bodyid[i])) or ""
        if "gripper" in name:
            model.geom_rgba[i] = [0.25, 0.31, 0.38, 1]
        elif name.startswith("link_"):
            model.geom_rgba[i] = [0.18, 0.50, 0.64, 1]
        else:
            model.geom_rgba[i] = [0.77, 0.84, 0.89, 1]
    mujoco.mj_forward(model, data)
    base_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base_link")
    base = data.xpos[base_id].copy()
    camera = mujoco.MjvCamera()
    camera.lookat[:] = base + [-0.12, 0, 0.08]
    camera.distance, camera.azimuth, camera.elevation = 2.65, 135, -18
    option = mujoco.MjvOption()
    option.geomgroup[0] = 1
    option.geomgroup[3] = 0
    option.geomgroup[4] = 0
    option.geomgroup[2] = 1
    model.vis.global_.offwidth = max(model.vis.global_.offwidth, 1200)
    model.vis.global_.offheight = max(model.vis.global_.offheight, 800)
    with mujoco.Renderer(model, height=800, width=1200) as renderer:
        renderer.update_scene(data, camera, scene_option=option)
        label(renderer.render(), "UVDMS | Dual-arm underwater robot", "Portable URDF + native MuJoCo  /  CAD-derived model, not a hardware photograph").save(args.output / "uvdms_overview.png")
        camera.azimuth = 45
        camera.elevation = -5
        camera.distance = 1.55
        camera.lookat[:] = base + [0.18, 0, -0.24]
        renderer.update_scene(data, camera, scene_option=option)
        label(renderer.render(), "UVDMS | Manipulators and grippers", "4 arm joints + 1 coupled gripper per side  /  colors are for presentation").save(args.output / "uvdms_arms.png")
        camera.azimuth = 90
        camera.elevation = -15
        camera.distance = 2.65
        camera.lookat[:] = base + [-0.12, 0, 0.08]
        option.geomgroup[3] = 1
        collision_ids = np.flatnonzero(model.geom_group == 3)
        model.geom_rgba[collision_ids, 3] = 0.7
        option.geomgroup[2] = 0
        renderer.update_scene(data, camera, scene_option=option)
        label(renderer.render(), "UVDMS | Collision representation", "Simplified collision geometry  /  not a calibrated underwater contact model").save(args.output / "uvdms_collision.png")
    camera.azimuth = 45
    camera.elevation = -15
    option.geomgroup[3] = 0
    option.geomgroup[2] = 1
    frames = []
    samples_per_frame = max(1, round(1 / 15 / model.opt.timestep))
    with mujoco.Renderer(model, height=480, width=720) as renderer:
        for frame_index in range(args.frames):
            for _ in range(samples_per_frame):
                phase = 2 * np.pi * data.time / 6
                for actuator in range(model.nu):
                    joint = int(model.actuator_trnid[actuator, 0])
                    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
                    if "gripper" in name:
                        target = 0.25 * np.sin(phase)
                    else:
                        target = 0.18 * np.sin(phase + (0.4 if name.endswith("B") else 0))
                    data.ctrl[actuator] = np.clip(target, *model.actuator_ctrlrange[actuator])
                mujoco.mj_step(model, data)
            if not np.isfinite(data.qpos).all():
                raise RuntimeError("Non-finite motion during gallery render")
            renderer.update_scene(data, camera, scene_option=option)
            frames.append(label(renderer.render(), "UVDMS | MuJoCo motion preview", "Fixed-base simulation  /  actual dynamics steps  /  no fluid model"))
    frames[0].save(args.output / "uvdms_motion.gif", save_all=True, append_images=frames[1:], duration=67, loop=0, optimize=True)
    print(f"Saved 3 PNG views and {len(frames)} stepped GIF frames to {args.output}")


if __name__ == "__main__":
    main()
