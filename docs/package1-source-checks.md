# Package 1 — Source-check register (Revision 21)

**Date:** 2026-11-08  
**Status:** In progress — **not** a completed Package 1 acceptance report.  
**Scope:** USGS/NASA product metadata and provenance checks required before publishing a scientific lunar survey. The synthetic prototype is independent of these products.

## 1. LGRS reference parameters

Revision 21's candidate parameters:

| Parameter | LTM | LPS |
| --- | --- | --- |
| Spherical radius | 1,737,400 m | 1,737,400 m |
| Central scale `k0` | 0.999 | 0.994 |
| False easting | 250,000 m | 500,000 m |
| False northing | 0 m (north), 2,500,000 m (south) | 500,000 m |
| Coverage | 45 longitude strips, each 8°, split by equator | poleward of 80° |

USGS primary report: https://pubs.usgs.gov/publication/tm11E1  
USGS GIS product release: https://data.usgs.gov/datacatalog/data/USGS:667b1061d34e6151c9d6bcc7  
Candidate Python library: https://github.com/rbeyer/lgrs

**Status:** The numerical parameters have been reviewed against the published report in the earlier design discussion. The official zone-numbering rule is confirmed from the USGS reference conversion code: LTM zone 1 has central meridian 176°W, zone 23 is 0°, zone 45 is 176°E; the formula is -176° + 8° × (zone - 1). The required *direct* `.prj` WKT extraction, 25 km grid origin, and <1 m shapefile comparison **have not yet been performed**. Therefore, `src/grid.py` is a candidate implementation, not an approved cadastral grid. The zone-number mapping is now implemented in `src/enumerate_grid.py`; the underlying WKT and boundary geometry remain provisional.

Validation needed:
1. Acquire and SHA-256 the official release archive and all source `.prj` files.
2. Tabulate WKT projection method, origin, central meridian, false origins, radius, scale factor, hemisphere, zone numbering and cut rules; compare independently with library `lgrs` pinned to 0.4.0.
3. Compare inverse-projected 25 km borders to authoritative USGS geometries in their common CRS, flagging differences over 1 m.
4. Classify all cut 1 km squares using the rev21 analytical algorithm, and independently sample each at <=1 m edge intervals, reporting mismatches and partial-area totals.
5. Do not derive global 25 km/1 km parcel counts from an area estimate; publish enumerated counts.

## 2. TiO₂ / FeO products and uncertainties

### LROC WAC TiO₂

Product description: https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LROC/SDR/SDWTIO.htm

Metadata indicates approximate 400 m/pixel map sampling at the equator over approximately 70°N–70°S. Estimates are based on ultraviolet reflectance, primarily intended for maria. Reported values at the low end are thresholded and artifacts are noted in some regions, especially high latitude.

**Status:** No supported universal per-pixel 1σ uncertainty or quantitative effective inter-pixel correlation length has been established from this product description. Leave the corresponding error layer **no-data** until primary documentation resolves it. The nominal pixel spacing must not be used as independent measurement precision. Geographic mare masking still requires the pinned Unified Geologic Map of the Moon.

### Lunar Prospector GRS

PDS product label: https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_2deg.lbl

The label references oxide fields including `W_FEO` and `W_TIO2`; their uncertainties are described via error-matrix terms. **Do not** apply elemental Fe/Ti conversion factors to oxide fields that are already oxides. Extract the actual declared column names, matrix order, units, flags, nodata, spatial pixel grid, longitude conventions and uncertainty conversion from the file label and data dictionaries. Confirm apparent inconsistent 2°/5° wording against the actual grid.

**Status:** Exact error matrix extraction and numerical 1σ derivation remain open. No values are manufactured for this report.

## 3. Redistribution checks

| Product | Source | Known status | Required action |
| --- | --- | --- | --- |
| USGS LGRS rasters/shapefiles | [USGS release](https://data.usgs.gov/datacatalog/data/USGS:667b1061d34e6151c9d6bcc7) | Public domain **per the supplied brief** | Verify exact product notice/attribution and preserve citation |
| USGS lunar grid technical report | [USGS](https://pubs.usgs.gov/publication/tm11E1) | Not independently examined for image or third-party rights | Cite and inspect notices before redistributing embedded figures |
| SLDEM2015 | [NASA PGDA](https://pgda.gsfc.nasa.gov/products/54) | Not yet cleared | Find product-specific provenance/redistribution terms |
| LOLA DEMs | [ODE](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRDEM.htm) | Not yet cleared | Record applicable NASA/PDS notices and attribution |
| PGDA illumination and shadow | [NASA PGDA](https://pgda.gsfc.nasa.gov/products/69) | Not yet cleared | Identify original providers and data use notices |
| LROC WAC TiO₂ | [ODE](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LROC/SDR/SDWTIO.htm) | Not yet cleared | Verify applicable LROC and NASA product reuse notices |
| Lunar Prospector GRS | [PDS](https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_2deg.lbl) | Not yet cleared | Verify data archive and third-party reuse requirements |
| Unified Geologic Map of the Moon | [USGS publication](https://pubs.usgs.gov/publication/sim3316) | Version 2.0 USGS release states CC0/public domain; citation requested | Pin exact GIS download SHA-256; preserve recommended attribution |

**Release gate:** No real-data derivative tiles may be published until this matrix is resolved with exact terms, links and any required attribution.

## 4. Implementation status / acceptance gates

- [x] Deterministic format-1 8,946-byte synthetic tile writer and reader.
- [x] Merkle index, tree and proof primitives; prototype unit tests.
- [x] Candidate LTM/LPS square classifier with independent edge-walk test helper.\n- [x] Zone numbering confirmed from the published USGS conversion reference code.\n- [x] Provisional per-zone 25 km tile and 1 km square inventory tool (`python -m src.enumerate_grid`).\n- [x] WKT and PDS3 source-inspection command (`python -m src.inspect_sources`).\n- [x] Preliminary raster summarization, Horn slope, source-hashing and fixed-unit packing helpers (`src/raster_pipeline.py`).
- [x] GitHub Actions test workflow.
- [ ] Authoritative WKT/zone-numbering/USGS border verification.
- [ ] Exhaustive Moon-wide grid and 1 m edge-walk checks.
- [ ] Complete product-specific scientific error model and **source-specific production raster ingestion**; generic reduction primitives have been implemented.
- [ ] Resolved source-specific redistribution conditions.
- [ ] Versioned real field with full provenance manifest, immutable folders and externally pinned trust anchors.
- [ ] Cross-language test against actual SDK `vendor/ld-interfaces/tools/ld.py`.

Do not mark Package 1 complete or `field_root` scientific until the three required source-check categories are verified.
