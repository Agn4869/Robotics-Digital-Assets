"""Step real UVDMS dynamics with servo animation or manual viewer controls.

Fixed: gravity acts on a bolted-down base. Floating: free base, zero gravity,
no fluid forces. Neither mode uses gravity compensation or pose teleportation.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import time

import mujoco
import numpy as np


def animation(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    """Small, smoothly introduced targets; independent joints only have servos."""
    ramp = 0.5 - 0.5 * math.cos(math.pi * min(data.time / 2.0, 1.0))
    for index in range(model.nu):
        joint_id = model.actuator_trnid[index, 0]
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
        side = -1.0 if name.endswith("B") or name.startswith("B_") else 1.0
        if "_gripper_" in name:
            target = 0.22 * ramp * math.sin(0.8 * data.time)
        else:
            joint_number = int(name.split("_")[1][0])
            amplitude = (0.12, 0.16, 0.20, 0.16)[joint_number - 1]
            target = side * amplitude * ramp * math.sin(0.55 * data.time + 0.4 * (joint_number - 1))
        data.ctrl[index] = np.clip(target, *model.actuator_ctrlrange[index])


def joint_errors(model: mujoco.MjModel, data: mujoco.MjData) -> np.ndarray:
    addresses = model.jnt_qposadr[model.actuator_trnid[:, 0]]
    return data.qpos[addresses] - data.ctrl


def mimic_errors(model: mujoco.MjModel, data: mujoco.MjData) -> dict[str, float]:
    errors = {}
    for index in range(model.neq):
        if model.eq_type[index] != mujoco.mjtEq.mjEQ_JOINT:
            continue
        first, second = model.eq_obj1id[index], model.eq_obj2id[index]
        first_address = model.jnt_qposadr[first]
        actual = data.qpos[first_address] - model.qpos0[first_address]
        if second >= 0:
            second_address = model.jnt_qposadr[second]
            master = data.qpos[second_address] - model.qpos0[second_address]
        else:
            master = 0.0
        expected = np.polynomial.polynomial.polyval(master, model.eq_data[index, :5])
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_EQUALITY, index)
        errors[name] = float(actual - expected)
    return errors


def preview(path: Path, seconds: float | None, headless: bool, manual: bool) -> None:
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    data.ctrl[:] = np.clip(0.0, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
    mujoco.mj_forward(model, data)
    print(f"Loaded {path.name}: {model.nbody - 1} link bodies, {model.njnt} joints, "
          f"{model.nu} independent controls, {model.neq} equalities; dt={model.opt.timestep:g} s")
    print(f"Gravity: {model.opt.gravity}; real dynamics, no fluid forces or gravity compensation.")
    print("Mode: held/manual servo targets." if manual else "Mode: modest animated dual-arm and gripper servo targets.")
    peak_joint_error = 0.0
    peak_mimic_error = 0.0
    steps = 0

    def step() -> None:
        nonlocal steps, peak_joint_error, peak_mimic_error
        if not manual:
            animation(model, data)
        mujoco.mj_step(model, data)
        steps += 1
        peak_joint_error = max(peak_joint_error, float(np.max(np.abs(joint_errors(model, data)), initial=0.0)))
        peak_mimic_error = max(peak_mimic_error, max((abs(value) for value in mimic_errors(model, data).values()), default=0.0))
        if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
            raise RuntimeError(f"Non-finite simulation state at step {steps}")
        for warning in (mujoco.mjtWarning.mjWARN_BADQPOS, mujoco.mjtWarning.mjWARN_BADQVEL,
                        mujoco.mjtWarning.mjWARN_BADQACC, mujoco.mjtWarning.mjWARN_BADCTRL):
            if data.warning[warning].number:
                raise RuntimeError(f"MuJoCo reported {warning.name} at step {steps}")

    if headless:
        duration = seconds if seconds is not None else 10.0
        while steps * model.opt.timestep < duration:
            step()
    else:
        from mujoco import viewer as viewer_api

        print("Close the viewer to exit; --manual (or --static) leaves Control sliders in charge.", flush=True)
        with viewer_api.launch_passive(model, data, show_left_ui=False, show_right_ui=True) as viewer:
            viewer.cam.lookat[:] = model.stat.center
            viewer.cam.distance = 2.6
            viewer.cam.azimuth = 135
            viewer.cam.elevation = -20
            viewer.opt.geomgroup[2] = 1  # Detailed CAD visuals.
            viewer.opt.geomgroup[3] = 0  # Collision proxies are not showcase geometry.
            viewer.opt.geomgroup[4] = 0  # TCP markers can be enabled in the UI.
            viewer.sync()
            batch = max(1, round(1.0 / (60 * model.opt.timestep)))
            while viewer.is_running() and (seconds is None or steps * model.opt.timestep < seconds):
                frame_start = time.perf_counter()
                with viewer.lock():
                    for _ in range(batch):
                        if seconds is not None and steps * model.opt.timestep >= seconds:
                            break
                        step()
                viewer.sync()
                time.sleep(max(0.0, batch * model.opt.timestep - (time.perf_counter() - frame_start)))
    print(f"Stepped {steps} times; simulated {data.time:.6f} s.")
    print(f"Peak absolute servo tracking error: {peak_joint_error:.6g} rad (finite gains/force limits; not a kinematic pose setter).")
    print(f"Peak absolute mimic constraint error: {peak_mimic_error:.6g} rad (soft equality constraints).")
    for index, error in enumerate(joint_errors(model, data)):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, index)
        print(f"  joint {name}: target={data.ctrl[index]:+.6f}, error={error:+.6g} rad")
    for name, error in mimic_errors(model, data).items():
        print(f"  mimic {name}: error={error:+.6g} rad")
    warning_count = sum(warning.number for warning in data.warning)
    print(f"MuJoCo warnings: {warning_count}; active contacts at final step: {data.ncon}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("fixed", "floating"), default="fixed")
    parser.add_argument("--seconds", type=float, help="Simulated duration; headless default 10, viewer default until closed")
    parser.add_argument("--headless", action="store_true", help="Step dynamics without opening a viewer; print tracking/mimic errors")
    parser.add_argument("--manual", "--static", dest="manual", action="store_true",
                        help="Do not animate targets; use viewer Control sliders (headless holds zero targets)")
    args = parser.parse_args()
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds <= 0):
        parser.error("--seconds must be finite and positive")
    root = Path(__file__).resolve().parents[1] / "assets" / "uvdms" / "mujoco"
    path = root / ("scene.xml" if args.model == "fixed" else "floating.xml")
    preview(path, args.seconds, args.headless, args.manual)


if __name__ == "__main__":
    main()
