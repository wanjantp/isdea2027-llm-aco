"""Loader for the Test-C Thai field dataset.

Usage:
    from load_fields import load_fields
    fields = load_fields()            # list of dicts, polygons in local metres
    poly = fields[0]["polygon"]       # shapely Polygon

Requires: shapely  (pip install shapely)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "thai_fields_utm48n_local.geojson")


def load_fields(path=LOCAL, shape_class=None, min_ha=None, max_ha=None):
    from shapely.geometry import shape
    fc = json.load(open(path, encoding="utf-8"))
    out = []
    for f in fc["features"]:
        p = f["properties"]
        if shape_class and p["shape_class"] != shape_class:
            continue
        if min_ha is not None and p["area_ha"] < min_ha:
            continue
        if max_ha is not None and p["area_ha"] > max_ha:
            continue
        out.append({**p, "polygon": shape(f["geometry"])})
    return out


if __name__ == "__main__":
    fields = load_fields()
    print(f"{len(fields)} fields loaded from {os.path.basename(LOCAL)}")
    print(f"{'id':10s} {'ha':>6s} {'verts':>5s} {'convex':>7s} class")
    for f in fields:
        print(f"{f['field_id']:10s} {f['area_ha']:6.2f} {f['n_vertices']:5d} {f['convexity']:7.3f} {f['shape_class']}")
