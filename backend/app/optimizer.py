# earnmax forecast + greedy load-shifting. the value-stack euros are illustrative; price + carbon are REAL.
from .factors import sources


# real 24h day-ahead price + carbon curve for the zone (energy-charts).
# national today, so the same shape per plz; the value stack still scales with kw/shiftable.
def day_profile(plz):
    prices = sources.price_curve()
    carbon = sources.carbon_curve()
    return [{"t": "%02d:00" % h, "price_eur_mwh": prices[h], "carbon_g_kwh": carbon[h]} for h in range(24)]


# greedy: run heavy (shiftable) compute in the cheapest hours, throttle when expensive
def recommend(plz, kw=30, shiftable=0.6):
    hours = day_profile(plz)
    cheap_n = 10  # cheapest ~10h carry the heavy load
    cheap = set(sorted(range(24), key=lambda i: hours[i]["price_eur_mwh"])[:cheap_n])
    throttled = round(kw * (1 - shiftable), 1)
    for i, h in enumerate(hours):
        h["load_kw_recommended"] = kw if i in cheap else throttled

    flat = sum(h["price_eur_mwh"] for h in hours) * kw / 1000.0
    managed = sum(h["price_eur_mwh"] * h["load_kw_recommended"] for h in hours) / 1000.0
    arbitrage = round(max(0.0, flat - managed), 1)

    # rough value split — illustrative, tune against real tariffs
    value = {
        "arbitrage": arbitrage,
        "peak_shaving": round(arbitrage * 0.30, 1),
        "heat": round(kw * 0.30, 1),
        "certificates": round(kw * 0.05, 1),
    }
    return {"plz": plz, "kw": kw, "shiftable": shiftable, "hours": hours, "value_today_eur": value}
