# Developer brief review — Site Field and Map

**Reviewed:** 2026-11-05  
**Source:** *Site Field and Map — Developer Brief* (2026-11-05)  
**Status:** Design review; not a completed scientific or legal audit  
**Scope:** Three delivery packages: (1) source checks, (2) public field pipeline, (3) static SDK map.

## Executive assessment

The brief offers a useful implementation contract and appropriately separates **public expected resource fields** from **actual private parcel endowments**. The format-1 tile layout, externally pinned trust anchors, and map acceptance tests are strong foundations.

Do **not** certify the field as an authoritative Moon-wide survey until grid edge geometry, primary-source semantics and redistribution conditions, scientific uncertainties, and end-to-end verification are resolved. The existing repository implementation is a **synthetic prototype**, not actual NASA/USGS lunar data.

## Blocking or high-priority findings

| ID | Priority | Finding | Required action |
| --- | --- | --- | --- |
| BR-01 | Critical | Testing four projected-square corners and four edge midpoints is not, by itself, a mathematical proof that the *entire* square is within a latitude/longitude zone. | Implement a validated boundary-intersection or conservative containment procedure, including curved projected zone boundaries and exact-boundary cases. |
| BR-02 | Critical | Checking a tile against a host-supplied `field_root` or `index_hash` alone is not authentic verification. | Obtain and pin **both** hashes from an independent world manifest or separately trusted value; verify the index before accepting its leaf ordering. |
| BR-03 | High | Mixed observed, modeled, inferred, and default field values lack per-cell provenance in the binary format. | Define provenance and quality semantics in versioned metadata or a future format revision; display defaults distinctly from measurements. |
| BR-04 | High | A nominal 400 m TiO₂ map pixel is not necessarily an independent 400 m ground-truth estimate; averaging it into 1 km parcels does not create independent parcel-scale measurement accuracy. | Document instrument/product validity, spatial correlation, masking, and error interpretation; avoid false precision. |
| BR-05 | High | Odd-node *promotion unchanged* is unusual and must be consistently reproduced across Python and JS. | Specify and test proof length and sibling omission at every level; reject missing, extra, wrong-index, or inconsistent proofs. |
| BR-06 | Medium | Projected 25 km tiles can straddle geographic zone boundaries. | Keep legal whole-square classification distinct from in-zone coverage and from synthetic or sampled raster cells. |
| BR-07 | Medium | `labels.bin` and overviews are expressly not Merkle-authenticated. | Treat them as display-only. Derive authoritative parcel key and verified measurements from verified tile/index content. |
| BR-08 | High | World manifest and pipeline reproducibility claims require more than version labels. | Freeze source checksums, processing parameters, software/dependency versions, environment and output serialization; rerun and compare `field_root`. |

## Package 1 — Source checks

### LGRS

The brief defines 45 LTM strips in each hemisphere, two polar stereographic zones, a reference sphere radius of 1,737,400 m, and the following projection parameters:

| Parameter | LTM | LPS |
| --- | --- | --- |
| Central scale factor | 0.999 | 0.994 |
| False easting | 250,000 m | 500,000 m |
| False northing | 0 m north; 2,500,000 m south | 500,000 m |
| Transition | LTM to 80° latitude | Poleward of 80° |

A prior review compared these numerical constants with the USGS lunar grid publication and found no discrepancy at the parameter level. **That does not verify** the complete projection code, geodetic coordinate conventions, zone numbering, grid origins, cell clipping, or 1 m shapefile comparison. Perform the brief's requested direct WKT and shapefile checks and retain evidence for each.

Primary reference: https://pubs.usgs.gov/publication/tm11E1  
USGS release: https://data.usgs.gov/datacatalog/data/USGS:667b1061d34e6151c9d6bcc7

### TiO₂ / FeO uncertainty and product meaning

The LROC WAC TiO₂ map is a remote-sensing estimate, mainly appropriate for mare terrains. The source documentation does not establish a single universal, validated per-pixel 1σ value for the whole product; do **not** fabricate one.

