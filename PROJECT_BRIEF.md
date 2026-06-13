# MicroDC Hub — full project brief

Everything decided and learned while planning this project. Hand this to any new session
so it has complete context. This is the source of truth for *intent*; the code is the source
of truth for *what's built*.

---

## 1. Context

- **Event:** Energy & AI hackathon. ~8 hours, team of 4.
- **Track:** Invertix — "Data-Center Siting & Power." (Invertix builds AI agents for renewable energy.)
- **The brief, in their words:** AI is driving a wave of new data centers; the binding constraint
  is increasingly electricity. Siting one is a multi-way trade-off between price, carbon, grid
  congestion and connectivity. Help someone reason about where to build and how to power it.
  Worth exploring: recommend locations for a given size and explain trade-offs; plan a supply mix
  of grid/PPA/on-site against cost and carbon; overlay capacity, prices, carbon and congestion to
  reveal good vs bad sites.
- **Suggested data sources:** PyPSA-Eur, Ember, OpenStreetMap, IEA Energy & AI, Google AlphaEarth.

There were 6 challenges total (Invertix siting, Invertix satellite-solar, Enerparc digital-twin,
Enerparc agents, E.ON grid-operation agents, E.ON grid foundation models). We picked the Invertix
siting track because it has the clearest judge story and the best demo potential.

---

## 2. The idea and the narrative

**Core reframe:** instead of one big data center, place a network of small (micro) data centers.
This started as an *edge / near-users* story (low-latency inference) and then shifted to the
stronger **grid-asset** story:

> "Compute that follows power, not power that chases compute."
> A flexible micro data center isn't just a load — it's a grid asset that earns money.

Why distributed micro-DCs make sense:
- A huge connection request sits in a multi-year grid queue. Small connections clear far faster.
- Small sites can go into grid-restricted areas big ones are locked out of (Frankfurt, Amsterdam,
  Dublin have effectively frozen large new loads).
- Each site can sit next to cheap, surplus renewables and a heat buyer.

**Honest limit (must address before a judge does):** big AI *training* needs co-located GPUs and
can't be naively split. *Inference* and *batch* work distribute fine. So workload type matters.
We chose to lean on the grid-asset/flexibility angle, where batch/shiftable compute is the win,
and to keep "training stays centralized" as a one-line answer if asked.

**Pitch line:** "Decide once with SiteScore. Earn every day with EarnMax."

---

## 3. The product — two packages

**SiteScore (one-time report):** "Where and what should I build?"
A map that scores every Bavarian postal code 0–100 on five factors, with a node detail panel and
"boost this site" what-ifs. This is mostly built (see §8).

**EarnMax (yearly subscription):** "How do I run it for maximum value?"
A 24h price/carbon forecast with a recommended load profile, plus an earnings/value stack and a
monitoring view. Backend endpoints exist; the frontend screen is not built yet.

Business logic: SiteScore is the paid report that funds customer acquisition; EarnMax is the
recurring revenue. Every SiteScore customer is an EarnMax lead.

---

## 4. Domain knowledge (definitions we nailed down)

- **Grid headroom (a.k.a. "grid room"):** spare capacity at a grid point to connect a NEW load.
  High headroom = you can connect, and connect soon. Low headroom = long queue or can't connect.
  This is the single most important real-world siting factor today. Weighted 30%.
- **Grid congestion:** whether existing lines are jammed with flow right now. It's an INPUT that
  *reduces* headroom. Congestion is the symptom; headroom is the decision-relevant conclusion.
- **Time-to-power:** the consequence of headroom — months (spare capacity) vs years (congested
  queue). The most decision-relevant way to express headroom. (Idea: show "~2027" or "~8 months"
  per site. Not yet built. Strong potential feature.)
- **Flexibility:** the data center's ability to shift heavy work to the cheapest/cleanest hours
  instead of running flat 24/7. As a LOCATION score it's driven by the daily price spread: big
  daily price swings = more to gain by shifting = higher flex. Weighted 15%.
