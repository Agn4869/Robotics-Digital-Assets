#!/usr/bin/env python3
"""Create lightweight geometry previews for the packaged USD interaction assets.

This is a USD geometry preview, not Isaac Sim rendering: materials, textures,
MDL shaders and dynamics are intentionally omitted. Code is MIT licensed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pxr import Usd, UsdGeom

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "environments"
OUT = ROOT / "docs" / "images" / "environments"
ASSET_SPECS = {
    "push_button": (ASSETS / "ambench/push_button.usd", "Push button", "Press and release"),
    "lever": (ASSETS / "marine_mechanisms_v1/lever.usda", "Lever", "Bounded rotation"),
    "slider_with_rail": (ASSETS / "marine_mechanisms_v1/slider_with_rail.usda", "Slider with rail", "Linear slide"),
    "industrial_handwheel": (ASSETS / "industrial_handwheel/valve_2p5x.usda", "Industrial handwheel", "Wheel rotation"),
    "grounded_panel": (ASSETS / "marine_mechanisms_v1/grounded_panel.usda", "Grounded panel", "Mechanism mounting"),
    "textured_panel": (ASSETS / "panels/ship_green/panel.usda", "Textured panel", "Environment surface"),
}
COLORS = {
    "push_button": "#2aa6c8", "lever": "#e18a3b", "slider_with_rail": "#6aa84f",
    "industrial_handwheel": "#c58b45", "grounded_panel": "#65808b", "textured_panel": "#4d8663",
}


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    return (homogeneous @ matrix)[:, :3]


def primitive_mesh(prim) -> tuple[np.ndarray, list[list[int]]]:
    typ = prim.GetTypeName()
    if typ == "Mesh":
        obj = UsdGeom.Mesh(prim)
        points = np.asarray(obj.GetPointsAttr().Get(), dtype=float)
        counts = list(obj.GetFaceVertexCountsAttr().Get() or [])
        indices = list(obj.GetFaceVertexIndicesAttr().Get() or [])
        faces = []
        offset = 0
        for count in counts:
            face = indices[offset:offset + count]
            offset += count
            for i in range(1, len(face) - 1):
                faces.append([face[0], face[i], face[i + 1]])
        return points, faces
    if typ == "Cube":
        size = float(UsdGeom.Cube(prim).GetSizeAttr().Get() or 1.0) / 2
        points = np.array([[x, y, z] for x in (-size, size) for y in (-size, size) for z in (-size, size)], dtype=float)
        faces = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
        return points, faces
    if typ in {"Cylinder", "Capsule"}:
        obj = UsdGeom.Cylinder(prim) if typ == "Cylinder" else UsdGeom.Capsule(prim)
        radius = float(obj.GetRadiusAttr().Get() or 0.05)
        height = float(obj.GetHeightAttr().Get() or radius * 4) / 2
        axis = obj.GetAxisAttr().Get() or "Z"
        n = 24
        z = np.linspace(-height, height, 8 if typ == "Capsule" else 2)
        rings = [np.column_stack([radius * np.cos(np.linspace(0, 2 * np.pi, n, endpoint=False)), radius * np.sin(np.linspace(0, 2 * np.pi, n, endpoint=False)), np.full(n, value)]) for value in z]
        points = np.vstack(rings)
        faces = []
        for j in range(len(rings) - 1):
            for i in range(n):
                a, b = j * n + i, j * n + (i + 1) % n
                c, d = (j + 1) * n + (i + 1) % n, (j + 1) * n + i
                faces.extend([[a, b, c], [a, c, d]])
        if axis == "X":
            points = points[:, [2, 1, 0]]
        elif axis == "Y":
            points = points[:, [0, 2, 1]]
        return points, faces
    return np.empty((0, 3)), []


def collect_geometry(path: Path) -> list[np.ndarray]:
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"Could not open USD: {path}")
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    polygons = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Gprim):
            continue
        points, faces = primitive_mesh(prim)
        if len(points) == 0 or not faces:
            continue
        matrix = np.array(cache.GetLocalToWorldTransform(prim), dtype=float)
        points = transform_points(points, matrix)
        for face in faces:
            polygons.append(points[face])
    if not polygons:
        raise RuntimeError(f"No renderable geometry found in {path}")
    return polygons


def draw_asset(name: str, title: str, subtitle: str, polygons: list[np.ndarray], output: Path) -> None:
    vertices = np.concatenate(polygons, axis=0)
    center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    extent = max(float((vertices.max(axis=0) - vertices.min(axis=0)).max()), 1e-3)
    fig = plt.figure(figsize=(8, 6), dpi=150, facecolor="#111a24")
    ax = fig.add_subplot(111, projection="3d", facecolor="#111a24")
    ax.add_collection3d(Poly3DCollection(polygons, facecolors=COLORS[name], edgecolors="none", alpha=0.92, linewidths=0))
    ax.set_xlim(center[0] - extent / 2, center[0] + extent / 2)
    ax.set_ylim(center[1] - extent / 2, center[1] + extent / 2)
    ax.set_zlim(center[2] - extent / 2, center[2] + extent / 2)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=22, azim=135)
    ax.set_axis_off()
    fig.text(0.05, 0.92, title, color="#eef5fa", fontsize=19, weight="bold")
    fig.text(0.05, 0.875, subtitle, color="#9fc4d7", fontsize=11)
    fig.text(0.05, 0.035, "USD geometry preview  |  materials/textures/dynamics omitted  |  Agn4869", color="#aac4d0", fontsize=8)
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    generated = []
    for name, (path, title, subtitle) in ASSET_SPECS.items():
        polygons = collect_geometry(path)
        output = args.output / f"{name}.png"
        draw_asset(name, title, subtitle, polygons, output)
        generated.append(output)
        print(f"{name}: {len(polygons)} triangles -> {output}")
    # Contact sheet for the bilingual catalog.
    from PIL import Image, ImageDraw, ImageFont
    images = [Image.open(path).convert("RGB") for path in generated]
    cards = []
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for path, image in zip(generated, images):
        image.thumbnail((560, 390))
        card = Image.new("RGB", (600, 460), "#111a24")
        card.paste(image, ((600 - image.width) // 2, 35))
        ImageDraw.Draw(card).text((22, 12), path.stem, font=font, fill="#eef5fa")
        cards.append(card)
    sheet = Image.new("RGB", (1200, 1380), "#0b1118")
    for i, card in enumerate(cards):
        sheet.paste(card, ((i % 2) * 600, (i // 2) * 460))
    sheet.save(args.output / "interaction_assets_overview.png")
    print(f"overview: {args.output / 'interaction_assets_overview.png'}")


if __name__ == "__main__":
    main()
