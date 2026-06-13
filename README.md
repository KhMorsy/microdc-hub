# MicroDC Hub

**Where should we build a micro data center, how do we power it, and how do we run it?**
A siting, supply-planning and operations tool for small flexible data centers across **Bavaria and Austria**, scored per postal code on live energy, grid, and generation data.

> Compute that follows power, not power that chases compute.

Built for the Invertix "Data-Center Siting & Power" track. The binding constraint on new data centers is no longer GPUs, it is electricity: price, carbon, grid headroom, local clean energy, and connectivity. MicroDC Hub turns that multi-way trade-off into one map, one score, and a supply plan you can act on.

---

## The product — one flow, four screens

The app is a small multi-page website. You move forward and back, and every page has a **Home** button.

```
start.html      Home / input  ── pick size, optimize goal, radius, postal code
   │  Build my supply mix →
supply.html     Supply mix    ── grid / PPA / on-site blend, cost & carbon, confirm
   │  Confirm & open the map →
sitescore.html  The map       ── every postal code scored 0–100, drill into a site
   │  Open EarnMax →
earnmax.html    EarnMax        ── 24h day-ahead plan, value stack, monitoring
```

1. **Input** — your data center size (Edge → Campus), whether you optimize for greenness / price / both, a service radius, and optionally a postal code.
2. **Supply mix** — auto-builds a grid / PPA / on-site blend tuned to your goal, with a **location-real cost** (the PPA leg uses the site's local PPA price) and carbon. You adjust the sliders, see the cost estimate, and confirm.
3. **The map** — every Bavarian and Austrian postal code scored 0–100. Pick a capacity, weight the factors, highlight the top 1/5/10, jump to the best site, and drill into any postal code for its full breakdown.
4. **EarnMax** — the daily operating plan: a 24h price/carbon forecast with a recommended load profile (run heavy work in the cheap, clean hours), a value stack, and a monitoring card.

---

## The scoring model

The SiteScore composite is a weighted sum of **six** subscores, each normalized 0–100 across all postal codes:

| Factor | What it measures | Source |
|---|---|---|
| **Grid headroom** | proximity to substations you can connect to, capacity-aware | OpenStreetMap |
| **Price** | wholesale day-ahead electricity price | Energy-Charts |
| **Carbon** | grid carbon intensity from the live generation mix | Energy-Charts |
| **Flexibility** | daily price spread (upside from shifting load) | Energy-Charts |
| **Heat reuse** | proximity to heat buyers (hospitals, greenhouses, pools) | OpenStreetMap |
| **Clean energy** | count of clean-energy sources nearby (wind + solar + hydro) | OpenStreetMap |

**One equation, dynamic weights.** The formula never changes; the weights adapt to everything you tell it:

- **Capacity class** (Edge … Campus) sets the base weights.
- **Grid headroom is capacity-aware** — the substation voltage that counts follows the class: Edge plugs into the everywhere medium-voltage grid; Campus needs sparse high-voltage transmission. So the same site scores differently for different sizes.
- **Optimize goal** tilts the weights: *green* raises carbon + clean energy; *price* raises price.
- **Supply mix** tilts them too: a PPA / on-site-heavy plan raises carbon + clean; a grid-heavy plan raises grid headroom + price.
- **Shiftable share** scales the flexibility weight.
- The six map sliders are a live manual override — change any and the whole map re-scores.

Normalization is by **percentile rank**, so a few sites on dense infrastructure do not squash the rest and the map spreads evenly red to green.

### A note on what varies and what does not

Germany and Austria are **two separate bidding zones** (DE-LU and AT). So price, carbon, and flexibility are uniform *within* a zone but differ *between* them (Bavaria is cheaper, Austria far cleaner). The genuinely per-postal-code factors are **grid, heat, and clean energy**. Adding regions in further bidding zones makes price/carbon differentiate automatically.

---

## What is real vs synthetic

Honesty matters when a judge pokes at the numbers.

| Data | Status |
|---|---|
| Price, carbon, flexibility | **Real** (Energy-Charts live day-ahead + generation mix) |
| Grid headroom | **Real proxy** (OSM substations, capacity-aware). See caveat. |
| Heat reuse | **Real** (OSM heat buyers) |
| Clean-energy factor + local generation table | **Real** (OSM power plants; capacities partly tagged, partly estimated) |
| Local PPA price | **Real-derived** (weighted by local renewable mix; per-tech prices are assumptions) |
| EarnMax forecast (price + carbon curves) | **Real** (Energy-Charts day-ahead) |
| Best rooftop solar sites | **Real** (Google Solar API, live per building) |
| EarnMax value-stack euros / supply-mix PPA & on-site costs | Illustrative, labeled |
| EarnMax monitoring card | **Synthetic** (a live site's telemetry comes from its own BMS, no public source) |
| Tile shapes | Voronoi cells around postal-code centroids (approximate) |

**Grid caveat:** the grid factor measures *infrastructure access* (is there a substation nearby), not *spare capacity* (is it congested). True spare capacity needs solved grid-flow data (PyPSA-Eur) — the proprietary layer.

---

## Quickstart

Requires Python 3.9+ and Node 18+ (Node only for the standalone solar script; the app itself is Python + static HTML).

**1. Backend (FastAPI on :8000)**
```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
For the "Solar roofs" feature, start it with a Google Solar API key (optional):
```
GOOGLE_SOLAR_API_KEY="your-key" uvicorn app.main:app --port 8000
```

**2. Frontend (serve over http so the localhost fetch works)**
```
cd frontend
python3 -m http.server 5500
# then open http://localhost:5500/start.html
```

**3. Rebuild the scored data (optional — the repo ships with it baked)**
```
cd backend/pipeline
python build_geojson.py
```
The first build fetches the live feeds (Energy-Charts prices/carbon, OSM substations / heat buyers / power plants) and caches them; later runs are fast.

That is it — open `http://localhost:5500/start.html` and walk the flow.

---

## Features

- **Per-postal SiteScore** (0–100) across 4,256 Bavarian + Austrian postal codes, 6 factors, dynamic weights.
- **Capacity classes** Edge / Micro / Container / Small / Campus, with capacity-aware grid headroom.
- **Optimize for** greenness / price / both — auto-tilts the weights.
- **Supply-mix planner** — grid / PPA / on-site blend with location-real cost (per-postal PPA price) and carbon, a cost estimate, and a confirm-to-map step.
- **Local generation table** — wind / solar / hydro / other within 4 km, shown three ways: plant count, capacity (MW), and estimated generation (MWh/yr).
- **EarnMax** — 24h day-ahead price/carbon plan, recommended load profile, value stack, monitoring.
- **Top 1 / 5 / 10 highlight** — outline the best-scoring postal codes.
- **Jump to best site** — fly to the #1 ranked postal code under your current weights.
- **Best rooftop solar** — for a selected postal code, the top 3 buildings by Google Solar potential, plotted on the map (inside the postal-code box).
- **Two regions** — Bavaria (DE-LU) and Austria (AT), with real cross-border price/carbon differences.
- **Scheduled refresh** — keeps prices/carbon current (see below).

---

## API

| Endpoint | What it returns |
|---|---|
| `GET /health` | status, node count |
| `GET /nodes` | scored postal-code nodes (GeoJSON). `?plz=`, `?capacity=`, `?shiftable=` |
| `GET /score` | the dynamic weight mix for a given capacity and shiftable |
| `GET /forecast/{plz}` | 24h price/carbon plan, recommended load, value stack. `?kw=`, `?shiftable=` |
| `GET /monitor/{plz}` | telemetry for the monitoring card (synthetic) |
| `GET /solar-sites/{plz}` | top rooftop-solar buildings in the postal code (needs `GOOGLE_SOLAR_API_KEY`). `?n=` |
| `GET /reload` | force a re-read of the baked data |

---

## Project structure

```
frontend/
  start.html            input / home page (the front door)
  supply.html           grid / PPA / on-site supply-mix planner
  sitescore.html        the scored map (Leaflet)
  earnmax.html          24h day-ahead operating plan
  DATA_CONTRACT.md      the GeoJSON schema the frontend expects
  demo.geojson          fallback data if the backend is down

backend/
  app/
    main.py             FastAPI endpoints + hot-reload
    scoring.py          the equation: dynamic weights + composite
    score_plz.py        per-postal scorer + percentile-rank normalization
    optimizer.py        EarnMax forecast + greedy load shifting (real day-ahead)
    telemetry.py        EarnMax monitoring (synthetic)
    solar.py            rooftop-solar ranking via Google Solar API
    factors/
      sources.py        live data fetch + cache (Energy-Charts, OSM Overpass)
      zones.py          postal code -> bidding zone (DE-LU / AT)
      grid.py price.py carbon.py flex.py heat.py
                        one provider per scoring input
      geo.py            centroid + distance helpers
  pipeline/
    build_geojson.py    walk every postal code, score, bake nodes.geojson
    build_austria_tiles.py  add Austria's tiles (Voronoi from GeoNames centroids)
    inputs/             plz centroids, region boundaries, geonames data
  data/
    nodes.geojson       the scored data the API serves
```

The clean seam: each factor is one `value(plz)` function and each feed is one function in `sources.py`. To swap a data source you change one function body; the schema, scorer, and frontend stay put.

---

## Scheduled refresh (optional)

A launchd job rebuilds the data every 30 minutes so prices and carbon stay current; the backend hot-reloads the rebuilt file with no restart.

- Script: `backend/pipeline/refresh.sh`
- Agent: load `com.microdc.refresh.plist` into `~/Library/LaunchAgents`, then `launchctl load -w <plist>`
- National feeds refresh every 30 min; OSM feeds are cached weekly.

---

## Adding another region

The architecture is region-ready. Austria was added with three steps, and any further region follows the same path:

1. **Tiles + centroids** — postal-code centroids (e.g. from GeoNames) and a boundary; `build_austria_tiles.py` shows the pattern (Voronoi clipped to the boundary).
2. **OSM coverage** — add the region's bounding box to `REGIONS` in `sources.py`.
3. **Zone mapping** — map its postal codes to a bidding zone in `zones.py`.

Pick a region in a *different* bidding zone and price/carbon differentiate automatically.

---

## Known limitations (honest)

- **Grid = infrastructure access, not congestion.** Dense cities score high even if their grid is full. True headroom needs PyPSA-Eur line loading.
- **Local generation capacities are partly estimated.** ~3/4 of OSM plants carry a real capacity tag; the rest use a typical default. Counts are exact, MW/MWh are estimates. The official German registry (MaStR) would remove the guessing.
- **EarnMax monitoring is synthetic** — that data only exists once a real site's sensors are live.
- **PPA prices and on-site costs are illustrative** — labeled as such; grid price/carbon are real.
- **Tiles are Voronoi approximations**, not official postal-code boundaries.

---

## Roadmap

- Grid congestion via solved PyPSA-Eur flows (replace the access proxy).
- Time-to-power: express grid headroom as a connection date.
- Swap OSM plant capacities for the official MaStR / OPSD registries.
- Cap the supply-mix PPA leg by the local renewable availability.
- More regions in more bidding zones.

---

See `PROJECT_BRIEF.md` for the full intent, domain notes, business model, and pitch.
