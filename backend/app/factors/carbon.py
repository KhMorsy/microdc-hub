# grid carbon intensity at this postal code, gco2/kwh. lower is better.
# REAL: computed from germany's live generation mix (energy-charts /public_power) weighted by
# per-fuel lifecycle emission factors. national -> uniform across bavaria.

from . import sources, zones

HIGHER_IS_BETTER = False
UNIT = "gco2/kwh (from generation mix, per country)"


def value(plz):
    return sources.zone_carbon(zones.country_for(plz))["g_per_kwh"]


# band from a given value (pass the number so the badge matches what's shown)
def band(g):
    return "low" if g < 200 else ("mid" if g < 300 else "high")