The Lunar Prospector GRS product labels and format must be examined directly before applying Fe-to-FeO and Ti-to-TiO₂ conversion. A product containing oxides or error-matrix values must not be treated as raw elemental abundances without checking its actual declared fields. Confirm the apparent disagreement between the GRS label filename (`2deg`) and the grid dimensions/metadata.

Sources:  
- https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LROC/SDR/SDWTIO.htm  
- https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_2deg.lbl

### Redistribution

The USGS LGRS release is identified as public domain in the brief. **No redistribution clearance for the other listed products was established in this review.** Package 1 must record product-specific terms, allowed transformation/redistribution, attribution, and links before releasing derived data.

## Package 2 — Public field pipeline

The proposed format-1 tile is exactly **8,946 bytes** with a fixed 24-byte header, 12-byte coarse block, 79-byte whole bitmap, 79-byte in-zone bitmap, padding bytes, and seven signed/unsigned 16-bit × 625-cell layers. Preserve the brief's byte layout for compatibility.

Implement checks for: exact length, magic/version, valid zone and key, zero reserved/padding bytes, consistent bitmap population count, whole subset of in-zone, no out-of-zone non-no-data values, and correct signed elevation interpretation.

Merkle rules: tile leaves hash stored uncompressed bytes; nodes hash the prescribed exact canonical JSON bytes; sorted tile order is zone/easting/northing; odd trailing nodes are carried up unchanged. Independently validate an index against an externally pinned `index_hash`, then verify proofs against an independently pinned `field_root`.

**Current implementation status:** Repository code contains a deterministic, synthetic test generator and basic encoder, Merkle packer, and unit tests. It does not yet enumerate the Moon's actual zones or produce a scientific field from NASA/USGS rasters.

Scientific processing concerns requiring separate confirmation:
- Slope from a uniform-resolution DEM is a meaningful choice, but define source grid alignment, nodata, pixel-scale conventions, 3×3 edge treatment, and the projected-cell summarization method.
- A center-in-square pixel rule can bias border summaries; document it and check area-weighted alternatives for coarse maps.
- Model defaults such as 0.5 illuminated fraction outside PGDA coverage must remain explicitly labeled **model defaults**.
- The site's best available sunlight fraction must not be misrepresented as parcel-average illumination or a complete temporal illumination schedule.
- Overviews and `labels.bin` are not authenticated; avoid giving them authoritative status.

## Package 3 — SDK map

The sample should remain a static HTML/JS demonstrator with no required `ldcp` or engine binary, capable of loading only needed tiles on slow connections. Keep both polar views because a global equirectangular presentation hides polar geometry.

The acceptance fixtures must reject:
1. A one-byte-modified tile.
2. A Merkle proof for the wrong leaf index.
3. A truncated or extra-length proof.
4. A data-host manifest that disagrees with pinned trust anchors.
5. An index with a mismatched external `index_hash`.

Make source status and uncertainty visible. A displayed approximate ilmenite grade (`1.9 × TiO₂`) is an interpretation, not a directly measured deposit or a filed endowment.

## Suggested completion gates

- **Gate P1:** Exact WKT parameter evidence, zone numbering and 80° transition; TiO₂/GRS uncertainty semantics; complete source redistribution matrix.
- **Gate P2a:** Validated zone geometry and 25 km / 1 km mapping; measured per-zone and per-boundary rejected-area counts; border comparison within stated tolerance.
- **Gate P2b:** Product-specific raster import and provenance, repeatable environment/source manifest, independent cross-language hashing, production-ready tile/index/proof fixtures.
- **Gate P3:** Responsive static map, world-manifest-pinned roots, passing corruption/incorrect-proof fixtures, explicit synthetic/observed/model-data labeling.

## Additional architecture note

The property registry, execution holding, and public resource field are distinct systems. Nothing in the map pipeline should derive information from unrevealed actual parcel endowments or treat a survey estimate as an awarded property right. Cadastral boundaries and field versions should be immutable **per world**, even if later worlds use improved scientific source maps.

**Disposition:** Proceed with the synthetic implementation and source checks. Do not label its output a verified Moon-wide survey or finalize immutable cadastral titles until the gates above pass.
