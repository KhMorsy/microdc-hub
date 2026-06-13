# Implementation Plan — MicroDC Hub (SiteScore + EarnMax)

Two products under **MicroDC Hub**, one stack. **SiteScore**: one-time siting report — scored postal-code (PLZ) areas on a map. **EarnMax**: yearly subscription — operations co-pilot showing *extra* earnings vs. unmanaged operation. Node resolution = **one PLZ polygon** (~8,200 in DE), not city level.

## Architecture

```
Offline (Python, pre-demo)              Live (demo)
─────────────────────────              ─────────────────────────────
raw datasets ──► ETL/scoring ──► plz_nodes.geojson ──► FastAPI ──► React/Vite
                              └► profiles.parquet      │  /nodes      MapLibre (SiteScore map)
                                 synthetic telemetry ──┘  /forecast   Recharts (EarnMax dashboard)
                                                          /monitor
```

Principles: all heavy data work precomputed offline; live stack = static files + 3 read endpoints + rule-based optimizer; demo works offline once data is local. No DB, no auth, no ML training.

## Data contracts (agree on these FIRST — they unblock all parallel work)

### `plz_nodes.geojson` — one Feature per PLZ
```json
{ "type": "Feature",
  "geometry": { "...": "PLZ polygon (simplified, <50 KB/feature)" },
  "properties": {
    "plz": "80933", "name": "München-Feldmoching",
    "score": 82,
    "sub": { "grid": 90, "price": 74, "carbon": 88, "flex": 79, "heat": 65 },
    "mix": { "wind": 0.38, "solar": 0.27, "grid": 0.35 },
    "carbon_g_kwh": 142, "carbon_band": "low",
    "boost": { "battery_20kwh": 6, "resize_30kw": 3 }
  } }
```
Composite score = weighted sum: grid 30%, price 25%, carbon 20%, flex 15%, heat 10%. Weights in `config.json`, not code. Boost toggles re-score client-side using `boost` deltas.

### `GET /nodes?kw=30&plz=80933` → GeoJSON above, filtered/recentered. `kw` selects the capacity-class default weights.
### `GET /forecast/{plz}` → `{ "hours": [{ "t": "2026-06-13T10:00", "price_eur_mwh": 62, "carbon_g_kwh": 138, "load_kw_recommended": 27 }, ...24] , "value_today_eur": { "arbitrage": 31, "peak_shaving": 12, "heat": 9, "certificates": 4 } }`
### `GET /monitor/{plz}` → `{ "thermal_headroom_pct": 71, "power_kw": 24.1, "power_limit_kw": 30, "inlet_c": 26.4, "alerts": [{ "from": "14:00", "to": "16:00", "action": "reduce load 15%", "reason": "thermal limit" }] }`

## Datasets and sources (all free)

