# real-data sources for the factor providers. fetch once, cache to disk, reuse.
# national feeds (price, carbon, flex) -> energy-charts. spatial feeds (grid, heat) -> osm overpass.
# everything here is stdlib-only (urllib) so the backend keeps just fastapi+uvicorn.

import json, os, time, urllib.request, urllib.parse

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)

UA = "microdc-hub/1.0 (hackathon data-center siting tool)"
EC = "https://api.energy-charts.info"
OVERPASS = "https://overpass-api.de/api/interpreter"

# OSM is fetched per region (south, west, north, east) and merged. add a region here to extend coverage;
# the rest of the pipeline works on the merged points wherever they are.
REGIONS = {
    "bavaria": (47.2, 8.9, 50.6, 13.9),
    "austria": (46.3, 9.5, 49.1, 17.2),
}

# lifecycle emission factors, gCO2eq/kWh, keyed by energy-charts production type (approx IPCC medians)
EMIT = {
    "Fossil brown coal / lignite": 1100, "Fossil hard coal": 900, "Fossil oil": 750,
    "Fossil coal-derived gas": 800, "Fossil gas": 450, "Waste": 500, "Biomass": 230,
    "Hydro Run-of-River": 24, "Hydro water reservoir": 24, "Hydro pumped storage": 24,
    "Geothermal": 38, "Wind offshore": 12, "Wind onshore": 11, "Solar": 45, "Others": 500,
}


TTL_NATIONAL = 1800        # 30 min: prices/carbon move intraday, refresh often
TTL_OSM = 7 * 86400        # weekly: substations / heat buyers barely change
_MEM = {}                  # in-memory memo: a feed is parsed once per process, not once per plz


def _get_json(url, data=None, timeout=90):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# two-level cache: in-memory (per process) over disk (across runs), both honoring this feed's ttl.
def _cached(name, build, ttl=TTL_NATIONAL):
    now = time.time()
    hit = _MEM.get(name)
    if hit and now - hit[1] < ttl:
        return hit[0]
    p = os.path.join(CACHE, name + ".json")
    if os.path.exists(p) and now - os.path.getmtime(p) < ttl:
        with open(p, encoding="utf-8") as f:
            val = json.load(f)
        ts = os.path.getmtime(p)
    else:
        val = build()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(val, f)
        ts = now
    _MEM[name] = (val, ts)
    return val


# ---- wholesale day-ahead price for a bidding zone, eur/mwh. cached per zone ----
# one zone today (DE-LU). add zones and price/carbon differ per region -> real spatial signal.
def zone_price(zone="DE-LU"):
    def build():
        d = _get_json(EC + "/price?bzn=" + zone)
        ps = [p for p in d.get("price", []) if p is not None]
        if not ps:
            return {"mean": 90.0, "min": 70.0, "max": 120.0, "spread": 50.0}
        return {"mean": round(sum(ps) / len(ps), 1), "min": round(min(ps), 1),
                "max": round(max(ps), 1), "spread": round(max(ps) - min(ps), 1)}
    return _cached("price_" + zone, build)


# fetch the generation mix over the last `days` (so we capture full daily solar/wind cycles, not just
# the elapsed hours of today — otherwise an early-morning fetch shows ~0% solar).
def _public_power(country, days=2):
    end = int(time.time())
    start = end - days * 86400
    return _get_json(EC + "/public_power?country=%s&start=%d&end=%d" % (country, start, end))


# ---- grid carbon intensity from a country's live generation mix, gco2/kwh. cached per country ----
def zone_carbon(country="de"):
    def build():
        d = _public_power(country)
        num = den = 0.0
        for pt in d.get("production_types", []):
            f = EMIT.get(pt["name"])
            if f is None:
                continue
            vals = [v for v in pt.get("data", []) if v is not None and v > 0]
            if not vals:
                continue
            avg = sum(vals) / len(vals)
            num += avg * f
            den += avg
        return {"g_per_kwh": round(num / den) if den else 300}
    return _cached("carbon_" + country, build)


