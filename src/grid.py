"""LGRS-derived projected cell geometry for LD-PEC-011 rev21.

This is an independently testable *candidate* implementation. It is NOT an
authoritative lunar survey until verified against the pinned USGS shapefiles.
All positions are on the nominal 1,737,400 m reference sphere.

Zone central meridians are intentionally supplied by the caller: determining
official LTM zone numbering is an explicit Package 1 acceptance gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, atan, atan2, cos, cosh, degrees, hypot, pi, radians, sin, sinh, sqrt, tan

RADIUS_M = 1_737_400.0
LTM_K0 = .999
LPS_K0 = .994
POLAR_LIMIT_DEG = 80.0
HALF_LTM_STRIP_DEG = 4.0
LTM_FALSE_EASTING = 250_000.0
LPS_FALSE_ORIGIN = 500_000.0


@dataclass(frozen=True)
class Zone:
    kind: str  # "ltm" or "lps"
    hemisphere: str  # "n" or "s"
    central_meridian_deg: float = 0.0

    def __post_init__(self):
        if self.kind not in ("ltm", "lps") or self.hemisphere not in ("n", "s"):
            raise ValueError("invalid projection zone")
        if self.kind == "ltm" and not -180 <= self.central_meridian_deg < 180:
            raise ValueError("invalid central meridian")


def _relative_lat_lon(zone: Zone, e_m: float, n_m: float) -> tuple[float, float]:
    """Inverse spherical LTM: returns latitude and offset from central meridian."""
    if zone.kind != "ltm":
        raise ValueError("LTM expected")
    north0 = 0 if zone.hemisphere == "n" else 2_500_000
    x = (e_m - LTM_FALSE_EASTING) / (RADIUS_M * LTM_K0)
    y = (n_m - north0) / (RADIUS_M * LTM_K0)
    latitude = degrees(asin(sin(y) / cosh(x)))
    longitude_offset = degrees(atan2(sinh(x), cos(y)))
    return latitude, longitude_offset


def _ltm_inside(zone: Zone, e_m: float, n_m: float) -> bool:
    phi, lam = _relative_lat_lon(zone, e_m, n_m)
    return ((0 <= phi <= 80 if zone.hemisphere == "n" else -80 <= phi <= 0)
            and -HALF_LTM_STRIP_DEG <= lam <= HALF_LTM_STRIP_DEG)


def _polar_radius_m() -> float:
    return 2 * RADIUS_M * LPS_K0 * tan(radians(5))


def _bounds(e_km: int, n_km: int, side_m: float = 1000) -> tuple[float,float,float,float]:
    if not isinstance(e_km,int) or not isinstance(n_km,int):
        raise TypeError("grid coordinates must be integers in kilometres")
    return e_km * 1000., n_km * 1000., e_km * 1000. + side_m, n_km * 1000. + side_m


def _split_at_zero(a: float, b: float, origin: float) -> tuple[float,...]:
    return ((a, origin, b) if a < origin < b else (a,b))


def _segment_candidates(f, a: float, b: float, target: float, iterations: int = 65):
    """Endpoints plus root of f(x)-target when a sign change is present."""
    fa, fb = f(a)-target, f(b)-target
    result=[a,b]
    if fa == 0 or fb == 0 or fa * fb >= 0:
        return result
    lo, hi = a, b
    for _ in range(iterations):
        mid=(lo+hi)*.5
        fm=f(mid)-target
        if fm == 0:
            lo=hi=mid
            break
        if fa * fm <= 0:
            hi=mid
        else:
            lo=mid
            fa=fm
    result.append((lo+hi)/2)
    return result


def classify_square(zone: Zone, e_km: int, n_km: int) -> tuple[bool,bool]:
    """Return (whole, in_zone) for a 1 km square.

    For LPS the zone is a convex disc, so farthest/nearest distances to its
    center decide. LTM whole uses four corners under rev21's monotonicity
    assumptions. LTM in_zone uses roots of the equatorward-edge latitude and
    longitude limits, retaining candidate midpoints between roots.

    A world-field builder MUST cross-check boundaries with USGS geodata and
    the rev21 1 m edge-walk acceptance test before publishing production bits.
    """
    e0,n0,e1,n1=_bounds(e_km,n_km)
    if zone.kind=="lps":
        radius=_polar_radius_m()
        cx=cy=LPS_FALSE_ORIGIN
        corners=[hypot(x-cx,y-cy) for x in (e0,e1) for y in (n0,n1)]
        nearest=hypot(max(e0-cx,0,cx-e1), max(n0-cy,0,cy-n1))
        return max(corners) <= radius, nearest <= radius

    corners=[_ltm_inside(zone,x,y) for x in (e0,e1) for y in (n0,n1)]
    whole=all(corners)
    if whole: return True, True

    y=n0 if zone.hemisphere=="n" else n1
    parts=_split_at_zero(e0,e1,LTM_FALSE_EASTING)
    candidates={e0,e1}
    for left,right in zip(parts,parts[1:]):
        for func,target in (
            (lambda x: _relative_lat_lon(zone,x,y)[0],80 if zone.hemisphere=="n" else -80),
            (lambda x: _relative_lat_lon(zone,x,y)[1],-4),
            (lambda x: _relative_lat_lon(zone,x,y)[1],4)):
            candidates.update(_segment_candidates(func,left,right,target))
    positions=sorted(candidates)
    positions += [(a+b)/2 for a,b in zip(positions,positions[1:])]
    in_zone=any(_ltm_inside(zone,x,y) for x in positions)
    return whole,in_zone


def projected_key_to_tile(e_km: int,n_km:int)->tuple[int,int,int]:
    """Tile e/n and row-major cell index; Python // and % handle negatives."""
    tile_e=e_km//25
    tile_n=n_km//25
    return tile_e,tile_n,(e_km%25)+25*(n_km%25)


def boundary_walk(zone:Zone,e_km:int,n_km:int,step_m:float=1.0)->tuple[bool,bool]:
    """Slow, independent sampling for validation, NOT the production classifier.

    Walk all four edges in <=step_m intervals plus the center. This is a
    diagnostic approximation, not a proof of the square's interior.
    """
    from math import ceil
    e0,n0,e1,n1=_bounds(e_km,n_km)
    intervals=ceil(1000/step_m)
    checks=[]
    if zone.kind=="lps":
        radius=_polar_radius_m()
        contains=lambda x,y:hypot(x-LPS_FALSE_ORIGIN,y-LPS_FALSE_ORIGIN)<=radius
    else:
        contains=lambda x,y:_ltm_inside(zone,x,y)
    for i in range(intervals+1):
        t=i/intervals
        checks.extend((contains(e0+(e1-e0)*t,n0),
                       contains(e0+(e1-e0)*t,n1),
                       contains(e0,n0+(n1-n0)*t),
                       contains(e1,n0+(n1-n0)*t)))
    checks.append(contains((e0+e1)/2,(n0+n1)/2))
    return all(checks),any(checks)
