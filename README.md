# Lunar Dig Public Field — Revision 21 development

This repository implements the **public expected survey** of the Moon for Lunar Dig, independent of private parcel endowments. The Site Field and Map — Developer Brief, revision 21 is the controlling implementation brief (supplied by the project owner; not yet committed here in full).

**Current status: synthetic prototype and candidate geometry — not a completed lunar survey.** In particular, projected-grid geometry has not passed the USGS WKT/shapefile match and global 1 m edge-walk acceptance gates.

## Working components

- `src/field.py`: deterministic 8,946-byte format-1 tiles, index, Merkle tree, proofs and synthetic samples.
- `src/grid.py`: independent spherical candidate LTM/LPS 1 km cell classification and an edge-walk diagnostic.
- `generate_demo.py`: five deliberately synthetic tiles and a separately saved verification anchor.
- `tests/`: prototype tile verification and geometry regression tests.
- `.github/workflows/test.yml`: GitHub Actions checks on pushes and pull requests.
- `docs/package1-source-checks.md`: primary-source review register, confirmed metadata and unresolved publication gates.
- `docs/developer-brief-review.md`: **historical** review of an earlier brief; revision 21 supersedes it.

## Run

```bash
python -m unittest discover -s tests -v
python generate_demo.py
```

Generated `demo-field/` and `trust-anchor-demo.json` are not committed. They are synthetic-only fixtures and must never be presented as measured lunar composition.

## Next acceptance gates

1. Package 1: USGS `.prj` extraction, official zone numbering and 25 km boundary comparison, verified source uncertainty and redistribution terms.
2. Package 2: full globe grid classification with exhaustive cut-edge walk, real raster ingestion, reproducible source hashes, and immutable versioned field folders.
3. Package 3 (separate `ld-sdk` repository): plain JS browser viewer, external trust anchors, index and proof verification, global and both polar views.
4. Cross-check the hash contract against the SDK release's `ld.py` and JavaScript before production use.

World genesis pins its first field version. Later signed records in public root history activate new fields; **older field folders are retained for audit**. The browser viewer verifies externally pinned `field_root` and `index_hash` but is not responsible for verifying governance signatures.
