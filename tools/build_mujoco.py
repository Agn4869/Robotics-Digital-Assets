"""Generate native MJCF from the packaged UVDMS URDF; never modifies the URDF/STLs.

The small armatures, damping, servo gains, contact proxies and equality softness
are numerical/demo assumptions, not identified hardware parameters. Original
link masses and full inertia tensors are retained, including the wrist plates.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def numbers(values) -> str:
    return " ".join(format(float(value), ".16g") for value in values)


def vector(text: str) -> np.ndarray:
    return np.asarray([float(value) for value in text.split()], dtype=float)


def orientation(rpy: str) -> tuple[np.ndarray, np.ndarray]:
    """URDF extrinsic xyz angles to a wxyz quaternion and rotation matrix."""
    roll, pitch, yaw = vector(rpy) / 2
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    w, x, y, z = cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy
    quat = np.asarray([w, x, y, z])
    rotation = np.asarray([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    return quat, rotation


def pose(element: ET.Element) -> dict[str, str]:
    origin = element.find("origin")
    if origin is None:
        return {}
    quat, _ = orientation(origin.get("rpy", "0 0 0"))
    return {"pos": origin.get("xyz", "0 0 0"), "quat": numbers(quat)}


def add_inertial(body: ET.Element, link: ET.Element) -> None:
    inertial = link.find("inertial")
    if inertial is None:
        return  # The two fixed TCP bodies intentionally have no mass.
    mass = inertial.find("mass")
    inertia = inertial.find("inertia")
    if mass is None or inertia is None:
        raise ValueError(f"Incomplete inertial: {link.attrib['name']}")
    origin = inertial.find("origin")
    xyz = origin.get("xyz", "0 0 0") if origin is not None else "0 0 0"
    rpy = origin.get("rpy", "0 0 0") if origin is not None else "0 0 0"
    _, rotation = orientation(rpy)
    xx, yy, zz, xy, xz, yz = (float(inertia.attrib[key]) for key in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz"))
    tensor = rotation @ np.asarray([[xx, xy, xz], [xy, yy, yz], [xz, yz, zz]]) @ rotation.T
    # fullinertia is expressed in the body axes; its COM position is unchanged.
    ET.SubElement(body, "inertial", mass=mass.attrib["value"], pos=xyz,
                  fullinertia=numbers([tensor[0, 0], tensor[1, 1], tensor[2, 2], tensor[0, 1], tensor[0, 2], tensor[1, 2]]))


def add_environment(world: ET.Element) -> None:
    ET.SubElement(world, "geom", name="floor", type="plane", size="5 5 0.1", group="0",
                  rgba="0.12 0.17 0.21 1", friction="0.8 0.02 0.002", condim="3")
    ET.SubElement(world, "light", name="key", pos="1 -2 4", dir="-0.3 0.5 -1", diffuse="0.8 0.8 0.8", castshadow="true")
    ET.SubElement(world, "light", name="fill", pos="-2 2 3", dir="0.5 -0.4 -1", diffuse="0.45 0.5 0.6", castshadow="false")
    # Cameras point toward the robot using explicit world-frame camera axes.
    for name, eye in (("overview", (2.0, -2.6, 2.0)), ("front", (2.5, 0, 1.35)), ("rear", (-2.5, 1.8, 1.9))):
        position = np.asarray(eye)
        z_axis = position - np.asarray([-0.15, 0, 1.15])
        z_axis /= np.linalg.norm(z_axis)
        x_axis = np.cross([0, 0, 1], z_axis)
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis)
        ET.SubElement(world, "camera", name=name, pos=numbers(position), xyaxes=numbers(np.concatenate([x_axis, y_axis])), fovy="42")


def write_xml(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def build(urdf: Path, output: Path) -> tuple[Path, Path, Path]:
    robot = ET.parse(urdf).getroot()
    links = {link.attrib["name"]: link for link in robot.findall("link")}
    joints = robot.findall("joint")
    children: dict[str, list[ET.Element]] = {name: [] for name in links}
    incoming: dict[str, ET.Element] = {}
    for joint in joints:
        parent = joint.find("parent").attrib["link"]
        child = joint.find("child").attrib["link"]
        if joint.attrib["type"] not in ("fixed", "revolute"):
            raise ValueError(f"Unsupported UVDMS joint: {joint.attrib['name']}")
        if child in incoming:
            raise ValueError(f"Multiple parent joints for {child}")
        children[parent].append(joint)
        incoming[child] = joint
    roots = set(links) - set(incoming)
    if len(roots) != 1:
        raise ValueError(f"Expected one URDF root, got {roots}")
    root_link = roots.pop()
    root = ET.Element("mujoco", model="uvdms_fixed")
    root.append(ET.Comment(" Generated from the portable URDF. Gains/collisions are demo assumptions; no hydrodynamics. "))
    ET.SubElement(root, "compiler", angle="radian", meshdir="../meshes", autolimits="true",
                  inertiafromgeom="false", fusestatic="false", balanceinertia="false", boundmass="0", boundinertia="0")
    ET.SubElement(root, "option", timestep="0.0005", integrator="implicitfast", solver="Newton",
                  iterations="100", tolerance="1e-10", gravity="0 0 -9.81")
    ET.SubElement(root, "statistic", center="-0.15 0 1.15", extent="1.8")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1600", offheight="1200")
    ET.SubElement(visual, "headlight", ambient="0.3 0.3 0.3", diffuse="0.6 0.6 0.6", specular="0.15 0.15 0.15")
    defaults = ET.SubElement(root, "default")
    visual_default = ET.SubElement(defaults, "default", {"class": "visual"})
    ET.SubElement(visual_default, "geom", contype="0", conaffinity="0", group="2", density="0")
    collision_default = ET.SubElement(defaults, "default", {"class": "collision"})
    ET.SubElement(collision_default, "geom", contype="1", conaffinity="1", group="3", density="0", rgba="0.8 0.25 0.1 0",
                  friction="0.7 0.01 0.001", condim="3", solref="0.005 1", solimp="0.9 0.95 0.001")
    assets = ET.SubElement(root, "asset")
    mesh_assets: dict[tuple[Path, str], str] = {}

    def mesh_attributes(mesh: ET.Element) -> dict[str, str]:
        uri = mesh.attrib["filename"]
        if "://" in uri or Path(uri).is_absolute():
            raise ValueError(f"Package the URDF first; mesh URI must be relative: {uri}")
        path = (urdf.parent / uri).resolve()
        meshdir = (output / "../meshes").resolve()
        if path.parent != meshdir or not path.is_file():
            raise ValueError(f"Mesh must exist in {meshdir}: {path}")
        scale = mesh.get("scale", "1 1 1")
        key = (path, scale)
        if key not in mesh_assets:
            name = f"mesh_{len(mesh_assets):02d}_{path.stem}"
            mesh_assets[key] = name
            ET.SubElement(assets, "mesh", name=name, file=path.name, scale=scale)
        return {"type": "mesh", "mesh": mesh_assets[key]}

    def add_geometry(body: ET.Element, link: ET.Element) -> None:
        name = link.attrib["name"]
        for index, element in enumerate(link.findall("visual")):
            mesh = element.find("geometry/mesh")
            if mesh is None:
                raise ValueError(f"Expected mesh visual on {name}")
            attributes = {"name": f"{name}_visual_{index}", "class": "visual", **pose(element), **mesh_attributes(mesh)}
            color = element.find("material/color")
            if color is not None:
                attributes["rgba"] = color.attrib["rgba"]
            ET.SubElement(body, "geom", attributes)
        if name == root_link:
            # The detailed hull's convex envelope closes the open arm workspace.
            # Instead use ONLY an upper-hull box (z=0.13..0.58 in base axes).
            # This deliberately omits the lower open frame, not a watertight hull.
            ET.SubElement(body, "geom", {"name": "base_link_collision_upper_hull", "class": "collision", "type": "box",
                                        "pos": "-0.2585 0 0.355", "size": "0.5885 0.3225 0.225"})
            return
        for index, element in enumerate(link.findall("collision")):
            mesh = element.find("geometry/mesh")
            if mesh is None:
                raise ValueError(f"Expected mesh collision on {name}")
            # MuJoCo mesh contacts use per-link convex hulls; all fingers retain
            # external contacts. These are not concave CAD contact surfaces.
            ET.SubElement(body, "geom", {"name": f"{name}_collision_{index}", "class": "collision",
                                         **pose(element), **mesh_attributes(mesh)})

    world = ET.SubElement(root, "worldbody")
    visited: set[str] = set()

    def add_body(name: str, parent_body: ET.Element) -> None:
        if name in visited:
            raise ValueError(f"Cyclic URDF at {name}")
        visited.add(name)
        joint = incoming.get(name)
        attributes = {"name": name}
        attributes.update(pose(joint) if joint is not None else {"pos": "0 0 1.2"})
        body = ET.SubElement(parent_body, "body", attributes)
        add_inertial(body, links[name])
        if joint is not None and joint.attrib["type"] != "fixed":
            limit = joint.find("limit")
            axis = joint.find("axis")
            is_gripper = "_gripper_" in joint.attrib["name"]
            ET.SubElement(body, "joint", name=joint.attrib["name"], type="hinge", axis=axis.get("xyz", "1 0 0") if axis is not None else "1 0 0",
                          limited="true", range=f"{limit.attrib['lower']} {limit.attrib['upper']}",
                          damping="0.02" if is_gripper else "0.3", armature="0.0002" if is_gripper else "0.01")
        add_geometry(body, links[name])
        if name in ("A_gripper_tcp", "B_gripper_tcp"):
            ET.SubElement(body, "site", name=name, type="sphere", size="0.006", group="4", rgba="0.1 0.8 0.9 1")
        for child_joint in children[name]:
            add_body(child_joint.find("child").attrib["link"], body)

    add_body(root_link, world)
    if visited != set(links):
        raise ValueError(f"Disconnected URDF links: {set(links) - visited}")
    contact = ET.SubElement(root, "contact")
    # Fixed mounts belong to the same collision adjacency group as their parent.
    welded = {name: name for name in links}

    def group(name: str) -> str:
        while welded[name] != name:
            name = welded[name]
        return name

    for joint in joints:
        if joint.attrib["type"] == "fixed":
            welded[group(joint.find("child").attrib["link"])] = group(joint.find("parent").attrib["link"])
    neighbors = {frozenset((group(joint.find("parent").attrib["link"]), group(joint.find("child").attrib["link"]))) for joint in joints}
    for first, second in itertools.combinations(links, 2):
        same_claw = any(first.startswith(f"{side}_gripper_") and second.startswith(f"{side}_gripper_") for side in ("A", "B"))
        if same_claw or group(first) == group(second) or frozenset((group(first), group(second))) in neighbors:
            ET.SubElement(contact, "exclude", body1=first, body2=second)
    equality = ET.SubElement(root, "equality")
    actuator = ET.SubElement(root, "actuator")
    for joint in joints:
        if joint.attrib["type"] == "fixed":
            continue
        name = joint.attrib["name"]
        mimic = joint.find("mimic")
        if mimic is not None:
            # Affine URDF mimic only: not a physical four-bar closure constraint.
            ET.SubElement(equality, "joint", name=f"{name}_mimic", joint1=name, joint2=mimic.attrib["joint"],
                          polycoef=f"{mimic.get('offset', '0')} {mimic.get('multiplier', '1')} 0 0 0",
                          solref="0.003 1", solimp="0.95 0.99 0.001")
            continue
        limit = joint.find("limit")
        effort = float(limit.attrib["effort"])
        if effort <= 0:
            raise ValueError(f"Expected positive source effort on {name}")
        is_gripper = "_gripper_" in name
        # URDF effort is used as the servo force bound, not hardware certification.
        ET.SubElement(actuator, "position", name=name, joint=name,
                      kp="4" if is_gripper else "80", kv="0.08" if is_gripper else "8",
                      ctrllimited="true", ctrlrange=f"{limit.attrib['lower']} {limit.attrib['upper']}",
                      forcelimited="true", forcerange=numbers([-effort, effort]))
    output.mkdir(parents=True, exist_ok=True)
    model_path, scene_path, floating_path = (output / name for name in ("model.xml", "scene.xml", "floating.xml"))
    write_xml(root, model_path)
    scene = ET.Element("mujoco", model="uvdms_fixed_scene")
    ET.SubElement(scene, "include", file="model.xml")
    add_environment(ET.SubElement(scene, "worldbody"))
    write_xml(scene, scene_path)
    floating = copy.deepcopy(root)
    floating.set("model", "uvdms_floating_zero_gravity")
    floating.find("option").set("gravity", "0 0 0")
    floating.append(ET.Comment(" Free rigid body in zero gravity: no buoyancy, drag, added mass, thrust or fluid forces. "))
    floating_body = floating.find("worldbody/body")
    floating_body.insert(0, ET.Element("freejoint", name="floating_base"))
    add_environment(floating.find("worldbody"))
    write_xml(floating, floating_path)
    print(f"Generated {len(links)} link bodies, {sum(j.attrib['type'] != 'fixed' for j in joints)} hinges, "
          f"{len(actuator)} independent servos and {len(equality)} mimic constraints.")
    for path in (model_path, scene_path, floating_path):
        print(path)
    return model_path, scene_path, floating_path


def main() -> None:
    package = Path(__file__).resolve().parents[1] / "assets" / "uvdms"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urdf", type=Path, default=package / "urdf" / "uvdms.urdf", help="Portable packaged URDF")
    parser.add_argument("--output", type=Path, default=package / "mujoco", help="Sibling of the package's meshes directory")
    args = parser.parse_args()
    build(args.urdf.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
