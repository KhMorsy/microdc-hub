# adds austria to the map: builds voronoi tiles for austrian postal codes (geonames centroids,
# clipped to the austria boundary), merges the centroids into plz_centroids.json, and appends the
# tiles into data/nodes.geojson. idempotent: existing austrian (4-digit) tiles are replaced.
#
# after this, run build_geojson.py to score every node (bavaria + austria) with real per-zone data.
#
# run:  python build_austria_tiles.py

import json, os
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPolygon, Point, shape
from shapely.ops import unary_union

HERE = os.path.dirname(__file__)
GEONAMES = os.path.join(HERE, "inputs", "at_geonames.txt")
BOUNDARY = os.path.join(HERE, "inputs", "austria_boundary.json")
CENTROIDS = os.path.join(HERE, "inputs", "plz_centroids.json")
NODES = os.path.join(HERE, "..", "data", "nodes.geojson")


def austria_boundary():
    bd = json.load(open(BOUNDARY, encoding="utf-8"))
    geoms = [shape(f["geometry"]) for f in bd.get("features", [])] if "features" in bd else [shape(bd)]
    return unary_union(geoms).buffer(0)


def at_centroids(boundary):
    # geonames: country, plz, place, ..., lat(9), lon(10), accuracy. one plz has several place rows.
    agg = {}
    for line in open(GEONAMES, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 11:
            continue
        plz = f[1]
        try:
            lat, lon = float(f[9]), float(f[10])
        except ValueError:
            continue
        agg.setdefault(plz, []).append((lat, lon))
    cent = {}
    for plz, pts in agg.items():
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        if boundary.contains(Point(lon, lat)):   # keep codes that actually sit inside austria
            cent[plz] = (round(lat, 4), round(lon, 4))
    return cent


def main():
    bav = austria_boundary()
    cent = at_centroids(bav)
    codes = list(cent.keys())
    pts = [(cent[c][1], cent[c][0]) for c in codes]   # (lon, lat)
    P = np.array(pts)

    minx, miny, maxx, maxy = bav.bounds
    frame = np.array([[minx - 2, miny - 2], [maxx + 2, miny - 2], [minx - 2, maxy + 2], [maxx + 2, maxy + 2]])
    vor = Voronoi(np.vstack([P, frame]))

    def cell(i):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            return None
        return Polygon([vor.vertices[v] for v in reg])

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
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {"plz": codes[i], "name": codes[i], "centroid": [round(lon, 4), round(lat, 4)]},
        })

    # merge centroids
    allc = json.load(open(CENTROIDS, encoding="utf-8"))
    for plz, (lat, lon) in cent.items():
        allc[plz] = [lat, lon]
    json.dump(allc, open(CENTROIDS, "w", encoding="utf-8"), ensure_ascii=False)

    # append tiles into nodes.geojson, replacing any prior austrian (4-digit) tiles
    nodes = json.load(open(NODES, encoding="utf-8"))
    kept = [ft for ft in nodes["features"] if len(str(ft["properties"].get("plz", ""))) != 4]
    nodes["features"] = kept + feats
    json.dump(nodes, open(NODES, "w", encoding="utf-8"), ensure_ascii=False)

    print("austria: %d centroids inside boundary, %d tiles appended; nodes total %d"
          % (len(cent), len(feats), len(nodes["features"])))


if __name__ == "__main__":
    main()
