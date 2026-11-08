# Site Field and Map — Developer Brief

Nov 5, 2026 · @Guy Stewart

Build the public map data for the Moon, and a map to view it, in three packages. Start with Package 1: three checks that everything else depends on.

## The work

Lunar Dig is dividing the Moon into 1 km mining parcels on the USGS Lunar Grid Reference System (LGRS). Each parcel needs public data on its terrain, light and likely composition, and players need a map to read it.

| Package | Delivers | Can start |
| --- | --- | --- |
| 1. Source checks | A short written report on three questions | Now |
| 2. Public field pipeline | Code in a new repository, and a first field of tiles | Grid work after Package 1; other layers as each check clears |
| 3. Map sample | A static page in `ld-sdk/examples/map/` | Now, on synthetic tiles |

The field is public data derived from NASA and USGS sources. It is a low-quality survey by design: it says what a parcel is *expected* to hold, with stated uncertainty. A parcel's actual composition is held separately and is not part of this brief.

## Getting started

- **Work from the release archive,** as in the SDK test. You need `0.1.0-alpha.6` or later: `alpha.5` lacks `examples/controllers`. Neither package needs the engine binaries.
- **Hashing.** `vendor/ld-interfaces/tools/ld.py` in the archive has `domain_hash`, `hash_value` and `canonical_bytes`. The map is JavaScript, so the bytes are spelled out under *Tile format*.
- **Sample style.** `examples/controllers` shows the expected style: plain HTML and JavaScript. The map must not depend on the `ldcp` client, which needs a build.
- **Pipeline repository.** Package 2 lives in the public repository [`lunardig/ld-field`](https://github.com/lunardig/ld-field).
- **Where things go.** Package 1 goes to the project owner as a report. Package 2 goes to `ld-field`. Package 3 goes to `ld-sdk` as a pull request from a fork, which is the only time you need a clone of it.
- **Questions.** Send anything this brief does not settle to the project owner. Record each one, as you did in the SDK test: it is a finding against this brief.

## Fixed decisions

These are settled. If one looks wrong, raise it instead of working around it.

1. **One projection per point.** LPS poleward of 80°, LTM elsewhere. The extended LTM range to 82° is not used, because it would give one place two addresses.
2. **The parcel key is projected.** `(zone, easting_km, northing_km)` at the square's corner of minimum easting and minimum northing. LGRS letters are for display only, because a band line can cross a square and give it two names.
3. **Zones are written** `ltm-1-n` to `ltm-45-n`, `ltm-1-s` to `ltm-45-s`, `lps-n` and `lps-s`. Check the numbering against `lgrs` in Package 1.
4. **A square is whole** when its open interior lies within the zone's latitude and longitude box. Touching a boundary does not cut it, so the equator cuts nothing. Use the default boundaries in `lgrs`, which follow latitude and longitude exactly. The pipeline sets the whole and in-zone bits by the tests under *Edge tests*, and the result is data: readers don't recompute it. Partial squares are shown on the map but cannot be claimed.
5. **Squares nest.** The 1 km grid sits exactly in the 25 km grid, so every parcel belongs to one 25 km tile.

The constants below come from `lgrs` 0.4.0 and have **not** been confirmed against the USGS publication. Package 1 settles them.

| Constant | LTM | LPS |
| --- | --- | --- |
| Radius | 1,737,400 m | 1,737,400 m |
| Scale factor k₀ | 0.999 | 0.994 |
| False easting | 250,000 m | 500,000 m |
| False northing | 0 m north, 2,500,000 m south | 500,000 m |
| Zone width | 8° of longitude | Poleward of 80° |

## Package 1: source checks

Deliver one short report answering these three questions. Quote each value with where you found it.

| Check | Question | Done when |
| --- | --- | --- |
| LGRS constants | Do the `.prj` files in the USGS release match the table above, and do the 25 km grid origin and the 80° cut match `lgrs`? | Each value is confirmed or corrected, from the WKT parameters, and zone numbering is stated |
| TiO₂ and Fe errors | What is the stated error of the LROC WAC TiO₂ map: per pixel, or one figure for the whole map? Is it valid outside the mare, and at what latitudes? Does the source state an effective resolution, or how errors correlate between pixels? What are the Lunar Prospector error terms, and does its product report elements or oxides? | A 1σ figure or method for each layer, or a statement that the source gives none |
| Redistribution | May we publish derived data from each source in Package 2's list? | For each source: terms, a link, and any attribution required |

The project has confirmed public-domain terms only for the USGS LGRS release. Everything else is open.

## Package 2: public field pipeline

Turn the sources into a versioned field of tiles, from one recorded run. The pipeline reads only the sources listed in `field.json` and uses no random numbers. Floating point is fine in the recorded environment, because the output is integers fixed by hash.

**Order of work:**

1. Compute the grid: every 25 km tile, every 1 km square, whole or partial.
2. Build terrain and light.
3. Build TiO₂ and the coarse layers, once Package 1 clears them.
4. Package the tiles, index, tree, overviews and manifest.

| Layer | Scale | Source | Summary rule |
| --- | --- | --- | --- |
| Elevation | 1 km | SLDEM2015 512 ppd within ±60°; LOLA `LDEM_60N_60M` and `LDEM_60S_60M` poleward | Mean of the source cells centred in the square, height above the 1,737,400 m sphere |
| Slope | 1 km | The same grids | Median |
| Usable ground | 1 km | The same grids | Fraction of the square's cells with slope ≤ 15° |
| Cold-trap fraction | 1 km | PGDA permanent shadow, poleward of 65° | Fraction of the square in permanent shadow |
| Best sunlit fraction | 1 km | PGDA illumination, poleward of 65° | **Highest value in the square, not the mean** |
| TiO₂ | 1 km, mare only | LROC WAC 400 m | Mean |
| TiO₂ error | 1 km, mare only | From Package 1 | Mean |
| FeO, TiO₂, with errors | 25 km | Lunar Prospector GRS 2° | Area-weighted mean of the pixels overlapping the tile |

**Slope is defined once:** Horn's 3 × 3 gradient, in degrees, on the source grid before summarizing. All slope comes from one \~60 m grid, so values compare across latitudes. Do not use the finer polar DEMs, whose slope would mean something else. Do not use the 118 m global DEM, which interpolates across track gaps. Use each cell's true ground spacing from the grid's own projection: east-west spacing on a cylindrical grid shrinks with latitude. Compute across file joins, and on each source grid before merging at ±60°. A cell missing any of its 3 × 3 neighbours has no slope.

**Elevation, slope and usable ground are provisional.** A domain expert is reviewing them, including the 15° threshold. Keep each rule in one place, so that it is a one-line change.

**Other rules:**

- **Light.** For PGDA, use the finest map covering the square's centre: 240 m from 65°, 120 m from 75°, 60 m from 85°. Read full-resolution files, because the overviews in its Cloud-Optimized GeoTIFFs are averaged.
- **Modelled defaults.** Equatorward of 65°, judged at the square's centre, cold-trap fraction is 0 and best sunlit fraction is 0.5. These are defaults, not measurements.
- Best sunlit fraction takes the highest value because a player puts arrays on the best spot. A mean would make a ridge look like a plain. It is one spot's figure, not a parcel average and not a schedule.
- **Mare.** A square is mare when at least half its area falls in mare units of the USGS Unified Geologic Map of the Moon, version pinned in `field.json`. Elsewhere TiO₂ is no data. Tell us if Package 1 finds a better mask.
- **Oxides.** If the GRS product reports elements, convert with FeO = 1.2865 × Fe and TiO₂ = 1.6685 × Ti.
- **Partial squares.** Summarize the square's whole footprint, since the ground is real either way.
- **Source cells.** A 1 km summary uses the source cells whose centres fall in the square. A centre on a grid line belongs to the square of greater easting or northing. Source no-data cells are left out, and a square with none left is no data. Report the lowest cell count per layer: a 400 m source gives a square only about six cells.
- **Error under averaging.** TiO₂ error is the mean of the source errors, with no reduction by the square root of the cell count, because neighbouring pixels aren't independent. A 400 m pixel is not an independent 400 m measurement, and 0.01 wt% is a storage unit, not a precision.
- **Rounding.** Scale to the layer's unit and round to nearest, ties to even. A value outside the type's range is a pipeline failure.
- **Edge tests.** On the sphere, with x′ and y′ the projected distances from the central meridian and the equator, each divided by R·k₀: sin φ = sin y′ / cosh x′, and tan λ = sinh x′ / cos y′. Within one hemisphere and one side of the central meridian, moving away from the meridian lowers φ and raises λ, and moving poleward raises both. So φ and λ each take their extremes at corners, and an LTM square is whole exactly when its four corners are in the box. No square straddles the central meridian or the equator, because the false origins are whole kilometres; tell us if Package 1 changes that. The LPS zone is a disc, which is convex, so the corners decide there too. For the in-zone bit, moving equatorward lowers both φ and λ, so an LTM square has ground in the zone exactly when its equatorward edge does. Along that edge the two limits bound x from opposite sides, so bisect for each limit and compare. An LPS square has ground in the zone exactly when its point nearest the pole does.
- Light phase is computed from longitude, so it isn't stored.

**Done when:**

- Zone borders and 25 km grid lines match the USGS shapefiles to within 1 m, in one projection, with any differences explained.
- The whole and in-zone bits match a 1 m walk of the edges of every cut square, in every zone.
- Counts are reported, per zone edge and in `field.json`. Expect about 68,900 tiles (754 per LTM zone, 516 per pole), 37.7 million whole squares and 1.2 % partial.
- A re-run in the recorded environment reproduces the same `field_root`. A difference of one bit fails.
- Every source's product, version, download location and file SHA-256 is in `field.json`, with the processing parameters and locked dependency versions.
- One LTM tile and one LPS tile build on a laptop within an hour.
- Packages 2 and 3 share one synthetic-field generator, so that the format is tested once.

## Tile format

A tile is one 25 km square as a fixed 8,946-byte file, so the map can fetch a screen of 20 for about 180 KB. All integers are little-endian. This is format 1, and it is **not frozen** until Package 1 and the domain review finish: if the WAC error proves to be one map-wide figure, it moves to the coarse block, usable ground takes layer 5, and the tile shrinks to 7,696 bytes.

| Offset | Bytes | Field |
| --- | --- | --- |
| 0 | 4 | Magic, ASCII `LDFT` |
| 4 | 2 | Format, u16, 1 |
| 6 | 2 | Zone index, u16 |
| 8 | 2 | `tile_e`, u16: floor(easting\_km ÷ 25) |
| 10 | 2 | `tile_n`, u16: floor(northing\_km ÷ 25) |
| 12 | 2 | Count of whole squares, u16 |
| 14 | 10 | Reserved, 0 |
| 24 | 12 | Coarse block: six u16, below |
| 36 | 79 | Whole bitmap, 625 bits |
| 115 | 1 | Padding, 0 |
| 116 | 79 | In-zone bitmap, 625 bits: set when any of the square's ground lies in the zone |
| 195 | 1 | Padding, 0 |
| 196 | 8,750 | Seven layers of 625 cells, each 2 bytes, in the order below |

**Zone index:** `ltm-1-n` to `ltm-45-n` are 0 to 44, `ltm-1-s` to `ltm-45-s` are 45 to 89, `lps-n` is 90 and `lps-s` is 91.

**Cell index:** i = (easting\_km mod 25) + 25 × (northing\_km mod 25), so cell 0 is the corner of minimum easting and northing. Bit i is bit (i & 7) of bitmap byte (i >> 3), least significant first.

| Layer | Type | Unit | No data |
| --- | --- | --- | --- |
| 0 Elevation | i16 | 1 m | −32,768 |
| 1 Slope, median | u16 | 0.01° | 65,535 |
| 2 Cold-trap fraction | u16 | 0.0001 | 65,535 |
| 3 Best sunlit fraction | u16 | 0.0001 | 65,535 |
| 4 TiO₂, mare | u16 | 0.01 wt% | 65,535 |
| 5 TiO₂ error, 1σ | u16 | 0.01 wt% | 65,535 |
| 6 Usable ground | u16 | 0.0001 | 65,535 |

A reader treats a cell as outside the zone only by the in-zone bit, never by a no-data value. Every value in an out-of-zone cell is no data. TiO₂ outside the mare is no data, and a reader falls back to the coarse block.

**Coarse block,** in this order, all u16 in 0.01 wt%, 65,535 for no data: FeO, FeO error, TiO₂, TiO₂ error, ice, ice error. Leave ice as no data: it is a modelled layer the project will supply.

**Reader checks.** Refuse a tile unless its length is exact, its magic and format are known, its zone index is below 92, reserved and padding bytes are 0, the whole count equals the bitmap's population count, the whole bitmap is a subset of the in-zone bitmap, every value in an out-of-zone cell is no data, and its key matches the index. Name the version when refusing. Any change to layout, layers, units, scales or no-data values is a new format number. A field holds one format. The meaning of every field in format 1 is fixed by this document, and `field.json`'s layer table is informative.

**Hashing.** All of this is in `ld.py`, and JavaScript must reproduce it exactly:

- `H(d, p)` = SHA-256 of UTF-8(d), then 0x00, then the length of p as a big-endian u64, then p. The result is 64 lowercase hex characters.
- Tile leaf: `H("ld.field.tile.v0", file_bytes)`, over the file as stored.
- Node: `H("ld.field.node.v0", ...)` over the exact bytes `{"left":"<64 hex>","right":"<64 hex>"}`. Uppercase hex gives a different node.
- Tiles are ordered by zone index, then `tile_e`, then `tile_n`. Tiles with no ground in the zone are absent.
- A level with an odd count carries its last node up unchanged. The top node is `field_root`.

**Locating a proof.** Check `index.bin` against the pinned `index_hash` before using it. `tile_count` is its length ÷ 6, and a tile's leaf index is its position in it. Find it by binary search on the key, and check that the key at that index equals the tile's header. Level sizes follow from `tile_count`, each the ceiling of half the level below, so a reader derives offsets into `tree.bin` and doesn't trust them. A proof holds one sibling for each level where the node has one, lowest first, and nothing where the node is carried up. Its length therefore follows from the leaf index and `tile_count`, and a shorter or longer proof is refused. A leaf index needs a u32: there are about 68,900 tiles and proofs have at most 17 hashes.

**Files,** all under a field-version folder, served with immutable caching:

| Path | Holds |
| --- | --- |
| `field.json` | Format, version, `field_root`, `index_hash`, `tile_count`, counts, layer table with each layer's basis (measured, derived or modelled default), sources with file SHA-256, processing parameters, pipeline commit, locked dependency versions, environment digest |
| `index.bin` | Tile keys in tree order, six bytes each: zone index, `tile_e`, `tile_n`, u16. `index_hash = H("ld.field.index.v0", file_bytes)` |
| `tiles/<zone>/<tile_e>-<tile_n>.ldft` | One tile. Gzip on the wire is fine, because the hash is over the uncompressed file |
| `tree.bin` | Every tree node as 32 raw bytes, level by level from the tiles up. Serve with `Accept-Ranges` and no content encoding, so that a proof can be fetched by range |
| `labels.bin` | Eight ASCII bytes per tile in index order, NUL-padded: the LGRS label of the tile's minimum corner. Display only and not hashed, because it depends on `lgrs` |
| `overview/` | 5 km and 25 km display data |

Overviews are not hashed either. Propose their format. Aggregate by mean, except best sunlit fraction, which takes the maximum.

The genesis manifest carries the first field version: its `field_root`, `index_hash`, sources, `ld-field` commit, environment digest and activation time. Each later version is a signed record with the same fields, chained to genesis in the world's public root history. `field.json` repeats them for convenience. The parcel grid is fixed for a world. The field may be reissued as sources improve, as a new version with a new root: that changes what the survey says, never what a parcel holds. Publish a new version when it activates, and keep every older version's folder published, because auditing a filed claim needs the tile it was filed against.

## Package 3: map sample

Build a static page in `ld-sdk/examples/map/` that reads tiles and verifies them against `field_root`. It has no engine behind it. It is a sample for other vendors to copy, so favour clear code over features.

Start from the synthetic-field generator shared with Package 2. The map then needs nothing else from Package 2 until real tiles exist.

**The root must come from outside the data host.** Take `field_root` and `index_hash` from values pinned in the page, or from `?root=` and `?index=` parameters copied from the active field version in the root history. Show which root is being checked. Treat `field.json`'s values as informative only: checking a host against itself proves nothing. The sample doesn't check the root history's signatures: whoever pins the values is responsible for that.

**It shows:**

- A global view and both polar views. An equirectangular map alone hides the poles, which is where much of the value is.
- Each layer as an overlay, one at a time, with its uncertainty where it has one.
- Whole and partial squares, with a count of unclaimable squares per zone edge.
- For a selected parcel: its address, built from the tile's label and the square's offsets, its parcel key, each value with its expected range, and how the value was derived.

It says *expected* throughout. These are survey values, not a parcel's actual contents. Multiply TiO₂ by 1.9 to show ilmenite, and label that as an estimate. Show modelled defaults differently from measurements, and label best sunlit fraction as the square's best spot. A synthetic field says so on the page. Ownership is not shown in the alpha.

**Done when:**

- It runs from a static server with no build step. `file://` won't work, because `fetch` and WebCrypto need a served page.
- It refuses and visibly flags each of these fixtures: a tile with one flipped byte, a proof for the wrong index, a truncated proof, an over-long proof, a `field.json` naming a different root, and an `index.bin` that fails the pinned `index_hash`.
- A screen of tiles loads over a slow connection without fetching the whole field.
- It works at phone width, in light and dark.
- A small test suite covers decoding and proof checking. JavaScript and `ld.py` must produce the same `field_root` for the synthetic field.

## Not in this brief

- **The survey table:** each parcel's actual composition. The project generates and holds it, in a separate module. No output of Package 2 may be derived from it.
- **Checking a revealed composition.** The map won't do this yet, because it needs the table's private leaf format.
- **The ice layer.** It is a model awaiting domain review, so leave it as no data.
- **Engine and catalog changes.** The field does not touch the engine, and neither package needs an amendment.
- **Filing and ownership.** These come later, with Omegeth.
- **Porting anything into `ld-web`.** The map stays an SDK sample.

## Sources

- [USGS TM 11-E1, Lunar grid systems](https://pubs.usgs.gov/publication/tm11E1) ([PDF](https://pubs.usgs.gov/tm/11/e1/tm11E1.pdf)). Its parameter tables are not in the PDF's text layer.
- [USGS LGRS Rasters and Shapefiles](https://data.usgs.gov/datacatalog/data/USGS:667b1061d34e6151c9d6bcc7), public domain
- [`lgrs` Python package](https://github.com/rbeyer/lgrs), Apache-2.0, pre-1.0 and changing
- [SLDEM2015](https://pgda.gsfc.nasa.gov/products/54)
- [LOLA gridded elevation](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRDEM.htm)
- [NASA PGDA lunar polar illumination](https://pgda.gsfc.nasa.gov/products/69)
- [LROC WAC TiO₂ map](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LROC/SDR/SDWTIO.htm)
- [Lunar Prospector GRS abundances](https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_2deg.lbl). The file is named 2°, but one reading of its label gave 5°, so confirm the pixel size.
- USGS Unified Geologic Map of the Moon, for the mare mask. Not yet opened by the project.
