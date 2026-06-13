# microdc-hub backend — sitescore data + earnmax endpoints
import json, os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .optimizer import recommend
from .telemetry import monitor
from .scoring import score_collection, build_weights
from . import score_plz, solar
from .factors import carbon as carbon_f

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data", "nodes.geojson")

app = FastAPI(title="microdc-hub backend")
# open cors so the static frontend can call us during the hackathon
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# load the scored nodes at startup, and hot-reload whenever the file is rebuilt (scheduled refresh).
NODES = {"type": "FeatureCollection", "features": []}
INDEX = {}
_DATA_MTIME = 0.0


def _maybe_reload():
    global NODES, INDEX, _DATA_MTIME
    try:
        m = os.path.getmtime(DATA)
    except OSError:
        return
    if m == _DATA_MTIME:
        return
    with open(DATA, encoding="utf-8") as f:
        NODES = json.load(f)
    INDEX = {ft["properties"]["plz"]: ft for ft in NODES["features"] if ft["properties"].get("plz")}
    _DATA_MTIME = m


_maybe_reload()

# test switch: set MICRODC_ZERO=1 (env) or pass ?zero=1.
# in test mode every subscore starts at 0 and increases by 1 on each /nodes call,
# so each frontend reload ticks the whole map up one step (red -> green) — proof it's reading the backend live.
ZERO_ENV = os.getenv("MICRODC_ZERO") in ("1", "true", "True")
COUNTER = 0


def _ramp(fc):
    global COUNTER
    v = min(100, COUNTER)
    feats = []
    for ft in fc["features"]:
        p = dict(ft["properties"])
        p["sub"] = {"grid": v, "price": v, "carbon": v, "flex": v, "heat": v}
        feats.append({"type": "Feature", "geometry": ft["geometry"], "properties": p})
    COUNTER += 1
    return {"type": "FeatureCollection", "features": feats}


# live scoring: recompute subscores from the factor providers on every call (currently random
# placeholders), keeping the tile geometry from the loaded file. each request returns fresh values.
def _live_collection():
    plz_list = [ft["properties"]["plz"] for ft in NODES["features"] if ft["properties"].get("plz")]
    raw = score_plz.raw_table(plz_list)              # one draw per factor per plz
    subs = score_plz.normalize_all(raw)             # -> 0-100 subscores
    feats = []
    for ft in NODES["features"]:
        p = dict(ft["properties"])
        code = p.get("plz")
        if code in subs:
            p["sub"] = subs[code]
            p["price_eur_mwh"] = int(round(raw["price"][code]))
            p["carbon_g_kwh"] = int(round(raw["carbon"][code]))
            p["carbon_band"] = carbon_f.band(raw["carbon"][code])
        feats.append({"type": "Feature", "geometry": ft["geometry"], "properties": p})
    return {"type": "FeatureCollection", "features": feats}


@app.get("/health")
def health():
    _maybe_reload()
    return {"ok": True, "nodes": len(NODES["features"]), "test_mode": ZERO_ENV, "counter": COUNTER}


@app.get("/reset")
def reset():
    global COUNTER
    COUNTER = 0
    return {"ok": True, "counter": COUNTER}


# force a re-read of nodes.geojson (called by the scheduled refresh after it rebuilds the file).
@app.get("/reload")
def reload():
    global _DATA_MTIME
    _DATA_MTIME = 0.0
    _maybe_reload()
    return {"ok": True, "nodes": len(NODES["features"])}


# sitescore: serve scored postal-code nodes.
# pass capacity/shiftable to have the backend build the dynamic weights and attach a composite `score`;
# omit them and you just get the raw subscores (frontend can still score client-side).
@app.get("/nodes")
def nodes(plz: Optional[str] = None, kw: Optional[int] = None, zero: bool = False,
          capacity: Optional[str] = None, shiftable: float = 0.5, live: bool = False):
    _maybe_reload()
    if live:
        data = _live_collection()
    else:
        data = _ramp(NODES) if (zero or ZERO_ENV) else NODES
    if plz:
        match = [ft for ft in data["features"] if ft["properties"].get("plz") == plz]
        if not match:
            raise HTTPException(404, "plz not found")
        data = {"type": "FeatureCollection", "features": match}
    if capacity is not None:
        return score_collection(data, capacity=capacity, shiftable=shiftable)
    return data


# best rooftop-solar buildings in a postal code (Google Solar API). needs GOOGLE_SOLAR_API_KEY.
@app.get("/solar-sites/{plz}")
def solar_sites(plz: str, n: int = 3):
    _maybe_reload()
    if plz not in INDEX:
        raise HTTPException(404, "plz not found")
    key = os.getenv("GOOGLE_SOLAR_API_KEY")
    if not key:
        raise HTTPException(503, "GOOGLE_SOLAR_API_KEY not set on the backend")
    ring = INDEX[plz]["geometry"]["coordinates"][0]   # [[lon, lat], ...]
    lons = [c[0] for c in ring]
    lats = [c[1] for c in ring]
    bbox = (min(lats), min(lons), max(lats), max(lons))   # s, w, n, e — the postal-code box
    return {"plz": plz, "sites": solar.rank_sites(bbox, key, n=n)}


# inspect the dynamic weight mix for a given case (capacity + shiftable), without the node payload.
@app.get("/score")
def score(capacity: str = "container", shiftable: float = 0.5):
    return {"capacity": capacity.lower(), "shiftable": shiftable, "weights": build_weights(capacity, None, shiftable)}


# earnmax: 24h price/carbon forecast + recommended load profile + value stack
@app.get("/forecast/{plz}")
def forecast(plz: str, kw: int = 30, shiftable: float = 0.6):
    if plz not in INDEX:
        raise HTTPException(404, "plz not found")
    return recommend(plz, kw, shiftable)


# earnmax: synthetic live telemetry for the monitoring card
@app.get("/monitor/{plz}")
def monitor_ep(plz: str):
    if plz not in INDEX:
        raise HTTPException(404, "plz not found")
    return monitor(plz)
