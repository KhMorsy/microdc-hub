# electricity price at this postal code, eur/mwh. lower is better.
# REAL: wholesale day-ahead for the DE-LU zone (energy-charts). germany is one bidding zone, so this
# is national -> the same across bavaria (it differentiates by time, not location).
# multi-source hook: add regional network charges (Netzentgelte) here for a spatial component later.

from . import sources, zones

HIGHER_IS_BETTER = False
UNIT = "eur/mwh (wholesale day-ahead, per bidding zone)"


def value(plz):
    return sources.zone_price(zones.zone_for(plz))["mean"]
