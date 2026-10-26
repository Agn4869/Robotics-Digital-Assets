#!/usr/bin/env python3
"""Render a lightweight preview from a mesh-based URDF.

This is a geometry preview, not a dynamics renderer. Code is MIT licensed.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial.transform import Rotation
import trimesh


def transform(xyz: str, rpy: str) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = Rotation.from_euler("xyz", np.fromstring(rpy or "0 0 0", sep=" ")).as_matrix()
    T[:3, 3] = np.fromstring(xyz or "0 0 0", sep=" ")
    return T


def mesh_path(uri: str, urdf: Path) -> Path:
    if uri.startswith("package://"):
        return urdf.parent.parent / "meshes" / Path(uri.split("/", 3)[-1]).name
    return (urdf.parent / uri).resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("urdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = ET.parse(args.urdf).getroot()
    links = {x.attrib["name"]: x for x in root.findall("link")}
    joints = root.findall("joint")
    parent_joint = {j.find("child").attrib["link"]: j for j in joints}
    root_link = next(name for name in links if name not in parent_joint)
    world = {root_link: np.eye(4)}
    pending = list(joints)
    while pending:
        progress = False
        for joint in pending[:]:
            parent, child = joint.find("parent").attrib["link"], joint.find("child").attrib["link"]
            if parent not in world:
                continue
            origin = joint.find("origin")
            T = transform(origin.attrib.get("xyz", "0 0 0"), origin.attrib.get("rpy", "0 0 0")) if origin is not None else np.eye(4)
            if joint.attrib.get("type") in {"revolute", "continuous"}:
                axis = np.fromstring(joint.find("axis").attrib.get("xyz", "1 0 0"), sep=" ")
                motion = np.eye(4); motion[:3, :3] = Rotation.from_rotvec(axis * 0.35).as_matrix()
                T = T @ motion
            world[child] = world[parent] @ T
            pending.remove(joint); progress = True
        if not progress:
            raise RuntimeError("URDF joint graph is not connected")
    polygons = []
    for name, link in links.items():
        link_world = world[name]
        for visual in link.findall("visual"):
            geometry = visual.find("geometry/mesh")
            if geometry is None:
                continue
            mesh = trimesh.load_mesh(str(mesh_path(geometry.attrib["filename"], args.urdf)), process=False)
            if not isinstance(mesh, trimesh.Trimesh):
                continue
            origin = visual.find("origin")
            T = transform(origin.attrib.get("xyz", "0 0 0"), origin.attrib.get("rpy", "0 0 0")) if origin is not None else np.eye(4)
            if geometry.get("scale"):
                scale = np.fromstring(geometry.attrib["scale"], sep=" "); T[:3, :3] = T[:3, :3] @ np.diag(scale)
            mesh = mesh.copy(); mesh.apply_transform(link_world @ T)
            faces = mesh.faces
            if len(faces) > 12000:
                faces = faces[np.linspace(0, len(faces) - 1, 12000, dtype=int)]
            polygons.extend(mesh.vertices[faces])
    vertices = np.concatenate(polygons)
    center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    extent = max(float((vertices.max(axis=0) - vertices.min(axis=0)).max()), 1e-3)
    fig = plt.figure(figsize=(8, 6), dpi=150, facecolor="#111a24")
    ax = fig.add_subplot(111, projection="3d", facecolor="#111a24")
    ax.add_collection3d(Poly3DCollection(polygons, facecolors="#4d9bb3", edgecolors="none", alpha=0.9))
    ax.set_xlim(center[0] - extent / 2, center[0] + extent / 2); ax.set_ylim(center[1] - extent / 2, center[1] + extent / 2); ax.set_zlim(center[2] - extent / 2, center[2] + extent / 2)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=24, azim=135); ax.set_axis_off()
    fig.text(0.05, 0.92, "Environment URDF export", color="#eef5fa", fontsize=19, weight="bold")
    fig.text(0.05, 0.875, "Two revolute joints  |  URDF/STL geometry preview", color="#9fc4d7", fontsize=11)
    fig.text(0.05, 0.035, "URDF/STL geometry preview  |  materials/dynamics omitted  |  Agn4869", color="#aac4d0", fontsize=8)
    args.output.parent.mkdir(parents=True, exist_ok=True); fig.savefig(args.output, bbox_inches="tight", facecolor=fig.get_facecolor()); plt.close(fig)
    print(args.output)


if __name__ == "__main__":
    main()
