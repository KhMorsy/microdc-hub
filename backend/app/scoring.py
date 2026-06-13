# sitescore composite. one fixed equation, weights flex with the inputs.
# score = sum(subscore_i * weight_i), weights derived from capacity + shiftable, renormalized to 1.

IDS = ["grid", "price", "carbon", "flex", "heat"]

# capacity presets set the *starting* weights (order: grid, price, carbon, flex, heat).
# tiny on-prem sites care about heat/flex; big grid loads are dominated by headroom.
CAPS = {
    "edge":      [10, 20, 20, 20, 30],
    "micro":     [15, 22, 20, 20, 23],
    "container": [30, 25, 20, 15, 10],
    "small":     [38, 24, 18, 13, 7],
    "campus":    [45, 25, 18, 9, 3],
}
DEFAULT_CAP = "container"


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# build the weight vector for this case. all inputs feed in here:
#  - capacity preset picks the base weights
#  - explicit overrides (dict or 5-list) replace the base if given
#  - shiftable share scales the flex weight: 0 -> half, 1 -> 1.5x
# then renormalize so the five sum to 1 (the equation never changes, only the mix).
def build_weights(capacity=None, weights=None, shiftable=0.5):
    if weights is not None:
        w = [float(weights[k]) for k in IDS] if isinstance(weights, dict) else [float(x) for x in weights]
    else:
        w = list(CAPS.get((capacity or DEFAULT_CAP).lower(), CAPS[DEFAULT_CAP]))

    sh = _clamp(float(shiftable), 0.0, 1.0)
    w[3] = w[3] * (0.5 + sh)            # flex weight reacts to how much load can wait

    s = sum(w) or 1.0
    return {k: w[i] / s for i, k in enumerate(IDS)}


# weighted sum of the five subscores, 0-100.
def composite(sub, w):
    s = sum(float(sub.get(k, 0)) * w[k] for k in IDS)
    return int(round(_clamp(s, 0, 100)))


# score one node. returns the number, the boosted number, and the weights used (for the explain panel).
def score_node(props, capacity=None, shiftable=0.5, weights=None, boosts=None):
    w = build_weights(capacity, weights, shiftable)
    base = composite(props.get("sub", {}), w)

    delta = 0
    b = props.get("boost", {}) or {}
    for flag in (boosts or []):
        if flag == "battery":
            delta += b.get("battery_20kwh", 0)
        elif flag == "resize":
            delta += b.get("resize", 0)

    return {
        "score": base,
        "score_boosted": int(round(_clamp(base + delta, 0, 100))),
        "boost_delta": delta,
        "weights": w,
    }


# score a whole geojson collection in place-ish: returns new features with the composite attached.
def score_collection(fc, capacity=None, shiftable=0.5, weights=None, boosts=None):
    w = build_weights(capacity, weights, shiftable)
    feats = []
    for ft in fc["features"]:
        p = dict(ft["properties"])
        base = composite(p.get("sub", {}), w)
        p["score"] = base
        feats.append({"type": "Feature", "geometry": ft["geometry"], "properties": p})
    return {
        "type": "FeatureCollection",
        "weights": w,
        "capacity": (capacity or DEFAULT_CAP).lower(),
        "shiftable": _clamp(float(shiftable), 0.0, 1.0),
        "features": feats,
    }
