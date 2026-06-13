# heat reuse — proximity to a buyer of waste heat. higher is better.
# REAL: OSM heat off-takers (hospitals, greenhouses, water parks, public baths), weighted by type
# and distance-decayed. genuinely per-location. swap/extend with district-heating networks later.

import math
from . import geo, sources

HIGHER_IS_BETTER = True
UNIT = "weighted heat-buyer proximity (OSM)"


def value(plz):
    lat, lon = geo.centroid(plz)
    acc = 0.0
    for blat, blon, wt in sources.heat_buyers():
        dlat = (blat - lat) * 111.0
        if dlat > 28 or dlat < -28:
            continue
        d = math.hypot(dlat, (blon - lon) * 71.0)
        if d > 28:
            continue
        acc += wt * math.exp(-d / 6.0)
    return round(acc, 2)
