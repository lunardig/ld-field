"""Inspect official GIS WKT and PDS labels for Revision 21 Package 1.

Usage:
 python -m src.inspect_sources wkt path/to/official.prj
 python -m src.inspect_sources pds path/to/lpgrs_high1_elem_abundance_2deg.lbl

Outputs evidence in JSON, quoting the source file SHA-256. Inspectors never
silently assert that a file is official; archive provenance must be checked
independently against the USGS/PDS download record.
"""
from __future__ import annotations
import argparse, json, pathlib, re
from .raster_pipeline import file_sha256

LUNAR_RADIUS=1_737_400.0

def inspect_wkt(path):
    try:
        from pyproj import CRS
    except ImportError as ex:
        raise RuntimeError('pyproj required: pip install pyproj') from ex
    p=pathlib.Path(path)
    crs=CRS.from_wkt(p.read_text())
    ell=crs.ellipsoid
    params=[]
    if crs.coordinate_operation:
        for param in crs.coordinate_operation.params:
            params.append({'name':param.name,'value':param.value,'unit':param.unit_name,
                           'code':getattr(param,'code',None)})
    result={'file':str(p),'sha256':file_sha256(p),'method':crs.coordinate_operation.method_name if crs.coordinate_operation else None,
            'ellipsoid_name':ell.name,'semi_major_m':ell.semi_major_metre,'semi_minor_m':ell.semi_minor_metre,
            'prime_meridian':crs.prime_meridian.name,'parameters':params,'wkt_version':crs.to_wkt(version='WKT2_2019')}
    result['radius_matches_nominal']=abs(ell.semi_major_metre-LUNAR_RADIUS)<.001 and abs(ell.semi_minor_metre-LUNAR_RADIUS)<.001
    return result

def parse_pds_label(path):
    """Parse simple PDS3 field definitions; preserve all raw key/value evidence."""
    p=pathlib.Path(path)
    text=p.read_text(errors='replace')
    records=[]
    current=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('/*'):continue
        if line.startswith('OBJECT') and '=' in line:
            current.append(line.split('=',1)[1].strip())
        if '=' in line:
            key,value=line.split('=',1)
            if key.strip() in ('NAME','DATA_TYPE','START_BYTE','BYTES','UNIT','UNITS','ITEMS','ITEM_BYTES','ROW_BYTES','ROWS','LINE_SAMPLES','MAP_RESOLUTION'):
                records.append({'object':list(current),'name':key.strip(),'value':value.strip()})
        if line.startswith('END_OBJECT') and current:current.pop()
    keys=('W_FEO','W_TIO2','ERROR','LATITUDE','LONGITUDE','SAMPLE','LINE','DEG')
    evidence=[line.strip() for line in text.splitlines() if any(k in line.upper() for k in keys)]
    return {'file':str(p),'sha256':file_sha256(p),'metadata':records,
            'selected_label_lines':evidence[:300],
            'note':'Values must be interpreted according to the exact PDS dataset format and error-matrix description.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for cmd in ('wkt','pds'):
        s=sub.add_parser(cmd);s.add_argument('file')
        s.add_argument('--output',help='Optional JSON report file')
    args=parser.parse_args()
    report=inspect_wkt(args.file) if args.command=='wkt' else parse_pds_label(args.file)
    result=json.dumps(report,indent=2,sort_keys=True)
    if args.output:pathlib.Path(args.output).write_text(result+'\n')
    else:print(result)

if __name__=='__main__':main()
