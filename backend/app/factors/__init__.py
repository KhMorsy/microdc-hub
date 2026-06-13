# the five sitescore inputs, one provider module each.
# each exposes value(plz) -> raw real-world metric, plus HIGHER_IS_BETTER so the scorer
# knows which direction is good. swap the inside of any value() for real data without touching the rest.

from . import grid, price, carbon, flex, heat

# keyed by the same names scoring.py / the data contract use
PROVIDERS = {
    "grid": grid,
    "price": price,
    "carbon": carbon,
    "flex": flex,
    "heat": heat,
}
