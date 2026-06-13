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
BAV = (47.2, 8.9, 50.6, 13.9)   # bavaria bbox: south, west, north, east

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


# ---- spatial: substations across bavaria [lat, lon, kv] ----
def substations():
    def build():
        s, w, n, e = BAV
        q = '[out:json][timeout:160];nwr["power"="substation"](%f,%f,%f,%f);out center;' % (s, w, n, e)
        d = _get_json(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), timeout=180)
        out = []
        for el in d.get("elements", []):
            c = el.get("center", {})
            lat = el.get("lat", c.get("lat"))
            lon = el.get("lon", c.get("lon"))
            if lat is None or lon is None:
                continue
            out.append([round(lat, 4), round(lon, 4), _voltage_kv(el.get("tags", {}).get("voltage"))])
        return out
    return _cached("substations", build, ttl=TTL_OSM)


# derived (no network): transmission-level substations only (>=110 kV), memoized like a feed.
def substations_hv():
    return _cached("substations_hv", lambda: [s for s in substations() if s[2] >= 110.0], ttl=TTL_OSM)


# ---- spatial: heat off-takers across bavaria [lat, lon, weight] ----
# hospitals + greenhouses + public baths = plausible buyers of waste heat. (private pools excluded: too noisy.)
def heat_buyers():
    def build():
        s, w, n, e = BAV
        bb = "(%f,%f,%f,%f)" % (s, w, n, e)
        q = ('[out:json][timeout:160];('
             'nwr["amenity"="hospital"]%s;'
             'nwr["landuse"="greenhouse_horticulture"]%s;'
             'nwr["leisure"="water_park"]%s;'
             'nwr["amenity"="public_bath"]%s;'
             ');out center;') % (bb, bb, bb, bb)
        d = _get_json(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), timeout=180)
        wmap = {"hospital": 3.0, "greenhouse_horticulture": 2.0, "water_park": 2.0, "public_bath": 2.0}
        out = []
        for el in d.get("elements", []):
            c = el.get("center", {})
            lat = el.get("lat", c.get("lat"))
            lon = el.get("lon", c.get("lon"))
            if lat is None or lon is None:
                continue
            t = el.get("tags", {})
            kind = t.get("amenity") or t.get("landuse") or t.get("leisure")
            out.append([round(lat, 4), round(lon, 4), wmap.get(kind, 1.0)])
        return out
    return _cached("heat_buyers", build, ttl=TTL_OSM)
