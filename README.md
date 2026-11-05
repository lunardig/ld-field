# Lunar Dig Public Field — Prototype

Python implementation of the format-1 8,946-byte survey tile encoder/decoder and Merkle packer. **Synthetic test data only — not a NASA/USGS-derived lunar survey.**

## Run

```bash
python -m unittest discover -s tests -v
python generate_demo.py
```

The second command creates `demo-field/` and `trust-anchor-demo.json` locally. These generated test artifacts are intentionally not committed.

## Status

This repository currently contains the prototype encoder, deterministic fixture generator, and tests. It does **not** yet contain the full Moon LGRS grid generator, NASA/USGS raster ingestion, scientific source error analysis, completed redistribution check, or production lunar survey data.

The companion HTML map prototype and developer source review are included in the separate delivery archive, not this repository.

The Python `H()` hashing contract was implemented independently from the specified format; cross-check against `ld.py` from the SDK release before production use.
