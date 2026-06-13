# per-postal-code scoring. pulls each input's raw value from its provider (factors/*),
# normalizes the five across all postal codes into 0-100 subscores, then applies the
# equation + weights from scoring.py to get one composite score per plz.
#
# pipeline:  factors.value(plz)  ->  normalize across set  ->  sub{}  ->  scoring.composite(sub, weights)

import bisect
from .factors import PROVIDERS, geo, grid as grid_f
from .scoring import IDS, build_weights, composite

_SUB_CACHE = None


# raw real-world metric per factor per plz: {factor: {plz: raw}}
def raw_table(plz_list=None):
    plz_list = plz_list or geo.all_plz()
    table = {}
    for name, mod in PROVIDERS.items():
        col = {}
        for plz in plz_list:
            try:
                col[plz] = mod.value(plz)
            except KeyError:
                pass
        table[name] = col
    return table


# normalize one factor to 0-100 by PERCENTILE RANK across all sites (red->green ranking map).
# rank handles heavy-tailed spatial factors gracefully (a few dense-substation outliers don't squash
# the rest) and gives an even spread. a uniform factor (national feeds) can't rank -> neutral 50.
def _normalize(col, higher_is_better):
    items = list(col.items())
    if len(set(v for _, v in items)) == 1:
        return {plz: 50 for plz in col}
    order = sorted(v for _, v in items)
    n = len(order)
    out = {}
    for plz, v in items:
        lo = bisect.bisect_left(order, v)
        hi = bisect.bisect_right(order, v)
        p = ((lo + hi - 1) / 2.0) / (n - 1)   # average percentile rank, ties shared
        if not higher_is_better:
            p = 1 - p
        out[plz] = int(round(p * 100))
    return out


# turn a raw table into normalized 0-100 subscores: {plz: {grid,price,carbon,flex,heat}}
def normalize_all(table):
    norm = {name: _normalize(table[name], PROVIDERS[name].HIGHER_IS_BETTER) for name in PROVIDERS}
    out = {}
    for plz in table["grid"]:
        out[plz] = {name: norm[name][plz] for name in IDS}
    return out


# the five subscores per plz, normalized across the whole set
def subscores(plz_list=None, use_cache=True):
    global _SUB_CACHE
    if use_cache and plz_list is None and _SUB_CACHE is not None:
        return _SUB_CACHE
    out = normalize_all(raw_table(plz_list))
    if plz_list is None and use_cache:
        _SUB_CACHE = out
    return out


# grid subscore for EVERY capacity class: {plz: {edge,micro,container,small,campus}}.
# grid is the one factor whose value depends on capacity (bigger load -> needs higher-voltage grid),
# so we rank-normalize each class separately. the frontend swaps sub.grid when the capacity pill changes.
def grid_by_capacity(plz_list=None):
    plz_list = plz_list or geo.all_plz()
    caps = list(grid_f.CAP_MIN_KV.keys())
    norm = {cap: _normalize({p: grid_f.value(p, cap) for p in plz_list}, grid_f.HIGHER_IS_BETTER) for cap in caps}
    return {p: {cap: norm[cap][p] for cap in caps} for p in plz_list}


# composite score for one postal code, given the case (capacity + shiftable + optional weight override).
def score(plz, capacity=None, shiftable=0.5, weights=None):
    sub = subscores().get(plz)
    if sub is None:
        raise KeyError("unknown plz: %s" % plz)
    w = build_weights(capacity, weights, shiftable)
    return {"plz": plz, "sub": sub, "weights": w, "score": composite(sub, w)}


# composite score for every postal code: {plz: score}. weights are built once, shared across all plz.
def score_all(capacity=None, shiftable=0.5, weights=None):
    w = build_weights(capacity, weights, shiftable)
    return {plz: composite(sub, w) for plz, sub in subscores().items()}
