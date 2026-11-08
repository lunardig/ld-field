"""Rev21 source-raster reduction primitives (not a validated NASA/USGS field).

No network access or implicit source selection. Input rasters MUST have their
coordinate reference system and file hashes recorded by the calling pipeline.
All raster sampling is on source pixel centers; pixel boundary ties belong to
the grid cell with larger easting/northing. Requires rasterio, numpy, pyproj.

This is a building block, NOT the complete source-specific production runner.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import ceil, floor, isfinite
from pathlib import Path
from typing import Callable
import hashlib
import json


def file_sha256(path, block_size=1024*1024):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        while block:=stream.read(block_size):
            h.update(block)
    return h.hexdigest()


def round_even(value, scale, *, low=0, high=65534):
    """Store fixed-unit integer: half-to-even; sentinel 65535 is reserved."""
    if not isfinite(value):raise ValueError('nonfinite raster value')
    result=round(value/scale)
    if not low<=result<=high:raise OverflowError(f'field {value} / {scale} outside [{low},{high}]')
    return int(result)


def source_cell_summary(dataset, bounds_m, *, project_xy=None, reduction='mean',
                        minimum_count=1, valid=None):
    """Aggregate raster values whose pixel centers fall in projected square.

    Dataset must be an open rasterio single-band dataset, with a valid CRS.
    `project_xy` transforms (source_x, source_y) into the target LGRS metre
    coordinates; when omitted the source CRS is already the target CRS.
    Uses a source window covering the projected square's preimage as selected
    by the caller; this function currently requires pre-projected rasters.

    The exact center-on-boundary convention is implemented as
    min <= center < max in both axes. No-data and invalid pixels omitted.
    """
    if project_xy is not None:
        raise NotImplementedError('reproject source onto pinned LGRS CRS first; no silent approximate reprojection')
    if dataset.crs is None:raise ValueError('source raster CRS required')
    from rasterio.windows import from_bounds, Window
    import numpy as np
    xmin,ymin,xmax,ymax=bounds_m
    if xmin>=xmax or ymin>=ymax:raise ValueError('empty bounds')
    w=from_bounds(xmin,ymin,xmax,ymax,transform=dataset.transform)
    col0=max(0,int(floor(w.col_off))-2);row0=max(0,int(floor(w.row_off))-2)
    col1=min(dataset.width,int(ceil(w.col_off+w.width))+2)
    row1=min(dataset.height,int(ceil(w.row_off+w.height))+2)
    if col1<=col0 or row1<=row0:return None,0
    window=Window(col0,row0,col1-col0,row1-row0)
    array=dataset.read(1,window=window,masked=True)
    affine=dataset.window_transform(window)
    yy,xx=np.indices(array.shape)
    sx=affine.a*(xx+.5)+affine.b*(yy+.5)+affine.c
    sy=affine.d*(xx+.5)+affine.e*(yy+.5)+affine.f
    inclusion=(sx>=xmin)&(sx<xmax)&(sy>=ymin)&(sy<ymax)
    inclusion &= ~np.ma.getmaskarray(array)
    vals=np.asarray(array)[inclusion]
    if valid is not None:vals=vals[valid(vals)]
    vals=vals[np.isfinite(vals)]
    count=int(vals.size)
    if count<minimum_count:return None,count
    if reduction=='mean':return float(np.mean(vals,dtype=np.float64)),count
    if reduction=='median':return float(np.median(vals)),count
    if reduction=='max':return float(np.max(vals)),count
    if reduction=='fraction':return float(np.mean(vals!=0)),count
    raise ValueError('unsupported reduction')


def horn_slope(dem, dx_m, dy_m):
    """Slope degrees for 3x3 elevations; missing samples return None.

    Horn weights [-1,0,1] by rows. Grid spacing MUST be actual local ground
    spacing in metres; source-grid geographic pixel spacing is *not* dx_m.
    """
    import math
    if len(dem)!=3 or any(len(row)!=3 for row in dem):raise ValueError('expected 3x3')
    if dx_m<=0 or dy_m<=0:raise ValueError('ground spacing')
    if any(v is None or not math.isfinite(v) for row in dem for v in row):
        return None
    dzdx=((dem[0][2]+2*dem[1][2]+dem[2][2])-
          (dem[0][0]+2*dem[1][0]+dem[2][0]))/(8*dx_m)
    dzdy=((dem[2][0]+2*dem[2][1]+dem[2][2])-
          (dem[0][0]+2*dem[0][1]+dem[0][2]))/(8*dy_m)
    return math.degrees(math.atan(math.hypot(dzdx,dzdy)))


def assemble_tile_layers(index, e, n, whole, inside, *,
                         elevation=None, slope=None, usable=None,
                         shadow=None, sunlight=None, tio2=None, tio2_error=None,
                         coarse=None):
    """Encode arrays already reduced to 625 cells, preserving no-data.

    Each source input is a sequence of 625 float physical values or None;
    a complete driver must populate them from vetted source rasters.
    Ice is not modeled here. Placeholder synthetic values are NEVER inserted.
    """
    from .field import Tile, NODATA, CELLS
    inputs=(elevation,slope,shadow,sunlight,tio2,tio2_error,usable)
    scales=(1.,.01,.0001,.0001,.01,.01,.0001)
    defaults=(-32768,)+(NODATA,)*6
    layers=[]
    for k,seq in enumerate(inputs):
        if seq is not None and len(seq)!=CELLS:raise ValueError('layer size')
        result=[]
        for i in range(CELLS):
            inside_cell=bool(inside[i>>3]&(1<<(i&7)))
            value=seq[i] if seq is not None else None
            if not inside_cell or value is None:
                result.append(defaults[k]);continue
            low=-32767 if k==0 else 0
            high=32767 if k==0 else 65534
            result.append(round_even(value,scales[k],low=low,high=high))
        layers.append(tuple(result))
    coarse=tuple(coarse) if coarse is not None else (NODATA,)*6
    return Tile(index,e,n,whole,inside,coarse,tuple(layers))


def write_provenance(source_spec, output_file):
    """Record, without guessing, the source files and their exact hashes."""
    records=[]
    for entry in source_spec:
        path=Path(entry['path'])
        if not path.is_file():raise FileNotFoundError(path)
        for required in ('product','version','url','license'):
            if not entry.get(required):raise ValueError(f'{required} missing for {path}')
        records.append({**entry,'sha256':file_sha256(path)})
    Path(output_file).write_text(json.dumps({'inputs':records},indent=2,sort_keys=True)+'\n')
    return records
