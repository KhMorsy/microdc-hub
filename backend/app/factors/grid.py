# grid headroom — ability to connect a NEW load here. higher is better. CAPACITY-AWARE.
# the substation voltage you can use scales with the load: a tiny edge box plugs into the ubiquitous
# low/medium-voltage grid; a campus needs sparse high-voltage (transmission). so the threshold follows
# the capacity class. value sums nearby usable-substation capacity (kv), distance-decayed.
#
# REAL proxy from OSM. multi-source: voltage (capacity proxy) + distance. swap for PyPSA-Eur later.

import math
from . import geo, sources

HIGHER_IS_BETTER = True
UNIT = "substation proximity proxy, capacity-aware (real: MW spare)"

# minimum substation voltage (kV) that a load of each class can realistically connect to.
# (german levels: 0.4 LV, 10/20/30 MV, 110 HV, 220/380 EHV.)
CAP_MIN_KV = {"edge": 0, "micro": 10, "container": 20, "small": 30, "campus": 110}
DEFAULT_CAP = "container"

_CELL = 0.4        # spatial bucket (~0.4 deg) so nearest-substation lookup is fast, not O(39k)/plz
_idx = {}          # min_kv -> {(ci, cj): [[lat, lon, kv], ...]}


def _index(min_kv):
    if min_kv not in _idx:
        buckets = {}
        for s in sources.substations():
            if s[2] < min_kv:
                continue
            buckets.setdefault((int(s[0] / _CELL), int(s[1] / _CELL)), []).append(s)
        _idx[min_kv] = buckets
    return _idx[min_kv]


def value(plz, capacity=DEFAULT_CAP):
    lat, lon = geo.centroid(plz)
    buckets = _index(CAP_MIN_KV.get(capacity, 20))
    ci, cj = int(lat / _CELL), int(lon / _CELL)
    acc = 0.0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for slat, slon, kv in buckets.get((ci + di, cj + dj), ()):
                d = math.hypot((slat - lat) * 111.0, (slon - lon) * 71.0)
                acc += kv * math.exp(-d / 12.0)
    return round(acc, 2)
