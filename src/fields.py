"""Field loading and synthetic field generation.

A *field* is a shapely Polygon in local metres (bbox min at (0,0)); holes are obstacles.

    from fields import load_fields, generate_synthetic
    fields = load_fields("data/thai_fields/thai_fields_utm48n_local.geojson")
    fields = load_fields("data/fields2benchmark/fields2benchmark_local.geojson", ids=split["test_A"])
    synth  = generate_synthetic(n=30, seed=0)
"""
from __future__ import annotations
import json, math, random, os
from dataclasses import dataclass, field
from typing import Iterable
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.validation import make_valid
from shapely import affinity


@dataclass
class Field:
    id: str
    polygon: Polygon            # metres, bbox min at (0,0)
    props: dict = field(default_factory=dict)

    @property
    def area_ha(self) -> float:
        return self.polygon.area / 1e4


def _norm(p: Polygon) -> Polygon:
    """Move polygon so bbox min is (0,0)."""
    minx, miny, _, _ = p.bounds
    return affinity.translate(p, -minx, -miny)


def load_fields(path: str, ids: Iterable[str] | None = None) -> list[Field]:
    fc = json.load(open(path, encoding="utf-8"))
    want = set(ids) if ids is not None else None
    out = []
    for f in fc["features"]:
        p = f["properties"]
        fid = p.get("field_id")
        if want is not None and fid not in want:
            continue
        rings = f["geometry"]["coordinates"]
        poly = Polygon(rings[0], rings[1:])
        if not poly.is_valid:
            poly = make_valid(poly)
            if isinstance(poly, MultiPolygon) or poly.geom_type == "GeometryCollection":
                poly = max((g for g in poly.geoms if g.geom_type == "Polygon"), key=lambda g: g.area)
        out.append(Field(fid, _norm(poly), p))
    if want is not None:  # keep the order of ids
        order = {k: i for i, k in enumerate(ids)}
        out.sort(key=lambda x: order[x.id])
    return out


def load_split(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


# ---------------------------------------------------------------- synthetic fields

def _random_polygon(rng: random.Random, n_pts: int, radius: float, irregularity: float, spikiness: float) -> Polygon:
    """Star-shaped random polygon (angles jittered by `irregularity`, radii by `spikiness`)."""
    angles = []
    step = 2 * math.pi / n_pts
    lo, hi = step * (1 - irregularity), step * (1 + irregularity)
    acc = 0.0
    for _ in range(n_pts):
        d = rng.uniform(lo, hi); angles.append(acc); acc += d
    angles = [a * 2 * math.pi / acc for a in angles]
    pts = []
    for a in angles:
        r = max(radius * 0.2, rng.gauss(radius, spikiness * radius))
        pts.append((r * math.cos(a), r * math.sin(a)))
    p = Polygon(pts)
    if not p.is_valid:
        p = make_valid(p)
        if p.geom_type != "Polygon":
            p = max((g for g in p.geoms if g.geom_type == "Polygon"), key=lambda g: g.area)
    return p


def generate_synthetic(n: int = 30, seed: int = 0, area_range_ha=(1.0, 12.0), p_hole: float = 0.3,
                       shape_mix=(("regular", 0.4), ("irregular", 0.6))) -> list[Field]:
    """Random fields covering the size/shape spread of real data.

    regular   : 4-8 vertices, mild jitter (rectangles, trapezoids)
    irregular : 10-30 vertices, strong jitter, sometimes notched / with 1 hole
    """
    rng = random.Random(seed)
    out = []
    for i in range(n):
        kind = rng.choices([k for k, _ in shape_mix], [w for _, w in shape_mix])[0]
        area_target = 10_000 * math.exp(rng.uniform(math.log(area_range_ha[0]), math.log(area_range_ha[1])))
        if kind == "regular":
            poly = _random_polygon(rng, rng.randint(4, 8), 100, irregularity=0.3, spikiness=0.12)
        else:
            poly = _random_polygon(rng, rng.randint(10, 30), 100, irregularity=0.7, spikiness=0.35)
            # cut a rectangular notch from one side half the time
            if rng.random() < 0.5:
                minx, miny, maxx, maxy = poly.bounds
                w, h = maxx - minx, maxy - miny
                notch = Polygon([(minx - 1, miny + h * 0.4), (minx + w * rng.uniform(0.2, 0.5), miny + h * 0.4),
                                 (minx + w * rng.uniform(0.2, 0.5), miny + h * 0.6), (minx - 1, miny + h * 0.6)])
                cut = poly.difference(notch)
                if cut.geom_type == "Polygon" and cut.area > 0.5 * poly.area:
                    poly = cut
        # stretch to a random aspect ratio, rotate, scale to target area
        poly = affinity.scale(poly, rng.uniform(0.6, 1.6), 1.0)
        poly = affinity.rotate(poly, rng.uniform(0, 180))
        s = math.sqrt(area_target / poly.area)
        poly = affinity.scale(poly, s, s)
        # optional obstacle hole (pond, pylon)
        if kind == "irregular" and rng.random() < p_hole:
            c = poly.representative_point()
            r = math.sqrt(poly.area) * rng.uniform(0.04, 0.10)
            hole = Point(c.x + rng.uniform(-r, r), c.y + rng.uniform(-r, r)).buffer(r, 8)
            cand = poly.difference(hole)
            if cand.geom_type == "Polygon" and len(cand.interiors) == 1:
                poly = cand
        poly = _norm(poly)
        out.append(Field(f"SYN-{seed:02d}-{i:03d}", poly,
                         {"field_id": f"SYN-{seed:02d}-{i:03d}", "shape_class": kind, "area_ha": round(poly.area / 1e4, 2),
                          "n_vertices": len(poly.exterior.coords) - 1, "n_holes": len(poly.interiors), "source": "synthetic", "seed": seed}))
    return out


def save_fields(fields: list[Field], path: str, name: str = "fields") -> None:
    feats = []
    for f in fields:
        rings = [list(map(lambda c: [round(c[0], 2), round(c[1], 2)], f.polygon.exterior.coords))]
        rings += [list(map(lambda c: [round(c[0], 2), round(c[1], 2)], r.coords)) for r in f.polygon.interiors]
        feats.append({"type": "Feature", "properties": {**f.props, "field_id": f.id}, "geometry": {"type": "Polygon", "coordinates": rings}})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump({"type": "FeatureCollection", "name": name, "features": feats}, open(path, "w"))


if __name__ == "__main__":
    fs = generate_synthetic(30, seed=0)
    print(f"{len(fs)} synthetic fields, area {min(f.area_ha for f in fs):.1f}-{max(f.area_ha for f in fs):.1f} ha, "
          f"holes: {sum(len(f.polygon.interiors) for f in fs)}, all valid: {all(f.polygon.is_valid for f in fs)}")
