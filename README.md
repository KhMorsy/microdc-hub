# MicroDC Hub

**Where should we build a micro data center, how do we power it, and how do we run it?**

A siting, supply-planning and operations tool for small flexible data centers across **Bavaria and Austria**, scored per postal code on live energy, grid, and generation data.

> Compute that follows power, not power that chases compute.

| Package | Model | Job |
|---|---|---|
| **SiteScore** | One-time | Where to build: scored PLZ areas, power mix, carbon intensity, boost proposals |
| **EarnMax** | Subscription | How to earn: forecast, load profile, extra earnings vs. unmanaged operation, monitoring |

Built for the Invertix "Data-Center Siting & Power" track.

---

## Quickstart (run the app)

Requires Python 3.9+.

**1. Backend (FastAPI on :8000)**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
Optional Google Solar API key for rooftop-solar feature:
```bash
GOOGLE_SOLAR_API_KEY="your-key" uvicorn app.main:app --port 8000
```

**2. Frontend**
```bash
cd frontend
python3 -m http.server 5500
# open http://localhost:5500/start.html
```

**3. Rebuild scored data (optional — repo ships with baked data)**
```bash
cd backend/pipeline
python build_geojson.py
```

---

## The product — one flow, four screens

```
start.html      Home / input  ── pick size, optimize goal, radius, postal code
   │  Build my supply mix →
supply.html     Supply mix    ── grid / PPA / on-site blend, cost & carbon, confirm
   │  Confirm & open the map →
sitescore.html  The map       ── every postal code scored 0–100, drill into a site
   │  Open EarnMax →
earnmax.html    EarnMax        ── 24h day-ahead plan, value stack, monitoring
```

---

## Scoring model (six factors)

| Factor | What it measures | Source |
|---|---|---|
| **Grid headroom** | proximity to substations, capacity-aware | OpenStreetMap |
| **Price** | wholesale day-ahead electricity price | Energy-Charts |
| **Carbon** | grid carbon intensity from live generation mix | Energy-Charts |
| **Flexibility** | daily price spread | Energy-Charts |
| **Heat reuse** | proximity to heat buyers | OpenStreetMap |
| **Clean energy** | nearby wind + solar + hydro | OpenStreetMap |

See teammate README sections in git history for API endpoints, project structure, refresh job, and known limitations.

---

## Repo layout

### Application
| Path | Purpose |
|---|---|
| [frontend/](frontend/) | `start.html`, `supply.html`, `sitescore.html`, `earnmax.html` |
| [backend/](backend/) | FastAPI, scoring pipeline, `data/nodes.geojson` |
| [PROJECT_BRIEF.md](PROJECT_BRIEF.md) | Full intent, domain notes, business model |

### Presentation & pitch
| Path | Purpose |
|---|---|
| [index.html](index.html) | Full product slide deck (10 slides) |
| [pitch-deck.html](pitch-deck.html) | Pitch-video deck Acts 1–3 with zoom/pan motion (for Loom) |
| [pitch-deck-standalone.html](pitch-deck-standalone.html) | Self-contained deck (single file, shareable) |
| [VO_TELEPROMPTER.md](VO_TELEPROMPTER.md) | Voiceover script for Acts 1–3 |
| [PITCH_SCRIPT.md](PITCH_SCRIPT.md) | 4-minute pitch script & storyline |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Problem, solution, scoring, architecture |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Original hackathon build plan |
| [assets/](assets/) | UI mocks + [assets/video/](assets/video/) pitch frames |

---

## Team onboarding

1. Clone → `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000`
2. `cd frontend && python3 -m http.server 5500` → open `start.html`
3. Read `PROJECT_BRIEF.md` for product context; `PITCH_SCRIPT.md` for the demo narrative

---

## API

| Endpoint | What it returns |
|---|---|
| `GET /health` | status, node count |
| `GET /nodes` | scored postal-code nodes (GeoJSON). `?plz=`, `?capacity=`, `?shiftable=` |
| `GET /score` | dynamic weight mix for capacity and shiftable |
| `GET /forecast/{plz}` | 24h plan, recommended load, value stack |
| `GET /monitor/{plz}` | monitoring card (synthetic) |
| `GET /solar-sites/{plz}` | top rooftop-solar buildings (needs `GOOGLE_SOLAR_API_KEY`) |
| `GET /reload` | force re-read of baked data |

---

## Known limitations

- Grid factor = infrastructure access, not spare capacity (PyPSA-Eur would fix this).
- Local generation capacities partly estimated from OSM; MaStR would improve this.
- EarnMax monitoring is synthetic until real site telemetry exists.
- Tile shapes are Voronoi approximations, not official PLZ boundaries.

See `PROJECT_BRIEF.md` for roadmap and full domain notes.
