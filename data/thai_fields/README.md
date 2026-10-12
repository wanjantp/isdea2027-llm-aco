# Test-C: Thai agricultural fields (Khon Kaen)

20 real field polygons for the Test-C generalization / case-study set.
Selected from 500 OpenStreetMap `landuse=farmland` ways in the bounding box
lat 16.20–16.60, lon 102.60–103.00 (Khon Kaen province), downloaded 2026-10-12.

## Selection protocol (reproducible)

1. Keep closed ways with >= 4 vertices and area 1–30 ha (316 of 500 qualified).
2. Stratify into 4 size bins: 1–2.5, 2.5–5, 5–10, 10–30 ha.
3. In each bin pick 3 "irregular" (area / convex-hull area < 0.85) and 2 "regular" fields,
   spread evenly over the candidates sorted by OSM id (deterministic, no cherry-picking).
4. Result: 20 fields, 12 irregular / 8 regular, 1.0–21.2 ha, 4–80 vertices.

## Files

| File | Content |
|---|---|
| `thai_fields_wgs84.geojson` | Original polygons in WGS84 lon/lat (open directly in QGIS) |
| `thai_fields_utm48n_local.geojson` | Same polygons in metres (EPSG:32648, UTM 48N), each translated so its bbox min is (0,0). `utm_origin_x/y` restore absolute UTM. Use this for planning. |
| `thai_fields_metadata.csv` | One row per field: area, perimeter, vertices, convexity, compactness, bbox, centroid |
| `thai_fields_preview.png` | Thumbnail grid of all 20 fields |
| `load_fields.py` | Loader: `python load_fields.py` prints a summary; `load_fields()` returns a list of dicts with shapely polygons |

## Properties per feature

- `field_id` TH-KK-01 … TH-KK-20 (sorted by area)
- `osm_way_id` source way id (for citation / re-download)
- `area_ha`, `perimeter_m`, `n_vertices`
- `convexity` = area / convex-hull area (1.0 = convex)
- `compactness` = 4·pi·area / perimeter^2 (1.0 = circle)
- `shape_class` irregular (< 0.85 convexity) or regular

## Licence and citation

Data © OpenStreetMap contributors, Open Database License (ODbL) 1.0.
Cite as: "OpenStreetMap contributors (2026). Farmland polygons, Khon Kaen, Thailand.
Retrieved 2026-10-12 via Overpass API. https://www.openstreetmap.org/copyright".

## Caveats to state in the paper

- OSM field boundaries are volunteer-mapped; they may lag real parcel changes.
  Verify a few against current satellite imagery (Google/Bing) in QGIS before publishing.
- Polygons are 2D; no obstacles (pylons, ponds) are included. Add them manually if needed.
- The region is mostly rice/sugarcane paddies; the irregular class reflects typical Isan smallholdings.
- To extend to another province, change the bbox in the Overpass query and re-run the same protocol.

## Overpass query used

```
[out:json][timeout:90];
way["landuse"="farmland"](16.20,102.60,16.60,103.00);
out geom 500;
```
