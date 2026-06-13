# shared geo lookup for the factor providers. plz -> centroid, plus a couple of distance helpers.
# the mock providers use distance-to-cities to fake a plausible story; real providers key off the same plz.
import json, math, os, hashlib

HERE = os.path.dirname(__file__)
CENTROIDS = os.path.join(HERE, "..", "..", "pipeline", "inputs", "plz_centroids.json")

_CACHE = None

# bavaria reference points the mocks lean on
MUC = (48.137, 11.575)   # munich  — pricey, congested
NUR = (49.452, 11.077)   # nuremberg


def _load():
    global _CACHE
    if _CACHE is None:
        with open(CENTROIDS, encoding="utf-8") as f:
            _CACHE = json.load(f)
    return _CACHE


def centroid(plz):
    c = _load().get(plz)
    if not c:
        raise KeyError("unknown plz: %s" % plz)
    return c[0], c[1]   # lat, lon


def all_plz():
    return list(_load().keys())


def dist_km(plz, ref):
    lat, lon = centroid(plz)
    return math.hypot((ref[0] - lat) * 111, (ref[1] - lon) * 71)


def north(plz):
    lat, _ = centroid(plz)
    return (lat - 47.3) / (50.6 - 47.3)   # 0 at the alps, 1 at the northern edge


# deterministic per-plz jitter so value(plz) is stable across calls (no global random state)
def jitter(plz, salt, lo, hi):
    h = int(hashlib.md5((plz + salt).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * h
