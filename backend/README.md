# backend — microdc-hub

Serves the scored SiteScore nodes, the EarnMax forecast/monitor, and the rooftop-solar ranking.

## run the api
```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
For the rooftop-solar endpoint, pass a Google Solar API key (optional):
```
GOOGLE_SOLAR_API_KEY="your-key" uvicorn app.main:app --reload --port 8000
```

Endpoints:
- `GET /health`
- `GET /nodes`                 → all scored postal-code nodes (GeoJSON)
- `GET /nodes?plz=80331`       → one node
- `GET /nodes?capacity=campus` → attach a composite score under that capacity's weights
- `GET /forecast/80331?kw=30&shiftable=0.6` → 24h price/carbon + recommended load + value stack
- `GET /monitor/80331`         → telemetry + alerts (synthetic)
- `GET /solar-sites/80331?n=3` → best rooftop-solar buildings in the postal code (needs the key)
- `GET /reload`                → re-read the baked data without restarting

Interactive docs at http://localhost:8000/docs

## regenerate the node data
```
cd backend/pipeline
python build_geojson.py        # writes ../data/nodes.geojson
```
`build_geojson.py` walks every postal code, pulls each scoring input from its provider in
`app/factors/`, normalizes them by percentile rank, and bakes the result (subscores, per-capacity
grid, price, carbon, power mix, local generation, local PPA price). The first run fetches the live
feeds (Energy-Charts prices/carbon, OSM substations / heat buyers / power plants) and caches them;
later runs are fast. To change a data source, edit one `value(plz)` in `app/factors/` — the schema,
the scorer and the frontend do not change.

Tile geometry: `build_nodes.py` builds Bavaria's Voronoi tiles, `build_austria_tiles.py` adds
Austria's (Voronoi from GeoNames centroids, clipped to the country boundary). Both need
numpy/scipy/shapely from `pipeline/requirements.txt`. `build_geojson.py` reuses that geometry and is
the scoring pass.

## contract
`frontend/DATA_CONTRACT.md` is the source of truth for the node schema.
