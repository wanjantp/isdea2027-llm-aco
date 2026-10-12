# Fields2Benchmark (converted)

Source: Mier, Valente, de Bruin (2023). Fields2Benchmark dataset. Zenodo. https://doi.org/10.5281/zenodo.14524734
License: CC BY 4.0. Fields extracted from EuroCrops (Netherlands, Estonia, Lithuania). Downloaded 2026-10-12 (wkt.zip only; imgs.zip not needed).

Cite: Mier G., Valente J., de Bruin S. (2023). Fields2Cover: An Open-Source Coverage Path Planning Library for
Unmanned Agricultural Vehicles. IEEE RA-L 8(4):2166-2172. doi:10.1109/LRA.2023.3248439

## Files
- fields2benchmark_local.geojson  350 polygons in metres (UTM zone per field, EPSG in properties), translated so bbox min = (0,0).
                                  Interior rings = holes (49 fields have them; treat as no-fly obstacles).
- fields2benchmark_metadata.csv   area, perimeter, vertices, holes, convexity, compactness, bbox, centroid
- split.json                      FIXED split, do not change after tuning starts:
                                  validation (50) for tuning/selection, test_A (100) main test,
                                  test_B (large >=10 ha) scale generalisation, pool (unused spares)
- wkt/                            original WKT files (WGS84)

## Stats
350 fields: NL 140, EE 97, LT 113. Area 0.5-25.9 ha (median 2.15). 86 fields with convexity < 0.85.
