# flexibility — upside from shifting load to the cheapest hours, driven by the daily price spread.
# higher is better.
# REAL: max-min of the DE-LU day-ahead curve (energy-charts). national -> uniform across bavaria.

from . import sources, zones

HIGHER_IS_BETTER = True
UNIT = "eur/mwh daily price spread (per bidding zone)"


def value(plz):
    return sources.zone_price(zones.zone_for(plz))["spread"]
