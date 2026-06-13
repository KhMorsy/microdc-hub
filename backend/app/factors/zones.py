# maps a postal code to its electricity bidding zone + country.
# today everything is bavaria -> DE-LU / de, so price/carbon come out uniform (neutral 50 after rank).
# EXTENSION POINT: when adding regions in other bidding zones, return the right zone/country here
# (e.g. austrian plz -> "AT"/"at", french -> "FR"/"fr"). price/carbon then differ per region and the
# map gains a real spatial price/carbon signal automatically — no other code changes needed.

DEFAULT_ZONE = "DE-LU"
DEFAULT_COUNTRY = "de"


def zone_for(plz):
    return DEFAULT_ZONE


def country_for(plz):
    return DEFAULT_COUNTRY
