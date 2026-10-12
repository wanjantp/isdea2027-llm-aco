"""Swath generation: cut a field into parallel flight strips.

A swath is a straight segment (p0, p1) the UAV must fly along; it can be flown in either direction.
Holes in the field polygon split a swath into several pieces (each piece is its own swath).

    from swaths import generate_swaths, best_angle
    sw = generate_swaths(field.polygon, width=5.0, angle_deg=best_angle(field.polygon, 5.0))
"""
from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, GeometryCollection
from shapely import affinity


@dataclass
class Swath:
    idx: int
    p0: tuple[float, float]
    p1: tuple[float, float]
    row: int                     # strip index (0 = first strip), useful for boustrophedon ordering

    @property
    def length(self) -> float:
        return math.hypot(self.p1[0] - self.p0[0], self.p1[1] - self.p0[1])

    def ends(self):
        return (self.p0, self.p1)


def generate_swaths(poly: Polygon, width: float, angle_deg: float, min_len: float = 1.0) -> list[Swath]:
    """Parallel strips of `width` at `angle_deg` (0 = east-west strips). Returns centre lines clipped to the field."""
    # rotate field so strips are horizontal, clip, rotate back
    c = poly.centroid
    rot = affinity.rotate(poly, -angle_deg, origin=c)
    minx, miny, maxx, maxy = rot.bounds
    swaths, row = [], 0
    y = miny + width / 2
    while y <= maxy - width / 2 + 1e-9 or (y < maxy and not swaths):
        line = LineString([(minx - 1, y), (maxx + 1, y)])
        inter = rot.intersection(line)
        pieces = []
        if isinstance(inter, LineString):
            pieces = [inter]
        elif isinstance(inter, (MultiLineString, GeometryCollection)):
            pieces = [g for g in inter.geoms if isinstance(g, LineString)]
        for seg in pieces:
            if seg.length < min_len:
                continue
            back = affinity.rotate(seg, angle_deg, origin=c)
            (x0, y0), (x1, y1) = back.coords[0], back.coords[-1]
            swaths.append(Swath(len(swaths), (x0, y0), (x1, y1), row))
        row += 1
        y += width
    return swaths


def best_angle(poly: Polygon, width: float, step_deg: float = 5.0) -> float:
    """Angle that minimises the number of swaths (fewest turns). Ties -> longest mean swath."""
    best, best_key = 0.0, None
    for a in np.arange(0, 180, step_deg):
        sw = generate_swaths(poly, width, float(a))
        if not sw:
            continue
        key = (len(sw), -sum(s.length for s in sw) / len(sw))
        if best_key is None or key < best_key:
            best, best_key = float(a), key
    return best


def longest_edge_angle(poly: Polygon) -> float:
    """Angle of the longest exterior edge (common agricultural heuristic)."""
    coords = list(poly.exterior.coords)
    best, blen = 0.0, -1
    for (x0, y0), (x1, y1) in zip(coords[:-1], coords[1:]):
        l = math.hypot(x1 - x0, y1 - y0)
        if l > blen:
            blen, best = l, math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180
    return best


if __name__ == "__main__":
    from fields import generate_synthetic
    f = generate_synthetic(3, seed=1)[2]
    a = best_angle(f.polygon, 5.0)
    sw = generate_swaths(f.polygon, 5.0, a)
    print(f"{f.id}: {f.area_ha:.1f} ha, best angle {a:.0f} deg, {len(sw)} swaths, total {sum(s.length for s in sw):.0f} m")
