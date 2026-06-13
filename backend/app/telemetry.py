# synthetic node telemetry for the monitoring card. recommendations only, no actuation.
import math, time, hashlib


def monitor(plz):
    s = int(hashlib.md5(plz.encode()).hexdigest()[:6], 16)
    h = time.localtime().tm_hour
    power = round(18 + 6 * math.sin(h / 24 * 2 * math.pi) + (s % 4), 1)
    limit = 30.0
    headroom = round(max(5.0, 100 - power / limit * 100 + (s % 10) - 5), 1)
    inlet = round(22 + 5 * math.sin((h - 14) / 24 * 2 * math.pi), 1)
    alerts = []
    # scripted afternoon thermal event so the demo always shows an alert mid-day
    if 13 <= h <= 16:
        alerts.append({"from": "14:00", "to": "16:00", "action": "reduce load 15%", "reason": "thermal limit"})
    return {
        "plz": plz,
        "thermal_headroom_pct": headroom,
        "power_kw": power,
        "power_limit_kw": limit,
        "inlet_c": inlet,
        "alerts": alerts,
    }
