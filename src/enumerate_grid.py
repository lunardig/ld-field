"""Revision 21 provisional lunar projected-grid enumeration.

Enumerates every 25 km tile touching each LTM/LPS zone and classifies its 625
1 km squares. Geometry remains PROVISIONAL until the official USGS 25 km grid
and mandatory all-cut-square 1 m edge validation have been completed.

Usage:
 python -m src.enumerate_grid --zone ltm-23-n --output build/grid
 python -m src.enumerate_grid --zone lps-s --output build/grid
 python -m src.enumerate_grid --all --output build/grid
 python -m src.enumerate_grid --zone ltm-23-n --output build/test --tile-limit 4
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, pathlib, time
from .grid import Zone, classify_square, projected_key_to_tile, RADIUS_M, LTM_K0, LTM_FALSE_EASTING, LPS_FALSE_ORIGIN, _polar_radius_m
from .field import ZONES

def zone_from_index(index:int)->Zone:
    if not 0 <= index < 92: raise ValueError('zone out of range')
    if index>=90: return Zone('lps','n' if index==90 else 's')
    z=(index%45)+1
    return Zone('ltm','n' if index<45 else 's',-176+8*(z-1))

def projected_bounds(zone:Zone):
    """Conservative 25 km tile bounds for the entire zone.

    Sampling the perimeter is augmented by a full 1 km safety buffer; this
    sampling bound is not a mathematical global-enclosure proof and must be
    reconciled with the USGS shapefile envelope before production use.
    """
    if zone.kind=='lps':
        r=_polar_radius_m()
        return (math.floor((LPS_FALSE_ORIGIN-r-1000)/25000),
                math.ceil((LPS_FALSE_ORIGIN+r+1000)/25000),
                math.floor((LPS_FALSE_ORIGIN-r-1000)/25000),
                math.ceil((LPS_FALSE_ORIGIN+r+1000)/25000))
    xy=[]
    origin=0 if zone.hemisphere=='n' else 2_500_000
    sign=1 if zone.hemisphere=='n' else -1
    # Dense samples on both lat bounds and both longitude bounds.
    # Forward spherical Transverse Mercator, relative longitude in radians.
    for step in range(321):
        latitude=sign*80*step/320
        for longitude in (-4,4):
            phi,lam=math.radians(latitude),math.radians(longitude)
            B=math.cos(phi)*math.sin(lam)
            x=RADIUS_M*LTM_K0*math.atanh(B)+LTM_FALSE_EASTING
            y=RADIUS_M*LTM_K0*math.atan2(math.tan(phi),math.cos(lam))+origin
            xy.append((x,y))
    for step in range(33):
        lon=-4+8*step/32
        for lat in (0,sign*80):
            phi,lam=math.radians(lat),math.radians(lon)
            B=math.cos(phi)*math.sin(lam)
            x=RADIUS_M*LTM_K0*math.atanh(B)+LTM_FALSE_EASTING
            y=RADIUS_M*LTM_K0*math.atan2(math.tan(phi),math.cos(lam))+origin
            xy.append((x,y))
    return (math.floor((min(x for x,y in xy)-1000)/25000),
            math.ceil((max(x for x,y in xy)+1000)/25000),
            math.floor((min(y for x,y in xy)-1000)/25000),
            math.ceil((max(y for x,y in xy)+1000)/25000))

def enumerate_zone(index:int, directory, *, tile_limit=None, on_tile=None):
    """Write a canonical grid mask inventory, optionally deliver tile to caller.

    CSV rows are one 25 km grid tile; bitmaps encoded as 158 lower-case hex
    characters. A masked cell's input data is not included. `on_tile`
    receives (zone_index, tile_e, tile_n, bytes(whole), bytes(in_zone)).
    """
    zone=zone_from_index(index)
    bounds=projected_bounds(zone)
    output=pathlib.Path(directory);output.mkdir(parents=True,exist_ok=True)
    filename=output/(ZONES[index]+'.csv')
    total_whole=total_partial=total_inzone=0
    count=0
    h=hashlib.sha256()
    with filename.open('w',newline='') as fp:
        writer=csv.writer(fp,lineterminator='\n')
        writer.writerow(('zone_index','tile_e','tile_n','whole_hex','inzone_hex','whole_count','partial_count'))
        for e in range(bounds[0],bounds[1]):
            for n in range(bounds[2],bounds[3]):
                whole=bytearray(79);inside=bytearray(79)
                cw=cp=ci=0
                for y in range(25):
                    for x in range(25):
                        w,z=classify_square(zone,25*e+x,25*n+y)
                        i=x+25*y
                        if z: inside[i>>3]|=1<<(i&7);ci+=1
                        if w: whole[i>>3]|=1<<(i&7);cw+=1
                        elif z:cp+=1
                if not ci:continue
                row=(index,e,n,whole.hex(),inside.hex(),cw,cp)
                line=','.join(map(str,row))+'\n'
                fp.write(line);h.update(line.encode())
                total_whole+=cw;total_partial+=cp;total_inzone+=ci;count+=1
                if on_tile:on_tile(index,e,n,bytes(whole),bytes(inside))
                if tile_limit is not None and count>=tile_limit:break
            if tile_limit is not None and count>=tile_limit:break
    result={'zone':ZONES[index],'zone_index':index,'bounds_candidate':bounds,
            'grid_inventory':str(filename),'inventory_sha256':h.hexdigest(),
            'tile_count':count,'whole':total_whole,'partial':total_partial,
            'in_zone':total_inzone,'provisional':True,
            'exhaustive_zone':tile_limit is None}
    (output/(ZONES[index]+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    selection=parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--zone',choices=ZONES)
    selection.add_argument('--all',action='store_true')
    parser.add_argument('--output',default='build/grid')
    parser.add_argument('--tile-limit',type=int)
    args=parser.parse_args()
    if args.tile_limit is not None and args.tile_limit<=0:parser.error('tile-limit must be positive')
    indices=range(92) if args.all else [ZONES.index(args.zone)]
    results=[]
    for idx in indices:
        info=enumerate_zone(idx,args.output,tile_limit=args.tile_limit)
        print(info['zone'],info['tile_count'],info['whole'],info['partial'],flush=True)
        results.append(info)
    pathlib.Path(args.output,'summary.json').write_text(json.dumps({'zones':results,'provisional':True},indent=2)+'\n')

if __name__=='__main__':main()
