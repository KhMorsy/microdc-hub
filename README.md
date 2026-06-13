# MicroDC Hub

**Where should we build a micro data center, and how do we power it?**
A siting and operations tool for small, flexible data centers in Bavaria, scored per postal code on live energy and grid data.

> Compute that follows power, not power that chases compute.

Built for the Invertix "Data-Center Siting & Power" track. The binding constraint on new data centers is no longer GPUs, it is electricity: price, carbon, grid headroom and connectivity. MicroDC Hub turns that multi-way trade-off into one map and one number you can reason about.

---

## The two products

**SiteScore** answers *where and what to build*. A map that scores every Bavarian postal code 0 to 100 on five factors, with a detail panel and what-if boosts. You pick a capacity class (Edge to Campus) and weight the factors to your priorities.

**EarnMax** answers *how to run it for maximum value*. A 24 hour day-ahead plan that shows when power is cheap and clean, a recommended load profile, and a daily value stack (arbitrage, peak shaving, heat reuse, certificates) net of the subscription.

The pitch in one line: **Decide once with SiteScore. Earn every day with EarnMax.**

---

## The scoring model

The SiteScore composite is a weighted sum of five subscores, each normalized 0 to 100 across all postal codes:

| Factor | What it measures | Source |
|---|---|---|
| **Grid headroom** | proximity to substations you can connect to, capacity-aware | OpenStreetMap |
| **Price** | wholesale day-ahead electricity price | Energy-Charts |
| **Carbon** | grid carbon intensity from the live generation mix | Energy-Charts |
| **Flexibility** | daily price spread (upside from shifting load) | Energy-Charts |
| **Heat reuse** | proximity to heat buyers (hospitals, greenhouses, pools) | OpenStreetMap |

Rules that matter:

- **One fixed equation, dynamic weights.** The formula never changes; the weights adapt to the case. Transparent: one number to decide, five to explain.
- **Capacity presets** set the starting weights. A tiny Edge box barely strains the grid so heat and flexibility lead; a Campus load lives or dies on grid headroom, so it dominates.
- **Grid headroom is capacity-aware.** The substation voltage that counts follows the class: Edge connects to the everywhere medium-voltage grid, Campus needs sparse high-voltage transmission. So the same location scores differently depending on what you want to build.
- **Shiftable share** scales the flexibility weight, then everything renormalizes to sum to 1.
- **Normalization is by percentile rank**, so a few sites on dense infrastructure do not squash the rest, and the map spreads evenly red to green.

### A note on what varies and what does not

Germany is a single electricity bidding zone (DE-LU). So price, carbon and flexibility are the **same everywhere in Bavaria**. They are real, but they do not rank sites against each other, so they sit at a neutral 50 and the map differentiates on **grid and heat** (the genuinely spatial factors). The architecture is built to add regions in other bidding zones, at which point price and carbon become real spatial signals automatically.

---

## What is real vs synthetic

Honesty matters when a judge pokes at the numbers.

| Data | Status |
|---|---|
| Price, carbon, flexibility | **Real** (Energy-Charts, live day-ahead and generation mix) |
| Grid headroom | **Real proxy** (OSM substations, capacity-aware). See caveat below. |
| Heat reuse | **Real** (OSM heat buyers) |
| Power mix donut | **Real** (national generation mix) |
| EarnMax forecast (price and carbon curves) | **Real** (Energy-Charts day-ahead) |
| EarnMax value stack euros | Illustrative, top of range |
| EarnMax monitoring card | **Synthetic** (a site's live telemetry comes from its own BMS, no public source) |
| Tile shapes | Voronoi cells around postal-code centroids (approximate, not official boundaries) |

**Grid caveat:** the grid factor measures *infrastructure access* (is there a substation nearby I can connect to), not *spare capacity* (is it congested). A highway is nearby, but we do not know if it is jammed. True spare capacity needs solved grid-flow data (PyPSA-Eur), which is the proprietary layer.

---

## Quickstart

Requires Python 3.9+.

**1. Backend (FastAPI on :8000)**
```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

**2. Frontend (serve over http so the localhost fetch works)**
```
cd frontend
python3 -m http.server 5500
# then open http://localhost:5500/sitescore.html
```

**3. Rebuild the scored data (fetches live feeds, bakes nodes.geojson)**
```
cd backend/pipeline
python build_geojson.py
```
The first build fetches the energy feeds and the OSM substations/heat buyers (about a minute), then caches them. Re-running is fast.

---

## Scheduled refresh (optional)

A launchd job can rebuild the data every 30 minutes so prices and carbon stay current. The backend hot-reloads the rebuilt file with no restart.

- Script: `backend/pipeline/refresh.sh`
- Agent: load `com.microdc.refresh.plist` into `~/Library/LaunchAgents`, then `launchctl load -w <plist>`
- Stop: `launchctl unload <plist>`

National feeds refresh every 30 minutes; OSM feeds are cached weekly (they barely change).

---

## API

| Endpoint | What it returns |
|---|---|
| `GET /health` | status, node count |
| `GET /nodes` | scored postal-code nodes (GeoJSON). `?plz=`, `?capacity=`, `?shiftable=` |
| `GET /score` | the dynamic weight mix for a given capacity and shiftable |
| `GET /forecast/{plz}` | 24h price and carbon plan, recommended load, value stack. `?kw=`, `?shiftable=` |
| `GET /monitor/{plz}` | telemetry for the monitoring card (synthetic) |
| `GET /reload` | force a re-read of the baked data |

---

## Project structure

```
frontend/
  sitescore.html        the SiteScore map (Leaflet, single file)
  earnmax.html          the EarnMax day-ahead plan + value stack
  DATA_CONTRACT.md      the GeoJSON schema the frontend expects
  demo.geojson          fallback data if the backend is down

backend/
  app/
    main.py             FastAPI endpoints + hot-reload
    scoring.py          the equation: dynamic weights + composite
    score_plz.py        per-postal-code scorer + rank normalization
    optimizer.py        EarnMax forecast + greedy load shifting
    telemetry.py        EarnMax monitoring (synthetic)
    factors/
      sources.py        live data fetch + cache (Energy-Charts, OSM)
      zones.py          postal code -> bidding zone (extension point for new regions)
      grid.py price.py carbon.py flex.py heat.py
                        one provider per scoring input
      geo.py            centroid + distance helpers
  pipeline/
    build_geojson.py    walk every postal code, score, bake nodes.geojson
  data/
    nodes.geojson       the scored data the API serves
```

The clean seam: each factor is one `value(plz)` function. To swap a data source you change one function body; the schema, scorer and frontend stay put.

---

## Roadmap

- **Supply-mix planner** (grid / PPA / on-site against cost and carbon)
- **Grid congestion** via solved PyPSA-Eur flows, replacing the access proxy
- **Multi-region**: add a region in another bidding zone so price and carbon differentiate
- **Time-to-power**: express grid headroom as a connection date
- Official postal-code polygons instead of Voronoi tiles

---

See `PROJECT_BRIEF.md` for the full intent, domain notes, business model and pitch.