- **Batch / shiftable share:** how much of the workload can wait (training, batch, rendering) vs
  must run now (live inference). Only the shiftable share benefits from flexibility. This is a
  user input (one slider: mostly real-time / mixed / mostly batch).
- **Heat reuse:** value from selling/using waste heat on premises. As a location score it's
  proximity to a heat buyer (pools, greenhouses, large buildings). Weighted 10%. Most relevant
  for small on-premises sites.
- **Capacity classes:** Edge (1–5 kW), Micro (6–10), Container (10–50), Small (50–250),
  Campus (250+ kW). These set DEFAULT weights, not data.

Where each subscore's data comes from (none from the customer — all public location data):
- grid → PyPSA-Eur line loading + substation distance
- price → SMARD / ENTSO-E zonal day-ahead prices
- carbon → Ember + SMARD generation mix
- flex → daily price spread from SMARD
- heat → OSM heat buyers (Overpass)

---

## 5. The scoring model (the heart of it)

Composite score = weighted sum of 5 subscores, each normalized 0–100:

| Subscore       | Default weight |
|----------------|----------------|
| Grid headroom  | 30%            |
| Price          | 25%            |
| Carbon         | 20%            |
| Flexibility    | 15%            |
| Heat reuse     | 10%            |

Rules that matter:
- **ONE fixed equation, DYNAMIC weights.** The weights adapt to the case (capacity, shiftable);
  the formula never changes. This keeps it transparent: "one number to decide, five to explain."
- **Capacity presets** (order: grid, price, carbon, flex, heat):
  - edge `[10,20,20,20,30]`  — tiny on-prem sites: heat/flex matter, grid barely
  - micro `[15,22,20,20,23]`
  - container `[30,25,20,15,10]`  — the demo default (matches the original plan)
  - small `[38,24,18,13,7]`
  - campus `[45,25,18,9,3]`  — big grid load: headroom dominates, heat fades
- **Shiftable input scales only the flex weight:** `flex_weight *= (0.5 + shiftable/100)`, then
  renormalize all five to sum to 1. (0% → half flex weight; 100% → 1.5× flex weight.)
- **Composite is computed on the FRONTEND** from subscores × weights. The backend only supplies
  the five subscores per node. Weights/capacity/shiftable are all client-side.
- **Boost toggles** (battery +N pts, resize +N pts) re-score the selected node client-side using
  precomputed deltas the backend supplies.

---

## 6. Business model

- **SaaS subscription** (core recurring revenue) — sell tool access to data-center developers,
  edge/colocation providers, telcos converting their sites.
- **Per-project / success fee** — siting studies that consultancies bill six figures for, over
  months; compress to a tool.
- **Data / API licensing** — the integrated, cleaned, current dataset (price+carbon+grid+heat) as
  an API for traders, ESG analysts, investors.
- **Lead-gen / origination** — the tool produces qualified data-center demand that needs clean
  power; broker PPAs / renewable developers for a fee. (This is the Invertix-aligned angle.)
- **Marketplace take** (longer-term) — be where siting turns into actual power deals; take a cut.

Pitch framing: SaaS + per-study today; data API and power-deal origination as the growth story.

---

## 7. Barriers to entry / moat (honest)

