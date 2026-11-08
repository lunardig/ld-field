# USGS LGRS WKT and 25 km grid comparison — Revision 21

**Date:** 2026-11-08  
**Scope:** Official upstream GIS release, 92 projected LTM/LPS zones, expected 25 km tile inventory.  
**Status:** **Passed WKT parameter verification and projected 25 km source-boundary alignment checks.** **NOT** a certificate of exhaustive 1 m cut-square classification.

## Input and reproducibility

- Official dataset: *Lunar Grid Reference System (LGRS) Rasters and Shapefiles*.
- USGS DOI: https://doi.org/10.5066/P13YPWQD
- Preserved upstream ZIP: https://github.com/lunardig/ld-field/releases/tag/usgs-lgrs-source-2024
- Unmodified ZIP SHA-256: `0ab9a17428a5ac076be301dd027cacb1ad3b6e06878c3768a488f9deda3c7623`.
- Audit workflow and retrievable evidence: https://github.com/lunardig/ld-field/actions/runs/42519335993
- Implementation: `src/validate_usgs_release.py`, `src/inspect_usgs_geometry.py`, `src/compare_usgs_grid.py`.
- Audited WKT entries: **381**, of which 278 are Transverse Mercator, 6 Polar Stereographic (variant A), and 97 geographic coordinate systems; **zero WKT parse errors**.
- Every WKT in the archive has sphere semi-major/semi-minor axes **1,737,400 m**.
- All projected LTM WKTs use scale **0.999**, false easting **250,000 m**, and false northing **0 m north / 2,500,000 m south**. Every northern and southern zone has the correct 8° central-meridian series from **−176° through +176°**, with 45 centers in each hemisphere.
- All projected polar WKTs use scale **0.994**, false east/north origins **500,000 m**, and natural origin latitude **±90°**.

**Evidence source:** GitHub Actions artifact `usgs-lgrs-projection-evidence` attached to the linked audit run contains `usgs-lgrs-release-audit.json`, `usgs-lgrs-grid-geometry.json`, and `usgs-lgrs-candidate-comparison.json`.

## The 80° vs. 82° distinction

The **official USGS LTM shapefiles extend to ±82° latitude**. Revision 21 intentionally removes the 80°–82° LTM overlap, assigning coordinates poleward of ±80° exclusively to LPS.

Therefore, the official LTM polygon feature count must **not** be used directly as the number of Lunar Dig 25 km tiles.

The USGS LGRS shapefiles may also split a single projected 25 km tile into multiple polygon features at latitude-band boundaries. Revision 21 correctly uses `(zone, easting_km, northing_km)` rather than the display label as the unique address.

## Results of all 92 zones

| Per-zone metric | Each of 90 LTM zones | Each of 2 LPS zones |
| --- | ---: | ---: |
| USGS projected 25 km shapefile polygon features | 832 | 516 |
| Distinct projected 25 km square keys | 760 | 516 |
| Duplicate features from latitude-band splitting | 72 | 0 |
| Squares intersecting Revision 21's assigned zone | **754** | **516** |
| Squares exclusively in the USGS 80°–82° LTM overlap | 6 | 0 |
| Features extending more than 1 m outside nominal 25 km square | **0** | **0** |

**Moon-wide candidate 25 km tile inventory:** `90 × 754 + 2 × 516 = 68,892` unique zone-local tile keys, matching the brief's ~68,900 estimate.

Boundary comparison:

- For every vertex of every official zone-border polygon in the 92 projected-zone shapefiles, evaluate its inverse spherical LTM or radial LPS coordinate.
- Compare each vertex to its nearest analytically specified USGS edge: LTM equator, ±4° longitude from central meridian, ±82° latitude; or LPS 80° polar circle.
- **Maximum vertex-to-analytic-boundary residual:** `3.757054326843114e-9 m`, arising from floating-point arithmetic. This is a *vertex-level* check, not a Hausdorff distance between continuous curves.
- Each official 25 km polygon feature is located within its nominal 25 km projected square. **Maximum detected outside-square deviation: 0 m**.
- All 92 zones have the same expected shape-count pattern, including the 80°–82° intentional difference.

## Acceptance criteria met

- [x] Official source archive verified against pinned SHA-256.
- [x] All 381 projection files parsed, zero errors.
- [x] WKT sphere, LTM/LPS methods, central-meridian numbering and projection constants compared.
- [x] All 92 zone-border source polylines compared at vertices against candidate analytic equations.
- [x] All source 25 km polygon features checked for containment in one integer-indexed projected 25 km square.
- [x] Distinct 25 km tile inventory across all 92 zones calculated and checked against Revision 21 estimate.
- [x] USGS 82° vs. Lunar Dig 80° discrepancy identified as an *intentional policy cut*, not a coordinate parameter mismatch.

## Remaining work (not passed)

- [ ] **1 m edge-walk of every cut 1 km parcel in every zone**, including whole/in-zone bit agreement. Sampling the 25 km polygon vertices is *not* a substitute for this.
- [ ] Independent continuous-border Hausdorff comparison, or equivalent certified maximum deviation between the discretized USGS polylines and analytic curves, as opposed to vertex residuals alone.
- [ ] Complete number of whole and partial **1 km** parcels by zone and zone edge (expected ~37.7 million whole and ~1.2% partial).
- [ ] Explicit comparison of **25 km line intersections** across every whole polygon and LGRS-0.4.0 transformations, not just zone borders and nominal tile-square containment.
- [ ] Publishing the fixed, reproducible global 1 km mask once those checks pass.

**Conclusion:** Revision 21's projection constants, numbering, 80° cut interpretation, and 25 km tile inventory are supported by authoritative USGS geometries. This does not yet certify the parcel-level property boundaries.
