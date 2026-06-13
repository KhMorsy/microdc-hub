# maps a postal code to its electricity bidding zone + country.
# bavaria (germany) uses 5-digit PLZ -> DE-LU / de; austria uses 4-digit PLZ -> AT / at.
# length cleanly separates them (no numeric overlap). add more regions here as they come.
#
# EXTENSION POINT: with >1 bidding zone in the set, price/carbon are no longer uniform, so they
# stop collapsing to the neutral 50 and become real spatial signals automatically.

ZONES = {
    "DE-LU": {"len": 5, "country": "de"},   # germany (bavaria)
    "AT":    {"len": 4, "country": "at"},   # austria
}
_BY_LEN = {z["len"]: (name, z["country"]) for name, z in ZONES.items()}
DEFAULT = ("DE-LU", "de")


def _lookup(plz):
    return _BY_LEN.get(len(str(plz).strip()), DEFAULT)


def zone_for(plz):
    return _lookup(plz)[0]


def country_for(plz):
    return _lookup(plz)[1]
