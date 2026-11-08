"""Compare projected USGS 25 km zone geometry to Lunar Dig Revision 21.

The official USGS LTM zones extend to +/-82 degrees, while Lunar Dig uses
+/-80 degrees. This checker reports that deliberate difference separately
from numerical projection/grid alignment differences.

The report measures:
 * residuals of all vertices on official LTM/LPS zone boundaries against
   inverse spherical projection equations;
 * whether each official clipped 25 km polygon stays within exactly one
   projected 25 km square;
 * count of USGS reference polygons that fall entirely outside the game's
   narrower 80-degree LTM region.

It is NOT the exhaustive 1 m validation of every 1 km cut square.
"""
from __future__ import annotations
from collections import Counter
from io import BytesIO
from math import asin, atan2, cos, cosh, degrees, floor, hypot, pi, sin, sinh
from pathlib import Path
from zipfile import ZipFile
import argparse, json

from .grid import (
    Zone, classify_square, _relative_lat_lon, _polar_radius_m,
    LPS_FALSE_ORIGIN, RADIUS_M, LTM_K0,
)

DATA={
 'ltm-23-n':('LTM_global_23N_Grid','LGRS_25km_23N_Grid',Zone('ltm','n',0)),
 'ltm-23-s':('LTM_global_23S_Grid','LGRS_25km_23S_Grid',Zone('ltm','s',0)),
 'lps-n':('LPS_global_N_Grid','PolarLGRS_25km_N_Grid',Zone('lps','n')),
 'lps-s':('LPS_global_S_Grid','PolarLGRS_25km_S_Grid',Zone('lps','s')),
}

def _source_reader(archive, name):
 import shapefile
 entries=archive.namelist()
 paths=[p for p in entries if p.endswith('/'+name+'.shp') and '/PCRS_Zone_Specific/' in p]
 if len(paths)!=1:raise ValueError(f'{name}: expected one PCRS shapefile, got {len(paths)}')
 stem=paths[0][:-4]
 return shapefile.Reader(
  shp=BytesIO(archive.read(stem+'.shp')),
  shx=BytesIO(archive.read(stem+'.shx')),
  dbf=BytesIO(archive.read(stem+'.dbf'))),paths[0]

def _residual_m(zone, x, y):
 if zone.kind=='lps':
  return abs(hypot(x-LPS_FALSE_ORIGIN,y-LPS_FALSE_ORIGIN)-_polar_radius_m())
 lat, lon=_relative_lat_lon(zone,x,y)
 # On the USGS LTM reference boundary, one of these is zero:
 # equator, |latitude|=82deg, |longitude-central_meridian|=4deg.
 # Convert angular difference into an approximate local ground distance.
 return min(abs(lat)*pi/180*RADIUS_M,
            abs(abs(lat)-82)*pi/180*RADIUS_M,
            abs(abs(lon)-4)*pi/180*RADIUS_M*max(.00001,cos(lat*pi/180)))

def check(archive_path):
 report={'status':'SAMPLED_ZONES_NOT_GLOBAL_1M_VALIDATION',
         'limits':['Only LTM zone 23 N/S and polar N/S inspected',
                   'USGS LTM reference zone extends to +/-82 degrees; project restricts it to +/-80',
                   'USGS curved edges are discrete sampled polylines, not exact analytic curves',
                   'This does NOT walk every cut 1km cell at 1m intervals'],
         'zones':[]}
 with ZipFile(archive_path) as archive:
  for key,(global_name,grid_name,zone) in DATA.items():
   boundaries,path=_source_reader(archive,global_name)
   if len(boundaries)!=1:raise ValueError(f'{global_name}: not one boundary')
   vertices=boundaries.shape(0).points
   residuals=[_residual_m(zone,x,y) for x,y in vertices]
   grids,grid_path=_source_reader(archive,grid_name)
   outside=bad=0;max_box_violation=0;offending=[];candidate_intersections=0
   for record in grids.iterShapeRecords():
    points=record.shape.points
    if not points:continue
    minx,miny,maxx,maxy=record.shape.bbox
    # A clipped polygon is contained by its nominal 25km square, and
    # its bbox midpoint unambiguously identifies that square.
    e=floor(((minx+maxx)/2)/25000)
    n=floor(((miny+maxy)/2)/25000)
    loe,hie=e*25000,(e+1)*25000
    lon,hin=n*25000,(n+1)*25000
    worst=max(max(loe-x,x-hie,lon-y,y-hin,0) for x,y in points)
    max_box_violation=max(max_box_violation,worst)
    if worst>1:
     bad+=1
     if len(offending)<10:offending.append([e,n,worst])
    # Determine if any constituent 1km parcel intersects the rev21 zone.
    intersects=False
    for dx in range(25):
     if intersects:break
     for dy in range(25):
      if classify_square(zone,25*e+dx,25*n+dy)[1]:
       intersects=True;break
    if intersects:candidate_intersections+=1
    else:outside+=1
   report['zones'].append({
    'zone':key,'official_boundary':path,'official_25km_grid':grid_path,
    'official_grid_polygon_count':len(grids),
    'boundary_vertex_count':len(vertices),
    'max_reference_boundary_residual_m':max(residuals),
    'mean_reference_boundary_residual_m':sum(residuals)/len(residuals),
    'max_polygon_outside_nominal_25km_square_m':max_box_violation,
    'polygons_exceeding_1m_grid_square_bounds':bad,
    'offending_polygon_examples':offending,
    'official_polygons_intersecting_rev21_zone':candidate_intersections,
    'official_polygons_outside_rev21_zone':outside,
    'note':('80-82 degree reference overlap is intentionally excluded'
            if zone.kind=='ltm' else '80 degree polar cap boundary')
   })
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('archive');p.add_argument('--output',required=True)
 args=p.parse_args()
 data=check(args.archive)
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(data,indent=2)+'\n')
 for z in data['zones']:
  print(z['zone'],'official polygons',z['official_grid_polygon_count'],
        'overlap polygons',z['official_polygons_outside_rev21_zone'],
        'boundary residual m',round(z['max_reference_boundary_residual_m'],6),
        'grid violation m',round(z['max_polygon_outside_nominal_25km_square_m'],6))
 if any(z['max_reference_boundary_residual_m']>1 or
        z['polygons_exceeding_1m_grid_square_bounds'] for z in data['zones']):
  raise SystemExit('Projection boundary or 25km grid alignment did not pass provisional 1m checks')

if __name__=='__main__': main()