# ---- 24h curves for EarnMax (hourly, bucketed by Berlin local hour) ----
def _hour_berlin(unix):
    return int((unix + 2 * 3600) // 3600) % 24   # CEST (+2) — correct for summer


def _fill24(curve):
    present = [v for v in curve if v is not None]
    m = sum(present) / len(present) if present else 0.0
    return [round(v) if v is not None else round(m) for v in curve]


# real day-ahead price curve, 24 hourly values (index = hour of day). eur/mwh.
def price_curve(zone="DE-LU"):
    def build():
        d = _get_json(EC + "/price?bzn=" + zone)
        by = {}
        for s, p in zip(d.get("unix_seconds", []), d.get("price", [])):
            if p is not None:
                by.setdefault(_hour_berlin(s), []).append(p)
        return _fill24([(sum(by[h]) / len(by[h]) if by.get(h) else None) for h in range(24)])
    return _cached("price_curve_" + zone, build)


# real carbon curve, 24 hourly gco2/kwh computed from the generation mix at each timestamp.
def carbon_curve(country="de"):
    def build():
        d = _public_power(country)
        secs = d.get("unix_seconds", [])
        types = d.get("production_types", [])
        by = {}
        for i, s in enumerate(secs):
            num = den = 0.0
            for pt in types:
                f = EMIT.get(pt["name"])
                if f is None:
                    continue
                data = pt.get("data", [])
                v = data[i] if i < len(data) else None
                if v is None or v <= 0:
                    continue
                num += v * f
                den += v
            if den:
                by.setdefault(_hour_berlin(s), []).append(num / den)
        return _fill24([(sum(by[h]) / len(by[h]) if by.get(h) else None) for h in range(24)])
    return _cached("carbon_curve_" + country, build)


# real national generation mix as wind / solar / other fractions (~sum 1).
def power_mix(country="de"):
    def build():
        d = _public_power(country)
        agg = {}
        for pt in d.get("production_types", []):
            vals = [v for v in pt.get("data", []) if v is not None and v > 0]
            agg[pt["name"]] = (sum(vals) / len(vals)) if vals else 0.0
        wind = agg.get("Wind onshore", 0) + agg.get("Wind offshore", 0)
        solar = agg.get("Solar", 0)
        gen = ["Hydro Run-of-River", "Biomass", "Fossil brown coal / lignite", "Fossil hard coal",
               "Fossil oil", "Fossil coal-derived gas", "Fossil gas", "Geothermal",
               "Hydro water reservoir", "Hydro pumped storage", "Others", "Waste",
               "Wind offshore", "Wind onshore", "Solar"]
        total = sum(agg.get(t, 0) for t in gen)
        if total <= 0:
            return {"wind": 0.2, "solar": 0.2, "other": 0.6}
        w, s = wind / total, solar / total
        return {"wind": round(w, 2), "solar": round(s, 2), "other": round(max(0.0, 1 - w - s), 2)}
    return _cached("powermix_" + country, build)


def _voltage_kv(tag):
    if not tag:
        return 20.0  # assume distribution-level if untagged
    best = 0.0
    for part in str(tag).replace(",", ";").split(";"):
        try:
            v = float(part.strip())
            best = max(best, v)
        except ValueError:
            pass
    return (best / 1000.0) if best else 20.0


# query overpass once per region (each selector gets the region bbox), union, yield (lat, lon, tags).
def _overpass_each(selectors):
    for name, (s, w, n, e) in REGIONS.items():
        bb = "(%f,%f,%f,%f)" % (s, w, n, e)
        body = "".join("%s%s;" % (sel, bb) for sel in selectors)
        q = '[out:json][timeout:160];(%s);out center;' % body
        d = _get_json(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), timeout=180)
        for el in d.get("elements", []):
            c = el.get("center", {})
            lat = el.get("lat", c.get("lat"))
            lon = el.get("lon", c.get("lon"))
            if lat is not None and lon is not None:
                yield round(lat, 4), round(lon, 4), el.get("tags", {})


# ---- spatial: substations across all regions [lat, lon, kv], deduped on coordinate ----
def substations():
    def build():
        seen = {}
        for lat, lon, tags in _overpass_each(['nwr["power"="substation"]']):
            seen[(lat, lon)] = [lat, lon, _voltage_kv(tags.get("voltage"))]
        return list(seen.values())
    return _cached("substations", build, ttl=TTL_OSM)


# derived (no network): transmission-level substations only (>=110 kV), memoized like a feed.
def substations_hv():
    return _cached("substations_hv", lambda: [s for s in substations() if s[2] >= 110.0], ttl=TTL_OSM)


# ---- spatial: heat off-takers across all regions [lat, lon, weight], deduped on coordinate ----
# hospitals + greenhouses + public baths = plausible buyers of waste heat. (private pools excluded: too noisy.)
def heat_buyers():
    def build():
        sels = ['nwr["amenity"="hospital"]', 'nwr["landuse"="greenhouse_horticulture"]',
                'nwr["leisure"="water_park"]', 'nwr["amenity"="public_bath"]']
        wmap = {"hospital": 3.0, "greenhouse_horticulture": 2.0, "water_park": 2.0, "public_bath": 2.0}
        seen = {}
        for lat, lon, t in _overpass_each(sels):
            kind = t.get("amenity") or t.get("landuse") or t.get("leisure")
            seen[(lat, lon)] = [lat, lon, wmap.get(kind, 1.0)]
        return list(seen.values())
    return _cached("heat_buyers", build, ttl=TTL_OSM)


import re

# categorize an OSM plant/generator source into wind / solar / hydro / other (battery is storage, skip).
def _gen_cat(src):
    s = (src or "").lower()
    if "wind" in s:
        return "wind"
    if "solar" in s or "photovoltaic" in s:
        return "solar"
    if "hydro" in s:
        return "hydro"
    if "battery" in s or "storage" in s:
        return None
    return "other"


# parse an OSM power-output tag ("50 MW", "1.5 MW", "100 kW", "500 W", "2.3 MWp") -> MW. None if unparseable.
def _parse_mw(s):
    if not s:
        return None
    m = re.match(r"([0-9.]+)\s*([kKmMgG]?)[wW]", str(s).replace("p", "").strip())
    if not m:
        return None
    mult = {"": 1e-6, "k": 1e-3, "m": 1.0, "g": 1000.0}[m.group(2).lower()]
    try:
        return float(m.group(1)) * mult
    except ValueError:
        return None


# typical capacity (MW) when a plant has no output tag — rough, so MW totals are populated not blank.
_DEF_MW = {"wind": 2.5, "solar": 1.0, "hydro": 0.6, "other": 4.0}


# ---- spatial: power generation nearby [lat, lon, category, mw]. plants (farms) + wind/hydro generators.
# individual rooftop solar (generator:source=solar) is excluded as noise; solar comes from solar farms (plants).
def generators():
    def build():
        sels = ['nwr["power"="plant"]["plant:source"]',
                'nwr["generator:source"="wind"]', 'nwr["generator:source"="hydro"]']
        seen = {}
        for lat, lon, t in _overpass_each(sels):
            cat = _gen_cat(t.get("plant:source") or t.get("generator:source"))
            if not cat:
                continue
            mw = _parse_mw(t.get("plant:output:electricity") or t.get("generator:output:electricity"))
            seen[(lat, lon)] = [lat, lon, cat, round(mw if mw else _DEF_MW[cat], 3)]
        return list(seen.values())
    return _cached("generators", build, ttl=TTL_OSM)
