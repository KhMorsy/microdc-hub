# MicroDC Hub

**SiteScore + EarnMax** — platform for distributed micro data centers. Invertix Challenge · Data-Center Siting & Power.

| Package | Model | Job |
|---|---|---|
| **SiteScore** | One-time | Where to build: scored PLZ areas, power mix, carbon intensity, boost proposals |
| **EarnMax** | Subscription | How to earn: forecast, load profile, extra earnings vs. unmanaged operation, monitoring |

Node resolution: **one PLZ polygon per node** (~8,200 in Germany).

Pitch: *"Decide once with SiteScore. Earn every day with EarnMax — that's MicroDC Hub."*

## Repo layout

| Path | Purpose |
|---|---|
| [index.html](index.html) | Slide deck (10 slides). Open in browser; ↑/↓ to navigate. |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Problem, solution, scoring, architecture, demo script — **start here** |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Data contracts, datasets, parallel workstreams, 5-hour build plan |
| [assets/](assets/) | UI mocks (`mock-sitescore.png`, `mock-earnmax.png`) |

## Quick start

```bash
open index.html
```

## Create & push this repo (`microdc-hub`)

GitHub repo name: **`microdc-hub`** (matches the product name MicroDC Hub).

```bash
cd microdc-hub          # this folder, once cloned or copied

git init
git add .
git commit -m "Initial commit: MicroDC Hub presentation, context, and implementation plan"

# GitHub CLI (creates github.com/<you>/microdc-hub)
gh repo create microdc-hub --public --source=. --remote=origin --push

# Or manually: create empty repo "microdc-hub" on GitHub, then:
git remote add origin https://github.com/<you>/microdc-hub.git
git branch -M main
git push -u origin main
```

**Team onboarding:** clone → read `PROJECT_CONTEXT.md` → assign workstreams from `IMPLEMENTATION_PLAN.md` → open `index.html` for the pitch deck.

## Hackathon build (next step)

Application code will live in this same repo under `api/`, `web/`, and `data/` per [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
