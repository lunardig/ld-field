"""Inspect the pinned USGS LGRS release archive without extracting shapefile bodies.

Used by GitHub Actions to validate preserved upstream archive bytes and
inventory all included WKT .prj files. Does not claim 1-m geometry validation.

Usage:
    python -m src.validate_usgs_release LTM_LPS_LGRS_Shapefiles.zip \
      --sha256 0ab9a17428a5ac076be301dd027cacb1ad3b6e06878c3768a488f9deda3c7623 \
      --output build/usgs-lgrs-release-audit.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def audit_archive(path, expected_sha256):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    actual=sha256(path)
    if actual!=expected_sha256.lower():
        raise ValueError(f'Archive SHA-256 mismatch: got {actual}, expected {expected_sha256}')
    from pyproj import CRS
    report={'source':'USGS LGRS Rasters and Shapefiles',
            'doi':'10.5066/P13YPWQD',
            'release':'https://github.com/lunardig/ld-field/releases/tag/usgs-lgrs-source-2024',
            'archive_name':path.name,'archive_size_bytes':path.stat().st_size,
            'archive_sha256':actual,'archive_checksum_match':True,
            'prj':[], 'shapefiles':[], 'errors':[],
            'geometry_comparison_passed':False,
            'status':'SOURCE_PROJECTION_INVENTORY_ONLY'}
    with ZipFile(path) as archive:
        problems=archive.testzip()
        if problems:raise BadZipFile(f'Bad member: {problems}')
        members=archive.infolist()
        report['zip_member_count']=len(members)
        report['shapefiles']=[m.filename for m in members if m.filename.lower().endswith('.shp')]
        for item in members:
            if not item.filename.lower().endswith('.prj'):continue
            raw=archive.read(item)
            record={'path':item.filename,'sha256':hashlib.sha256(raw).hexdigest(),
                    'size_bytes':len(raw)}
            try:
                crs=CRS.from_wkt(raw.decode('utf-8-sig'))
                ellipsoid=crs.ellipsoid
                record.update(
                    method=crs.coordinate_operation.method_name if crs.coordinate_operation else None,
                    semi_major_m=ellipsoid.semi_major_metre,
                    semi_minor_m=ellipsoid.semi_minor_metre,
                    params=[{'name':p.name,'value':p.value,'unit':p.unit_name}
                            for p in (crs.coordinate_operation.params if crs.coordinate_operation else [])],
                    crs_name=crs.name,
                )
            except Exception as ex:
                record['error']=str(ex)
                report['errors'].append({'path':item.filename,'reason':str(ex)})
            report['prj'].append(record)
    report['prj_count']=len(report['prj'])
    report['shp_count']=len(report['shapefiles'])
    if report['prj_count']==0:
        raise ValueError('No .prj files in official archive; inspect packaging')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('--sha256',required=True,help='Externally pinned release digest')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    report=audit_archive(args.archive,args.sha256)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('Archive verified:',report['archive_sha256'])
    print('Shapefile entries:',report['shp_count'],'WKT projection entries:',report['prj_count'])
    print('WKT decode errors:',len(report['errors']))
    print('Evidence:',output)
    if report['errors']:raise SystemExit('One or more WKT projections failed to decode')

if __name__=='__main__':main()