| Dataset | Source | Used for | Fetch |
|---|---|---|---|
| PLZ polygons (~8,170) | [suche-postleitzahl.org](https://www.suche-postleitzahl.org/downloads) (OSM-derived, ODbL) | Node geometry | One GeoJSON download; simplify with `shapely`/`mapshaper` |
| Installed PV/wind per PLZ | Marktstammdatenregister (MaStR) bulk export, [marktstammdatenregister.de](https://www.marktstammdatenregister.de) | `mix`, flex + carbon subscores | CSV/XML bulk download, aggregate kW per PLZ |
| Day-ahead prices, hourly generation mix | [SMARD.de](https://www.smard.de) CSV export (or ENTSO-E Transparency API) | `profiles.parquet`, price/flex subscores, EarnMax forecast | 1 year hourly CSV, DE-LU zone |
| Carbon intensity | Ember yearly DE figure + hourly profile derived from SMARD mix | `carbon_g_kwh`, carbon subscore, green windows | Derived in ETL |
| Grid headroom proxy | PyPSA-Eur network (line loading near node) + OSM `power=substation` distance via Overpass | `grid` subscore | Precomputed once; fallback: substation-distance-only heuristic |
| Heat-demand POIs | OSM Overpass: `leisure=swimming_pool`, `landuse=greenhouse_horticulture`, large `building` footprints per PLZ | `heat` subscore | One Overpass query per region, cached JSON |
| Weather/renewables forecast | [Open-Meteo](https://open-meteo.com) free API | EarnMax 24h forecast flavor | Live call or cached response (demo-safe) |
| Telemetry | Synthetic generator (sine + noise + scripted 14:00 thermal event) | `/monitor` | Generated in backend |

Demo scope: Germany only; if time is short, restrict polygons/scores to Bayern (~2,000 PLZ) — contract unchanged.

## Workstreams (parallel sub-agents; sync points marked)

**WS1 — Data pipeline (Python/pandas), owns the GeoJSON.**
1. Download PLZ polygons + MaStR + SMARD CSVs; simplify polygons. *Verify: file sizes sane, ~8k features.*
2. Compute 5 subscores per PLZ (formulas above; min-max normalize 0–100), composite, mix, carbon band, boost deltas. *Verify: spot-check 80933 plausible; score histogram not degenerate.*
3. Emit `plz_nodes.geojson` + `profiles.parquet` (hourly price/carbon, 1 year). **Sync: hand contract-valid sample (5 PLZ) to WS2/WS3 within first hour; full file later — same schema.**

**WS2 — Backend (FastAPI).**
1. Scaffold `api/`: serve the 3 endpoints from static files; CORS on. *Verify: `curl` each endpoint matches contract.*
2. Greedy optimizer: sort next-24h hours by `price × carbon weight`, fill shiftable load (e.g. 60% of capacity) into cheapest-greenest hours within thermal limit → `load_kw_recommended` + €-value split. *Verify: recommended load is low during price peak.*
3. Synthetic telemetry generator with scripted 14:00–16:00 alert. *Verify: `/monitor` shows alert.*
   Until WS1 delivers: code against the 5-PLZ sample committed in repo.

**WS3 — Frontend: SiteScore (React + Vite + MapLibre GL).**
1. Scaffold app, dark theme tokens (bg #0d0a07, accent #E8742C), routing: `/site` and `/earnmax`. **Sync: theme + scaffold shared with WS4 at hour 1.**
2. Map with PLZ polygon fill by score (green→red), score labels at zoom; left panel: capacity pills (Edge 1–5 / Micro 6–10 / Container 10–50 / Small 50–250 / Campus 250+ kW) + PLZ input → flyTo + select. *Verify: typing 80933 highlights its polygon.*
3. Node detail panel: composite, 5 subscore bars, mix donut, carbon badge; boost toggles re-score client-side from `boost` deltas. *Verify: battery toggle +6 pts updates instantly.*

**WS4 — Frontend: EarnMax dashboard (Recharts).**
1. 24h chart: price line + stepped recommended-load line + "shift batch jobs here" annotations (no renewable-share series). *Verify: matches `/forecast` data.*
2. Stat card "+€1,240 extra earnings · net +€1,040 after €200 subscription"; value-stack card from `value_today_eur`. *Verify: numbers sum.*
3. Monitoring card from `/monitor`: gauges, sparkline, amber alert. *Verify: alert renders.*

**WS5 — Integration + demo (lead, final hour).**
1. Wire FE→BE, remove sample-data fallbacks, run the 3-min demo script end-to-end twice. *Verify: no console errors, works without internet (except optional Open-Meteo).*
2. Polish: legend, loading states, deck numbers consistent with app numbers. Freeze at T-30 min.

## Timeline (5 h, 4 people + sub-agents)

| Hour | WS1 | WS2 | WS3 | WS4 |
|---|---|---|---|---|
| 0–1 | Downloads + sample GeoJSON | Scaffold + static endpoints | Scaffold + theme + map shell | (joins WS3 scaffold) |
| 1–2 | Subscores + scoring | Optimizer | Polygons rendered + PLZ search | Forecast chart |
| 2–3 | Full GeoJSON + profiles | Telemetry + alerts | Node detail panel | Stat + value-stack cards |
| 3–4 | QA data, edge cases | Contract QA | Boost toggles | Monitoring card |
| 4–5 | — Integration, rehearsal, freeze (WS5, all hands) — |

**Cut order if late:** monitoring card → boost toggles → value-stack split (keep single € number) → restrict to Bayern. Irreducible demo: PLZ map + score panel + forecast chart.

## Risks

- MaStR bulk export is bulky/fiddly → fallback: hardcode plausible mix per Bundesland from Ember; keep schema.
- Overpass rate limits → cache one regional query result in repo.
- PyPSA-Eur learning curve in 5 h is real → ship substation-distance heuristic first, upgrade only if time allows.
