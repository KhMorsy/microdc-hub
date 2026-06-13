# builds backend/data/nodes.geojson — one scored feature per bavaria postal code.
#
# current state: postal-code tiles are voronoi cells around plz centroids clipped to bavaria,
# and the 5 subscores are spatially-generated MOCK values.
#
# TODO (real data, swap in place — schema stays identical):
#   geometry  -> official plz polygons (suche-postleitzahl.org, ODbL) instead of voronoi cells
#   grid      -> PyPSA-Eur line loading + substation distance (spare connection capacity)
#   price     -> SMARD / ENTSO-E zonal day-ahead prices
#   carbon    -> Ember + SMARD generation mix (gCO2/kWh)
#   flex      -> daily price spread from SMARD (arbitrage potential)
#   heat      -> OSM heat buyers nearby (pools, greenhouses, large buildings)
#
# run:  python build_nodes.py   (writes ../data/nodes.geojson)

import json, math, os, random
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

HERE = os.path.dirname(__file__)
COUNTIES = os.path.join(HERE, "inputs", "bavaria_counties.json")   # used only to clip voronoi to bavaria
CENTROIDS = os.path.join(HERE, "inputs", "plz_centroids.json")     # plz -> [lat, lon]
OUT = os.path.join(HERE, "..", "data", "nodes.geojson")

MUC = (48.137, 11.575)
NUR = (49.452, 11.077)


def dist_km(lat, lon, a):
    return math.hypot((a[0] - lat) * 111, (a[1] - lon) * 71)


def bavaria_boundary():
    counties = json.load(open(COUNTIES, encoding="utf-8"))["regions"]
    polys = []
    for r in counties:
        try:
            polys.append(Polygon([(p[0], p[1]) for p in r["ring"]]).buffer(0))
        except Exception:
            pass
    return unary_union(polys).buffer(0)


def main():
    random.seed(11)
    bav = bavaria_boundary()
    plz = json.load(open(CENTROIDS, encoding="utf-8"))

    pts, codes = [], []
    for code, (lat, lon) in plz.items():
        if bav.contains(Point(lon, lat)):
            pts.append((lon, lat)); codes.append(code)

    P = np.array(pts)
    minx, miny, maxx, maxy = bav.bounds
    frame = np.array([[minx - 2, miny - 2], [maxx + 2, miny - 2], [minx - 2, maxy + 2], [maxx + 2, maxy + 2]])
    vor = Voronoi(np.vstack([P, frame]))

    def cell(i):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            return None
        return Polygon([vor.vertices[v] for v in reg])

    # --- MOCK metrics (replace per TODO above) ---
    raw = []
    for (lon, lat) in pts:
        dM, dN = dist_km(lat, lon, MUC), dist_km(lat, lon, NUR)
        pull = math.exp(-dM / 90) + 0.6 * math.exp(-dN / 90)
        north = (lat - 47.3) / (50.6 - 47.3)
        raw.append(dict(
            price=74 + 24 * pull + random.uniform(-2, 2),
            carbon=205 + 150 * north - 40 * math.exp(-dM / 200) + random.uniform(-12, 12),
            cong=min(0.95, 0.22 + 0.5 * pull + random.uniform(-0.04, 0.04)),
            flex=45 + 45 * pull + random.uniform(-6, 6),
            heat=30 + 55 * math.exp(-dM / 70) + 40 * math.exp(-dN / 70) + random.uniform(0, 8),
            north=north,
        ))
    arr = np.array([(r["price"], r["carbon"], r["cong"], r["flex"], r["heat"]) for r in raw])

    def nrm(c):
        lo, hi = c.min(), c.max(); return (c - lo) / ((hi - lo) or 1)

    price_s = 1 - nrm(arr[:, 0]); carbon_s = 1 - nrm(arr[:, 1]); grid_s = 1 - nrm(arr[:, 2])
    flex_s = nrm(arr[:, 3]); heat_s = nrm(arr[:, 4])

    feats = []
    for i, (lon, lat) in enumerate(pts):
        c = cell(i)
        if c is None:
            continue
        g = c.intersection(bav)
        if g.is_empty:
            continue
        if isinstance(g, MultiPolygon):
            g = max(g.geoms, key=lambda x: x.area)
        g = g.simplify(0.004, preserve_topology=True)
        if g.is_empty or g.geom_type != "Polygon":
            continue
        ring = [[round(x, 4), round(y, 4)] for x, y in g.exterior.coords]
        carbon = int(round(raw[i]["carbon"]))
        band = "low" if carbon < 200 else ("mid" if carbon < 300 else "high")
        north = raw[i]["north"]
        wind = round(0.18 + 0.30 * north, 2); solar = round(0.30 - 0.12 * north, 2)
        grid = round(max(0.0, 1 - wind - solar), 2)
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "plz": codes[i], "name": codes[i], "centroid": [round(lon, 4), round(lat, 4)],
                "sub": {"grid": int(round(grid_s[i] * 100)), "price": int(round(price_s[i] * 100)),
                        "carbon": int(round(carbon_s[i] * 100)), "flex": int(round(flex_s[i] * 100)),
                        "heat": int(round(heat_s[i] * 100))},
                "price_eur_mwh": int(round(raw[i]["price"])), "carbon_g_kwh": carbon, "carbon_band": band,
                "mix": {"wind": wind, "solar": solar, "grid": grid},
                "boost": {"battery_20kwh": random.choice([5, 6, 7]), "resize": random.choice([2, 3])},
            },
        })

    json.dump({"type": "FeatureCollection", "features": feats}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("wrote", OUT, "with", len(feats), "nodes")


if __name__ == "__main__":
    main()
