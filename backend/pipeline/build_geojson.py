# builds the final backend/data/nodes.geojson the frontend reads.
#
# walks every postal code, pulls each input from its provider (app/factors/*), normalizes the five
# into 0-100 subscores (app/score_plz), and emits one feature per plz in the DATA_CONTRACT schema.
#
# geometry (the voronoi tile shapes) is reused from the existing geojson — that's a separate, rarely
# -changing concern handled by build_nodes.py. this file is purely the scoring/data pass: swap any
# factors/<input>.value() for real data and re-run, the schema stays identical.
#
# run:  python build_geojson.py

import json, os, sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))   # so we can import the app package

from app.factors import price as price_f, carbon as carbon_f, geo, sources   # noqa: E402
from app import score_plz                                            # noqa: E402

GEOMETRY_SRC = os.path.join(HERE, "..", "data", "nodes.geojson")     # tile shapes come from here
OUT = os.path.join(HERE, "..", "data", "nodes.geojson")


# power mix shown in the detail panel — REAL national generation mix (energy-charts), same for all nodes.
def power_mix(plz):
    return sources.power_mix()


# boost deltas for the "what-if" toggles — deterministic per plz so re-runs are stable.
def boosts(plz):
    return {
        "battery_20kwh": int(5 + round(geo.jitter(plz, "battery", 0, 2))),
        "resize": int(2 + round(geo.jitter(plz, "resize", 0, 1))),
    }


def main():
    with open(GEOMETRY_SRC, encoding="utf-8") as f:
        src = json.load(f)

    # the postal codes we'll emit — drives normalization so subscores are relative to this exact set
    geoms = {}
    plz_list = []
    for ft in src["features"]:
        p = ft["properties"]
        code = p.get("plz")
        if not code:
            continue
        geoms[code] = {"geometry": ft["geometry"], "centroid": p.get("centroid"), "name": p.get("name", code)}
        plz_list.append(code)

    subs = score_plz.subscores(plz_list, use_cache=False)       # normalized across plz_list
    gbc = score_plz.grid_by_capacity(plz_list)                  # grid subscore per capacity class

    feats = []
    for code in plz_list:
        sub = subs.get(code)
        if sub is None:
            continue
        carbon = carbon_f.value(code)
        feats.append({
            "type": "Feature",
            "geometry": geoms[code]["geometry"],
            "properties": {
                "plz": code,
                "name": geoms[code]["name"],
                "centroid": geoms[code]["centroid"],
                "sub": sub,
                "grid_by_cap": gbc[code],          # frontend swaps sub.grid to match the capacity pill
                "price_eur_mwh": int(price_f.value(code)),
                "carbon_g_kwh": carbon,
                "carbon_band": carbon_f.band(carbon),
                "mix": power_mix(code),
                "boost": boosts(code),
            },
        })

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, ensure_ascii=False)
    print("wrote", OUT, "with", len(feats), "nodes")


if __name__ == "__main__":
    main()
