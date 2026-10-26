#!/usr/bin/env python3
"""Package authorized UVDMS CAD assets; requires trimesh and fast-simplification.

Run with --source-urdf FILE --source-meshes DIRECTORY [--output DIRECTORY].
Source geometry coordinates, URDF transforms, masses and inertias are not rescaled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import xml.etree.ElementTree as ET

import fast_simplification
import trimesh


PROJECT_URL = "https://github.com/Agn4869/Robotics-Digital-Assets"
LICENSE = "CC-BY-NC-4.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometry_record(mesh: trimesh.Trimesh) -> dict:
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "bounds_m": mesh.bounds.tolist(),
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
    }


def load_mesh(path: Path) -> trimesh.Trimesh:
    # Merge STL's repeated corner vertices without changing geometry or repairing it.
    mesh = trimesh.load_mesh(path, file_type="stl", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError(f"Expected a nonempty triangle mesh: {path.name}")
    mesh.merge_vertices()
    return mesh


def simplify(mesh: trimesh.Trimesh, target: int, name: str) -> trimesh.Trimesh:
    if len(mesh.faces) <= target:
        return mesh
    vertices, faces = fast_simplification.simplify(
        mesh.vertices, mesh.faces, target_count=target, agg=7.0
    )
    result = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    result.merge_vertices()
    if not len(result.faces):
        raise ValueError(f"Simplification produced an empty mesh: {name}")
    # Do not silently trade a closed source surface for an open output surface.
    # This edge-incidence check is not a proof of physical or geometric validity.
    if mesh.is_watertight and not result.is_watertight:
        raise ValueError(f"Simplification opened a watertight source mesh: {name}")
    # Multi-component CAD can reach a topology floor above the requested budget.
    # Retain that geometry rather than delete components to hit an arbitrary count.
    if len(result.faces) > target:
        print(f"{name}: topology-preserving result {len(result.faces):,} exceeds requested target {target:,}", flush=True)
    return result


def package(source_urdf: Path, source_meshes: Path, output: Path) -> None:
    source_urdf = source_urdf.resolve(strict=True)
    source_meshes = source_meshes.resolve(strict=True)
    output = output.resolve()
    if not source_urdf.is_file() or not source_meshes.is_dir():
        raise ValueError("Source URDF must be a file and source meshes must be a directory")
    if output.is_relative_to(source_meshes) or source_meshes.is_relative_to(output):
        raise ValueError("Output must not overlap the source mesh directory")
    if source_urdf.is_relative_to(output):
        raise ValueError("Output must not contain the source URDF")

    # Default ElementTree parsing discards all source comments, including paths.
    tree = ET.parse(source_urdf)
    root = tree.getroot()
    if root.tag != "robot":
        raise ValueError("Source must be a URDF robot")
    mesh_elements = root.findall(".//mesh")
    inputs: dict[str, Path] = {}
    uri_names: dict[str, str] = {}
    destination_names: dict[str, str] = {}
    for element in mesh_elements:
        uri = element.attrib["filename"]
        basename = PurePosixPath(uri.replace("\\", "/")).name
        if Path(basename).suffix.lower() != ".stl":
            raise ValueError(f"Only STL mesh references are supported: {basename}")
        name = Path(basename).stem + ".stl"
        previous = destination_names.setdefault(name.casefold(), basename)
        if previous != basename:
            raise ValueError(f"Mesh basenames collide on a case-insensitive filesystem: {basename}")
        source = (source_meshes / basename).resolve(strict=True)
        if not source.is_relative_to(source_meshes) or not source.is_file():
            raise ValueError(f"Mesh reference must resolve to a file in the source directory: {basename}")
        inputs[name] = source
        uri_names[uri] = name
    if not inputs:
        raise ValueError("Source URDF contains no meshes")

    # All referenced inputs have been checked before any output directory is made.
    for element in mesh_elements:
        element.set("filename", "../meshes/" + uri_names[element.attrib["filename"]])
    root.insert(0, ET.Comment(
        " Portable UVDMS model derived from authorized SolidWorks CAD exports. "
        "Mesh coordinates and source kinematic/inertial parameters are retained. "
        "Assets: CC BY-NC 4.0; attribution: Agn4869. "
    ))
    links = root.findall("link")
    joints = root.findall("joint")
    movable = [joint for joint in joints if joint.get("type") != "fixed"]
    mimic = [joint for joint in joints if joint.find("mimic") is not None]
    metadata = {
        "schema_version": 1,
        "name": "uvdms",
        "title": "UVDMS dual-arm underwater vehicle/manipulator model",
        "license": LICENSE,
        "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "attribution": "Agn4869",
        "source_project_url": PROJECT_URL,
        "source": {"format": "URDF and SolidWorks-derived STL", "urdf_sha256": sha256(source_urdf)},
        "units": {"length": "m", "mass": "kg", "inertia": "kg*m^2"},
        "mass_kg": sum(float(node.attrib["value"]) for node in root.findall("link/inertial/mass")),
        "counts": {
            "links": len(links), "joints": len(joints),
            "fixed_joints": len(joints) - len(movable),
            "movable_joints": len(movable), "mimic_joints": len(mimic),
            "independent_movable_joints": sum(joint.find("mimic") is None for joint in movable),
            "links_without_inertial": sum(link.find("inertial") is None for link in links),
            "unique_meshes": len(inputs),
        },
        "simplification": {
            "method": "fast-simplification quadric-error mesh decimation",
            "hull_triangle_target": 40000, "other_mesh_triangle_cap": 6000,
            "disclaimer": (
                "Meshes are reduced visual/collision approximations of the source CAD, not manufacturing geometry. "
                "Small meshes are preserved geometrically. Units, origins and URDF inertias are unchanged; "
                "inertias are not recomputed from reduced meshes. Watertightness is an edge-incidence diagnostic, "
                "not proof of topology, absence of self-intersections, or physical fidelity. "
                "Existing non-watertight input geometry is not repaired. "
                "Grippers retain affine mimic approximations, not closed four-bar constraints. "
                "No hydrodynamics or hardware-fidelity validation is claimed."
            ),
        },
        "meshes": {},
    }
    output.mkdir(parents=True, exist_ok=True)
    # Stage the complete owned bundle before publishing; leave MuJoCo files alone.
    with tempfile.TemporaryDirectory(prefix=".uvdms-package-", dir=output.parent) as temp:
        stage = Path(temp)
        (stage / "meshes").mkdir()
        (stage / "urdf").mkdir()
        for name, source in inputs.items():
            original = load_mesh(source)
            target = 40000 if name == "base_link.stl" else 6000
            reduced = simplify(original, target, name)
            destination = stage / "meshes" / name
            destination.write_bytes(trimesh.exchange.stl.export_stl(reduced))
            # Record actual binary-STL geometry (float32), not pre-export doubles.
            exported = load_mesh(destination)
            if original.is_watertight and not exported.is_watertight:
                raise ValueError(f"STL serialization opened a watertight mesh: {name}")
            metadata["meshes"][name] = {
                "source": {"name": source.name, "sha256": sha256(source),
                           "bytes": source.stat().st_size, **geometry_record(original)},
                "generated": {"path": "meshes/" + name, "sha256": sha256(destination),
                              "bytes": destination.stat().st_size, **geometry_record(exported)},
                "triangle_target": target,
                "simplified": len(original.faces) > target,
            }
            print(f"{name}: {len(original.faces):,} -> {len(exported.faces):,} triangles", flush=True)
        urdf = stage / "urdf" / "uvdms.urdf"
        tree.write(urdf, encoding="utf-8", xml_declaration=True)
        metadata["generated"] = {"urdf_path": "urdf/uvdms.urdf", "urdf_sha256": sha256(urdf)}
        metadata["counts"]["source_triangles"] = sum(item["source"]["triangles"] for item in metadata["meshes"].values())
        metadata["counts"]["generated_triangles"] = sum(item["generated"]["triangles"] for item in metadata["meshes"].values())
        (stage / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        (output / "meshes").mkdir(exist_ok=True)
        (output / "urdf").mkdir(exist_ok=True)
        for name in inputs:
            (stage / "meshes" / name).replace(output / "meshes" / name)
        urdf.replace(output / "urdf" / "uvdms.urdf")
        (stage / "metadata.json").replace(output / "metadata.json")
    print(f"Packaged {len(links)} links, {len(joints)} joints, {len(inputs)} unique meshes")
    print(f"URDF: {output / 'urdf' / 'uvdms.urdf'}")
    print(f"Meshes: {output / 'meshes'}")
    print(f"Metadata: {output / 'metadata.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-urdf", type=Path, required=True)
    parser.add_argument("--source-meshes", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "assets" / "uvdms")
    args = parser.parse_args()
    package(args.source_urdf, args.source_meshes, args.output)


if __name__ == "__main__":
    main()
