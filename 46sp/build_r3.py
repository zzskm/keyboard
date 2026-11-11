"""Rebuild the SolidCraft flat parts and the switch inventory from the r3 drawing."""

import argparse
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import ezdxf
from shapely.geometry import Polygon


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source/46sp_plate_r3.converted.dxf"
PLATES = {
    "L_R0": ("1384", 6), "L_R1": ("138C", 6), "L_R2": ("23BE", 6),
    "L_R3": ("132E", 3), "R_R0": ("1695", 6), "R_R1": ("1696", 6),
    "R_R2": ("23DC", 5), "R_R3": ("1771", 3), "R_Thumb": ("178A", 4),
}
SUPPORTS = {
    "Rib_Full_A": "26E8", "Rib_Full_B": "26E9", "Rib_Full_C": "2730",
    "Rib_Short_A": "2723", "Rib_Short_B": "2724", "Rib_Short_C": "2725",
    "Rib_Short_D": "2726", "Rib_Short_E": "2727", "Rib_Short_F": "2728",
    "Rib_End_A": "2767", "Rib_End_B": "276F",
    "Cheek_A": "229E", "Cheek_B": "22A1", "Cheek_C": "22B6", "Cheek_D": "22B8",
}
CHEEK_CUTS = {"229E": "22A0", "22A1": "22A2", "22B6": "22CB", "22B8": "22B9"}


def read_profiles():
    drawing = ezdxf.readfile(SOURCE)
    if drawing.units != 4:
        raise ValueError("Expected a millimetre drawing")
    profiles = {}
    for entity in drawing.modelspace().query("LWPOLYLINE"):
        handle = entity.dxf.handle
        points = [(float(x), float(y)) for x, y in entity.get_points("xy")]
        explicit_closure = math.dist(points[0], points[-1]) < 1e-6
        if entity.has_arc or not (entity.closed or explicit_closure):
            raise ValueError(f"Unsupported contour {handle}")
        profile = Polygon(points[:-1] if explicit_closure else points)
        if not profile.is_valid or profile.area == 0:
            raise ValueError(f"Invalid contour {handle}")
        profiles[handle] = profile
    return profiles


def dxf_text(profiles):
    """Write ASCII line entities so each sketch travels inside its SolidCraft file."""
    tags = ["0", "SECTION", "2", "ENTITIES"]
    for profile in profiles:
        points = list(profile.exterior.coords)
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            tags.extend(["0", "LINE", "8", "0", "10", str(x0), "20", str(y0),
                         "11", str(x1), "21", str(y1)])
    return "\n".join(tags + ["0", "ENDSEC", "0", "EOF", ""])


def add_part(commands, name, thickness, outline, holes):
    sketch = f"{name}_Profile"
    loops = [outline, *holes]
    edges = sum(len(loop.exterior.coords) - 1 for loop in loops)
    commands.extend([
        {"command": "sketch.create", "params": {"name": sketch, "plane": "XY"}},
        {"command": "sketch.insert_dxf", "params": {"text": dxf_text(loops)}},
        {"command": "sketch.constraint.fix", "params": {
            "entities": [f"l{index}" for index in range(1, edges + 1)], "fixed": True,
        }},
        {"command": "sketch.solve", "params": {}},
        {"command": "sketch.finish", "params": {}},
        {"command": "solid.extrude", "params": {
            "sketch": sketch, "operation": "new", "distance": thickness,
            "name": f"Extrude {name}", "body_name": name,
        }},
    ])


def build(cli, output, parameters, parts, profiles):
    commands = [
        {"command": "parameters.change", "params": {"name": name, "value": value}}
        for name, value in parameters.items()
    ]
    expected = {}
    for name, handle, thickness, cuts in parts:
        outline = profiles[handle]
        holes = [profiles[cut] for cut in cuts]
        if any(not outline.contains(hole) for hole in holes):
            raise ValueError(f"Contour outside {name}")
        add_part(commands, name, thickness, outline, holes)
        expected[name] = (outline.area - sum(hole.area for hole in holes)) * parameters[thickness]

    with TemporaryDirectory() as work:
        recipe = Path(work) / "build.json"
        design = Path(work) / output.name
        measurement = Path(work) / "measure.json"
        recipe.write_text(json.dumps(commands), encoding="utf-8")
        subprocess.run([cli, "run", str(recipe), "--save", str(design),
                        "--json-out", str(measurement)], check=True)
        result = json.loads(measurement.read_text(encoding="utf-8"))
        bodies = {body["name"]: body for body in result["bodies"]}
        if bodies.keys() != expected.keys():
            raise ValueError(f"{output.name}: unexpected bodies {sorted(bodies)}")
        for name, volume in expected.items():
            body = bodies[name]
            if not body["closed"] or not math.isclose(body["volume_mm3"], volume, abs_tol=0.02):
                raise ValueError(f"{name}: expected a closed body of {volume:.3f} mm³, got {body}")
        output.write_bytes(design.read_bytes())
    print(f"{output.name}: {len(expected)} closed bodies, {sum(expected.values()):.3f} mm³")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default="solidcraft-cli")
    parser.add_argument("--out", type=Path, default=ROOT / "model")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    profiles = read_profiles()
    switch_holes = {handle: profile for handle, profile in profiles.items()
                    if all(abs(size - 14) < 0.03 for size in (
                        profile.bounds[2] - profile.bounds[0],
                        profile.bounds[3] - profile.bounds[1]))}
    plates = []
    switches = []
    for name, (handle, count) in PLATES.items():
        cuts = [cut for cut, hole in switch_holes.items() if profiles[handle].contains(hole)]
        if len(cuts) != count:
            raise ValueError(f"{name}: expected {count} switches, found {len(cuts)}")
        cuts.sort(key=lambda cut: switch_holes[cut].centroid.x)
        plates.append((name, handle, "plate_t", cuts))
        switches.extend({"plate": name, "handle": cut,
                         "x_mm": round(switch_holes[cut].centroid.x, 5),
                         "y_mm": round(switch_holes[cut].centroid.y, 5)} for cut in cuts)
    if len(switches) != len(switch_holes) or len({key["handle"] for key in switches}) != len(switches):
        raise ValueError("Each switch opening must belong to exactly one plate")

    supports = [(name, handle, "cheek_t" if handle in CHEEK_CUTS else "rib_t",
                 [CHEEK_CUTS[handle]] if handle in CHEEK_CUTS else [])
                for name, handle in SUPPORTS.items()]
    build(args.cli, args.out / "r3-plates.sc", {"plate_t": 5}, plates, profiles)
    build(args.cli, args.out / "r3-supports.sc", {"rib_t": 1.5, "cheek_t": 5}, supports, profiles)
    (args.out / "r3-switches.json").write_text(json.dumps(switches, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
