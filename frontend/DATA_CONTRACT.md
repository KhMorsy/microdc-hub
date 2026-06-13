# SiteScore — data contract (backend → map)

Bavaria only. One **GeoJSON file**: `nodes.geojson` — one Feature per PLZ (postal-code area).
The map renders whatever you put in `properties`; it computes the composite score, boosts,
and weighting itself. **You just deliver the 5 subscores + display values + geometry.**

---

## What the backend delivers

A single `nodes.geojson`, `FeatureCollection`, one Feature per Bavaria PLZ.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [ [ [lon,lat], [lon,lat], ... ] ] },
      "properties": {
        "plz": "80933",
        "name": "München-Feldmoching",
        "centroid": [11.55, 48.21],

        "sub": { "grid": 90, "price": 74, "carbon": 88, "flex": 79, "heat": 65 },

        "price_eur_mwh": 71,
        "carbon_g_kwh": 142,
        "carbon_band": "low",
        "mix": { "wind": 0.38, "solar": 0.27, "grid": 0.35 },

        "boost": { "battery_20kwh": 6, "resize": 3 }
      }
    }
  ]
}
```

---

## Field reference

| Field | Type | Range / units | Meaning |
|---|---|---|---|
| `plz` | string | 5 digits | postal code (the node id) |
| `name` | string | — | human label (district / area name) |
| `centroid` | [lon, lat] | WGS84 | used to fly the map + place the label |
| `geometry` | Polygon | WGS84, simplified | the PLZ outline (keep it simplified — see note) |
| `sub.grid` | int | 0–100 | **grid headroom** — spare connection capacity (high = easy/fast to connect) |
| `sub.price` | int | 0–100 | **price** — 100 = cheapest electricity |
| `sub.carbon` | int | 0–100 | **carbon** — 100 = cleanest power mix |
| `sub.flex` | int | 0–100 | **flexibility** — from daily price spread (100 = biggest spread = most to gain shifting load) |
| `sub.heat` | int | 0–100 | **heat reuse** — proximity to a heat buyer (pool / greenhouse / big building) |
| `price_eur_mwh` | int | €/MWh | shown in the node panel (the raw number behind `sub.price`) |
| `carbon_g_kwh` | int | gCO₂/kWh | shown + drives `carbon_band` |
| `carbon_band` | string | "low" / "mid" / "high" | badge color |
| `mix.wind/solar/grid` | float | 0–1, sum ≈ 1 | power-mix donut |
| `boost.battery_20kwh` | int | points | how much the score rises if a 20 kWh battery is added |
| `boost.resize` | int | points | how much the score rises if the node is resized to the next class |

**All 5 subscores must be 0–100 and normalized across all Bavaria nodes** (min–max), so colors spread nicely. Don't pre-weight them — the map applies the weights.

---

## What the MAP does (so you DON'T)

- **Composite score** = weighted sum of the 5 subscores. Weights are sliders in the UI
  (default: grid 30 / price 25 / carbon 20 / flex 15 / heat 10). You don't compute the composite.
- **Shiftable %** (one input: "how much of the workload can wait?") only re-weights `flex` in the UI.
  You don't need it — just give the full-potential `flex` subscore from price spread.
- **Capacity category** (Edge / Micro / Container / Small / Campus) only changes default weights in the UI.
- **Boost toggles** re-score client-side using your `boost` deltas. Just supply the numbers.

---

## Coverage & size

- **Bavaria PLZ only** (~2,000). Not all of Germany.
- Simplify polygons hard (target < ~30 KB per feature, whole file ideally < ~5–8 MB).
  `mapshaper -simplify 5%` or shapely `simplify(0.001)` is fine.
- If a node is missing data, either omit it or set the missing `sub.*` to `null` — the map will grey it out rather than fake a value.

---

## Minimum to unblock me early

Send a **5-node sample** that matches this schema in the first hour (any 5 real PLZ).
I build the whole map against the sample; you swap in the full ~2,000-node file later —
same schema, no frontend changes. I load it via the "Load data" button.
