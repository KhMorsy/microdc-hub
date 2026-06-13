# backend — microdc-hub

Two jobs: serve the scored SiteScore nodes, and serve the EarnMax forecast/monitor.

## run the api
```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Then:
- `GET /health`
- `GET /nodes`                 → all scored postal-code nodes (GeoJSON)
- `GET /nodes?plz=80331`       → one node
- `GET /nodes?capacity=campus` → attach a composite score under that capacity's weights
- `GET /forecast/80331?kw=30&shiftable=0.6` → 24h price/carbon + recommended load + value stack
- `GET /monitor/80331`         → telemetry + alerts (synthetic)
- `GET /reload`                → re-read the baked data without restarting

Interactive docs at http://localhost:8000/docs

## regenerate the node data
```
cd backend/pipeline
python build_geojson.py        # writes ../data/nodes.geojson
```
`build_geojson.py` walks every postal code, pulls each scoring input from its provider in
`app/factors/`, normalizes them by percentile rank, and bakes the result. The first run fetches the
live feeds (Energy-Charts prices and carbon, OSM substations and heat buyers) and caches them; later
runs are fast. To change a data source, edit one `value(plz)` in `app/factors/` — the schema, the
scorer and the frontend do not change.

Note: `build_nodes.py` is the older builder that generates the Voronoi tile geometry (needs
numpy/scipy/shapely from `pipeline/requirements.txt`). `build_geojson.py` reuses that geometry and is
the current scoring pass.

## contract
`frontend/DATA_CONTRACT.md` is the source of truth for the node schema.
