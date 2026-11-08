"""Read selected official USGS projected-coordinate LGRS shapefiles.

Samples official source geometries without changing upstream files. Generates
evidence needed to design a real 1 m geometric comparison. This is a
diagnostic, NOT itself the rev21 global 1 m acceptance test.
"""
from __future__ import annotations
import argparse, io, json, math, pathlib, zipfile
from collections import Counter

DATASETS=[
 "LGRS_25km_23N_Grid",
 "LGRS_25km_23S_Grid",
 "PolarLGRS_25km_N_Grid",
 "PolarLGRS_25km_S_Grid",
 "LTM_global_23N_Grid",
 "LTM_global_23S_Grid",
 "LPS_global_N_Grid",
 "LPS_global_S_Grid",
]

def inspect(archive):
 import shapefile
 report=[]
 with zipfile.ZipFile(archive) as z:
  names=z.namelist()
  for name in DATASETS:
   paths=[s for s in names if s.endswith('/'+name+'.shp') and '/PCRS_Zone_Specific/' in s]
   if not paths: report.append(dict(name=name,error="not present"));continue
   path=paths[0];stem=path[:-4]
   try:
    shp=shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),
                         shx=io.BytesIO(z.read(stem+'.shx')),
                         dbf=io.BytesIO(z.read(stem+'.dbf')))
    data=dict(name=name,source=path,shape_count=len(shp),shape_type=shp.shapeTypeName,
              bbox=shp.bbox,fields=shp.fields[1:],
              sample_records=[],coordinate_stats={})
    counts=Counter();total=0;on_grid=0;max_on_grid=0;min_grid=math.inf
    max_fraction=0
    for idx, sr in enumerate(shp.iterShapeRecords()):
     pts=sr.shape.points
     if idx<4:
      data['sample_records'].append(dict(attrs=list(sr.record),points=pts[:10],
                                         bbox=sr.shape.bbox if hasattr(sr.shape,'bbox') else None,
                                         point_count=len(pts),parts=list(sr.shape.parts)))
     total+=len(pts)
     for x,y in pts:
      dx=abs(x/25000-round(x/25000))*25000
      dy=abs(y/25000-round(y/25000))*25000
      dd=min(dx,dy)
      if dd<=1:on_grid+=1;max_on_grid=max(max_on_grid,dd)
      min_grid=min(min_grid,dd)
      counts[int(min(dd,9999)//50)*50]+=1
    data['coordinate_stats']={'vertex_count':total,
         'within_1m_of_25km_e_or_n_grid':on_grid,
         'fraction_grid_aligned':round(on_grid/total,6) if total else None,
         'residual_bins_m':counts.most_common(20)}
    report.append(data)
 return report

def main():
 p=argparse.ArgumentParser()
 p.add_argument('archive');p.add_argument('--output',required=True)
 args=p.parse_args()
 j={'datasets':inspect(args.archive),'note':'Descriptive source geometry inventory; no 1m approval.'}
 path=pathlib.Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(j,indent=2)+'\n')
 for d in j['datasets']:print(d['name'],d.get('shape_count'),d.get('coordinate_stats',{}).get('fraction_grid_aligned'),d.get('error'))
if __name__=='__main__':main()
