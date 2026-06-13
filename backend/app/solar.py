# rank buildings in a postal code by rooftop solar suitability (Google Solar API).
# candidates come from OSM Overpass; scoring mirrors rank-data-center-sites-solar.js.
# needs GOOGLE_SOLAR_API_KEY in the environment (server-side; never sent to the browser).

import json, urllib.request, urllib.parse

UA = "microdc-hub/1.0 (data-center siting)"
OVERPASS = "https://overpass-api.de/api/interpreter"
SOLAR = "https://solar.googleapis.com/v1/buildingInsights:findClosest"


def _get_json(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


# large / commercial buildings INSIDE the postal-code bbox (s, w, n, e) — the data-center candidates.
def candidates(bbox, limit=9):
    s, w, n, e = bbox
    bb = "(%f,%f,%f,%f)" % (s, w, n, e)
    q = ('[out:json][timeout:25];('
         'way["building"~"commercial|retail|warehouse|industrial|public|office|hotel"]%s;'
         'way["building"="yes"]["name"]%s;'
         ');out center tags;') % (bb, bb)
    d = _get_json(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), timeout=60)
    out, seen = [], set()
    for el in d.get("elements", []):
        c = el.get("center", {})
        if not c or el["id"] in seen:
            continue
        seen.add(el["id"])
        t = el.get("tags", {})
        out.append({"label": t.get("name") or ((t.get("building") or "building") + " building"),
                    "osm_id": el["id"], "lat": c["lat"], "lng": c["lon"]})
        if len(out) >= limit:
            break
    return out


def _building_solar(lat, lng, key, quality="BASE"):
    p = urllib.parse.urlencode({"location.latitude": lat, "location.longitude": lng,
                                "requiredQuality": quality, "key": key})
    return _get_json(SOLAR + "?" + p, timeout=30)


# same screening score as the js: annual energy + usable+whole roof area + sunshine + panels.
def _score(sp):
    if not sp:
        return 0.0
    cfgs = sp.get("solarPanelConfigs") or []
    cfg = cfgs[-1] if cfgs else {}
    return (cfg.get("yearlyEnergyDcKwh", 0) * 0.45
            + sp.get("maxArrayAreaMeters2", 0) * 8
            + (sp.get("wholeRoofStats") or {}).get("areaMeters2", 0) * 2
            + sp.get("maxSunshineHoursPerYear", 0) * 3
            + sp.get("maxArrayPanelsCount", 0) * 20)


def rank_sites(bbox, key, n=3):
    s, w, north, e = bbox
    ranked = []
    for c in candidates(bbox):
        try:
            sp = (_building_solar(c["lat"], c["lng"], key).get("solarPotential")) or {}
            cfgs = sp.get("solarPanelConfigs") or []
            cfg = cfgs[-1] if cfgs else {}
            ranked.append({
                "label": c["label"],
                "lat": _clamp(c["lat"], s, north),   # keep the pin inside the postal-code box
                "lng": _clamp(c["lng"], w, e),
                "score": round(_score(sp), 1),
                "annual_kwh": cfg.get("yearlyEnergyDcKwh"),
                "panels": sp.get("maxArrayPanelsCount"),
                "roof_m2": (sp.get("wholeRoofStats") or {}).get("areaMeters2"),
                "sunshine_h": sp.get("maxSunshineHoursPerYear"),
            })
        except Exception:
            pass   # building not covered by Solar API -> skip (the js drops these into "failed")
    ranked.sort(key=lambda x: -x["score"])
    return ranked[:n]