Weak (don't lean on): the UI, public data, the formula — all replicable.
Real, buildable moat:
- The integrated, cleaned, continuously-updated proprietary **data layer**.
- **Proprietary data via operator/TSO partnerships** (true connection queue times, capacity).
- **Domain trust / track record** — siting a €500M build is bet-the-company; trust is slow to
  build and hard to copy.
- **Demand-to-power flywheel** (two-sided network: developers on one side, power providers on the
  other) — the strongest structural moat, but you don't have it day one.
- **Workflow lock-in** — become the system of record for siting decisions.
Biggest real threat: a hyperscaler builds it internally, or an energy-data incumbent
(Wood Mackenzie / Enverus) adds it. Defense: move fast, own the edge/distributed niche, lock in
operator data partnerships.

---

## 8. Cost reference (for the supply-mix / EarnMax math)

Microgrid / on-site generation benchmark (NREL): roughly **$2–5M per MW** installed.
- community ~$2.1M/MW, utility ~$2.6M/MW, campus ~$3.3M/MW, commercial ~$4M/MW.
- Under 3 MW costs more per MW; 2–10 MW gets economies of scale.
- Cost split: ~30–45% energy resources, ~20% switchgear/transformers, ~10–20% controls,
  ~30% engineering/construction, 5–15% ops. Add 25–40% for install/permitting/interconnection.
- These are US$ benchmarks; European figures differ. For a grid-connected edge site (grid +
  on-site solar/battery), use the cheaper end (~€2–4M/MW of on-site capacity).

---

## 9. The build — current state

### Frontend — SiteScore map (WORKS)
Single file `frontend/sitescore.html` (Leaflet + CARTO light tiles, Manrope font, light/Airbnb
style, accent `#E0703C`). Features:
- Fits the viewport (no scroll); map panel dominates.
- **2,042 Bavaria postal-code tiles**, colored by composite score (red→green).
- Capacity pills (Edge/Micro/Container/Small/Campus) set default weights.
- Five weight sliders + a "batch/shiftable" slider (scales flex weight).
- **Per-tile score labels** appear when zoomed in (zoom ≥ 10); hidden when zoomed out.
- **Node detail panel** on click/search: composite /100, five subscore bars, power-mix donut
  (wind/solar/grid), carbon badge (low/mid/high + gCO2/kWh + €/MWh), and **boost toggles**
  (+20 kWh battery, resize) that re-score live.
- **Postal-code search**: type a 5-digit code → flies there, drops a pin, selects the tile.
- **On load it fetches `http://localhost:8000/nodes`**; if the backend isn't up it falls back to
  embedded demo data. Badge shows "LIVE · backend" (green) or "DEMO DATA".
- Canvas renderer (preferCanvas) so 2,000+ tiles stay smooth.
- "Load GeoJSON" button + "download template" for manual data swaps.

### Backend (WORKS) — `backend/`
FastAPI. Endpoints:
- `GET /health` — status, node count, test mode, counter
- `GET /nodes` (`?plz=`, `?kw=`, `?zero=`) — scored nodes GeoJSON
- `GET /forecast/{plz}?kw=&shiftable=` — 24h price/carbon + recommended load + value stack (EarnMax)
- `GET /monitor/{plz}` — synthetic telemetry + thermal alert (EarnMax)
- `GET /reset` — reset the test counter
- **Test mode** (env `MICRODC_ZERO=1` or `?zero=1`): every subscore starts at 0 and increases by
  +1 on each `/nodes` call, so each frontend reload ticks the whole map up (red→green) — a visible
  proof the map is reading the backend live, not the embedded demo.
CORS is open so the static frontend can call it.

### Pipeline — `backend/pipeline/build_nodes.py`
Builds `backend/data/nodes.geojson`. Currently:
- Tiles are **Voronoi cells around PLZ centroids clipped to Bavaria** (official PLZ polygons
  weren't reachable during the build; can be swapped for real boundaries).
- Subscores are **MOCK** (spatially generated so the map tells a coherent story: Munich/Nuremberg
  pricier + congested, alpine south cheaper + cleaner).
- TODOs at the top list which real dataset replaces each subscore (schema stays identical).

### Data contract — `frontend/DATA_CONTRACT.md` (CANONICAL)
One GeoJSON Feature per PLZ:
```
properties = {
  plz, name, centroid:[lon,lat],
  sub:{grid,price,carbon,flex,heat},   // each 0–100, normalized across all nodes
  price_eur_mwh, carbon_g_kwh, carbon_band,  // "low"/"mid"/"high"
  mix:{wind,solar,grid},               // fractions ~sum 1
  boost:{battery_20kwh, resize}        // point deltas
}
geometry = Polygon
```
**Never change this schema casually** — it's the contract between frontend and backend. The backend
supplies subscores; the frontend computes the composite.

### What's MOCK vs REAL right now
- Tile shapes: Voronoi approximations (real PLZ codes, approximate outlines).
- Subscores: mock/spatial.
- Forecast + telemetry: synthetic.
- Everything mock is marked and swappable without touching the frontend.

---

## 10. What's left to build

1. **EarnMax frontend screen** (second HTML page in `frontend/`): consume `/forecast/{plz}`
   (24h price line + recommended-load overlay, "shift batch jobs here") and `/monitor/{plz}`
   (thermal/power gauges + alert), plus a value-stack card (arbitrage / peak shaving / heat /
   certificates, minus subscription = net). Same visual style as the map.
2. **Wire real datasets** into `build_nodes.py` (replace mocks; keep schema). Priority order if
   short on time: price (SMARD) and carbon (Ember) are easiest; grid headroom is the hardest and
   most valuable (proxy with substation distance first).
3. **Link SiteScore → EarnMax**: from a selected node, open its EarnMax view.
4. **(Optional) official PLZ polygons** to replace the Voronoi tiles.
5. **(Optional) time-to-power**: express grid headroom as an estimated connection date/duration
   that reacts to the chosen capacity. Potentially the strongest single feature.

Hackathon priority: SiteScore (done) + EarnMax forecast chart + value card = the demo. Monitoring
card and real data are nice-to-haves.

---

## 11. Pitch & demo (3 min)

1. Hook (20s): "Grid connections, not GPUs, are the bottleneck. We turn restricted grid areas into
   the best places to build."
2. SiteScore (60s): pick "Container", type a postal code → its tile scores high among neighbors →
   show subscores, power mix, carbon badge.
3. Boost (30s): toggle +20 kWh battery → score jumps. "That's the report the customer pays for once."
4. EarnMax (60s): forecast with recommended load profile → value stack "€X today, +€Y/month extra,
   net +€Z after the fee" → a thermal alert. "That's the subscription."
5. Close (10s): "Decide once with SiteScore. Earn every day with EarnMax."

Selling to Invertix specifically: demo the grid-asset/flexibility angle and mention each micro-site
is a flexible asset near renewables — that's their world. Pre-bake answers: "is latency model real?"
(conservative estimate, swappable), "where's the data from?" (Ember/SMARD/OSM, all open),
"what about training workloads?" (out of scope by design; training stays centralized).

---

## 12. Style rules (keep these)

- Code must not look AI-generated: lowercase terse comments, no docstrings, realistic TODOs,
  no authorship markers.
- Copy: short, punchy, human. No em dashes. Plain language for non-technical audiences.
- Map: light/Airbnb aesthetic, accent `#E0703C`, minimal chrome.
- Lead with consequences before mechanisms.

---

## 13. How to run

```
# backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000           # add MICRODC_ZERO=1 for the live-read test

# frontend (serve over http so the localhost fetch works — file:// can be blocked, esp. Safari)
cd frontend
python3 -m http.server 5500
# open http://localhost:5500/sitescore.html

# regenerate node data
cd backend/pipeline
pip install -r requirements.txt
python build_nodes.py
```

---

## 14. Honest open risks

- Scope: two products in a hackathon is a lot. Keep EarnMax to one killer chart + value card.
- Grid-headroom data is the most valuable and hardest to source — proxy it and say so.
- EarnMax euro figures are illustrative/top-of-range — show assumptions or a judge will poke them.
- Voronoi tiles are approximate postal-code shapes, not official boundaries.
- The frontend embeds ~1MB demo GeoJSON; once the backend fetch is reliable, slim it but keep a
  small fallback.
```
